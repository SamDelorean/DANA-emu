#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Offline 012-E observation controls; synthetic fixtures NEVER native PASS."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import f1_emutos_run as f1
import dana_012e_verify as v
from f1_emutos_run import lua
import d2_3_test as fixtures
from lua_contract import check_lua

ROOT=f1.PROJECT
ENCODER='local function encode(x)'+(f1.HERE/'f1_emutos_boot.lua').read_text().split('local function encode(x)',1)[1].split('if e6 then observer=',1)[0]


def compressed(rows,limits=None,extra=''):
    """Execute the ACTUAL Lua encoder/aggregator, without a MAME instance."""
    rows=copy.deepcopy(rows)
    for row in rows:
        for name in v.STATE_FIELDS:row['state'].setdefault(name,0)
    with tempfile.TemporaryDirectory(prefix='012e-lua-') as temp:
        output=Path(temp)/'result.json'
        script=ENCODER+'\nlocal module=dofile('+lua(str(f1.HERE/'dana_012e_observer.lua'))+')\n'
        script+='local limits='+lua(limits or v.LIMITS)+'\nlocal observer=module.new(encode,limits)\n'
        script+='local rows='+lua(rows)+'\nfor _,e in ipairs(rows) do observer:push(e) end\n'+extra
        script+='\nlocal f=assert(io.open('+lua(str(output))+',"w"));f:write(encode({events=observer.events,compression_stats=observer:stats()}));f:close()\n'
        check_lua(script)
        return json.loads(output.read_text())


def poll(data=0x347,pc=0x8500,time=0):
    return dict(kind='read',address=0xfffff202,data=data,mask=65535,origin='cpu',tap_id='f1_read',side_effects_disabled=False,
                after_dependency=False,virtual_seconds=time,byte_addresses=[0xfffff202,0xfffff203],width_bits=16,
                state=dict(CURPC=pc,PC=pc+2,SR=0x2700,SP=0x1000,IR=0x3039,D0=0))


class Compression(unittest.TestCase):
    def test_100000_polls_are_one_exact_counted_span(self):
        e=poll();extra='''
for n=2,100000 do
    local e={kind='read',address=0xfffff202,data=0x347,mask=65535,origin='cpu',tap_id='f1_read',side_effects_disabled=false,
        after_dependency=false,virtual_seconds=n/10000000,byte_addresses={0xfffff202,0xfffff203},width_bits=16,
        state={CURPC=0x8500,PC=0x8502,SR=0x2700,SP=0x1000,IR=0x3039,D0=0}}
    for _,k in ipairs({'D1','D2','D3','D4','D5','D6','D7','A0','A1','A2','A3','A4','A5','A6','USP'}) do e.state[k]=0 end
    observer:push(e)
end
assert(#observer.events==1 and observer.events[1].count==100000)
'''
        data=compressed([e],extra=extra)
        obs=dict(data,event_count=1,virtual_seconds=.1,reason='OBSERVATION_LIMIT_TIME')
        _,_,spans,counts=v.rows_info(obs)
        self.assertEqual((spans[0]['raw_first'],spans[0]['raw_last'],counts['poll_reads']),(0,99999,100000))
    def test_data_state_pc_and_irq_changes_are_retained(self):
        rows=[poll(time=0),poll(time=.001),poll(0x8347,time=.002),poll(0x8347,pc=0x8502,time=.003)]
        irq=poll(time=.004);irq.update(kind='iack',tap_id='f1_iack',address=0xfffffffc,mask=255,data=0x46,byte_addresses=[0xfffffffd],width_bits=8)
        rows += [irq,poll(time=.005),poll(time=.006)]
        rows[-1]['state']['D0']=1
        data=compressed(rows)
        self.assertEqual([e['kind'] for e in data['events']],['poll_span','poll_span','poll_span','iack','poll_span','poll_span'])
        self.assertEqual([e['epoch'] for e in data['events']],[0,0,0,1,1,1])
        self.assertEqual(data['compression_stats']['accepted_raw'],7)
    def test_write_or_rte_observation_never_compresses(self):
        rows=[poll(),poll(time=.1)];rows[0]['kind']=rows[1]['kind']='write';rows[0]['tap_id']=rows[1]['tap_id']='f1_write'
        rows += [dict(poll(time=.2),role='rte'),dict(poll(time=.3),role='rte')]
        self.assertEqual([e['kind'] for e in compressed(rows)['events']],['write','write','read','read'])
    def test_overflow_has_first_omitted_event_and_no_hidden_tail(self):
        limits=dict(v.LIMITS,max_retained_events=1)
        rows=[poll(),poll(0x8347,time=.1),poll(time=.2)]
        d=compressed(rows,limits)
        self.assertEqual((d['compression_stats']['accepted_raw'],d['compression_stats']['dropped_raw'],d['compression_stats']['attempted_raw']),(1,2,3))
        self.assertEqual(d['compression_stats']['overflow']['first_unrecorded']['raw_first'],1)
        obs=dict(d,event_count=1,virtual_seconds=.3,reason='OBSERVATION_LIMIT_EVENTS')
        v.rows_info(obs)
    def test_forged_count_lane_pc_origin_and_epoch_are_blocked(self):
        baseline=compressed([poll(),poll(time=.1)])
        mutations=[lambda d:d['events'][0].update(raw_last=8),lambda d:d['events'][0].update(address=0xfffff800),
                   lambda d:d['events'][0].update(last_pc=0x9999),lambda d:d['events'][0].update(origin='host'),
                   lambda d:d['events'][0].update(epoch=1),lambda d:d['compression_stats'].update(native_reads=3)]
        for mutate in mutations:
            d=copy.deepcopy(baseline);mutate(d)
            with self.subTest(d=d),self.assertRaises(ValueError):v.rows_info(dict(d,event_count=len(d['events']),virtual_seconds=.2,reason='OBSERVATION_LIMIT_TIME'))


class NativePrefix(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.E5();self.case.setUp();self.addCleanup(self.case.doCleanups)
        c=self.case;self.root=c.root;self.guest=c.guest;self.qualification=c.qualification
        # New functional candidate uses a same-source build. Historical reuse
        # positive controls remain executable in the frozen 0aa2034 baseline.
        self.raw=[]
        for i,(run,obs) in enumerate(zip(c.runs,c.observations)):
            run.update(integrated_hardware=True,observation_profile='012-E',build_source_commit=c.q['source_commit'],qualification_sha256=f1.sha(self.qualification),
                       limits_sha256=v.LIMITS_SHA,observer_sha256=v.OBS_SHA,boot_sha256=v.BOOT_SHA)
            obs.update(run,schema='dana-012e-observation-v1',observation_limits=v.LIMITS,virtual_seconds=12.01)
            rows=copy.deepcopy(obs['events'])
            for token,value in ((1,100),(2,1000000)):
                rows.append(dict(kind='progress',origin='debugger_observation',state=copy.deepcopy(rows[0]['state']),token=token,totalcycles=value,cycle_api='native_debugger_totalcycles',virtual_seconds=.1*token))
            self.raw.append(rows)
            (self.root/f'run-{i+1}'/'cycles.log').write_text('DANA012E token=1 cycles=64\nDANA012E token=2 cycles=F4240\n')
        self.flush()
    def flush(self):
        for i,(run,obs,rows) in enumerate(zip(self.case.runs,self.case.observations,self.raw)):
            d=compressed(rows);obs.update(d,event_count=len(d['events']))
            obs['first_instruction']=next(e['state'] for e in d['events'] if e['kind']=='first_instruction')
            unknown=next((e for e in d['events'] if e.get('address')==0xfffff90c),None)
            if unknown:
                dep={k:unknown[k] for k in ('kind','address','data','mask','state','byte_addresses','width_bits','origin','tap_id')}
                dep.update(event_seq=unknown['seq'],effective_address=0xfffff90c);obs['dependency']=dep;obs['reason']='BLOCKED_HARDWARE'
            else:obs['dependency']=None;obs['reason']='OBSERVATION_LIMIT_TIME'
            folder=self.root/f'run-{i+1}';obs['trace_bytes']=(folder/'guest.trace').stat().st_size
            (folder/'run.json').write_text(json.dumps(run));(folder/'observation.json').write_text(json.dumps(obs))
    def result(self):return v.verify_pair(self.root,self.guest,self.qualification,self.case.source)
    def test_genuine_prefix_without_dependency_is_valid_not_full_boot(self):
        for rows in self.raw:rows[:]=[e for e in rows if e.get('address')!=0xfffff90c]
        self.flush();r=self.result()
        self.assertEqual(r['status'],'PARTIAL');self.assertIsNone(r['dependency']);self.assertFalse(r['full_boot'])
        self.assertEqual(r['components']['pfsel']['status'],'PASS');self.assertEqual(r['components']['uart1_tx']['status'],'NOT_REACHED')
    def test_new_dependency_is_kept_with_actual_instruction(self):
        r=self.result();self.assertEqual(r['status'],'PARTIAL')
        self.assertEqual(r['dependency']['effective_address'],0xfffff90c)
        self.assertEqual(r['first_unsupported_instruction']['PC'],0x8400)
    def test_polls_and_cycles_are_not_functional_progress(self):
        for rows in self.raw:
            rows[:]=[e for e in rows if e.get('address')!=0xfffff90c]
            rows.insert(-2,poll(time=.05))
        for i in (1,2):
            p=self.root/f'run-{i}/guest.trace';p.write_text(p.read_text()+'00008500: move.w (a0),d0\n')
        self.flush();r=self.result()
        self.assertEqual(r['runs'][0]['activity']['classification'],'POLLING_WITHOUT_OBSERVED_CLOCK_TRANSITION')
        self.assertFalse(r['runs'][0]['activity']['functional_progress_proven'])
    def test_unreached_limit_and_changed_limits_are_blocked(self):
        for rows in self.raw:rows[:]=[e for e in rows if e.get('address')!=0xfffff90c]
        self.flush();obs=self.case.observations[0];obs['virtual_seconds']=.2
        p=self.root/'run-1/observation.json';p.write_text(json.dumps(obs));self.assertEqual(self.result()['status'],'BLOCKED')
        obs['virtual_seconds']=12.01;obs['observation_limits']=dict(v.LIMITS,max_virtual_seconds=600)
        p.write_text(json.dumps(obs));self.assertEqual(self.result()['status'],'BLOCKED')
    def test_uart_lcd_and_st_require_their_own_cpu_chains(self):
        for i,rows in enumerate(self.raw):
            rows[:]=[e for e in rows if e.get('address')!=0xfffff90c]
            additions=[]
            def bus(kind,a,value,mask=65535):
                pc=0x8500+len(additions)*4
                e=poll(pc=pc,time=.02+len(additions)/10000);e.update(kind=kind,address=a,data=value,mask=mask,
                    tap_id='f1_'+kind,byte_addresses=f1.selected_bytes(dict(address=a,mask=mask)),width_bits=16 if mask==65535 else 8)
                additions.append(e)
            bus('write',0xfffff900,0xa100);bus('write',0xfffff906,0x0800,0xff00)
            bus('read',0xfffff906,0x2800);bus('write',0xfffff906,0x41,255)
            bus('read',0xfffff440,4,255);bus('write',0xfffff420,0,255)
            bus('write',0xfffff800,0);bus('write',0xfffff802,0x2307);bus('read',0xfffff802,0x2087)
            bus('write',0xfffff420,8,255);bus('read',0xfffff800,0xaa)
            for a,value,mask in ((0xfffffa00,0x3f,65535),(0xfffffa02,0xd440,65535),(0xfffffa04,35,255),
                    (0xfffffa08,560,65535),(0xfffffa0a,159,65535),(0xfffffa20,8<<8,65280),(0xfffffa26,0x80,255)):
                bus('write',a,value,mask)
            rows[-2:-2]=additions
            folder=self.root/f'run-{i+1}';p=folder/'guest.trace';p.write_text(p.read_text()+''.join(f"{e['state']['CURPC']:08x}: synthetic peripheral instruction\n" for e in additions))
            (folder/'error.log').write_text('DANA_VZ_UART1_SERIAL_TX count=1 data=41 time=0.030000000\n')
            self.case.observations[i]['guest_lcd']=dict(geometry_configured=True,lssa=0x3fd440,lvpw=35,lxmax=560,lymax=159,lpicf=8,lckcon=0x80,frame_bytes=11200,nonzero_bytes=1)
            (folder/'lcd-frame.bin').write_bytes(bytes([0x80])+bytes(11199))
        self.flush();r=self.result()
        for name in ('uart1_tx','st_greeting','spi2_exchange','lcd_controller','lcd_frame'):self.assertEqual(r['components'][name]['status'],'PASS',(name,r))
        next(e for e in self.raw[0] if e.get('address')==0xfffff440)['data']=0
        next(e for e in self.raw[0] if e.get('address')==0xfffff906 and e['kind']=='read')['data']=0
        self.flush();r=self.result();self.assertEqual(r['components']['st_greeting']['status'],'PARTIAL');self.assertEqual(r['components']['uart1_tx']['status'],'PARTIAL')
        self.assertEqual(r['components']['spi2_exchange']['status'],'PASS')
        next(e for e in self.raw[0] if e.get('address')==0xfffff802 and e['kind']=='read')['data']=0
        self.flush();self.assertEqual(self.result()['components']['spi2_exchange']['status'],'PARTIAL')
    def test_forged_cycle_output_is_blocked(self):
        (self.root/'run-1/cycles.log').write_text('DANA012E token=1 cycles=64\nDANA012E token=2 cycles=F4241\n')
        self.assertEqual(self.result()['status'],'BLOCKED')
    def test_replay_missing_image_or_wrong_build_blocks(self):
        self.case.runs[1]['pid']=self.case.runs[0]['pid'];self.flush();self.assertEqual(self.result()['status'],'BLOCKED')
        self.case.runs[1]['pid']+=1;self.case.observations[0]['build_source_commit']='0'*40
        folder=self.root/'run-1';(folder/'observation.json').write_text(json.dumps(self.case.observations[0]))
        self.assertEqual(self.result()['status'],'BLOCKED')
    def test_undeclared_loss_and_fabricated_dependency_block(self):
        obs=self.case.observations[0];obs['compression_stats']['attempted_raw']+=1
        (self.root/'run-1/observation.json').write_text(json.dumps(obs));self.assertEqual(self.result()['status'],'BLOCKED')
        self.flush();obs['dependency']['effective_address']=0xfffff700
        (self.root/'run-1/observation.json').write_text(json.dumps(obs));self.assertEqual(self.result()['status'],'BLOCKED')
    def add_irq(self):
        for i,rows in enumerate(self.raw):
            end=next(j for j,e in enumerate(rows) if e.get('address')==0xfffff90c)
            state=lambda pc,ir=0x33fc,sp=0x1000,sr=0x2700:dict(CURPC=pc,PC=pc+2,IR=ir,SP=sp,SR=sr)
            additions=[]
            def bus(kind,address,data,pc,mask=65535,role=None,ir=0x33fc,sp=0x1000,sr=0x2700):
                e=dict(kind=kind,address=address,data=data,mask=mask,origin='cpu',tap_id='f1_iack' if kind=='iack' else 'f1_'+kind,side_effects_disabled=False,after_dependency=False,
                       state=state(pc,ir,sp,sr),byte_addresses=f1.selected_bytes(dict(address=address,mask=mask)),width_bits=8*(2 if mask==65535 else 1),virtual_seconds=.05+len(additions)/10000)
                if role:e['role']=role
                additions.append(e)
            bus('write',0xfffff602,2,0x8320);bus('write',0xfffff604,0xd7e4,0x8328);bus('write',0xfffff600,0x33,0x8330)
            bus('iack',0xfffffffc,0x46,0x8600,255)
            bus('read',0x118,0,0x8600);bus('read',0x11a,0x9000,0x8600)
            bus('read',0xfffff60a,1,0x9002,ir=0x3039,sp=0xffa,sr=0x2600)
            for a,value in ((0xffa,0x2700),(0xffc,0),(0xffe,0x8600)):
                bus('read',a,value,0x9004,role='rte',ir=0x4e73,sp=a,sr=0x2600)
            bus('read',0x8600,0x4e71,0x8600,role='resume',ir=0x4e71)
            rows[end:end]=additions
            for n,e in enumerate(rows):e['virtual_seconds']=n/1000
            p=self.root/f'run-{i+1}/guest.trace';p.write_text(p.read_text().replace('00008400:', '00008320: move.w\n00008328: move.w\n00008330: move.w\n00008600: nop\n   (interrupted at 00008600, IRQ 6)\n00009000: move.w\n00009002: move.w\n00009004: rte\n00008600: nop\n00008400:'))
            (self.root/f'run-{i+1}/error.log').write_text('DANA_VZ_TIMER1_COMPARE count=1 tctl=0033\nDANA_VZ_IACK level=6 vector=46 pending=00000002 imr=00000000 ack6=1\n')
        self.flush()
    def test_irq_entry_frame_rte_and_resume_are_required(self):
        self.add_irq();r=self.result();self.assertEqual(r['components']['irq6']['status'],'PASS',r)
        self.assertEqual(r['components']['timer1_compare']['status'],'PASS')
        self.raw[0]=[e for e in self.raw[0] if e.get('role')!='resume'];self.flush()
        self.assertEqual(self.result()['components']['irq6']['status'],'PARTIAL')
    def test_rte_text_or_iack_alone_cannot_qualify_irq(self):
        self.add_irq();self.raw[0]=[e for e in self.raw[0] if e.get('role')!='rte'];self.flush()
        self.assertEqual(self.result()['components']['irq6']['status'],'PARTIAL')
    def test_wrong_restored_pc_or_host_iack_cannot_pass(self):
        self.add_irq();next(e for e in self.raw[0] if e.get('role')=='resume')['state']['CURPC']=0x8602
        self.flush();self.assertNotEqual(self.result().get('components',{}).get('irq6',{}).get('status'),'PASS')
        next(e for e in self.raw[0] if e.get('kind')=='iack')['origin']='host';self.flush()
        self.assertEqual(self.result()['status'],'BLOCKED')


class Syntax(unittest.TestCase):
    def test_rte_prefetch_is_not_misidentified_as_resume(self):
        block=(f1.HERE/'f1_emutos_boot.lua').read_text().split('                local role=nil',1)[1].split('                if address<0x800',1)[0]
        script="""
local rte_active,rte_pc=false,nil;local e6=true;local kind='read'
local cpu={state={IR={value=0x4e73},CURPC={value=0x9004}}}
local function sample()
 local role=nil
"""+block+"""
 return role
end
assert(sample()=='rte')
cpu.state.IR.value=0x4e71;assert(sample()=='rte_prefetch')
cpu.state.CURPC.value=0x8600;assert(sample()=='resume')
assert(sample()==nil)
"""
        check_lua(script)
    def test_modified_lua_parses(self):
        for name in ('f1_emutos_boot.lua','dana_012e_observer.lua'):
            check_lua('assert(load('+json.dumps((f1.HERE/name).read_text())+'))')
    def test_python_lua_boolean_configuration_round_trip(self):
        from d1_2_run import lua as old_lua
        check_lua('local cfg='+old_lua(dict(integrated_recovery=True))+';assert(cfg.integrated_recovery==nil)')
        code='local cfg='+f1.lua(dict(integrated_recovery=True,full_boot=False,timeout=.25))
        check_lua(code+';assert(cfg.integrated_recovery==true and cfg.full_boot==false and cfg.timeout==0.25)')
        with self.assertRaises(ValueError):f1.lua(float('nan'))
    def test_native_cycle_checkpoint_parses_unique_console_tokens(self):
        block=(f1.HERE/'f1_emutos_boot.lua').read_text().split('local function cycle_checkpoint()',1)[1].split('emu.register_periodic',1)[0]
        script='''
local host=false;local checkpoints=0;local cycle_start=nil
local cfg={observation_limits={max_checkpoints=512,max_cycles=400000000},output='''+lua(tempfile.gettempdir())+'''}
local count=0;local manager={machine={debugger={consolelog={}}}}
manager.machine.debugger.command=function(self,command)
    local token=assert(command:match(',0x(%x+),totalcycles'))
    self.consolelog[#self.consolelog+1]='DANA012E token='..token..' cycles='..string.format('%X',tonumber(token,16)*100)
end
local function record(e) assert(host and e.totalcycles==e.token*100);count=count+1;return e end
local function cycle_checkpoint()
'''+block+'''
for i=1,12 do assert(cycle_checkpoint()==nil) end
assert(count==12 and not host)
'''
        with tempfile.TemporaryDirectory(prefix='012e-cycles-') as temp:
            script=script.replace(lua(tempfile.gettempdir()),lua(temp),1);check_lua(script)
    def test_counter_uses_native_read_only_command_not_estimates(self):
        source=(f1.HERE/'f1_emutos_boot.lua').read_text()
        self.assertIn('0x%X,totalcycles',source);self.assertIn('Missing native totalcycles expression',source)
        self.assertNotIn('trace off', (f1.HERE/'dana_012e_observer.lua').read_text())

if __name__=='__main__':unittest.main()
