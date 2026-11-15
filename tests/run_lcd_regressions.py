#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Reuse the established system campaigns after the LCD integration."""
import argparse,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--prefix',required=True);p.add_argument('--installed',action='store_true');p.add_argument('--groups',nargs='*',default=['gui','h2','nor','uart','usb','power','cursor']);a=p.parse_args()
 assert re.fullmatch('[A-Za-z0-9_-]+',a.prefix);root=Path(__file__).resolve().parents[1];folder=root/'local-evidence/runtime-compare/h4-20261115';report=folder/(a.prefix+'-regressions.json');results=[]
 binary=root/('runtime/diag/bin/dana-diag'if a.installed else'runtime/diag/source/danadiagd');sha=hashlib.sha256(binary.read_bytes()).hexdigest()
 def run(name,script,extra=(),timeout=400):
  command=[sys.executable,str(root/'tests'/script)]+list(extra);start=time.monotonic();env=os.environ.copy();env['TMPDIR']=str(folder)
  with(folder/(a.prefix+'-'+name+'.log')).open('w')as f:r=subprocess.run(command,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  results.append(dict(name=name,command=command,returncode=r.returncode,elapsed_seconds=time.monotonic()-start,binary_sha256=sha,pass_=r.returncode==0));report.write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results[-1]),flush=True)
  if r.returncode:raise SystemExit(1)
 installed=['--installed']if a.installed else[]
 if 'gui'in a.groups:run('gui','run_keyboard_headless_campaign.py',['--prefix',a.prefix+'-gui']+installed,1000)
 if 'h2'in a.groups:
  for n,c in enumerate(json.loads((root/'docs/H2_NATIVE_RESULTS_20261101.json').read_text())['native_h2_cases']):
   run('h2-'+str(n)+'-'+c['mode'],'h2_native.py',['--mode',c['mode'],'--rate',str(c['rate']),'--case',a.prefix+'-h2-'+str(n)]+installed)
 if 'nor'in a.groups:
  for chip in ['m28w640hcb','m29w320db']:run('nor-'+chip,'run_nor_campaign.py',['--prefix',a.prefix+'-'+chip,'--chip',chip]+installed,1500)
 if 'uart'in a.groups:
  for n,(mode,uart)in enumerate([('backend',1),('backend',2),('irda',1),('irda',2),('dual',1),('saveir',2),('clock',1),('irq',1),('irq',2)]):
   run('uart-'+str(n),'serial_native.py',['--mode',mode,'--uart',str(uart),'--case',a.prefix+'-uart-'+str(n)]+installed)
 if 'usb'in a.groups:
  for mode in ['host-printer','device','host-faults','ptd-bus']:run('usb-'+mode,'run_isp1161_native.py',['--mode',mode,'--case',a.prefix+'-usb-'+mode]+installed)
  run('palm-print','run_isp1161_palm.py',['--mode','printer','--case',a.prefix+'-palm-print']+installed,400)
 if 'power'in a.groups:run('power','run_host_calendar_native.py',['--case',a.prefix+'-power','--script','tests/h2_palm_power.lua']+([]if a.installed else['--candidate']),400)
 if 'cursor'in a.groups:run('cursor','lcd_cursor_uk15_test.py')
 assert hashlib.sha256(binary.read_bytes()).hexdigest()==sha
 print('H4_REGRESSION_PASS',len(results),flush=True)
if __name__=='__main__':main()
