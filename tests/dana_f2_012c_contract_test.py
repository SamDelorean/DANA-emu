#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""F2-only production-method and Motorola/EmuTOS-contract tests, not native MAME PASS.

Only the single real DIAG driver is read. Compiled C++ extraction is a
small transient test executable, NOT an alternate Dana emulator.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

# Exact reusable helpers from previously qualified source-method suites.
# No import from an unrelated revision of the local T checkout.
def method_body(source: str, start_pattern: str) -> str:
    match=re.search(start_pattern,source)
    if not match: raise AssertionError("Missing production method: "+start_pattern)
    opening=source.index("{",match.start())
    depth=0
    for i in range(opening,len(source)):
        if source[i]=="{": depth+=1
        elif source[i]=="}":
            depth-=1
            if depth==0: return source[match.start():i+1]
    raise AssertionError("Unclosed C++ method")

def compile_logic(code):
    # Standalone production-method test; not another emulator/DIAG build.
    with tempfile.TemporaryDirectory(prefix="dana-f2-method-") as temp:
        work=Path(temp)
        (work/"test.cpp").write_text("#include <initializer_list>\n"+code)
        subprocess.run(["c++","-std=c++20","-Wall","-Wextra","-Werror",
            "-fsanitize=address,undefined",str(work/"test.cpp"),"-o",str(work/"logic")],
            check=True,timeout=60)
        subprocess.run([str(work/"logic")],check=True,timeout=10)

ROOT=Path(__file__).resolve().parents[1]
DRIVER=ROOT/"src/mame/skeleton/alphasdana.cpp"


class DanaF2FromQualified012C(unittest.TestCase):
    def test_f2_scope_and_pinned_guest_contract(self):
        src=DRIVER.read_text()
        for required in (
            'required_ioport m_pen_contact;', 'required_ioport m_pen_x;',
            'required_ioport m_pen_y;', 'PORT_START("PEN")',
            'PORT_START("PENX")', 'PORT_START("PENY")',
            'u16 alphasdana_state::pen_exchange(unsigned width, u16 outgoing)',
            'save_item(NAME(m_pen_command));', 'save_item(NAME(m_pen_sample));',
            'm_pen_command=0; m_pen_sample=0;',
            'if ((m_spi2_ctrl & 0x0300)!=0x0300)',
        ):
            self.assertIn(required,src)
        for forbidden in ('device_serial_interface', 'm_spi1_rx',
                          'm_extra_keys', 'm_uart_tx_fifo', 'scans[128]'):
            self.assertNotIn(forbidden,src)
        spi=method_body(src,r'void alphasdana_state::spi2_ctrl_w\(offs_t, u16 data, u16 mem_mask\)\s*')
        # In 012-C, IRQ4 synthesis is an independent unqualified workstream.
        self.assertNotIn('update_irq_lines',spi)
        self.assertNotIn('(m_spi2_ctrl & 0x2100)',spi)
        # CPU finder and all other peripherals retain the qualified 012-C form.
        self.assertIn('required_device<dana_vz_cpu_device> m_maincpu;',src)
        self.assertNotIn('m_st_queue_pos',src)

    def test_sdl_pointer_reuses_single_absolute_lightgun_input(self):
        """Source contract, not a claim of an interactive GUI test."""
        src=DRIVER.read_text()
        pen_start=src.index('PORT_START("PEN")')
        x_start=src.index('PORT_START("PENX")',pen_start)
        y_start=src.index('PORT_START("PENY")',x_start)
        keys_start=src.index('PORT_START("KEYS")',y_start)
        pen=src[pen_start:x_start]
        x=src[x_start:y_start]
        y=src[y_start:keys_start]
        # SDL lightgun module consumes window mouse motion AND button events.
        # Do not mix a second mouse-class input provider for contact alone.
        self.assertIn('PORT_CODE(GUNCODE_BUTTON1)',pen)
        self.assertIn('PORT_PLAYER(1)',pen)
        self.assertNotIn('MOUSECODE_BUTTON1',pen)
        self.assertIn('IPT_LIGHTGUN_X',x)
        self.assertIn('IPT_LIGHTGUN_Y',y)
        for axis in (x,y):
            self.assertIn('PORT_MINMAX(0,0xffff)',axis)
            self.assertIn('PORT_PLAYER(1)',axis)
        self.assertIn('m_screen->set_size(560,160)',src)
        self.assertIn('m_screen->set_visarea(0,559,0,159)',src)
        self.assertNotIn('call_mousevec(',src)
        self.assertNotIn('GEM_MOUSE',src)

    def test_exact_EmuTOS_pen_spi2_and_existing_st_slave(self):
        src=DRIVER.read_text()
        pf=src[src.index('    u8 pf_r(offs_t reg)'):src.index('    void pf_w(offs_t reg, u8 value)')]
        pg=src[src.index('    u8 pg_r(offs_t reg)'):src.index('    DANA_GPIO_PORT(pj, 5)')]
        adc=method_body(src,r'u16 alphasdana_state::pen_exchange\(unsigned width, u16 outgoing\)\s*')
        spi=method_body(src,r'void alphasdana_state::spi2_ctrl_w\(offs_t, u16 data, u16 mem_mask\)\s*')
        compile_logic('''#include <cstdint>
#include <cassert>
using u8=std::uint8_t;
using u16=std::uint16_t;
using u32=std::uint32_t;
using offs_t=unsigned;
#define COMBINE_DATA(p) (*(p)=(*(p)&~mem_mask)|(data&mem_mask))
struct Port {unsigned value=0; unsigned read() const{return value;}};
struct alphasdana_state {
 Port pen, x, y;
 Port *m_pen_contact=&pen, *m_pen_x=&x, *m_pen_y=&y;
 u8 m_gpio[32]={}; u8 m_pfsel=0xc5, m_pen_command=0;
 u16 m_spi2_data=0, m_spi2_ctrl=0, m_pen_sample=0;
 unsigned st_calls=0;
 u8 st_exchange(u8){++st_calls;return 0xaa;}
 u16 pen_exchange(unsigned,u16);
 void spi2_ctrl_w(offs_t,u16,u16);
'''+pf+pg+'''};
'''+adc+spi+'''
int main() {
 alphasdana_state s;
 // R-direct preset: PE3/ST and PG2/ADC both deselected.
 s.m_gpio[9]=0x08; s.m_gpio[17]=0x1d;
 // Input PF1 low when pen touches, and high when pen lifted.
 assert((s.pf_r(1)&2)==2);
 s.pen.value=1; assert((s.pf_r(1)&2)==0);
 // Output PF1 must preserve its latch; dedicated function must not override.
 s.m_gpio[12]=2; s.m_gpio[13]=2; assert((s.pf_r(1)&2)==2);
 s.m_gpio[12]=0; s.m_pfsel|=2; assert((s.pf_r(1)&2)==2);
 s.m_pfsel&=~u8(2); assert((s.pf_r(1)&2)==0);
 auto ctrl=[&](u16 value){s.spi2_ctrl_w(0,value,0xffff);};
 auto transfer=[&](u16 value,u16 command){
     s.m_spi2_data=value; ctrl(command);
     assert((s.m_spi2_ctrl & 0x0100)==0);
     assert((s.m_spi2_ctrl & 0x0080)==0x0080);
     return s.m_spi2_data;
 };
 // Exact EmuTOS sequence: 0x2247 / cmd 0x90 / PG2 select /
 // 0x2347, then 0x224f / data=0 / 0x234f / PG2 deselect.
 auto penread=[&](u8 command){
     ctrl(0x2247);
     s.m_spi2_data=command; s.pg_w(1,0x19); // PG2 active low
     ctrl(0x2347); assert(s.m_spi2_data==0xff);
     s.m_spi2_data=0; ctrl(0x224f); ctrl(0x234f);
     u16 result=s.m_spi2_data;
     s.pg_w(1,0x1d);
     assert(s.m_pen_command==0 && s.m_pen_sample==0);
     return result;
 };
 assert(penread(0x90)==u16(290u<<4));
 assert(penread(0xd0)==u16(200u<<4));
 s.x.value=65535; s.y.value=65535;
 assert(penread(0x90)==u16(3760u<<4));
 assert(penread(0xd0)==u16(3650u<<4));
 assert(penread(0x55)==0xffff);
 // Manufacturer: ENABLE bit9, exchange bit8, speed is NOT an enable bit.
 s.x.value=0;s.pg_w(1,0x19);
 s.m_spi2_data=0x90;
 ctrl(0x0347); // 0x2000 rate bit is not set
 assert(s.m_pen_command==0x90);
 s.m_spi2_data=0;ctrl(0x034f);
 assert(s.m_spi2_data==u16(290u<<4));
 s.pg_w(1,0x1d);
 // Exchange without enable must not consume a command.
 s.pg_w(1,0x19); s.m_spi2_data=0x90; ctrl(0x0147);
 assert(s.m_pen_command==0);
 s.pg_w(1,0x1d);
 // No-pen does not invent a valid reading.
 s.pen.value=0;
 assert(penread(0x90)==0xffff);
 s.pen.value=1;
 // Disabled/overlapping slaves produce idle-high responses.
 unsigned prev=s.st_calls;
 s.pg_w(1,0x19);s.m_gpio[9]=0;
 assert(transfer(0x90,0x2347)==0xff);
 assert(s.st_calls==prev);
 s.pg_w(1,0x1d);
 s.m_gpio[9]=0x08;
 assert(transfer(0x90,0x2347)==0xff);
 // Original ST keyboard over PE3 still returns its reply.
 s.m_gpio[9]=0; prev=s.st_calls;
 assert(transfer(0x00,0x2307)==0xaa);
 assert(s.st_calls==prev+1);
}
''')

if __name__=="__main__":
    unittest.main()
