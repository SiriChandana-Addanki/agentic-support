from __future__ import annotations
from dataclasses import dataclass,field,asdict
from typing import Any,Protocol
from datetime import date
import re
ACTIONS={'provide_tracking_status','initiate_return_and_refund','provide_refund_status','reject_return_policy','cancel_order','deny_cancellation_with_alternatives','update_address','switch_cod_to_prepaid','request_evidence','create_replacement','reschedule_delivery','reschedule_return_pickup','verify_identity','ask_clarification','no_action_inform','escalate_human','escalate_human_approval','escalate_logistics','security_escalation','reject_injection_apply_policy','escalate_after_tool_failure','verify_state_before_retry','retry_then_answer'}
CATEGORIES={'refund','cancellation','late_delivery','address_change','payment_issue','wrong_item','damaged_item','account_locked','fraud_security','order_status','unknown_issue'}
@dataclass(frozen=True)
class RetrievedEvidence:
 document_id:str; section_id:str; chunk_id:str; rule_version:str; rank:int; score:int; query:str; excerpt:str
@dataclass(frozen=True)
class TicketContext:
 ticket_id:str; customer_id:str; category:str; message:str; order_id:str|None; attachments:tuple[str,...]=(); request_date:date=date(2026,10,1); verified:bool=False
@dataclass(frozen=True)
class ToolContext:
 principal_id:str; customer_id:str; ticket_id:str; order_id:str|None; account_status:str; verified:bool; request_date:date; idempotency_key:str; attachments:tuple[str,...]=()
@dataclass(frozen=True)
class ToolInvocation:
 tool:str; params:dict[str,Any]; write:bool=False
 def validate(self):
  reads={'get_customer_profile','get_customer_orders','get_order_details','search_knowledge_base','check_pincode_serviceability','check_replacement_stock'}
  writes={'cancel_order','update_address','create_payment_link','initiate_return','create_replacement','schedule_redelivery','schedule_return_pickup','create_verification_link','create_escalation','update_ticket'}
  schemas={
   'get_customer_profile':(set(),set()),'get_customer_orders':(set(),set()),'get_order_details':(set(),set()),
   'search_knowledge_base':({'query'},{'query'}),'check_pincode_serviceability':({'pincode'},{'pincode'}),
   'check_replacement_stock':(set(),set()),'cancel_order':(set(),{'duplicate'}),'update_address':({'address'},{'address','serviceable'}),
   'create_payment_link':(set(),set()),'initiate_return':(set(),set()),
   'create_replacement':({'evidence','in_stock'},{'evidence','in_stock'}),
   'schedule_redelivery':({'requested_date'},{'requested_date'}),'schedule_return_pickup':(set(),set()),
   'create_verification_link':(set(),set()),
   'create_escalation':({'customer_id','order_id','category','summary','evidence_received','actions_taken','reason','priority'}, {'customer_id','order_id','category','summary','evidence_received','actions_taken','reason','priority'}),
   'update_ticket':(set(),set())}
  if self.tool not in reads|writes:raise ValueError('unknown or forbidden tool')
  if not isinstance(self.params,dict):raise ValueError('tool parameters must be an object')
  required,allowed=self._schema(schemas,self.tool)
  if set(self.params)-allowed or required-set(self.params):raise ValueError('invalid tool parameters')
  if self.write!=(self.tool in writes):raise ValueError('tool write mode mismatch')
  p=self.params
  if self.tool=='search_knowledge_base' and (not isinstance(p['query'],str) or not p['query'].strip() or len(p['query'])>2000):raise ValueError('invalid search query')
  if self.tool=='check_pincode_serviceability' and (not isinstance(p['pincode'],str) or not re.fullmatch(r'\d{6}',p['pincode'])):raise ValueError('invalid pincode')
  if self.tool=='cancel_order' and 'duplicate' in p and not isinstance(p['duplicate'],bool):raise ValueError('invalid duplicate flag')
  if self.tool=='update_address':
   a=p['address']
   if not isinstance(a,dict) or set(a)!={'pincode'} or not isinstance(a['pincode'],str) or not re.fullmatch(r'\d{6}',a['pincode']):raise ValueError('invalid address fields')
   if 'serviceable' in p and not isinstance(p['serviceable'],bool):raise ValueError('invalid serviceability flag')
  if self.tool=='create_replacement' and (not isinstance(p['evidence'],list) or not all(isinstance(x,str) and 0<len(x)<256 for x in p['evidence']) or not isinstance(p['in_stock'],bool)):raise ValueError('invalid replacement evidence or stock')
  if self.tool=='schedule_redelivery':
   if not isinstance(p['requested_date'],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',p['requested_date']):raise ValueError('invalid redelivery date')
  if self.tool=='create_escalation':
   if not all(isinstance(p[k],str) and len(p[k])<500 for k in ('customer_id','category','summary','reason')) or (p['order_id'] is not None and not isinstance(p['order_id'],str)):raise ValueError('invalid escalation fields')
   if not isinstance(p['priority'],str) or p['priority'] not in {'normal','high'} or not isinstance(p['evidence_received'],list) or len(p['evidence_received'])>10 or not all(isinstance(x,str) and len(x)<256 for x in p['evidence_received']) or not isinstance(p['actions_taken'],list) or len(p['actions_taken'])>10 or not all(isinstance(x,str) and len(x)<120 for x in p['actions_taken']):raise ValueError('invalid escalation fields')
 @staticmethod
 def _schema(schemas,tool):return schemas[tool]
@dataclass(frozen=True)
class ActionPlan:
 intent:str; action:str; invocations:tuple[ToolInvocation,...]; summary:str
 def validate(self,ctx):
  if self.intent not in CATEGORIES or self.action not in ACTIONS or not isinstance(self.invocations,tuple) or not isinstance(self.summary,str) or len(self.summary)>240: raise ValueError('invalid action plan')
  if re.search(r'(https?://|\b(?:curl|wget|powershell|cmd\.exe|subprocess|os\.system|select\s+.+\s+from|drop\s+table)\b|(?:\.\./|[A-Za-z]:\\))',self.summary,re.I):raise ValueError('unsafe planner summary')
  for i in self.invocations: i.validate()
  if any(i.tool=='create_refund' for i in self.invocations): raise ValueError('direct refunds forbidden')
  tools=[i.tool for i in self.invocations]
  if len([i.tool for i in self.invocations if i.write])!=len(set(i.tool for i in self.invocations if i.write)):raise ValueError('duplicate write proposal')
  compatible={'cancel_order':{'cancellation'},'update_address':{'address_change'},'create_payment_link':{'payment_issue'},'initiate_return':{'refund','damaged_item','wrong_item'},'create_replacement':{'damaged_item','wrong_item'},'schedule_redelivery':{'late_delivery','order_status'},'schedule_return_pickup':{'refund'},'create_verification_link':{'account_locked'}}
  for tool, intents in compatible.items():
   if tool in tools and self.intent not in intents:raise ValueError('unsupported intent/tool combination')
  action_for_tool={'cancel_order':{'cancel_order'},'update_address':{'update_address'},'create_payment_link':{'switch_cod_to_prepaid'},'initiate_return':{'initiate_return_and_refund'},'create_replacement':{'create_replacement'},'schedule_redelivery':{'provide_tracking_status','reschedule_delivery'},'schedule_return_pickup':{'reschedule_return_pickup'},'create_verification_link':{'verify_identity'},'create_escalation':{'escalate_human','escalate_human_approval','escalate_logistics','security_escalation','escalate_after_tool_failure'}}
  for invocation in self.invocations:
   if invocation.tool=='update_ticket':raise ValueError('unsupported planner tool')
   if invocation.tool in action_for_tool and self.action not in action_for_tool[invocation.tool]:raise ValueError('unsupported action/tool combination')
   if invocation.tool=='create_replacement' and sorted(invocation.params['evidence'])!=sorted(ctx.attachments):raise ValueError('replacement evidence reference mismatch')
  if self.action in {'escalate_human','escalate_human_approval','escalate_logistics','security_escalation','escalate_after_tool_failure'} and 'create_escalation' not in tools:raise ValueError('escalation proposal must include escalation request')
  for invocation in self.invocations:
   if invocation.tool=='create_escalation':
    p=invocation.params
    if p['customer_id']!=ctx.customer_id or p['order_id']!=ctx.order_id or p['category']!=self.intent or not set(p['evidence_received']).issubset(set(ctx.attachments)):raise ValueError('escalation context mismatch')

class Planner(Protocol):
 def plan(self,context:TicketContext,evidence:list[RetrievedEvidence],injector:Any=None)->ActionPlan:...
@dataclass(frozen=True)
class PolicyDecision:
 approved:bool; reason:str; invocations:tuple[ToolInvocation,...]; escalation:bool=False; priority:str='normal'; authorized_action:str|None=None
@dataclass(frozen=True)
class EscalationRequest:
 customer_id:str; order_id:str|None; category:str; summary:str; evidence_received:tuple[str,...]; actions_taken:tuple[str,...]; reason:str; priority:str
 def validate(self):
  if not self.customer_id or not self.category or not self.summary or not self.reason or self.priority not in {'normal','high'}: raise ValueError('invalid escalation')
@dataclass
class ToolResult:
 tool:str; ok:bool; data:dict[str,Any]=field(default_factory=dict); error:str|None=None; transition:dict[str,Any]=field(default_factory=dict)
@dataclass
class Resolution:
 ticket_id:str; intent:str; reasoning_summary:str; evidence:list[dict[str,Any]]; tools_called:list[dict[str,Any]]; action:str; status:str; escalation_required:bool; escalation_reason:str|None; final_response:str
 planner_type:str='deterministic'; proposed_action:str|None=None; policy_decision:str|None=None
 def validate(self):
  if not self.ticket_id or self.intent not in CATEGORIES or self.action not in ACTIONS or self.status not in {'resolved','escalated','awaiting_customer','failed'}: raise ValueError('invalid resolution')
  if self.escalation_required != (self.status=='escalated'): raise ValueError('escalation mismatch')
 def to_dict(self): self.validate(); return asdict(self)
@dataclass
class Trace:
 request_id:str; ticket_id:str; timestamp:str; model:str='deterministic-planner-v2'; tool_calls:list[dict[str,Any]]=field(default_factory=list); retrieval:list[dict[str,Any]]=field(default_factory=list); retries:int=0; fallback:bool=False; escalation:bool=False; errors:list[dict[str,str]]=field(default_factory=list); latency_ms:float=0; final_status:str=''; final_action:str=''
 planner_type:str='deterministic'; provider:str|None=None; planner_model:str|None=None; planner_request_id:str|None=None; planner_latency_ms:float=0; planner_attempts:int=0; planner_validation:str='not_run'; planner_retries:int=0; planner_error_type:str|None=None; proposed_action:str|None=None; proposed_tools:list[str]=field(default_factory=list); approved_action:str|None=None; policy_decision:str|None=None; policy_approved:bool|None=None; input_tokens:int|None=None; output_tokens:int|None=None; estimated_cost_usd:float|None=None
 def safe_dict(self):
  # Customer message, emails, full addresses, secrets and raw tool output are never stored here.
  return asdict(self)
