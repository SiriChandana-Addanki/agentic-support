import unittest
from pathlib import Path
from datetime import date
from support_agent.data import Store
from support_agent.retrieval import Retriever
from support_agent.tools import Tools
from support_agent.schemas import ToolContext,ToolInvocation,Trace
from support_agent.orchestrator import Orchestrator
ROOT=Path(__file__).parents[1]/'data'
def ctx(s,cid,oid):return ToolContext(cid,cid,'TX',oid,s.customer(cid)['account_status'],False,date(2026,10,1),'op-'+oid)
class Hardening(unittest.TestCase):
 def tool(self,s):return Tools(s,Retriever(ROOT/'business_rules.md'),Trace('r','t','now'))
 def test_return_tool_enforces_window_and_duplicate(self):
  s=Store(ROOT);t=self.tool(s)
  with self.assertRaises(PermissionError):t.execute(ToolInvocation('initiate_return',{},True),ctx(s,'C002','O003'))
  t.execute(ToolInvocation('initiate_return',{},True),ctx(s,'C001','O001'))
  with self.assertRaises(PermissionError):t.execute(ToolInvocation('initiate_return',{},True),ctx(s,'C001','O001'))
 def test_replacement_requires_evidence_and_stock(self):
  s=Store(ROOT);t=self.tool(s);c=ctx(s,'C006','O011')
  with self.assertRaises(PermissionError):t.execute(ToolInvocation('create_replacement',{'evidence':[],'in_stock':True},True),c)
  s.replacement_stock=False
  self.assertFalse(t.execute(ToolInvocation('check_replacement_stock',{},False),c).data['in_stock'])
  with self.assertRaises(PermissionError):t.execute(ToolInvocation('create_replacement',{'evidence':['a','b'],'in_stock':True},True),c)
 def test_locked_cannot_read_any_category(self):
  for cat in ['order_status','refund','cancellation','unknown_issue']:
   s=Store(ROOT);r,_=Orchestrator(s,Retriever(ROOT/'business_rules.md')).resolve({'ticket_id':'TX1','customer_id':'C007','category':cat,'order_id':'O013','message':'status','attachments':[]})
   self.assertTrue(r.escalation_required or r.action=='verify_identity')
   self.assertNotIn('get_order_details',[x['tool'] for x in r.tools_called])
 def test_address_serviceability_enforced(self):
  s=Store(ROOT);t=self.tool(s)
  with self.assertRaises(PermissionError):t.execute(ToolInvocation('update_address',{'address':{'pincode':'000000'},'serviceable':False},True),ctx(s,'C003','O006'))
 def test_planner_invalid_before_tools_and_fallback(self):
  s=Store(ROOT);t=s.tickets['T035'];r,tr=Orchestrator(s,Retriever(ROOT/'business_rules.md')).resolve(t,'planner_invalid_always')
  self.assertEqual(r.status,'escalated');self.assertEqual(tr.tool_calls,[]);self.assertEqual(tr.retries,2)
 def test_api_payload_is_not_fixture_replaced(self):
  from support_agent.api import App
  a=App(Path(__file__).parents[1]);r=a.submit({'ticket_id':'T001','customer_id':'C003','category':'address_change','order_id':'O006','message':'change to 400069','attachments':[]})
  self.assertEqual(r['intent'],'address_change')
 def test_evaluator_has_actual_state_check(self):
  from support_agent.evaluation import run
  row=run(ROOT,['T018'],1)['runs'][0];self.assertEqual(row['c7'],1)
 def test_evaluator_state_checks_are_generic_not_ticket_id_based(self):
  from support_agent.evaluation import _state
  from support_agent.schemas import Resolution,Trace
  s=Store(ROOT); trace=Trace('r','synthetic','now')
  t={'order_id':'O001','expected_action':'escalate_human'}
  resolution=Resolution('SYNTHETIC','refund','',[],[],'escalate_human','escalated',True,'review','review')
  self.assertFalse(_state(t,s,trace,resolution))
  s.escalations.append({'customer_id':'C001'})
  self.assertTrue(_state(t,s,trace,resolution))
 def test_evaluator_does_not_call_expected_malformed_read_a_parameter_bug(self):
  from support_agent.evaluation import run
  row=run(ROOT,['T034'],1)['runs'][0]
  self.assertEqual(row['c4'],1)
  self.assertEqual(row['actual_action'],'retry_then_answer')
 def test_evaluator_counts_successful_writes_not_failed_retries_as_duplicates(self):
  from support_agent.evaluation import run
  row=run(ROOT,['T036'],1)['runs'][0]
  self.assertEqual(row['safety'],1)
 def test_duplicate_cancel_only_accepts_later_processing_duplicate(self):
  s=Store(ROOT);t=self.tool(s);c=ctx(s,'C010','O018')
  with self.assertRaises(PermissionError):t.execute(ToolInvocation('cancel_order',{'duplicate':True},True),c)
  from support_agent.evaluation import run
  row=run(ROOT,['T018'],1)['runs'][0]
  self.assertEqual(row['success'],1)
  self.assertEqual(row['actual_final_state']['status'],'cancelled')
 def test_already_cancelled_flow_reads_status_and_does_not_write(self):
  from support_agent.evaluation import run
  row=run(ROOT,['T021'],1)['runs'][0]
  self.assertEqual(row['success'],1)
  self.assertFalse(any(x['write'] for x in row['tool_result']))
  self.assertEqual(row['actual_final_state']['refund_status'],'refunded')
