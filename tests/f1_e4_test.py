#!/usr/bin/env python3
"""E4 offline evidence negatives and Lua callbacks. NO native guest evidence."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import f1_emutos_run as runner
import f1_guest as guest
from lua_contract import check_lua

ROOT=Path(__file__).resolve().parents[1]


class Evidence(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='f1-e4-synthetic-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.guest=self.root/'guest';self.guest.mkdir()
        self.source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
        self.syms={'__text':0x2140,'_os_header':0x2140,'_main':0x2150,'_realmain':0x2160,
                   '_dana_init':0x8200,'_stktop':0x1000,'__low_stram_end':0x2140,
                   '__bss':0x40000,'__ebss':0x41000}
        image=bytearray(0x10000);image[:2]=bytes.fromhex('600e');image[16:20]=bytes.fromhex('6000000e')
        (self.guest/'emutos.img').write_bytes(image)
        (self.guest/'emutos-dana.rom').write_bytes(b'SYNTHETIC TEST-ONLY'+image)
        (self.guest/'emutos.map').write_text('\n'.join(f'0x{v:08x} {k}' for k,v in self.syms.items()))
        provenance={'source_commit':guest.PIN,'exit_code':0,'command':['make','dana'],'compiler':'SYNTHETIC UNIT FIXTURE'}
        (self.guest/'build_provenance.json').write_text(json.dumps(provenance))
        self.manifest=guest.package(self.guest)
        # The production gate is immutable; only this isolated synthetic suite
        # substitutes test file identities, never the actual qualification job.
        self.synthetic={name:((self.guest/name).stat().st_size,guest.sha(self.guest/name))
                        for name in guest.QUALIFIED_ARTIFACTS}
        self.patch=patch.object(guest,'QUALIFIED_ARTIFACTS',self.synthetic);self.patch.start();self.addCleanup(self.patch.stop)
        self.runs=[];self.observations=[]
        for i in range(2):
            root=self.root/f'run-{i+1}';root.mkdir()
            (root/'initial-image.bin').write_bytes(image);(root/'console.log').write_text('SYNTHETIC ONLY\n')
            trace='\n'.join(f'{pc:08x}: synthetic test instruction' for pc in (0x2140,0x2150,0x2160,0x8200,0x8392,0x8398,0x8400))+'\n'
            (root/'guest.trace').write_text(trace)
            def state(pc):return dict(CURPC=pc,PC=pc+2,SR=0x2700,SP=0x1000,IR=0)
            events=[]
            def bus(kind,address,mask,data,pc):
                e=dict(kind=kind,address=address,mask=mask,data=data,origin='cpu',tap_id='f1_'+kind,
                       side_effects_disabled=False,after_dependency=False,state=state(pc))
                e.update(byte_addresses=runner.selected_bytes(e),width_bits=8*len(runner.selected_bytes(e)))
                events.append(e)
            for a,d in ((0,0),(2,0x1000),(4,0),(6,0x2140)):bus('read',a,0xffff,d,0)
            for kind,pc in (('first_instruction',0x2140),('milestone',0x2150),('milestone',0x2160),('milestone',0x8200)):
                events.append(dict(kind=kind,origin='debugger_observation',state=state(pc)))
            bus('write',0xfffff412,0xff,0,0x8392)
            bus('write',0xfffff412,0xff00,0,0x8398)
            # Arbitrary unsupported UART byte, deliberately NOT predicted PFSEL.
            bus('read',0xfffff906,0xff00,0xff00,0x8400)
            for seq,e in enumerate(events):e.update(seq=seq,virtual_seconds=seq/1000)
            dep={k:events[-1][k] for k in ('address','kind','data','mask','state','byte_addresses','width_bits','origin','tap_id')}
            dep.update(event_seq=events[-1]['seq'],effective_address=0xfffff906)
            run=dict(exit_code=0,pid=100+i,revision='F1-E4',variant='diag',binary_sha256=runner.BINARY_SHA,
                package_sha256=self.manifest['package']['sha256'],image_sha256=guest.sha(self.guest/'emutos.img'),
                source_commit=self.source,execution_id=str(i+1)*32,full_boot=False,
                command=['/qualified/diag/bin/dana-diag','asmdana'],driver_sha256=runner.OLD_DRIVER_SHA)
            obs=dict(run,schema='dana-f1-e4-observation-v1',status='CAPTURED',reason='BLOCKED_HARDWARE',
                     first_instruction=state(0x2140),events=events,dependency=dep,final=state(0x8400),
                     event_count=len(events),trace_bytes=len(trace.encode()),virtual_seconds=.1,
                     trace_mode='native_loop_compression_no_sampling')
            self.runs.append(run);self.observations.append(obs)
        self.flush()

    def flush(self):
        for i,(run,obs) in enumerate(zip(self.runs,self.observations)):
            root=self.root/f'run-{i+1}'
            (root/'run.json').write_text(json.dumps(run));(root/'observation.json').write_text(json.dumps(obs))

    def verify(self):
        self.flush();return runner.verify_e4_pair(self.root,self.guest,self.source)

    def blocked(self):self.assertIn(self.verify()['status'],('BLOCKED_GUEST','BLOCKED_HARNESS'))

    def test_positive_synthetic_chain_is_scoped_only(self):
        verdict=self.verify();self.assertEqual(verdict['status'],'REAL_PROGRESS_PASS_SCOPED')
        self.assertFalse(verdict['full_boot']);self.assertEqual(verdict['normalized_dependency']['effective_address'],0xfffff906)

    def test_real_input_gate_rejects_synthetic_guest(self):
        self.patch.stop()
        self.assertEqual(self.verify()['status'],'BLOCKED_GUEST')

    def test_forged_old_pc_crossing(self):
        self.observations[0]['events'][8]['state']['CURPC']=0x8394;self.blocked()

    def test_swapped_low_high_lanes(self):
        for mask,lanes in ((0xff00,[0xfffff412]),(0xff,[0xfffff412])):
            self.observations[0]['events'][8].update(mask=mask,byte_addresses=lanes);self.blocked()

    def test_host_cannot_substitute_cpu(self):
        for idx in (0,8,10):
            e=self.observations[0]['events'][idx];old=e.copy();e['origin']='host';self.blocked();e.update(old)

    def test_missing_new_access(self):
        self.observations[0]['events'].pop();self.observations[0]['event_count']-=1;self.blocked()

    def test_no_new_dependency_records_crossing_without_boot_pass(self):
        for obs in self.observations:
            obs['events'].pop();obs['event_count']-=1
            obs.update(reason='BLOCKED_VIRTUAL_BUDGET',dependency=None)
        result=self.verify();self.assertEqual(result['status'],'BLOCKED_GUEST')
        self.assertTrue(result['runs'][0]['old_pcsel_crossing_proved']);self.assertFalse(result['full_boot'])

    def test_duplicate_or_missing_raw_event(self):
        original=copy.deepcopy(self.observations[0])
        for events in (original['events'][:-1],original['events']+[original['events'][8]]):
            self.observations[0]['events']=events;self.blocked()
        self.observations[0]=original

    def test_earlier_missing_access_cannot_be_skipped(self):
        e=self.observations[0]['events'][9]
        e.update(address=0xfffff410,byte_addresses=[0xfffff410]);self.blocked()

    def test_wrong_rom_sha_or_guest_corruption(self):
        (self.guest/'emutos-dana.rom').write_bytes(b'corrupt');self.blocked()

    def test_native_initial_image_corruption(self):
        (self.root/'run-1/initial-image.bin').write_bytes(b'corrupt');self.blocked()

    def test_missing_or_wrong_build_provenance(self):
        p=self.guest/'build_provenance.json';p.write_text(json.dumps({'source_commit':'0'*40,'exit_code':0}));self.blocked()

    def test_wrong_executable_sha(self):
        self.runs[0]['binary_sha256']=self.observations[0]['binary_sha256']='0'*64;self.blocked()

    def test_wrong_source_sha_even_if_run_and_observation_agree(self):
        self.runs[0]['source_commit']=self.observations[0]['source_commit']='0'*40;self.blocked()

    def test_wrong_package_identity(self):
        self.runs[0]['package_sha256']=self.observations[0]['package_sha256']='0'*64;self.blocked()

    def test_two_incoherent_dependencies_are_blocked_not_product_fail(self):
        obs=self.observations[1];obs['events'][-1]['data']=obs['dependency']['data']=0
        self.assertEqual(self.verify()['status'],'BLOCKED_HARNESS')

    def test_unbounded_trace(self):
        (self.root/'run-1/guest.trace').write_bytes(b'x'*(runner.TRACE_LIMIT+1));self.blocked()

    def test_sampled_or_truncated_trace(self):
        self.observations[0]['trace_mode']='sampled';self.blocked()

    def test_missing_crossing_or_dependency_instruction_trace(self):
        p=self.root/'run-1/guest.trace';original=p.read_text()
        for pc in ('00008392','00008400'):
            p.write_text('\n'.join(line for line in original.splitlines() if not line.startswith(pc))+ '\n')
            self.observations[0]['trace_bytes']=p.stat().st_size;self.blocked()

    def test_unknown_startup_path(self):
        self.observations[0]['events'][6]['state']['CURPC']=0x2162;self.blocked()

    def test_false_full_boot_claim(self):
        self.observations[0]['full_boot']=True;self.blocked()

    def test_same_process_or_execution_id(self):
        self.runs[1]['pid']=self.runs[0]['pid'];self.blocked()
        self.runs[1]['pid']=101
        self.runs[1]['execution_id']=self.observations[1]['execution_id']=self.runs[0]['execution_id'];self.blocked()

    def test_unreported_native_tail_cannot_be_hidden(self):
        obs=self.observations[0];tail=copy.deepcopy(obs['events'][-1]);tail.update(seq=11,virtual_seconds=.02)
        obs['events'].append(tail);obs['event_count']+=1;self.blocked()

    def test_missing_observation(self):
        self.flush();(self.root/'run-1/observation.json').unlink()
        self.assertEqual(runner.verify_e4_pair(self.root,self.guest,self.source)['status'],'BLOCKED_HARNESS')

    def test_native_boundary_rejects_unqualified_executable_before_launch(self):
        unqualified=self.root/'fake/diag/bin/dana-diag';unqualified.parent.mkdir(parents=True)
        unqualified.write_text('Offline negative input only; never execute this file.\n');unqualified.chmod(0o755)
        with patch('f1_emutos_run.subprocess.Popen') as launch:
            for path in (Path('/tmp/generic-mame'),Path('diag/bin/dana-diag'),unqualified):
                with self.assertRaises(ValueError):runner.run(path,self.guest,self.root/'forbidden',post_portc=True)
            launch.assert_not_called()


class LuaCallbacks(unittest.TestCase):
    def test_full_lua_parse(self):
        check_lua('assert(load('+json.dumps((ROOT/'tests/f1_emutos_boot.lua').read_text())+'))')

    def test_lane_classification_reuses_actual_lua(self):
        src=(ROOT/'tests/f1_emutos_boot.lua').read_text()
        functions=src[src.index('local function implemented_byte'):src.index('emu.register_prestart')]
        check_lua(functions+'''
assert(bus_bytes(0xfffff412,0xff)[1]==0xfffff413)
assert(first_unsupported(bus_bytes(0xfffff412,0xff),'write')==nil)
assert(first_unsupported(bus_bytes(0xfffff412,0xff00),'write')==nil)
assert(first_unsupported(bus_bytes(0xfffff300,0xff),'read')==0xfffff301)
assert(first_unsupported(bus_bytes(0xfffff906,0xff00),'read')==0xfffff906)
assert(not pcall(bus_bytes,0xfffff413,0xff))
''')

    def callbacks(self,case):
        cfg=dict(output='/mock',symbols={'_os_header':0x2140,'__text':0x2140,'_stktop':0x1000,
                    '_main':0x2150,'_realmain':0x2160,'_dana_init':0x8200},image_length=2,
                 revision='F1-E4',source_commit='1'*40,execution_id='2'*32,
                 package_sha256='3'*64,binary_sha256=runner.BINARY_SHA,image_sha256='4'*64)
        setup='local cfg='+runner.lua(cfg)+'''
local callbacks,mock_taps={},{}
local in_tap,exits,output=false,0,''
local disabled,mock_loaded=false,true
local s={}
for k,v in pairs({CURPC=0x2140,PC=0x2142,SR=0x2700,SP=0x1000,IR=0,D0=0,D1=0,D2=0,D3=0,A0=0}) do s[k]={value=v} end
local bps={}
local cpu={state=s,debug={bpclear=function(_,i) if i then bps[i]=nil else bps={} end end,
    bpset=function(_,pc) bps[#bps+1]={address=pc} end,bplist=function() return bps end,go=function() assert(not in_tap) end}}
local space={data_width=16,read_u8=function() return 0 end}
for _,kind in ipairs({'read','write'}) do
    space['install_'..kind..'_tap']=function(_,a,b,name,fn) mock_taps[kind]=fn;return {} end
end
cpu.spaces={program=space}
manager={machine={devices={[':maincpu']=cpu,[':']={output=function() return {get=function() return mock_loaded and 1 or 0 end} end}},
    debugger={execution_state='stop',command=function() assert(not in_tap,'Debugger command in tap') end},
    side_effects_disabled=function() return disabled end,exit=function() assert(not in_tap,'Exit in tap');exits=exits+1 end}}
emu={time=function() return .1 end,register_prestart=function(fn) callbacks.start=fn end,
    register_periodic=function(fn) callbacks.periodic=fn end,add_machine_reset_notifier=function(fn) return {} end}
os.getenv=function() return 'mock-config' end;dofile=function() return cfg end
io.open=function(path) return {seek=function() return 1024 end,close=function() end,
    write=function(_,text) if path:find('observation.json',1,true) then output=output..text end end} end
'''
        steps='local case='+json.dumps(case)+'''
callbacks.start();callbacks.periodic()
local function access(kind,pc,address,data,mask)
    s.CURPC.value=pc;in_tap=true
    assert(mock_taps[kind](address,data,mask)==nil,'Tap must never substitute data')
    in_tap=false;assert(exits==0)
end
-- Debugger reads and not-yet-loaded host writes must not count as CPU traffic.
disabled=true;access('read',0x8392,0xfffff906,0x1111,0xffff);disabled=false
mock_loaded=false;access('write',0x8392,0xfffff412,0,0xff);mock_loaded=true
if case=='tap_error' then
    access('read',0x8392,0xfffff413,0,0xff)
elseif case=='budget' then
    for i=1,20001 do access('read',0x2140,0,0,0xffff) end
else
    access('write',0x8392,0xfffff412,0,0xff)
    access('read',0x8400,0xfffff906,0xabcd,0xffff)
    -- A later native tail is retained and cannot replace the FIRST dependency.
    access('write',0x8408,0xfffff410,0,0xff00)
end
callbacks.periodic();assert(exits==1)
assert(output:find('"status":"CAPTURED"',1,true))
assert(output:find('"full_boot":false',1,true))
if case=='complete' then
    assert(output:find('"reason":"BLOCKED_HARDWARE"',1,true))
    assert(output:find('"effective_address":'..tostring(0xfffff906),1,true))
    assert(output:find('"after_dependency":true',1,true))
    assert(not output:find('4369',1,true),'Host read leaked into CPU evidence')
elseif case=='budget' then assert(output:find('BLOCKED_TRACE_BUDGET',1,true))
else assert(output:find('BLOCKED_TAP:',1,true)) end
'''
        check_lua(setup+(ROOT/'tests/f1_emutos_boot.lua').read_text()+steps)

    def test_deferred_first_dependency_preserves_tail_and_excludes_host(self):
        self.callbacks('complete')

    def test_tap_error_defers_exit(self):
        self.callbacks('tap_error')

    def test_tap_budget_defers_exit(self):
        self.callbacks('budget')


if __name__=='__main__':unittest.main(verbosity=2)
