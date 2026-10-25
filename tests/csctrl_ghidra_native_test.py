#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Evaluate the real production CSCTRL1/2 handlers against native UK1.5 writes."""
from pathlib import Path
import subprocess, shutil, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/"src/mame/skeleton/alphasdana.cpp").read_text()
class CSCTRLNative(unittest.TestCase):
    def test_ghidra_confirmed_init(self):
        head="void alphasdana_state::cs_w(offs_t offset, u16 data, u16 mem_mask)"
        start=SRC.index(head); opening=SRC.index("{",start); depth=0
        for i in range(opening,len(SRC)):
            if SRC[i]=="{":depth+=1
            elif SRC[i]=="}":
                depth-=1
                if depth==0:break
        method=SRC[start:i+1].replace("void alphasdana_state::cs_w","constexpr void cs_w",1)
        self.assertIn("offset==5 ? 0x7f55 : 0xf300",method)
        self.assertIn("CS_CONTROL_RESERVED_BITS",method)
        unit=r"""
#include <cstdint>
using u16=std::uint16_t;using offs_t=unsigned;
#define COMBINE_DATA(p) (*(p)=(*(p)&~mem_mask)|(data&mem_mask))
struct Dev {
  u16 m_cs_base[4]={};u16 m_cs_upper=0;
  u16 m_cs_control[3]={0,0x1000,0x9c00};bool blocked=false;
  constexpr void physical_block(const char*,unsigned,u16=0){blocked=true;}
"""+method+r"""
};
constexpr bool check(){
 Dev d;
 d.cs_w(6,0xd000,0xffff);
 if(d.blocked||d.m_cs_control[1]!=0xd000)return false;
 d.cs_w(5,0x0100,0xffff);
 if(d.blocked||d.m_cs_control[0]!=0x0100)return false;
 d.cs_w(5,0x0140,0xffff);
 if(d.blocked||d.m_cs_control[0]!=0x0140)return false;
 d.cs_w(6,0,0x00ff);
 if(d.m_cs_control[1]!=0xd000)return false;
 d.cs_w(6,0xffff,0x00ff);
 if(!d.blocked||d.m_cs_control[1]!=0xd000)return false;
 d.blocked=false;
 d.cs_w(5,0xffff,0x0002);
 if(!d.blocked||d.m_cs_control[0]!=0x0140)return false;
 return true;
}
static_assert(check());
"""
        compiler=shutil.which("clang++-21") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.NamedTemporaryFile(mode="w",suffix=".cpp") as tmp:
            tmp.write(unit);tmp.flush()
            r=subprocess.run([compiler,"-std=c++20","-fsyntax-only","-Werror",
                              "-Wall","-Wextra",tmp.name],capture_output=True,text=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stderr)
if __name__=="__main__":unittest.main()
