#!/usr/bin/env python3
"""Run/verify two fresh real EmuTOS-Dana boots on an existing DIAG binary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
sys.path.insert(0,str(PROJECT/'tools'))
from f1_guest import validate,sha
from d1_2_run import lua

def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')

def verify(root,guest):
    root=Path(root)
    try:
        manifest=validate(guest);syms=manifest['symbols']
        run=json.loads((root/'run.json').read_text())
        obs=json.loads((root/'observation.json').read_text())
        if run.get('reason')=='HOST_TIMEOUT':return {'status':'BLOCKED','domain':'INFRA','reason':'HOST_TIMEOUT'}
        if run['exit_code']!=0:return {'status':'BLOCKED','domain':'HARNESS','reason':'MAME_EXIT_'+str(run['exit_code'])}
        if obs['package_sha256']!=manifest['package']['sha256'] or obs['binary_sha256']!=run['binary_sha256']:
            raise ValueError('Observation/input identity mismatch')
        first=obs['first_instruction']
        if not first or (first['CURPC'],first['SP'],first['SR'])!=(syms['_os_header'],syms['_stktop'],0x2700):
            return {'status':'BLOCKED','domain':'HARNESS','reason':'BLOCKED_BOOTSTRAP'}
        if sha(root/'initial-image.bin')!=manifest['artifacts']['emutos.img']['sha256']:
            raise ValueError('Native loaded RAM differs from original guest image')
        events=obs['events']
        if not isinstance(events,list) or len(events)>20000 or len(json.dumps(events).encode())>5*1024*1024:
            raise ValueError('Missing/over-budget events')
        if [e['seq'] for e in events]!=list(range(len(events))):raise ValueError('Incomplete event sequence')
        reads=[(e['address'],e['data']) for e in events if e['kind']=='read']
        expected=[(0,syms['_stktop']>>16),(2,syms['_stktop']&65535),(4,syms['_os_header']>>16),(6,syms['_os_header']&65535)]
        if reads[:4]!=expected:raise ValueError('Native reset vector fetch ordering/value mismatch')
        milestones=[e['state']['CURPC'] for e in events if e['kind']=='milestone']
        if not all(syms[n] in milestones for n in ('_main','_realmain')):
            return {'status':'BLOCKED','domain':'GUEST','reason':'STARTUP_NOT_REACHED','observed':milestones}
        trace=(root/'guest.trace').read_text()
        if len(trace.encode())>5*1024*1024 or len(trace.splitlines())>20000:
            return {'status':'BLOCKED','domain':'HARNESS','reason':'INSTRUCTION_TRACE_LIMIT'}
        pcs=[int(v,16) for v in re.findall(r'^\s*([0-9a-fA-F]+):',trace,re.M)]
        if not all(syms[n] in pcs for n in ('_os_header','_main','_realmain')):
            raise ValueError('Native instruction trace does not corroborate startup PCs')
        data={'status':'BLOCKED','domain':'HARDWARE','reason':obs['reason'],
              'guest_execution':{'status':'PASS','scope':'Actual map-bound _os_header -> _main -> _realmain'},
              'dependency':obs.get('dependency'),'final':obs['final'],
              'milestones':milestones,'instruction_trace_sha256':sha(root/'guest.trace'),
              'package_sha256':manifest['package']['sha256'],'binary_sha256':run['binary_sha256'],
              'exception_vector_reads':[e for e in events if e['kind']=='read' and 8<=e['address']<0x400],
              'normalized':{'reason':obs['reason'],'dependency':obs.get('dependency'),'final':obs['final'],
                            'milestones':milestones,
                            'bus':[{k:e[k] for k in ('kind','address','data','mask','state')} for e in events if e['kind'] in ('read','write')]}}
        if obs['reason']=='BLOCKED_HARDWARE':
            dep=obs.get('dependency')
            if not dep or dep['address']<0xfffff000:raise ValueError('Invalid VZ dependency evidence')
            if not any(e['kind']==dep['kind'] and e['address']==dep['address'] for e in events):
                raise ValueError('Dependency has no actual CPU transaction')
        elif obs['reason'].startswith('FAIL_'):data.update(status='FAIL',domain='PRODUCT')
        else:data['domain']='HARNESS'
        return data
    except FileNotFoundError as error:
        return {'status':'BLOCKED','domain':'INPUT_OR_HARNESS','reason':str(error)}
    except (ValueError,KeyError,TypeError) as error:
        return {'status':'FAIL','domain':'EVIDENCE','reason':str(error)}

def limits():
    # Finite native trace/console artifacts, rather than unlimited trace output.
    resource.setrlimit(resource.RLIMIT_FSIZE,(5*1024*1024,5*1024*1024))

def run(binary,guest,root,reject=False):
    manifest=validate(guest);syms=manifest['symbols'];root=Path(root).resolve()
    root.mkdir(parents=True,exist_ok=False)
    plugin=root/'plugin';plugin.mkdir();shutil.copyfile(HERE/'f1_emutos_boot.lua',plugin/'boot.lua')
    config={'output':str(root),'symbols':syms,'image_length':manifest['artifacts']['emutos.img']['size'],
            'package_sha256':manifest['package']['sha256'],'binary_sha256':sha(binary)}
    cfg=root/'config.lua';cfg.write_text('return '+lua(config)+'\n')
    environment=dict(os.environ,DANA_F1_CONFIG=str(cfg))
    image=Path(guest).resolve()/'emutos.dana'
    if reject:
        image=root/'corrupt.dana';payload=bytearray((Path(guest)/'emutos.dana').read_bytes());payload[-1]^=1
        image.write_bytes(payload)
    command=[str(binary),'asmdana','-noreadconfig','-quickload',str(image),
             '-debug','-debugger','none','-pluginspath',str(plugin),'-plugins','-video','none',
             '-sound','none','-log','-skip_gameinfo','-seconds_to_run','6']
    record={'binary_sha256':config['binary_sha256'],'command':command,
            'driver_sha256':sha(PROJECT/'src/mame/skeleton/alphasdana.cpp'),
            'package_sha256':config['package_sha256'],'host_timeout_seconds':180}
    try:
        with (root/'console.log').open('wb') as log:
            proc=subprocess.run(command,cwd=root,env=environment,stdout=log,stderr=subprocess.STDOUT,
                                timeout=180,preexec_fn=limits)
        record['exit_code']=proc.returncode
    except subprocess.TimeoutExpired:record.update(exit_code=None,reason='HOST_TIMEOUT')
    save(root/'run.json',record)
    if reject:
        try:
            obs=json.loads((root/'observation.json').read_text())
            console=(root/'console.log').read_text(errors='replace')
            trace=(root/'guest.trace').read_text(errors='replace')
            rejected=('Guest image digest mismatch' in console and not obs['first_instruction']
                      and not re.search(r'^\s*[0-9a-fA-F]+:',trace,re.M))
            result={'status':'PASS' if rejected else 'FAIL','scope':'Native corrupt-image rejection; no guest execution',
                    'reason':'DIGEST_REJECTED_BEFORE_CPU_FETCH' if rejected else 'NATIVE_REJECTION_NOT_PROVED'}
        except (OSError,ValueError,KeyError) as error:
            result={'status':'BLOCKED','reason':str(error)}
    else:result=verify(root,guest)
    save(root/'result.json',result)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('diag',type=Path)
    p.add_argument('guest',type=Path);p.add_argument('evidence',type=Path)
    args=p.parse_args();root=args.evidence.resolve();root.mkdir(parents=True,exist_ok=False)
    try:
        binary=args.diag.resolve()
        if not binary.is_file():raise RuntimeError('BLOCKED_EXECUTABLE_MISSING: '+str(binary))
        validate(args.guest)
        a=run(binary,args.guest,root/'run-1');b=run(binary,args.guest,root/'run-2')
        negative=run(binary,args.guest,root/'native-rejection',reject=True)
        repeated='normalized' in a and 'normalized' in b and a['normalized']==b['normalized']
        result={'status':'FAIL' if 'FAIL' in (a['status'],b['status']) else 'BLOCKED',
                'scope':'First real guest execution and next dependency; not complete EmuTOS boot',
                'repeat':'PASS' if repeated else 'BLOCKED' if 'normalized' not in a or 'normalized' not in b else 'FAIL',
                'runs':[a,b],'native_rejection':negative}
        if negative['status']=='FAIL':result.update(status='FAIL',reason='NATIVE_REJECTION_REGRESSION')
        if result['repeat']=='FAIL':result.update(status='FAIL',reason='NONDETERMINISTIC_GUEST_STATE')
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        result={'status':'BLOCKED','domain':'INPUT_OR_INFRA','reason':str(error)}
    save(root/'result.json',result);print(json.dumps(result,indent=2))
    return 1 if result['status']=='FAIL' else 2

if __name__=='__main__':sys.exit(main())
