#!/usr/bin/env python3
"""PFSEL-only native qualification on ONE newly source-qualified dana-diag.

No CPU emulation. The fixture builder emits test-owned M68000 instructions.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import uuid

from d1_2_run import lua
from f1_emutos_run import qualify_pfsel_build,limits,sha

HERE=Path(__file__).resolve().parent
PFSEL=0xfffff42b
MARKER,RESULT=0x20000,0x20002


def fixture():
    data=bytearray.fromhex('4a79000200006600000033fc000100020000')
    expected=[];snapshots=[]
    def emit(code):
        pc=0x4000+len(data);data.extend(bytes.fromhex(code));return pc
    def write(address,value,word=False):
        pc=emit(('33fc%04x%08x' if word else '13fc%04x%08x')%(value,address))
        expected.append(dict(kind='write',address=address & ~1,mask=65535 if word else 255 if address&1 else 65280,
                             value=value if word or address&1 else value<<8,pc=pc))
    def read(value,word=False,address=PFSEL,store=True):
        emit('7000') # MOVEQ #0,D0: byte load must not inherit upper D0 bits.
        pc=emit(('3039' if word else '1039')+'%08x'%address)
        expected.append(dict(kind='read',address=address & ~1,mask=65535 if word else 255 if address&1 else 65280,
                             value=value,pc=pc))
        if store:
            dest=0x10000+2*len(snapshots);store_pc=emit('33c0%08x'%dest)
            snapshots.append(dict(address=dest,read_pc=pc,store_pc=store_pc,value=value))
    read(0xc5)
    for value in (0,1,0x80,0xff):write(PFSEL,value);read(value);read(value)
    write(PFSEL-1,0x7e);read(0xff) # high PFPUEN lane must not hit PFSEL
    read(None,address=PFSEL-1,store=False)
    write(PFSEL-1,0x12a5,True);read(None,word=True,address=PFSEL-1) # even word address
    write(0x00fff42b,0);read(0xa5) # no 24-bit alias
    write(PFSEL,0x5a);read(0x5a)
    endpoint=emit('4e722700')
    post=emit('7000');post_read=emit('1039fffff42b');store=emit('33c000020002');stop=emit('4e722700')
    data[8:10]=struct.pack('>h',post-0x4008)
    return bytes(data),dict(endpoint=endpoint,post=post,post_read=post_read,store=store,stop=stop,
                           expected=expected,snapshots=snapshots)


def verify(root,binary,qualification,mode):
    root=Path(root)
    try:
        q=qualify_pfsel_build(binary,qualification)
        run=json.loads((root/'run.json').read_text());obs=json.loads((root/'observation.json').read_text())
        payload,layout=fixture();digest=hashlib.sha256(payload).hexdigest()
        harness=subprocess.check_output(['git','-C',str(HERE.parent),'rev-parse','HEAD'],text=True).strip()
        if q['source_commit']!=harness and any(obj.get('build_source_commit')!=q['source_commit'] for obj in (run,obs)):
            raise ValueError('Unbound immutable binary build source')
        for key,value in (('variant','diag'),('revision','D2.3'),('execution',mode),('fixture_sha256',digest),
                          ('binary_sha256',q['binary_sha256']),('source_commit',harness),
                          ('qualification_sha256',sha(Path(qualification)))):
            if run.get(key)!=value or obs.get(key)!=value:raise ValueError('Unbound '+key)
        if run['command'][0]!=str(binary) or run.get('exit_code')!=0 or type(run.get('pid')) is not int or run['pid']<=0:
            raise ValueError('Missing native process identity')
        if not re.fullmatch('[0-9a-f]{32}',run.get('execution_id','')) or obs.get('execution_id')!=run['execution_id']:
            raise ValueError('Unbound execution ID')
        if obs.get('status')!='CAPTURED':raise ValueError(obs.get('reason','No capture'))
        events=obs['events']
        if not isinstance(events,list) or len(events)>256 or [e['seq'] for e in events]!=list(range(len(events))):
            raise ValueError('Missing/duplicate/budget events')
        def one(kind):
            found=[e for e in events if e['kind']==kind]
            if len(found)!=1:raise ValueError('Missing/duplicate '+kind)
            return found[0]
        def vectors(epoch):
            rows=[e for e in events if e['origin']=='cpu' and e['epoch']==epoch and e.get('address',8)<8]
            if [(e['kind'],e['address'],e['data'],e['mask'],e['request_id']) for e in rows]!=[
                    ('read',0,0,65535,epoch),('read',2,0x8000,65535,epoch),
                    ('read',4,0,65535,epoch),('read',6,0x4000,65535,epoch)]:raise ValueError('Native vectors')
            return rows
        initial_vectors=vectors(0)
        cpu=[e for e in events if e['origin']=='cpu']
        if any(e.get('tap_id')!='pfsel_'+e['kind'] for e in cpu):raise ValueError('Forged CPU origin')
        if any(e.get('epoch') not in (0,1) or e.get('request_id')!=e['epoch'] for e in cpu):raise ValueError('Unbound CPU reset epoch/request')
        bus=[e for e in cpu if e['epoch']==0 and e.get('address',0)>=0x400000]
        if len(bus)!=len(layout['expected']):raise ValueError('Native bus transaction count')
        bad=False
        for event,wanted in zip(bus,layout['expected']):
            if any(event.get(k)!=wanted[k] for k in ('kind','address','mask','pc')) or event['request_id']!=0:
                raise ValueError('Native lane/order/address mismatch')
            if wanted['value'] is not None and event['data'] & event['mask']!=wanted['value']:bad=True
            if wanted['value'] is None and wanted['kind']=='read' and wanted['mask']==65535 and event['data'] & 255!=0xa5:bad=True
        begin=one('profile_initial');end=one('fixture_complete')
        if (begin['origin'],begin['value'],begin['pc'],begin['sp'])!=('host_observation',0xc5,0x4000,0x8000):
            raise ValueError('Initial R-direct profile')
        if (end['origin'],end['pc'],end['sp'],end['value'])!=('host_observation',layout['endpoint'],0x8000,0x5a):bad=True
        seed=bytearray(0x400000);seed[:8]=struct.pack('>II',0x8000,0x4000)
        seed[0x4000:0x4000+len(payload)]=payload;seed[RESULT:RESULT+2]=bytes.fromhex('a55a')
        if (root/'initial.ram').read_bytes()!=seed:raise ValueError('Initial full RAM/fixture/sentinel')
        expected=bytearray(seed);expected[MARKER:MARKER+2]=b'\0\1'
        snapshot_stores=[e for e in cpu if e['epoch']==0 and 0x10000<=e.get('address',0)<=0x10018]
        if len(snapshot_stores)!=len(layout['snapshots']):raise ValueError('Missing/duplicate CPU RAM stores')
        for snapshot,store in zip(layout['snapshots'],snapshot_stores):
            read=next(e for e in bus if e['pc']==snapshot['read_pc'])
            value=read['data'] & read['mask'] # actual native value, including unmapped high lane
            if (store['kind'],store['address'],store['mask'],store['pc'],store['data'])!=('write',snapshot['address'],65535,snapshot['store_pc'],value) or store['seq']<=read['seq']:
                raise ValueError('CPU native read/store chain')
            expected[snapshot['address']:snapshot['address']+2]=struct.pack('>H',value)
        if (root/'final.ram').read_bytes()!=expected:raise ValueError('CPU read/store/full RAM mismatch')
        trace=(root/'cpu.trace').read_bytes()
        if not 0<len(trace)<=5*1024*1024 or obs.get('trace_bytes')!=len(trace):raise ValueError('Incomplete/bounded trace')
        pcs=[int(v,16) for v in re.findall(rb'^\s*([0-9a-fA-F]+):',trace,re.M)]
        if pcs.count(0x4012)!=1 or any(e['pc'] not in pcs for e in bus):raise ValueError('Missing/replayed native body trace')
        markers=[e for e in cpu if e.get('address')==MARKER]
        first=[('read',0,0x4000,0),('write',1,0x400a,0)]
        if mode=='reset':first+=[('read',1,0x4000,1)]
        if [(e['kind'],e['data'],e['pc'],e['epoch']) for e in markers]!=first:raise ValueError('Persistent CPU marker')
        if any(e['mask']!=65535 for e in markers):raise ValueError('CPU marker lane')
        if not initial_vectors[-1]['seq']<begin['seq']<markers[0]['seq']<markers[1]['seq']<bus[0]['seq']<end['seq']:
            raise ValueError('Initial CPU fixture ordering')
        if any(e['seq']>=end['seq'] for e in bus+snapshot_stores):raise ValueError('Late first fixture transaction')
        if [e for e in cpu if e['epoch']==0]!=sorted(initial_vectors+markers[:2]+bus+snapshot_stores,key=lambda e:e['seq']):
            raise ValueError('Unexpected first fixture CPU activity')
        if mode=='save_restore':
            if pcs.count(0x4000)!=1 or any(e['epoch']!=0 for e in cpu) or any(e['kind'] in ('reset_request','reset_transition') for e in events):raise ValueError('Unexpected reset/replayed save fixture')
            saved=one('state_saved');mutated=one('state_mutated');restored=one('state_restored')
            if not end['seq']<saved['seq']<mutated['seq']<restored['seq']:raise ValueError('Native save order')
            if saved['bytes']<=0 or saved['value']!=0x5a or mutated['value']!=0x3c or restored['value']!=0x5a or not restored['load_ok']:
                bad=True
            if saved['origin']!='host_observation' or mutated['origin']!='host_request' or restored['origin']!='host_observation':raise ValueError('Native save origins')
            if events[-1] is not restored:raise ValueError('Ambiguous save terminal observation')
            if (root/'restored.ram').read_bytes()!=expected:raise ValueError('Restored full RAM')
        else:
            request=one('reset_request');transition=one('reset_transition');post=vectors(1);capture=one('cpu_reset_complete')
            if (request['origin'],request['api'],transition['origin'])!=('host_request','soft_reset','native_notification'):
                raise ValueError('Missing genuine reset request/transition')
            if (request['epoch'],request['request_id'],transition['epoch'],transition['request_id'],request['value'],transition['value'])!=(0,1,1,1,0x5a,0x5a):raise ValueError('Reset request profile/identity')
            if (capture['origin'],capture['epoch'],capture['request_id'],capture['event_count'],capture['cpu_event_count'],capture['post_cpu_event_count'])!=('host_observation',1,1,capture['seq'],len(cpu),7) or events[-1] is not capture:
                raise ValueError('Unbound periodic reset capture')
            if not end['seq']<request['seq']<transition['seq']<post[0]['seq']:raise ValueError('Reset ordering')
            postbus=[e for e in cpu if e['epoch']==1 and e.get('address',0)>=0x400000]
            stores=[e for e in cpu if e['epoch']==1 and e.get('address')==RESULT]
            if len(postbus)!=1 or len(stores)!=1:raise ValueError('Missing/duplicate post-reset CPU read/store')
            read,store=postbus[0],stores[0]
            if (read['kind'],read['address'],read['mask'],read['pc'])!=('read',0xfffff42a,255,layout['post_read']):raise ValueError('Reset CPU PFSEL lane')
            if (store['kind'],store['mask'],store['pc'],store['data'])!=('write',65535,layout['store'],read['data'] & 255):raise ValueError('Reset CPU result store')
            if [e for e in cpu if e['epoch']==1]!=post+[markers[-1],read,store]:raise ValueError('Extra reset CPU events')
            if not post[-1]['seq']<markers[-1]['seq']<read['seq']<store['seq']<capture['seq']:raise ValueError('Reset read/store order')
            expected[RESULT:RESULT+2]=struct.pack('>H',store['data'])
            if (root/'reset.ram').read_bytes()!=expected or capture['marker']!=1 or capture['result']!=store['data']:
                raise ValueError('Post-reset full RAM/marker/result')
            second=pcs[pcs.index(0x4000,1):]
            path=[0x4000,0x4006,layout['post'],layout['post_read'],layout['store'],layout['stop']]
            if second[:6]!=path or pcs.count(0x4000)!=2:raise ValueError('Reset trace branch/STOP/replay')
            if any(pc!=layout['stop']+4 for pc in second[6:]) or len(second[6:])>2:raise ValueError('Unexpected terminal tail')
            low=store['data'] & 255;tail_sr=0x2700|(4 if low==0 else 8 if low&128 else 0)
            if (capture['sp']!=0x8000 or capture['sr'] not in ((0x2700,tail_sr) if second[6:] else (0x2700,))
                    or capture['pc'] not in (second[-1],second[-1]+2)
                    or capture['next_pc']-capture['pc'] not in (0,2,4)):raise ValueError('Uncorroborated terminal CPU state')
            if not re.search(rb'^\s*0*'+format(layout['stop'],'x').encode()+rb':\s+stop\s+#\$?2700\s*$',trace,re.M|re.I):raise ValueError('Native STOP disassembly absent')
            if read['data'] & 255!=0xc5:bad=True
        if bad:return dict(status='FAIL',reason='CORROBORATED_NATIVE_PFSEL_VALUE_MISMATCH')
        return dict(status='PASS',scope='PFSEL latch R-direct only',pid=run['pid'],execution_id=run['execution_id'])
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError,subprocess.SubprocessError) as exc:
        return dict(status='BLOCKED',reason=str(exc))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary',type=Path);parser.add_argument('qualification',type=Path);parser.add_argument('evidence',type=Path)
    args=parser.parse_args();root=args.evidence.resolve();root.mkdir(parents=True,exist_ok=False)
    try:
        q=qualify_pfsel_build(args.binary,args.qualification);results=[]
        payload,layout=fixture()
        for mode in ('save_restore','reset'):
            work=root/mode;work.mkdir();plugin=work/'plugin';plugin.mkdir()
            shutil.copyfile(HERE/'d2_3_pfsel_boot.lua',plugin/'boot.lua')
            cfg=dict(output=str(work),hex=payload.hex(),**{k:layout[k] for k in ('endpoint','post','post_read','store','stop')},
                     revision='D2.3',variant='diag',execution=mode,execution_id=uuid.uuid4().hex,
                     source_commit=subprocess.check_output(['git','-C',str(HERE.parent),'rev-parse','HEAD'],text=True).strip(),
                     build_source_commit=q['source_commit'],binary_sha256=q['binary_sha256'],fixture_sha256=hashlib.sha256(payload).hexdigest(),
                     qualification_sha256=sha(args.qualification))
            config=work/'config.lua';config.write_text('return '+lua(cfg)+'\n')
            command=[str(args.binary),'asmdana','-noreadconfig','-debug','-debugger','none','-pluginspath',str(plugin),
                     '-plugins','-video','none','-sound','none','-skip_gameinfo','-seconds_to_run','2']
            run={k:cfg[k] for k in ('revision','variant','execution','execution_id','source_commit','build_source_commit','binary_sha256','fixture_sha256','qualification_sha256')}
            with (work/'console.log').open('wb') as log:
                proc=subprocess.Popen(command,cwd=work,env=dict(os.environ,DANA_PFSEL_CONFIG=str(config)),stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits)
                run.update(command=command,pid=proc.pid)
                try:run['exit_code']=proc.wait(timeout=90)
                except subprocess.TimeoutExpired:proc.kill();proc.wait();run['exit_code']=None
            (work/'run.json').write_text(json.dumps(run,indent=2)+'\n')
            result=verify(work,args.binary,args.qualification,mode);results.append(result)
            (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        status='BLOCKED' if any(r['status']=='BLOCKED' for r in results) else 'FAIL' if any(r['status']=='FAIL' for r in results) else 'PASS'
        if status=='PASS' and (results[0]['pid']==results[1]['pid'] or results[0]['execution_id']==results[1]['execution_id']):status='BLOCKED'
        result=dict(status=status,executions=results)
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:result=dict(status='BLOCKED',reason=str(exc))
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return dict(PASS=0,FAIL=1,BLOCKED=2)[result['status']]


if __name__=='__main__':raise SystemExit(main())
