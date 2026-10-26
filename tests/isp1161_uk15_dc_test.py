#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Compile actual ISP1161 HC/DC production handlers and test the Ghidra DC sequence."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/mame/skeleton/alphasdana.cpp"


def method(text, signature):
    start = text.index(signature)
    first = text.index("{", start)
    count = 0
    for pos in range(first, len(text)):
        if text[pos] == "{":
            count += 1
        elif text[pos] == "}":
            count -= 1
            if not count:
                return text[start:pos + 1].replace("alphasdana_state::", "Mock::")
    raise ValueError("Missing body for " + signature)


class DCNativeInitTest(unittest.TestCase):
    def test_production_ISP1161_HC_DC_state_and_original_boot(self):
        code = SOURCE.read_text()
        for required in (
            "m_isp_dc_cmd=0; m_isp_dc_pending=false;",
            "save_item(NAME(m_isp_dc_cmd));",
            "save_item(NAME(m_isp_dc_unlocked));",
            "save_item(NAME(m_isp_dc_hw));",
        ):
            self.assertIn(required, code)
        self.assertIn("save_item(NAME(m_isp_dc_mode));", code)
        self.assertIn("save_item(NAME(m_isp_dc_suspend_requested));", code)
        self.assertIn(
            "m_boot_memory[1](0x1f000000,0x1f000007)"
            ".rw(FUNC(alphasdana_state::isp1161_r),"
            "FUNC(alphasdana_state::isp1161_w));", code
        )
        handlers = "\n".join([
            method(code, "void alphasdana_state::isp1161_w("),
            method(code, "u16 alphasdana_state::isp1161_r("),
        ])
        cpp = r"""
#include <cstdint>
#include <string>
#include <cstdio>
using u8=std::uint8_t;
using u16=std::uint16_t;
using u32=std::uint32_t;
using offs_t=unsigned;
struct Mock {
 bool blocked=false;
 std::string reason;
 u8 m_isp_cmd=0,m_isp_phase=0;
 u16 m_isp_low=0,m_isp_up_irq=0,m_isp_itl_len=0,m_isp_atl_len=0,m_isp_hardware=0x28;
 u32 m_isp_control=0,m_isp_interrupt_status=0,m_isp_interrupt_enable=0,
     m_isp_frame_interval=0x27782edf;
 u8 m_isp_dc_cmd=0;
 bool m_isp_dc_pending=false,m_isp_dc_unlocked=false,m_isp_dc_suspend_requested=false;
 u16 m_isp_dc_hw=0,m_isp_dc_mode=0;
 void physical_block(const char* s,u32,u16=0){ blocked=true;reason=s; }
 void logerror(const char*,...){}
 void isp1161_w(offs_t,u16,u16);
 u16 isp1161_r(offs_t,u16);
};
""" + handlers + r"""
int main() {
 Mock d;
 auto cmd=[&](u16 x){d.isp1161_w(3,x,0xffff);};
 auto data=[&](u16 x){d.isp1161_w(2,x,0xffff);};
 cmd(0xb0);data(0xaa37);
 if (d.blocked||!d.m_isp_dc_unlocked||d.m_isp_dc_pending) return 1;
 cmd(0xba);data(0x0f04);
 if(d.blocked||d.m_isp_dc_hw!=0x0f04) return 2;
 cmd(0xb8);data(0x0020);
 if(d.blocked||d.m_isp_dc_mode!=0x0020||d.m_isp_dc_suspend_requested) return 3;
 cmd(0xb8);
 // Original M68000 CLR.W first reads the write port; this is discarded.
 if(d.isp1161_r(2,0xffff)!=0xffff||d.blocked||!d.m_isp_dc_pending) return 4;
 data(0x0000);
 if(d.blocked||d.m_isp_dc_mode!=0||!d.m_isp_dc_suspend_requested) return 5;
 if(d.m_isp_cmd!=0||d.m_isp_phase!=0||d.m_isp_control!=0) return 6;
 // Incomplete command must not silently accept another command.
 cmd(0xb8);cmd(0xba);
 if(!d.blocked||d.reason!="ISP1161_DC_INCOMPLETE_WRITE") return 7;
 Mock bad;
 bad.isp1161_w(3,0xb0,0xffff);bad.isp1161_w(2,0x1234,0xffff);
 if(!bad.blocked||bad.m_isp_dc_unlocked) return 8;
 return 0;
}
"""
        compiler = shutil.which("clang++-21") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "isp1161_dc.cpp"
            exe = Path(td) / "isp1161_dc"
            path.write_text(cpp)
            build = subprocess.run(
                [compiler, "-std=c++20", "-Wall", "-Wextra",
                 "-Werror", str(path), "-o", str(exe)],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(exe)], capture_output=True,
                                    text=True, timeout=10)
            self.assertEqual(result.returncode, 0,
                             f"original handlers test returned {result.returncode}")


if __name__ == "__main__":
    unittest.main()
