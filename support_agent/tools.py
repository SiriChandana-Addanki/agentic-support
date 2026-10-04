from __future__ import annotations
from .failures import InjectedFailure, InjectedTimeout
class Tools:
 def __init__(self, store, retriever, trace, injector=None): self.s=store; self.r=retriever; self.t=trace; self.i=injector
 def _call(self,name, fn, write=False):
  self.t.tool_calls.append({'tool':name,'write':write})
  marker=self.i.before(name) if self.i else None
  result=fn()
  if marker=='malformed': raise ValueError('malformed tool response')
  if marker=='timeout_after_write': raise InjectedTimeout('response timeout after server-side write')
  return result
 def profile(self,cid): return self._call('get_customer_profile',lambda:{k:v for k,v in self.s.customer(cid).items() if k not in {'email'}})
 def orders(self,cid): return self._call('get_customer_orders',lambda:self.s.customer_orders(cid))
 def order(self,oid,cid): return self._call('get_order_details',lambda:self.s.public_order(self.s.order(oid,cid)))
 def knowledge(self,q): return self._call('search_knowledge_base',lambda:self.r.search(q, self.i.mode if self.i else None))
 def serviceability(self,pincode): return self._call('check_pincode_serviceability',lambda:{'pincode':pincode,'serviceable':pincode.isdigit() and len(pincode)==6})
 def stock(self,o): return self._call('check_replacement_stock',lambda:{'order_id':o['order_id'],'in_stock':True})
 def return_pickup(self,o): return self._call('schedule_return_pickup',lambda:{'order_id':o['order_id'],'pickup_rescheduled':True},True)
 def cancel(self,o):
  def f():
   if o['status']!='processing': raise PermissionError('cancellation not authorized')
   o.update(status='cancelled',tracking_stage='cancelled',refund_status='refund_initiated'); return {'order_id':o['order_id'],'state':'cancelled'}
  return self._call('cancel_order',f,True)
 def address(self,o,pincode):
  def f():
   if o['tracking_stage']!='order_confirmed' or not pincode.isdigit() or len(pincode)!=6: raise PermissionError('address update not authorized')
   o['delivery_pincode']=pincode; return {'order_id':o['order_id'],'address_updated':True}
  return self._call('update_address',f,True)
 def payment(self,o): return self._call('create_payment_link',lambda:{'order_id':o['order_id'],'payment_link_created':True} if o['status']=='processing' and o['payment_method']=='COD' else (_ for _ in ()).throw(PermissionError('payment link not authorized')),True)
 def return_(self,o):
  def f():
   if o['status']!='delivered' or o['is_returnable']!='yes': raise PermissionError('return not authorized')
   o['tracking_stage']='return_pickup_scheduled'; o['return_requested_date']='2026-10-01'; return {'pickup_scheduled':True,'refund':'after QC'}
  return self._call('initiate_return',f,True)
 def replacement(self,o): return self._call('create_replacement',lambda:{'replacement_created':True,'pickup_scheduled':True} if float(o['amount'])<=10000 else (_ for _ in ()).throw(PermissionError('replacement limit')),True)
 def redelivery(self,o): return self._call('schedule_redelivery',lambda:{'redelivery_scheduled':True} if o['tracking_stage']=='delivery_attempt_failed' and int(o['delivery_attempts'])<3 else (_ for _ in ()).throw(PermissionError('redelivery not authorized')),True)
 def escalation(self,cid,oid,category,reason,priority='normal'):
  return self._call('create_escalation',lambda:self.s.escalations.append({'customer_id':cid,'order_id':oid,'category':category,'reason':reason,'priority':priority}) or {'escalated':True},True)
 def verification(self,cid): return self._call('create_verification_link',lambda:{'verification_link_sent':True},True)
 def ticket(self,tid,status): return self._call('update_ticket',lambda:self.s.ticket_updates.append({'ticket_id':tid,'status':status}) or {'updated':True},True)
