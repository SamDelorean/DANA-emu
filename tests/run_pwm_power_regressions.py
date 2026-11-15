#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""H5 affected-path regressions using existing qualified harnesses."""
import argparse,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--prefix',required=True);p.add_argument('--installed',action='store_true');p.add_argument('--groups',nargs='*',default=['original','gui','lcd','h2','nor','uart','usb','power','cursor']);a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.prefix)
 root=Path(__file__).resolve().parents[1];folder=root/'local-evidence/runtime-compare/h5-20261115';results=[];binary=root/('runtime/diag/bin/dana-diag'if a.installed else'runtime/diag/source/danadiagd');digest=hashlib.sha256(binary.read_bytes()).hexdigest();installed=['--installed']if a.installed else[]
 def run(name,script,args=(),timeout=400):
  command=[sys.executable,str(root/'tests'/script)]+list(args);start=time.monotonic();env=os.environ.copy();env['TMPDIR']=str(folder)
  with(folder/(a.prefix+'-'+name+'.log')).open('w')as f:r=subprocess.run(command,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  results.append(dict(name=name,command=command,returncode=r.returncode,elapsed_seconds=time.monotonic()-start,binary_sha256=digest,pass_=r.returncode==0));(folder/(a.prefix+'-regressions.json')).write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results[-1]),flush=True)
  if r.returncode:raise SystemExit(1)
 if 'original'in a.groups:
  for pg1 in [0,1]:run('original-'+str(pg1),'power_original_native.py',['--pg1',str(pg1),'--case',a.prefix+'-original-'+str(pg1)]+installed)
 if 'gui'in a.groups:run('gui','run_keyboard_headless_campaign.py',['--prefix',a.prefix+'-gui']+installed,1000)
 if 'lcd'in a.groups:run('lcd','run_lcd_campaign.py',['--prefix',a.prefix+'-lcd','--modes','bpp1','bpp2','bpp4','dynamic','clock','sleep-save','save','cursor2','contrast']+installed)
 if 'h2'in a.groups:
  for i,(mode,rate)in enumerate([('clock',0),('pcm',15),('sleep',3),('doze',0),('irq-mixed',0),('watchdog-reset',0),('rtc-calendar',0),('gpio',0),('save',0)]):run('h2-'+mode,'h2_native.py',['--mode',mode,'--rate',str(rate),'--case',a.prefix+'-h2-'+str(i)]+installed)
 if 'nor'in a.groups:
  base=root/'local-evidence/runtime-compare'
  for chip in ['m28w640hcb','m29w320db']:
   for mode in ['program','erase','protect','persist','save','watchdog']:run(chip+'-'+mode,'nor_native.py',['--mode',mode,'--chip',chip,'--case',a.prefix+'-'+chip+'-'+mode]+installed)
   run(chip+'-readback','nor_native.py',['--mode','readback','--chip',chip,'--case',a.prefix+'-'+chip+'-readback','--reuse',str(base/(a.prefix+'-'+chip+'-persist'))]+installed)
 if 'uart'in a.groups:
  for mode,uart in [('dual',1),('irda',2),('saveir',2),('clock',1)]:run('uart-'+mode,'serial_native.py',['--mode',mode,'--uart',str(uart),'--case',a.prefix+'-uart-'+mode]+installed)
 if 'usb'in a.groups:
  for mode in ['host-printer','device','host-faults','ptd-bus']:run('usb-'+mode,'run_isp1161_native.py',['--mode',mode,'--case',a.prefix+'-usb-'+mode]+installed)
  run('original-print','run_isp1161_palm.py',['--mode','printer','--case',a.prefix+'-print']+installed)
 if 'power'in a.groups:run('original-wake','run_host_calendar_native.py',['--case',a.prefix+'-wake','--script','tests/h2_palm_power.lua']+([]if a.installed else['--candidate']))
 if 'cursor'in a.groups:run('cursor','lcd_cursor_uk15_test.py')
 assert hashlib.sha256(binary.read_bytes()).hexdigest()==digest
 print('H5_REGRESSION_PASS',len(results),flush=True)
if __name__=='__main__':main()
