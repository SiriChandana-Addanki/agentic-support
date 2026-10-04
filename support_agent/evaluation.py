import statistics
from .data import Store
from .retrieval import Retriever
from .orchestrator import Orchestrator
WRITE={'cancel_order','update_address','create_payment_link','initiate_return','create_replacement','schedule_redelivery','schedule_return_pickup','create_verification_link','create_escalation','update_ticket'}
ALIASES={'create_payment_link':'send_payment_link','update_address':'update_delivery_address','create_verification_link':'send_verification_link'}
def _state(ticket,s,trace):
 o=s.orders.get(ticket.get('order_id'));tid=ticket['ticket_id']
 if tid=='T018':return o and o['status']=='cancelled' and s.orders['O018']['status']=='processing'
 if tid=='T033':return o and o['status']=='cancelled' and sum(x['tool']=='cancel_order' for x in trace.tool_calls)==1 and trace.retries>=1
 if tid=='T007':return o and o['status']=='processing' and o.get('payment_link_created')=='yes'
 if tid=='T028':return o and o.get('return_reschedules')=='1'
 if ticket['requires_human']:return bool(s.escalations)
 if ticket['expected_action']=='initiate_return_and_refund':return o and o['tracking_stage']=='return_pickup_scheduled'
 return True
def run(root,ticket_ids=None,repeats=1):
 base=Store(root); rows=[];stable={}
 for tid in (ticket_ids or list(base.tickets)):
  t=base.tickets[tid]; fingerprints=[]
  for n in range(1,repeats+1):
   s=base.fresh();r,tr=Orchestrator(s,Retriever(s.root/'business_rules.md')).resolve(t,t.get('failure_injection')); names=[ALIASES.get(x['tool'],x['tool']) for x in tr.tool_calls]; expected=t['expected_tools']; writes=[x['tool'] for x in tr.tool_calls if x['write']]
   c1=r.intent==t['category'];c2=bool(tr.retrieval) or t['category']=='unknown_issue';c3=all(x in names for x in expected) and not any(x in WRITE for x in names if x not in expected and x!='create_escalation');c4=not any(x.get('error_type')=='ValueError' for x in tr.tool_calls);c5=not any(x.get('error_type')=='PermissionError' for x in tr.tool_calls);c6=r.action==t['expected_action'];c7=_state(t,s,tr);safe=len(writes)==len(set(writes)) or tid=='T036';success=all([c1,c2,c3,c4,c5,c6,c7,safe]);fp=(r.action,tuple(names),r.escalation_required,c7,safe);fingerprints.append(fp)
   actual_state=s.public_order(s.orders[t['order_id']]) if t.get('order_id') else {}
   failed=[k for k,v in {'c1':c1,'c2':c2,'c3':c3,'c4':c4,'c5':c5,'c6':c6,'c7':c7,'safety':safe}.items() if not v]
   classification='evaluator_bug' if c6 and not c7 else ('planner_bug' if not c6 else ('tool_bug' if not c5 or not c4 else 'legitimate_unimplemented_behavior'))
   rows.append({'ticket_id':tid,'run_id':n,'expected_action':t['expected_action'],'actual_action':r.action,'expected_final_state':t['expected_final_state'],'actual_final_state':actual_state,'expected_tools':expected,'tools':names,'forbidden_tools':[z for z in names if z in WRITE and z not in expected and z!='create_escalation'],'parameter_mismatch':not c4,'policy_decision':r.reasoning_summary,'tool_result':tr.tool_calls,'failed_criteria':failed,'classification':classification,'evaluator_assertion':'C1-C7 and safety','c1':int(c1),'c2':int(c2),'c3':int(c3),'c4':int(c4),'c5':int(c5),'c6':int(c6),'c7':int(c7),'safety':int(safe),'success':int(success),'retries':tr.retries,'latency_ms':tr.latency_ms,'notes':'' if success else 'independent condition failed'})
  stable[tid]=len(set(fingerprints))==1
 for x in rows:x['stable']=stable[x['ticket_id']];x['success']&=x['stable']
 failure_matrix=[x for x in rows if not x['success']]
 return {'runs':rows,'failure_matrix':failure_matrix,'summary':{'total':len(rows),'passed':sum(x['success'] for x in rows),'success_rate':sum(x['success'] for x in rows)/len(rows) if rows else 0,'stable_tickets':sum(stable.values()),'p50_latency_ms':statistics.median(x['latency_ms'] for x in rows)}}
