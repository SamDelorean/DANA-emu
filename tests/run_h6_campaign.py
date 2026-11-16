#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
import argparse,json,re,subprocess,sys
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--prefix',required=True);p.add_argument('--installed',action='store_true');a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.prefix);root=Path(__file__).resolve().parents[1];e=root/'local-evidence/runtime-compare/h6-20261116';results=[]
 cases=[('basic',b,m)for b in range(4)for m in [0,1]]+[('original-cleanup',3,m)for m in [0,1]]+[('save',3,1),('sleep',3,1),('bound',3,1),('basic',3,1)]
 for i,(mode,board,monitor)in enumerate(cases):
  case=f'{a.prefix}-{i:02d}';cmd=[sys.executable,str(root/'tests/h6_power_native.py'),'--mode',mode,'--board',str(board),'--monitor',str(monitor),'--case',case]+(['--installed']if a.installed else[])+(['--network-audit']if i==13 else[])
  with(e/(case+'.log')).open('w')as f:r=subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT,timeout=150)
  path=e/case/'result.json';d=json.loads(path.read_text())if path.exists()else{'pass_':False};results.append(d);(e/(a.prefix+'-campaign.json')).write_text(json.dumps(results,indent=2)+'\n');print(case,r.returncode,d.get('pass_',False),flush=True)
  if r.returncode or not d.get('pass_'):raise SystemExit(1)
 for i in [0,2,4,6,8]:assert results[i]['cpu']==results[i+1]['cpu'],'Observer changed guest CPU journal'
 print('H6_PASS',len(results),'PASSIVITY_PAIRS',5,flush=True)
if __name__=='__main__':main()
