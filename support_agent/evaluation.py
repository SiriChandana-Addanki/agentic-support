import statistics,json
from .data import Store
from .retrieval import Retriever
from .orchestrator import Orchestrator
WRITE={'cancel_order','update_address','create_payment_link','initiate_return','create_replacement','schedule_redelivery','schedule_return_pickup','create_verification_link','create_escalation','update_ticket'}
ALIASES={'create_payment_link':'send_payment_link','update_address':'update_delivery_address','create_verification_link':'send_verification_link'}
def _state(ticket,s,trace,resolution):
 """Check reusable state invariants from action and recorded state, never fixture IDs."""
 o=s.orders.get(ticket.get('order_id'))
 action=resolution.action
 if action in {'escalate_human','escalate_human_approval','escalate_logistics','security_escalation','escalate_after_tool_failure'}:
  return bool(s.escalations) and resolution.status=='escalated'
 if action=='cancel_order':return o is not None and o['status']=='cancelled' and sum(x['tool']=='cancel_order' and x['status']=='ok' for x in trace.tool_calls)==1
 if action=='verify_state_before_retry':return o is not None and o['status']=='cancelled' and sum(x['tool']=='cancel_order' for x in trace.tool_calls)==1 and trace.retries>=1
 if action=='switch_cod_to_prepaid':return o is not None and o['status']=='processing' and o.get('payment_link_created')=='yes'
 if action=='reschedule_return_pickup':return o is not None and o.get('return_reschedules')=='1'
 if action=='initiate_return_and_refund':return o is not None and o['tracking_stage']=='return_pickup_scheduled' and o['refund_status']!='issued'
 if action=='create_replacement':return o is not None and o.get('replacement_created')=='yes'
 if action=='update_address':return o is not None and any(x['tool']=='update_address' and x['status']=='ok' for x in trace.tool_calls)
 if action=='reschedule_delivery':return o is not None and bool(o.get('redelivery_date'))
 unchanged=not o or s.public_order(o)==s.public_order(s._original[o['order_id']])
 if action in {'reject_return_policy','deny_cancellation_with_alternatives','provide_tracking_status','provide_refund_status','no_action_inform','ask_clarification','request_evidence'}:
  return unchanged and not any(x['write'] for x in trace.tool_calls if x['tool']!='create_escalation')
 if action=='verify_identity':
  return resolution.status in {'resolved','escalated'} and not any(x['tool'] in {'get_order_details','get_customer_orders'} for x in trace.tool_calls)
 if action=='retry_then_answer':
  return any(x['tool']=='get_order_details' and x.get('status')=='ok' for x in trace.tool_calls)
 if action=='escalate_after_tool_failure':return bool(s.escalations) and resolution.status=='escalated'
 return unchanged
def run(root,ticket_ids=None,repeats=1):
 base=Store(root); rows=[];stable={}
 for tid in (ticket_ids or list(base.tickets)):
  t=base.tickets[tid]; fingerprints=[]
  for n in range(1,repeats+1):
   s=base.fresh();r,tr=Orchestrator(s,Retriever(s.root/'business_rules.md')).resolve(t,t.get('failure_injection')); names=[ALIASES.get(x['tool'],x['tool']) for x in tr.tool_calls]; expected=t['expected_tools']; writes=[x['tool'] for x in tr.tool_calls if x['write']]
   c1=r.intent==t['category'];c2=bool(tr.retrieval) or 'search_knowledge_base' in names or t['category']=='unknown_issue';c3=all(x in names for x in expected) and not any(x in WRITE for x in names if x not in expected and x!='create_escalation');c4=not any(x.get('error_type') in {'ParameterError','TypeError','ValueError'} for x in tr.tool_calls);c5=not any(x.get('error_type')=='PermissionError' for x in tr.tool_calls);c6=r.action==t['expected_action'];c7=_state(t,s,tr,r);successful_writes=[x['tool'] for x in tr.tool_calls if x['write'] and x.get('status')=='ok'];safe=len(successful_writes)==len(set(successful_writes));success=all([c1,c2,c3,c4,c5,c6,c7,safe]);actual_state=s.public_order(s.orders[t['order_id']]) if t.get('order_id') else {};fp=(r.action,tuple(names),r.escalation_required,c7,safe,json.dumps(actual_state,sort_keys=True),r.status);fingerprints.append(fp)
   actual_state=s.public_order(s.orders[t['order_id']]) if t.get('order_id') else {}
   failed=[k for k,v in {'c1':c1,'c2':c2,'c3':c3,'c4':c4,'c5':c5,'c6':c6,'c7':c7,'safety':safe}.items() if not v]
   classification='planner_bug' if not c6 else ('tool_bug' if not c5 or not c4 else 'legitimate_unimplemented_behavior')
   rows.append({'ticket_id':tid,'run_id':n,'expected_action':t['expected_action'],'actual_action':r.action,'expected_final_state':t['expected_final_state'],'actual_final_state':actual_state,'expected_tools':expected,'tools':names,'forbidden_tools':[z for z in names if z in WRITE and z not in expected and z!='create_escalation'],'parameter_mismatch':not c4,'policy_decision':r.reasoning_summary,'tool_result':tr.tool_calls,'failed_criteria':failed,'classification':classification,'evaluator_assertion':'C1-C7 and safety','c1':int(c1),'c2':int(c2),'c3':int(c3),'c4':int(c4),'c5':int(c5),'c6':int(c6),'c7':int(c7),'safety':int(safe),'success':int(success),'retries':tr.retries,'latency_ms':tr.latency_ms,'notes':'' if success else 'independent condition failed'})
  stable[tid]=len(set(fingerprints))==1
 for x in rows:x['stable']=stable[x['ticket_id']];x['success']&=x['stable']
 failure_matrix=[x for x in rows if not x['success']]
 return {'runs':rows,'failure_matrix':failure_matrix,'summary':{'total':len(rows),'passed':sum(x['success'] for x in rows),'success_rate':sum(x['success'] for x in rows)/len(rows) if rows else 0,'stable_tickets':sum(stable.values()),'p50_latency_ms':statistics.median(x['latency_ms'] for x in rows)}}
