#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
import argparse,json,re,subprocess,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--prefix',required=True);p.add_argument('--installed',action='store_true');p.add_argument('--modes',nargs='*');a=p.parse_args()
 assert re.fullmatch('[A-Za-z0-9_-]+',a.prefix);root=Path(__file__).resolve().parents[1];folder=root/'local-evidence/runtime-compare/h5-20261115';results=[]
 modes=a.modes or ['repeat0','repeat1','repeat2','repeat3','period-ff','counter','duty0','duty100','irq','irq-control','mixed','clock','clock32','sleep','sleep32','save','reset','adc7','adc8','adc-pen','power-low','power-high']
 for i,mode in enumerate(modes):
  case=f'{a.prefix}-{i:02d}-{mode}';command=[sys.executable,str(root/'tests/pwm_power_native.py'),'--mode',mode,'--case',case]+(['--installed']if a.installed else[])
  with(folder/(case+'.log')).open('w')as f:r=subprocess.run(command,cwd=root,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  path=folder/case/'result.json';data=json.loads(path.read_text())if path.exists()else{'pass_':False}
  results.append(dict(case=case,**{k:v for k,v in data.items()if k not in ['events','states']}));(folder/(a.prefix+'-campaign.json')).write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(dict(case=case,returncode=r.returncode,pass_=data.get('pass_',False))),flush=True)
  if r.returncode or not data.get('pass_'):raise SystemExit(1)
 print('H5_NATIVE_PASS',len(results),flush=True)
if __name__=='__main__':main()
