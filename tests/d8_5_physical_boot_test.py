#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""D8.5 static checks only. No emulator, firmware fixture, object or executable."""
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
DRIVER=ROOT/'src/mame/skeleton/alphasdana.cpp'
BASE='47afeb58e2baa8b56af04fa8a23539454a472256'
BASE_SHA='8e88d36d9d5b1e7574b7d5d58683975aa78ae94f6baf8213a311236707975e21'


def function(source, signature):
    start=source.index(signature);brace=source.index('{',start);depth=1;i=brace+1
    while depth:
        depth+=(source[i]=='{')-(source[i]=='}');i+=1
    return source[start:i]


class CanonicalPreservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':src/mame/skeleton/alphasdana.cpp']).decode()
        cls.new=DRIVER.read_text()

    def test_exact_canonical_base(self):
        self.assertEqual(hashlib.sha256(self.old.encode()).hexdigest(),BASE_SHA)

    def test_all_existing_peripheral_functions_are_byte_identical(self):
        # Preserve ALL out-of-class canonical methods except lifecycle/map/config
        # methods that must integrate the extra boot memory view and image device.
        changed={'machine_start','machine_reset','program_map','alphasdana'}
        names=re.findall(r'^(?:void|u8|u16|u32) alphasdana_state::(\w+)\(',self.old,re.M)
        preserved=[name for name in names if name not in changed]
        self.assertGreaterEqual(len(preserved),25)
        for name in preserved:
            signature=re.search(r'^(?:void|u8|u16|u32) alphasdana_state::'+name+r'\([^\n]*',self.old,re.M)[0]
            with self.subTest(name=name):self.assertEqual(function(self.old,signature),function(self.new,signature))
        # Inline GPIO/UART/ADC handlers and original state fields are untouched.
        first=self.old.index('    void update_irq_lines();');last=self.old.index('    DECLARE_QUICKLOAD_LOAD_MEMBER(guest_load);')
        self.assertIn(self.old[first:last],self.new)
        inputs=self.old[self.old.index('static INPUT_PORTS_START'):]
        self.assertIn(inputs,self.new)

    def test_native_cpu_callbacks_and_original_save_fields_are_preserved(self):
        cpu=self.old[self.old.index('// Minimal VZ-aware'):self.old.index('namespace {')]
        self.assertIn(cpu,self.new)
        for name in ('clk32_tick','timer1_compare'):
            signature='TIMER_CALLBACK_MEMBER(alphasdana_state::'+name+')'
            self.assertEqual(function(self.old,signature),function(self.new,signature))
        for saved in re.findall(r'save_item\(NAME\(([^)]+)\)\);',self.old):
            self.assertEqual(self.new.count('save_item(NAME('+saved+'));'),1,saved)

    def test_ram_loader_unchanged_after_early_profile_guard(self):
        signature='QUICKLOAD_LOAD_MEMBER(alphasdana_state::guest_load)'
        old=function(self.old,signature);new=function(self.new,signature)
        guard='''    if (m_firmware->exists() || m_physical_boot)
        return std::make_pair(image_error::INVALIDIMAGE,std::string("DANARAM1 cannot replace a physical Flash boot"));
'''
        self.assertEqual(new.replace(guard,'',1),old)
        self.assertLess(new.index(guard),new.index('space.write_dword'))

    def test_original_mmio_and_sdl_cursor_patches_are_unchanged(self):
        def maps(s):return [line.strip() for line in function(s,'void alphasdana_state::program_map(').splitlines() if 'map(' in line and '.ram()' not in line and '.view(' not in line and 'm_boot_memory[' not in line and 'void program_map' not in line]
        self.assertEqual(maps(self.old),maps(self.new))
        for name in ('patches/025_dana_host_cursor_blink_sdl2.patch','patches/026_dana_cursor_as2k_writer_380_190.patch'):
            original=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name])
            self.assertEqual((ROOT/name).read_bytes(),original)

    def test_physical_reset_has_no_host_vector_or_cpu_state_injection(self):
        body=function(self.new,'void alphasdana_state::physical_reset()')
        for forbidden in ('write_dword','write_word','set_state_int','M68K_SP','M68K_PC','m_maincpu->reset('):self.assertNotIn(forbidden,body)
        self.assertIn('m_cs_select[0]=0x00b0',body)
        for corrected in ('m_cs_control[1]=0x1000','m_cs_control[2]=0x9c00','m_dram[2]=0x003c'):self.assertIn(corrected,body)
        self.assertNotIn('m_ram[',body)
        reset=function(self.new,'void alphasdana_state::machine_reset()')
        self.assertIn('m_boot_memory.select(m_physical_boot ? 1 : 0)',reset)
        self.assertIn('physical_reset();\n        return;',reset)

    def test_read_only_image_conflicts_short_reads_and_save_identity(self):
        load=function(self.new,'DEVICE_IMAGE_LOAD_MEMBER(alphasdana_state::firmware_load)')
        self.assertLess(load.index('m_guest->exists()'),load.index('rom_alloc'))
        self.assertIn('image.fread(rom,size)!=size',load)
        self.assertLess(load.index('m_firmware->get_rom_size()!=size'),load.index('image.fread(rom,size)'))
        self.assertIn('!firmware_vectors_valid(rom)',load)
        for forbidden in ('image.fwrite','battery_save','memset(','write_dword','set_state_int'):self.assertNotIn(forbidden,load)
        saved=function(self.new,'void alphasdana_state::boot_postload()')
        self.assertIn('m_physical_boot!=m_firmware->exists()',saved)
        self.assertIn('std::memcmp(hash.m_raw,m_flash_sha1',saved)
        self.assertIn('fatalerror(',saved)
        self.assertIn('FLASH_COMMAND_SET_UNVERIFIED',self.new)
        self.assertIn('MMIO_READ_UNIMPLEMENTED',self.new)


class ConstantEvaluation(unittest.TestCase):
    def test_production_decode_lane_reset_and_fail_closed_logic_without_executable(self):
        source=DRIVER.read_text()
        inline=('u32 cs_base(', 'u32 cs_size(', 'bool cs_hit(', 'bool physical_ram_ready()', 'static bool firmware_size_valid(', 'static bool firmware_vectors_valid(')
        methods=[]
        for name in inline:
            method=function(source,name)
            method=method.replace('static bool','static constexpr bool',1) if name.startswith('static') else 'constexpr '+method
            methods.append(method)
        signatures=('u16 alphasdana_state::physical_r(', 'void alphasdana_state::physical_w(',
                    'void alphasdana_state::physical_reset()', 'u16 alphasdana_state::cs_r(',
                    'void alphasdana_state::cs_w(', 'void alphasdana_state::cs_control3_w(',
                    'void alphasdana_state::scr_w(', 'void alphasdana_state::physical_block(',
                    'u16 alphasdana_state::physical_mmio_r(', 'void alphasdana_state::physical_mmio_w(',
                    'u32 alphasdana_state::guest_system_clock_hz()')
        definitions=[]
        for name in signatures:
            text=function(source,name)
            # Only storage duration changes for C++20 constant evaluation;
            # production expressions, branches, masks and data remain identical.
            text=text.replace('static constexpr u8 reset_gpio','constexpr u8 reset_gpio')
            definitions.append('constexpr '+text)
        unit=r'''
#include <cstdint>
#include <array>
#include <algorithm>
#include <iterator>
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;using u64=std::uint64_t;using offs_t=unsigned;
#define COMBINE_DATA(p) (*(p)=(*(p)&~mem_mask)|(data&mem_mask))
template<typename... T> constexpr void discard(T&&...) {}
#define logerror(...) discard(__VA_ARGS__)
#define SUSPEND_REASON_DISABLE 1
enum {STATE_GENPCBASE, M68K_IR, M68K_SP, M68K_USP, M68K_SR, M68K_A4};
// Constant register/data controls only. No guest program or emulator instance.
struct Slot {std::array<u8,0x20002> bytes{};u32 size=0x20000;
 constexpr u32 get_rom_size()const{return size;}constexpr const u8*get_rom_base()const{return bytes.data();}};
struct Ram {u16 low[32]={},last=0;constexpr u16 &operator[](unsigned i){if(i<32)return low[i];if(i==0x1fffff)return last;throw "UNEXPECTED_RAM_INDEX";}};
struct CPU {u32 clock=0;constexpr void set_unscaled_clock(u32 c){clock=c;}bool resumed=false,suspended=false;constexpr void resume(int){resumed=true;}constexpr void suspend(int,bool){suspended=true;}constexpr u32 pc()const{return 0x1234;}constexpr u32 state_int(int)const{return 0;}};
struct alphasdana_state {
 Slot storage;Slot*m_firmware=&storage;Ram m_ram;CPU cpu;CPU*m_maincpu=&cpu;
 bool peek=false;constexpr auto &machine(){return *this;}constexpr bool side_effects_disabled()const{return peek;}
 bool m_physical_blocked=false,m_guest_loaded=true;int m_guest_ready=1;
 u16 m_pllfsr=0x0347;constexpr u32 guest_system_clock_hz()const;
 u8 m_scr=0,m_pcpden=0,m_pcsel=0,m_pfsel=0,m_gpio[32]={};
 u16 m_cs_base[4]={},m_cs_select[4]={},m_cs_upper=0,m_cs_control[3]={},m_emucs=0,m_dram[4]={};
 constexpr void physical_block(const char*,u32,u16=0);
 constexpr u16 physical_mmio_r(offs_t,u16);constexpr void physical_mmio_w(offs_t,u16,u16);
 constexpr u16 physical_r(offs_t,u16=0xffff);constexpr void physical_w(offs_t,u16,u16);
 constexpr void physical_reset();constexpr u16 cs_r(offs_t);constexpr void cs_w(offs_t,u16,u16);
 constexpr void cs_control3_w(offs_t,u16,u16);constexpr void scr_w(u8);
'''+ '\n'.join(methods)+'\n};\n'+'\n'.join(definitions)+r'''
constexpr bool size_checks(){
 return !alphasdana_state::firmware_size_valid(0) && !alphasdana_state::firmware_size_valid(65536)
  && !alphasdana_state::firmware_size_valid(131073) && alphasdana_state::firmware_size_valid(0x5d0000)
  && alphasdana_state::firmware_size_valid(131072) && alphasdana_state::firmware_size_valid(0x1000000)
  && !alphasdana_state::firmware_size_valid(0x2000000);
}
constexpr bool vector_structure_checks(){
 std::array<u8,12> bytes{};bytes[4]=0x10;
 if(!alphasdana_state::firmware_vectors_valid(bytes.data()))return false;
 bytes[7]=1;if(alphasdana_state::firmware_vectors_valid(bytes.data()))return false;
 bytes[7]=0;bytes[8]=0xef;
 if(!alphasdana_state::firmware_vectors_valid(bytes.data()))return false; // No invented PalmCard header location.
 bytes[4]=0xff;bytes[5]=0xff;bytes[6]=0xf0;return !alphasdana_state::firmware_vectors_valid(bytes.data());
}
constexpr bool reset_and_vector_bytes(){
 alphasdana_state s;s.m_ram.low[0]=0x9876;s.physical_reset();
 s.storage.bytes[0]=0x12;s.storage.bytes[1]=0x34;s.storage.bytes[2]=0x56;s.storage.bytes[3]=0x78;
 s.storage.bytes[4]=0x10;s.storage.bytes[5]=0xc0;s.storage.bytes[6]=0;s.storage.bytes[7]=0x10;
 return s.m_cs_select[0]==0xb0 && s.m_cs_select[3]==0x200 && s.m_cs_control[1]==0x1000
  && s.m_cs_control[2]==0x9c00 && s.m_dram[1]==0 && s.m_dram[2]==0x3c && s.m_ram.low[0]==0x9876
  && !s.m_guest_loaded && s.m_guest_ready==0 && s.cpu.resumed && s.cpu.clock==33161216
  && s.physical_r(0)==0x1234 && s.physical_r(1)==0x5678 && s.physical_r(2)==0x10c0 && s.physical_r(3)==0x10
  && s.physical_r(0x10c00000/2)==0x1234;
}
constexpr bool remap_and_byte_lanes(){
 alphasdana_state s;s.physical_reset();s.cs_w(0,0x8000,0xffff);s.m_cs_select[0]=0x00b1;
 s.storage.bytes[0]=0xa5;s.storage.bytes[1]=0x5a;
 if(s.physical_r(0x10000000/2)!=0xa55a)return false;
 s.m_cs_select[3]=0x020f;s.m_dram[2]=0x803c;s.physical_w(0,0x1234,0xffff);s.physical_w(0,0xab00,0xff00);s.physical_w(0,0x00cd,0x00ff);
 if(s.physical_r(0)!=0xabcd)return false;
 s.physical_w(0x3ffffe/2,0x6543,0xffff);if(s.physical_r(0x3ffffe/2)!=0x6543)return false;
 s.cs_w(0,0x8203,0xffff);if(s.cs_r(0)!=0x8202)return false;
 s.physical_reset();return s.m_cs_base[0]==0 && !(s.m_cs_select[0]&1) && s.m_ram.low[0]==0xabcd;
}
constexpr bool unsupported_accesses_are_terminal(){
 alphasdana_state s;s.physical_reset();s.storage.bytes[0]=0xa5;
 s.physical_w(0,0x55aa,0xffff);if(!s.m_physical_blocked||s.storage.bytes[0]!=0xa5)return false;
 s.physical_reset();s.cs_w(4,1,0xffff);if(!s.m_physical_blocked)return false;
 s.physical_reset();s.cs_w(5,1,0xffff);if(!s.m_physical_blocked)return false;
 s.physical_reset();s.cs_control3_w(0,0,0xffff);if(!s.m_physical_blocked)return false;
 s.physical_reset();s.scr_w(0);if(!s.m_physical_blocked)return false;
 s.physical_reset();s.m_cs_select[0]=0xb1;s.m_cs_select[3]=0x20f;
 s.physical_r(0);if(!s.m_physical_blocked)return false; // Overlapping groups.
 s.physical_reset();s.m_cs_select[0]=0xb1;s.m_cs_base[0]=0x8000;
 s.physical_r(0);if(!s.m_physical_blocked)return false; // RAM not enabled, no implicit alias.
 s.physical_reset();s.m_cs_select[0]=0xb1;s.storage.size=0x40000;
 s.physical_r(0);if(!s.m_physical_blocked)return false; // Unknown subarray bank wiring.
 s.physical_reset();s.storage.size=0x20000;s.m_cs_select[0]=0xb1;s.m_cs_base[0]=2;
 s.physical_r(0x4000/2);if(!s.m_physical_blocked)return false; // Unaligned window unsupported.
 s.physical_reset();s.m_cs_select[0]=0xb1;s.m_cs_base[0]=0x8000;s.m_cs_select[3]=0x20f;
 s.physical_w(0,0x2222,0xffff);if(!s.m_physical_blocked)return false; // No DRAM before controller enable.
 s.physical_reset();s.m_cs_select[0]=0xb1;s.m_cs_base[0]=0x8000;s.m_cs_select[3]=0x20f;
 s.m_dram[2]=0x883c;s.m_ram.low[0]=0xabcd;s.physical_w(0,0x2222,0xffff);
 return !s.m_physical_blocked && s.m_ram.low[0]==0xabcd; // Precharge command is not a RAM store.
}
constexpr bool debugger_peeks_are_not_cpu_evidence(){
 alphasdana_state s;s.physical_reset();s.peek=true;
 s.physical_mmio_r(0x100,0xff);if(s.m_physical_blocked||s.cpu.suspended)return false;
 s.physical_mmio_w(0x100,0,0xff);if(s.m_physical_blocked||s.cpu.suspended)return false;
 s.peek=false;s.physical_mmio_r(0x100,0xff);return s.m_physical_blocked&&s.cpu.suspended;
}
constexpr bool coverage_boundaries(){
 alphasdana_state s;s.physical_reset();s.storage.size=0x20002;
 s.storage.bytes[0]=0x12;s.storage.bytes[1]=0x34;
 s.storage.bytes[0x20000]=0xab;s.storage.bytes[0x20001]=0xcd;
 if(s.physical_r(0x10000000/2)!=0x1234 || s.physical_r(0x10020000/2)!=0xabcd || s.m_physical_blocked)return false;
 s.physical_r(0x10020002/2);if(!s.m_physical_blocked)return false;
 s.physical_reset();s.physical_r(0x10040000/2);if(!s.m_physical_blocked)return false;
 s.physical_reset();s.m_cs_select[0]=0x00b3;s.m_cs_base[0]=0x8000;
 if(s.physical_r(0x10020000/2)!=0xabcd || s.m_physical_blocked)return false;
 s.physical_r(0x10020002/2);return s.m_physical_blocked;
}
static_assert(coverage_boundaries());
static_assert(debugger_peeks_are_not_cpu_evidence());
static_assert(size_checks());
static_assert(vector_structure_checks());
static_assert(reset_and_vector_bytes());
static_assert(remap_and_byte_lanes());
static_assert(unsupported_accesses_are_terminal());
'''
        compiler=shutil.which('c++');self.assertIsNotNone(compiler)
        # -fsyntax-only produces NO object or executable. static_assert executes
        # these constant expressions inside the compiler, not a virtual CPU.
        with tempfile.NamedTemporaryFile(mode='w',suffix='.cpp',prefix='dana-d85-static-',dir='/tmp') as f:
            f.write(unit);f.flush()
            result=subprocess.run([compiler,'-std=c++20','-fsyntax-only','-Wall','-Wextra','-Werror',f.name],capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main(verbosity=2)
