from .schemas import ActionPlan,ToolInvocation
class DeterministicPlanner:
 def propose(self,ctx,evidence,injector=None):
  if injector and injector.planner_invalid(): return {'bad':'plan'}
  c=ctx.category;o=ctx.order_id; read=ToolInvocation('get_order_details',{},False) if o else None
  inv=[] if not read else [read]
  if c=='account_locked': return ActionPlan(c,'verify_identity',(ToolInvocation('get_customer_profile',{},False),ToolInvocation('create_verification_link',{},True)),'Account verification route.')
  if c=='fraud_security':return ActionPlan(c,'security_escalation',(ToolInvocation('create_escalation',{},True),),'Security escalation route.')
  if c=='unknown_issue':return ActionPlan(c,'ask_clarification' if 'something' in ctx.message.lower() else 'escalate_human',tuple(inv),'Unknown request.')
  if c=='cancellation':return ActionPlan(c,'cancel_order',tuple(inv+[ToolInvocation('cancel_order',{},True)]),'Cancellation requested.')
  if c=='address_change':return ActionPlan(c,'update_address',tuple(inv+[ToolInvocation('check_pincode_serviceability',{'pincode':self._pin(ctx)},False),ToolInvocation('update_address',{'address':{'pincode':self._pin(ctx)},'serviceable':True},True)]),'Address requested.')
  if c=='payment_issue':return ActionPlan(c,'switch_cod_to_prepaid',tuple(inv+[ToolInvocation('create_payment_link',{},True)]),'Payment requested.')
  if c in {'damaged_item','wrong_item'}:return ActionPlan(c,'create_replacement' if ctx.attachments else 'request_evidence',tuple(inv+([ToolInvocation('check_replacement_stock',{},False),ToolInvocation('create_replacement',{'evidence':list(ctx.attachments),'in_stock':True},True)] if ctx.attachments else [])),'Item issue.')
  if c in {'order_status','late_delivery'}:return ActionPlan(c,'provide_tracking_status',tuple(inv),'Tracking requested.')
  if c=='refund':return ActionPlan(c,'initiate_return_and_refund',tuple(inv+[ToolInvocation('initiate_return',{},True)]),'Return requested.')
  return ActionPlan(c,'escalate_human',tuple(inv),'Safe fallback.')
 def _pin(self,ctx):
  import re
  return (re.findall(r'\b\d{6}\b',ctx.message) or ['000000'])[0]
