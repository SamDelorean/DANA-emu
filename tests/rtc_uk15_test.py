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
#include <string>
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;
using offs_t=unsigned;
struct Model {
    static constexpr u32 rtc_time_mask=0x1f3f003fU;
    static constexpr bool rtc_time_valid(u32);
    u32 m_rtc_time=0,m_pending=0;
    u16 m_rtc_day=0,m_rtc_control=0x0080,m_rtc_ien=0,m_rtc_isr=0;
    bool blocked=false;
    const char* error="";
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
 // Original 68000 TST.L FB00 must see a 32-bit clock value, high then low.
 if(d.rtc_time_r(0)!=0 || d.rtc_time_r(1)!=0) return 1;
 d.rtc_time_w(0,0x1834,0xffff); // invalid hour 24
 if(!d.blocked || d.m_rtc_time) return 2;
 d.blocked=false;
 d.rtc_time_w(0,0x1230,0xffff); // 18h 48min
 if(d.blocked || d.rtc_time_r(0)!=0x1230) return 3;
 d.rtc_time_w(1,0x003a,0xffff); // 58sec
 if(d.blocked || d.rtc_time_r(1)!=0x003a) return 4;
 d.rtc_ien_w(0,0x000a,0xffff); // authentic native code
 if(d.blocked || d.m_rtc_ien!=0x000a) return 5;
 d.rtc_control_w(0,0x0080,0xffff);
 if(d.blocked || d.m_rtc_control!=0x80) return 6;
 d.rtc_tick();
 if(d.m_rtc_time!=0x1230003b || d.m_pending!=0) return 7;
 d.rtc_tick();
 if(d.m_rtc_time!=0x12310000 || !(d.m_rtc_isr&0x0002) ||
    !(d.m_pending&0x10)) return 8; // minute IRQ on real VZ bit4
 d.rtc_isr_w(0,0x0002,0xffff);
 if(d.m_pending!=0 || (d.m_rtc_isr&2)) return 9;
 d.rtc_time_w(0,0x173b,0xffff); // 23:59
 d.rtc_time_w(1,0x003b,0xffff); // 59 sec
 d.rtc_tick();
 if(d.m_rtc_time!=0 || d.m_rtc_day!=1 || !(d.m_rtc_isr&8) ||
    !(d.m_pending&0x10)) return 10;
 d.rtc_control_w(0,0x0000,0xffff); // disabled counter
 const u32 now=d.m_rtc_time;
 d.rtc_tick();
 if(d.m_rtc_time!=now || d.m_pending) return 11;
 d.rtc_control_w(0,0x0080,0xffff);
 d.rtc_ien_w(0,0,0xffff);
 if(d.m_pending) return 12;
 // High and low byte lanes remain independent.
 d.rtc_time_w(0,0x0400,0xff00); // hours=4, leave minutes=0
 d.rtc_time_w(0,0x0005,0x00ff); // minutes=5
 if(d.rtc_time_r(0)!=0x0405) return 13;
 // Unsupported subsecond modes are rejected, not pretended.
 d.rtc_ien_w(0,0x0100,0xffff);
 if(!d.blocked || d.m_rtc_ien!=0) return 14;
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
