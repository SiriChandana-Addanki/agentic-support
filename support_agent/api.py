from __future__ import annotations
import json,os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .data import Store
from .retrieval import Retriever
from .orchestrator import Orchestrator
from .evaluation import run
class App:
 def __init__(self,root): self.root=Path(root); self.store=Store(self.root/'data'); self.retriever=Retriever(self.root/'data/business_rules.md'); self.resolutions={}; self.traces={}
 def submit(self,payload):
  required={'ticket_id','customer_id','message'}
  if not required <= payload.keys(): raise ValueError('ticket_id, customer_id, and message are required')
  ticket=self.store.tickets.get(payload['ticket_id'],payload)
  # Dataset-declared faults are used for known evaluation tickets; callers may
  # explicitly inject faults only for a custom evaluation submission.
  injection=payload.get('failure_injection', ticket.get('failure_injection'))
  r,t=Orchestrator(self.store,self.retriever).resolve(ticket,injection)
  self.resolutions[r.ticket_id]=r.to_dict(); self.traces[r.ticket_id]=t.safe_dict(); return self.resolutions[r.ticket_id]
def handler(app):
 class H(BaseHTTPRequestHandler):
  def _send(self,status,obj):
   body=json.dumps(obj).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
  def do_GET(self):
   if self.path=='/health': return self._send(200,{'status':'ok'})
   if self.path.startswith('/resolutions/'):
    tid=self.path.rsplit('/',1)[1]; return self._send(200,app.resolutions.get(tid,{'error':'not found'}) if tid in app.resolutions else {'error':'not found'})
   if self.path.startswith('/observability/'):
    tid=self.path.rsplit('/',1)[1]; return self._send(200,app.traces.get(tid,{'error':'not found'}))
   self._send(404,{'error':'not found'})
  def do_POST(self):
   try:
    data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
    if self.path=='/tickets': return self._send(200,app.submit(data))
    if self.path=='/evaluations': return self._send(200,run(app.root/'data',data.get('ticket_ids'),data.get('repeats',1)))
    self._send(404,{'error':'not found'})
   except (ValueError,json.JSONDecodeError) as e: self._send(400,{'error':str(e)})
   except Exception: self._send(500,{'error':'request could not be completed safely'})
  def log_message(self,*args): pass
 return H
def serve(root='.',host=None,port=None):
 a=App(root); httpd=ThreadingHTTPServer((host or os.getenv('SUPPORT_HOST','127.0.0.1'),int(port or os.getenv('SUPPORT_PORT','8000'))),handler(a)); httpd.serve_forever()
