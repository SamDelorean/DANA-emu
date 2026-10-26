#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Test the production VZ PCTLR handler (UK1.5 at 1007D12A).

Motorola MC68VZ328UM §4.5.4 / Table 4-5: PCTLR FFFFF207 reset 1F,
PCEN bit7, WIDTH bits4..0, reserved bits6..5 zero. PCEN+WIDTH31 means
continuous CPU clock (the exact observed original ROM write 0x9f).
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src/mame/skeleton/alphasdana.cpp"


def body(code: str, signature: str) -> str:
    pos = code.index(signature)
    brace = code.index("{", pos)
    depth = 0
    for i in range(brace, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if not depth:
                return code[pos:i + 1].replace("alphasdana_state::", "Model::")
    raise ValueError("Unclosed C++ method")


class PCTLRTest(unittest.TestCase):
    def test_real_controller_full_duty_and_fail_closed_burst(self):
        code = SOURCE.read_text()
        self.assertIn("u8 m_pctlr = 0x1f;", code)
        self.assertIn("m_pctlr = 0x1f;", code)
        self.assertIn("save_item(NAME(m_pctlr));", code)
        mapping = ("m_boot_memory[1](0xfffff207,0xfffff207)"
                   ".rw(FUNC(alphasdana_state::pctlr_r),"
                   "FUNC(alphasdana_state::pctlr_w)).umask16(0x00ff);")
        self.assertEqual(code.count(mapping), 1)
        self.assertNotIn("m_boot_memory[1](0xfffff206,0xfffff207)", code)
        self.assertIn("PCTLR_CPU_BURST_UNIMPLEMENTED", code)
        handler = body(code, "void alphasdana_state::pctlr_w(u8 data)")
        read = body(code, "u8 pctlr_r()")
        cpp = """#include <cstdint>
using u8=std::uint8_t; using u32=std::uint32_t;
struct Model {
    u8 m_pctlr=0x1f;
    bool blocked=false;
    const char *reason=nullptr;
    void physical_block(const char *r,u32,u8) { blocked=true; reason=r; }
    void logerror(const char*,...) {}
    u8 pctlr_r();
    void pctlr_w(u8 data);
};
""" + read.replace("u8 pctlr_r()", "u8 Model::pctlr_r()") + "\n" + handler + """
int main(){
    Model m;
    if(m.pctlr_r()!=0x1f) return 1;
    m.pctlr_w(0x9f); // original UK1.5 PCEN=1, WIDTH=31 -> full CPU clock
    if(m.blocked || m.pctlr_r()!=0x9f) return 2;
    m.pctlr_w(0xff); // reserved bits 6..5 must read zero
    if(m.blocked || m.pctlr_r()!=0x9f) return 3;
    m.pctlr_w(0x9e); // partial CPU clock bursts unmodelled
    if(!m.blocked || m.pctlr_r()!=0x9f) return 4;
    m.blocked=false;
    m.pctlr_w(0x80); // CPU clock fully disabled, reject unqualified sleep
    if(!m.blocked || m.pctlr_r()!=0x9f) return 5;
    m.blocked=false;
    m.pctlr_w(0x02); // PCEN=0: continuous CPU clock irrespective of WIDTH
    if(m.blocked || m.pctlr_r()!=0x02) return 6;
    m.pctlr_w(0x1f);
    if(m.pctlr_r()!=0x1f) return 7;
    return 0;
}
"""
        compiler = shutil.which("clang++-21") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "pctlr.cpp"
            exe = Path(td) / "pctlr"
            src.write_text(cpp)
            built = subprocess.run(
                [compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror",
                 str(src), "-o", str(exe)],
                text=True, capture_output=True, timeout=60
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], text=True, capture_output=True, timeout=10)
            self.assertEqual(ran.returncode, 0, ran.stderr +
                             f"directed case {ran.returncode}")


if __name__ == "__main__":
    unittest.main()
