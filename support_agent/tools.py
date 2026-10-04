from __future__ import annotations
import time
from datetime import date
from .schemas import ToolContext,ToolInvocation,ToolResult,EscalationRequest
from .failures import InjectedTimeout
class Tools:
 def __init__(self,store,retriever,trace,injector=None):self.s=store;self.r=retriever;self.t=trace;self.i=injector
 def _record(self,i,ctx,fn,retry=0):
  start=time.perf_counter(); row={'tool':i.tool,'write':i.write,'params':self._redact(i.params),'retry_attempt':retry,'idempotency_key':ctx.idempotency_key,'status':'started'};self.t.tool_calls.append(row)
  try:
   marker=self.i.before(i.tool) if self.i else None; result=fn();
   if marker=='malformed':raise ValueError('malformed tool response')
   if marker=='timeout':raise InjectedTimeout('ambiguous server timeout')
   row.update(status='ok',duration_ms=round((time.perf_counter()-start)*1000,2),transition=result.transition);return result
  except Exception as e:
   row.update(status='error',error_type=type(e).__name__,duration_ms=round((time.perf_counter()-start)*1000,2));self.t.errors.append({'tool':i.tool,'type':type(e).__name__});raise
 def _redact(self,p):return {k:('[redacted]' if k in {'address','email','otp','password','upi'} else v) for k,v in p.items()}
 def _order(self,ctx):
  if ctx.principal_id!=ctx.customer_id:raise PermissionError('principal mismatch')
  if not ctx.order_id:raise ValueError('order required')
  return self.s.order(ctx.order_id,ctx.customer_id)
 def _active(self,ctx):
  if ctx.account_status!='active':raise PermissionError('active account required')
 def execute(self,i,ctx,retry=0):
  i.validate();
  if i.tool=='search_knowledge_base': return self._record(i,ctx,lambda:ToolResult(i.tool,True,{'evidence':self.r.search(i.params['query'],self.i.mode if self.i else None)}),retry)
  if i.tool=='get_customer_profile':
   return self._record(i,ctx,lambda:ToolResult(i.tool,True,{'account_status':ctx.account_status}),retry)
  if i.tool in {'get_order_details','get_customer_orders'}:
   def read():
    if ctx.account_status=='locked' and not ctx.verified:raise PermissionError('locked unverified account')
    if i.tool=='get_order_details':return ToolResult(i.tool,True,{'order':self.s.public_order(self._order(ctx))})
    return ToolResult(i.tool,True,{'orders':[self.s.public_order(o) for o in self.s.orders.values() if o['customer_id']==ctx.customer_id]})
   return self._record(i,ctx,read,retry)
  if i.tool=='check_pincode_serviceability':
   pin=i.params.get('pincode');return self._record(i,ctx,lambda:ToolResult(i.tool,True,{'serviceable':isinstance(pin,str) and pin in {'400069','500081','600042','110024','411045','380015','500034','695004','440010'}}),retry)
  if i.tool=='check_replacement_stock':return self._record(i,ctx,lambda:ToolResult(i.tool,True,{'in_stock':not bool(i.params.get('force_out_of_stock'))}),retry)
  if i.tool=='cancel_order':
   def f():
    o=self._order(ctx);self._active(ctx)
    if o['status']!='processing':raise PermissionError('cancel lifecycle denied')
    if self.s.operations.get(ctx.idempotency_key):raise PermissionError('duplicate operation')
    before=o['status'];o.update(status='cancelled',tracking_stage='cancelled',refund_status='refund_initiated');self.s.operations[ctx.idempotency_key]=i.tool
    return ToolResult(i.tool,True,{'order_id':o['order_id']},transition={'status':[before,'cancelled']})
   return self._record(i,ctx,f,retry)
  if i.tool=='update_address':
   def f():
    o=self._order(ctx);self._active(ctx);a=i.params.get('address',{});pin=a.get('pincode') if isinstance(a,dict) else None
    if o['tracking_stage']!='order_confirmed' or not isinstance(pin,str) or len(pin)!=6 or not i.params.get('serviceable'):raise PermissionError('address update denied')
    if self.s.operations.get(ctx.idempotency_key):raise PermissionError('duplicate operation')
    before=o['delivery_pincode'];o['delivery_pincode']=pin;self.s.operations[ctx.idempotency_key]=i.tool;return ToolResult(i.tool,True,transition={'delivery_pincode':[before,pin]})
   return self._record(i,ctx,f,retry)
  if i.tool=='create_payment_link':
   def f():
    o=self._order(ctx);self._active(ctx)
    if o['status']!='processing' or o['payment_method']!='COD' or o.get('payment_link_created')=='yes':raise PermissionError('payment link denied')
    o['payment_link_created']='yes';return ToolResult(i.tool,True,{'payment_link_created':True},transition={'payment_link_created':['no','yes']})
   return self._record(i,ctx,f,retry)
  if i.tool=='initiate_return':
   def f():
    o=self._order(ctx);self._active(ctx);days=(ctx.request_date-date.fromisoformat(o['delivery_date'])).days if o['delivery_date'] else 999
    if o['status']!='delivered' or o['is_returnable']!='yes' or not 0<=days<=10 or float(o['amount'])>5000 or o.get('return_requested_date'):raise PermissionError('return denied')
    o.update(tracking_stage='return_pickup_scheduled',return_requested_date=ctx.request_date.isoformat());return ToolResult(i.tool,True,transition={'tracking_stage':['delivered','return_pickup_scheduled']})
   return self._record(i,ctx,f,retry)
  if i.tool=='create_replacement':
   def f():
    o=self._order(ctx);self._active(ctx)
    if o['status']!='delivered' or float(o['amount'])>10000 or len(i.params.get('evidence',[]))<2 or not i.params.get('in_stock') or o.get('replacement_created')=='yes':raise PermissionError('replacement denied')
    o['replacement_created']='yes';return ToolResult(i.tool,True,transition={'replacement_created':['no','yes']})
   return self._record(i,ctx,f,retry)
  if i.tool=='schedule_redelivery':
   def f():
    o=self._order(ctx);self._active(ctx);d=i.params.get('requested_date')
    if o['tracking_stage']!='delivery_attempt_failed' or int(o['delivery_attempts'])>=3 or not isinstance(d,str) or o.get('redelivery_date')==d:raise PermissionError('redelivery denied')
    o['redelivery_date']=d;return ToolResult(i.tool,True,transition={'redelivery_date':[None,d]})
   return self._record(i,ctx,f,retry)
  if i.tool=='schedule_return_pickup':
   def f():
    o=self._order(ctx);self._active(ctx)
    if o['tracking_stage']!='return_pickup_scheduled' or int(o.get('return_reschedules','0'))>=1:raise PermissionError('pickup denied')
    o['return_reschedules']='1';return ToolResult(i.tool,True,transition={'return_reschedules':['0','1']})
   return self._record(i,ctx,f,retry)
  if i.tool=='create_verification_link':
   return self._record(i,ctx,lambda: ToolResult(i.tool,True,{'sent':True}) if ctx.account_status=='locked' and ctx.principal_id==ctx.customer_id else (_ for _ in ()).throw(PermissionError('verification denied')),retry)
  if i.tool=='create_escalation':
   def f():
    req=EscalationRequest(**i.params);req.validate()
    if req.customer_id!=ctx.customer_id or req.order_id!=ctx.order_id:raise PermissionError('escalation context denied')
    self.s.escalations.append(i.params);return ToolResult(i.tool,True,{'escalated':True})
   return self._record(i,ctx,f,retry)
  if i.tool=='update_ticket':return self._record(i,ctx,lambda: ToolResult(i.tool,True,{'updated':True}),retry)
  raise ValueError('unsupported tool')
