from __future__ import annotations
import re
from pathlib import Path
class Retriever:
    def __init__(self, rules_path): self.text=Path(rules_path).read_text()
    def search(self, query, injection=None):
        if injection == 'search_knowledge_base_returns_empty': return []
        terms=set(re.findall(r'[a-z]{4,}', query.lower()))
        chunks=[x.strip() for x in self.text.split('\n## ') if x.strip()]
        scored=sorted(((len(terms & set(re.findall(r'[a-z]{4,}',c.lower()))), c) for c in chunks), reverse=True)
        return [{'source':'business_rules.md','section':c.splitlines()[0][:80], 'score':s, 'excerpt':' '.join(c.split())[:300]} for s,c in scored[:2] if s]
