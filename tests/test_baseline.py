import unittest
from pathlib import Path
from support_agent.data import Store
from support_agent.retrieval import Retriever
from support_agent.orchestrator import Orchestrator
ROOT=Path(__file__).parents[1]/'data'
def resolve(tid):
 s=Store(ROOT); t=s.tickets[tid]; return Orchestrator(s,Retriever(ROOT/'business_rules.md')).resolve(t,t['failure_injection'])
class BaselineTests(unittest.TestCase):
 def test_dataset_relationships(self):
  s=Store(ROOT)
  for t in s.tickets.values():
   if t['order_id']: self.assertEqual(s.order(t['order_id'],t['customer_id'])['customer_id'],t['customer_id'])
 def test_ticket_actions_and_safe_cases(self):
  for tid in ['T001','T002','T003','T004','T006','T007','T009','T011','T012','T013','T014','T015','T018','T020','T023','T024','T027','T028','T030','T037','T038']:
   r,_=resolve(tid); self.assertEqual(r.action,Store(ROOT).tickets[tid]['expected_action'],tid); r.validate()
 def test_timeout_rereads_instead_of_duplicate_cancel(self):
  r,t=resolve('T033'); self.assertEqual(r.action,'verify_state_before_retry'); self.assertEqual([x['tool'] for x in t.tool_calls].count('cancel_order'),1)
 def test_failure_and_malformed_retries(self):
  for tid in ['T031','T034','T036']:
   r,t=resolve(tid); self.assertGreaterEqual(t.retries,1); self.assertIn(r.status,{'resolved','escalated'})
 def test_locked_order_is_not_read(self):
  _,t=resolve('T013'); self.assertNotIn('get_order_details',[x['tool'] for x in t.tool_calls])
 def test_no_internal_note_in_resolution(self):
  r,_=resolve('T029'); self.assertNotIn('data_note',str(r.to_dict()))
 def test_ownership_protection(self):
  s=Store(ROOT)
  with self.assertRaises(PermissionError): s.order('O001','C002')
