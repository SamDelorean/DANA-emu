#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Compile actual PLLCR and physical clock formulas; no synthetic guest boot."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from d8_5_physical_boot_test import function

ROOT = Path(__file__).resolve().parents[1]


class PllcrRegister(unittest.TestCase):
    def test_rdirect_guard_and_native_physical_clock_transitions(self):
        source = (ROOT / 'src/mame/skeleton/alphasdana.cpp').read_text()
        methods = '\n'.join('constexpr ' + function(source, signature) for signature in (
            'u16 pllcr_r()', 'bool pllcr_clko_enabled()'))
        clocks = '\n'.join('constexpr ' + function(source, signature) for signature in (
            'u32 alphasdana_state::guest_system_clock_hz() const',
            'u32 alphasdana_state::physical_system_clock_hz() const'))
        write = 'constexpr ' + function(source, 'void alphasdana_state::pllcr_w(')
        unit = r'''
#include <cstdint>
#include <string_view>
using u16=std::uint16_t;using u8=std::uint8_t;using u32=std::uint32_t;
using offs_t=unsigned;
template<typename...T> constexpr void discard(T&&...){}
#define logerror(...) discard(__VA_ARGS__)
struct MockCPU {
    u32 hz=0;
    constexpr void set_unscaled_clock(u32 value){hz=value;}
};
struct alphasdana_state {
    u16 m_pllcr=0x24b3,m_pllfsr=0x0347,m_tctl1=0,m_tcn1=0;
    u8 m_pfsel=0x87;
    bool m_physical_boot=false,blocked=false;
    std::string_view reason;
    MockCPU cpu;MockCPU *m_maincpu=&cpu;
    constexpr void physical_block(const char*r,unsigned,u16){blocked=true;reason=r;}
    constexpr u16 timer1_tcn_r(){return m_tcn1;}
    constexpr void timer1_schedule(){}
    constexpr void pllcr_w(offs_t,u16,u16);
    constexpr u32 guest_system_clock_hz() const;
    constexpr u32 physical_system_clock_hz() const;
''' + methods + '\n};\n' + clocks + '\n' + write + r'''
constexpr bool checks(){
 alphasdana_state s;
 if(s.pllcr_r()!=0x24b3 || s.pllcr_clko_enabled())return false;
 if(s.guest_system_clock_hz()!=33161216)return false;
 s.pllcr_w(0,s.pllcr_r() & 0xffef,0xffff);
 if(s.blocked || s.pllcr_r()!=0x24a3 || s.pllcr_clko_enabled())return false;
 s.m_pfsel=0x83;
 if(!s.pllcr_clko_enabled())return false;
 s.pllcr_w(0,0x00b3,0x00ff);
 if(s.blocked || s.pllcr_r()!=0x24b3 || s.pllcr_clko_enabled())return false;
 s.pllcr_w(0,0xe400,0xff00);
 if(s.blocked || s.pllcr_r()!=0x24b3)return false;
 s.pllcr_w(0,0x00f7,0x00ff);
 if(s.blocked || s.pllcr_r()!=0x24b3)return false;
 s.pllcr_w(0,0,0);if(s.blocked || s.pllcr_r()!=0x24b3)return false;
 alphasdana_state sleep;sleep.pllcr_w(0,0x24bb,0xffff);
 if(!sleep.blocked || sleep.reason!="PLL_SLEEP_MODE_UNIMPLEMENTED"
    || sleep.pllcr_r()!=0x24b3)return false;
 alphasdana_state divider;divider.pllcr_w(0,0x25b3,0xffff);
 if(!divider.blocked || divider.reason!="PLL_CLOCK_MODE_UNIMPLEMENTED"
    || divider.pllcr_r()!=0x24b3)return false;
 alphasdana_state wake;wake.pllcr_w(0,0x24b2,0xffff);
 if(!wake.blocked || wake.reason!="PLL_WAKE_DELAY_UNIMPLEMENTED"
    || wake.pllcr_r()!=0x24b3)return false;
 alphasdana_state physical;
 physical.m_physical_boot=true;
 if(physical.physical_system_clock_hz()!=16580608)return false;
 physical.cpu.hz=physical.physical_system_clock_hz(); // physical_reset already sets CPU clock. // VZ reset clock
 physical.pllcr_w(0,0x24a3,0xffff);
 if(physical.blocked || physical.cpu.hz!=16580608)return false;
 physical.pllcr_w(0,0x22a3,0xffff); // UK1.5 @ CURPC 100053e4
 if(physical.blocked || physical.pllcr_r()!=0x22a3
    || physical.cpu.hz!=2072576)return false;
 physical.pllcr_w(0,0x2483,0xffff); // UK1.5 @ CURPC 10005426
 if(physical.blocked || physical.pllcr_r()!=0x2483
    || physical.cpu.hz!=33161216)return false;
 physical.pllcr_w(0,0x2c83,0xffff); // LCD divider mode needs its own model
 if(!physical.blocked || physical.pllcr_r()!=0x2483)return false;
 return true;
}
static_assert(checks());
'''
        compiler = shutil.which('c++')
        self.assertIsNotNone(compiler)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp') as f:
            f.write(unit)
            f.flush()
            result = subprocess.run(
                [compiler, '-std=c++20', '-fsyntax-only',
                 '-Wall', '-Wextra', '-Werror', f.name],
                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
