#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Production ISP1161A1 HC/DC regression for canonical Dana MAME driver.

Structural tests run anywhere. With ISP1161_TEST_MAME and ISP1161_TEST_ROM,
also executes the genuine mapped 16-bit HC/DC command/data ports using the
persisted tests/isp1161_hc_dc_bus.lua (19 actual bus assertions). No firmware
or USB peripherals are generated and the installed binary is never replaced.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/mame/skeleton/alphasdana.cpp"
LUA = ROOT / "tests/isp1161_hc_dc_bus.lua"


class ISP1161NativeModelTest(unittest.TestCase):
    def test_control_register_tables_and_isolated_state(self):
        source = SOURCE.read_text()
        for code in (
            "0x6123",                    # HC and DC ChipID, Rev03
            "m_isp_hc_regs32[0x17]",
            "m_isp_hc_regs16[0x42]",
            "m_isp_hc_ram[0x1000]",
            "m_isp_dc_ram[2462]",
            "isp1161_hc_32bit(u8 code)",
            "isp1161_hc_16bit(u8 code)",
            "isp1161_hc_can_write(u8 code)",
            "isp1161_dc_read_command(u8 cmd)",
            "isp1161_dc_write_command(u8 cmd)",
            "void alphasdana_state::isp1161_hc_reset()",
            "void alphasdana_state::isp1161_dc_reset()",
            "save_item(NAME(m_isp_hc_ram));",
            "save_item(NAME(m_isp_dc_ram));",
            "m_boot_memory[1](0x1f000000,0x1f000007)",
        ):
            self.assertIn(code, source, code)
        self.assertEqual(source.count("0x6123"), 3)  # HC reset, HC read, DC read
        self.assertIn("if(code==0x40 || code==0x41)", source)
        self.assertIn("m_isp_dc_interrupt_enable=u32(m_isp_dc_write_low)", source)
        self.assertIn("m_isp_dc_read_phase=0;", source)
        self.assertIn("m_isp_hc_sof_timer->adjust", source)
        self.assertIn("if (value!=0xf6)", source)
        self.assertTrue(LUA.is_file())

    def test_33_real_mame_bus_transactions_when_configured(self):
        mame = os.environ.get("ISP1161_TEST_MAME")
        rom = os.environ.get("ISP1161_TEST_ROM")
        if not mame or not rom:
            self.skipTest("Set ISP1161_TEST_MAME and ISP1161_TEST_ROM for native test")
        with tempfile.TemporaryDirectory() as td:
            logfile = Path(td) / "isp1161_bus_result.txt"
            env = dict(os.environ, DANA_PALM_TRACE=str(logfile))
            args = [
                mame, "asmdana", "-rom", rom,
                "-video", "none", "-sound", "none", "-nothrottle",
                "-skip_gameinfo", "-nowriteconfig",
                "-autoboot_script", str(LUA), "-autoboot_delay", "0",
                "-log", "-oslog"
            ]
            executed = subprocess.run(
                args, cwd=td, env=env, capture_output=True,
                text=True, timeout=45)
            self.assertEqual(executed.returncode, 0, executed.stderr[-1800:])
            self.assertTrue(logfile.exists(), executed.stderr[-1000:])
            evidence = logfile.read_text()
            self.assertIn("USB_DIRECTED_TOTAL_PASS=33", evidence)
            self.assertEqual(len(re.findall(r"^PASS ", evidence, re.MULTILINE)), 33)
            self.assertNotIn("FAIL ", evidence)
            self.assertNotIn("DANA_PHYSICAL_BLOCKED", executed.stderr)


if __name__ == "__main__":
    unittest.main()
