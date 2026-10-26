#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Execute actual production LCD cursor handlers identified from UK1.5 in Ghidra.

Checks the MC68VZ328 manufacturer's register masks, reset, save-state, real
68000 big-endian byte lanes and the physical-only cursor map.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/mame/skeleton/alphasdana.cpp"


def inline(src, signature):
    pos = src.index(signature)
    brace = src.index("{", pos)
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[pos:i + 1]
    raise ValueError("Unclosed production handler: " + signature)


class LCDCursorRegisters(unittest.TestCase):
    def test_production_handlers_reset_bus_lanes_and_reserved_bits(self):
        source = DRIVER.read_text()
        for declaration in (
            "u16 m_lcxp = 0, m_lcyp = 0, m_lcwch = 0x0101;",
            "u8 m_lblkc = 0x7f;",
            "m_lcxp=0; m_lcyp=0; m_lcwch=0x0101; m_lblkc=0x7f;",
            "DANA_LCD_BYTE(lblkc)",
            "save_item(NAME(m_lcxp));", "save_item(NAME(m_lcyp));",
            "save_item(NAME(m_lcwch));", "save_item(NAME(m_lblkc));",
        ):
            self.assertIn(declaration, source)
        registers = (
            ("lcxp", "0xfffffa18,0xfffffa19"),
            ("lcyp", "0xfffffa1a,0xfffffa1b"),
            ("lcwch", "0xfffffa1c,0xfffffa1d"),
        )
        for name, address in registers:
            mapping = f"{address}).rw(FUNC(alphasdana_state::{name}_r),FUNC(alphasdana_state::{name}_w))"
            self.assertIn("m_boot_memory[1](" + mapping, source)
            self.assertIn("map(" + mapping, source)
        byte = "0xfffffa1f,0xfffffa1f).rw(FUNC(alphasdana_state::lblkc_r),FUNC(alphasdana_state::lblkc_w)).umask16(0x00ff);"
        self.assertIn("m_boot_memory[1](" + byte, source)
        self.assertIn("map(" + byte, source)
        signatures = ("u16 lcxp_r()", "void lcxp_w(", "u16 lcyp_r()",
                      "void lcyp_w(", "u16 lcwch_r()", "void lcwch_w(")
        funcs = "\n".join(inline(source, sig) for sig in signatures)
        cpp = r"""
#include <cstdint>
using u8=std::uint8_t; using u16=std::uint16_t; using offs_t=unsigned;
struct Device {
    u16 m_lcxp=0,m_lcyp=0,m_lcwch=0x0101;
    u8 m_lblkc=0x7f;
""" + funcs + r"""
    constexpr u8 lblkc_r() { return m_lblkc; }
    constexpr void lblkc_w(u8 d) { m_lblkc=d; }
};
int main(){
    Device d;
    if(d.lcxp_r()!=0 || d.lcyp_r()!=0 || d.lcwch_r()!=0x0101
        || d.lblkc_r()!=0x7f) return 1;
    // Real UK1.5 read-modify-write must preserve the CC control bits.
    d.lcxp_w(0,0x8000,0xffff);
    if(d.lcxp_r()!=0x8000) return 2;
    d.lcxp_w(0,0x0230,0x03ff);
    if(d.lcxp_r()!=0x8230) return 3;
    d.lcxp_w(0,0xffff,0xffff);
    if(d.lcxp_r()!=0xc3ff) return 4;
    d.lcxp_w(0,0x0000,0x00ff);
    if(d.lcxp_r()!=0xc300) return 5;
    d.lcxp_w(0,0x0000,0xff00);
    if(d.lcxp_r()!=0) return 6;
    d.lcyp_w(0,0xffff,0xffff);
    if(d.lcyp_r()!=0x01ff) return 7;
    d.lcyp_w(0,0x0000,0x00ff);
    if(d.lcyp_r()!=0x0100) return 8;
    d.lcyp_w(0,0x0000,0xff00);
    if(d.lcyp_r()!=0x0000) return 9;
    d.lcwch_w(0,0xffff,0xffff);
    if(d.lcwch_r()!=0x1f1f) return 10;
    d.lcwch_w(0,0x0000,0x00ff);
    if(d.lcwch_r()!=0x1f00) return 11;
    d.lcwch_w(0,0x0000,0xff00);
    if(d.lcwch_r()!=0) return 12;
    d.lblkc_w(0x80);
    if(d.lblkc_r()!=0x80) return 13;
    Device reset;
    if(reset.lcxp_r()!=0 || reset.lcyp_r()!=0 ||
       reset.lcwch_r()!=0x0101 || reset.lblkc_r()!=0x7f) return 14;
    return 0;
}
"""
        compiler = shutil.which("clang++-21") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lcd_cursor.cpp"
            binary = Path(temp) / "lcd_cursor"
            path.write_text(cpp)
            build = subprocess.run(
                [compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror",
                 str(path), "-o", str(binary)],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stderr)
            test = subprocess.run([str(binary)], capture_output=True,
                                  text=True, timeout=10)
            self.assertEqual(test.returncode, 0, test.stderr +
                             f" production cursor handler failed case {test.returncode}")


if __name__ == "__main__":
    unittest.main()
