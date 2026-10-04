import json,os,re
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from .data import Store
from .retrieval import Retriever
from .orchestrator import Orchestrator
from .evaluation import run
from .planner import planner_from_env
MAX=32768
def validate(p):
 allowed={'ticket_id','customer_id','category','message','order_id','attachments','verified'};required={'ticket_id','customer_id','category','message'}
 if not isinstance(p,dict) or set(p)-allowed or not required<=set(p):raise ValueError('invalid request fields')
 if not all(isinstance(p[x],str) and len(p[x]) for x in required) or p['category'] not in __import__('support_agent.schemas',fromlist=['CATEGORIES']).CATEGORIES:raise ValueError('invalid field types')
 if len(p['message'])>5000 or not re.fullmatch(r'T[0-9A-Za-z_-]+',p['ticket_id']) or not re.fullmatch(r'C\d{3}',p['customer_id']):raise ValueError('invalid IDs or message')
 if p.get('order_id') is not None and not re.fullmatch(r'O\d{3}',p['order_id']):raise ValueError('invalid order id')
 if not isinstance(p.get('attachments',[]),list) or not all(isinstance(x,str) and len(x)<256 for x in p.get('attachments',[])):raise ValueError('invalid attachments')
 return p
class App:
 def __init__(self,root,planner=None):self.root=Path(root);self.store=Store(self.root/'data');self.retriever=Retriever(self.root/'data/business_rules.md');self.planner=planner or planner_from_env();self.resolutions={};self.traces={}
 @property
 def planner_type(self):return getattr(self.planner,'planner_type','deterministic')
 def submit(self,p):
  p=validate(p);r,t=Orchestrator(self.store,self.retriever,self.planner).resolve(p);self.resolutions[r.ticket_id]=r.to_dict();self.traces[r.ticket_id]=t.safe_dict();return self.resolutions[r.ticket_id]
def handler(app):
 class H(BaseHTTPRequestHandler):
  def sendj(self,s,o):
   b=json.dumps(o).encode();self.send_response(s);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
  def do_GET(self):
   if self.path=='/health':return self.sendj(200,{'status':'ok','development_only':True,'planner_type':app.planner_type})
   for prefix,data in [('/resolutions/',app.resolutions),('/observability/',app.traces)]:
    if self.path.startswith(prefix):
     k=self.path[len(prefix):];return self.sendj(200,data[k]) if k in data else self.sendj(404,{'error':'not found'})
   self.sendj(404,{'error':'not found'})
  def do_POST(self):
   if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.sendj(400,{'error':'content-type must be application/json'})
   try:
    n=int(self.headers.get('Content-Length','-1'))
    if n<0 or n>MAX:raise ValueError('invalid body size')
    p=json.loads(self.rfile.read(n))
    if self.path=='/tickets':return self.sendj(200,app.submit(p))
    if self.path=='/evaluations':return self.sendj(200,run(app.root/'data',p.get('ticket_ids'),p.get('repeats',1),planner_type=p.get('planner_type',app.planner_type)))
    self.sendj(404,{'error':'not found'})
   except json.JSONDecodeError:self.sendj(400,{'error':'malformed json'})
   except ValueError as e:self.sendj(422,{'error':str(e)})
   except Exception:self.sendj(500,{'error':'request could not be completed safely'})
  def log_message(self,*x):pass
 return H
def serve(root='.',host=None,port=None):ThreadingHTTPServer((host or os.getenv('SUPPORT_HOST','127.0.0.1'),int(port or os.getenv('SUPPORT_PORT','8000'))),handler(App(root))).serve_forever()
