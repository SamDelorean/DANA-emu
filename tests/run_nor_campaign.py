#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Sequential H3 qualification; one existing binary and disposable synthetic media."""
import argparse, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

MODES=['identify','program','erase','protect','suspend','save','timing','vpp-off',
       'multi','multi-vdd','invalid','otp','cs-ro','partial-data','width','unmapped',
       'unknown','erase-unknown','rp','reset-cpu','program-suspend','group-alignment',
       'reverse-group','watchdog','address-error','cs-berr','save-program',
       'save-nested','save-setup','persist','powercut']

def main():
    p=argparse.ArgumentParser();p.add_argument('--prefix',required=True)
    p.add_argument('--installed',action='store_true');p.add_argument('--chip',choices=['m28w640hcb','m29w320db'],default='m28w640hcb');a=p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+',a.prefix)
    root=Path(__file__).resolve().parents[1];base=root/'local-evidence/runtime-compare'
    record=base/(a.prefix+'-campaign');record.mkdir(parents=True,exist_ok=False)
    receipts=[]
    def run(mode,label=None,extra=()):
        label=label or mode;case=a.prefix+'-'+label
        command=[sys.executable,str(root/'tests/nor_native.py'),'--mode',mode,'--case',case,'--chip',a.chip]
        if a.installed:command+=['--installed']
        subprocess.run(command+list(extra),cwd=root,check=True)
        data=json.loads((base/case/'result.json').read_text());assert data['pass']
        receipts.append(dict(case=case,**data))
        return base/case
    modes=MODES if a.chip=='m28w640hcb'else ['identify','program','erase','chip','suspend','multi','save','watchdog','save-unlock','timing','protect','rp','invalid','accelerated','factory-lock','factory-unprotect','partial-data','width','unmapped','address-error','cs-ro','cs-berr','persist','powercut']
    for mode in modes:run(mode)
    media=base/(a.prefix+'-persist');nv=next(p for p in (media/'nvram').rglob('*')if p.is_file())
    digest=hashlib.sha256(nv.read_bytes()).hexdigest()
    saved=run('readback',extra=['--reuse',str(media),'--save-final'])
    run('readback','state-reopen',['--reuse',str(media),'--load-state',str(saved/'pending.sta')])
    assert hashlib.sha256(nv.read_bytes()).hexdigest()==digest
    if a.chip=='m28w640hcb':run('otp-readback',extra=['--reuse',str(base/(a.prefix+'-otp'))])
    else:run('protection-readback',extra=['--reuse',str(base/(a.prefix+'-factory-lock'))])
    cut=base/(a.prefix+'-powercut')
    run('powercut-read',extra=['--reuse',str(cut)])
    run('powercut-erase',extra=['--reuse',str(cut)])
    saved=base/(a.prefix+'-save')
    run('save','state-conflict',['--reuse',str(saved),'--load-state',str(saved/'pending.sta'),'--expect-rejection'])
    run('save','reference-state-reject',['--reuse',str(saved),'--load-state',str(saved/'pending.sta'),'--reference','--expect-rejection'])
    for kind in ['corrupt','foreign']:
        dest=record/(kind+'-media');dest.mkdir();shutil.copy2(media/'seed.bin',dest/'seed.bin');shutil.copytree(media/'nvram',dest/'nvram')
        target=dest/'seed.bin'if kind=='foreign'else next(p for p in (dest/'nvram').rglob('*')if p.is_file())
        target.chmod(0o644) # Only this explicitly disposable corruption fixture.
        data=bytearray(target.read_bytes());data[0x60000]^=1;target.write_bytes(data)
        run('identify',kind,['--reuse',str(dest),'--expect-rejection'])
    run('vpp-off'if a.chip=='m28w640hcb'else'reference','reference',['--reference'])
    assert len({r['binary_sha256']for r in receipts})==1
    result=dict(status='PROFILE_NATIVE_PASS_WITH_DECLARED_BOUNDARIES',cases=receipts,
                physical_U7_identity='NO_VERIFICADO',global_chip_erase='NOT_SUPPORTED_BY_PROFILE'if a.chip=='m28w640hcb'else'CPU_NATIVE_PASS')
    (record/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('H3_NOR_CAMPAIGN_PASS',len(receipts),flush=True)
if __name__=='__main__':main()
