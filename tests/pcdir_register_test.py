#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Source-extracted Port C and Timer 2 register checks; no synthesized guest boot.

Ghidra source instructions: UK1.5 at 100051A0/100051A6/10005278/1000527E.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/mame/skeleton/alphasdana.cpp"


def inline(source, signature):
    pos = source.index(signature)
    start = source.index("{", pos)
    depth = 0
    for offset in range(start, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if not depth:
                return source[pos:offset + 1]
    raise ValueError(f"Unclosed handler: {signature}")


class PortCAndTimer2(unittest.TestCase):
    def test_actual_handlers_and_native_lane_mappings(self):
        source = DRIVER.read_text()
        for needle in [
            "u8 m_pcdata = 0;", "save_item(NAME(m_pcdata));",
            "u16 m_tctl2=0;", "save_item(NAME(m_tctl2));",
            "m_tctl1=0; m_tctl2=0;", "m_pcpden=0xff; m_pcsel=0xff;",
            "m_boot_memory[1](0xfffff410,0xfffff410)",
            "FUNC(alphasdana_state::pcdir_w)).umask16(0xff00);",
            "m_boot_memory[1](0xfffff411,0xfffff411)",
            "FUNC(alphasdana_state::pcdata_w)).umask16(0x00ff);",
            "m_boot_memory[1](0xfffff610,0xfffff611)",
            "FUNC(alphasdana_state::timer2_tctl_w));",
            "PCDATA_PIN_LEVEL_UNQUALIFIED", "TIMER2_RUNNING_UNIMPLEMENTED",
        ]:
            self.assertIn(needle, source)
        signatures = (
            "void portc_reset()", "u8 pcdir_r()", "void pcdir_w(u8 data)",
            "u8 pcdata_r()", "void pcdata_w(u8 data)",
            "u8 pcpden_r()", "void pcpden_w(u8 data)",
            "u8 pcsel_r()", "void pcsel_w(u8 data)",
            "u16 timer2_tctl_r()", "void timer2_tctl_w(",
        )
        methods = "\n".join("constexpr " + inline(source, sig)
                            for sig in signatures)
        unit = """
#include <cstdint>
using u8=std::uint8_t; using u16=std::uint16_t; using offs_t=unsigned;
struct Device {
    u8 m_pcdir=0, m_pcdata=0, m_pcpden=0, m_pcsel=0;
    u16 m_tctl2=0; bool blocked=false;
    constexpr void physical_block(const char*,unsigned,u16=0){blocked=true;}
""" + methods + """
};
constexpr bool verify() {
    Device d;
    if(d.pcdir_r()!=0 || d.m_pcdata!=0 || d.timer2_tctl_r()!=0) return false;
    // CPU physical init writes to PCDATA while PCSEL is GPIO and DIR is input.
    d.pcdata_w(0xa5);
    if(d.m_pcdata!=0xa5 || d.blocked) return false;
    // Reads are pin levels; only all-GPIO-output pins can safely use the latch.
    d.pcdir_w(0xff); d.pcsel_w(0xff);
    if(d.pcdata_r()!=0xa5) return false;
    d.pcdir_w(0);
    if(d.pcdata_r()!=0xff || !d.blocked) return false;
    d.blocked=false;
    d.pcdata_w(0); if(d.m_pcdata!=0) return false;
    d.pcdir_w(0x55); d.pcpden_w(0x3c);d.pcsel_w(0xc3);
    if(d.pcdir_r()!=0x55||d.pcpden_r()!=0x3c||d.pcsel_r()!=0xc3) return false;
    d.portc_reset();
    if(d.pcdir_r()!=0||d.m_pcdata!=0||d.pcsel_r()!=0||d.pcpden_r()!=0) return false;
    // Genuine 16-bit word 0000 at TCTL2. No running-counter fiction.
    d.timer2_tctl_w(0,0x0000,0xffff);
    if(d.timer2_tctl_r()!=0) return false;
    d.timer2_tctl_w(0,0x0100,0xff00);
    if(d.timer2_tctl_r()!=0x0100) return false;
    d.timer2_tctl_w(0,0x0000,0xff00);
    if(d.timer2_tctl_r()!=0) return false;
    d.timer2_tctl_w(0,0x0001,0x00ff);
    if(!d.blocked||d.timer2_tctl_r()!=0) return false;
    return true;
}
static_assert(verify());
"""
        compiler = shutil.which("clang++-21") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp") as handle:
            handle.write(unit)
            handle.flush()
            test = subprocess.run(
                [compiler, "-std=c++20", "-fsyntax-only",
                 "-Wall", "-Wextra", "-Werror", handle.name],
                capture_output=True, text=True, timeout=60)
        self.assertEqual(test.returncode, 0, test.stderr)


if __name__ == "__main__":
    unittest.main()
