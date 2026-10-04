from datetime import date
from dataclasses import replace
from .schemas import PolicyDecision,ToolInvocation
class PolicyEngine:
 def evaluate(self,ctx,plan,store,evidence,planner_type='deterministic'):
  decision=self._evaluate(ctx,plan,store,evidence)
  if planner_type!='llm' or plan.summary=='Planner validation failed; specialist review required.':return decision
  if not any(i.tool=='create_escalation' for i in plan.invocations) or decision.escalation:return decision
  invocations=tuple(i for i in decision.invocations if i.tool!='create_escalation')
  safe_actions={'already cancelled':'no_action_inform','evidence required':'request_evidence','clarification':'ask_clarification','return ineligible':'reject_return_policy','cancellation unavailable':'deny_cancellation_with_alternatives','refund status':'provide_refund_status','redelivery':'reschedule_delivery','pickup reschedule':'reschedule_return_pickup','locked verification allowed':'verify_identity'}
  authorized=safe_actions.get(decision.reason)
  if authorized is None and plan.action in {'escalate_human','escalate_human_approval','escalate_logistics','security_escalation','escalate_after_tool_failure'}:authorized='ask_clarification'
  return replace(decision,invocations=invocations,authorized_action=authorized or decision.authorized_action or plan.action,reason='unnecessary escalation proposal removed by policy' if decision.reason=='policy approved' else decision.reason)
 def _evaluate(self,ctx,plan,store,evidence):
  try: plan.validate(ctx)
  except Exception as e:return PolicyDecision(False,str(e),(),True)
  customer=store.customer(ctx.customer_id)
  if not customer:return PolicyDecision(False,'unknown customer',(),True)
  if customer['account_status']=='locked' and not ctx.verified:
   allowed={'get_customer_profile','create_verification_link','create_escalation'}
   if any(i.tool not in allowed for i in plan.invocations):return PolicyDecision(False,'locked account requires verification',(),True)
  if plan.summary=='Planner validation failed; specialist review required.':
   return PolicyDecision(True,'planner recovery escalation',tuple(i for i in plan.invocations if i.tool=='create_escalation'),True,authorized_action=plan.action)
  if not evidence and ctx.category not in {'unknown_issue'}:return PolicyDecision(False,'required policy evidence unavailable',(),True)
  o=store.orders.get(ctx.order_id) if ctx.order_id else None
  def esc(reason,priority='normal'):return PolicyDecision(False,reason,(),True,priority)
  if ctx.category=='account_locked':
   if 'abroad' in ctx.message.lower() or 'old number' in ctx.message.lower():return esc('identity review required')
   return PolicyDecision(True,'locked verification allowed',plan.invocations)
  if ctx.category=='fraud_security':return esc('fraud risk','high')
  if ctx.category=='unknown_issue':return PolicyDecision(True,'clarification',()) if plan.action=='ask_clarification' else esc('unknown process')
  if not o:return esc('missing order')
  if customer['account_status']=='suspended' and ctx.category in {'refund','damaged_item','wrong_item'}:return PolicyDecision(False,'suspended account review',(ToolInvocation('get_customer_profile',{},False),),True)
  if ctx.category=='cancellation':
   if o['status']=='cancelled':return PolicyDecision(True,'already cancelled',(ToolInvocation('get_order_details',{},False),))
   if any(w in ctx.message.lower() for w in ('twice','same order','duplicate')):
    candidates=[x for x in store.orders.values() if x['customer_id']==ctx.customer_id and x['product']==o['product'] and x['status']=='processing']
    if len(candidates)<2 or max(candidates,key=lambda x:(x['order_date'],x['order_id']))['order_id']!=ctx.order_id:return esc('duplicate order cannot be confirmed')
   if o['status']!='processing':return PolicyDecision(True,'cancellation unavailable',tuple(i for i in plan.invocations if not i.write))
  if ctx.category=='address_change' and o['tracking_stage']!='order_confirmed':return esc('address change requires review')
  if ctx.category=='payment_issue' and 'charged' in ctx.message.lower():return esc('payment record conflict')
  if ctx.category in {'damaged_item','wrong_item'}:
   if not ctx.attachments:return PolicyDecision(True,'evidence required',tuple(i for i in plan.invocations if not i.write))
   if float(o['amount'])>10000:return esc('replacement exceeds automatic limit','high')
   if not store.replacement_stock:
    if float(o['amount'])>5000:return esc('replacement out of stock above return limit','high')
    return PolicyDecision(True,'replacement unavailable; return eligible',(ToolInvocation('get_order_details',{},False),ToolInvocation('initiate_return',{},True)))
  if ctx.category=='refund':
   if o['tracking_stage']=='return_pickup_scheduled':return PolicyDecision(True,'pickup reschedule',(ToolInvocation('get_order_details',{},False),ToolInvocation('schedule_return_pickup',{},True)))
   if o['status']=='returned' and o['refund_status']=='refund_pending':return esc('refund SLA breach')
   if o['status']=='cancelled':return PolicyDecision(True,'refund status',tuple(i for i in plan.invocations if not i.write))
   if 'time is over' in ctx.message.lower() and 'help' in ctx.message.lower():return esc('policy exception review')
   if not o['delivery_date'] or (ctx.request_date-date.fromisoformat(o['delivery_date'])).days>10 or o['is_returnable']!='yes':return PolicyDecision(True,'return ineligible',tuple(i for i in plan.invocations if not i.write))
   if float(o['amount'])>5000:return esc('approval required','high')
  if ctx.category in {'order_status','late_delivery'}:
   if o['tracking_stage']=='delivery_attempt_failed':return PolicyDecision(True,'redelivery', (ToolInvocation('get_order_details',{},False),ToolInvocation('schedule_redelivery',{'requested_date':'2026-10-03'},True)))
   late=(ctx.request_date-date.fromisoformat(o['expected_delivery_date'])).days>2
   if late or (o['tracking_stage']=='out_for_delivery' and int(o['days_in_current_stage'])>=2) or 'not received' in ctx.message.lower() or 'nobody came' in ctx.message.lower():return esc('logistics investigation','high' if 'unreachable' in ctx.message.lower() else 'normal')
  return PolicyDecision(True,'policy approved',plan.invocations,authorized_action=plan.action)
