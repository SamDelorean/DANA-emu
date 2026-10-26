#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Test exact production SDRAM read-permission logic against Motorola CSD bits."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src/mame/skeleton/alphasdana.cpp"


def extract(code, signature):
    start = code.index(signature)
    pos = code.index("{", start)
    depth = 0
    for i in range(pos, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if not depth:
                return code[start:i + 1]
    raise ValueError(signature)


class SDRAMReadProtection(unittest.TestCase):
    def test_actual_rom_rop_and_supervisor_read_semantics(self):
        source = SOURCE.read_text()
        signature = "static bool cs_ram_read_allowed(u16 csd, bool supervisor)"
        method = extract(source, signature)
        self.assertIn(
            "if (ram && !flash && cs_ram_read_allowed(m_cs_select[3],",
            source
        )
        self.assertIn("bool(m_maincpu->state_int(M68K_SR) & 0x2000)", source)
        self.assertIn(
            "&& !(m_cs_select[3] & 0xe000)", source,
            "Existing fail-closed protected writes must remain unchanged"
        )
        self.assertIn("const index=physical_sdram_index(address-cs_base(3))", source)
        body = method.replace("static bool ", "static constexpr bool ", 1)
        cpp = """
#include <cstdint>
using u16 = std::uint16_t;
struct Production {
""" + body + """
};
static_assert(Production::cs_ram_read_allowed(0x0283,false));
static_assert(Production::cs_ram_read_allowed(0x2283,false)); // ROM UK1.5 ROP read
static_assert(Production::cs_ram_read_allowed(0x8283,false)); // RO does not block read
static_assert(Production::cs_ram_read_allowed(0xa283,false)); // RO+ROP read
static_assert(Production::cs_ram_read_allowed(0x4283,true));  // SOP supervisor
static_assert(!Production::cs_ram_read_allowed(0x4283,false)); // SOP user guarded
static_assert(!Production::cs_ram_read_allowed(0x6283,false)); // SOP+ROP user
static_assert(Production::cs_ram_read_allowed(0x6283,true)); // SOP+ROP supervisor
int main() {}
"""
        compiler = shutil.which("clang++-21") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "physical_dram_read.cpp"
            src.write_text(cpp)
            p = subprocess.run(
                [compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror",
                 "-fsyntax-only", str(src)],
                capture_output=True, text=True, timeout=30
            )
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
