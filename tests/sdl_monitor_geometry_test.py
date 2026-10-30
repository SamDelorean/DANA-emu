#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""The existing SDL monitor must yield finite UI coordinates when disconnected."""
from pathlib import Path
import subprocess,tempfile,unittest

class MonitorGeometryTest(unittest.TestCase):
 def test_real_monitor_aspect(self):
  root=Path(__file__).resolve().parents[1]
  s=(root/"src/osd/modules/monitor/monitor_module.h").read_text()
  start=s.index("float pixel_aspect() const");begin=s.index("{",start);depth=1;i=begin+1
  while depth:depth+=(s[i]=="{")-(s[i]=="}");i+=1
  method=s[start:i]
  cpp=r"""
#include <cmath>
struct Rect {int w,h;int width()const{return w;}int height()const{return h;}};
struct Monitor {float m_aspect;Rect m_pos_size;
"""+method+r"""
};
int main(){
 Monitor a{16.0f/9.0f,{1920,1080}};
 if(std::abs(a.pixel_aspect()-1.0f)>1e-6)return 1;
 Monitor b{4.0f/3.0f,{1280,720}};
 if(std::abs(b.pixel_aspect()-0.75f)>1e-6)return 2;
 for(auto r:{Rect{0,0},Rect{1920,0},Rect{0,1080},Rect{-1,1080}}){
  Monitor m{NAN,r};
  if(!std::isfinite(m.pixel_aspect())||m.pixel_aspect()!=1.0f)return 3;
 }
 return 0;
}
"""
  cpp=cpp.replace("#include <cmath>","#include <cmath>\n#include <initializer_list>")
  with tempfile.TemporaryDirectory()as tmp:
   p=Path(tmp)/"monitor.cpp";exe=Path(tmp)/"monitor";p.write_text(cpp)
   build=subprocess.run(["clang++-21","-std=c++20","-Wall","-Wextra","-Werror",str(p),"-o",str(exe)],capture_output=True,text=True,timeout=60)
   self.assertEqual(build.returncode,0,build.stderr)
   run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
   self.assertEqual(run.returncode,0,f"monitor case {run.returncode}")
if __name__=="__main__":unittest.main()
