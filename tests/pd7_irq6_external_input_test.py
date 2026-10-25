#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Check production Port D external-pin mux, not an inferred board schematic."""
from pathlib import Path
import shutil, subprocess, tempfile, unittest
SOURCE=(Path(__file__).resolve().parents[1]/"src/mame/skeleton/alphasdana.cpp")
class DanaPD7(unittest.TestCase):
    def test_original_cpu_poll_on_external_pin(self):
        code=SOURCE.read_text()
        sig="u8 alphasdana_state::pd_r(offs_t reg)"
        a=code.index(sig);b=code.index("{",a);depth=0
        for k in range(b,len(code)):
            if code[k]=="{":depth+=1
            elif code[k]=="}":
                depth-=1
                if depth==0:break
        method=code[a:k+1].replace("u8 alphasdana_state::pd_r","constexpr u8 pd_r",1)
        self.assertIn('m_pd7_pin->read()',method)
        self.assertIn('PORT_START("PDPIN7")',code)
        self.assertIn('PORT_CONFNAME(0x80,0x80',code)
        unit="""
#include <cstdint>
using u8=std::uint8_t;using offs_t=unsigned;
struct Port{u8 val;constexpr u8 read(){return val;}};
struct D{
 u8 m_gpio[32]={};
 Port irq{0x0c},pd7{0x80};Port *m_sd_irq=&irq,*m_pd7_pin=&pd7;
"""+method+"""
};
constexpr bool check(){
 D d;
 // Physical firmware writes PD direction=0, DATA=0, pull-up=0x1f.
 d.m_gpio[4]=0;d.m_gpio[5]=0;d.m_gpio[6]=0x1f;
 if(d.pd_r(1)!=0x8c)return false; // PD7 high + independent SD input levels.
 d.pd7.val=0;
 if(d.pd_r(1)!=0x0c)return false;
 d.m_gpio[4]=0x80;d.m_gpio[5]=0x80;
 if(d.pd_r(1)!=0x8c)return false; // output latch, not external pin.
 d.m_gpio[5]=0;
 if(d.pd_r(1)!=0x0c)return false;
 return true;
}
static_assert(check());
"""
        compiler=shutil.which("clang++-21") or shutil.which("c++")
        with tempfile.NamedTemporaryFile(mode="w",suffix=".cpp") as f:
            f.write(unit);f.flush()
            p=subprocess.run([compiler,"-std=c++20","-fsyntax-only",
                "-Wall","-Wextra","-Werror",f.name],capture_output=True,text=True,timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
if __name__=="__main__": unittest.main()
