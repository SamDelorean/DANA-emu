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
import uuid

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
sys.path.insert(0,str(PROJECT/'tools'))
from f1_guest import validate,validate_qualified,sha
from d1_2_run import lua

def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')

BINARY_SHA='d7bcdf513289a73b8a5c7ab1d258eeac45dc8dd6d89dd7d568cf7784900e6fe5'
OLD_PC=0x8392
TRACE_LIMIT=5*1024*1024


def selected_bytes(event):
    """Independently decode the raw 16-bit, big-endian native tap lanes."""
    address,mask=event['address'],event['mask']
    if type(address) is not int or not 0<=address<=0xfffffffe or address%2 or mask not in (0xff00,0xff,0xffff):
        raise ValueError('Unsupported native bus shape')
    return [address+i for i,lane in enumerate((0xff00,0xff)) if mask & lane]


def implemented_byte(address,kind):
    # Match only the individually decoded production addresses; no new device.
    return (0xfffff202<=address<=0xfffff203 or address==0xfffff300
        or 0xfffff302<=address<=0xfffff307 or 0xfffff30c<=address<=0xfffff30f
        or (kind=='read' and 0xfffff310<=address<=0xfffff313)
        or address in (0xfffff412,0xfffff413))


def verify_e4(root,guest,expected_source=None):
    """Independent raw-evidence check. A single run cannot qualify E4."""
    root=Path(root)
    try:
        manifest=validate_qualified(guest);syms=manifest['symbols']
    except (OSError,ValueError,KeyError,TypeError) as exc:
        return {'status':'BLOCKED_GUEST','domain':'INPUT','reason':str(exc)}
    try:
        from d2_2_gpio_run import staged_identity
        if expected_source is None:
            expected_source=subprocess.check_output(['git','-C',str(PROJECT),'rev-parse','HEAD'],text=True).strip()
        run=json.loads((root/'run.json').read_text());obs=json.loads((root/'observation.json').read_text())
        if not isinstance(run,dict) or not isinstance(obs,dict):raise ValueError('Invalid evidence objects')
        staged_identity(run)
        if run.get('exit_code')!=0 or run.get('reason')=='HOST_TIMEOUT':raise ValueError('Native process incomplete')
        for key,value in (('revision','F1-E4'),('variant','diag'),('binary_sha256',BINARY_SHA),
                          ('package_sha256',manifest['package']['sha256']),
                          ('image_sha256',manifest['artifacts']['emutos.img']['sha256'])):
            if run.get(key)!=value or obs.get(key)!=value:raise ValueError('Identity mismatch: '+key)
        if type(run.get('pid')) is not int or run['pid']<=0:raise ValueError('Missing native process ID')
        for key,pattern in (('source_commit',r'[0-9a-f]{40}'),('execution_id',r'[0-9a-f]{32}')):
            if not re.fullmatch(pattern,run.get(key,'')) or run[key]!=obs.get(key):
                raise ValueError('Unbound '+key)
        if run['source_commit']!=expected_source or run.get('driver_sha256')!=sha(PROJECT/'src/mame/skeleton/alphasdana.cpp'):
            raise ValueError('Wrong harness or production source identity')
        if obs.get('status')!='CAPTURED' or obs.get('schema')!='dana-f1-e4-observation-v1':
            raise ValueError('No E4 capture')
        if run.get('full_boot') is not False or obs.get('full_boot') is not False:
            raise ValueError('False or ambiguous full-boot claim')
        if obs.get('trace_mode')!='native_loop_compression_no_sampling':raise ValueError('Incomplete trace mode')
        if not 0<=obs['virtual_seconds']<=6:raise ValueError('Virtual execution bound')
        first=obs['first_instruction']
        if (first['CURPC'],first['SP'],first['SR'])!=(syms['_os_header'],syms['_stktop'],0x2700):
            raise ValueError('Unproved map-bound CPU entry')
        if sha(root/'initial-image.bin')!=manifest['artifacts']['emutos.img']['sha256']:
            raise ValueError('Native initial image mismatch')
        events=obs['events']
        if (not isinstance(events,list) or not events or len(events)>20000
                or any(not isinstance(e,dict) for e in events)
                or len(json.dumps(events).encode())>TRACE_LIMIT):raise ValueError('Invalid event budget/shape')
        if obs.get('event_count')!=len(events) or [e.get('seq') for e in events]!=list(range(len(events))):
            raise ValueError('Missing/duplicate raw events')
        if any(e.get('kind')=='instruction_trace_sampling_end' for e in events):raise ValueError('Sampled trace')
        times=[e['virtual_seconds'] for e in events]
        if times!=sorted(times) or not 0<=times[0]<=times[-1]<=obs['virtual_seconds']:
            raise ValueError('Reordered/out-of-window native evidence')
        bus=[e for e in events if e.get('kind') in ('read','write')]
        if len(bus)<4:raise ValueError('Missing native reset vectors')
        for e in bus:
            if (e.get('origin')!='cpu' or e.get('tap_id')!='f1_'+e['kind']
                    or e.get('side_effects_disabled') is not False):raise ValueError('Non-CPU bus origin')
            lanes=selected_bytes(e)
            if e.get('byte_addresses')!=lanes or e.get('width_bits')!=8*len(lanes):
                raise ValueError('Wrong effective byte lane')
            if type(e.get('data')) is not int or not 0<=e['data']<=65535:raise ValueError('Invalid bus value')
            state=e['state']
            if any(type(state.get(k)) is not int for k in ('CURPC','PC','SR','SP','IR')):
                raise ValueError('Missing native CPU diagnostic state')
        vector=[(e['kind'],e['address'],e['mask'],e['data']) for e in bus[:4]]
        expected=[('read',a,65535,d) for a,d in ((0,syms['_stktop']>>16),(2,syms['_stktop']&65535),
                    (4,syms['_os_header']>>16),(6,syms['_os_header']&65535))]
        if vector!=expected:raise ValueError('Missing/incorrect native reset vectors')
        starts=[e for e in events if e.get('kind')=='first_instruction']
        if len(starts)!=1 or starts[0]['origin']!='debugger_observation' or starts[0]['state']!=first:
            raise ValueError('Unbound first instruction')
        if bus[3]['seq']>=starts[0]['seq']:raise ValueError('CPU entry precedes vector reads')
        if [e for e in bus if e['seq']<starts[0]['seq']]!=bus[:4]:
            raise ValueError('Extra/duplicated pre-entry CPU vector traffic')
        if any(type(obs['final'].get(k)) is not int for k in ('CURPC','PC','SR','SP','IR')):
            raise ValueError('Missing final CPU diagnostic state')
        trace_path=root/'guest.trace'
        if (root/'console.log').stat().st_size>TRACE_LIMIT:raise ValueError('Console size limit')
        if not 0<trace_path.stat().st_size<=TRACE_LIMIT:raise ValueError('Instruction trace size limit')
        trace=trace_path.read_text()
        if len(trace.splitlines())>20000 or obs.get('trace_bytes')!=trace_path.stat().st_size:
            raise ValueError('Incomplete/unbounded instruction trace')
        pcs=[int(v,16) for v in re.findall(r'^\s*([0-9a-fA-F]+):',trace,re.M)]
        if not pcs or pcs[0]!=syms['_os_header'] or pcs.count(syms['_os_header'])!=1:
            raise ValueError('Missing/replayed guest trace entry')
        path=['_os_header','_main','_realmain']+(['_dana_init'] if '_dana_init' in syms else [])
        positions=[pcs.index(syms[n]) for n in path]
        if positions!=sorted(set(positions)):raise ValueError('Unknown startup trace order')
        milestone_events=[starts[0]]
        for name in path[1:]:
            match=[e for e in events if e.get('kind')=='milestone' and e['state']['CURPC']==syms[name]]
            if len(match)!=1 or match[0].get('origin')!='debugger_observation':raise ValueError('Missing startup milestone')
            milestone_events+=match
        if [e['seq'] for e in milestone_events]!=sorted(e['seq'] for e in milestone_events):
            raise ValueError('Out-of-order startup milestones')
        crossing=[e for e in bus if e['kind']=='write' and e['address']==0xfffff412
                  and e['mask']==0xff and e['state']['CURPC']==OLD_PC and e['data'] & 0xff==0]
        crossing_proved=(len(crossing)==1 and milestone_events[-1]['seq']<crossing[0]['seq']
                         and pcs.count(OLD_PC)==1 and positions[-1]<pcs.index(OLD_PC))
        # Find, independently of Lua's claimed dependency, the FIRST unsupported
        # native byte. Later native tail is retained but never counts as progress.
        missing=[]
        for e in bus:
            for address in selected_bytes(e):
                if address>=0x400000 and not implemented_byte(address,e['kind']):missing.append((e,address))
        if not missing:
            return {'status':'BLOCKED_GUEST','reason':'NO_NEW_CPU_DEPENDENCY_WITHIN_BOUND',
                    'milestones':path,'old_pcsel_crossing_proved':crossing_proved,'full_boot':False}
        event,effective=missing[0]
        if obs.get('reason')!='BLOCKED_HARDWARE' or effective<0xfffff000:
            return {'status':'BLOCKED_GUEST','reason':'NO_CONFIDENT_NEXT_VZ_DEPENDENCY','full_boot':False}
        dep=obs.get('dependency')
        if (not isinstance(dep,dict) or dep.get('event_seq')!=event['seq'] or dep.get('origin')!='cpu'
                or dep.get('effective_address')!=effective or dep.get('tap_id')!=event['tap_id']
                or any(dep.get(k)!=event[k] for k in ('address','kind','data','mask','state','byte_addresses','width_bits'))):
            raise ValueError('Claimed dependency is not first raw unsupported CPU access')
        if not crossing_proved or crossing[0]['seq']>=event['seq']:
            raise ValueError('No genuine old-PCSEL CPU write before new dependency')
        pc=event['state']['CURPC']
        if not syms['__text']<=pc<syms['__text']+manifest['artifacts']['emutos.img']['size']:
            raise ValueError('Unknown dependency instruction path')
        if pc not in pcs[pcs.index(OLD_PC)+1:]:raise ValueError('Dependency absent from post-PCSEL instruction trace')
        for e in bus:
            if e.get('after_dependency') is not (e['seq']>event['seq']):raise ValueError('Hidden/reordered deferred bus tail')
        normalized={'address':event['address'],'effective_address':effective,'kind':event['kind'],
                    'mask':event['mask'],'value':event['data'] & event['mask'],
                    'byte_addresses':event['byte_addresses'],'width_bits':event['width_bits'],
                    'state':{k:event['state'][k] for k in ('CURPC','PC','SR','SP','IR')}}
        return {'status':'OBSERVED_UNQUALIFIED_SINGLE_RUN','scope':'Post-Port-C guest dependency only',
                'full_boot':False,'dependency':dep,'normalized_dependency':normalized,'milestones':path,
                'crossing_event_seq':crossing[0]['seq'],'dependency_event_seq':event['seq'],
                'deferred_tail_bus_events':sum(e['seq']>event['seq'] for e in bus),
                'instruction_trace_sha256':sha(trace_path),'binary':run['command'][0],
                **{k:run[k] for k in ('source_commit','binary_sha256','package_sha256','image_sha256','pid','execution_id')},
                'normalized_bus_prefix':[{k:e[k] for k in ('kind','address','data','mask','state')}
                                         for e in bus if e['seq']<=event['seq']]}
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError,subprocess.SubprocessError) as exc:
        return {'status':'BLOCKED_HARNESS','domain':'EVIDENCE','reason':str(exc),'full_boot':False}


def verify_e4_pair(root,guest,expected_source=None):
    runs=[verify_e4(Path(root)/name,guest,expected_source) for name in ('run-1','run-2')]
    result={'status':'BLOCKED_HARNESS','scope':'F1-E4 two-run authentic post-Port-C continuation only',
            'full_boot':False,'runs':runs,'reason':'TWO_GENUINE_PROGRESS_OBSERVATIONS_REQUIRED'}
    if any(r['status']!='OBSERVED_UNQUALIFIED_SINGLE_RUN' for r in runs):
        if any(r['status']=='BLOCKED_GUEST' for r in runs):result['status']='BLOCKED_GUEST'
        return result
    a,b=runs
    if a['pid']==b['pid'] or a['execution_id']==b['execution_id']:
        result['reason']='INDEPENDENT_NATIVE_PROCESSES_NOT_PROVED'
    elif any(a[k]!=b[k] for k in ('binary','source_commit','binary_sha256','package_sha256','image_sha256')):
        result['reason']='DIFFERENT_NATIVE_SOURCE_OR_INPUTS'
    elif a['normalized_dependency']!=b['normalized_dependency'] or a['milestones']!=b['milestones']:
        result['reason']='NONREPRODUCIBLE_NEXT_CPU_DEPENDENCY'
    else:
        result.update(status='REAL_PROGRESS_PASS_SCOPED',reason='OLD_PCSEL_CROSSED_NEW_DEPENDENCY_REPRODUCED',
                      normalized_dependency=a['normalized_dependency'],
                      raw_bus_prefix_equal=a['normalized_bus_prefix']==b['normalized_bus_prefix'])
    return result

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

def run(binary,guest,root,reject=False,post_portc=False):
    from d2_2_gpio_run import diag_path
    if not Path(binary).is_absolute():raise ValueError('Explicit absolute DIAG path required')
    binary=diag_path(binary)
    if post_portc and sha(binary)!=BINARY_SHA:raise ValueError('Qualified DIAG SHA required; no fallback')
    manifest=(validate_qualified if post_portc else validate)(guest);syms=manifest['symbols'];root=Path(root).resolve()
    root.mkdir(parents=True,exist_ok=False)
    plugin=root/'plugin';plugin.mkdir();shutil.copyfile(HERE/'f1_emutos_boot.lua',plugin/'boot.lua')
    config={'output':str(root),'symbols':syms,'image_length':manifest['artifacts']['emutos.img']['size'],
            'package_sha256':manifest['package']['sha256'],'binary_sha256':sha(binary)}
    if post_portc:
        config.update(revision='F1-E4',variant='diag',execution_id=uuid.uuid4().hex,
                      source_commit=subprocess.check_output(['git','-C',str(PROJECT),'rev-parse','HEAD'],text=True).strip(),
                      image_sha256=manifest['artifacts']['emutos.img']['sha256'],full_boot=False)
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
    if post_portc:
        record.update({k:config[k] for k in ('revision','variant','execution_id','source_commit','image_sha256','full_boot')})
    try:
        with (root/'console.log').open('wb') as log:
            proc=subprocess.Popen(command,cwd=root,env=environment,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits)
            record['pid']=proc.pid
            try:record['exit_code']=proc.wait(timeout=180)
            except subprocess.TimeoutExpired:
                proc.kill();proc.wait();record.update(exit_code=None,reason='HOST_TIMEOUT')
    except OSError as error:record.update(exit_code=None,reason='NATIVE_LAUNCH: '+str(error))
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
    else:result=(verify_e4 if post_portc else verify)(root,guest)
    save(root/'result.json',result)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('diag',type=Path)
    p.add_argument('guest',type=Path);p.add_argument('evidence',type=Path)
    p.add_argument('--post-portc',action='store_true',help='F1-E4: two qualified guest runs; no native campaign replay')
    args=p.parse_args();root=args.evidence.resolve();root.mkdir(parents=True,exist_ok=False)
    try:
        from d2_2_gpio_run import diag_path
        if not args.diag.is_absolute():raise ValueError('Explicit absolute DIAG path required')
        binary=diag_path(args.diag)
        if args.post_portc:
            if sha(binary)!=BINARY_SHA:raise ValueError('Qualified DIAG SHA required; no fallback')
            validate_qualified(args.guest)
            run(binary,args.guest,root/'run-1',post_portc=True)
            run(binary,args.guest,root/'run-2',post_portc=True)
            result=verify_e4_pair(root,args.guest)
            save(root/'result.json',result);print(json.dumps(result,indent=2))
            return 0 if result['status']=='REAL_PROGRESS_PASS_SCOPED' else 2
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
