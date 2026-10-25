#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Compile-time checks of production WATCHDOG handlers; no emulated guest."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from d8_5_physical_boot_test import function

ROOT = Path(__file__).resolve().parents[1]


class WatchdogRegister(unittest.TestCase):
    def test_lanes_status_counter_clear_disable_and_enabled_guard(self):
        source = (ROOT / 'src/mame/skeleton/alphasdana.cpp').read_text()
        read = function(source, 'u16 watchdog_r()')
        write = function(source, 'void alphasdana_state::watchdog_w(')
        guard = function(source, 'TIMER_CALLBACK_MEMBER(alphasdana_state::watchdog_guard)')
        unit = r'''
#include <cstdint>
using u16=std::uint16_t;using offs_t=unsigned;
struct attotime { static constexpr int never=0; };
struct Timer {int adjustments=0;constexpr void adjust(int){++adjustments;}};
struct alphasdana_state {
 u16 m_watchdog=1;Timer timer;Timer*m_watchdog_guard=&timer;
 bool m_physical_boot=true,blocked=false;
 constexpr void physical_block(const char*,unsigned,u16){blocked=true;}
 constexpr void watchdog_w(offs_t,u16,u16);
 constexpr void guard();
''' + 'constexpr ' + read + '\n};\nconstexpr ' + write + '\n' + guard.replace(
            'TIMER_CALLBACK_MEMBER(alphasdana_state::watchdog_guard)',
            'constexpr void alphasdana_state::guard()', 1) + r'''
constexpr bool checks(){
 alphasdana_state s;
 if(s.watchdog_r()!=1)return false;
 s.watchdog_w(0,0,0xffff); // Original UK1.5 disable write.
 if(s.watchdog_r()!=0 || s.blocked || s.timer.adjustments!=1)return false;
 s.guard();if(s.blocked)return false; // Disabled timer has no action.
 s.m_watchdog=0x0382; // Valid counter/status/control fields.
 s.watchdog_w(0,0xffff,0xff00); // Upper byte clears CNTR only.
 if(s.watchdog_r()!=0x82 || s.blocked)return false;
 s.watchdog_w(0,0x0002,0x00ff); // Writing INTF=0 preserves it.
 if(s.watchdog_r()!=0x82 || s.blocked)return false;
 s.watchdog_w(0,0x0082,0x00ff); // W1C acknowledges INTF, ISEL retained.
 if(s.watchdog_r()!=2 || s.blocked)return false;
 s.m_watchdog=0x0302;int previous=s.timer.adjustments;
 s.watchdog_w(0,0xffff,0); // No lane selected: not a hardware write.
 if(s.watchdog_r()!=0x302 || s.timer.adjustments!=previous)return false;
 s.watchdog_w(0,0xfffc,0xffff); // Reserved and counter bits cannot be set.
 if(s.watchdog_r()!=0 || s.blocked)return false;
 s.watchdog_w(0,3,0xffff); // EN+ISEL retained, unsupported timing stops CPU.
 if(s.watchdog_r()!=3 || !s.blocked)return false;
 alphasdana_state reset;reset.guard();
 if(!reset.blocked || reset.watchdog_r()!=1)return false;
 alphasdana_state ram;ram.m_physical_boot=false;ram.guard();
 return !ram.blocked;
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
