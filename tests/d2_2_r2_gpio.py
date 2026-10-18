#!/usr/bin/env python3
"""R2 CPU-origin reset observation. Reuse qualified A unchanged; never emulate a CPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import uuid

import d2_2_gpio_run as qualified
from d1_2_run import lua
from f1_emutos_run import limits

HERE=Path(__file__).resolve().parent
BINARY_SHA='d7bcdf513289a73b8a5c7ab1d258eeac45dc8dd6d89dd7d568cf7784900e6fe5'
A_SHA='d2aa7123b85ee0bfeece050b88f2e801a7fd0cd8dc443791b8c1f821685052a9'
B_SHA='8cb8a9a943301f36a1bec27c9b0e1b7fc874e1642705926c1c156358096e0512'
MARKER,RESULT,SENTINEL=0x20000,0x20002,0xa55a
BODY,ENDPOINT,POST,STORE,STOP=0x4012,0x409e,0x40a2,0x40a8,0x40ae


def reset_fixture():
    original,_=qualified.fixture()
    if hashlib.sha256(original).hexdigest()!=A_SHA:raise ValueError('Qualified A fixture changed')
    # Bcc.w uses the extension-word address (4008), NOT the next opcode (400A).
    prefix=bytes.fromhex('4a79000200006600009a33fc000100020000')
    suffix=bytes.fromhex('3039fffff41233c0000200024e722700')
    data=prefix+original+suffix
    assert len(data)==178 and BODY+len(original)==POST
    assert 0x4008+struct.unpack('>h',data[8:10])[0]==POST
    assert hashlib.sha256(data).hexdigest()==B_SHA
    return data,ENDPOINT


class Incomplete(Exception):
    pass


def verify_reset(root):
    root=Path(root)
    try:
        run=json.loads((root/'run.json').read_text())
        obs=json.loads((root/'observation.json').read_text())
        qualified.staged_identity(run)
        for key,wanted in (('execution','reset'),('variant','diag'),('revision','R2'),
                           ('fixture_sha256',B_SHA),('binary_sha256',BINARY_SHA)):
            if run.get(key)!=wanted or obs.get(key)!=wanted:raise Incomplete('INVALID_'+key.upper())
        for key in ('source_commit','execution_id'):
            if not run.get(key) or run[key]!=obs.get(key):raise Incomplete('UNBOUND_'+key.upper())
        if not isinstance(run.get('pid'),int) or run['pid']<=0:raise Incomplete('MISSING_PROCESS_ID')
        if run.get('exit_code')!=0:raise Incomplete('NATIVE_PROCESS_EXIT_OR_TIMEOUT')
        if obs.get('status') not in ('PASS','CAPTURED'):
            return {'status':obs.get('status') if obs.get('status') in ('FAIL','BLOCKED') else 'BLOCKED',
                    'reason':obs.get('reason','INCOMPLETE_OBSERVATION')}
        events=obs['events']
        if not isinstance(events,list) or len(events)>256:raise Incomplete('EVENT_BUDGET')
        if [e.get('seq') for e in events]!=list(range(len(events))):raise Incomplete('MISSING_OR_DUPLICATE_RAW_SEQUENCE')
        if any(e.get('epoch') not in (0,1) for e in events):raise Incomplete('INVALID_RESET_EPOCH')
        def one(kind,origin,epoch,request):
            found=[e for e in events if e.get('kind')==kind]
            if len(found)!=1:raise Incomplete('MISSING_OR_DUPLICATE_'+kind.upper())
            e=found[0]
            if (e.get('origin'),e.get('epoch'),e.get('request_id'))!=(origin,epoch,request):
                raise Incomplete('UNBOUND_'+kind.upper())
            return e
        def cpu(epoch,kind,address):
            return [e for e in events if e.get('origin')=='cpu' and e.get('epoch')==epoch
                    and e.get('kind')==kind and e.get('address')==address]
        def exactly(values,description):
            if len(values)!=1:raise Incomplete('MISSING_OR_DUPLICATE_'+description)
            return values[0]
        def vector(epoch,request):
            v=[e for e in events if e.get('origin')=='cpu' and e.get('epoch')==epoch
               and e.get('kind')=='read' and e.get('address',8)<8]
            if [(e['address'],e['data'],e['mask'],e['request_id']) for e in v]!=[
                (0,0,65535,request),(2,0x8000,65535,request),(4,0,65535,request),(6,0x4000,65535,request)]:
                raise Incomplete('MISSING_DUPLICATE_OR_INCORRECT_NATIVE_VECTORS')
            return v
        first=one('profile_initial','host_observation',0,0)
        end=one('fixture_complete','host_observation',0,0)
        request=one('reset_request','host_request',0,1)
        transition=one('reset_transition','native_notification',1,1)
        complete=one('cpu_reset_complete','host_observation',1,1)
        before=vector(0,0);after=vector(1,1)
        if first.get('value')!=0 or first.get('pc')!=0x4000 or first.get('sp')!=0x8000:
            raise Incomplete('INITIAL_PROFILE_OR_ENTRY')
        if (end.get('value'),end.get('pc'),end.get('sp'))!=(0xfe81,ENDPOINT,0x8000):
            raise Incomplete('FIRST_BOOT_FE81_NOT_PROVED')
        if request.get('api')!='soft_reset' or transition.get('point')!='before_device_reset':
            raise Incomplete('RESET_API_NOT_BOUND')
        if request.get('value')!=0xfe81 or transition.get('value')!=0xfe81:
            raise Incomplete('PRE_RESET_FE81_NOT_PROVED')
        if not before[-1]['seq']<first['seq']<end['seq']<request['seq']<transition['seq']<after[0]['seq']:
            raise Incomplete('RESET_CHAIN_ORDER')
        # CPU marker operations, not host bootstrap writes, prove the branch decision.
        marker0=exactly(cpu(0,'read',MARKER),'INITIAL_CPU_MARKER_READ')
        mark=exactly(cpu(0,'write',MARKER),'CPU_MARKER_WRITE')
        marker1=exactly(cpu(1,'read',MARKER),'POST_RESET_CPU_MARKER_READ')
        for e,value,pc,rid in ((marker0,0,0x4000,0),(mark,1,0x400a,0),(marker1,1,0x4000,1)):
            if (e.get('data'),e.get('mask'),e.get('pc'),e.get('request_id'))!=(value,0xffff,pc,rid):
                raise Incomplete('CPU_MARKER_VALUE_OR_ORIGIN_MISMATCH')
        if not first['seq']<marker0['seq']<mark['seq']<end['seq']:
            raise Incomplete('INITIAL_MARKER_ORDER')
        if any(e.get('origin')=='cpu' and e.get('kind')=='write' and e.get('address')==MARKER
               and e['seq']>mark['seq'] for e in events):raise Incomplete('LOST_MARKER_OR_FIXTURE_REPLAY')
        original_writes=[(0xfffff412,0xff00,0x5500),(0xfffff412,0xff,0xaa),(0xfffff412,0xffff,0x1234),
            (0xfffff412,0xff00,0xfe00),(0xfffff412,0xff,0x81),(0xfff412,0xff00,0),
            (0xfff412,0xff,0),(0xfffff410,0xff00,0),(0xfffff410,0xff,0),(0xfffff414,0xff00,0)]
        bus0=[e for e in events if e.get('origin')=='cpu' and e['epoch']==0 and e.get('address',0)>=0x400000]
        if any(not mark['seq']<e['seq']<end['seq'] or e['request_id']!=0 for e in bus0):
            raise Incomplete('FIRST_BOOT_MMIO_ORDER')
        if [(e['address'],e['mask'],e['data'] & e['mask']) for e in bus0 if e['kind']=='write']!=original_writes:
            raise Incomplete('FIRST_BOOT_NATIVE_LANES_ALIASES_OR_DUPLICATES')
        if [e['data'] for e in bus0 if e['kind']=='read' and e['address']==0xfffff412 and e['mask']==0xffff]!=[
                0x55aa,0x1234,0xfe34,0xfe81,0xfe81]:raise Incomplete('FIRST_BOOT_READBACK')
        # After the transition there must be one and only one MMIO transaction.
        # A write, a replay or a duplicate is not reduced to an invented read.
        bus1=[e for e in events if e.get('origin')=='cpu' and e['epoch']==1 and e.get('address',0)>=0x400000]
        read=exactly(bus1,'POST_RESET_MMIO_READ')
        if (read.get('kind'),read.get('address'),read.get('mask'),read.get('pc'),read.get('request_id'))!=(
            'read',0xfffff412,0xffff,POST,1):raise Incomplete('POST_RESET_WRITE_REPLAY_OR_FAKE_READ')
        result=exactly(cpu(1,'write',RESULT),'CPU_RESULT_STORE')
        if (result.get('mask'),result.get('pc'),result.get('request_id'))!=(0xffff,STORE,1):
            raise Incomplete('INVALID_CPU_RESULT_STORE')
        if any(e.get('origin')=='cpu' and e.get('address')==RESULT and e is not result for e in events):
            raise Incomplete('EARLY_DUPLICATE_OR_STALE_RESULT_STORE')
        if not after[-1]['seq']<marker1['seq']<read['seq']<result['seq']<complete['seq']:
            raise Incomplete('CPU_POST_RESET_OBSERVATION_ORDER')
        if [e for e in events if e.get('origin')=='cpu' and e['epoch']==1]!=after+[marker1,read,result]:
            raise Incomplete('EXTRA_OR_AMBIGUOUS_POST_RESET_CPU_OBSERVATIONS')
        if read['data']!=result['data']:raise Incomplete('CONTRADICTORY_CPU_READ_AND_STORE')
        data,_=reset_fixture()
        initial=(root/'initial.ram').read_bytes();final=(root/'final.ram').read_bytes();reset=(root/'reset.ram').read_bytes()
        seed=bytearray(0x400000);seed[:8]=struct.pack('>II',0x8000,0x4000)
        seed[0x4000:0x4000+len(data)]=data;seed[0x10010:0x10012]=bytes.fromhex('cafe')
        seed[RESULT:RESULT+2]=struct.pack('>H',SENTINEL)
        if initial!=seed:raise Incomplete('INITIAL_RAM_FIXTURE_MARKER_OR_SENTINEL')
        expected=bytearray(seed);expected[0x10000:0x1000a]=bytes.fromhex('55aa1234fe34fe81fe81')
        expected[MARKER:MARKER+2]=b'\x00\x01'
        if final!=expected:raise Incomplete('FIRST_BOOT_RAM_MARKER_SENTINEL_OR_CORRUPTION')
        expected[RESULT:RESULT+2]=struct.pack('>H',result['data'])
        if reset!=expected:raise Incomplete('RESET_RAM_RESULT_MARKER_OR_CORRUPTION')
        if (complete.get('marker'),complete.get('result'))!=(1,result['data']):raise Incomplete('RAM_OBSERVATION_CONTRADICTION')
        if complete.get('next_pc')!=STOP+4 or complete.get('sp')!=0x8000 or complete.get('sr')!=0x2700:
            raise Incomplete('NATIVE_STOP_STATE_NOT_PROVED')
        pcs=[int(v,16) for v in re.findall(r'^\s*([0-9a-fA-F]+):',(root/'cpu.trace').read_text(),re.M)]
        if pcs.count(0x4000)!=2 or pcs.count(BODY)!=1:raise Incomplete('MISSING_OR_REPLAYED_NATIVE_INSTRUCTIONS')
        second=pcs[pcs.index(0x4000,pcs.index(0x4000)+1):]
        if second[:5]!=[0x4000,0x4006,POST,STORE,STOP] or any(BODY<=pc<=ENDPOINT for pc in second):
            raise Incomplete('POST_RESET_BRANCH_OR_FIXTURE_REPLAY')
        if read['data']!=0:
            return {'status':'FAIL','reason':'CONFIRMED_CPU_POST_RESET_PORTC_NONZERO','value':read['data']}
        return {'status':'PASS','scope':'CPU-origin R-direct reset observation only','binary':run['command'][0],
            **{k:run[k] for k in ('binary_sha256','source_commit','fixture_sha256','pid','execution_id')},
            'post_reset_value':read['data'],'marker':1,'sentinel':SENTINEL}
    except (FileNotFoundError,Incomplete) as exc:return {'status':'BLOCKED','reason':str(exc)}
    except (OSError,ValueError,KeyError,TypeError,IndexError,struct.error) as exc:
        return {'status':'BLOCKED','reason':'INVALID_OR_CONTRADICTORY_EVIDENCE: '+str(exc)}


def verify(root):
    root=Path(root)
    a=qualified.verify_execution(root/'save_restore','save_restore')
    b=verify_reset(root/'reset');results={'save_restore':a,'reset':b}
    statuses=[a['status'],b['status']]
    status='FAIL' if 'FAIL' in statuses else 'BLOCKED' if 'BLOCKED' in statuses else 'PASS'
    reason='INDEPENDENT_NATIVE_QUALIFICATION_INCOMPLETE'
    if status=='PASS':
        if a['pid']==b['pid'] or a['execution_id']==b['execution_id']:
            status='BLOCKED';reason='TWO_INDEPENDENT_PROCESSES_NOT_PROVED'
        elif any(a[k]!=b[k] for k in ('binary','binary_sha256','source_commit')) or a['binary_sha256']!=BINARY_SHA:
            status='BLOCKED';reason='INCONSISTENT_OR_UNQUALIFIED_DIAG_IDENTITY'
        else:reason='BOTH_INDEPENDENT_EXECUTIONS_VERIFIED_CPU_RESET_R2'
    return {'status':status,'reason':reason,'revision':'R2','executions':results}


def execute_reset(binary,root,source):
    root.mkdir();payload,endpoint=reset_fixture()
    plugin=root/'plugin';plugin.mkdir();shutil.copyfile(HERE/'d2_2_reset_r2_boot.lua',plugin/'boot.lua')
    config={'output':str(root),'hex':payload.hex(),'endpoint':endpoint,'stop_pc':STOP,'execution':'reset',
            'revision':'R2','execution_id':uuid.uuid4().hex,'source_commit':source,
            'binary_sha256':qualified.digest(binary),'fixture_sha256':B_SHA}
    cfg=root/'config.lua';cfg.write_text('return '+lua(config)+'\n')
    command=[str(binary),'asmdana','-noreadconfig','-debug','-debugger','none','-pluginspath',str(plugin),
             '-plugins','-video','none','-sound','none','-nothrottle','-skip_gameinfo','-seconds_to_run','2']
    record={k:config[k] for k in ('execution','revision','execution_id','source_commit','binary_sha256','fixture_sha256')}
    record.update(command=command,variant='diag',host_timeout_seconds=90)
    if qualified.digest(binary)!=BINARY_SHA:raise ValueError('Qualified DIAG hash required')
    with (root/'console.log').open('wb') as log:
        proc=subprocess.Popen(command,cwd=root,env=dict(os.environ,DANA_PORTC_CONFIG=str(cfg)),stdout=log,
                              stderr=subprocess.STDOUT,preexec_fn=limits)
        record['pid']=proc.pid
        try:record['exit_code']=proc.wait(timeout=90)
        except subprocess.TimeoutExpired:proc.kill();proc.wait();record.update(exit_code=None,reason='HOST_TIMEOUT')
    (root/'run.json').write_text(json.dumps(record,indent=2)+'\n')
    (root/'result.json').write_text(json.dumps(verify_reset(root),indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('diag',type=Path);parser.add_argument('evidence',type=Path)
    args=parser.parse_args();root=args.evidence.resolve();root.mkdir(parents=True,exist_ok=False)
    try:
        binary=qualified.diag_path(args.diag)
        if qualified.digest(binary)!=BINARY_SHA:raise ValueError('Qualified DIAG hash required; no fallback')
        source=subprocess.check_output(['git','-C',str(HERE.parent),'rev-parse','HEAD'],text=True).strip()
        qualified.execute(binary,root/'save_restore','save_restore',source)
        execute_reset(binary,root/'reset',source)
        result=verify(root)
    except (OSError,ValueError,subprocess.SubprocessError) as exc:result={'status':'BLOCKED','reason':str(exc)}
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return {'PASS':0,'FAIL':1,'BLOCKED':2}[result['status']]


if __name__=='__main__':sys.exit(main())
