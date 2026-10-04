from __future__ import annotations
from dataclasses import dataclass,field,asdict
from typing import Any
from datetime import date
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
 principal_id:str; customer_id:str; ticket_id:str; order_id:str|None; account_status:str; verified:bool; request_date:date; idempotency_key:str
@dataclass(frozen=True)
class ToolInvocation:
 tool:str; params:dict[str,Any]; write:bool=False
 def validate(self):
  allowed={'get_customer_profile','get_customer_orders','get_order_details','search_knowledge_base','check_pincode_serviceability','check_replacement_stock','cancel_order','update_address','create_payment_link','initiate_return','create_replacement','schedule_redelivery','schedule_return_pickup','create_verification_link','create_escalation','update_ticket'}
  if self.tool not in allowed or self.tool=='create_refund': raise ValueError('unknown or forbidden tool')
@dataclass(frozen=True)
class ActionPlan:
 intent:str; action:str; invocations:tuple[ToolInvocation,...]; summary:str
 def validate(self,ctx):
  if self.intent not in CATEGORIES or self.action not in ACTIONS: raise ValueError('invalid action plan')
  for i in self.invocations: i.validate()
  if any(i.tool=='create_refund' for i in self.invocations): raise ValueError('direct refunds forbidden')
@dataclass(frozen=True)
class PolicyDecision:
 approved:bool; reason:str; invocations:tuple[ToolInvocation,...]; escalation:bool=False; priority:str='normal'
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
 def validate(self):
  if not self.ticket_id or self.intent not in CATEGORIES or self.action not in ACTIONS or self.status not in {'resolved','escalated','awaiting_customer','failed'}: raise ValueError('invalid resolution')
  if self.escalation_required != (self.status=='escalated'): raise ValueError('escalation mismatch')
 def to_dict(self): self.validate(); return asdict(self)
@dataclass
class Trace:
 request_id:str; ticket_id:str; timestamp:str; model:str='deterministic-planner-v2'; tool_calls:list[dict[str,Any]]=field(default_factory=list); retrieval:list[dict[str,Any]]=field(default_factory=list); retries:int=0; fallback:bool=False; escalation:bool=False; errors:list[dict[str,str]]=field(default_factory=list); latency_ms:float=0; final_status:str=''; final_action:str=''
 def safe_dict(self):
  # Customer message, emails, full addresses, secrets and raw tool output are never stored here.
  return asdict(self)
