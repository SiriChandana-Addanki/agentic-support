import argparse
from .api import serve
from .evaluation import run
def main():
 p=argparse.ArgumentParser(); p.add_argument('command',choices=['serve','evaluate']); p.add_argument('--ticket',action='append'); p.add_argument('--repeats',type=int,default=1); args=p.parse_args()
 if args.command=='serve': serve()
 else: import json; print(json.dumps(run('data',args.ticket,args.repeats),indent=2))
if __name__=='__main__': main()
