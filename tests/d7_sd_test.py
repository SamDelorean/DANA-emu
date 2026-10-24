#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""D7/D8.3 source qualification. Syntax/constant evaluation only; no emulator."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
PATH='src/mame/skeleton/alphasdana.cpp'
BASE='4275fb76156a6b8e41d60935142ed7d28eb9c8b0'
MAME=Path(os.environ.get('DANA_MAME_REFERENCE','/workspace/mame-as3k'))
PIN='c4e48388ca620472643110db2941ce70aa5f3c07'


def function(text,signature):
    start=text.index(signature); end=text.index('{',start); depth=1; end+=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}'); end+=1
    return text[start:end]


def syntax(source,extra=()):
    compiler=shutil.which(os.environ.get('CXX','c++'))
    if not compiler: raise unittest.SkipTest('BLOCKED: C++20 compiler missing')
    subprocess.run([compiler,'-std=c++20','-fsyntax-only','-Werror',*extra,str(source)],cwd=ROOT,check=True)


class SourceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=subprocess.check_output(['git','show',BASE+':'+PATH],cwd=ROOT,text=True)
        cls.new=(ROOT/PATH).read_text()
        cls.image=(ROOT/'src/mame/skeleton/alphasdana_sd_image.h').read_text()
        cls.logic=(ROOT/'src/mame/skeleton/alphasdana_sd.h').read_text()

    def test_01_exact_installed_source_baseline(self):
        self.assertEqual(hashlib.sha256(self.old.encode()).hexdigest(),'5b8d3ae5f7a01034241aa448b77eb4803f6c2dc8ac79d7dc50ad851f6436ddee')

    def test_02_flash_ram_lcd_st_pen_timer_uart_preservation(self):
        cpu=self.old[self.old.index('// Minimal VZ-aware'):self.old.index('namespace {')]
        self.assertIn(cpu,self.new)
        allowed={'machine_start','machine_reset','program_map','alphasdana','pb_w','pk_w','update_irq_lines'}
        names=re.findall(r'^(?:void|u8|u16|u32) alphasdana_state::(\w+)\(',self.old,re.M)
        for name in names:
            if name in allowed: continue
            sig=re.search(r'^(?:void|u8|u16|u32) alphasdana_state::'+name+r'\([^\n]*',self.old,re.M)[0]
            with self.subTest(name=name): self.assertEqual(function(self.old,sig),function(self.new,sig))
        for sig in ['QUICKLOAD_LOAD_MEMBER(alphasdana_state::guest_load)',
                    'TIMER_CALLBACK_MEMBER(alphasdana_state::clk32_tick)',
                    'TIMER_CALLBACK_MEMBER(alphasdana_state::timer1_compare)']:
            self.assertEqual(function(self.old,sig),function(self.new,sig))
        # Entire existing input map including stylus and keys is unchanged.
        old_inputs=self.old[self.old.index('    // Use one SDL lightgun-class'):]
        self.assertIn(old_inputs,self.new)

    def test_03_original_gpio_behaviour_plus_sd_notifications(self):
        for name in ('pb_w','pk_w'):
            sig='void alphasdana_state::'+name+'('
            self.assertEqual(function(self.old,sig),function(self.new,sig).replace('    sd_lines();\n',''))
        for sig in ('u8 pf_r(', 'u8 alphasdana_state::pk_r(', 'void pg_w('):
            self.assertEqual(function(self.old,sig),function(self.new,sig))
        self.assertIn('void pfsel_w(u8 data) { m_pfsel = data; sd_lines(); }',self.new)
        self.assertIn('void pf_w(offs_t reg, u8 value) { m_gpio[3*4+reg]=value; sd_lines(); }',self.new)

    def test_04_original_maps_save_fields_and_gui_patches(self):
        for line in self.old.splitlines():
            if line.strip().startswith(('map(','m_boot_memory[')):
                self.assertIn(line,self.new)
        for saved in re.findall(r'save_item\(NAME\(([^)]+)\)\);',self.old):
            self.assertEqual(self.new.count('save_item(NAME('+saved+'));'),1,saved)
        changed=subprocess.check_output(['git','diff','--name-only',BASE],cwd=ROOT,text=True)
        self.assertFalse(any(p.startswith('src/osd/') or Path(p).name.startswith(('025_','026_','DANA_GUI025','DANA_GUI026')) for p in changed.splitlines()))

    def test_05_mame_full_driver_syntax(self):
        if not (MAME/'src/emu/emu.h').is_file(): self.skipTest('BLOCKED: pinned MAME headers missing; set DANA_MAME_REFERENCE')
        self.assertEqual(subprocess.check_output(['git','-C',str(MAME),'rev-parse','HEAD'],text=True).strip(),PIN)
        includes=['src/emu','src/devices','src/lib','src/lib/util','src/osd','3rdparty','3rdparty/asio/include','3rdparty/rapidjson/include']
        syntax(ROOT/PATH,['-I'+str(MAME/p) for p in includes])

    def test_06_wire_protocol_fifo_negative_and_restore_constants(self):
        syntax(ROOT/'tests/d7_sd_static.cpp',['-Wall','-Wextra','-fconstexpr-ops-limit=200000000'])
        self.assertEqual((ROOT/'tests/d7_sd_static.cpp').read_text().count('static_assert('),6)

    def test_07_readonly_media_identity_and_eject(self):
        self.assertIn('bool is_writeable() const noexcept override { return true; }',self.image)
        self.assertIn('!(m_write_access->read() & (1U<<m_slot))',self.image)
        self.assertIn('bool is_creatable() const noexcept override { return false; }',self.image)
        self.assertNotRegex(self.image,r'\b(?:fwrite|ofstream|fopen)\s*\(')
        self.assertIn('error || actual!=512',self.image)
        self.assertIn('image_core_file().flush()',self.image)
        for part in ('bytes%512','bytes/512>0x4000000','card::geometry','fread(data,512)==512',
                     'm_bound!=exists()','std::memcmp(actual,m_sha1,20)','register_presave','register_postload'):
            self.assertIn(part,self.image)
        self.assertIn('m_card.blocks)*512!=length()',self.image)
        unload=function(self.image,'virtual void call_unload()')
        self.assertIn('m_card=dana_sd::card{}',unload)
        self.assertNotIn('m_sd[',unload)
        self.assertNotIn('suspend(',unload)

    def test_08_all_protocol_and_controller_state_saved(self):
        card_fields=['cmd','reply','reply_pos','reply_size','write_left','command_size','bit_count','input','output',
                     'initial_clocks','status','blocks','next_block','powered','selected','idle','app','crc_enabled',
                     'high_capacity','multi_read','multi_write','write_data','write_reply']
        for item in card_fields: self.assertIn('DANA_SD_SAVE('+item+')',self.image)
        for item in ('tx','rx','control','mask','spc','last_tx','last_rx','tx_head','rx_head','tx_count','rx_count','rx_edge'):
            self.assertIn('DANA_SPI1_SAVE('+item+')',self.new)
        for item in ('m_spi1_word','m_spi1_control','m_spi1_received','m_spi1_bits_left','m_spi1_busy',
                     'm_pd_extra','m_sd_last_pins','m_sd_edges','m_ilcr'):
            self.assertIn('save_item(NAME('+item+'));',self.new)

    def test_09_independent_native_image_devices(self):
        self.assertIn('m_sd(*this, "sd%u", 0U)',self.new)
        for i in range(2): self.assertIn(f'DANA_SD_IMAGE(config,m_sd[{i}]).set_slot({i});',self.new)
        self.assertIn('image_brief_type_name() const noexcept override { return "sd"; }',self.image)
        self.assertIn('is_reset_on_load() const noexcept override { return false; }',self.image)
        self.assertNotIn('hard_disk_file',self.image)
        self.assertNotRegex(self.image,r'\b(FAT|GEMDOS|VFS)\b')

    def test_10_actual_gpio_irq_production_logic(self):
        declarations='''
#include <array>
using u8=unsigned char; using u16=unsigned short; using u32=unsigned int; using offs_t=unsigned;
constexpr int ASSERT_LINE=1,CLEAR_LINE=0;
struct slot { bool powered=false,selected=false; constexpr void lines(bool p,bool s) {powered=p;selected=p&&s;} };
struct pins {u8 value=12;constexpr u8 read() const{return value;}};
struct cpu {std::array<int,8> levels{};constexpr void set_input_line(unsigned i,int v){levels[i]=v;}};
struct fixture {
 u8 m_gpio[32]={},m_pfsel=0,m_pd_extra[4]={},m_sd_edges=0,m_sd_last_pins=12;
 u16 m_ilcr=0x6533;u32 m_pending=0,m_imr=0;
 slot a,b;std::array<slot*,2> m_sd{{&a,&b}};
 pins irq; pins *m_sd_irq=&irq; cpu core;cpu *m_maincpu=&core;
'''
        for sig in ['void alphasdana_state::sd_lines()', 'void alphasdana_state::sd_gpio_irq()',
                    'u8 alphasdana_state::pd_r(', 'void alphasdana_state::pd_w(',
                    'void alphasdana_state::update_irq_lines()']:
            declarations+='constexpr '+function(self.new,sig).replace('alphasdana_state::','')+'\n'
        declarations+='''
};
constexpr bool check(){
 fixture f;f.m_gpio[0]=f.m_gpio[3]=f.m_gpio[1]=0x20;
 f.m_gpio[20]=f.m_gpio[23]=8; f.m_gpio[21]=0;
 f.sd_lines();if(!f.a.powered||!f.a.selected||f.b.powered||f.b.selected)return false;
 f.m_gpio[24]=f.m_gpio[27]=f.m_gpio[25]=0x20;
 f.m_gpio[12]=f.m_pfsel=4; f.m_gpio[13]=0;
 f.sd_lines();if(!f.b.selected||!f.a.selected)return false;
 f.m_gpio[13]=4;f.sd_lines();if(f.b.selected||!f.a.selected)return false;
 f.m_gpio[1]=0;f.sd_lines();if(f.a.powered||!f.b.powered)return false;
 f.m_gpio[23]=0;f.sd_lines();if(f.a.selected)return false;
 f.m_pd_extra[1]=12;f.sd_gpio_irq();if(f.m_pending&0xc00)return false;
 f.irq.value=8;f.sd_gpio_irq();if((f.m_pending&0xc00)!=0x400||f.core.levels[4]!=1)return false;
 if((f.pd_r(1)&12)!=8)return false;
 f.m_gpio[4]=4;f.sd_gpio_irq();if(f.m_pending&0xc00)return false;
 f.m_gpio[4]=0;f.m_pd_extra[3]=12;f.m_pd_extra[0]=12;
 f.irq.value=12;f.sd_gpio_irq();if(!(f.m_pending&0x400))return false;
 f.pd_w(1,4);if(f.m_pending&0x400)return false;
 f.m_pending=0x200002;f.update_irq_lines();if(f.core.levels[6]!=1)return false;
 f.m_ilcr=0x3533;f.update_irq_lines();if(f.core.levels[3]!=1||f.core.levels[6]!=1)return false;
 f.m_pending=4;f.update_irq_lines();return f.core.levels[4]==1&&f.core.levels[3]==0&&f.core.levels[6]==0;
}
static_assert(check(),"production GPIO direction/selection, dual power/CS, independent PD IRQs and timer coexistence");
'''
        with tempfile.TemporaryDirectory(prefix='dana-sd-source-check-') as folder:
            source=Path(folder)/'registers.cpp';source.write_text(declarations)
            syntax(source,['-Wall','-Wextra'])

    def test_11_scheduler_and_terminal_errors(self):
        complete=function(self.new,'TIMER_CALLBACK_MEMBER(alphasdana_state::spi1_complete)')
        self.assertIn('m_spi1_bits_left-1',complete)
        self.assertIn('sd_lines();',complete)
        self.assertIn('attotime::from_ticks',complete)
        self.assertIn('TWO_SELECTED_CARDS_BUS_CONTENTION',complete)
        self.assertIn('RX_FIFO_OVERFLOW',complete)
        self.assertIn('if (m_spi1_busy) spi1_schedule();',complete)
        self.assertIn('side_effects_disabled()',function(self.new,'u16 alphasdana_state::spi1_r('))
        self.assertIn('m_spi1_timer->adjust(attotime::never)',self.new)
        reset=function(self.new,'void alphasdana_state::spi1_reset()')
        self.assertIn('slot->lines(false,false)',reset)
        self.assertNotRegex(reset,r'\b(load|unload|fwrite)\(')

    def test_12_original_portc_and_pll_assertions_preserved(self):
        # Preserve existing assertions and critical bitfields; no historic
        # shallow-checkout or evidence-index workaround is involved here.
        for sig in ['void portc_reset()', 'u8 pcpden_r()', 'void pcpden_w(',
                    'u8 pcsel_r()', 'void pcsel_w(', 'u16 pllfsr_r()']:
            self.assertEqual(function(self.old,sig),function(self.new,sig))
        self.assertIn('m_pllfsr = 0x0347;',self.new)

    def test_13_d75_write_protocol_constants(self):
        syntax(ROOT/'tests/d7_5_sd_static.cpp',['-Wall','-Wextra','-fconstexpr-ops-limit=200000000'])

    def test_14_qualified_spi1_and_peripheral_bodies_unchanged(self):
        baseline=subprocess.check_output(['git','show','5be8beb797fdf40475f564f54ca3ebd243dc20a5:'+PATH],cwd=ROOT,text=True)
        names=re.findall(r'^(?:void|u8|u16|u32) alphasdana_state::(\w+)\(',baseline,re.M)
        for name in names:
            if name=='alphasdana':continue # only add per-device slot identity
            sig=re.search(r'^(?:void|u8|u16|u32) alphasdana_state::'+name+r'\([^\n]*',baseline,re.M)[0]
            self.assertEqual(function(baseline,sig),function(self.new,sig),name)
        self.assertEqual(function(baseline,'TIMER_CALLBACK_MEMBER(alphasdana_state::spi1_complete)'),function(self.new,'TIMER_CALLBACK_MEMBER(alphasdana_state::spi1_complete)'))
        old_header=subprocess.check_output(['git','show','5be8beb797fdf40475f564f54ca3ebd243dc20a5:src/mame/skeleton/alphasdana_sd.h'],cwd=ROOT,text=True)
        self.assertEqual(old_header[old_header.index('struct controller'):],self.logic[self.logic.index('struct controller'):])
        for signature in ('static constexpr bool geometry(', 'constexpr bool address(', 'template<class Media> constexpr void read_block(', 'template<class Media> constexpr byte exchange(', 'template<class Media> constexpr bool bit('):
            self.assertEqual(function(old_header,signature),function(self.logic,signature),signature)

    def test_15_d75_write_commit_order_and_snapshot_quarantine(self):
        write=function(self.image,'bool write_sector(')
        required=['write_protected()','fingerprint(before','util::write_at','error || actual!=512',
                  'image_core_file().flush()','util::read_at','std::memcmp(verified,data,512)',
                  'fingerprint(after)','std::memcmp(after,expected,20)','std::copy(std::begin(after)','return true']
        positions=[write.index(part) for part in required]
        self.assertEqual(positions,sorted(positions))
        self.assertIn('m_io_fault=true',function(self.image,'bool fail_write('))
        self.assertNotIn('save_item(NAME(m_io_fault))',self.image)
        self.assertIn('m_saved_writable!=(m_bound && !write_protected())',self.image)
        self.assertIn('std::copy_n(replacement,512',self.image)
        self.assertIn('m_io_fault',function(self.image,'void check_media()'))

    def test_16_d75_independent_safe_defaults_and_partial_abort(self):
        for mask in ('0x01','0x02'):
            self.assertIn('PORT_CONFNAME('+mask+',0x00,',self.new)
        self.assertIn('protected_media ? 0x10 : 0',self.logic)
        block=function(self.logic,'template<class Media> constexpr void receive(')
        self.assertLess(block.index('crc16(write_data.data(),512)!=received'),block.index('media.write_sector'))
        self.assertIn('next_block>=blocks',block)
        self.assertIn('token=0x05; ++next_block',block)
        for sig in ('constexpr void power(', 'constexpr void select('):
            self.assertNotIn('write_sector',function(self.logic,sig))

    def test_17_d75_native_job_syntax_and_hold_guards(self):
        import ast
        ast.parse((ROOT/'tests/d7_5_native.py').read_text())
        job=ROOT/'tests/d7_5_native_HOLD.job.sh'
        subprocess.run(['bash','-n',str(job)],check=True)
        result=subprocess.run(['bash',str(job)],env={**os.environ,'DANA_D75_NATIVE_AUTHORIZED':'NO'},capture_output=True,text=True)
        self.assertEqual(result.returncode,3)
        self.assertIn('HOLD',result.stderr)
        native=(ROOT/'tests/d7_5_native.py').read_text()
        for required in ('DANA_D75_NATIVE_AUTHORIZED','args.output.exists()','DISPOSABLE_SD0.img','DISPOSABLE_SD1.img',
                         'RLIMIT_FSIZE','signal.SIG_IGN','image changed','write protection differs','2*1024*1024','time.monotonic()+90'):
            self.assertIn(required,native)
        self.assertNotIn('force push',native)

    def test_18_d75_native_fixture_encoding_and_envelope(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('d75_native_static',ROOT/'tests/d7_5_native.py')
        native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
        import struct
        self.assertEqual(native.crc7(bytes.fromhex('4000000000')),0x95)
        self.assertEqual(native.crc16(b'123456789'),0x31c3)
        # In-memory bytes only; no image, emulator or firmware file created.
        for mode in ('protected','crc','partial','power_partial','eject_partial','close_partial','reset_partial','io_error','write','both_write','reopen'):
            package,ranges=native.fixture(mode)
            self.assertEqual(package[:8],b'DANARAM1')
            self.assertEqual(package[40:60],hashlib.sha1(package[64:]).digest())
            entry,base,length=struct.unpack_from('>III',package,8)
            self.assertEqual((entry,base,length),(0x2140,0x2140,len(package)-64))
            self.assertEqual(length%2,0)
            self.assertIn(bytes.fromhex('33c0fffff70200790100fffff70408390000fffff704'),package)
            for address,count in ranges:self.assertGreaterEqual(address,0x21000);self.assertEqual(count,1536)

    def test_19_d75_generated_lua_syntax_without_execution(self):
        import ctypes
        import ctypes.util
        import importlib.util
        library=ctypes.util.find_library('lua5.4')
        if not library:self.skipTest('BLOCKED: Lua syntax library absent')
        lua=ctypes.CDLL(library)
        lua.luaL_newstate.restype=ctypes.c_void_p
        lua.luaL_loadbufferx.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_char_p]
        lua.lua_close.argtypes=[ctypes.c_void_p]
        lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p];lua.lua_tolstring.restype=ctypes.c_char_p
        spec=importlib.util.spec_from_file_location('native_lua_syntax',ROOT/'tests/d7_5_native.py')
        native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
        for mask in range(4):
            for state_path in (None,Path('/tmp/disposable.sta')):
                text=native.lua_script(Path('/tmp/not_created.json'),[(0x21000,1536)],mask,True,True,state_path).encode()
                machine=lua.luaL_newstate()
                try:
                    rc=lua.luaL_loadbufferx(machine,text,len(text),b'd75_syntax_only',None)
                    self.assertEqual(rc,0,lua.lua_tolstring(machine,-1,None) if rc else '')
                finally:lua.lua_close(machine)


if __name__=='__main__': unittest.main(verbosity=2)
