#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Exercise production first-format preset and Gregorian conversion with Clang."""
from pathlib import Path
from datetime import date
import subprocess, tempfile, unittest
from rtc_uk15_test import method

SOURCE=Path(__file__).resolve().parents[1]/"src/mame/skeleton/alphasdana.cpp"

class HostCalendarTest(unittest.TestCase):
 def test_calendar_and_first_format_guards(self):
  src=SOURCE.read_text()
  methods="\n".join(method(src,s) for s in (
   "u32 alphasdana_state::calendar_hours(",
   "u16 alphasdana_state::calendar_format_word("))
  checks=[]
  for year,month,day in [(1904,1,1),(1904,2,29),(2000,1,1),(2005,1,1),(2024,2,28),(2024,2,29),(2024,3,1),
                         (2026,10,30),(2026,12,31),(2027,1,1),(2031,12,31)]:
   expected=(date(year,month,day)-date(1904,1,1)).days*24
   checks.append(f"if(Model::calendar_hours({year},{month-1},{day})!={expected}U) return 1;")
  code=r"""
#include <cstdint>
#include <cstring>
#include <algorithm>
#include <array>
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;
constexpr int STATE_GENPCBASE=1,M68K_D4=2;
struct system_time {struct {int year=2026,month=9,mday=30;}local_time;};
struct Machine {system_time now;bool disabled=false;
 bool side_effects_disabled(){return disabled;}
 void current_datetime(system_time&t){t=now;}};
struct CPU {u32 pc=0x10015c84,d4=0xcd740;
 u32 state_int(int id){return id==STATE_GENPCBASE?pc:d4;}};
struct Model {
 Machine host;CPU cpu;CPU*m_maincpu=&cpu;Machine&machine(){return host;}
 std::array<u16,0x200000> m_ram{};
 u8 m_flash_sha1[20]={0xc8,0x9b,0x8a,0x2b,0x2a,0x5d,0x2a,0x9e,0xd4,0x9a,
  0x7a,0xb2,0x17,0x0a,0xce,0xde,0xcf,0xd2,0x74,0x18};
 u32 m_calendar_store=0,m_calendar_hours=0;u8 m_calendar_phase=0;
 static u32 calendar_hours(int,int,int);
 u16 calendar_format_word(u32,u16,u16);
 void logerror(const char*,...){}
 void write(u32 a,u16 d,u16 mask=0xffff){
  d=calendar_format_word(a,d,mask);
  m_ram[a/2]=(m_ram[a/2]&~mask)|(d&mask);
 }
 void format(u32 base){
  cpu.pc=0x10015c84;write(base,0xfeed);write(base+2,0xface);
  write(base+4,1);write(base+6,1);
  cpu.pc=0x10015cc2;write(base+0x4c,0xc);write(base+0x4e,0xd740);
 }
};
""" + methods + "\nint main(){\n" + "\n".join(checks) + r"""
 for(auto value:{Model::calendar_hours(2025,1,29),Model::calendar_hours(2100,1,29),
    Model::calendar_hours(1903,0,1),Model::calendar_hours(2026,-1,1),
    Model::calendar_hours(2026,12,1),Model::calendar_hours(2026,0,0),
    Model::calendar_hours(2040,11,31)})if(value!=0xffffffffU)return 2;
 auto a=std::make_unique<Model>();a->format(0x80000);
 auto hours=[&](){return (u32(a->m_ram[0x8004c/2])<<16)|a->m_ram[0x8004e/2];};
 if(hours()!=Model::calendar_hours(2026,9,30)||a->m_calendar_phase)return 3;
 // Palm's normal writes, including a deliberate factory year, are untouched.
 a->cpu.pc=0x10017f8e;a->host.now.local_time.year=2027;
 a->write(0x8004e,0xd740);a->write(0x8004c,0xc);
 if(hours()!=0xcd740)return 4;
 // A valid/persisted header must never qualify as a newly cleared store.
 a->format(0x80000);if(hours()!=0xcd740)return 5;
 auto b=std::make_unique<Model>();b->m_flash_sha1[0]^=1;b->format(0x80000);
 if(b->m_ram[0x8004e/2]!=0xd740||b->m_calendar_phase)return 6;
 auto c=std::make_unique<Model>();c->m_ram[0x800fc/2]=1;c->format(0x80000);
 if(c->m_ram[0x8004e/2]!=0xd740)return 7;
 auto d=std::make_unique<Model>();d->cpu.pc=0x10015c84;
 d->write(0x80000,0xfe00,0xff00);if(d->m_calendar_phase)return 8;
 // Saved in-flight word state resumes using its original calendar sample.
 auto e=std::make_unique<Model>();e->cpu.pc=0x10015c84;
 e->write(0x80000,0xfeed);e->write(0x80002,0xface);
 e->write(0x80004,1);e->write(0x80006,1);e->cpu.pc=0x10015cc2;
 e->write(0x8004c,0xc);auto saved=std::make_unique<Model>(*e);
 saved->m_maincpu=&saved->cpu;saved->host.now.local_time.year=2027;
 saved->write(0x8004e,0xd740);
 if(saved->m_ram[0x8004e/2]!=u16(Model::calendar_hours(2026,9,30)))return 9;
 return 0;
}
"""
  code=code.replace("#include <array>","#include <array>\n#include <memory>")
  with tempfile.TemporaryDirectory() as tmp:
   cpp=Path(tmp)/"calendar.cpp";exe=Path(tmp)/"calendar";cpp.write_text(code)
   build=subprocess.run(["clang++-21","-std=c++20","-Wall","-Wextra","-Werror",
    str(cpp),"-o",str(exe)],capture_output=True,text=True,timeout=50)
   self.assertEqual(build.returncode,0,build.stderr)
   run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
   self.assertEqual(run.returncode,0,f"calendar case {run.returncode}")
  for name in ("store","hours","phase"):
   self.assertIn(f"save_item(NAME(m_calendar_{name}));",src)

if __name__=="__main__":unittest.main()
