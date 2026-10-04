from .schemas import ActionPlan,ToolInvocation
from contextvars import ContextVar
from .providers import provider_from_env
from .llm_planner import LLMPlanner
class DeterministicPlanner:
 planner_type='deterministic'
 def plan(self,ctx,evidence,injector=None):
  raw=self.propose(ctx,evidence,injector)
  if not isinstance(raw,ActionPlan):return raw
  raw.validate(ctx);return raw
 def propose(self,ctx,evidence,injector=None):
  if injector and injector.planner_invalid(): return {'bad':'plan'}
  c=ctx.category;o=ctx.order_id; read=ToolInvocation('get_order_details',{},False) if o else None
  inv=[] if not read else [read]
  kb=ToolInvocation('search_knowledge_base',{'query':ctx.message},False)
  if c=='account_locked': return ActionPlan(c,'verify_identity',(ToolInvocation('get_customer_profile',{},False),ToolInvocation('create_verification_link',{},True)),'Account verification route.')
  if c=='fraud_security':return ActionPlan(c,'security_escalation',(ToolInvocation('create_escalation',{'customer_id':ctx.customer_id,'order_id':o,'category':c,'summary':'Security concern reported','evidence_received':list(ctx.attachments),'actions_taken':[],'reason':'fraud risk','priority':'high'},True),),'Security escalation route.')
  if c=='unknown_issue':
   unclear='something' in ctx.message.lower()
   plan_inv=inv+[ToolInvocation('get_customer_profile',{},False),kb]
   if not unclear:plan_inv.append(self._escalation(ctx,c,'unknown process'))
   return ActionPlan(c,'ask_clarification' if unclear else 'escalate_human',tuple(plan_inv),'Unknown request.')
  if c=='cancellation':
   duplicate=any(w in ctx.message.lower() for w in ('twice','same order','duplicate'))
   reads=inv+([ToolInvocation('get_customer_orders',{},False)] if duplicate else [])+[kb]
   return ActionPlan(c,'cancel_order',tuple(reads+[ToolInvocation('cancel_order',{'duplicate':duplicate},True)]),'Cancellation requested.')
  if c=='address_change':return ActionPlan(c,'update_address',tuple(inv+[ToolInvocation('check_pincode_serviceability',{'pincode':self._pin(ctx)},False),ToolInvocation('update_address',{'address':{'pincode':self._pin(ctx)},'serviceable':True},True)]),'Address requested.')
  if c=='payment_issue':return ActionPlan(c,'switch_cod_to_prepaid',tuple(inv+[ToolInvocation('create_payment_link',{},True)]),'Payment requested.')
  if c in {'damaged_item','wrong_item'}:return ActionPlan(c,'create_replacement' if ctx.attachments else 'request_evidence',tuple(inv+([ToolInvocation('check_replacement_stock',{},False),ToolInvocation('create_replacement',{'evidence':list(ctx.attachments),'in_stock':True},True)] if ctx.attachments else [])),'Item issue.')
  if c in {'order_status','late_delivery'}:return ActionPlan(c,'provide_tracking_status',tuple(inv),'Tracking requested.')
  if c=='refund':return ActionPlan(c,'initiate_return_and_refund',tuple(inv+[kb,ToolInvocation('initiate_return',{},True)]),'Return requested.')
  return ActionPlan(c,'escalate_human',tuple(inv),'Safe fallback.')
 def _escalation(self,ctx,category,reason,priority='normal'):
  return ToolInvocation('create_escalation',{'customer_id':ctx.customer_id,'order_id':ctx.order_id,'category':category,'summary':'Specialist review requested','evidence_received':list(ctx.attachments),'actions_taken':[],'reason':reason,'priority':priority},True)
 def _pin(self,ctx):
  import re
  return (re.findall(r'\b\d{6}\b',ctx.message) or ['000000'])[0]

class ShadowPlanner:
 planner_type='shadow'
 def __init__(self,deterministic,llm=None):self.deterministic=deterministic;self.llm=llm;self._observation=ContextVar('shadow_observation_'+str(id(self)),default={})
 def observation(self):return dict(self._observation.get())
 def plan(self,ctx,evidence,injector=None):
  authoritative=self.deterministic.plan(ctx,evidence,injector);obs={'planner_type':'shadow','provider':None,'validation':'not_run','authoritative_action':authoritative.action,'difference':None}
  if self.llm:
   try:
    proposal=self.llm.plan(ctx,evidence);obs.update(self.llm.observation());obs.update(planner_type='shadow',authoritative_action=authoritative.action,difference=proposal.action!=authoritative.action)
   except Exception as e:obs.update(validation='invalid_or_unavailable',error_type=type(e).__name__)
  else:obs.update(validation='llm_not_configured',error_type='ProviderUnavailable')
  self._observation.set(obs);return authoritative

def planner_from_env(kind=None,provider_override=None):
 import os
 kind=(kind or os.getenv('PLANNER_TYPE','deterministic')).strip().lower()
 if kind not in {'deterministic','llm','shadow'}:raise ValueError('PLANNER_TYPE must be deterministic, llm, or shadow')
 deterministic=DeterministicPlanner()
 if kind=='deterministic':return deterministic
 provider=provider_override or provider_from_env()
 if kind=='llm':
  if provider is None:raise ValueError('PLANNER_TYPE=llm requires OPENAI_API_KEY')
  return LLMPlanner(provider)
 return ShadowPlanner(deterministic,LLMPlanner(provider) if provider else None)
