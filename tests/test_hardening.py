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
  with self.assertRaises(PermissionError):t.execute(ToolInvocation('create_replacement',{'evidence':['a','b'],'in_stock':False},True),c)
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
