#!/usr/bin/env python3
"""R2 offline checks only. Synthetic CPU records and callback mocks are NOT native evidence."""
import copy
import hashlib
import inspect
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest

import d2_2_gpio_run as q
import d2_2_r2_gpio as r2
import d2_2_test_verifiers as previous
from lua_contract import check_lua

HERE=Path(__file__).resolve().parent


class FixtureContract(unittest.TestCase):
    def test_qualified_A_code_and_Lua_are_unchanged(self):
        for name,wanted in (
            ('fixture','a01682970cb7bf791ddabbab6bad1bcb2331ffb8a9e81d7c81ad10e49ed4b1ee'),
            ('verify_execution','880885dd73d4fb48cd27600ea8dd2324a22f36c6df8d265ba691dd68921a9014'),
            ('execute','7a1a075992327d354beeb0f18a3f81f149e2536a44b8ba86344c38069a53cfbb')):
            self.assertEqual(hashlib.sha256(inspect.getsource(getattr(q,name)).encode()).hexdigest(),wanted)
        self.assertEqual(hashlib.sha256((HERE/'d2_2_gpio_boot.lua').read_bytes()).hexdigest(),
                         'c1f521d6433a6e7ce0c56cb892c6aacf0db7ae5c85b0ca06fd18ed2bd4998a32')

    def test_independently_assembled_layout_and_corrected_displacement(self):
        data,end=r2.reset_fixture();original,_=q.fixture()
        self.assertEqual((len(data),end),(178,0x409e))
        self.assertEqual(data[18:162],original)
        self.assertEqual(hashlib.sha256(original).hexdigest(),r2.A_SHA)
        self.assertEqual(data[:18].hex(),'4a79000200006600009a33fc000100020000')
        self.assertEqual(0x4008+struct.unpack('>h',data[8:10])[0],0x40a2)
        self.assertEqual(0x4008+0x98,0x40a0) # proposed 0098 would branch into STOP immediate
        self.assertEqual(data[162:].hex(),'3039fffff41233c0000200024e722700')
        self.assertEqual(hashlib.sha256(data).hexdigest(),r2.B_SHA)

    def test_b_lua_parses(self):
        check_lua('assert(load('+json.dumps((HERE/'d2_2_reset_r2_boot.lua').read_text())+'))')


class CPUResetVerifier(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='r2-synthetic-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        seed=previous.NativeVerifier();seed.setUp();self.addCleanup(seed.doCleanups)
        shutil.copytree(seed.root,self.root/'save_restore')
        self.b=self.root/'reset';self.b.mkdir()
        ar=json.loads((self.root/'save_restore/run.json').read_text())
        ao=json.loads((self.root/'save_restore/observation.json').read_text())
        ar['binary_sha256']=ao['binary_sha256']=r2.BINARY_SHA
        (self.root/'save_restore/run.json').write_text(json.dumps(ar))
        (self.root/'save_restore/observation.json').write_text(json.dumps(ao))
        self.run=dict(ar,execution='reset',revision='R2',fixture_sha256=r2.B_SHA,pid=43,execution_id='b'*32)
        payload,_=r2.reset_fixture();ram=bytearray(0x400000)
        ram[:8]=struct.pack('>II',0x8000,0x4000);ram[0x4000:0x4000+len(payload)]=payload
        ram[0x10010:0x10012]=bytes.fromhex('cafe');ram[r2.RESULT:r2.RESULT+2]=bytes.fromhex('a55a')
        (self.b/'initial.ram').write_bytes(ram)
        ram[0x10000:0x1000a]=bytes.fromhex('55aa1234fe34fe81fe81');ram[r2.MARKER:r2.MARKER+2]=b'\0\1'
        (self.b/'final.ram').write_bytes(ram);ram[r2.RESULT:r2.RESULT+2]=b'\0\0'
        (self.b/'reset.ram').write_bytes(ram)
        self.events=[]
        def add(kind,origin='host_observation',epoch=0,request_id=0,**kw):
            self.events.append(dict(kind=kind,origin=origin,epoch=epoch,request_id=request_id,**kw))
        for a,d in ((0,0),(2,0x8000),(4,0),(6,0x4000)):
            add('read','cpu',address=a,data=d,mask=65535,pc=0x4000)
        add('profile_initial',value=0,pc=0x4000,sp=0x8000)
        add('read','cpu',address=r2.MARKER,data=0,mask=65535,pc=0x4000)
        add('write','cpu',address=r2.MARKER,data=1,mask=65535,pc=0x400a)
        for event in ao['events']:
            if event['origin']=='cpu' and event.get('address',0)>=0x400000:
                e=copy.deepcopy(event);e['pc']=r2.BODY;self.events.append(e)
        add('fixture_complete',value=0xfe81,pc=r2.ENDPOINT,sp=0x8000)
        add('reset_request','host_request',request_id=1,value=0xfe81,api='soft_reset')
        add('reset_transition','native_notification',1,1,value=0xfe81,point='before_device_reset')
        for a,d in ((0,0),(2,0x8000),(4,0),(6,0x4000)):
            add('read','cpu',1,1,address=a,data=d,mask=65535,pc=r2.ENDPOINT)
        add('read','cpu',1,1,address=r2.MARKER,data=1,mask=65535,pc=0x4000)
        add('read','cpu',1,1,address=0xfffff412,data=0,mask=65535,pc=r2.POST)
        add('write','cpu',1,1,address=r2.RESULT,data=0,mask=65535,pc=r2.STORE)
        add('cpu_reset_complete',epoch=1,request_id=1,marker=1,result=0,pc=r2.STOP,
            next_pc=r2.STOP+4,sp=0x8000,sr=0x2700)
        self.obs=dict(self.run,status='CAPTURED',reason='SYNTHETIC UNIT RECORD',events=self.events)
        (self.b/'cpu.trace').write_text('4000: synthetic\n4006: synthetic\n400a: synthetic\n4012: synthetic\n4098: synthetic\n'
                                      '4000: synthetic\n4006: synthetic\n40a2: synthetic\n40a8: synthetic\n40ae: synthetic\n')
        self.flush()

    def flush(self):
        for i,e in enumerate(self.events):e['seq']=i
        self.write()

    def write(self):
        (self.b/'run.json').write_text(json.dumps(self.run))
        (self.b/'observation.json').write_text(json.dumps(self.obs))

    def after(self,kind,address):
        return next(e for e in self.events if e['epoch']==1 and e['kind']==kind and e.get('address')==address)

    def blocked(self):
        self.flush();self.assertEqual(r2.verify(self.root)['status'],'BLOCKED')

    def test_positive_without_any_profile_reset_callback(self):
        self.assertFalse(any(e['kind']=='profile_reset' for e in self.events))
        self.assertEqual(r2.verify(self.root)['status'],'PASS')

    def test_missing_vector(self):
        self.events.remove(self.after('read',2));self.blocked()

    def test_host_vector(self):
        self.after('read',0)['origin']='host_observation';self.blocked()

    def test_duplicate_vector(self):
        self.events.insert(-1,copy.deepcopy(self.after('read',0)));self.blocked()

    def test_incorrect_vector(self):
        self.after('read',6)['data']=0x4012;self.blocked()

    def test_missing_transition_or_request(self):
        self.events[:]=[e for e in self.events if e['kind']!='reset_transition'];self.blocked()

    def test_missing_explicit_request(self):
        self.events[:]=[e for e in self.events if e['kind']!='reset_request'];self.blocked()

    def test_host_portc_read(self):
        self.after('read',0xfffff412)['origin']='host_observation';self.blocked()

    def test_portc_write_precedes_read(self):
        e=copy.deepcopy(self.after('read',0xfffff412));e['kind']='write'
        self.events.insert(self.events.index(self.after('read',0xfffff412)),e);self.blocked()

    def test_duplicate_portc_read(self):
        self.events.insert(-1,copy.deepcopy(self.after('read',0xfffff412)));self.blocked()

    def test_host_only_marker_change(self):
        next(e for e in self.events if e['kind']=='write' and e.get('address')==r2.MARKER)['origin']='host_request'
        self.blocked()

    def test_lost_marker(self):
        self.after('read',r2.MARKER)['data']=0;self.blocked()

    def test_zero_initial_sentinel(self):
        p=self.b/'initial.ram';d=bytearray(p.read_bytes());d[r2.RESULT:r2.RESULT+2]=b'\0\0';p.write_bytes(d)
        self.blocked()

    def test_stale_result_without_cpu_store(self):
        self.events.remove(self.after('write',r2.RESULT));self.blocked()

    def test_host_result_store(self):
        self.after('write',r2.RESULT)['origin']='host_request';self.blocked()

    def test_forged_ram_result(self):
        p=self.b/'reset.ram';d=bytearray(p.read_bytes());d[r2.RESULT:r2.RESULT+2]=bytes.fromhex('a55a');p.write_bytes(d)
        self.blocked()

    def test_same_pid(self):
        self.run['pid']=42;self.blocked()

    def test_reused_execution_id(self):
        self.run['execution_id']=self.obs['execution_id']='a'*32;self.blocked()

    def test_wrong_binary(self):
        self.run['binary_sha256']=self.obs['binary_sha256']='0'*64;self.blocked()

    def test_wrong_fixture_identity(self):
        self.run['fixture_sha256']=self.obs['fixture_sha256']=r2.A_SHA;self.blocked()

    def test_wrong_source(self):
        self.obs['source_commit']='0'*40;self.blocked()

    def test_corrupted_unrelated_ram(self):
        p=self.b/'reset.ram';d=bytearray(p.read_bytes());d[0x30000]=1;p.write_bytes(d);self.blocked()

    def test_instruction_replay(self):
        p=self.b/'cpu.trace';p.write_text(p.read_text()+'4012: synthetic replay\n');self.blocked()

    def test_incorrect_cpu_value_is_fail_only_when_corroborated(self):
        self.after('read',0xfffff412)['data']=self.after('write',r2.RESULT)['data']=0xfe81
        self.events[-1]['result']=0xfe81
        p=self.b/'reset.ram';d=bytearray(p.read_bytes());d[r2.RESULT:r2.RESULT+2]=bytes.fromhex('fe81');p.write_bytes(d)
        self.flush();self.assertEqual(r2.verify(self.root)['status'],'FAIL')

    def test_conflicting_read_and_store_is_blocked(self):
        self.after('read',0xfffff412)['data']=0xfe81;self.blocked()

    def test_duplicate_raw_sequence(self):
        self.events[-1]['seq']=self.events[-2]['seq'];self.write()
        self.assertEqual(r2.verify(self.root)['status'],'BLOCKED')

    def test_stale_epoch_or_request(self):
        self.after('read',0xfffff412)['request_id']=0;self.blocked()

    def test_missing_native_trace_stop(self):
        p=self.b/'cpu.trace';p.write_text(p.read_text().replace('40ae: synthetic\n',''));self.blocked()

    def test_a_failure_cannot_be_overridden_by_b(self):
        p=self.root/'save_restore/observation.json';d=json.loads(p.read_text());d['status']='BLOCKED';p.write_text(json.dumps(d))
        self.assertEqual(r2.verify(self.root)['status'],'BLOCKED')


class LuaObserver(unittest.TestCase):
    def check_callbacks(self,case):
        from d1_2_run import lua
        payload,endpoint=r2.reset_fixture()
        cfg=dict(output='/mock',execution='reset',revision='R2',execution_id='mock',source_commit='1'*40,
                 binary_sha256=r2.BINARY_SHA,fixture_sha256=r2.B_SHA,hex=payload.hex(),endpoint=endpoint,stop_pc=r2.STOP)
        setup="""
local cb,tap={},{}
local port,exits,in_tap,seed_writes,tap_installs,bp_installs=0,0,false,0,0,0
local output=''
local cfg=CONFIG
local ram={}
os.getenv=function() return 'offline-only' end
dofile=function() return cfg end
io.open=function(path) return {write=function(_,s)
    if path:find('observation.json',1,true) then output=output..s end
end,close=function() end} end
local space={data_width=16,read_u16=function(_,a) if a==0xfffff412 then return port end;return ram[a] or 0 end,
    read_u8=function() return 0 end,write_u32=function() seed_writes=seed_writes+1 end,
    write_u8=function() seed_writes=seed_writes+1 end,write_u16=function(_,a,v) ram[a]=v end}
for _,kind in ipairs({'read','write'}) do
    space['install_'..kind..'_tap']=function(_,a,b,id,fn) tap_installs=tap_installs+1;tap[kind]=fn;return {} end
end
local state={CURPC={value=0x4000},PC={value=0x4002},SP={value=0x8000},SR={value=0x2700},IR={value=0x4a79}}
local cpu={state=state,spaces={program=space},debug={bpclear=function() end,
    bpset=function() bp_installs=bp_installs+1 end,go=function() end}}
manager={machine={devices={[':maincpu']=cpu},debugger={execution_state='stop',command=function() end},
    exit=function() assert(not in_tap,'Exit called from tap!');exits=exits+1 end,soft_reset=function() end}}
emu={time=function() return 0.1 end,register_prestart=function(fn) cb.prestart=fn end,
    register_periodic=function(fn) cb.periodic=fn end,add_machine_reset_notifier=function(fn) cb.reset=fn;return {} end}
""".replace('CONFIG',lua(cfg))
        steps="""
cb.prestart();cb.periodic()
assert(ram[0x20000]==0 and ram[0x20002]==0xa55a)
local writes=seed_writes
port=0xfe81;ram[0x20000]=1;state.CURPC.value=cfg.endpoint
cb.periodic();cb.prestart() -- deliberately never invoke the absent reset notifier
assert(seed_writes==writes and tap_installs==2 and bp_installs==2)
assert(exits==0)
local function observe(kind,a,d)
    in_tap=true;tap[kind](a,d,0xffff);in_tap=false
    assert(exits==0,'Tap must only record/defer')
end
if CASE=='budget' then
    for i=1,260 do observe('read',0,0) end
elseif CASE=='replay' then
    observe('write',0xfffff412,0x5500)
else
    if CASE~='missing_vectors' then
        for _,v in ipairs({{0,0},{2,0x8000},{4,0},{6,0x4000}}) do observe('read',v[1],v[2]) end
    end
    state.CURPC.value=0x4000;observe('read',0x20000,1)
    state.CURPC.value=0x40a2;observe('read',0xfffff412,0)
    state.CURPC.value=0x40a8;observe('write',0x20002,0);ram[0x20002]=0
    state.CURPC.value=cfg.stop_pc;state.PC.value=cfg.stop_pc+4;state.IR.value=0x4e72
end
cb.periodic()
if CASE=='missing_vectors' then
    assert(exits==0,'Result write alone cannot complete capture')
    emu.time=function() return 1.1 end;cb.periodic()
end
assert(exits==1)
if CASE=='complete' then
    assert(output:find('"status":"CAPTURED"',1,true))
    assert(output:find('"kind":"cpu_reset_complete"',1,true))
    assert(not output:find('"kind":"profile_reset"',1,true))
else assert(output:find('"status":"BLOCKED"',1,true)) end
""".replace('CASE',json.dumps(case))
        check_lua(setup+'\n'+(HERE/'d2_2_reset_r2_boot.lua').read_text()+'\n'+steps)

    def test_complete_without_reset_notifier_or_post_reset_breakpoint(self):
        self.check_callbacks('complete')

    def test_trace_budget_never_exits_from_bus_tap(self):
        self.check_callbacks('budget')

    def test_fixture_replay_deferred_to_periodic(self):
        self.check_callbacks('replay')

    def test_result_write_without_vectors_does_not_complete_capture(self):
        self.check_callbacks('missing_vectors')


if __name__=='__main__':unittest.main(verbosity=2)
