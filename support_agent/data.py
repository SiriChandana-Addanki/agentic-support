from __future__ import annotations
import csv, json
from pathlib import Path
from copy import deepcopy

PRIVATE_ORDER_FIELDS = {'data_note'}
class Store:
    def __init__(self, root: str | Path):
        root=Path(root); self.root=root
        with (root/'customers.csv').open() as f: self.customers={r['customer_id']:r for r in csv.DictReader(f)}
        with (root/'orders.csv').open() as f: self._original={r['order_id']:r for r in csv.DictReader(f)}
        self.orders=deepcopy(self._original)
        with (root/'tickets.json').open() as f: self.tickets={t['ticket_id']:t for t in json.load(f)}
        self.escalations=[]; self.ticket_updates=[]
    def fresh(self): return Store(self.root)
    def customer(self, cid): return self.customers.get(cid)
    def order(self, oid, cid):
        o=self.orders.get(oid)
        if not o or o['customer_id'] != cid: raise PermissionError('order is not owned by ticket customer')
        return o
    def public_order(self,o): return {k:v for k,v in o.items() if k not in PRIVATE_ORDER_FIELDS}
    def customer_orders(self,cid): return [self.public_order(o) for o in self.orders.values() if o['customer_id']==cid]
