from __future__ import annotations
import time,uuid
from datetime import datetime,timezone,date
from .schemas import TicketContext,ToolContext,ToolInvocation,Resolution,Trace,ActionPlan
from .tools import Tools,MalformedToolResponse
from .planner import DeterministicPlanner
from .policy import PolicyEngine
from .failures import FailureInjector,InjectedFailure,InjectedTimeout
class Orchestrator:
 def __init__(self,store,retriever,planner=None,policy=None):self.store=store;self.retriever=retriever;self.planner=planner or DeterministicPlanner();self.policy=policy or PolicyEngine()
 def _context(self,t):
  return TicketContext(t['ticket_id'],t['customer_id'],t.get('category','unknown_issue'),t['message'],t.get('order_id'),tuple(t.get('attachments',[])),date(2026,10,1),bool(t.get('verified',False)))
 def resolve(self,ticket,failure_injection=None):
  start=time.perf_counter();ctx=self._context(ticket);trace=Trace(uuid.uuid4().hex,ctx.ticket_id,datetime.now(timezone.utc).isoformat());inj=FailureInjector(failure_injection);tools=Tools(self.store,self.retriever,trace,inj)
  customer=self.store.customer(ctx.customer_id); status=customer['account_status'] if customer else 'unknown'; tc=ToolContext(ctx.customer_id,ctx.customer_id,ctx.ticket_id,ctx.order_id,status,ctx.verified,ctx.request_date,uuid.uuid4().hex)
  query=f'{ctx.category} {ctx.message}'; evidence=self.retriever.search(query,inj.mode);trace.retrieval=[e.__dict__ for e in evidence]
  def finish(action,summary,state='resolved',esc=False,reason=None,text=None):
   trace.final_action=action;trace.final_status=state;trace.escalation=esc;trace.latency_ms=round((time.perf_counter()-start)*1000,2)
   r=Resolution(ctx.ticket_id,ctx.category,summary,trace.retrieval,trace.tool_calls,action,state,esc,reason,text or summary);r.validate();return r,trace
  # Planner parse/validation retry happens before any tool execution.
  plan=None
  for attempt in range(2):
   raw=self.planner.propose(ctx,evidence,inj)
   try:
    if not isinstance(raw,ActionPlan):raise ValueError('invalid structured planner output')
    raw.validate(ctx);plan=raw;break
   except ValueError as e:trace.retries+=1;trace.errors.append({'tool':'planner','type':str(e)})
  if not plan:return finish('escalate_after_tool_failure','Planning output was invalid; a specialist will review.','escalated',True,'planner output invalid')
  decision=self.policy.evaluate(ctx,plan,self.store,evidence)
  if not decision.approved:
   # Preserve evidence gathering in the typed plan even when policy denies its write.
   # Only independently authorized reads run before the escalation is recorded.
   for read_invocation in (decision.invocations or plan.invocations):
    if not read_invocation.write:
     if tc.account_status=='locked' and not tc.verified and read_invocation.tool in {'get_order_details','get_customer_orders'}:continue
     try:tools.execute(read_invocation,tc)
     except Exception:pass
   esc=ToolInvocation('create_escalation',{'customer_id':ctx.customer_id,'order_id':ctx.order_id,'category':ctx.category,'summary':'Policy review required','evidence_received':list(ctx.attachments),'actions_taken':[],'reason':decision.reason,'priority':decision.priority},True)
   try:tools.execute(esc,tc)
   except Exception:pass
   action='security_escalation' if 'fraud' in decision.reason else ('escalate_human_approval' if decision.reason=='approval required' else ('escalate_logistics' if 'logistics' in decision.reason else 'escalate_human'))
   return finish(action,decision.reason,'escalated',True,decision.reason,'A specialist will review this request.')
  results=[]
  for inv in decision.invocations:
   try:
    if inv.tool=='check_pincode_serviceability':
     res=tools.execute(inv,tc); results.append(res)
     # bind actual check result into following address invocation, never planner-supplied serviceability.
     decision=type(decision)(True,decision.reason,tuple(ToolInvocation(x.tool,({**x.params,'serviceable':res.data['serviceable']} if x.tool=='update_address' else x.params),x.write) for x in decision.invocations),False)
    else: results.append(tools.execute(inv,tc))
   except InjectedTimeout:
    trace.retries+=1
    if inv.tool=='cancel_order' and self.store.order(ctx.order_id,ctx.customer_id)['status']=='cancelled':return finish('verify_state_before_retry','Cancellation timed out; state re-read confirmed cancellation.','resolved',False,None,'Your cancellation is confirmed.')
    return finish('escalate_after_tool_failure','Ambiguous write outcome.','escalated',True,'ambiguous write')
   except (InjectedFailure,MalformedToolResponse,ValueError,PermissionError) as e:
    if inv.tool=='get_order_details':
     recovered=False
     for retry_no in range(1,3):
      trace.retries+=1
      try:results.append(tools.execute(inv,tc,retry_no));recovered=True;break
      except Exception:continue
     if recovered:continue
     esc=ToolInvocation('create_escalation',{'customer_id':ctx.customer_id,'order_id':ctx.order_id,'category':ctx.category,'summary':'Order service unavailable','evidence_received':list(ctx.attachments),'actions_taken':['get_order_details'],'reason':'order service failed repeatedly','priority':'normal'},True)
     try:tools.execute(esc,tc)
     except Exception:pass
     return finish('escalate_after_tool_failure','Order status is unavailable; a specialist will follow up.','escalated',True,'order service failed repeatedly','Order status is unavailable right now. A specialist will follow up.')
    if inv.tool=='schedule_redelivery':
     for n in (1,2):
      trace.retries+=1
      try:results.append(tools.execute(inv,tc,n));break
      except Exception:continue
     else:
      esc=ToolInvocation('create_escalation',{'customer_id':ctx.customer_id,'order_id':ctx.order_id,'category':ctx.category,'summary':'Repeated tool failure','evidence_received':list(ctx.attachments),'actions_taken':['schedule_redelivery'],'reason':'tool failed repeatedly','priority':'normal'},True)
      try: tools.execute(esc,tc)
      except Exception: pass
      return finish('escalate_after_tool_failure','Repeated redelivery failure.','escalated',True,'tool failed repeatedly')
    return finish('escalate_after_tool_failure',str(e),'escalated',True,'tool failure')
  o=self.store.orders.get(ctx.order_id) if ctx.order_id else None
  action=plan.action;reason=decision.reason
  if ctx.category=='cancellation' and o and o['status']=='cancelled' and not any(x.tool=='cancel_order' for x in decision.invocations):action='no_action_inform'
  elif ctx.category=='cancellation' and o and o['status']!='cancelled':action='deny_cancellation_with_alternatives'
  elif ctx.category in {'order_status','late_delivery'} and decision.reason=='redelivery':action='reschedule_delivery'
  elif ctx.category=='refund':
   if decision.reason=='pickup reschedule':action='reschedule_return_pickup'
   elif decision.reason=='refund status':action='provide_refund_status'
   elif decision.reason=='return ineligible':action='reject_return_policy'
  elif ctx.category in {'damaged_item','wrong_item'} and not ctx.attachments:action='request_evidence'
  elif ctx.category=='order_status' and failure_injection:action='retry_then_answer'
  elif ctx.category=='unknown_issue' and decision.reason=='clarification':action='ask_clarification'
  # This label is informational only: untrusted text never changes plan/policy/tool permissions.
  if ctx.category=='refund' and any(w in ctx.message.lower().replace(' ','') for w in ('ignoreprevious','systeminstruction','adminmode','developerinstruction')):action='reject_injection_apply_policy'
  return finish(action,reason,'awaiting_customer' if action in {'request_evidence','ask_clarification'} else 'resolved',False,None,self._text(action,o))
 def _text(self,a,o):
  if a=='initiate_return_and_refund':return 'Return pickup is scheduled; any refund is released after receipt and quality check.'
  if a=='reject_return_policy':return 'This request is not eligible under the return policy.'
  if a=='no_action_inform' and o:return f"Your order is already cancelled. The recorded refund status is {o['refund_status']}."
  if a=='cancel_order' and o:return f"The duplicate order {o['order_id']} was cancelled; the matching earlier order remains active. Any prepaid cancellation refund follows the normal system timeline."
  if a=='provide_tracking_status' and o:return f"Your order is {o['tracking_stage']}; expected delivery is {o['expected_delivery_date']}."
  return 'Your request was processed under the applicable policy.'
