#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Check real production CSD UPSIZ/EUPEN/DUPS2 ROM memory protection.

MC68VZ328UM §6.3.5, Table 6-12 and Example 6-1. Native ROM values:
CSD=2283, CSCTRL1=4150, 16 MiB CSD bank, stack write 0007EC96.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src/mame/skeleton/alphasdana.cpp"


def extract(src, signature):
    pos = src.index(signature)
    start = src.index("{", pos)
    depth = 0
    for end in range(start, len(src)):
        if src[end] == "{":
            depth += 1
        elif src[end] == "}":
            depth -= 1
            if depth == 0:
                return src[pos:end + 1]
    raise ValueError(signature)


class ProtectionAndUpperSize(unittest.TestCase):
    def test_original_csd_actual_handlers_and_exact_boundary(self):
        src = SOURCE.read_text()
        signatures = (
            "static constexpr u32 cs_ram_unprotected_bytes(",
            "static constexpr bool cs_ram_read_allowed(",
            "static constexpr bool cs_ram_write_allowed(",
        )
        defs = "\n".join(extract(src, sig) for sig in signatures)
        for fragment in (
            "if (ram && !flash && cs_ram_read_allowed(",
            "cs_ram_write_allowed(m_cs_select[3],",
            "cs_ram_unprotected_bytes(cs_size(3),",
            "m_cs_select[3],m_cs_control[0])",
            "COMBINE_DATA(&m_ram[index>>1]);",
            "COMBINE_DATA(&m_physical_ram_extra[(index-0x400000)>>1]);",
        ):
            self.assertIn(fragment, src)
        cpp = """
#include <cstdint>
using u16=std::uint16_t; using u32=std::uint32_t;
struct P {
""" + defs + """
};
constexpr u16 CSD=0x2283, CSCTRL1=0x4150;
constexpr u32 BANK=0x1000000, STACK=0x0007ec96;
constexpr u32 SIZE=P::cs_ram_unprotected_bytes(BANK,CSD,CSCTRL1);
static_assert(SIZE==0x200000);  // EUPEN=1, DUPS2=1: 16 MiB / 8
static_assert(STACK<SIZE);
static_assert(P::cs_ram_read_allowed(CSD,true,STACK,SIZE));
static_assert(P::cs_ram_write_allowed(CSD,true,STACK,SIZE));
static_assert(P::cs_ram_write_allowed(CSD,false,STACK,SIZE));
// Proper protection must remain beyond the actual unprotected boundary.
static_assert(P::cs_ram_write_allowed(CSD,true,SIZE-2,SIZE));
static_assert(!P::cs_ram_write_allowed(CSD,true,SIZE,SIZE));
static_assert(!P::cs_ram_write_allowed(CSD,true,BANK-2,SIZE));
static_assert(P::cs_ram_read_allowed(CSD,true,BANK-2,SIZE));
// Legacy UPSIZ uses 32..256 KiB; extended division requires EUPEN.
static_assert(P::cs_ram_unprotected_bytes(BANK,CSD,0x0150)==0x8000);
static_assert(P::cs_ram_unprotected_bytes(BANK,CSD,0x4140)==0x20000);
static_assert(P::cs_ram_unprotected_bytes(BANK,CSD,0x0150 | 0x10)==0x8000);
static_assert(!P::cs_ram_write_allowed(CSD,true,STACK,0x8000));
// Check additional UPSIZ configurations and actual Motorola example 6-1.
static_assert(P::cs_ram_unprotected_bytes(0x400000,0x1800,0)==0x40000);
static_assert(P::cs_ram_unprotected_bytes(BANK,0x3983,0x4150)==BANK);
// RO is whole-bank independent of UPSIZ; SOP only protects high region.
static_assert(!P::cs_ram_write_allowed(0x8283,true,STACK,SIZE));
static_assert(!P::cs_ram_write_allowed(0xa283,true,STACK,SIZE));
static_assert(P::cs_ram_write_allowed(0x6283,false,STACK,SIZE));
static_assert(!P::cs_ram_write_allowed(0x6283,false,SIZE,SIZE));
static_assert(P::cs_ram_write_allowed(0x6283,true,SIZE,SIZE)==false);
// ROP off, SOP supervisor permitted in protected area.
static_assert(P::cs_ram_write_allowed(0x4283,true,SIZE,SIZE));
static_assert(!P::cs_ram_write_allowed(0x4283,false,SIZE,SIZE));
static_assert(P::cs_ram_read_allowed(0x4283,true,SIZE,SIZE));
static_assert(!P::cs_ram_read_allowed(0x4283,false,SIZE,SIZE));
static_assert(P::cs_ram_read_allowed(0x4283,false,STACK,SIZE));
int main() {}
"""
        compiler = shutil.which("clang++-21") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "csd_upsiz.cpp"
            source.write_text(cpp)
            result = subprocess.run(
                [compiler, "-std=c++20", "-fsyntax-only",
                 "-Wall", "-Wextra", "-Werror", str(source)],
                capture_output=True, text=True, timeout=40,
            )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
