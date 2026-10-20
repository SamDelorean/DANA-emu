#!/usr/bin/env python3
"""STATIC ONLY: extracted C++ latch, synthetic evidence and actual Lua parsing."""
import copy
import hashlib
import json
import re
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import d2_3_pfsel_run as pf
import f1_emutos_run as f1
from f1_e4_test import Evidence as E4Fixture
from d2_1_pllfsr_contract_test import method_body
from lua_contract import check_lua

ROOT=Path(__file__).resolve().parents[1]
DRIVER=ROOT/'src/mame/skeleton/alphasdana.cpp'


def build_record(root):
    binary=root/'diag/bin/dana-diag';binary.parent.mkdir(parents=True,exist_ok=True)
    binary.write_text('SYNTHETIC OFFLINE INPUT, NEVER EXECUTE\n');binary.chmod(0o755)
    source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    q=dict(schema='dana-d23-build-v1',source_commit=source,driver_sha256=f1.sha(DRIVER),mame_commit=f1.MAME_PIN,
           binary=str(binary),binary_sha256=f1.sha(binary),variant='diag',subtarget='danadiag',build_exit_code=0,
           build_command=['make','-j3','SUBTARGET=danadiag','DEBUG=1','SOURCES=src/mame/skeleton/alphasdana.cpp'])
    manifest=binary.parent.parent/'source-manifest.json'
    manifest.write_text(json.dumps(dict(status='BUILT_DIAG',source_commit=source,driver_sha256=q['driver_sha256'],
                                       mame_commit=f1.MAME_PIN,variant='diag',binary_sha256=q['binary_sha256'])))
    q['source_manifest_sha256']=f1.sha(manifest)
    path=root/'binary_qualification.json';path.write_text(json.dumps(q))
    return binary,path,q


class SourceContracts(unittest.TestCase):
    def test_actual_extracted_cpp_latch_all_bits_and_reset(self):
        source=DRIVER.read_text()
        methods='\n'.join(method_body(source,p) for p in (r'void pfsel_reset\(\)\s*',r'u8 pfsel_r\(\)\s*',r'void pfsel_w\(u8 data\)\s*'))
        code='#include <cstdint>\n#include <cassert>\nusing u8=std::uint8_t;\nstruct Latch {u8 m_pfsel=0xc5;\n'+methods+'''\n};
int main(){Latch p;p.pfsel_reset();assert(p.pfsel_r()==0xc5 && p.pfsel_r()!=0x87);
for(unsigned v: {0u,1u,0x80u,0xffu}){p.pfsel_w(v);assert(p.pfsel_r()==v);assert(p.pfsel_r()==v);}
for(unsigned v=0;v<256;v++){p.pfsel_w(v);assert(p.pfsel_r()==v);}
auto saved=p.pfsel_r();p.pfsel_w(0x3c);p.pfsel_w(saved);assert(p.pfsel_r()==saved);
p.pfsel_reset();assert(p.pfsel_r()==0xc5);}
'''
        code=code.replace('#include <cassert>','#include <cassert>\n#include <initializer_list>')
        with tempfile.TemporaryDirectory(prefix='pfsel-static-cpp-') as tmp:
            root=Path(tmp);(root/'test.cpp').write_text(code)
            compiler=shutil.which('c++');self.assertIsNotNone(compiler)
            subprocess.run([compiler,'-std=c++20','-Wall','-Wextra','-Werror',str(root/'test.cpp'),'-o',str(root/'logic')],check=True,timeout=60)
            subprocess.run([str(root/'logic')],check=True,timeout=10)

    def test_individual_byte_decode_save_reset_and_no_neighbors(self):
        src=DRIVER.read_text()
        self.assertEqual(src.count('save_item(NAME(m_pfsel));'),1)
        self.assertIn('pfsel_reset();',method_body(src,r'void alphasdana_state::machine_reset\(\)\s*'))
        self.assertEqual(src.count('map(0xfffff42b, 0xfffff42b).rw(FUNC(alphasdana_state::pfsel_r), FUNC(alphasdana_state::pfsel_w));'),1)
        self.assertIn('map(0xfffff428,0xfffff42a).rw(FUNC(alphasdana_state::pf_r),FUNC(alphasdana_state::pf_w));',src)
        self.assertNotIn('map(0x00fff42',src)
        for start,end in re.findall(r'map\((0x[0-9a-f]+), (0x[0-9a-f]+)\)',src):
            a,b=int(start,16),int(end,16)
            if a<=0xfffff42f and b>=0xfffff428:self.assertIn((a,b),((0xfffff428,0xfffff42a),(0xfffff42b,0xfffff42b)))
            self.assertFalse(0x00fff000<=a<=0x00ffffff)
        self.assertTrue(f1.implemented_byte(0xfffff42a,'read',True))
        self.assertTrue(f1.implemented_byte(0xfffff42b,'write',True))
        self.assertFalse(f1.implemented_byte(0xfffff42b,'read',False))

    def test_preserved_qualified_portc_and_pllfsr_methods(self):
        old=subprocess.check_output(['git','-C',str(ROOT),'show','56a0a0040edfc161e45c1131692a64c3649fe3af:src/mame/skeleton/alphasdana.cpp'],text=True)
        new=DRIVER.read_text()
        for pattern in (r'void portc_reset\(\)\s*',r'u8 pcpden_r\(\)\s*',r'void pcpden_w\(u8 data\)\s*',
                        r'u8 pcsel_r\(\)\s*',r'void pcsel_w\(u8 data\)\s*',r'u16 pllfsr_r\(\)\s*',
                        r'void alphasdana_state::pllfsr_w\(offs_t, u16 data, u16 mem_mask\)\s*'):
            self.assertEqual(method_body(old,pattern),method_body(new,pattern))

    def test_fixture_identity_and_aligned_word_encoding(self):
        code,layout=pf.fixture()
        self.assertEqual((len(code),hashlib.sha256(code).hexdigest()),(294,'7a73d9966b07eb8669a393735fc7640ea917f25a7428a53eb1afa1de4b7d3a1a'))
        self.assertEqual(0x4008+struct.unpack('>h',code[8:10])[0],layout['post'])
        self.assertIn(bytes.fromhex('3039fffff42a'),code)
        self.assertNotIn(bytes.fromhex('3039fffff42b'),code)

    def test_actual_lua_modes_keep_old_binary_pfsel_unimplemented(self):
        src=(ROOT/'tests/f1_emutos_boot.lua').read_text()
        functions=src[src.index('local function implemented_byte'):src.index('emu.register_prestart')]
        check_lua('local e5=false\n'+functions+"\nassert(first_unsupported(bus_bytes(0xfffff42a,0xff),'read')==0xfffff42b)")
        check_lua('local e5=true\n'+functions+"\nassert(first_unsupported(bus_bytes(0xfffff42a,0xff),'read')==nil)\nassert(first_unsupported(bus_bytes(0xfffff42a,0xff00),'read')==nil)\nassert(first_unsupported(bus_bytes(0xfffffa06,0xff00),'read')==0xfffffa06)")
        for file in ('f1_emutos_boot.lua','d2_3_pfsel_boot.lua'):
            check_lua('assert(load('+json.dumps((ROOT/'tests'/file).read_text())+'))')

    def test_pfsel_lua_save_and_cpu_reset_callbacks_without_emulator(self):
        payload,layout=pf.fixture()
        for mode in ('save_restore','reset'):
            cfg=dict(output='/mock',hex=payload.hex(),execution=mode,revision='D2.3',
                     **{k:layout[k] for k in ('endpoint','post','post_read','store','stop')})
            setup='local cfg='+pf.lua(cfg)+'''
local cb,mock_taps={},{}
local in_tap,exits,output,port=false,0,'',0xc5
local ram={}
local state={CURPC={value=0x4000},PC={value=0x4002},SP={value=0x8000},SR={value=0x2700},IR={value=0}}
local cpu={state=state,debug={bpclear=function() assert(not in_tap) end,bpset=function() assert(not in_tap) end,go=function() assert(not in_tap) end}}
local space={data_width=16,read_u8=function(_,a) return a==0xfffff42b and port or 0 end,
 read_u16=function(_,a) return ram[a] or 0 end,write_u32=function() end,
 write_u8=function(_,a,v) if a==0xfffff42b then port=v end end,write_u16=function(_,a,v) ram[a]=v end}
for _,kind in ipairs({'read','write'}) do space['install_'..kind..'_tap']=function(_,a,b,id,fn) mock_taps[kind]=fn;return {} end end
cpu.spaces={program=space}
manager={machine={devices={[':maincpu']=cpu},debugger={execution_state='stop',command=function() assert(not in_tap) end},
 side_effects_disabled=function() return false end,exit=function() assert(not in_tap);exits=exits+1 end,
 soft_reset=function() assert(not in_tap) end,buffer_save=function() assert(not in_tap);return 'mock native API' end,
 buffer_load=function() assert(not in_tap);port=0x5a;return true end}}
emu={time=function() return .1 end,register_prestart=function(fn) cb.start=fn end,
 register_periodic=function(fn) cb.periodic=fn end,add_machine_reset_notifier=function(fn) return {} end}
os.getenv=function() return 'mock-config' end;dofile=function() return cfg end
io.open=function(path) return {seek=function() return 1024 end,close=function() end,
 write=function(_,text) if path:find('observation.json',1,true) then output=output..text end end} end
'''
            steps='''
cb.start();cb.periodic()
port=0x5a;ram[0x20000]=1;state.CURPC.value=cfg.endpoint;cb.periodic()
if cfg.execution=='reset' then
    assert(exits==0);cb.start();port=0xc5
    local function access(kind,a,d,mask,pc)
        state.CURPC.value=pc;in_tap=true;assert(mock_taps[kind](a,d,mask)==nil);in_tap=false;assert(exits==0)
    end
    for _,v in ipairs({{0,0},{2,0x8000},{4,0},{6,0x4000}}) do access('read',v[1],v[2],0xffff,0) end
    access('read',0x20000,1,0xffff,0x4000)
    access('read',0xfffff42a,0xc5,0xff,cfg.post_read)
    access('write',0x20002,0xc5,0xffff,cfg.store);ram[0x20002]=0xc5
    state.CURPC.value=cfg.stop+4;state.PC.value=cfg.stop+6;cb.periodic()
    assert(output:find('"kind":"cpu_reset_complete"',1,true))
else assert(output:find('"kind":"state_restored"',1,true)) end
assert(exits==1 and output:find('"status":"CAPTURED"',1,true))
'''
            with self.subTest(mode=mode):check_lua(setup+(ROOT/'tests/d2_3_pfsel_boot.lua').read_text()+steps)


class NativeEvidence(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='d23-synthetic-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.binary,self.qualification,self.q=build_record(self.root)
        self.code,self.layout=pf.fixture();self.events=[]
        def add(kind,origin='host_observation',epoch=0,**kw):
            self.events.append(dict(kind=kind,origin=origin,epoch=epoch,request_id=epoch,**kw))
        def cpu(kind,address,data,mask,pc,epoch=0):
            add(kind,'cpu',epoch,address=address,data=data,mask=mask,pc=pc,tap_id='pfsel_'+kind)
        for a,d in ((0,0),(2,0x8000),(4,0),(6,0x4000)):cpu('read',a,d,65535,0)
        add('profile_initial',value=0xc5,pc=0x4000,sp=0x8000)
        cpu('read',pf.MARKER,0,65535,0x4000);cpu('write',pf.MARKER,1,65535,0x400a)
        snapshots={e['read_pc']:e for e in self.layout['snapshots']}
        values={}
        for wanted in self.layout['expected']:
            data=wanted['value'] if wanted['value'] is not None else 0x77a5 if wanted['mask']==65535 else 0x6600
            cpu(wanted['kind'],wanted['address'],data,wanted['mask'],wanted['pc'])
            if wanted['pc'] in snapshots:
                s=snapshots[wanted['pc']];value=data & wanted['mask'];values[s['address']]=value
                cpu('write',s['address'],value,65535,s['store_pc'])
        add('fixture_complete',value=0x5a,pc=self.layout['endpoint'],sp=0x8000)
        add('reset_request','host_request',api='soft_reset',value=0x5a);self.events[-1]['request_id']=1
        add('reset_transition','native_notification',1,value=0x5a)
        for a,d in ((0,0),(2,0x8000),(4,0),(6,0x4000)):cpu('read',a,d,65535,0,1)
        cpu('read',pf.MARKER,1,65535,0x4000,1)
        cpu('read',0xfffff42a,0xc5,255,self.layout['post_read'],1)
        cpu('write',pf.RESULT,0xc5,65535,self.layout['store'],1)
        add('cpu_reset_complete',epoch=1,marker=1,result=0xc5,sp=0x8000,sr=0x2700,
            pc=self.layout['stop']+2,next_pc=self.layout['stop']+4,post_cpu_event_count=7)
        seed=bytearray(0x400000);seed[:8]=struct.pack('>II',0x8000,0x4000)
        seed[0x4000:0x4000+len(self.code)]=self.code;seed[pf.RESULT:pf.RESULT+2]=bytes.fromhex('a55a')
        (self.root/'initial.ram').write_bytes(seed);seed[pf.MARKER:pf.MARKER+2]=b'\0\1'
        for a,v in values.items():seed[a:a+2]=struct.pack('>H',v)
        (self.root/'final.ram').write_bytes(seed);seed[pf.RESULT:pf.RESULT+2]=b'\0\xc5';(self.root/'reset.ram').write_bytes(seed)
        pcs=sorted({0x4000,0x4006,0x400a,0x4012,self.layout['endpoint']}|{e['pc'] for e in self.layout['expected']}|{e['store_pc'] for e in self.layout['snapshots']})
        pcs += [0x4000,0x4006,self.layout['post'],self.layout['post_read'],self.layout['store'],self.layout['stop']]
        trace='\n'.join(f'{pc:x}: '+('stop #$2700' if pc==self.layout['stop'] else 'synthetic') for pc in pcs)+'\n'
        (self.root/'cpu.trace').write_text(trace)
        self.run=dict(revision='D2.3',variant='diag',execution='reset',source_commit=self.q['source_commit'],
                      binary_sha256=self.q['binary_sha256'],qualification_sha256=f1.sha(self.qualification),fixture_sha256=hashlib.sha256(self.code).hexdigest(),
                      execution_id='a'*32,pid=123,exit_code=0,command=[str(self.binary),'asmdana'])
        self.obs=dict(self.run,status='CAPTURED',events=self.events,trace_bytes=len(trace.encode()))
        self.flush()

    def flush(self):
        for seq,e in enumerate(self.events):e['seq']=seq
        capture=self.events[-1]
        capture.update(event_count=capture['seq'],cpu_event_count=sum(e['origin']=='cpu' for e in self.events))
        (self.root/'run.json').write_text(json.dumps(self.run));(self.root/'observation.json').write_text(json.dumps(self.obs))

    def result(self):
        self.flush();return pf.verify(self.root,self.binary,self.qualification,'reset')

    def test_complete_synthetic_cpu_reset_chain(self):self.assertEqual(self.result()['status'],'PASS')
    def test_native_save_restore_chain(self):
        self.events[:]=self.events[:next(i for i,e in enumerate(self.events) if e['kind']=='reset_request')]
        for kind,value,origin in (('state_saved',0x5a,'host_observation'),('state_mutated',0x3c,'host_request'),('state_restored',0x5a,'host_observation')):
            self.events.append(dict(kind=kind,value=value,origin=origin,epoch=0,request_id=0,bytes=4199000,load_ok=True))
        self.run['execution']=self.obs['execution']='save_restore'
        (self.root/'restored.ram').write_bytes((self.root/'final.ram').read_bytes())
        p=self.root/'cpu.trace';text=p.read_text();offset=text.index('4000:',1);p.write_text(text[:offset]);self.obs['trace_bytes']=p.stat().st_size
        self.flush();self.assertEqual(pf.verify(self.root,self.binary,self.qualification,'save_restore')['status'],'PASS')
        self.events[-1]['value']=0x3c;self.flush()
        self.assertEqual(pf.verify(self.root,self.binary,self.qualification,'save_restore')['status'],'FAIL')
    def test_host_forged_pfsel_read(self):
        self.events[-3]['origin']='host';self.assertEqual(self.result()['status'],'BLOCKED')
    def test_wrong_lane(self):
        self.events[-3]['mask']=65280;self.assertEqual(self.result()['status'],'BLOCKED')
    def test_lost_marker(self):
        self.events[-4]['data']=0;self.assertEqual(self.result()['status'],'BLOCKED')
    def test_missing_transition(self):
        self.events[:]=[e for e in self.events if e['kind']!='reset_transition'];self.assertEqual(self.result()['status'],'BLOCKED')
    def test_duplicate_vector(self):
        self.events.insert(1,copy.deepcopy(self.events[0]));self.assertEqual(self.result()['status'],'BLOCKED')
    def test_unbound_reset_request(self):
        self.events[-3]['request_id']=0;self.assertEqual(self.result()['status'],'BLOCKED')
    def test_wrong_physical_reset_only_fails_with_cpu_ram_corroboration(self):
        self.events[-3]['data']=self.events[-2]['data']=self.events[-1]['result']=0x87
        p=self.root/'reset.ram';d=bytearray(p.read_bytes());d[pf.RESULT:pf.RESULT+2]=b'\0\x87';p.write_bytes(d)
        self.assertEqual(self.result()['status'],'FAIL')
    def test_stale_result_sentinel(self):
        p=self.root/'reset.ram';d=bytearray(p.read_bytes());d[pf.RESULT:pf.RESULT+2]=bytes.fromhex('a55a');p.write_bytes(d)
        self.assertEqual(self.result()['status'],'BLOCKED')
    def test_missing_native_stop(self):
        p=self.root/'cpu.trace';p.write_text(p.read_text().replace('stop #$2700','nop'));self.obs['trace_bytes']=p.stat().st_size
        self.assertEqual(self.result()['status'],'BLOCKED')


class E5(unittest.TestCase):
    # Reuse the established synthetic guest builder, not its E4 test cases.
    def setUp(self):
        E4Fixture.setUp(self);self.binary,self.qualification,self.q=build_record(self.root)
        for i,(run,obs) in enumerate(zip(self.runs,self.observations)):
            for obj in (run,obs):obj.update(revision='F1-E5',binary_sha256=self.q['binary_sha256'],driver_sha256=self.q['driver_sha256'],qualification_sha256=f1.sha(self.qualification))
            run['command'][0]=str(self.binary);obs['schema']='dana-f1-e5-observation-v1'
            old=obs['events'];read=copy.deepcopy(old[-1]);write=copy.deepcopy(read)
            # E4's synthetic UART1 address F906 is now implemented in E5.
            # Exercise the exact first UNIMPLEMENTED byte just after the
            # UART1 register bank, without changing the E4 baseline or
            # rewriting any native guest observation.
            missing=old[-1]
            assert missing['kind']=='read' and missing['address']==0xfffff906
            assert missing['mask']==0xff00 and missing['byte_addresses']==[0xfffff906]
            missing.update(address=0xfffff90c,byte_addresses=[0xfffff90c])
            obs['dependency'].update(address=0xfffff90c,effective_address=0xfffff90c,
                                     byte_addresses=[0xfffff90c])
            read.update(kind='read',address=0xfffff42a,mask=255,data=0xc5,byte_addresses=[0xfffff42b],tap_id='f1_read')
            read['state']=dict(read['state'],CURPC=0x83a2,PC=0x83a4)
            write.update(kind='write',address=0xfffff42a,mask=255,data=0xc5,byte_addresses=[0xfffff42b],tap_id='f1_write')
            write['state']=dict(write['state'],CURPC=0x83a8,PC=0x83aa)
            old[-1:-1]=[read,write]
            for seq,e in enumerate(old):e.update(seq=seq,virtual_seconds=seq/1000)
            obs['event_count']=len(old);obs['dependency']['event_seq']=old[-1]['seq']
            p=self.root/f'run-{i+1}/guest.trace';p.write_text(p.read_text().replace('00008400:', '000083a2: synthetic\n000083a8: synthetic\n00008400:'))
            obs['trace_bytes']=p.stat().st_size
        self.flush()
    flush=E4Fixture.flush
    blocked=E4Fixture.blocked
    def verify(self):
        self.flush();return f1.verify_e4_pair(self.root,self.guest,self.source,self.qualification)
    def test_e5_requires_new_build_and_c5_native_read_write(self):
        result=self.verify()
        self.assertEqual(result['status'],'REAL_PROGRESS_PASS_SCOPED')
        self.assertEqual(result['normalized_dependency']['effective_address'],0xfffff90c)
        self.assertTrue(f1.implemented_byte(0xfffff906,'read',True))
        self.assertFalse(f1.implemented_byte(0xfffff90c,'read',True))
    def test_e5_rejects_wrong_read_profile(self):
        self.observations[0]['events'][-3]['data']=0x87;self.blocked()
    def test_e5_rejects_unqualified_build(self):
        q=json.loads(self.qualification.read_text());q['build_exit_code']=1;self.qualification.write_text(json.dumps(q));self.blocked()
    def test_e5_rejects_missing_or_changed_stage_manifest(self):
        manifest=self.binary.parent.parent/'source-manifest.json'
        original=manifest.read_text();manifest.unlink();self.blocked()
        manifest.write_text(original+'\n');self.blocked()
        manifest.write_text('[]')
        with self.assertRaises(ValueError):f1.qualify_pfsel_build(self.binary,self.qualification,self.source)
    def test_e5_rejects_wrong_source_and_old_binary(self):
        q=json.loads(self.qualification.read_text());q['source_commit']='0'*40;self.qualification.write_text(json.dumps(q));self.blocked()
        self.qualification.write_text(json.dumps(self.q))
        original=f1.sha
        with patch('f1_emutos_run.sha',side_effect=lambda p:f1.BINARY_SHA if Path(p)==self.binary else original(p)):
            with self.assertRaises(ValueError):f1.qualify_pfsel_build(self.binary,self.qualification,self.source)



class IntegratedGPIOAndLCD(unittest.TestCase):
    """Grouped source behavior; no claim that new dana-diag binary was run."""
    def test_rdirect_eight_port_profile(self):
        src=DRIVER.read_text()
        match=re.search(r'static constexpr u8 profile\[32\] = \{([^}]*)\}',src,re.S)
        self.assertIsNotNone(match)
        profile=[int(v,16) for v in re.findall(r'0x[0-9a-f]+',match.group(1))]
        self.assertEqual(profile,[0x60,0,0,0x60,0,0,0x1f,0x10,
            0xc8,0x08,0x10,0xc8,0x44,0,0,0xc5,
            0x1f,0x1d,0,0x3f,0xbf,0x40,0,0xcf,
            0xf9,0,0,0xfd,0x20,0x20,0,0x20])
        self.assertEqual(len(profile),32)
        self.assertIn('gpio_bootstrap_reset();',src)
        for port in ('pb','pd','pe','pf','pg','pj','pk','pm'):
            self.assertIn('FUNC(alphasdana_state::'+port+'_r)',src)
            self.assertIn('FUNC(alphasdana_state::'+port+'_w)',src)

    def test_screen_reads_guest_owned_ram_only(self):
        src=DRIVER.read_text()
        for value in ('required_shared_ptr<u16> m_ram','u16 const word = m_ram[',
                      'BIT(word,15-(x & 15))','m_lssa > 0x400000 - 11200',
                      'm_lpicf != 8','m_lvpw != 35','m_lxmax != 560',
                      'm_lymax != 159','m_lckcon & 0x80',
                      'm_screen->set_size(560,160)',
                      'm_screen->set_screen_update(FUNC(alphasdana_state::screen_update))'):
            self.assertIn(value,src)
        self.assertEqual(560*160//8,11200)
        self.assertEqual(160*35*2,11200)
        self.assertEqual((0x8000>>1)+(159*35)+34,(0x8000+11198)//2)
        self.assertNotIn('m_maincpu->space(AS_PROGRAM).read_byte',src)

    def test_lcd_register_width_save_restore_and_no_fake_page(self):
        src=DRIVER.read_text()
        for name in ('lssa','lvpw','lxmax','lymax','lpicf','lpolcf','lacdrc',
                     'lpxcd','lckcon','lrra','lposr','lgpmr','pwmr','gpio'):
            self.assertEqual(src.count('save_item(NAME(m_'+name+'));'),1)
        for pair in ('0xfffffa00,0xfffffa03','0xfffffa28,0xfffffa29',
                     '0xfffffa08,0xfffffa09','0xfffffa0a,0xfffffa0b'):
            self.assertIn('map('+pair+')',src)
        self.assertNotIn('map(0xfffffa29,',src)
        self.assertIn('m_lrra=0x00ff',src)
        self.assertIn('DANA_LCD_WORD(lrra)',src)
        self.assertNotIn('map(0xfffffa00,0xfffffaff)',src)

    def test_e5_dependency_detector_tracks_new_hardware_model(self):
        self.assertTrue(f1.implemented_byte(0xfffffa27,'write',True))
        self.assertTrue(f1.implemented_byte(0xfffff443,'read',True))
        self.assertTrue(f1.implemented_byte(0xfffff42a,'read',True))
        self.assertFalse(f1.implemented_byte(0xfffffa27,'read',False))
        self.assertFalse(f1.implemented_byte(0xfffffa06,'read',True))
        lua=(ROOT/'tests/f1_emutos_boot.lua').read_text()
        self.assertIn('address>=0xfffffa27',lua)
        self.assertIn('address<=0xfffff443',lua)


class IntegratedSPI2AndKeyboard(unittest.TestCase):
    """Exercise extracted *production C++* handshake / SPI2 / ST queue logic."""
    def test_native_cpp_st_reset_spi2_and_key_events(self):
        src=DRIVER.read_text()
        start=src.index('void alphasdana_state::st_input_reset()')
        end=src.index('void alphasdana_state::lcd_bootstrap_reset()',start)
        methods=src[start:end]
        code=r"""
#include <cstdint>
#include <cassert>
using u8=std::uint8_t;
using u16=std::uint16_t;
using offs_t=unsigned;
#define BIT(value, index) (((value) >> (index)) & 1)
#define COMBINE_DATA(dst) (*(dst)=(*(dst)&~mem_mask)|(data&mem_mask))
struct Keys { unsigned value=0; unsigned read() const { return value; } };
struct alphasdana_state {
    Keys *m_keys;
    u8 m_gpio[32]{};
    u16 m_spi2_data=0, m_spi2_ctrl=0;
    bool m_st_ready=false, m_st_hello=false, m_st_reset_held=false;
    u8 m_st_old_keys=0, m_st_pending_keys=0, m_st_queue_left=0;
    void st_input_reset();
    void pb_w(offs_t, u8);
    u8 pk_r(offs_t);
    void pk_w(offs_t, u8);
    u8 st_exchange(u8);
    void spi2_ctrl_w(offs_t, u16, u16);
};
""" + methods + r"""
int main() {
    Keys k;
    alphasdana_state t;
    t.m_keys=&k;
    t.st_input_reset();
    t.m_gpio[6*4]=0xf9;
    t.m_gpio[6*4+1]=0;
    t.m_gpio[2*4+1]=0; // ST chip select active low.
    assert(!(t.pk_r(1)&4));
    t.pk_w(0,0xfd); // guest PK2 output pulse -> ST ready.
    t.pk_w(0,0xf9); // guest releases PK2 to input.
    assert((t.pk_r(1)&4) && t.m_st_ready);
    t.m_spi2_data=0;
    t.spi2_ctrl_w(0,0x2307,0xffff);
    assert((t.m_spi2_ctrl&0x80) && !(t.m_spi2_ctrl&0x100));
    assert((t.m_spi2_data&0xff)==0xaa);
    t.m_spi2_data=0;
    t.spi2_ctrl_w(0,0x2307,0xffff);
    assert((t.m_spi2_data&0xff)==0);
    k.value=3;
    assert(t.st_exchange(0)==0x42); // 2 keys, ST protocol header.
    assert(t.st_exchange(0)==0x2b); // A
    assert(t.st_exchange(0)==0x7a); // B
    assert(t.st_exchange(0)==0);
    k.value=0;
    assert(t.st_exchange(0)==0x40); // all released.
    t.pb_w(1,0x40); // ST hardware reset high.
    assert(!t.m_st_ready && !(t.pk_r(1)&4));
    t.pb_w(1,0); // release reset.
    assert(t.m_st_ready && t.m_st_hello);
    t.m_gpio[2*4+1]=8; // ST deselected (PE3 high).
    assert(t.st_exchange(0)==0xff);
    t.m_gpio[2*4+1]=0;
    assert(t.st_exchange(0)==0xaa);
    // Unsupported 16-bit pen/ADC transfer must not emulate a sample.
    t.m_spi2_data=0;
    t.spi2_ctrl_w(0,0x234f,0xffff);
    assert(t.m_spi2_data==0xffff);
}
"""
        with tempfile.TemporaryDirectory(prefix='dana-spi2-cpp-') as tmp:
            p=Path(tmp)
            (p/'test.cpp').write_text(code)
            compiler=shutil.which('c++')
            self.assertIsNotNone(compiler)
            subprocess.run([compiler,'-std=c++20','-O2','-Wall','-Wextra','-Werror',
                            str(p/'test.cpp'),'-o',str(p/'test')],check=True,timeout=90)
            subprocess.run([str(p/'test')],check=True,timeout=10)

    def test_real_spi2_registers_st_io_and_serialized_state(self):
        src=DRIVER.read_text()
        for name in ('spi2_data','spi2_ctrl','st_ready','st_hello','st_reset_held',
                     'st_old_keys','st_pending_keys','st_queue_left'):
            self.assertEqual(src.count('save_item(NAME(m_'+name+'));'),1)
        self.assertIn('map(0xfffff800,0xfffff801)',src)
        self.assertIn('map(0xfffff802,0xfffff803)',src)
        self.assertIn('PORT_START("KEYS")',src)
        for key in ('KEYCODE_A','KEYCODE_B','KEYCODE_ENTER','KEYCODE_SPACE'):
            self.assertIn(key,src)
        # Guest polls PF1 active-low pen interrupt. Idle must NOT look pressed.
        self.assertIn('u8 pf_r(offs_t reg)',src)
        self.assertIn('value |= 0x02;',src)
        self.assertIn('m_st_ready=true;',src)
        self.assertIn('m_st_hello=true;',src)
        self.assertIn('(m_spi2_ctrl & 0x2100)!=0x2100',src)
        self.assertIn('m_spi2_ctrl=(m_spi2_ctrl & ~0x0100) | 0x0080;',src)
        self.assertFalse(f1.implemented_byte(0xfffff800,'read',False))
        self.assertTrue(f1.implemented_byte(0xfffff802,'read',True))


class IntegratedTimerUARTIRQ(unittest.TestCase):
    """Single grouped source test: timer scheduler, IRQ6/4 IACK and UART1 TX."""
    def test_production_cpp_timer_uart_irq_in_isolation(self):
        src=DRIVER.read_text()
        a=src.index('void alphasdana_state::update_irq_lines()')
        b=src.index('QUICKLOAD_LOAD_MEMBER(alphasdana_state::guest_load)',a)
        production=src[a:b]
        code=r"""
#include <cassert>
#include <cmath>
#include <cstdint>
using u8=std::uint8_t;
using u16=std::uint16_t;
using u32=std::uint32_t;
using u64=std::uint64_t;
using offs_t=unsigned;
#define ASSERT_LINE 1
#define CLEAR_LINE 0
#define COMBINE_DATA(dst) (*(dst)=(*(dst)&~mem_mask)|(data&mem_mask))
#define TIMER_CALLBACK_MEMBER(name) void name()
#define logerror(...) ((void)0)
struct attotime {
    long double seconds;
    static attotime never;
    static attotime from_ticks(u64 ticks, u32 hz) {
        return {static_cast<long double>(ticks)/hz};
    }
    u64 as_ticks(u32 hz) const { return u64(seconds*hz); }
};
attotime attotime::never{-1};
struct FakeCPU {
    int irq4=0,irq6=0;
    void set_input_line(int level,int value) {
        if (level==6) irq6=value;
        else if (level==4) irq4=value;
        else assert(false);
    }
};
struct FakeTimer {
    attotime delay=attotime::never;
    attotime elapsed_value{0};
    void adjust(attotime value) { delay=value; elapsed_value={0}; }
    attotime elapsed() const { return elapsed_value; }
};
struct alphasdana_state {
    FakeCPU *m_maincpu;
    FakeTimer *m_timer1_timer;
    u16 m_pllfsr=0x0347,m_tctl1=0,m_tprer1=0,m_tcmp1=0xffff;
    u16 m_tcr1=0,m_tcn1=0,m_tstat1=0,m_tstat_clear1=0;
    u32 m_timer1_compares=0,m_timer1_iacks=0;
    u16 m_utx1=0;
    u32 m_pending=0,m_imr=0x00ffffff;
    u8 m_ivr=0x40;
    void update_irq_lines();
    u8 irq_vector_r(offs_t);
    TIMER_CALLBACK_MEMBER(timer1_compare);
    u32 guest_system_clock_hz() const;
    u32 timer1_source_hz() const;
    void timer1_schedule();
    void timer1_tctl_w(offs_t,u16,u16);
    void timer1_tprer_w(offs_t,u16,u16);
    void timer1_tcmp_w(offs_t,u16,u16);
    u16 timer1_tcn_r();
    u16 timer1_tstat_r();
    void timer1_tstat_w(offs_t,u16,u16);
    void uart1_utx_w(offs_t,u16,u16);
};
""" + production + r"""
int main() {
    FakeCPU cpu;
    FakeTimer timer;
    alphasdana_state m;
    m.m_maincpu=&cpu;
    m.m_timer1_timer=&timer;
    assert(m.guest_system_clock_hz()==33161216);
    assert(m.timer1_source_hz()==0); // Timer1 disabled until TCTL enabled.
    assert(m.irq_vector_r(6)==0x46 && m.irq_vector_r(4)==0x44);
    m.timer1_tprer_w(0,2,0xffff);
    m.timer1_tcmp_w(0,0xd7e4,0xffff);
    m.timer1_tctl_w(0,0x0033,0xffff);
    assert(m.timer1_source_hz()==33161216);
    assert(timer.delay.seconds>0.004L && timer.delay.seconds<0.006L);
    m.timer1_compare();
    assert(m.m_timer1_compares==1);
    assert((m.m_tstat1&1) && (m.m_pending&2));
    assert(cpu.irq6==0); // masked after reset
    m.m_imr &= ~u32(2);
    m.update_irq_lines();
    assert(cpu.irq6==1);
    assert(m.irq_vector_r(6)==0x46 && m.m_timer1_iacks==1);
    assert(m.timer1_tstat_r()==1);
    m.timer1_tstat_w(0,0,0xffff); // MAME donor read-then-write clear
    assert(m.m_tstat1==0 && (m.m_pending&2)==0 && cpu.irq6==0);
    // UART1 Tx-empty/Tx-ready, no unsolicited RX IRQ.
    m.uart1_utx_w(0,0x0045,0x00ff);
    assert(m.m_utx1==0x45 && cpu.irq4==0);
    m.m_pending|=4;
    m.update_irq_lines();
    assert(cpu.irq4==0); // still masked
    m.m_imr &= ~u32(4);
    m.update_irq_lines();
    assert(cpu.irq4==1 && cpu.irq6==0);
    m.m_pending &= ~u32(4);
    m.update_irq_lines();
    assert(cpu.irq4==0);
    m.timer1_tctl_w(0,0,0xffff);
    assert(timer.delay.seconds<0);

    // Preserve live counter when modifying comparator during an active
    // period, and compute the 16-bit wrap instead of resetting a full cycle.
    m.timer1_tprer_w(0,2,0xffff);
    m.timer1_tcmp_w(0,150,0xffff);
    m.timer1_tctl_w(0,0x0033,0xffff);
    u32 const hz=m.timer1_source_hz();
    timer.elapsed_value=attotime::from_ticks(300,hz); // 100 prescaled ticks
    assert(m.timer1_tcn_r()==100);
    m.timer1_tcmp_w(0,150,0xffff);
    assert(m.m_tcn1==100);
    assert(std::fabs(timer.delay.seconds-150.0L/hz)<1e-9L);
    timer.elapsed_value=attotime::from_ticks(300,hz);
    m.timer1_tcmp_w(0,50,0xffff); // comparator now below counter
    assert(m.m_tcn1==200);
    assert(std::fabs(timer.delay.seconds-(u64(65536-200+50)*3.0L/hz))<1e-9L);
    m.timer1_tctl_w(0,0,0xffff);

    // Genuine free-run: next comparator match is one 16-bit wrap away.
    m.timer1_tcmp_w(0,150,0xffff);
    m.timer1_tctl_w(0,0x0133,0xffff);
    m.timer1_compare();
    assert(m.m_tcn1==150);
    assert(std::fabs(timer.delay.seconds-(65536.0L*3.0L/hz))<1e-9L);
}
"""
        with tempfile.TemporaryDirectory(prefix='dana-timer-uart-cpp-') as tmp:
            p=Path(tmp)
            (p/'test.cpp').write_text(code)
            compiler=shutil.which('c++')
            self.assertIsNotNone(compiler)
            subprocess.run([compiler,'-std=c++20','-O2','-Wall','-Wextra','-Werror',
                            str(p/'test.cpp'),'-o',str(p/'test')],check=True,timeout=90)
            subprocess.run([str(p/'test')],check=True,timeout=10)

    def test_complete_vz_timer_uart_irq_map(self):
        src=DRIVER.read_text()
        pairs=[
            ('timer1_tctl','0xfffff600,0xfffff601'),
            ('timer1_tprer','0xfffff602,0xfffff603'),
            ('timer1_tcmp','0xfffff604,0xfffff605'),
            ('timer1_tcr','0xfffff606,0xfffff607'),
            ('timer1_tcn','0xfffff608,0xfffff609'),
            ('timer1_tstat','0xfffff60a,0xfffff60b'),
            ('uart1_ustcnt','0xfffff900,0xfffff901'),
            ('uart1_ubaud','0xfffff902,0xfffff903'),
            ('uart1_urx','0xfffff904,0xfffff905'),
            ('uart1_utx','0xfffff906,0xfffff907'),
            ('uart1_umisc','0xfffff908,0xfffff909'),
            ('uart1_prescaler','0xfffff90a,0xfffff90b')]
        for name,address in pairs:
            self.assertIn('map('+address+')',src)
            self.assertIn('FUNC(alphasdana_state::'+name+'_r)',src)
        for state in ('tctl1','tprer1','tcmp1','tcr1','tcn1','tstat1','tstat_clear1',
                      'timer1_compares','timer1_iacks','ustcnt1','ubaud1','urx1','utx1','umisc1','uart_prescaler1'):
            self.assertIn('save_item(NAME(m_'+state+'));',src)
        self.assertIn('m_maincpu->set_unscaled_clock(guest_system_clock_hz());',src)
        self.assertIn('if (m_guest_loaded)\n        m_maincpu->set_unscaled_clock(guest_system_clock_hz());',src)
        self.assertIn("DANA_VZ_CPU(config, m_maincpu, 1'000'000)",src)
        self.assertIn('set_addrmap(m68000_base_device::AS_CPU_SPACE, &alphasdana_state::cpu_space_map)',src)
        self.assertIn('map(0xfffffff0,0xffffffff)',src)
        self.assertIn('m_pending |= 0x00000002;',src)
        self.assertIn('u32 remaining=(u32(m_tcmp1)-u32(m_tcn1)) & 0xffff;',src)
        self.assertIn('if (m_tctl1 & 1) m_tcn1=timer1_tcn_r();',src)
        self.assertIn('DANA_VZ_TIMER1_COMPARE count=',src)
        self.assertIn('if (m_timer1_compares<=16)',src)
        self.assertIn('if ((offset & 7)==6 && (m_pending & ~m_imr & 2))',src)
        self.assertIn('(active & 0x00000002)',src)
        self.assertIn('(active & 0x00000004)',src)
        self.assertNotIn('map(0xfffff600,0xfffff6ff)',src)
        self.assertTrue(f1.implemented_byte(0xfffff602,'write',True))
        self.assertTrue(f1.implemented_byte(0xfffff900,'read',True))
        self.assertFalse(f1.implemented_byte(0xfffff602,'write',False))
        self.assertFalse(f1.implemented_byte(0xfffff90c,'read',True))

if __name__=='__main__':
    result=unittest.main(exit=False)
    print('D2_3_STATIC_PASS' if result.result.wasSuccessful() else 'D2_3_STATIC_FAIL')
    raise SystemExit(0 if result.result.wasSuccessful() else 1)
