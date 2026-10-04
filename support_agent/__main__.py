import argparse
import json
from pathlib import Path
from .api import serve
from .evaluation import run,planner_comparison
def main():
 p=argparse.ArgumentParser(); p.add_argument('command',choices=['serve','evaluate','compare']); p.add_argument('--ticket',action='append'); p.add_argument('--repeats',type=int,default=1);p.add_argument('--planner-type',choices=['deterministic','llm','shadow']); args=p.parse_args()
 if args.command=='serve': serve()
 elif args.command=='evaluate':print(json.dumps(run('data',args.ticket,args.repeats,args.planner_type or 'deterministic'),indent=2))
 else:
  result=planner_comparison('data',args.repeats);Path('reports/planner_comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__': main()
