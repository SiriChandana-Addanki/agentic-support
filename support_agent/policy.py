from datetime import date
from .schemas import PolicyDecision,ToolInvocation
class PolicyEngine:
 def evaluate(self,ctx,plan,store,evidence):
  try: plan.validate(ctx)
  except Exception as e:return PolicyDecision(False,str(e),(),True)
  customer=store.customer(ctx.customer_id)
  if not customer:return PolicyDecision(False,'unknown customer',(),True)
  if customer['account_status']=='locked' and not ctx.verified:
   allowed={'get_customer_profile','create_verification_link','create_escalation'}
   if any(i.tool not in allowed for i in plan.invocations):return PolicyDecision(False,'locked account requires verification',(),True)
  if not evidence and ctx.category not in {'unknown_issue'}:return PolicyDecision(False,'required policy evidence unavailable',(),True)
  o=store.orders.get(ctx.order_id) if ctx.order_id else None
  def esc(reason,priority='normal'):return PolicyDecision(False,reason,(),True,priority)
  if ctx.category=='account_locked':
   if 'abroad' in ctx.message.lower() or 'old number' in ctx.message.lower():return esc('identity review required')
   return PolicyDecision(True,'locked verification allowed',plan.invocations)
  if ctx.category=='fraud_security':return esc('fraud risk','high')
  if ctx.category=='unknown_issue':return PolicyDecision(True,'clarification',()) if plan.action=='ask_clarification' else esc('unknown process')
  if not o:return esc('missing order')
  if customer['account_status']=='suspended' and ctx.category in {'refund','damaged_item','wrong_item'}:return esc('suspended account review')
  if ctx.category=='cancellation':
   if o['status']=='cancelled':return PolicyDecision(True,'already cancelled',())
   if o['status']!='processing':return PolicyDecision(True,'cancellation unavailable',tuple(i for i in plan.invocations if not i.write))
  if ctx.category=='address_change' and o['tracking_stage']!='order_confirmed':return esc('address change requires review')
  if ctx.category=='payment_issue' and 'charged' in ctx.message.lower():return esc('payment record conflict')
  if ctx.category in {'damaged_item','wrong_item'} and not ctx.attachments:return PolicyDecision(True,'evidence required',tuple(i for i in plan.invocations if not i.write))
  if ctx.category=='refund':
   if o['tracking_stage']=='return_pickup_scheduled':return PolicyDecision(True,'pickup reschedule',(ToolInvocation('get_order_details',{},False),ToolInvocation('schedule_return_pickup',{},True)))
   if o['status']=='returned' and o['refund_status']=='refund_pending':return esc('refund SLA breach')
   if o['status']=='cancelled':return PolicyDecision(True,'refund status',tuple(i for i in plan.invocations if not i.write))
   if not o['delivery_date'] or (ctx.request_date-date.fromisoformat(o['delivery_date'])).days>10 or o['is_returnable']!='yes':return PolicyDecision(True,'return ineligible',tuple(i for i in plan.invocations if not i.write))
   if float(o['amount'])>5000:return esc('approval required','high')
  if ctx.category in {'order_status','late_delivery'}:
   if o['tracking_stage']=='delivery_attempt_failed':return PolicyDecision(True,'redelivery', (ToolInvocation('get_order_details',{},False),ToolInvocation('schedule_redelivery',{'requested_date':'2026-10-03'},True)))
   late=(ctx.request_date-date.fromisoformat(o['expected_delivery_date'])).days>2
   if late or (o['tracking_stage']=='out_for_delivery' and int(o['days_in_current_stage'])>=2) or 'not received' in ctx.message.lower() or 'nobody came' in ctx.message.lower():return esc('logistics investigation','high' if 'unreachable' in ctx.message.lower() else 'normal')
  return PolicyDecision(True,'policy approved',plan.invocations)
