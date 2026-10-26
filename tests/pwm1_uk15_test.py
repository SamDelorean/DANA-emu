#!/usr/bin/env python3
"""Compile and execute real PWMC1 handlers against the original UK1.5 operation."""
from pathlib import Path
import subprocess
import tempfile
import unittest

DRIVER = Path(__file__).resolve().parents[1] / "src/mame/skeleton/alphasdana.cpp"

def implementation(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if not depth:
            return source[start:pos + 1].replace("alphasdana_state::", "Mock::")
    raise ValueError(signature)

class PWM1OriginalROMTest(unittest.TestCase):
    def test_uk15_rmw_control(self):
        source = DRIVER.read_text()
        for needed in (
            "m_pwm1_control=0x0020;",
            "save_item(NAME(m_pwm1_control));",
            "m_boot_memory[1](0xfffff500,0xfffff501).rw("
            "FUNC(alphasdana_state::pwm1_control_r),"
            "FUNC(alphasdana_state::pwm1_control_w));",
        ):
            self.assertIn(needed, source)
        read = implementation(source, "u16 alphasdana_state::pwm1_control_r()")
        write = implementation(source, "void alphasdana_state::pwm1_control_w(")
        code = """
#include <cstdint>
using u16=std::uint16_t; using u32=std::uint32_t; using offs_t=unsigned;
struct Mock {
    u16 m_pwm1_control=0x0020;
    bool blocked=false;
    void logerror(const char*,...){}
    void physical_block(const char*,u32,u16){blocked=true;}
    u16 pwm1_control_r();
    void pwm1_control_w(offs_t,u16,u16);
};
""" + read + "\n" + write + """
int main(){
    Mock d;
    if(d.pwm1_control_r()!=0x0020) return 1;
    const u16 before=d.pwm1_control_r();
    d.pwm1_control_w(0,before & 0xffef,0xffff);
    if(d.blocked||d.pwm1_control_r()!=0x0020) return 2;
    d.pwm1_control_w(0,0x270c,0xffff);
    if(d.blocked||d.m_pwm1_control!=0x272c||d.pwm1_control_r()!=0x2720) return 3;
    d.pwm1_control_w(0,0x0003,0x00ff);
    if(d.blocked||d.pwm1_control_r()!=0x2723) return 4;
    d.pwm1_control_w(0,0x0010,0x00ff);
    if(!d.blocked||d.pwm1_control_r()!=0x2723) return 5;
    d.blocked=false;
    d.pwm1_control_w(0,0x0040,0x00ff);
    if(!d.blocked||d.pwm1_control_r()!=0x2723) return 6;
    d.blocked=false;
    d.pwm1_control_w(0,0x0080,0x00ff);
    if(!d.blocked||d.pwm1_control_r()!=0x2723) return 7;
    d.blocked=false;
    d.pwm1_control_w(0,0x0000,0x00ff);
    if(d.blocked||d.pwm1_control_r()!=0x2720) return 8;
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/"pwm1.cpp"
            exe = Path(tmp)/"pwm1"
            file.write_text(code)
            build = subprocess.run(
                ["clang++-21","-std=c++20","-Wall","-Wextra","-Werror",
                 str(file),"-o",str(exe)], capture_output=True, text=True, timeout=50)
            self.assertEqual(build.returncode,0,build.stderr)
            run = subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
            self.assertEqual(run.returncode,0,f"production handler case {run.returncode}")

if __name__ == "__main__":
    unittest.main()
