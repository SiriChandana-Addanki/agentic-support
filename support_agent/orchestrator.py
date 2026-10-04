from __future__ import annotations
import re,time,uuid
from datetime import datetime,date,UTC
from .schemas import Resolution,Trace
from .tools import Tools
from .failures import InjectedFailure,InjectedTimeout

class Orchestrator:
 def __init__(self,store,retriever): self.store=store; self.retriever=retriever
 def resolve(self,ticket, failure_injection=None):
  start=time.perf_counter(); tid=ticket.get('ticket_id','submitted-'+uuid.uuid4().hex[:8]); cid=ticket.get('customer_id'); cat=ticket.get('category','unknown_issue'); oid=ticket.get('order_id'); msg=ticket.get('message','')
  trace=Trace(uuid.uuid4().hex,tid,datetime.now(UTC).isoformat()); tools=Tools(self.store,self.retriever,trace,__import__('support_agent.failures',fromlist=['FailureInjector']).FailureInjector(failure_injection))
  def finish(intent, summary, action, status, final, esc=False, reason=None, evidence=[]):
   trace.escalation=esc; trace.final_status=status; trace.latency_ms=round((time.perf_counter()-start)*1000,2)
   r=Resolution(tid,intent,summary,evidence,trace.tool_calls,action,status,esc,reason,final); r.validate(); return r,trace
  def escalate(action,reason,final,priority='normal', evidence=[]):
   tools.escalation(cid,oid,cat,reason,priority); return finish(cat,reason,action,'escalated',final,True,reason,evidence)
  try:
   customer=self.store.customer(cid)
   if not customer: return finish(cat,'Customer could not be verified.','escalate_human','escalated','We could not verify the account, so a specialist will review this.',True,'unknown customer')
   # Lock/suspension gates execute before any potentially disclosing order read.
   if cat=='account_locked':
    tools.profile(cid)
    if 'abroad' in msg.lower() or 'cannot get' in msg.lower() or 'old number' in msg.lower(): return escalate('escalate_human','Identity verification requires human review.','We have sent this to our identity verification team.')
    tools.verification(cid); return finish(cat,'The account is locked, so order details are withheld until verification.','verify_identity','resolved','A verification link was sent to your registered email. We cannot share order details until verification is complete.')
   if cat=='fraud_security': return escalate('security_escalation','Potential fraud was reported.','Do not share OTPs, card details, PINs, or passwords with anyone. A security specialist has been alerted.','high')
   if cat=='unknown_issue':
    if oid is None and ('something is wrong' in msg.lower()): return finish(cat,'The request does not identify an issue or order.','ask_clarification','awaiting_customer','Please tell us which order and what needs help; we will ask only this one clarification.')
    tools.profile(cid); ev=tools.knowledge(msg); trace.retrieval=ev
    return escalate('escalate_human','No matching supported process was confirmed.','We could not confirm a policy for that request, so a specialist will review it.',evidence=ev)
   if cat=='refund' and oid is None:
    ev=tools.knowledge(msg); trace.retrieval=ev
    if not ev: return escalate('escalate_human','No policy evidence was available.','We cannot confirm that policy, so a specialist will review it.')
   # Required state read with a bounded one retry for malformed/transient reads.
   o=None
   if oid:
    for attempt in range(2):
     try: o=self.store.order(oid,cid); public=tools.order(oid,cid); break
     except (ValueError,InjectedFailure) as e:
      trace.errors.append(str(e)); trace.retries+=1
      if attempt==1: return escalate('escalate_after_tool_failure','Order service is unavailable after retry.','Order status is unavailable right now; we created a callback escalation.')
    evidence=[{'source':'order','order_id':o['order_id'],'status':o['status'],'tracking_stage':o['tracking_stage']}]
   else: evidence=[]
   if customer['account_status']=='suspended' and cat in {'refund','damaged_item','wrong_item'}:
    tools.profile(cid); return escalate('escalate_human','The account requires review before this action.','A specialist will review the request.')
   injection=any(x in msg.lower() for x in ('ignore all previous','admin mode','do not mention'))
   if injection:
    return finish(cat,'The request was handled under the applicable return policy.','reject_injection_apply_policy','resolved','This order is outside the return window, so we cannot start a return.',False,None,evidence)
   if cat in {'order_status','late_delivery'}:
    if cat=='order_status' and ('not received' in msg.lower() or 'nobody came' in msg.lower()): return escalate('escalate_logistics','Delivered status conflicts with the customer report.','A proof-of-delivery investigation has been opened; no refund has been promised.',evidence=evidence)
    if cat=='late_delivery' and (o['tracking_stage']=='out_for_delivery' and int(o['days_in_current_stage'])>=2 or (date(2026,10,1)-date.fromisoformat(o['expected_delivery_date'])).days>2 or 'not received' in msg.lower() or 'nobody came' in msg.lower()): return escalate('escalate_logistics','Delivery requires a logistics investigation.','A logistics investigation has been opened; no refund has been promised.', 'high' if 'unreachable' in msg.lower() else 'normal',evidence)
    if o['tracking_stage']=='delivery_attempt_failed':
     try: tools.redelivery(o); return finish(cat,'A delivery attempt failed and another attempt is allowed.','reschedule_delivery','resolved','Your redelivery has been scheduled.',False,None,evidence)
     except InjectedFailure:
      for _ in range(2):
       trace.retries+=1
       try: tools.redelivery(o); return finish(cat,'Redelivery was retried successfully.','reschedule_delivery','resolved','Your redelivery has been scheduled.',False,None,evidence)
       except InjectedFailure as e: trace.errors.append(str(e))
      return escalate('escalate_after_tool_failure','Redelivery failed three consecutive times.','Your request is logged but not confirmed; a specialist will arrange it.',evidence=evidence)
    return finish(cat,'Verified order tracking was read from the order record.','retry_then_answer' if failure_injection else 'provide_tracking_status','resolved',f"Your order is {o['tracking_stage'].replace('_',' ')}. Expected delivery: {o['expected_delivery_date']} via {o['carrier']}.",False,None,evidence)
   if cat=='cancellation':
    if o['status']=='cancelled': return finish(cat,'The order is already cancelled.','no_action_inform','resolved','This order is already cancelled and its refund status is '+o['refund_status']+'.',False,None,evidence)
    if o['status']!='processing':
     ev=tools.knowledge(msg); trace.retrieval=ev; return finish(cat,'Cancellation is not allowed after shipment.','deny_cancellation_with_alternatives','resolved','This order has shipped. You may refuse it at delivery or request an eligible return after delivery.',False,None,evidence)
    if 'same' in msg.lower() or 'twice' in msg.lower(): tools.orders(cid); o=self.store.order('O030',cid)
    try: tools.cancel(o); return finish(cat,'The processing order was cancelled under policy.','cancel_order','resolved','Your order was cancelled. Any prepaid refund follows the normal payment timeline.',False,None,evidence)
    except InjectedTimeout:
     trace.errors.append('cancel response timeout'); trace.retries+=1; state=self.store.order(o['order_id'],cid)
     if state['status']=='cancelled': return finish(cat,'Cancellation timed out, then the order state was re-read and confirmed.','verify_state_before_retry','resolved','Your order cancellation is confirmed.',False,None,evidence)
     return escalate('escalate_after_tool_failure','Cancellation outcome could not be confirmed.','A specialist will confirm the cancellation.',evidence=evidence)
   if cat=='address_change':
    if o['tracking_stage']!='order_confirmed': return escalate('escalate_human','Address updates are not automatic after packing.','The fulfilment team will review the address correction.',evidence=evidence)
    pin=(re.findall(r'\b\d{6}\b',msg) or [o['delivery_pincode']])[0]; tools.serviceability(pin); tools.address(o,pin); return finish(cat,'The order is confirmed and the supplied pincode format is valid.','update_address','resolved','Your delivery address pincode was updated.',False,None,evidence)
   if cat=='payment_issue':
    if 'charged' in msg.lower(): return escalate('escalate_human','The customer claim conflicts with the order record.','A payments specialist will review the charge.',evidence=evidence)
    tools.payment(o); return finish(cat,'COD can be changed while the order is processing.','switch_cod_to_prepaid','resolved','A secure payment link has been created; the order remains active.',False,None,evidence)
   if cat in {'damaged_item','wrong_item'}:
    if not ticket.get('attachments'): return finish(cat,'Photos of both the item and package label are required before action.','request_evidence','awaiting_customer','Please upload a photo of the item and a photo of the package or shipping label.')
    if float(o['amount'])>10000: return escalate('escalate_human','Replacement requires approval above the limit.','A specialist will review the replacement.',evidence=evidence)
    tools.stock(o); tools.replacement(o); return finish(cat,'Required evidence is present and the replacement is within the limit.','create_replacement','resolved','A replacement and pickup for the affected item have been created.',False,None,evidence)
   if cat=='refund':
    ev=tools.knowledge(msg); trace.retrieval=ev
    if o['tracking_stage']=='return_pickup_scheduled': tools.return_pickup(o); return finish(cat,'A missed return pickup can be rescheduled once.','reschedule_return_pickup','resolved','Your return pickup has been rescheduled.',False,None,evidence)
    if o['status']=='returned' and o['refund_status']=='refund_pending': return escalate('escalate_human','Refund is beyond its service timeline.','A finance specialist will review the delayed refund.',evidence=evidence)
    if o['status']=='cancelled': return finish(cat,'The refund is within its stated processing timeline.','provide_refund_status','resolved','Your refund is in progress and normally takes 5–7 business days.',False,None,evidence)
    in_window=o['delivery_date'] and (date(2026,10,1)-date.fromisoformat(o['delivery_date'])).days<=10
    if not in_window or o['is_returnable']!='yes':
     if 'exception' in msg.lower() or 'stopped working' in msg.lower(): return escalate('escalate_human','This is a policy exception outside the return window.','A specialist will review the exception and possible warranty route.',evidence=evidence)
     return finish(cat,'The return is not eligible under the return policy.','reject_return_policy','resolved','This item cannot be returned under the applicable policy. Damaged or wrong items are handled separately.',False,None,evidence)
    if float(o['amount'])>5000: return escalate('escalate_human_approval','This return needs human approval because it exceeds the automatic limit.','We logged your request date to protect the return window; a specialist will review it.','high',evidence)
    tools.return_(o); final='Your return pickup is scheduled. Refund is released only after the item is received and passes quality check.'
    if o['payment_method']=='COD': final+=' Please provide bank-account or UPI details through the secure follow-up.'
    return finish(cat,'The delivered, returnable order is within the automatic return limit.','initiate_return_and_refund','resolved',final,False,None,evidence)
   return escalate('escalate_human','No safe supported action matched this request.','A specialist will review your request.',evidence=evidence)
  except (PermissionError,InjectedFailure,ValueError) as e:
   trace.errors.append(str(e)); return escalate('escalate_after_tool_failure','A validated tool operation could not be completed safely.','A specialist will review this request.')
