from __future__ import annotations
import statistics
from .data import Store
from .retrieval import Retriever
from .orchestrator import Orchestrator
ALIASES={'create_payment_link':'send_payment_link','update_address':'update_delivery_address','create_verification_link':'send_verification_link','schedule_redelivery':'schedule_redelivery','initiate_return':'initiate_return'}
def run(root, ticket_ids=None, repeats=1):
 base=Store(root); ids=ticket_ids or list(base.tickets); rows=[]
 for tid in ids:
  ticket=base.tickets[tid]
  for run_id in range(1,repeats+1):
   store=base.fresh(); resolution,trace=Orchestrator(store,Retriever(store.root/'business_rules.md')).resolve(ticket,ticket.get('failure_injection'))
   names=[ALIASES.get(x['tool'],x['tool']) for x in trace.tool_calls]; expected=ticket['expected_tools']
   action=resolution.action==ticket['expected_action']; tools=all(x in names for x in expected)
   escalation=resolution.escalation_required==ticket['requires_human']
   success=action and tools and escalation and resolution.status!='failed'
   rows.append({'ticket_id':tid,'run_id':run_id,'success':int(success),'expected_action':ticket['expected_action'],'actual_action':resolution.action,'expected_tools':expected,'actual_tools':names,'escalation_correct':escalation,'tool_errors':trace.errors,'retries':trace.retries,'fallback_used':trace.fallback,'latency_ms':trace.latency_ms,'cost_usd':None,'notes':'' if success else 'action, tools, or escalation mismatch'})
 return {'runs':rows,'summary':{'total':len(rows),'passed':sum(x['success'] for x in rows),'success_rate':sum(x['success'] for x in rows)/len(rows) if rows else 0,'p50_latency_ms':statistics.median([x['latency_ms'] for x in rows]) if rows else 0}}
