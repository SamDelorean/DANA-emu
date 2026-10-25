#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Constant evaluation of production ICE handlers; no guest or ICE events."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from d8_5_physical_boot_test import function

ROOT = Path(__file__).resolve().parents[1]


class IceRegisters(unittest.TestCase):
    def test_normal_setup_lanes_w1c_reserved_bits_and_active_mode_guards(self):
        source = (ROOT / 'src/mame/skeleton/alphasdana.cpp').read_text()
        reads = '\n'.join('constexpr ' + function(source, name) for name in (
            'u16 icemcr_r()', 'u16 icemsr_r()'))
        writes = '\n'.join('constexpr ' + function(source, name) for name in (
            'void alphasdana_state::icemcr_w(', 'void alphasdana_state::icemsr_w('))
        unit = r'''
#include <cstdint>
#include <string_view>
using u16=std::uint16_t;using offs_t=unsigned;
template<typename...T> constexpr void discard(T&&...){}
#define logerror(...) discard(__VA_ARGS__)
struct alphasdana_state {
 u16 m_icemcr=0,m_icemsr=0;bool blocked=false;
 unsigned address=0;std::string_view reason;
 constexpr void physical_block(const char*r,unsigned a,u16){blocked=true;reason=r;address=a;}
 constexpr void icemcr_w(offs_t,u16,u16);
 constexpr void icemsr_w(offs_t,u16,u16);
''' + reads + '\n};\n' + writes + r'''
constexpr bool setup_and_lanes(){
 alphasdana_state s;
 if(s.icemcr_r()!=0 || s.icemsr_r()!=0)return false;
 s.icemcr_w(0,8,0xffff); // Observed UK1.5 HMDIS write.
 s.icemsr_w(0,7,0xffff); // Known next instruction, not yet natively measured.
 if(s.blocked || s.icemcr_r()!=8 || s.icemsr_r()!=0)return false;
 s.icemcr_w(0,0xff00,0xff00); // High reserved bits cannot change low control.
 if(s.blocked || s.icemcr_r()!=8)return false;
 s.icemcr_w(0,0xffa8,0xffff); // Reserved bits 15..7/5 ignored.
 if(s.blocked || s.icemcr_r()!=8)return false;
 s.icemcr_w(0,0,0);s.icemsr_w(0,0xffff,0);
 if(s.blocked || s.icemcr_r()!=8 || s.icemsr_r()!=0)return false;
 s.icemcr_w(0,0,0x00ff); // HMDIS=0 in normal mode does not activate hard-map.
 return !s.blocked && s.icemcr_r()==0;
}
constexpr bool flags(){
 alphasdana_state s;s.m_icemsr=7; // Register fixture only, not generated events.
 s.icemsr_w(0,0,0xffff);if(s.icemsr_r()!=7 || s.blocked)return false;
 s.icemsr_w(0,2,0x00ff);if(s.icemsr_r()!=5 || s.blocked)return false;
 s.icemsr_w(0,0xff00,0xff00);if(s.icemsr_r()!=5 || s.blocked)return false;
 s.icemsr_w(0,0xfff7,0xffff);if(s.icemsr_r()!=0 || s.blocked)return false;
 s.icemsr_w(0,7,0x00ff);return s.icemsr_r()==0 && !s.blocked;
}
constexpr bool guards(){
 for(u16 bit:{u16(1),u16(2),u16(4),u16(0x10),u16(0x40)}){
  alphasdana_state s;s.icemcr_w(0,8,0xffff);
  s.icemcr_w(0,8|bit,0x00ff);
  if(!s.blocked || s.icemcr_r()!=8 || s.address!=0xfffffd0c || s.reason!="ICE_CONTROL_MODE_UNIMPLEMENTED")return false;
 }
 alphasdana_state s;s.m_icemsr=7;
 s.icemsr_w(0,0x000f,0xffff); // Bit3 is EMUEN, unlike secondary Linux headers.
 return s.blocked && s.icemsr_r()==7 && s.address==0xfffffd0e
  && s.reason=="ICE_EMULATION_MODE_UNIMPLEMENTED";
}
static_assert(setup_and_lanes());
static_assert(flags());
static_assert(guards());
'''
        compiler = shutil.which('c++')
        self.assertIsNotNone(compiler)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp') as f:
            f.write(unit)
            f.flush()
            result = subprocess.run(
                [compiler, '-std=c++20', '-fsyntax-only', '-Wall', '-Wextra', '-Werror', f.name],
                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
