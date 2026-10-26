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
        for state in ("m_isp_dc_interrupt", "m_isp_dc_read_snapshot", "m_isp_dc_read_phase"):
            self.assertIn(f"save_item(NAME({state}));", code)
        self.assertIn("m_isp_dc_interrupt=0; m_isp_dc_read_snapshot=0; m_isp_dc_read_phase=0;",code)
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
 u32 m_isp_dc_interrupt=0,m_isp_dc_read_snapshot=0;
 u8 m_isp_dc_read_phase=0;
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
 // Philips Rev03 §13.3.6: C0 issues one 32-bit snapshot;
 // the CPU reads LOW then HIGH 16-bit word, no fabricated USB events.
 Mock irq;
 irq.isp1161_w(3,0x00c0,0xffff);
 if(irq.blocked||irq.m_isp_dc_read_phase!=1) return 9;
 if(irq.isp1161_r(2,0xffff)!=0x0000 || irq.m_isp_dc_read_phase!=2) return 10;
 if(irq.isp1161_r(2,0xffff)!=0x0000 || irq.m_isp_dc_read_phase!=0) return 11;
 if(irq.blocked || irq.m_isp_dc_interrupt!=0) return 12;
 irq.isp1161_r(2,0xffff);
 if(!irq.blocked || irq.reason!="ISP1161_DC_READ_UNIMPLEMENTED") return 13;
 // Validate low/high ordering and status-clear mask using synthetic
 // register state injected only in this directed test (never in UK1.5).
 Mock status;
 status.m_isp_dc_interrupt=0x00015b80U;
 status.isp1161_w(3,0x00c0,0xffff);
 if(status.isp1161_r(2,0xffff)!=0x5b80U) return 14;
 if(status.isp1161_r(2,0xffff)!=0x0001U) return 15;
 if(status.m_isp_dc_interrupt!=0x00015b80U) return 16;
 // RESET/RESUME/EOT/SOF/SP_EOT flags are read-to-clear.
 status.m_isp_dc_interrupt=0x0000015bU;
 status.isp1161_w(3,0xc0,0xffff);
 status.isp1161_r(2,0xffff);status.isp1161_r(2,0xffff);
 if(status.m_isp_dc_interrupt!=0x00000100U) return 17;
 // Cannot replace an incomplete C0 two-word read with new command.
 Mock incomplete;
 incomplete.isp1161_w(3,0xc0,0xffff);
 incomplete.isp1161_r(2,0xffff);
 incomplete.isp1161_w(3,0xb8,0xffff);
 if(!incomplete.blocked||incomplete.reason!="ISP1161_DC_INCOMPLETE_READ") return 18;
 // C0 does not interfere with host or previously programmed DC settings.
 if(irq.m_isp_cmd || irq.m_isp_control || irq.m_isp_dc_mode) return 19;
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
