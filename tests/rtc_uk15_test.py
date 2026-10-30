#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Validate real VZ RTC production handlers with 68000 word accesses.

Checks Motorola MC68VZ328UM 11.2.1, 11.2.6–8 against original Palm OS
TST.L/conditional MOVE.L at FB00, IEN=000A, CTL=0080.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src/mame/skeleton/alphasdana.cpp"


def method(src, signature):
    start = src.index(signature)
    first = src.index("{", start)
    depth = 0
    for i in range(first, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1].replace(
                    "alphasdana_state::", "Model::"
                )
    raise ValueError("Unterminated " + signature)


class RTCAuthenticTest(unittest.TestCase):
    def test_production_rtc_clock_and_interrupt_semantics(self):
        src = SOURCE.read_text()
        for token in (
            "m_rtc_timer = timer_alloc(FUNC(alphasdana_state::rtc_tick), this);",
            "save_item(NAME(m_rtc_time));",
            "save_item(NAME(m_rtc_control));",
            "save_item(NAME(m_rtc_ien));",
            "save_item(NAME(m_rtc_isr));",
            "save_item(NAME(m_rtc_day));",
            "save_item(NAME(m_rtc_offset_seconds));",
            "save_item(NAME(m_rtc_last_tick));",
            "machine().current_datetime(host);",
            "m_rtc_control=0x0080; m_rtc_ien=0; m_rtc_isr=0;",
            "m_rtc_timer->adjust(attotime::from_seconds(1), 0, attotime::from_seconds(1));",
            "active & 0x00000c14",
        ):
            self.assertIn(token, src)
        for first, last, suffix in (
            ("0xfffffb00", "0xfffffb03", "rtc_time"),
            ("0xfffffb0c", "0xfffffb0d", "rtc_control"),
            ("0xfffffb0e", "0xfffffb0f", "rtc_isr"),
            ("0xfffffb10", "0xfffffb11", "rtc_ien"),
        ):
            mapping = (
                f"m_boot_memory[1]({first},{last})"
                f".rw(FUNC(alphasdana_state::{suffix}_r),"
                f"FUNC(alphasdana_state::{suffix}_w));"
            )
            self.assertEqual(src.count(mapping), 1, mapping)

        signatures = (
            "static constexpr bool rtc_time_valid(",
            "u16 rtc_time_r(",
            "u32 alphasdana_state::rtc_host_seconds()",
            "void alphasdana_state::rtc_sync_from_host()",
            "void alphasdana_state::rtc_time_w(",
            "void alphasdana_state::rtc_control_w(",
            "void alphasdana_state::rtc_ien_w(",
            "void alphasdana_state::rtc_isr_w(",
            "void alphasdana_state::rtc_update_irq()",
            "TIMER_CALLBACK_MEMBER(alphasdana_state::rtc_tick)",
        )
        extracted = "\n".join(method(src, sig) for sig in signatures)
        # Inline methods defined inside the real device class become
        # ordinary standalone Model member definitions in the fixture.
        extracted = extracted.replace("static constexpr bool rtc_time_valid(", "constexpr bool Model::rtc_time_valid(")
        extracted = extracted.replace("u16 rtc_time_r(", "u16 Model::rtc_time_r(")
        extracted = extracted.replace("TIMER_CALLBACK_MEMBER(Model::rtc_tick)", "void Model::rtc_tick()")
        cpp = r"""
#include <cstdint>
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;
using s32=std::int32_t;
using offs_t=unsigned;
struct system_time {
 struct {u8 hour=0,minute=0,second=0;} local_time;
};
struct HostMachine {
 u32 seconds=0;
 void current_datetime(system_time &t) {
  const u32 s=seconds%86400;
  t.local_time.hour=s/3600;
  t.local_time.minute=(s/60)%60;
  t.local_time.second=s%60;
 }
};
struct Model {
    static constexpr u32 rtc_time_mask=0x1f3f003fU;
    static constexpr bool rtc_time_valid(u32);
    HostMachine host;
    HostMachine &machine() {return host;}
    u32 m_rtc_time=0,m_rtc_last_tick=0,m_pending=0,m_rtc_alarm=0;
    s32 m_rtc_offset_seconds=0;
    u16 m_rtc_day=0,m_rtc_day_alarm=0,m_rtc_control=0x0080,m_rtc_ien=0,m_rtc_isr=0;
    bool blocked=false;
    const char* error="";
    u32 rtc_host_seconds();
    void rtc_sync_from_host();
    u16 rtc_time_r(offs_t);
    void rtc_time_w(offs_t,u16,u16);
    void rtc_control_w(offs_t,u16,u16);
    void rtc_ien_w(offs_t,u16,u16);
    void rtc_isr_w(offs_t,u16,u16);
    void rtc_update_irq();
    void rtc_tick();
    void update_irq_lines(){}
    void physical_block(const char *name,u32,u16=0) {blocked=true;error=name;}
    void logerror(const char*,...){}
};
""" + extracted + r"""
int main() {
 Model d;
 d.host.seconds=11*3600+42*60+57;
 if(d.rtc_time_r(0)!=0x0b2a || d.rtc_time_r(1)!=57) return 1;
 if(d.m_rtc_isr!=0 || d.m_pending!=0) return 2;
 d.m_rtc_last_tick=d.m_rtc_time;
 d.host.seconds++;
 if(d.rtc_time_r(0)!=0x0b2a || d.rtc_time_r(1)!=58) return 3;
 d.rtc_ien_w(0,0x000a,0xffff); // original UK1.5
 d.rtc_control_w(0,0x0080,0xffff);
 if(d.blocked || d.m_rtc_ien!=0x000a) return 4;
 d.rtc_tick();
 if(d.m_pending!=0 || !(d.m_rtc_isr&0x10)) return 5;
 d.host.seconds+=2;
 d.rtc_tick();
 if(d.m_rtc_time!=0x0b2b0000 || !(d.m_rtc_isr&2) ||
    !(d.m_pending&0x10)) return 6;
 d.rtc_isr_w(0,0x0002,0xffff);
 if(d.m_pending!=0 || (d.m_rtc_isr&2)) return 7;
 d.rtc_time_w(0,0x1834,0xffff); // invalid hour 24
 if(!d.blocked || d.m_rtc_time!=0x0b2b0000) return 8;
 d.blocked=false;
 d.rtc_time_w(0,0x1230,0xffff);
 d.rtc_time_w(1,0x003a,0xffff);
 if(d.blocked || d.rtc_time_r(0)!=0x1230 ||
    d.rtc_time_r(1)!=0x003a) return 9;
 const s32 offset=d.m_rtc_offset_seconds;
 d.host.seconds++;
 if(d.rtc_time_r(0)!=0x1230 || d.rtc_time_r(1)!=0x003b ||
    d.m_rtc_offset_seconds!=offset) return 10;
 d.rtc_tick();
 if(d.m_pending) return 11;
 d.host.seconds++;
 d.rtc_tick();
 if(d.rtc_time_r(0)!=0x1231 || d.rtc_time_r(1)!=0 ||
    !(d.m_rtc_isr&2) || !(d.m_pending&0x10)) return 12;
 d.rtc_isr_w(0,0x0002,0xffff);
 d.rtc_control_w(0,0x0000,0xffff);
 const u32 frozen=d.m_rtc_time;
 d.host.seconds+=3600;
 if(d.rtc_time_r(0)!=u16(frozen>>16) ||
    d.rtc_time_r(1)!=u16(frozen)) return 13;
 d.rtc_tick();
 if(d.m_rtc_time!=frozen || d.m_pending) return 14;
 d.rtc_control_w(0,0x0080,0xffff);
 if(d.rtc_time_r(0)!=u16(frozen>>16) ||
    d.rtc_time_r(1)!=u16(frozen)) return 15;
 d.host.seconds++;
 if(d.rtc_time_r(1)!=1) return 16;
 d.rtc_time_w(0,0x0400,0xff00);
 d.rtc_time_w(0,0x0005,0x00ff);
 if(d.rtc_time_r(0)!=0x0405) return 17;
 d.rtc_ien_w(0,0x0100,0xffff);
 if(!d.blocked || d.m_rtc_ien!=0x000a) return 18;
 Model midnight;
 midnight.host.seconds=23*3600+59*60+59;
 midnight.rtc_time_r(0);
 midnight.m_rtc_last_tick=midnight.m_rtc_time;
 midnight.host.seconds++;
 midnight.rtc_tick();
 if(midnight.m_rtc_time!=0 || midnight.m_rtc_day!=1
    || !(midnight.m_rtc_isr&0x8)) return 19;
 return 0;
}
"""
        compiler = shutil.which("clang++-21") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "rtc_prod.cpp"
            exe = Path(d) / "rtc_prod"
            target.write_text(cpp)
            build = subprocess.run(
                [compiler, "-std=c++20", "-Wall", "-Wextra",
                 "-Werror", str(target), "-o", str(exe)],
                text=True, capture_output=True, timeout=55,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run(
                [str(exe)], text=True, capture_output=True, timeout=12)
            self.assertEqual(result.returncode, 0, result.stderr +
                             f"RTC case {result.returncode}")


if __name__ == "__main__":
    unittest.main()
