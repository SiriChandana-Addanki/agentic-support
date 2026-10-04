import csv,json
from pathlib import Path
from copy import deepcopy
PRIVATE_ORDER_FIELDS={'data_note'}
class Store:
 def __init__(self,root):
  self.root=Path(root)
  with (self.root/'customers.csv').open() as f:self.customers={x['customer_id']:x for x in csv.DictReader(f)}
  with (self.root/'orders.csv').open() as f:self._original={x['order_id']:x for x in csv.DictReader(f)}
  self.orders=deepcopy(self._original)
  with (self.root/'tickets.json').open() as f:self.tickets={x['ticket_id']:x for x in json.load(f)}
  self.operations={};self.escalations=[];self.ticket_updates=[];self.replacement_stock=True
 def fresh(self):return Store(self.root)
 def customer(self,cid):return self.customers.get(cid)
 def order(self,oid,cid):
  o=self.orders.get(oid)
  if not o or o['customer_id']!=cid:raise PermissionError('order ownership denied')
  return o
 def public_order(self,o):return {k:v for k,v in o.items() if k not in PRIVATE_ORDER_FIELDS}
