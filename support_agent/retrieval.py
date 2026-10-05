import re
from pathlib import Path
from .schemas import RetrievedEvidence
class Retriever:
 def __init__(self,rules_path):
  self.text=Path(rules_path).read_text(encoding='utf-8');self.version='2026-10-01';self.chunks=[]
  for n,raw in enumerate(re.split(r'(?m)^## ',self.text)):
   raw=raw.strip()
   if not raw:continue
   title,_,body=raw.partition('\n');title=title.strip().lstrip('#').strip()
   rule_id=re.sub(r'[^a-z0-9]+','_',title.lower()).strip('_') or f'rule_{n}'
   rule_id=re.sub(r'^\d+_','',rule_id)
   self.chunks.append((n,rule_id,title,body.strip()))
 def search(self,query,injection=None):
  if injection=='search_knowledge_base_returns_empty': return []
  terms=set(re.findall(r'[a-z]{3,}',query.lower()));scored=[]
  for n,rule_id,title,body in self.chunks:
   text=f'{title} {body}';score=len(terms & set(re.findall(r'[a-z]{3,}',text.lower())))
   if score:scored.append((score,n,rule_id,title,body))
  evidence=[]
  for rank,(score,n,rule_id,title,body) in enumerate(sorted(scored,key=lambda x:(x[0],-x[1]),reverse=True)[:5],1):
   excerpt=self._relevant_excerpt(body,terms)
   evidence.append(RetrievedEvidence('business_rules','section_'+str(n),'chunk_'+str(n),self.version,rank,score,query,excerpt,rule_id,title))
  return evidence
 @staticmethod
 def _relevant_excerpt(body,terms):
  lines=[re.sub(r'\s+',' ',line).strip(' |') for line in body.splitlines() if line.strip()]
  scored=[]
  for index,line in enumerate(lines):
   words=set(re.findall(r'[a-z]{3,}',line.lower()));score=len(words&terms)
   if score:scored.append((score,-index,line))
  picked=[line for _,_,line in sorted(scored,reverse=True)[:5]]
  if not picked:picked=[' '.join(body.split())]
  text=' | '.join(picked)
  return text[:900]
