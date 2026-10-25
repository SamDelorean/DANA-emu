#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Compile source-extracted ISP1161 data/command handlers, not a fake guest run.

Philips ISP1161(A) HC §8.3: 16-bit DATA at 1F000000, CMD at 1F000002,
lower word first for 32-bit registers. Original UK1.5 writes from Ghidra.
"""
from pathlib import Path
import shutil, subprocess, tempfile, unittest

SOURCE=Path(__file__).resolve().parents[1]/"src/mame/skeleton/alphasdana.cpp"

def extract(s,signature):
    start=s.index(signature);opening=s.index("{",start);depth=0
    for i in range(opening,len(s)):
        if s[i]=="{":depth+=1
        elif s[i]=="}":
            depth-=1
            if depth==0:return s[start:i+1]
    raise ValueError(signature)

class ISP1161Init(unittest.TestCase):
    def test_production_register_protocol(self):
        s=SOURCE.read_text()
        self.assertIn("m_boot_memory[1](0x1f000000,0x1f000003)",s)
        for marker in [
            "save_item(NAME(m_isp_command))",  # adjusted below to exact field
            "ISP1161_REQUIRES_WORD_ACCESS", "ISP1161_COMMAND_UNIMPLEMENTED",
            "ISP1161_FIFO_ALLOCATION_INVALID", "ISP1161_CONTROL_UNMODELLED"
        ][1:]:self.assertIn(marker,s)
        self.assertIn("save_item(NAME(m_isp_cmd))",s)
        self.assertIn("save_item(NAME(m_isp_frame_interval))",s)
        write=extract(s,"void alphasdana_state::isp1161_w(")
        read=extract(s,"u16 alphasdana_state::isp1161_r(")
        write=write.replace("void alphasdana_state::isp1161_w","constexpr void isp1161_w",1)
        read=read.replace("u16 alphasdana_state::isp1161_r","constexpr u16 isp1161_r",1)
        unit=r'''
#include <cstdint>
using u8=std::uint8_t;using u16=std::uint16_t;
using u32=std::uint32_t;using offs_t=unsigned;
#define logerror(...) ((void)0)
struct Controller {
 u8 m_isp_cmd=0,m_isp_phase=0;
 u16 m_isp_low=0,m_isp_up_irq=0,m_isp_itl_len=0,m_isp_atl_len=0,m_isp_hardware=0x28;
 u32 m_isp_control=0,m_isp_interrupt_status=0,
     m_isp_interrupt_enable=0,m_isp_frame_interval=0x27782edf;
 bool stopped=false;u32 blocked_addr=0;
 constexpr void physical_block(const char*,u32 a,u16=0){stopped=true;blocked_addr=a;}
''' + write + '\n' + read + r'''
};
constexpr bool checks() {
 Controller d;
 auto cmd=[&](u16 c){d.isp1161_w(1,c,0xffff);};
 auto data=[&](u16 v){d.isp1161_w(0,v,0xffff);};
 // Exact ROM initialization values and ordering.
 d.m_isp_interrupt_enable=0xffffffff;
 cmd(0x85); data(0xffff);data(0xffff);
 if(d.stopped||d.m_isp_phase||d.m_isp_interrupt_enable)return false;
 d.m_isp_interrupt_status=0xff0f;
 cmd(0x83);data(0xffff);data(0xffff);
 if(d.m_isp_interrupt_status)return false;
 d.m_isp_up_irq=0x77;cmd(0xa4);data(0x77);
 if(d.m_isp_up_irq)return false;
 cmd(0xaa);data(0);
 cmd(0xab);data(0x1000);
 if(d.m_isp_itl_len||d.m_isp_atl_len!=0x1000)return false;
 cmd(0x8d);data(0x2edf);data(0x2778);
 if(d.m_isp_frame_interval!=0x27782edf)return false;
 cmd(0xa0);data(0x1008);
 if(d.m_isp_hardware!=0x1008)return false;
 cmd(0x83);data(0xffff);data(0xffff);
 cmd(0x81);data(0x80);data(0);
 if(d.m_isp_control!=0x80)return false;
 cmd(0x81);data(0xc0);data(0);
 if(d.stopped||d.m_isp_control!=0xc0)return false;
 // 68000 CLR.W reads the current selected write port but discards data.
 d.isp1161_r(0,0xffff);
 if(d.stopped||d.m_isp_control!=0xc0)return false;
 // A read without a selected write command must still fail closed.
 Controller read_without_command;
 read_without_command.isp1161_r(0,0xffff);
 if(!read_without_command.stopped||
    read_without_command.blocked_addr!=0x1f000000)return false;
 Controller bad;
 bad.isp1161_w(1,0xff,0xffff);
 if(!bad.stopped||bad.blocked_addr!=0x1f000002)return false;
 Controller half;
 half.isp1161_w(1,0x85,0xffff);half.isp1161_w(0,0xffff,0xffff);
 half.isp1161_w(1,0x83,0xffff);
 if(!half.stopped)return false;
 Controller invalid_fifo;
 invalid_fifo.isp1161_w(1,0xaa,0xffff);
 invalid_fifo.isp1161_w(0,0x801,0xffff);
 if(!invalid_fifo.stopped)return false;
 Controller invalid_width;
 invalid_width.isp1161_w(1,0x85,0xff00);
 if(!invalid_width.stopped)return false;
 return true;
}
static_assert(checks());
'''
        with tempfile.NamedTemporaryFile(mode="w",suffix=".cpp") as f:
            f.write(unit);f.flush()
            compiler=shutil.which("clang++-21") or shutil.which("c++")
            result=subprocess.run([compiler,"-std=c++20","-fsyntax-only",
                "-Werror","-Wall","-Wextra",f.name],capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=="__main__":unittest.main()
