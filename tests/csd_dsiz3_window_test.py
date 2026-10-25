#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Production chip-select decoder; manufacturer AN2148 Table 5."""
from pathlib import Path
import shutil, subprocess, tempfile, unittest
SOURCE=Path(__file__).resolve().parents[1]/"src/mame/skeleton/alphasdana.cpp"
class CSDSiz(unittest.TestCase):
 def test_actual_controlled_dram_window(self):
  s=SOURCE.read_text()
  sig="u32 cs_size(unsigned group) const"
  a=s.index(sig);b=s.index("{",a);d=0
  for k in range(b,len(s)):
   if s[k]=="{":d+=1
   if s[k]=="}":
    d-=1
    if not d:break
  method=s[a:k+1]
  self.assertIn("0x0040",method)
  unit="""
#include <cstdint>
using u16=std::uint16_t;using u32=std::uint32_t;
struct D {u16 m_cs_select[4]={},m_cs_control[3]={};
constexpr """+method+"""
};
constexpr bool check(){
 D a; a.m_cs_select[3]=0x1a83; a.m_cs_control[0]=0x0140;
 if(a.cs_size(3)!=0x1000000)return false; // UK1.5 16 MiB CS D window
 a.m_cs_control[0]=0x0100;
 if(a.cs_size(3)!=0x10000)return false; // Legacy 64KiB with DSIZ3=0
 a.m_cs_control[0]=0x0140; a.m_cs_select[3]=0x1e83;
 if(a.cs_size(3)!=0x2000000)return false; // COMB 32MiB
 a.m_cs_select[3]=0x0281;
 if(a.cs_size(3)!=0x800000)return false; // size 000 and DSIZ3=1
 a.m_cs_select[3]=0x028f;
 if(a.cs_size(3)!=0x400000)return false; // siz 111, still 4MiB
 a.m_cs_select[0]=0x018d;
 if(a.cs_size(0)!=0x800000)return false; // CSA SIZ=110 => 8 MiB
 return true;
}
static_assert(check());
"""
  with tempfile.NamedTemporaryFile(mode="w",suffix=".cpp") as f:
   f.write(unit);f.flush()
   compiler=shutil.which("clang++-21") or shutil.which("c++")
   p=subprocess.run([compiler,"-std=c++20","-fsyntax-only","-Werror",f.name],capture_output=True,text=True,timeout=60)
  self.assertEqual(p.returncode,0,p.stderr)
if __name__=="__main__":unittest.main()
