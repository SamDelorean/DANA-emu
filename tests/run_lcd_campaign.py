#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Single sequential H4 qualification in the canonical MAME build/runtime."""
import argparse,json,re,subprocess,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--prefix',required=True);p.add_argument('--installed',action='store_true');p.add_argument('--modes',nargs='*');a=p.parse_args()
 assert re.fullmatch('[A-Za-z0-9_-]+',a.prefix);root=Path(__file__).resolve().parents[1]
 modes=a.modes or ['bpp1','bpp2','bpp4']+['palette'+format(i,'x')for i in range(16)]+['pan','pagewrap','ram8','ram16','dynamic','live','clock','self-refresh','off','save','cursor','blink','polarity','dma','pins','contrast','watchdog','sleep','sleep-save','bus1','bus2','bus8','lanes','timing','contrast-line','contrast-pixel','mux','acd-line','acd-frame','cursor2']
 cases=[(m,1)for m in modes]
 if not a.modes:cases+=[('bpp4',0),('bpp4',2)]
 results=[];folder=root/'local-evidence/runtime-compare/h4-20261115';report=folder/(a.prefix+'-campaign.json')
 for index,(mode,panel)in enumerate(cases):
  case=f'{a.prefix}-{index:02d}-{mode}-p{panel}'
  command=[sys.executable,str(root/'tests/lcd_native.py'),'--mode',mode,'--panel',str(panel),'--case',case]+(['--installed']if a.installed else[])
  with(folder/(case+'.log')).open('w')as f:r=subprocess.run(command,cwd=root,stdout=f,stderr=subprocess.STDOUT,timeout=200)
  path=folder/case/'result.json';data=json.loads(path.read_text())if path.exists()else{'pass_':False}
  results.append(dict(mode=mode,panel=panel,case=case,returncode=r.returncode,**{k:v for k,v in data.items()if k not in ['mode','panel','returncode','events']}))
  report.write_text(json.dumps(results,indent=2)+'\n')
  print(json.dumps(dict(case=case,pass_=data.get('pass_',False),returncode=r.returncode)),flush=True)
  if r.returncode or not data.get('pass_'):raise SystemExit(1)
 print('H4_NATIVE_PASS',len(results),flush=True)
if __name__=='__main__':main()
