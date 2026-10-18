#!/usr/bin/env python3
"""Bounded Port C native DIAG fixture; no guest, reference emulator or ROM build."""
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

from d1_2_run import lua
from f1_emutos_run import limits

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def diag_path(path):
    path = Path(path).absolute()
    # Resolve identity before invoking anything. No CLI probe of an arbitrary emulator.
    if path.name != 'dana-diag' or path.parent.name != 'bin' or path.parent.parent.name != 'diag':
        raise ValueError('BLOCKED_DIAG_STAGING_PATH_REQUIRED')
    if path.resolve()!=path or path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError('BLOCKED_STAGED_DIAG_EXECUTABLE_MISSING')
    return path


def fixture():
    data = bytearray()
    def byte(value, addr):
        data.extend(struct.pack('>HHI', 0x13fc, value, addr))
    def snapshot(offset):
        data.extend(bytes.fromhex('3039fffff412'))  # MOVE.W absolute,D0
        data.extend(struct.pack('>HI', 0x33c0, 0x10000+offset))
    byte(0x55, 0xfffff412); byte(0xaa, 0xfffff413); snapshot(0)
    data.extend(bytes.fromhex('33fc1234fffff412')); snapshot(2)
    byte(0xfe, 0xfffff412); snapshot(4)
    byte(0x81, 0xfffff413); snapshot(6)
    for addr in (0x00fff412, 0x00fff413, 0xfffff410, 0xfffff411, 0xfffff414):
        byte(0, addr)
    snapshot(8)
    endpoint = 0x4000+len(data)
    data.extend(bytes.fromhex('4e722700'))
    return bytes(data), endpoint



class MissingEvidence(Exception):
    """Incomplete/ambiguous observation is BLOCKED, never inferred PASS."""


def staged_identity(record):
    path = Path(record['command'][0])
    if (not path.is_absolute() or '..' in path.parts or path.name!='dana-diag' or
        path.parent.name!='bin' or path.parent.parent.name!='diag' or record.get('variant')!='diag'):
        raise ValueError('Non-DIAG execution identity')
    if 'asmdana' not in record['command']:
        raise ValueError('Missing internal Dana machine selector')
    for name, size in (('binary_sha256',64),('source_commit',40)):
        if not re.fullmatch('[0-9a-f]{'+str(size)+'}',record.get(name,'')):
            raise ValueError('Invalid '+name)


def verify_execution(root, execution='save_restore'):
    root = Path(root)
    try:
        record = json.loads((root/'run.json').read_text())
        obs = json.loads((root/'observation.json').read_text())
        staged_identity(record)
        payload, endpoint = fixture()
        wanted = hashlib.sha256(payload).hexdigest()
        if execution not in ('save_restore','reset'):
            raise ValueError('Invalid execution variant')
        for key, expected in (('execution',execution),('variant','diag'),('fixture_sha256',wanted)):
            if record.get(key)!=expected or obs.get(key)!=expected:
                raise ValueError('Invalid '+key+' identity')
        for key in ('binary_sha256','source_commit','execution_id'):
            if obs.get(key)!=record.get(key) or not record.get(key):
                raise ValueError('Observation '+key+' identity mismatch')
        if not isinstance(record.get('pid'),int) or record['pid']<=0:
            raise ValueError('Missing process identity')
        if record['exit_code']!=0:
            raise MissingEvidence('NATIVE_PROCESS_EXIT_OR_TIMEOUT')
        if obs['status'] not in ('PASS','FAIL','BLOCKED'):
            raise ValueError('Invalid observation verdict')
        if obs['status']!='PASS':
            return {'status':obs['status'],'reason':obs['reason']}
        events = obs['events']
        if not isinstance(events,list) or len(events)>256:
            raise MissingEvidence('INCOMPLETE_OR_OVER_BUDGET_EVENTS')
        seqs=[e['seq'] for e in events]
        if len(set(seqs))!=len(seqs):
            raise MissingEvidence('DUPLICATE_OBSERVATIONS; raw events retained, no deduplication')
        if seqs!=list(range(len(events))):
            raise MissingEvidence('INCOMPLETE_EVENT_SEQUENCE')
        def one(kind,origin,epoch=0,request=0):
            found=[e for e in events if e['kind']==kind]
            if len(found)!=1:
                raise MissingEvidence('MISSING_OR_DUPLICATE_'+kind.upper())
            e=found[0]
            if (e.get('origin'),e.get('epoch'),e.get('request_id'))!=(origin,epoch,request):
                raise MissingEvidence('UNBOUND_'+kind.upper())
            return e
        def vectors(epoch,request):
            found=[e for e in events if e['kind']=='read' and e.get('origin')=='cpu'
                   and e['epoch']==epoch and e['address']<8]
            expected=[(0,0),(2,0x8000),(4,0),(6,0x4000)]
            if any(e.get('request_id')!=request or e.get('mask')!=0xffff for e in found):
                raise MissingEvidence('UNBOUND_NATIVE_VECTORS')
            actual=[(e['address'],e['data']) for e in found]
            if actual!=expected:
                # Do not turn repeated callbacks into an invented reset sequence.
                if len(actual)==4 and [a for a,d in actual]==[a for a,d in expected]:
                    raise ValueError('Confirmed incorrect native reset vector values')
                raise MissingEvidence('MISSING_OR_AMBIGUOUS_NATIVE_VECTOR_SEQUENCE')
            return found
        initial = (root/'initial.ram').read_bytes()
        final = (root/'final.ram').read_bytes()
        if len(initial)!=0x400000 or len(final)!=0x400000:
            raise MissingEvidence('INCOMPLETE_RAM_EVIDENCE')
        seed=bytearray(0x400000);seed[:8]=struct.pack('>II',0x8000,0x4000)
        seed[0x4000:0x4000+len(payload)]=payload;seed[0x10010:0x10012]=bytes.fromhex('cafe')
        if initial!=seed:
            raise ValueError('Fixture code/baseline identity mismatch')
        expected=bytearray(initial);expected[0x10000:0x1000a]=bytes.fromhex('55aa1234fe34fe81fe81')
        if final!=expected:
            raise ValueError('NATIVE_LANES_ALIAS_OR_RAM_CORRUPTION')
        start=one('profile_initial','host_observation')
        complete=one('fixture_complete','host_observation')
        if (start['value'],start['pc'],start['sp'])!=(0,0x4000,0x8000):
            raise ValueError('Incorrect native initial profile/entry')
        if (complete['value'],complete['pc'],complete['sp'])!=(0xfe81,endpoint,0x8000):
            raise ValueError('Incorrect fixture endpoint/stack/Port C')
        initial_vectors=vectors(0,0)
        if not initial_vectors[-1]['seq']<start['seq']<complete['seq']:
            raise MissingEvidence('INCORRECT_STARTUP_EVENT_ORDER')
        bus=[e for e in events if e.get('origin')=='cpu' and e['epoch']==0 and e['address']>=0x400000]
        if any(not start['seq']<e['seq']<complete['seq'] for e in bus):
            raise MissingEvidence('CPU_ACTIVITY_OUTSIDE_FIXTURE')
        expected_writes=[(0xfffff412,0xff00,0x5500),(0xfffff412,0xff,0xaa),
            (0xfffff412,0xffff,0x1234),(0xfffff412,0xff00,0xfe00),(0xfffff412,0xff,0x81),
            (0xfff412,0xff00,0),(0xfff412,0xff,0),(0xfffff410,0xff00,0),
            (0xfffff410,0xff,0),(0xfffff414,0xff00,0)]
        writes=[(e['address'],e['mask'],e['data'] & e['mask']) for e in bus if e['kind']=='write']
        if len(writes)>len(expected_writes):
            raise MissingEvidence('AMBIGUOUS_DUPLICATED_NATIVE_WRITES')
        if writes!=expected_writes:
            raise ValueError('Missing/duplicate CPU-origin lane or alias transaction')
        reads=[e['data'] for e in bus if e['kind']=='read' and e['address']==0xfffff412 and e['mask']==0xffff]
        if len(reads)>5:
            raise MissingEvidence('AMBIGUOUS_DUPLICATED_NATIVE_READS')
        if reads!=[0x55aa,0x1234,0xfe34,0xfe81,0xfe81]:
            raise ValueError('Missing/duplicate native MMIO readback')
        trace=(root/'cpu.trace').read_text()
        pcs={int(pc,16) for pc in re.findall(r'^\s*([0-9a-fA-F]+):',trace,re.M)}
        if not {0x4000,endpoint-6}<=pcs:
            raise MissingEvidence('MISSING_NATIVE_INSTRUCTION_EVIDENCE')
        if execution=='save_restore':
            if any(e['kind'].startswith('reset_') or e['kind']=='profile_reset' for e in events):
                raise ValueError('Save/restore process attempted reset')
            saved=one('state_saved','host_observation')
            mutated=one('state_mutated','host_request')
            restored=one('state_restored','host_observation')
            if not complete['seq']<saved['seq']<mutated['seq']<restored['seq']:
                raise MissingEvidence('UNORDERED_SAVE_RESTORE')
            if (saved['value'],mutated['value'],restored['value'])!=(0xfe81,0xcdef,0xfe81):
                raise ValueError('NATIVE_SAVE_MUTATION_OR_RESTORE_VALUE')
            if saved.get('bytes',0)<=0 or restored.get('load_ok') is not True:
                raise MissingEvidence('SAVE_OR_LOAD_NOT_CONFIRMED')
            if (root/'restored.ram').read_bytes()!=final:
                raise ValueError('SAVE_RESTORE_RAM_CORRUPTION')
            if any(e.get('origin')=='cpu' and e['seq']>saved['seq'] for e in events):
                raise MissingEvidence('POST_LOAD_CPU_REPLAY')
        else:
            if any(e['kind'].startswith('state_') for e in events):
                raise ValueError('Reset process used save/load')
            request=one('reset_request','host_request',0,1)
            transition=one('reset_transition','native_notification',1,1)
            post=one('profile_reset','native_notification',1,1)
            entry=one('reset_entry','host_observation',1,1)
            after=vectors(1,1)
            if not (complete['seq']<request['seq']<transition['seq']<post['seq']<
                    after[0]['seq']<=after[-1]['seq']<entry['seq']):
                raise MissingEvidence('UNORDERED_NATIVE_RESET_CHAIN')
            if request.get('api')!='soft_reset' or transition.get('point')!='before_device_reset' or post.get('point')!='after_device_reset':
                raise MissingEvidence('UNBOUND_NATIVE_RESET_API')
            if request['value']!=0xfe81 or transition['value']!=0xfe81:
                raise MissingEvidence('PRE_RESET_FE81_NOT_PROVED')
            if post['value']!=0 or entry['value']!=0:
                raise ValueError('CONFIRMED_INCORRECT_POST_RESET_PORTC')
            if entry['pc']!=0x4000 or entry['sp']!=0x8000 or entry['sr'] & 0xa700 != 0x2700:
                raise ValueError('CONFIRMED_INCORRECT_POST_RESET_CPU_STATE')
            if any(e.get('origin')=='cpu' and e['epoch']==1 and e['address']>=0x400000 for e in events):
                raise MissingEvidence('POST_RESET_FIXTURE_REPLAY')
            if (root/'reset.ram').read_bytes()!=final:
                raise ValueError('RESET_RAM_CORRUPTION_OR_RESEED')
        return {'status':'PASS','scope':'Native R-direct Port C '+execution,
                'binary_sha256':record['binary_sha256'],'binary':record['command'][0],
                'fixture_sha256':wanted,'source_commit':record['source_commit'],
                'execution_id':record['execution_id'],'pid':record['pid'],
                'physical_reset':'MOTOROLA_0xFF; R_DIRECT_SOFTWARE_PROFILE_0x00'}
    except (FileNotFoundError,MissingEvidence) as error:
        return {'status':'BLOCKED','reason':str(error)}
    except (OSError,ValueError,KeyError,TypeError) as error:
        return {'status':'FAIL','reason':str(error)}


def verify(root):
    results={mode:verify_execution(Path(root)/mode,mode) for mode in ('save_restore','reset')}
    statuses=[r['status'] for r in results.values()]
    status='FAIL' if 'FAIL' in statuses else 'BLOCKED' if 'BLOCKED' in statuses else 'PASS'
    if status=='PASS':
        a,b=results.values()
        if a['pid']==b['pid'] or a['execution_id']==b['execution_id']:
            status='BLOCKED';reason='TWO_INDEPENDENT_PROCESSES_NOT_PROVED'
        elif any(a[k]!=b[k] for k in ('binary','binary_sha256','source_commit','fixture_sha256')):
            status='FAIL';reason='INCONSISTENT_TWO_PROCESS_IDENTITIES'
        else:reason='BOTH_INDEPENDENT_NATIVE_EXECUTIONS_VERIFIED'
    else:reason='INDEPENDENT_NATIVE_QUALIFICATION_INCOMPLETE'
    return {'status':status,'reason':reason,'executions':results}


def execute(binary, root, mode, source_commit):
    root.mkdir()
    payload,endpoint=fixture()
    plugin=root/'plugin';plugin.mkdir()
    shutil.copyfile(HERE/'d2_2_gpio_boot.lua',plugin/'boot.lua')
    config={'output':str(root),'hex':payload.hex(),'endpoint':endpoint,'execution':mode,
            'execution_id':uuid.uuid4().hex,'source_commit':source_commit,
            'binary_sha256':digest(binary),'fixture_sha256':hashlib.sha256(payload).hexdigest()}
    cfg=root/'config.lua';cfg.write_text('return '+lua(config)+'\n')
    command=[str(binary),'asmdana','-noreadconfig','-debug','-debugger','none',
             '-pluginspath',str(plugin),'-plugins','-video','none','-sound','none',
             '-nothrottle','-skip_gameinfo','-seconds_to_run','2']
    record={k:config[k] for k in ('execution','execution_id','source_commit','binary_sha256','fixture_sha256')}
    record.update(command=command,variant='diag',host_timeout_seconds=90)
    # Check again before each process. A replaced binary may not inherit prior identity.
    if digest(binary)!=config['binary_sha256']:raise ValueError('DIAG binary changed')
    with (root/'console.log').open('wb') as log:
        proc=subprocess.Popen(command,cwd=root,env=dict(os.environ,DANA_PORTC_CONFIG=str(cfg)),
                              stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits)
        record['pid']=proc.pid
        try:record['exit_code']=proc.wait(timeout=90)
        except subprocess.TimeoutExpired:
            proc.kill();proc.wait();record.update(exit_code=None,reason='HOST_TIMEOUT')
    (root/'run.json').write_text(json.dumps(record,indent=2)+'\n')
    result=verify_execution(root,mode)
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('diag',type=Path);parser.add_argument('evidence',type=Path)
    args=parser.parse_args();root=args.evidence.resolve();root.mkdir(parents=True,exist_ok=False)
    try:
        binary=diag_path(args.diag)
        source=subprocess.check_output(['git','-C',str(HERE.parent),'rev-parse','HEAD'],text=True).strip()
        expected_binary=digest(binary)
        for mode in ('save_restore','reset'):
            if digest(binary)!=expected_binary:raise ValueError('DIAG binary changed between processes')
            execute(binary,root/mode,mode,source)
        result=verify(root)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        result={'status':'BLOCKED','reason':str(error)}
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return {'PASS':0,'FAIL':1,'BLOCKED':2}[result['status']]


if __name__=='__main__':
    # R2 changes B only; qualified.execute and its A Lua/fixture/verifier stay intact.
    from d2_2_r2_gpio import main as r2_main
    sys.exit(r2_main())
