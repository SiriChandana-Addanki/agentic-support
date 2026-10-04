import re
from pathlib import Path
from .schemas import RetrievedEvidence
class Retriever:
 def __init__(self,rules_path): self.text=Path(rules_path).read_text(); self.version='2026-10-01'; self.chunks=[x.strip() for x in self.text.split('\n## ') if x.strip()]
 def search(self,query,injection=None):
  if injection=='search_knowledge_base_returns_empty': return []
  terms=set(re.findall(r'[a-z]{3,}',query.lower())); scored=[]
  for n,c in enumerate(self.chunks):
   score=len(terms & set(re.findall(r'[a-z]{3,}',c.lower())))
   if score: scored.append((score,n,c))
  return [RetrievedEvidence('business_rules','section_'+str(n),'chunk_'+str(n),self.version,rank,score,query,' '.join(c.split())[:320]) for rank,(score,n,c) in enumerate(sorted(scored,reverse=True)[:3],1)]
