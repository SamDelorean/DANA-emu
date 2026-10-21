#!/usr/bin/env python3
"""Run/verify two fresh real EmuTOS-Dana boots on an existing DIAG binary."""
import argparse
import hashlib
import json
import math
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

def lua(value):
    """Serialize observer configuration without Python bool/float identifiers."""
    if value is None:return 'nil'
    if isinstance(value,bool):return 'true' if value else 'false'
    if isinstance(value,(int,float)):
        if isinstance(value,float) and not math.isfinite(value):raise ValueError('Non-finite Lua configuration value')
        return repr(value)
    if isinstance(value,str):return json.dumps(value)
    if isinstance(value,list):return '{'+','.join(lua(v) for v in value)+'}'
    if isinstance(value,dict):return '{'+','.join('['+lua(k)+']='+lua(v) for k,v in value.items())+'}'
    raise TypeError(type(value))

def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')

BINARY_SHA='d7bcdf513289a73b8a5c7ab1d258eeac45dc8dd6d89dd7d568cf7784900e6fe5'
OLD_DRIVER_SHA='6bff19e0ae1e6c7a1f99a86fcfa2fbe235ac096c6624a10f6600fbd8851ddcf0'
OLD_PC=0x8392
TRACE_LIMIT=5*1024*1024
MAME_PIN='c4e48388ca620472643110db2941ce70aa5f3c07'


# Immutable 012-C artifact. A harness-only recovery must not relabel its build.
REUSE_012C = dict(source_commit='581601b49acb6603af2a100817d0f06fed17ed96',
    binary_sha256='caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37',
    qualification_sha256='6fda7a9474c7594ae1019fea33766ad65c99d9e81a5d323ec1e1f6b5ba914131',
    source_manifest_sha256='504530b8ba90549fc6cfd5dc7ec7505ff013ee025daceec9c60dc26a4e4988de')


def qualify_pfsel_build(binary,qualification,expected_source=None):
    """Read-only validation, with ordered predicates and pinned 012-C reuse.

    expected_source identifies the harness. The build source remains immutable.
    No arbitrary branch or hash substitution is accepted for a reused binary.
    """
    from d2_2_gpio_run import diag_path
    def require(predicate,condition):
        if not condition:raise ValueError('PFSEL_QUALIFICATION:'+predicate)
    require('binary.absolute_path',Path(binary).is_absolute())
    binary=diag_path(binary)
    require('qualification.regular_file',Path(qualification).is_file() and not Path(qualification).is_symlink())
    q=json.loads(Path(qualification).read_text())
    require('qualification.object',isinstance(q,dict))
    harness=expected_source or subprocess.check_output(['git','-C',str(PROJECT),'rev-parse','HEAD'],text=True).strip()
    source=q.get('source_commit')
    manifest_path=binary.parent.parent/'source-manifest.json'
    require('manifest.regular_file',manifest_path.is_file() and not manifest_path.is_symlink())
    manifest=json.loads(manifest_path.read_text())
    require('manifest.object',isinstance(manifest,dict))
    binary_sha=sha(binary);driver_sha=sha(PROJECT/'src/mame/skeleton/alphasdana.cpp')
    # Retain the original content checks in their original order. Report the
    # first failing predicate instead of the former ambiguous combined error.
    require('manifest.sha256',q.get('source_manifest_sha256')==sha(manifest_path))
    require('manifest.status',manifest.get('status')=='BUILT_DIAG')
    require('manifest.source_commit',manifest.get('source_commit')==source)
    require('manifest.mame_commit',manifest.get('mame_commit')==MAME_PIN)
    require('manifest.variant',manifest.get('variant')=='diag')
    require('manifest.binary_sha256',manifest.get('binary_sha256')==binary_sha)
    require('manifest.driver_sha256',manifest.get('driver_sha256')==driver_sha)
    require('qualification.schema',q.get('schema')=='dana-d23-build-v1')
    if source!=harness:
        for key,value in REUSE_012C.items():
            actual=sha(Path(qualification)) if key=='qualification_sha256' else q.get(key)
            require('reuse.'+key,actual==value)
        # Verify actual pinned Git bytes, not a claimed branch/source label.
        compiled=subprocess.check_output(['git','-C',str(PROJECT),'show',source+':src/mame/skeleton/alphasdana.cpp'])
        require('reuse.compiled_driver_sha256',hashlib.sha256(compiled).hexdigest()==driver_sha)
        require('reuse.production_tree',subprocess.check_output(
            ['git','-C',str(PROJECT),'diff','--name-only',source,harness,'--','src','overlays'],text=True).strip()=='')
    require('qualification.driver_sha256',q.get('driver_sha256')==driver_sha)
    require('qualification.mame_commit',q.get('mame_commit')==MAME_PIN)
    require('qualification.subtarget',q.get('subtarget')=='danadiag')
    require('qualification.build_exit_code',type(q.get('build_exit_code')) is int and q['build_exit_code']==0)
    require('qualification.variant',q.get('variant')=='diag')
    require('qualification.binary_sha256',q.get('binary_sha256')==binary_sha)
    require('qualification.new_binary',binary_sha!=BINARY_SHA)
    require('qualification.binary_path',q.get('binary')==str(binary))
    command=q.get('build_command',[])
    require('qualification.build_command',isinstance(command,list) and all(isinstance(v,str) for v in command)
        and {'make','-j3','SUBTARGET=danadiag','DEBUG=1','SOURCES=src/mame/skeleton/alphasdana.cpp'}.issubset(command))
    return q


def selected_bytes(event):
    """Independently decode the raw 16-bit, big-endian native tap lanes."""
    address,mask=event['address'],event['mask']
    if type(address) is not int or not 0<=address<=0xfffffffe or address%2 or mask not in (0xff00,0xff,0xffff):
        raise ValueError('Unsupported native bus shape')
    return [address+i for i,lane in enumerate((0xff00,0xff)) if mask & lane]


def implemented_byte(address,kind,pfsel=False,integrated_hardware=False):
    # Match only the individually decoded production addresses; no new device.
    return ((integrated_hardware and (0xfffff704<=address<=0xfffff70b
        or (kind=='read' and 0xfffff700<=address<=0xfffff701)
        or (kind=='write' and 0xfffff702<=address<=0xfffff703)))
        or 0xfffff202<=address<=0xfffff203 or address==0xfffff300
        or 0xfffff302<=address<=0xfffff307 or 0xfffff30c<=address<=0xfffff30f
        or (kind=='read' and 0xfffff310<=address<=0xfffff313)
        or address in (0xfffff412,0xfffff413) or (pfsel and address==0xfffff42b)
        or (pfsel and (0xfffff408<=address<=0xfffff40b or
          0xfffff418<=address<=0xfffff41b or
          0xfffff420<=address<=0xfffff423 or
          0xfffff428<=address<=0xfffff433 or
          0xfffff438<=address<=0xfffff43b or
          0xfffff440<=address<=0xfffff443 or
          0xfffff448<=address<=0xfffff44b or
          0xfffffa00<=address<=0xfffffa03 or
          address==0xfffffa05 or
          0xfffffa08<=address<=0xfffffa0b or
          0xfffffa20<=address<=0xfffffa21 or
          address==0xfffffa23 or
          address==0xfffffa25 or
          0xfffffa27<=address<=0xfffffa29 or
          address==0xfffffa2d or
          address==0xfffffa33 or
          0xfffffa36<=address<=0xfffffa37 or
          0xfffff800<=address<=0xfffff803 or
          0xfffff600<=address<=0xfffff60b or
          0xfffff900<=address<=0xfffff90b)))


def verify_e4(root,guest,expected_source=None,qualification=None):
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
        pfsel=qualification is not None
        revision='F1-E5' if pfsel else 'F1-E4'
        expected_binary=BINARY_SHA
        if pfsel:
            build=qualify_pfsel_build(Path(run['command'][0]),qualification,expected_source)
            expected_binary=build['binary_sha256']
            if build['source_commit']!=expected_source:
                if any(obj.get('build_source_commit')!=build['source_commit'] for obj in (run,obs)):
                    raise ValueError('Unbound immutable binary build source')
            if run.get('qualification_sha256')!=sha(Path(qualification)) or obs.get('qualification_sha256')!=sha(Path(qualification)):
                raise ValueError('Unbound PFSEL build qualification')
        if run.get('exit_code')!=0 or run.get('reason')=='HOST_TIMEOUT':raise ValueError('Native process incomplete')
        for key,value in (('revision',revision),('variant','diag'),('binary_sha256',expected_binary),
                          ('package_sha256',manifest['package']['sha256']),
                          ('image_sha256',manifest['artifacts']['emutos.img']['sha256'])):
            if run.get(key)!=value or obs.get(key)!=value:raise ValueError('Identity mismatch: '+key)
        if type(run.get('pid')) is not int or run['pid']<=0:raise ValueError('Missing native process ID')
        for key,pattern in (('source_commit',r'[0-9a-f]{40}'),('execution_id',r'[0-9a-f]{32}')):
            if not re.fullmatch(pattern,run.get(key,'')) or run[key]!=obs.get(key):
                raise ValueError('Unbound '+key)
        wanted_driver=sha(PROJECT/'src/mame/skeleton/alphasdana.cpp') if pfsel else OLD_DRIVER_SHA
        if run['source_commit']!=expected_source or run.get('driver_sha256')!=wanted_driver:
            raise ValueError('Wrong harness or production source identity')
        if obs.get('status')!='CAPTURED' or obs.get('schema')!=('dana-f1-e5-observation-v1' if pfsel else 'dana-f1-e4-observation-v1'):
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
                if address>=0x400000 and not implemented_byte(address,e['kind'],pfsel):missing.append((e,address))
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
        if pfsel:
            reads=[e for e in bus if e['address']==0xfffff42a and e['mask']==0xff
                   and e['kind']=='read' and e['state']['CURPC']==0x83a2]
            writes=[e for e in bus if e['address']==0xfffff42a and e['mask']==0xff
                    and e['kind']=='write' and e['state']['CURPC']==0x83a8]
            if (len(reads)!=1 or len(writes)!=1 or reads[0]['data'] & 255!=0xc5
                    or writes[0]['data'] & 255!=0xc5
                    or not crossing[0]['seq']<reads[0]['seq']<writes[0]['seq']<event['seq']
                    or not pcs.index(OLD_PC)<pcs.index(0x83a2)<pcs.index(0x83a8)<pcs.index(event['state']['CURPC'])):
                raise ValueError('Native PFSEL C5 read/ORI/write path not proved')
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


def verify_e4_pair(root,guest,expected_source=None,qualification=None):
    runs=[verify_e4(Path(root)/name,guest,expected_source,qualification) for name in ('run-1','run-2')]
    result={'status':'BLOCKED_HARNESS','scope':'F1-E4 two-run authentic post-Port-C continuation only',
            'full_boot':False,'runs':runs,'reason':'TWO_GENUINE_PROGRESS_OBSERVATIONS_REQUIRED'}
    if qualification:result['scope']='F1-E5 two-run authentic post-PFSEL continuation only'
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
        if qualification:result['reason']='PFSEL_C5_READ_WRITE_AND_NEW_DEPENDENCY_REPRODUCED'
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

def observation_limits():
    from dana_012e_verify import LIMITS
    resource.setrlimit(resource.RLIMIT_FSIZE,(LIMITS['max_file_bytes'],LIMITS['max_file_bytes']))

def run(binary,guest,root,reject=False,post_portc=False,qualification=None,observation_012e=False,integrated_hardware=False):
    from d2_2_gpio_run import diag_path
    if not Path(binary).is_absolute():raise ValueError('Explicit absolute DIAG path required')
    binary=diag_path(binary)
    if qualification:build=qualify_pfsel_build(binary,qualification)
    elif post_portc and sha(binary)!=BINARY_SHA:raise ValueError('Qualified DIAG SHA required; no fallback')
    manifest=(validate_qualified if post_portc else validate)(guest);syms=manifest['symbols'];root=Path(root).resolve()
    root.mkdir(parents=True,exist_ok=False)
    plugin=root/'plugin';plugin.mkdir();shutil.copyfile(HERE/'f1_emutos_boot.lua',plugin/'boot.lua')
    config={'output':str(root),'symbols':syms,'image_length':manifest['artifacts']['emutos.img']['size'],
            'package_sha256':manifest['package']['sha256'],'binary_sha256':sha(binary)}
    if post_portc:
        config.update(revision='F1-E4',variant='diag',execution_id=uuid.uuid4().hex,
                      source_commit=subprocess.check_output(['git','-C',str(PROJECT),'rev-parse','HEAD'],text=True).strip(),
                      image_sha256=manifest['artifacts']['emutos.img']['sha256'],full_boot=False)
        if qualification:config.update(revision='F1-E5',qualification_sha256=sha(Path(qualification)),build_source_commit=build['source_commit'])
        if qualification and build['source_commit']==REUSE_012C['source_commit']:config['integrated_recovery']=True
    if observation_012e:
        from dana_012e_verify import LIMITS,LIMITS_SHA,OBS_SHA,BOOT_SHA
        if not qualification or (not integrated_hardware and (build['source_commit']!=REUSE_012C['source_commit'] or build['binary_sha256']!=REUSE_012C['binary_sha256'])):
            raise ValueError('012-E requires exact reused 012-C DIAG')
        shutil.copyfile(HERE/'dana_012e_observer.lua',plugin/'dana_012e_observer.lua')
        config.update(observation_profile='012-E',observer_module=str(plugin/'dana_012e_observer.lua'),
                      observation_limits=LIMITS,limits_sha256=LIMITS_SHA,observer_sha256=OBS_SHA,boot_sha256=BOOT_SHA)
    if integrated_hardware:
        if not observation_012e or build['source_commit']!=config['source_commit'] or sha(binary)==REUSE_012C['binary_sha256']:
            raise ValueError('Integrated hardware requires a NEW same-source DIAG build')
        config['integrated_hardware']=True
    cfg=root/'config.lua';cfg.write_text('return '+lua(config)+'\n')
    environment=dict(os.environ,DANA_F1_CONFIG=str(cfg))
    image=Path(guest).resolve()/'emutos.dana'
    if reject:
        image=root/'corrupt.dana';payload=bytearray((Path(guest)/'emutos.dana').read_bytes());payload[-1]^=1
        image.write_bytes(payload)
    command=[str(binary),'asmdana','-noreadconfig','-quickload',str(image),
             '-debug','-debugger','none','-pluginspath',str(plugin),'-plugins','-video','none',
             '-sound','none','-log','-skip_gameinfo','-seconds_to_run','6']
    if observation_012e:command[-1]=str(LIMITS['emulator_seconds_to_run'])
    record={'binary_sha256':config['binary_sha256'],'command':command,
            'driver_sha256':sha(PROJECT/'src/mame/skeleton/alphasdana.cpp') if qualification else OLD_DRIVER_SHA,
            'package_sha256':config['package_sha256'],'host_timeout_seconds':180}
    if post_portc:
        record.update({k:config[k] for k in ('revision','variant','execution_id','source_commit','image_sha256','full_boot')})
        if qualification:record.update(qualification_sha256=config['qualification_sha256'],build_source_commit=build['source_commit'])
    if integrated_hardware:record['integrated_hardware']=True
    if observation_012e:
        record.update({k:config[k] for k in ('observation_profile','limits_sha256','observer_sha256','boot_sha256')})
        record['host_timeout_seconds']=LIMITS['host_timeout_seconds']
    try:
        with (root/'console.log').open('wb') as log:
            proc=subprocess.Popen(command,cwd=root,env=environment,stdout=log,stderr=subprocess.STDOUT,preexec_fn=observation_limits if observation_012e else limits)
            record['pid']=proc.pid
            try:record['exit_code']=proc.wait(timeout=LIMITS['host_timeout_seconds'] if observation_012e else 180)
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
    elif observation_012e:
        from dana_012e_verify import verify_run
        result=verify_run(root,guest,qualification)
    else:result=verify_e4(root,guest,qualification=qualification) if post_portc else verify(root,guest)
    save(root/'result.json',result)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('diag',type=Path)
    p.add_argument('guest',type=Path);p.add_argument('evidence',type=Path)
    p.add_argument('--post-portc',action='store_true',help='F1-E4: two qualified guest runs; no native campaign replay')
    p.add_argument('--pfsel-build',type=Path,help='F1-E5 only: new DIAG build qualification JSON')
    p.add_argument('--observation-012e',action='store_true',help='012-E bounded poll aggregation, native cycles and RTE evidence; exact 012-C reuse only')
    p.add_argument('--integrated-hardware',action='store_true',help='New same-source DIAG hardware build; preserve immutable 012-C reuse mode')
    args=p.parse_args();root=args.evidence.resolve();root.mkdir(parents=True,exist_ok=False)
    try:
        from d2_2_gpio_run import diag_path
        if not args.diag.is_absolute():raise ValueError('Explicit absolute DIAG path required')
        binary=diag_path(args.diag)
        if args.integrated_hardware and not (args.observation_012e and args.pfsel_build):raise ValueError('Integrated hardware requires bounded observation and build qualification')
        if args.observation_012e and not args.pfsel_build:raise ValueError('012-E requires original build qualification')
        if args.post_portc or args.pfsel_build:
            if args.pfsel_build:qualify_pfsel_build(binary,args.pfsel_build)
            elif sha(binary)!=BINARY_SHA:raise ValueError('Qualified DIAG SHA required; no fallback')
            validate_qualified(args.guest)
            run(binary,args.guest,root/'run-1',post_portc=True,qualification=args.pfsel_build,observation_012e=args.observation_012e,integrated_hardware=args.integrated_hardware)
            run(binary,args.guest,root/'run-2',post_portc=True,qualification=args.pfsel_build,observation_012e=args.observation_012e,integrated_hardware=args.integrated_hardware)
            if args.observation_012e:
                from dana_012e_verify import verify_pair
                result=verify_pair(root,args.guest,args.pfsel_build)
            else:result=verify_e4_pair(root,args.guest,qualification=args.pfsel_build)
            save(root/'result.json',result);print(json.dumps(result,indent=2))
            return 0 if result['status']=='REAL_PROGRESS_PASS_SCOPED' or args.observation_012e and result['status'] in ('PASS','PARTIAL') else 2
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
