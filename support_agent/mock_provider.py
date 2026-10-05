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
  packet=json.loads(input_json)['ticket_and_planning_context'];data=packet['ticket'];state=packet['trusted_state'];order=state.get('selected_order') or {};message=data['message'].lower();oid=data['order_id'];category=data['category_hint'];attachments=data['attachment_names']
  if any(x in message for x in ('where is my parcel','track my order','where is my order','delivery status')) and not any(x in message for x in ('return','refund')):category='order_status'
  def call(tool,params=None,write=False):return {'tool':tool,'params':params or {},'write':write}
  def escalation(intent,reason,priority='normal'):
   return call('create_escalation',{'customer_id':data['customer_id'],'order_id':oid,'category':intent,'summary':'Specialist review requested','evidence_received':attachments,'actions_taken':[],'reason':reason,'priority':priority},True)
  if any(x in message for x in ('someone asked me for my otp','card details','phishing','asked for otp')):
   intent,action='fraud_security','security_escalation';tools=[escalation(intent,'fraud risk','high')]
  elif category=='account_locked' or any(x in message for x in ('account got locked','unlock','wrong password','otp')):
   intent,action='account_locked','verify_identity';tools=[call('get_customer_profile')]
   if any(x in message for x in ('abroad','old number','lost phone','cannot receive')):intent,action='account_locked','escalate_human';tools=[escalation(intent,'identity verification unavailable')]
   else:tools.append(call('create_verification_link',write=True))
  elif category=='refund' or any(x in message for x in ('refund','return','give my money')):
   intent='refund';days=None
   try:days=(__import__('datetime').date.fromisoformat(data['request_date'])-__import__('datetime').date.fromisoformat(order['delivery_date'])).days
   except (ValueError,TypeError,KeyError):pass
   status_question=any(x in message for x in ('status','where is','still waiting','delay')) and (order.get('status')=='cancelled' or order.get('refund_status') in {'refund_pending','refund_issued'})
   if order.get('status')=='returned' and order.get('refund_status')=='refund_pending':action,tools='escalate_human',[escalation(intent,'refund SLA breach')]
   elif status_question:intent,action,tools='refund','provide_refund_status',[call('get_order_details')]
   elif state.get('account_status')=='suspended':action='escalate_human';tools=[escalation(intent,'suspended account review')]
   elif float(order.get('amount','0') or 0)>5000:action='escalate_human_approval';tools=[call('get_order_details'),escalation(intent,'return exceeds automatic amount limit','high')]
   elif order.get('status')=='delivered' and order.get('is_returnable')=='yes' and days is not None and 0<=days<=10 and state.get('account_status')=='active' and not order.get('return_requested_date'):
    action='initiate_return_and_refund';tools=[call('get_order_details'),call('initiate_return',write=True)]
   elif order and (days is None or days>10 or order.get('is_returnable')=='no'):
    action='reject_return_policy';tools=[call('get_order_details'),call('search_knowledge_base',{'query':'return eligibility policy'})]
   else:action='initiate_return_and_refund';tools=[call('get_order_details')]
  elif category in {'damaged_item','wrong_item'} or any(x in message for x in ('damaged','wrong item','sound quality')):
   intent=category if category in {'damaged_item','wrong_item'} else 'damaged_item'
   if not attachments:intent,action,tools=intent,'request_evidence',[call('get_order_details')]
   elif state.get('account_status')=='suspended':action,tools='escalate_human',[escalation(intent,'suspended account review')]
   elif len(attachments)<2:action,tools='request_evidence',[call('get_order_details')]
   elif not state.get('replacement_stock') and float(order.get('amount','0') or 0)<=5000:action,tools='initiate_return_and_refund',[call('get_order_details'),call('initiate_return',write=True)]
   else:action,tools='create_replacement',[call('get_order_details'),call('check_replacement_stock'),call('create_replacement',{'evidence':attachments,'in_stock':bool(state.get('replacement_stock'))},True)]
  elif category=='cancellation' or any(x in message for x in ('cancel','stop the order','do not want')):
   intent='cancellation'
   if any(x in message for x in ('twice','same order','duplicate')):tools=[call('get_customer_orders')]
   else:tools=[]
   if order.get('status')=='cancelled':action='no_action_inform';tools.append(call('get_order_details'))
   elif order.get('status')=='processing':action='cancel_order';tools.extend([call('get_order_details'),call('cancel_order',{'duplicate':any(x in message for x in ('twice','same order','duplicate'))},True)])
   else:action='deny_cancellation_with_alternatives';tools.extend([call('get_order_details'),call('search_knowledge_base',{'query':'cancellation alternatives policy'})])
  elif category in {'order_status','late_delivery'} or any(x in message for x in ('where','track','delivery','arrive','reach')):
   intent='order_status' if category=='order_status' else category;action,tools='provide_tracking_status',[call('get_order_details')]
  else:intent,action,tools=category or 'unknown_issue','ask_clarification',[]
  return intent,action,tools
