#!/usr/bin/env python3
"""Compile/run the ACTUAL Dana PLLFSR handlers in a minimal C++ harness.

Isolated functional check of selected handler bodies and static integration guards;
NOT a substitute for the genuine MAME DIAG / EmuTOS runtime campaign.
"""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/mame/skeleton/alphasdana.cpp"
LUA = ROOT / "tests/f1_emutos_boot.lua"


def method_body(source: str, start_pattern: str) -> str:
    match = re.search(start_pattern, source)
    if not match:
        raise AssertionError(f"Missing production method: {start_pattern}")
    opening = source.index("{", match.start())
    depth = 0
    for i in range(opening, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start(): i + 1]
    raise AssertionError("Unclosed C++ method")


class VzPllfsrContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = DRIVER.read_text()
        cls.lua = LUA.read_text()

    def test_16_bit_decode_and_native_observer_scope(self):
        self.assertEqual(self.src.count("map(0xfffff202, 0xfffff203).rw("), 1)
        self.assertEqual(self.lua.count("address>=0xfffff202 and address<=0xfffff203"), 1)
        self.assertNotIn("address>=0xfffff200 and address<=0xfffff2ff", self.lua)

    def test_virtual_time_reset_save_and_only_one_clock(self):
        self.assertIn("m_pllfsr = 0x0347;", self.src)
        self.assertIn("save_item(NAME(m_pllfsr));", self.src)
        self.assertIn("save_item(NAME(m_clk32_high));", self.src)
        self.assertIn("m_clk32_high = false;", self.src)
        self.assertIn("timer_alloc(FUNC(alphasdana_state::clk32_tick), this)", self.src)
        self.assertIn("adjust(attotime::from_hz(32768), 0, attotime::from_hz(32768))", self.src)
        self.assertEqual(self.src.count("TIMER_CALLBACK_MEMBER(alphasdana_state::clk32_tick)"), 1)
        self.assertNotIn("map(0xfffff200, 0xfffff2ff)", self.src)

    def test_compiled_production_handler_semantics(self):
        compiler = shutil.which("clang++") or shutil.which("g++")
        if not compiler:
            self.fail("BLOCKED_COMPILER: C++ compiler required; do not claim PASS")
        inline = method_body(self.src, r"u16 pllfsr_r\(\)\s*")
        writer = method_body(self.src, r"void alphasdana_state::pllfsr_w\(offs_t, u16 data, u16 mem_mask\)\s*")
        tick = method_body(self.src, r"TIMER_CALLBACK_MEMBER\(alphasdana_state::clk32_tick\)\s*")
        source = """#include <cstdint>
#include <cassert>
using u16 = std::uint16_t;
using offs_t = unsigned;
#define TIMER_CALLBACK_MEMBER(x) void x()
class alphasdana_state {
public:
    u16 m_pllfsr = 0x0347;
    bool m_clk32_high = false;
""" + inline + """
    void pllfsr_w(offs_t, u16, u16);
    void clk32_tick();
};
""" + writer + "\n" + tick + "\n" + """
int main() {
    alphasdana_state m;
    // True VZ reset; on every oscillator callback CLK32 changes.
    assert(m.pllfsr_r() == 0x0347);
    m.clk32_tick(); assert(m.pllfsr_r() == 0x8347);
    m.clk32_tick(); assert(m.pllfsr_r() == 0x0347);
    // Full-width write changes counters, not read-only CLK32 or reserved bits.
    m.pllfsr_w(0, 0xaabb, 0xffff);
    assert(m.pllfsr_r() == 0x0abb);
    // M68000 big-endian high lane updates Q, low lane updates P.
    m.pllfsr_w(0, 0x0400, 0xff00);
    assert(m.pllfsr_r() == 0x04bb);
    m.pllfsr_w(0, 0x0071, 0x00ff);
    assert(m.pllfsr_r() == 0x0471);
    // One write can update both counters and irrevocably set PROT.
    m.pllfsr_w(0, 0x4123, 0xffff);
    assert(m.pllfsr_r() == 0x4123);
    m.pllfsr_w(0, 0x0000, 0xffff);
    m.pllfsr_w(0, 0x00ff, 0x00ff);
    m.pllfsr_w(0, 0x0800, 0xff00);
    assert(m.pllfsr_r() == 0x4123);
    m.clk32_tick(); assert(m.pllfsr_r() == 0xc123);
    m.clk32_tick(); assert(m.pllfsr_r() == 0x4123);
    // Software cannot clear PROT; reset can.
    m.m_pllfsr = 0x0347; m.m_clk32_high = false;
    assert(m.pllfsr_r() == 0x0347);
    m.pllfsr_w(0, 0x0255, 0xffff);
    assert(m.pllfsr_r() == 0x0255);
}
"""
        with tempfile.TemporaryDirectory(prefix="dana-pllfsr-compiled-") as td:
            path = pathlib.Path(td)
            (path / "real_driver_handlers.cpp").write_text(source)
            build = subprocess.run([compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror",
                                    "-o", str(path / "check"), str(path / "real_driver_handlers.cpp")],
                                   capture_output=True, text=True, timeout=90)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(path / "check")], capture_output=True,
                                 text=True, timeout=20)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
