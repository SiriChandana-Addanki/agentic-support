"""Deterministic, network-free provider double used by LLM planner tests."""
from __future__ import annotations
import json
from collections import deque
from .providers import ProviderResponse,ProviderTimeout,ProviderError

class MockLLMProvider:
 provider_name='mock';model='mock-planner-v1'
 def __init__(self,scenario='valid',responses=None):self.scenario=scenario;self.responses=deque(responses or []);self.calls=[]
 def generate_structured_plan(self,*,system_prompt,input_json,schema):
  self.calls.append({'system_prompt':system_prompt,'input_json':input_json,'schema':schema})
  if self.responses:
   response=self.responses.popleft()
   if isinstance(response,Exception):raise response
   content=response if isinstance(response,str) else json.dumps(response)
   return ProviderResponse(content,self.provider_name,self.model,'mock-request',100,30)
  if self.scenario=='timeout':raise ProviderTimeout('mock provider timeout')
  if self.scenario=='provider_error':raise ProviderError('mock provider error')
  if self.scenario=='malformed_json':content='{not-json'
  else:
   intent,action,invocations=self._valid_plan(input_json)
   payload={'intent':intent,'action':action,'invocations':invocations,'summary':'Mock proposal.'}
   if self.scenario=='schema_invalid':payload.pop('summary')
   elif self.scenario=='unknown_tool':payload['invocations']=[{'tool':'shell_exec','params':{'cmd':'echo nope'},'write':True}]
   elif self.scenario=='direct_refund':payload['invocations']=[{'tool':'create_refund','params':{'amount':1},'write':True}]
   elif self.scenario=='prompt_injection':payload['invocations']=[{'tool':'create_refund','params':{'amount':9999},'write':True}]
   elif self.scenario in {'unauthorized_order','wrong_order'}:payload['invocations']=[{'tool':'get_order_details','params':{'order_id':'O999'},'write':False}]
   elif self.scenario=='missing_parameter':payload['invocations']=[{'tool':'search_knowledge_base','params':{},'write':False}]
   content=json.dumps(payload)
  return ProviderResponse(content,self.provider_name,self.model,'mock-request',100,30)
 @staticmethod
 def _valid_plan(input_json):
  data=json.loads(input_json)['untrusted_ticket_and_evidence']['ticket'];message=data['message'].lower();oid=data['order_id']
  if any(x in message for x in ('account got locked','unlock','wrong password','otp')):
   intent,action='account_locked','verify_identity';tools=[{'tool':'get_customer_profile','params':{},'write':False},{'tool':'create_verification_link','params':{},'write':True}]
  elif any(x in message for x in ('someone asked me for my otp','card details','phishing')):
   intent,action='fraud_security','security_escalation';tools=[{'tool':'create_escalation','params':{'customer_id':data['customer_id'],'order_id':oid,'category':intent,'summary':'Security concern reported','evidence_received':data['attachment_names'],'actions_taken':[],'reason':'fraud risk','priority':'high'},'write':True}]
  elif any(x in message for x in ('cancel','stop the order','do not want')):
   intent,action='cancellation','cancel_order';tools=([{'tool':'get_order_details','params':{},'write':False}] if oid else [])+[{'tool':'cancel_order','params':{},'write':True}]
  elif any(x in message for x in ('refund','return','give my money')):
   intent,action='refund','initiate_return_and_refund';tools=([{'tool':'get_order_details','params':{},'write':False}] if oid else [])+[{'tool':'initiate_return','params':{},'write':True}]
  elif any(x in message for x in ('where','track','delivery','arrive','reach')):
   intent,action='order_status','provide_tracking_status';tools=[{'tool':'get_order_details','params':{},'write':False}] if oid else []
  else:intent,action,tools='unknown_issue','ask_clarification',[]
  return intent,action,tools
