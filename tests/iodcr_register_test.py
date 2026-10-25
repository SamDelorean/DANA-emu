#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Constant checks of production IODCR handlers; no guest or pad simulation."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from d8_5_physical_boot_test import function

ROOT = Path(__file__).resolve().parents[1]


class IodcrRegister(unittest.TestCase):
    def test_reset_word_byte_lanes_reserved_bits_and_masking(self):
        source = (ROOT / 'src/mame/skeleton/alphasdana.cpp').read_text()
        state = re.search(r'u16 m_iodcr\s*=\s*0x[0-9a-f]+;', source)[0]
        methods = '\n'.join('constexpr ' + function(source, signature) for signature in (
            'u16 iodcr_r()', 'void iodcr_w('))
        reset = re.search(r'm_iodcr\s*=\s*0x[0-9a-f]+;',
                          function(source, 'void alphasdana_state::machine_reset()'))[0]
        unit = r'''
#include <cstdint>
using u16=std::uint16_t;using offs_t=unsigned;
#define COMBINE_DATA(p) (*(p)=(*(p)&~mem_mask)|(data&mem_mask))
struct Device {
''' + state + '\nconstexpr void reset(){' + reset + '}\n' + methods + r'''
};
constexpr bool checks(){
 Device s;
 if(s.iodcr_r()!=0x1fff)return false;
 s.iodcr_w(0,0x0000,0xffff); // Authentic UK1.5 word transaction.
 if(s.iodcr_r()!=0)return false;
 s.iodcr_w(0,0x1a00,0xff00); // Even/high byte, low byte unchanged.
 if(s.iodcr_r()!=0x1a00)return false;
 s.iodcr_w(0,0x00a5,0x00ff); // Odd/low byte, high byte unchanged.
 if(s.iodcr_r()!=0x1aa5)return false;
 s.iodcr_w(0,0xfa00,0xff00); // Reserved bits 15..13 cannot be stored.
 if(s.iodcr_r()!=0x1aa5 || s.m_iodcr!=0x1aa5)return false;
 s.iodcr_w(0,0x0000,0);if(s.iodcr_r()!=0x1aa5)return false;
 s.iodcr_w(0,0xffff,0xffff);if(s.iodcr_r()!=0x1fff || s.m_iodcr!=0x1fff)return false;
 s.iodcr_w(0,0,0x0001);if(s.iodcr_r()!=0x1ffe)return false;
 s.iodcr_w(0,0,0xff00);if(s.iodcr_r()!=0x00fe)return false;
 s.iodcr_w(0,0,0x00ff);if(s.iodcr_r()!=0)return false;
 s.reset();return s.iodcr_r()==0x1fff;
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
