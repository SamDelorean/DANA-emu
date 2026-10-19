#!/usr/bin/env python3
"""Actual handler/observer logic checks; never native MAME or guest qualification."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from d2_1_pllfsr_contract_test import method_body
from lua_contract import check_lua

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / 'src/mame/skeleton/alphasdana.cpp'
LUA = ROOT / 'tests/f1_emutos_boot.lua'


class PortCContract(unittest.TestCase):
    def test_actual_cpp_configuration_handlers(self):
        src = DRIVER.read_text()
        methods = '\n'.join(method_body(src, pattern) for pattern in (
            r'void portc_reset\(\)\s*', r'u8 pcpden_r\(\)\s*',
            r'void pcpden_w\(u8 data\)\s*', r'u8 pcsel_r\(\)\s*',
            r'void pcsel_w\(u8 data\)\s*'))
        harness = '''#include <cstdint>
#include <cassert>
using u8 = std::uint8_t;
struct PortC {
    u8 m_pcpden = 0, m_pcsel = 0;
''' + methods + '''
};
int main() {
    PortC p;
    p.portc_reset();
    assert(p.pcpden_r()==0 && p.pcsel_r()==0); // R-direct software profile
    for (unsigned a=0; a<256; ++a) {
        for (unsigned b=0; b<256; ++b) {
            p.pcpden_w(a); p.pcsel_w(b);
            assert(p.pcpden_r()==a && p.pcsel_r()==b);
            p.pcsel_w(b^255);
            assert(p.pcpden_r()==a && p.pcsel_r()==(b^255));
        }
    }
    p.portc_reset(); assert(p.pcpden_r()==0 && p.pcsel_r()==0);
}
'''
        compiler = shutil.which('c++')
        self.assertIsNotNone(compiler, 'BLOCKED_CXX_COMPILER_MISSING')
        with tempfile.TemporaryDirectory(prefix='dana-portc-cpp-') as td:
            path = Path(td)
            (path/'check.cpp').write_text(harness)
            subprocess.run([compiler, '-std=c++20', '-Wall', '-Wextra', '-Werror',
                            str(path/'check.cpp'), '-o', str(path/'check')], check=True, timeout=90)
            subprocess.run([str(path/'check')], check=True, timeout=20)

    def test_individual_gpio_decodes_and_save_reset(self):
        src = DRIVER.read_text()
        for addr, name in ((0xfffff412, 'pcpden'), (0xfffff413, 'pcsel')):
            line = f'map(0x{addr:x}, 0x{addr:x}).rw(FUNC(alphasdana_state::{name}_r), FUNC(alphasdana_state::{name}_w));'
            self.assertEqual(src.count(line), 1)
            self.assertIn(f'save_item(NAME(m_{name}));', src)
        reset = method_body(src, r'void alphasdana_state::machine_reset\(\)\s*')
        self.assertIn('portc_reset();', reset)
        # No decoded data/input registers, page storage or 24-bit/low aliases.
        for start, end in re.findall(r'map\((0x[0-9a-f]+), (0x[0-9a-f]+)\)', src):
            a, b = int(start, 16), int(end, 16)
            if a <= 0xfffff4ff and b >= 0xfffff400:
                self.assertIn((a, b), [(0xfffff412, 0xfffff412), (0xfffff413, 0xfffff413),
                                       (0xfffff42b, 0xfffff42b)]) # D2.3 independently decoded PFSEL only
            self.assertFalse(0xfff000 <= a <= 0xffffff)

    def test_real_lua_lane_and_neighbor_classification(self):
        src = LUA.read_text()
        functions = src[src.index('local function implemented_byte'):src.index('emu.register_prestart')]
        check_lua(functions + '''
local a=bus_bytes(0xfffff412,0xff00)
assert(#a==1 and a[1]==0xfffff412)
local b=bus_bytes(0xfffff412,0x00ff)
assert(#b==1 and b[1]==0xfffff413)
assert(first_unsupported(a,'write')==nil and first_unsupported(b,'write')==nil)
assert(first_unsupported(bus_bytes(0xfffff412,0xffff),'write')==nil)
-- Whitelisting a neighboring implemented byte must never hide a missing byte.
assert(first_unsupported(bus_bytes(0xfffff300,0xff00),'write')==nil)
assert(first_unsupported(bus_bytes(0xfffff300,0x00ff),'write')==0xfffff301)
assert(first_unsupported(bus_bytes(0xfffff300,0xffff),'write')==0xfffff301)
assert(first_unsupported(bus_bytes(0xfffff410,0xffff),'write')==0xfffff410)
assert(first_unsupported(bus_bytes(0xfffff414,0xff00),'read')==0xfffff414)
assert(first_unsupported(bus_bytes(0xfffff42a,0x00ff),'read')==0xfffff42b)
assert(first_unsupported(bus_bytes(0xfffff440,0x00ff),'read')==0xfffff441)
assert(first_unsupported(bus_bytes(0xfffff310,0xffff),'read')==nil)
assert(first_unsupported(bus_bytes(0xfffff310,0xffff),'write')==0xfffff310)
assert(first_unsupported(bus_bytes(0x00fff412,0xff00),'write')==0x00fff412)
assert(first_unsupported(bus_bytes(0x00000412,0xffff),'write')==nil) -- real RAM
assert(not pcall(bus_bytes,0xfffff413,0xff))
assert(not pcall(bus_bytes,0xfffff412,0))
assert(not pcall(bus_bytes,0xfffff412,0x10000))
''')

    def test_lua_scripts_parse_without_running_emulator(self):
        for file in (LUA, ROOT/'tests/d2_2_gpio_boot.lua'):
            # Compile the complete chunk without executing MAME-specific APIs.
            import json
            check_lua('assert(load(' + json.dumps(file.read_text()) + '))')


if __name__ == '__main__':
    unittest.main(verbosity=2)
