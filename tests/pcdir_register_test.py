#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Check actual production Port C handlers and deliberate PCDATA fail-closed mapping.

The 68k bus-lane/native execution test is recorded separately in
docs/PALM_UK15_NATIVE_PCDIR_PASS_20261025.md.
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
    raise ValueError(f"Unclosed method: {signature}")


class PortCDirection(unittest.TestCase):
    def test_actual_handlers_reset_persistence_and_guarded_lanes(self):
        source = DRIVER.read_text()
        self.assertIn("u8 m_pcdir = 0;", source)
        self.assertIn("save_item(NAME(m_pcdir));", source)
        self.assertIn(
            "m_boot_memory[1](0xfffff410,0xfffff410)"
            ".rw(FUNC(alphasdana_state::pcdir_r),"
            "FUNC(alphasdana_state::pcdir_w)).umask16(0xff00);", source)
        self.assertIn(
            "m_boot_memory[1](0xfffff411,0xfffff411)"
            ".rw(FUNC(alphasdana_state::pcdata_unknown_r),"
            "FUNC(alphasdana_state::pcdata_unknown_w)).umask16(0x00ff);", source)
        self.assertIn("PCDATA_WRITE_UNIMPLEMENTED", source)
        self.assertIn("PCDATA_READ_UNIMPLEMENTED", source)
        self.assertIn("m_pcpden=0xff; m_pcsel=0xff;", source)

        signatures = (
            "void portc_reset()", "u8 pcdir_r()", "void pcdir_w(u8 data)",
            "u8 pcpden_r()", "void pcpden_w(u8 data)",
            "u8 pcsel_r()", "void pcsel_w(u8 data)")
        methods = "\n".join("constexpr " + inline(source, signature)
                            for signature in signatures)
        unit = """
#include <cstdint>
using u8 = std::uint8_t;
struct Device {
    u8 m_pcdir = 0, m_pcpden = 0, m_pcsel = 0;
""" + methods + """
};
constexpr bool check() {
    Device s;
    if (s.pcdir_r() != 0) return false;
    s.pcdir_w(0xff);
    if (s.pcdir_r() != 0xff) return false;
    s.pcdir_w(0xa5);
    if (s.pcdir_r() != 0xa5) return false;
    s.pcpden_w(0x3c); s.pcsel_w(0xc3);
    if (s.pcdir_r() != 0xa5 || s.pcpden_r() != 0x3c
        || s.pcsel_r() != 0xc3) return false;
    s.portc_reset();
    return s.pcdir_r() == 0 && s.pcpden_r() == 0 && s.pcsel_r() == 0;
}
static_assert(check());
"""
        compiler = shutil.which("clang++-21") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp") as handle:
            handle.write(unit)
            handle.flush()
            check = subprocess.run(
                [compiler, "-std=c++20", "-fsyntax-only",
                 "-Wall", "-Wextra", "-Werror", handle.name],
                capture_output=True, text=True, timeout=45)
        self.assertEqual(check.returncode, 0, check.stderr)


if __name__ == "__main__":
    unittest.main()
