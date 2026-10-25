#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Source-extracted MC68VZ328 SDCTRL initialization sequence.

Motorola/Freescale AN2148, Code Listing 1, matches Dana UK1.5 at
0x10005364/0x1000537E/0x10005398 exactly. No synthetic guest execution.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

DRIVER=(Path(__file__).resolve().parents[1]/"src/mame/skeleton/alphasdana.cpp")

def method(source, sig):
    i=source.index(sig);j=source.index("{",i);depth=0
    for k in range(j,len(source)):
        if source[k]=="{":depth+=1
        if source[k]=="}":
            depth-=1
            if not depth:return source[i:k+1]
    raise ValueError(sig)

class NativeSdramInit(unittest.TestCase):
    def test_real_sequence_and_fail_closed_mappings(self):
        text=DRIVER.read_text()
        self.assertIn("save_item(NAME(m_sdram_init_phase));",text)
        self.assertIn("m_sdram_init_phase=0;",text)
        self.assertIn("(m_dram[2] & 0x8000) && m_sdram_init_phase!=3",text)
        self.assertIn("SDRAM_NOT_INITIALIZED_WRITE",text)
        self.assertIn("DRAM_DISABLED_OR_INIT_READ",text)
        handler=method(text,"void dram_w(offs_t offset, u16 data, u16 mem_mask)")
        unit="""
#include <cstdint>
using u16=std::uint16_t;using u8=std::uint8_t;using offs_t=unsigned;
#define COMBINE_DATA(p) (*(p)=(*(p)&~mem_mask)|(data&mem_mask))
#define logerror(...) ((void)0)
struct Device{
 u16 m_dram[4]={0,0,0x003c,0};u8 m_sdram_init_phase=0;
 bool m_physical_boot=false;
 constexpr """+handler+"""
};
constexpr bool check(){
 Device d;
 // Before DRAMC enable, precharge is not qualified.
 d.dram_w(2,0xc83f,0xffff);if(d.m_sdram_init_phase)return false;
 d.dram_w(2,0xc03f,0xffff);
 d.dram_w(1,0x8000,0xffff);
 d.dram_w(2,0xd43f,0xffff);
 if(d.m_sdram_init_phase)return false; // Out-of-order mode is not ready.
 d.dram_w(2,0xc83f,0xffff);
 if(d.m_sdram_init_phase!=1)return false;
 d.dram_w(2,0xd03f,0xffff);
 if(d.m_sdram_init_phase!=2)return false;
 d.dram_w(2,0xd43f,0xffff);
 if(d.m_sdram_init_phase!=3 || d.m_dram[2]!=0xd43f)return false;
 // Actual native byte read now receives memory, not a stale INIT gate.
 d.dram_w(1,0,0xffff);
 if(d.m_sdram_init_phase!=0)return false;
 d.dram_w(1,0x8000,0xffff);
 if(d.m_sdram_init_phase)return false;
 d.dram_w(2,0xc83f,0xffff);
 d.dram_w(2,0xd03f,0xffff);
 d.dram_w(2,0xd43f,0xffff);
 return d.m_sdram_init_phase==3;
}
static_assert(check());
"""
        compiler=shutil.which("clang++-21") or shutil.which("c++")
        with tempfile.NamedTemporaryFile(mode="w",suffix=".cpp") as f:
            f.write(unit);f.flush()
            result=subprocess.run([compiler,"-std=c++20","-fsyntax-only",
                "-Wall","-Wextra","-Werror",f.name],capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=="__main__": unittest.main()
