#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Offline protocol/control regressions, never native emulator qualification."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import dana_012d_verify as integrated
import f1_emutos_run as f1
from d2_3_test import build_record
from lua_contract import check_lua


class Provenance(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='012d-offline-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.binary,self.qualification,self.q=build_record(self.root)
        self.manifest=self.binary.parent.parent/'source-manifest.json'
        self.m=json.loads(self.manifest.read_text())
    def flush(self):
        self.manifest.write_text(json.dumps(self.m));self.q['source_manifest_sha256']=f1.sha(self.manifest)
        self.qualification.write_text(json.dumps(self.q))
    def test_current_source_still_qualifies_read_only(self):
        before={p:p.read_bytes() for p in (self.binary,self.qualification,self.manifest)}
        self.assertEqual(f1.qualify_pfsel_build(self.binary,self.qualification),self.q)
        self.assertEqual(before,{p:p.read_bytes() for p in before})
    def test_first_content_predicate_is_precise(self):
        for key,value in (('status','PREPARED'),('source_commit','0'*40),('mame_commit','0'*40),
                          ('variant','stable'),('binary_sha256','0'*64),('driver_sha256','0'*64)):
            with self.subTest(key=key):
                original=copy.deepcopy(self.m);self.m[key]=value;self.flush()
                with self.assertRaisesRegex(ValueError,'PFSEL_QUALIFICATION:manifest.'+key):f1.qualify_pfsel_build(self.binary,self.qualification)
                self.m=original
    def test_manifest_hash_is_not_relaxed(self):
        self.manifest.write_text(self.manifest.read_text()+'\n')
        self.assertEqual(integrated.probe(self.binary,self.qualification)['first_failing_predicate'],'PFSEL_QUALIFICATION:manifest.sha256')
    def test_path_and_missing_manifest_are_distinct(self):
        self.manifest.unlink()
        with self.assertRaisesRegex(ValueError,'manifest.regular_file'):f1.qualify_pfsel_build(self.binary,self.qualification)
        with self.assertRaisesRegex(ValueError,'binary.absolute_path'):f1.qualify_pfsel_build(Path('diag/bin/dana-diag'),self.qualification)
    def test_build_command_and_binary_path_remain_bound(self):
        for key,value in (('build_command',['make','SUBTARGET=danastable']),('binary','/another/diag/bin/dana-diag'),('build_exit_code',True)):
            with self.subTest(key=key):
                q=dict(self.q);q[key]=value;self.qualification.write_text(json.dumps(q))
                with self.assertRaisesRegex(ValueError,'qualification.'+key):f1.qualify_pfsel_build(self.binary,self.qualification)
    def test_known_build_reuse_requires_both_pinned_source_and_real_git_bytes(self):
        self.q['source_commit']=self.m['source_commit']=integrated.SOURCE_012C;self.flush()
        constants={k:self.q[k] for k in ('source_commit','binary_sha256','source_manifest_sha256')}
        constants['qualification_sha256']=f1.sha(self.qualification)
        before=[p.read_bytes() for p in (self.binary,self.manifest,self.qualification)]
        with patch.object(f1,'REUSE_012C',constants):
            with patch.object(f1.subprocess,'check_output',wraps=subprocess.check_output) as git:
                with self.assertRaisesRegex(ValueError,'reuse.compiled_driver_sha256'):
                    f1.qualify_pfsel_build(self.binary,self.qualification)
                self.assertTrue(any('show' in row.args[0] for row in git.call_args_list))
        self.assertEqual(before,[p.read_bytes() for p in (self.binary,self.manifest,self.qualification)])
    def test_arbitrary_old_source_cannot_be_relabelled(self):
        self.q['source_commit']=self.m['source_commit']='749517b2f48c9788e5555071561e738017ac5f7c';self.flush()
        with self.assertRaisesRegex(ValueError,'reuse.source_commit'):f1.qualify_pfsel_build(self.binary,self.qualification)
    def test_reuse_cannot_replace_original_qualification_or_executable(self):
        self.q['source_commit']=self.m['source_commit']=integrated.SOURCE_012C;self.flush()
        with self.assertRaisesRegex(ValueError,'reuse.binary_sha256'):f1.qualify_pfsel_build(self.binary,self.qualification)
    def test_actual_supplied_subset_when_available(self):
        root=os.getenv('DANA_012C_EVIDENCE_DIR')
        if not root:self.skipTest('Original private evidence not supplied to this offline run')
        root=Path(root);index=json.loads((root/'evidence_sha256.json').read_text())
        for p in root.rglob('*'):
            if p.is_file() and p.name!='evidence_sha256.json':
                actual=f1.sha(p);expected=index[str(p.relative_to(root))]
                self.assertEqual(actual,expected,
                    'relative_path='+str(p.relative_to(root))+' expected_sha256='+index[str(p.relative_to(root))]+
                    ' calculated_sha256='+actual+' origin=EXPLICIT_DANA_012C_EVIDENCE_DIR'+
                    ' selected_evidence='+str(p.absolute())+' resolved='+str(p.resolve())+
                    ' index='+str((root/'evidence_sha256.json').absolute())+
                    ' index_sha256='+f1.sha(root/'evidence_sha256.json'))
        q=json.loads((root/'binary_qualification.json').read_text());m=json.loads((root/'source-manifest.json').read_text())
        self.assertEqual(f1.sha(root/'binary_qualification.json'),integrated.QUALIFICATION_012C_SHA)
        self.assertEqual(f1.sha(root/'source-manifest.json'),f1.REUSE_012C['source_manifest_sha256'])
        for key in ('source_commit','driver_sha256','mame_commit','variant','binary_sha256'):self.assertEqual(q[key],m[key])
        self.assertEqual(m['driver_sha256'],integrated.DRIVER_012C_SHA)
        self.assertEqual(hashlib.sha256(subprocess.check_output(['git','-C',str(f1.PROJECT),'show',integrated.SOURCE_012C+':src/mame/skeleton/alphasdana.cpp'])).hexdigest(),m['driver_sha256'])
        self.assertEqual(m['status'],'BUILT_DIAG')


class ReusedEvidence(unittest.TestCase):
    def reuse(self,case,objects):
        self.addCleanup(case.doCleanups)
        case.q['source_commit']=integrated.SOURCE_012C
        manifest=case.binary.parent.parent/'source-manifest.json'
        m=json.loads(manifest.read_text());m['source_commit']=integrated.SOURCE_012C
        manifest.write_text(json.dumps(m));case.q['source_manifest_sha256']=f1.sha(manifest)
        case.qualification.write_text(json.dumps(case.q))
        for obj in objects:obj.update(build_source_commit=integrated.SOURCE_012C,qualification_sha256=f1.sha(case.qualification))
        constants={k:case.q[k] for k in ('source_commit','binary_sha256','source_manifest_sha256')}
        constants['qualification_sha256']=f1.sha(case.qualification)
        return patch.object(f1,'REUSE_012C',constants)
    def test_pfsel_retains_harness_and_build_identities(self):
        from d2_3_test import NativeEvidence
        case=NativeEvidence();case.setUp()
        with self.reuse(case,[case.run,case.obs]):
            self.assertEqual(case.result()['status'],'BLOCKED')
            del case.obs['build_source_commit']
            self.assertEqual(case.result()['status'],'BLOCKED')
    def test_both_authentic_guest_records_bind_reused_build(self):
        from d2_3_test import E5
        case=E5();case.setUp()
        with self.reuse(case,case.runs+case.observations):
            self.assertEqual(case.verify()['status'],'BLOCKED_HARNESS')
            del case.observations[1]['build_source_commit']
            self.assertEqual(case.verify()['status'],'BLOCKED_HARNESS')


class Integrated(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='012d-synthetic-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.events=[]
        def bus(kind,address,data,mask=65535):
            row=dict(seq=len(self.events),kind=kind,address=address,data=data,mask=mask,origin='cpu',
                     tap_id='f1_iack' if kind=='iack' else 'f1_'+kind,side_effects_disabled=False,after_dependency=False,
                     state=dict(CURPC=0x8300,PC=0x8302,SP=0x1000,SR=0x2000,IR=0x4e71))
            row['byte_addresses']=f1.selected_bytes(row);row['width_bits']=8*len(row['byte_addresses'])
            self.events.append(row);return row
        bus('write',0xfffff602,2);bus('write',0xfffff604,0xd7e4);bus('write',0xfffff600,0x33)
        bus('read',0xfffff900,0);bus('write',0xfffff906,0x41,255)
        bus('write',0xfffff800,0);bus('write',0xfffff802,0x2307);bus('read',0xfffff802,0x2087);bus('read',0xfffff800,0xaa)
        bus('iack',0xfffffffc,0x46,255);bus('read',0x118,0);bus('read',0x11a,0x9000)
        self.obs=dict(events=self.events,guest_lcd={})
        self.accepted=dict(status='OBSERVED_UNQUALIFIED_SINGLE_RUN',dependency_event_seq=99)
        (self.root/'guest.trace').write_text('00008300: nop\n00009000: synthetic handler\n')
        (self.root/'error.log').write_text('DANA_VZ_UART1_TX data=41 char=A\nDANA_VZ_TIMER1_COMPARE count=1 tctl=0033\nDANA_VZ_IACK level=6 vector=46 pending=00000002 imr=00000000 ack6=1\n')
    def result(self):
        (self.root/'observation.json').write_text(json.dumps(self.obs))
        return integrated.per_run(self.root,self.accepted)
    def test_causal_integrated_synthetic_control(self):
        r=self.result()
        for key in ('timer1','uart1_registers','uart1_tx','spi2_registers','st_greeting','irq6'):self.assertEqual(r[key]['status'],'PASS',key)
        self.assertEqual(r['full_boot']['status'],'BLOCKED')
    def test_post_dependency_tail_cannot_pass_irq(self):
        self.accepted['dependency_event_seq']=8;self.assertEqual(self.result()['irq6']['status'],'BLOCKED')
    def test_host_iack_is_rejected(self):
        self.events[9]['origin']='host'
        with self.assertRaisesRegex(ValueError,'IACK provenance'):self.result()
    def test_irq_wrong_vector_or_pending_is_not_delivery(self):
        self.events[9]['data']=0x44;self.assertEqual(self.result()['irq6']['status'],'BLOCKED')
        self.events[9]['data']=0x46
        p=self.root/'error.log';p.write_text(p.read_text().replace('pending=00000002','pending=00000000'))
        self.assertEqual(self.result()['irq6']['status'],'BLOCKED')
    def test_irq_without_vector_fetch_or_handler_trace_is_not_pass(self):
        self.events[10]['address']=0x120;self.assertEqual(self.result()['irq6']['status'],'BLOCKED')
        self.events[10]['address']=0x118;(self.root/'guest.trace').write_text('00008300: nop\n')
        self.assertEqual(self.result()['irq6']['status'],'BLOCKED')
    def test_uart_access_is_not_tx_and_log_must_match(self):
        self.events[4]['address']=0xfffff904;self.assertEqual(self.result()['uart1_tx']['status'],'BLOCKED')
        self.events[4]['address']=0xfffff906;self.events[4]['data']=0x42
        self.assertEqual(self.result()['uart1_tx']['status'],'BLOCKED')
    def test_arbitrary_aa_or_wrong_lane_is_not_st_greeting(self):
        self.events[6]['data']=0;self.assertEqual(self.result()['st_greeting']['status'],'BLOCKED')
        self.events[6]['data']=0x2307;self.events[8]['mask']=0xff00;self.events[8]['data']=0xaa00
        self.assertEqual(self.result()['st_greeting']['status'],'BLOCKED')
    def test_frame_is_size_geometry_and_content_checked(self):
        frame=bytes([0x80])+bytes(11199);(self.root/'lcd-frame.bin').write_bytes(frame)
        self.obs['guest_lcd']=dict(geometry_configured=True,lssa=0x3fd440,lvpw=35,lxmax=560,lymax=159,lpicf=8,lckcon=0x80,frame_bytes=11200,nonzero_bytes=1)
        value=self.result()['lcd_frame'];self.assertEqual(value['status'],'PASS');self.assertFalse(value['pre_dependency_time_proven'])
        self.assertTrue((self.root/'lcd-screen.png').read_bytes().startswith(b'\x89PNG'))
        self.obs['guest_lcd']['nonzero_bytes']=2
        with self.assertRaisesRegex(ValueError,'metadata mismatch'):self.result()
    def test_first_unsupported_instruction_is_read_from_raw_trace(self):
        instruction=integrated.dependency_instruction(self.root,dict(state=dict(CURPC=0x9000)))
        self.assertEqual(instruction['PC'],0x9000);self.assertEqual(instruction['disassembly'],'synthetic handler')
        with self.assertRaisesRegex(ValueError,'instruction absent'):
            integrated.dependency_instruction(self.root,dict(state=dict(CURPC=0x9002)))
    def test_missing_or_unequal_pair_never_scores_components(self):
        with patch.object(f1,'verify_e4_pair',return_value=dict(status='REAL_PROGRESS_PASS_SCOPED',raw_bus_prefix_equal=False)):
            result=integrated.verify(self.root,self.root,self.root/'qualification')
            self.assertEqual(result['status'],'BLOCKED');self.assertNotIn('components',result)


class Observer(unittest.TestCase):
    def test_actual_lua_iack_tap_has_no_host_effects(self):
        source=(f1.HERE/'f1_emutos_boot.lua').read_text()
        block=source.split('    if e5 and cfg.integrated_recovery then',1)[1].split("    manager.machine.debugger:command('trace",1)[0]
        script='''
local e5=true; local cfg={integrated_recovery=true}; local taps={}
local pending_dependency=nil; local pending=nil; local done=false; local host=false
local count=0; local item=nil; local callback=nil
local function loaded() return true end
local manager={machine={side_effects_disabled=function() return false end}}
local function record(e,origin) count=count+1;item=e;item.origin=origin end
local function bus_bytes(address,mask) assert(address==0xfffffffc and mask==255);return {address+1} end
local cpu={spaces={cpu_space={data_width=16,install_read_tap=function(self,a,b,name,fn) callback=fn;return {} end}}}
if e5 and cfg.integrated_recovery then
'''+block+'''
callback(0xfffffffc,0x46,255)
assert(count==1 and item.origin=='cpu' and item.kind=='iack' and item.tap_id=='f1_iack')
assert(item.address==0xfffffffc and item.byte_addresses[1]==0xfffffffd and item.data==0x46 and not item.after_dependency)
host=true;callback(0xfffffffc,0x46,255);assert(count==1)
'''
        check_lua(script)
    def test_full_modified_lua_parses(self):
        for name in ('f1_emutos_boot.lua','d2_3_pfsel_boot.lua'):
            check_lua('assert(load('+json.dumps((f1.HERE/name).read_text())+'))')


if __name__=='__main__':unittest.main()
