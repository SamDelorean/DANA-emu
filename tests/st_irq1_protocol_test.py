#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Exercise production ST electrical IRQ1 and version protocol handlers."""
from pathlib import Path
import subprocess,tempfile,unittest
from rtc_uk15_test import method

class STWireTest(unittest.TestCase):
 def test_production_wire_contract(self):
  root=Path(__file__).resolve().parents[1]
  src=(root/"src/mame/skeleton/alphasdana.cpp").read_text()
  code=r"""
#include <cstdint>
#include <algorithm>
#include <iterator>
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;
struct Model {
 bool m_st_ready=true,m_st_reset_held=false,m_st_irq_high=true,m_st_irq_edge=false;
 u8 m_st_event_count=0,m_gpio[32]={},m_st_version_in=0,m_st_version_out=0,m_st_queue_left=0;
 u32 m_st_pending_keys[4]={},m_pending=0;u16 m_icr=0;
 unsigned updates=0;
 void update_irq_lines(){++updates;}
 void st_irq_update(bool);
 u8 st_version_exchange(u8);
};
"""+method(src,"void alphasdana_state::st_irq_update(")+"\n"+method(src,"u8 alphasdana_state::st_version_exchange(")+r"""
int main(){
 Model d;
 d.st_irq_update(false);
 if(!d.m_st_irq_high||d.m_pending)return 1;
 d.m_st_event_count=1;d.st_irq_update(true);
 if(d.m_st_irq_high||d.m_pending!=0x10000)return 2;
 // A level request cannot be cleared by acknowledging while the pad is low.
 d.m_pending=0;d.st_irq_update(false);
 if(d.m_pending!=0x10000)return 3;
 d.m_st_event_count=0;d.st_irq_update(true);if(d.m_pending)return 4;
 // ET1 falling edge remains latched after the input returns high.
 d.m_icr=0x0800;d.m_st_event_count=1;d.st_irq_update(true);
 d.m_st_event_count=0;d.st_irq_update(true);
 if(!d.m_st_irq_edge||d.m_pending!=0x10000)return 5;
 d.m_st_irq_edge=false;d.st_irq_update(false);if(d.m_pending)return 6;
 // POL1 selects rising edge; an ICR change alone must not invent an edge.
 d.m_icr=0x8800;d.st_irq_update(false);if(d.m_pending)return 7;
 d.m_st_event_count=1;d.st_irq_update(true);if(d.m_pending)return 8;
 d.m_st_event_count=0;d.st_irq_update(true);if(d.m_pending!=0x10000)return 9;
 d.m_gpio[7]=0x10;d.st_irq_update(false);if(d.m_pending)return 10;
 d.m_gpio[7]=0;d.m_gpio[4]=0x10;d.st_irq_update(false);if(d.m_pending)return 11;
 Model v;
 for(char c: "Get Ver!")if(c&&v.st_version_exchange(c))return 12;
 for(char expected: "06.8")if(expected&&v.st_version_exchange(0)!=expected)return 13;
 if(v.m_st_version_in||v.m_st_version_out)return 14;
 v.st_version_exchange('G');v.st_version_exchange('x');
 if(v.m_st_version_in)return 15;
 // A version exchange cannot leak an earlier key packet's payload words.
 v.m_st_queue_left=2;v.m_st_pending_keys[0]=0x100;
 v.st_version_exchange('G');
 if(v.m_st_queue_left||v.m_st_pending_keys[0])return 16;
 return 0;
}
"""
  with tempfile.TemporaryDirectory()as tmp:
   p=Path(tmp)/"st.cpp";exe=Path(tmp)/"st";p.write_text(code)
   build=subprocess.run(["clang++-21","-std=c++20","-Wall","-Wextra","-Werror",str(p),"-o",str(exe)],capture_output=True,text=True,timeout=60)
   self.assertEqual(build.returncode,0,build.stderr)
   run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
   self.assertEqual(run.returncode,0,f"wire case {run.returncode}")
if __name__=="__main__":unittest.main()
