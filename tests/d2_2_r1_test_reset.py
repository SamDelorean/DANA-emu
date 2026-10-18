#!/usr/bin/env python3
"""Offline R1 verifier and Lua lifecycle checks. All observations are SYNTHETIC."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from d2_2_gpio_run import verify, verify_execution
import d2_2_test_verifiers as previous
from lua_contract import check_lua


class IndependentExecutions(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='portc-r1-synthetic-')
        self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        # Keep the previous positive fixture and all its original negative cases.
        seed=previous.NativeVerifier();seed.setUp();self.addCleanup(seed.doCleanups)
        for mode in ('save_restore','reset'):
            shutil.copytree(seed.root,self.root/mode)
        self.records={}
        self.observations={}
        for mode in ('save_restore','reset'):
            self.records[mode]=json.loads((self.root/mode/'run.json').read_text())
            self.observations[mode]=json.loads((self.root/mode/'observation.json').read_text())
        rec=self.records['reset'];obs=self.observations['reset']
        rec.update(execution='reset',execution_id='b'*32,pid=43)
        for key in ('execution','execution_id','pid'):obs[key]=rec[key]
        obs['events']=[e for e in obs['events'] if not e['kind'].startswith('state_')]
        obs['events']+= [
            dict(kind='reset_request',origin='host_request',epoch=0,request_id=1,value=0xfe81,api='soft_reset'),
            dict(kind='reset_transition',origin='native_notification',epoch=1,request_id=1,value=0xfe81,point='before_device_reset'),
            dict(kind='profile_reset',origin='native_notification',epoch=1,request_id=1,value=0,point='after_device_reset')]
        obs['events'] += [dict(kind='read',origin='cpu',address=a,data=d,mask=0xffff,epoch=1,request_id=1)
                          for a,d in ((0,0),(2,0x8000),(4,0),(6,0x4000))]
        obs['events'].append(dict(kind='reset_entry',origin='host_observation',value=0,
                                 epoch=1,request_id=1,pc=0x4000,sp=0x8000,sr=0x2708))
        shutil.copyfile(self.root/'reset/final.ram',self.root/'reset/reset.ram')
        (self.root/'reset/restored.ram').unlink()
        self.flush()

    def flush(self):
        for mode,obs in self.observations.items():
            for i,e in enumerate(obs['events']):e['seq']=i
            self.write(mode)

    def write(self,mode='reset'):
        (self.root/mode/'observation.json').write_text(json.dumps(self.observations[mode]))
        (self.root/mode/'run.json').write_text(json.dumps(self.records[mode]))

    def event(self,kind):
        return next(e for e in self.observations['reset']['events'] if e['kind']==kind)

    def remove(self,kind):
        self.observations['reset']['events']=[e for e in self.observations['reset']['events'] if e['kind']!=kind]
        self.flush()

    def test_positive_two_process_synthetic_evidence(self):
        self.assertEqual(verify(self.root)['status'],'PASS')

    def test_missing_reset_request_blocked(self):
        self.remove('reset_request');self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_missing_native_transition_blocked(self):
        self.remove('reset_transition');self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_preexisting_zero_is_not_post_reset_evidence(self):
        self.event('profile_reset').update(epoch=0,request_id=0)
        self.flush();self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_confirmed_wrong_post_reset_value_fails(self):
        self.event('profile_reset')['value']=0xfe81
        self.flush();self.assertEqual(verify(self.root)['status'],'FAIL')

    def test_host_read_cannot_replace_native_reset_notification(self):
        self.event('profile_reset')['origin']='host_observation'
        self.flush();self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_duplicate_sequence_observations_never_create_reset(self):
        obs=self.observations['reset']
        duplicate=copy.deepcopy(self.event('profile_reset'))
        obs['events'].append(duplicate)
        self.write();self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_duplicated_native_vectors_remain_ambiguous(self):
        obs=self.observations['reset']
        v=next(e for e in obs['events'] if e['epoch']==1 and e['kind']=='read')
        obs['events'].insert(obs['events'].index(v),copy.deepcopy(v))
        self.flush();self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_duplicate_mmio_callbacks_are_blocked_without_deduplication(self):
        obs=self.observations['reset']
        e=next(e for e in obs['events'] if e['kind']=='write')
        obs['events'].insert(obs['events'].index(e),copy.deepcopy(e))
        self.flush();self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_startup_vector_copies_without_reset_chain_are_blocked(self):
        self.remove('reset_transition')
        self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_missing_post_request_vectors_blocked(self):
        obs=self.observations['reset']
        obs['events']=[e for e in obs['events'] if not (e['epoch']==1 and e['kind']=='read')]
        self.flush();self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_host_vector_reads_are_not_cpu_reset_proof(self):
        for e in self.observations['reset']['events']:
            if e['epoch']==1 and e['kind']=='read':e['origin']='host_observation'
        self.flush();self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_confirmed_wrong_native_vector_value_fails(self):
        v=next(e for e in self.observations['reset']['events'] if e['epoch']==1 and e['kind']=='read')
        v['data']=1;self.flush();self.assertEqual(verify(self.root)['status'],'FAIL')

    def test_wrong_reset_request_binding_or_order_blocked(self):
        self.event('reset_entry')['request_id']=0
        self.flush();self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_zero_before_device_reset_cannot_prove_transition(self):
        self.event('reset_transition')['value']=0
        self.flush();self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_invalid_binary_fixture_or_source_identity_fails(self):
        original=copy.deepcopy(self.observations['reset'])
        for key,value in (('binary_sha256','9'*64),('fixture_sha256','8'*64),('source_commit','0'*40)):
            self.observations['reset']=copy.deepcopy(original)
            self.observations['reset'][key]=value;self.flush()
            self.assertEqual(verify(self.root)['status'],'FAIL',key)

    def test_failed_state_save_or_load_blocks_aggregate(self):
        obs=self.observations['save_restore']
        next(e for e in obs['events'] if e['kind']=='state_restored')['load_ok']=False
        self.flush();self.assertEqual(verify(self.root)['status'],'BLOCKED')
        obs['events']=[e for e in obs['events'] if e['kind']!='state_saved']
        self.flush();self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_wrong_execution_variant_or_non_diag_record_fails(self):
        self.records['reset']['variant']='stable';self.flush()
        self.assertEqual(verify(self.root)['status'],'FAIL')
        self.records['reset']['variant']='diag'
        self.records['reset']['command'][0]='/usr/bin/mame';self.flush()
        self.assertEqual(verify(self.root)['status'],'FAIL')

    def test_same_process_or_execution_id_is_not_independent(self):
        self.records['reset']['pid']=42;self.flush()
        self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_cross_process_binary_identity_must_match(self):
        self.records['reset']['binary_sha256']='3'*64
        self.observations['reset']['binary_sha256']='3'*64
        self.flush();self.assertEqual(verify(self.root)['status'],'FAIL')

    def test_reset_ram_reseed_or_corruption_fails(self):
        ram=bytearray((self.root/'reset/reset.ram').read_bytes());ram[0x10000]=0
        (self.root/'reset/reset.ram').write_bytes(ram)
        self.assertEqual(verify(self.root)['status'],'FAIL')

    def test_timeout_remains_blocked(self):
        self.records['reset']['exit_code']=None;self.flush()
        self.assertEqual(verify(self.root)['status'],'BLOCKED')


class LuaLifecycle(unittest.TestCase):
    def exercise(self,mode):
        from d2_2_gpio_run import fixture
        payload,endpoint=fixture()
        cfg=json.dumps(dict(execution=mode,execution_id='offline-only',source_commit='1'*40,
                            binary_sha256='2'*64,fixture_sha256='3'*64,output='/synthetic',
                            hex=payload.hex(),endpoint=endpoint))
        # Mocks exercise callback orchestration only; they do not emulate CPU/hardware.
        source=(Path(__file__).parent/'d2_2_gpio_boot.lua').read_text()
        setup='''
local callbacks,tap_callbacks={},{}
local port,seed_writes,tap_installs,reset_calls,save_calls,exits=0,0,0,0,0,0
local output=''
local cfg=CONFIG
os.getenv=function() return 'offline-only' end
dofile=function() return cfg end
io.open=function(path) return {write=function(_,s)
    if path:find('observation.json',1,true) then output=output..s end
end,close=function() end} end
local space={data_width=16,read_u16=function() return port end,read_u8=function() return 0 end,
    write_u32=function() seed_writes=seed_writes+1 end,write_u8=function() seed_writes=seed_writes+1 end,
    write_u16=function(_,a,v) if a==0xfffff412 then port=v end end}
for _,kind in ipairs({'read','write'}) do
    space['install_'..kind..'_tap']=function(_,a,b,id,fn)
        tap_installs=tap_installs+1;tap_callbacks[kind]=fn;return {} end
end
local state={CURPC={value=0x4000},SP={value=0x8000},SR={value=0x2700}}
local cpu={state=state,spaces={program=space},debug={bpclear=function() end,bpset=function() end,go=function() end}}
manager={machine={devices={[':maincpu']=cpu},debugger={execution_state='stop',command=function() end},
    exit=function() exits=exits+1 end,
    soft_reset=function() reset_calls=reset_calls+1 end,
    buffer_save=function() save_calls=save_calls+1;return 'mock-saved' end,
    buffer_load=function() port=0xfe81;return true end}}
emu={time=function() return 0.1 end,register_prestart=function(fn) callbacks.prestart=fn end,
    register_periodic=function(fn) callbacks.periodic=fn end,
    add_machine_reset_notifier=function(fn) callbacks.reset=fn;return {} end}
'''
        from d1_2_run import lua
        setup=setup.replace('CONFIG',lua(json.loads(cfg)))
        steps='''
callbacks.prestart();callbacks.reset();callbacks.periodic()
assert(tap_installs==2 and seed_writes>0)
local writes=seed_writes
port=0xfe81;state.CURPC.value=cfg.endpoint
callbacks.periodic()
if cfg.execution=='save_restore' then
    assert(save_calls==1 and reset_calls==0 and exits==1)
    assert(output:find('"status":"PASS"',1,true))
else
    assert(save_calls==0 and reset_calls==1 and exits==0)
    callbacks.prestart() -- actual second pre-reset callback; initialization must be one-shot
    assert(seed_writes==writes and tap_installs==2)
    port=0;callbacks.reset()
    assert(exits==0) -- notification alone never completes the reset test
    for _,v in ipairs({{0,0},{2,0x8000},{4,0},{6,0x4000}}) do
        tap_callbacks.read(v[1],v[2],0xffff)
    end
    state.CURPC.value=0x4000;state.SR.value=0x2708
    callbacks.periodic()
    assert(exits==1 and output:find('"status":"PASS"',1,true))
    assert(output:find('"kind":"reset_transition"',1,true))
    assert(output:find('"kind":"profile_reset"',1,true))
end
'''
        check_lua(setup+'\n'+source+'\n'+steps)

    def test_actual_lua_save_restore_finishes_without_requesting_reset(self):
        self.exercise('save_restore')

    def test_actual_lua_reset_does_not_reseed_or_reinstall_taps(self):
        self.exercise('reset')


if __name__=='__main__':unittest.main(verbosity=2)
