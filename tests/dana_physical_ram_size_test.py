#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Evaluate actual Dana 8/16MiB physical SDRAM index mapping."""
from pathlib import Path
import tempfile,subprocess,shutil,unittest
SOURCE=Path(__file__).resolve().parents[1]/"src/mame/skeleton/alphasdana.cpp"
class DanaSdramCapacity(unittest.TestCase):
 def test_production_capacity_and_aliasing(self):
  s=SOURCE.read_text()
  def m(sig):
   i=s.index(sig);j=s.index("{",i);d=0
   for k in range(j,len(s)):
    if s[k]=="{":d+=1
    if s[k]=="}":
     d-=1
     if d==0:return s[i:k+1]
   raise ValueError(sig)
  self.assertIn('save_pointer(NAME(m_physical_ram_extra),0x600000)',s)
  self.assertIn('PORT_START("PHYSRAM")',s)
  self.assertIn('m_physical_ram_extra[(index-0x400000)>>1]',s)
  methods="\n".join("constexpr "+m(x) for x in (
   "u32 physical_sdram_bytes() const","u32 physical_sdram_index(u32 index) const"))
  unit="""
#include <cstdint>
using u32=std::uint32_t;
struct P{u32 value; constexpr u32 read()const{return value;}};
struct D{
 P port{1};P *m_sdram_profile=&port;
"""+methods+"""
};
constexpr bool check(){
 D d;
 if(d.physical_sdram_bytes()!=0x1000000 || d.physical_sdram_index(0x400000)!=0x400000
 || d.physical_sdram_index(0x800000)!=0x800000)return false;
 d.port.value=0;
 if(d.physical_sdram_bytes()!=0x800000 || d.physical_sdram_index(0x800000)!=0
 || d.physical_sdram_index(0xf00000)!=0x700000)return false;
 return true;
}
static_assert(check());
"""
  with tempfile.NamedTemporaryFile(mode="w",suffix=".cpp") as f:
   f.write(unit);f.flush()
   comp=shutil.which("clang++-21") or shutil.which("c++")
   p=subprocess.run([comp,"-std=c++20","-fsyntax-only","-Werror",f.name],capture_output=True,text=True,timeout=60)
  self.assertEqual(p.returncode,0,p.stderr)
if __name__=="__main__":unittest.main()
