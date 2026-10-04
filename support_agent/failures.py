class InjectedFailure(Exception):pass
class InjectedTimeout(TimeoutError):pass
class FailureInjector:
 def __init__(self,mode=None):self.mode=mode;self.counts={}
 def before(self,tool):
  n=self.counts.get(tool,0)+1;self.counts[tool]=n
  if self.mode=='get_order_details_returns_503_on_every_call' and tool=='get_order_details':raise InjectedFailure('order service 503')
  if self.mode=='get_order_details_returns_malformed_json_on_first_call' and tool=='get_order_details' and n==1:return 'malformed'
  if self.mode=='schedule_redelivery_fails_3_consecutive_times' and tool=='schedule_redelivery' and n<=3:raise InjectedFailure('redelivery unavailable')
  if self.mode=='cancel_order_times_out_once_but_cancellation_succeeds_server_side' and tool=='cancel_order' and n==1:return 'timeout'
 def planner_invalid(self):
  n=self.counts.get('planner',0)+1;self.counts['planner']=n
  return self.mode in {'model_returns_invalid_JSON_for_first_planning_step','planner_invalid_always'} and (n==1 or self.mode=='planner_invalid_always')
