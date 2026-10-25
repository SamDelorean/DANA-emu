#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Compile-time checks of actual PLLCR handlers, without a guest or emulator."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from d8_5_physical_boot_test import function

ROOT = Path(__file__).resolve().parents[1]


class PllcrRegister(unittest.TestCase):
    def test_rmw_lanes_reserved_bits_clko_and_unsupported_modes(self):
        source = (ROOT / 'src/mame/skeleton/alphasdana.cpp').read_text()
        methods = '\n'.join('constexpr ' + function(source, signature) for signature in (
            'u16 pllcr_r()', 'bool pllcr_clko_enabled()'))
        write = 'constexpr ' + function(source, 'void alphasdana_state::pllcr_w(')
        unit = r'''
#include <cstdint>
#include <string_view>
using u16=std::uint16_t;using u8=std::uint8_t;using offs_t=unsigned;
template<typename...T> constexpr void discard(T&&...){}
#define logerror(...) discard(__VA_ARGS__)
struct alphasdana_state {
 u16 m_pllcr=0x24b3;u8 m_pfsel=0x87;bool blocked=false;std::string_view reason;
 constexpr void physical_block(const char*r,unsigned,u16){blocked=true;reason=r;}
 constexpr void pllcr_w(offs_t,u16,u16);
''' + methods + '\n};\n' + write + r'''
constexpr bool checks(){
 alphasdana_state s;
 if(s.pllcr_r()!=0x24b3 || s.pllcr_clko_enabled())return false;
 s.pllcr_w(0,s.pllcr_r() & 0xffef,0xffff); // Native ANDI.W operation.
 if(s.blocked || s.pllcr_r()!=0x24a3 || s.pllcr_clko_enabled())return false;
 s.m_pfsel=0x83; // PF2 selects peripheral CLKO instead of GPIO.
 if(!s.pllcr_clko_enabled())return false;
 s.pllcr_w(0,0x00b3,0x00ff); // Low byte: disable CLKO, preserve upper byte.
 if(s.blocked || s.pllcr_r()!=0x24b3 || s.pllcr_clko_enabled())return false;
 s.pllcr_w(0,0xe400,0xff00); // Reserved upper bits read zero.
 if(s.blocked || s.pllcr_r()!=0x24b3)return false;
 s.pllcr_w(0,0x00f7,0x00ff); // Reserved low bits 6/2 read zero.
 if(s.blocked || s.pllcr_r()!=0x24b3)return false;
 s.pllcr_w(0,0,0);if(s.blocked || s.pllcr_r()!=0x24b3)return false;
 s.pllcr_w(0,0x00a3,0x00ff);
 if(s.blocked || s.pllcr_r()!=0x24a3 || !s.pllcr_clko_enabled())return false;
 alphasdana_state sleep;sleep.pllcr_w(0,0x24bb,0xffff);
 if(!sleep.blocked || sleep.reason!="PLL_SLEEP_MODE_UNIMPLEMENTED" || sleep.pllcr_r()!=0x24b3)return false;
 alphasdana_state divider;divider.pllcr_w(0,0x25b3,0xffff);
 if(!divider.blocked || divider.reason!="PLL_CLOCK_MODE_UNIMPLEMENTED" || divider.pllcr_r()!=0x24b3)return false;
 alphasdana_state wake;wake.pllcr_w(0,0x24b2,0xffff);
 return wake.blocked && wake.reason=="PLL_WAKE_DELAY_UNIMPLEMENTED" && wake.pllcr_r()==0x24b3;
}
static_assert(checks());
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
