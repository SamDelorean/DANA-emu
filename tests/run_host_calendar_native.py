#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Run authentic UK1.5 with qualified native PEN input and read-only probes.
Defaults to the installed emulator through the official launcher. --candidate
qualifies the existing build artifact with the same ROM/config/input arguments.
Private ROM, logs, WAV and framebuffer files remain under local-evidence.
"""
import argparse, hashlib, os, shutil, subprocess, tempfile, wave
from pathlib import Path
from array import array

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--candidate",action="store_true")
 p.add_argument("--rtc",default="")
 p.add_argument("--case",default="installed-host")
 p.add_argument("--script",default="tests/palm_uk15_host_calendar.lua")
 args=p.parse_args()
 root=Path(__file__).resolve().parents[1]
 evidence=root/"local-evidence/runtime-compare/calendar-host"
 case=evidence/args.case
 case.mkdir(parents=True,exist_ok=True)
 env=os.environ.copy()
 env.update(SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy",DANA_REPO_ROOT=str(root),
  DANA_LCD_DUMP_DIR=str(case),DANA_TRACE_FILE=str(case/"trace.txt"),
  DANA_CALENDAR_PROBE=str(case/"calendar.txt"))
 extra=["-video","none","-nothrottle","-skip_gameinfo","-nowriteconfig",
  "-autoboot_script",str(root/args.script),"-autoboot_delay","0","-log","-oslog",
  "-samplerate","48000","-wavwrite",str(case/"audio.wav")]
 if args.rtc:extra+=["-rtc",args.rtc]
 binary=root/("runtime/diag/source/danadiagd" if args.candidate else "runtime/diag/bin/dana-diag")
 with tempfile.TemporaryDirectory(prefix=".calendar-",dir=root/"runtime/diag/work") as cfg:
  if args.candidate:
   shutil.copy2(root/"config/palm-uk15/asmdana.cfg",Path(cfg)/"asmdana.cfg")
   shutil.copy2(root/"config/palm-uk15/default.cfg",Path(cfg)/"default.cfg")
   command=[str(binary),"asmdana","-rom",str(root/"runtime/diag/work/uk15_qualify_20261025/UK15_private.raw"),
    "-cfg_directory",cfg,"-window","-nomaximize","-lightgun","-lightgun_device","lightgun",
    "-lightgunprovider","sdl","-nomouse"]+extra
  else:command=[str(root/"tools/run-palm-uk15.sh")]+extra
  run=subprocess.run(command,cwd=root/"runtime/diag",env=env,stdout=subprocess.PIPE,
   stderr=subprocess.STDOUT,text=True,timeout=120)
 (case/"run.out").write_text(run.stdout)
 shutil.copy2(root/"runtime/diag/error.log",case/"run.log")
 print("CASE",args.case,"RC",run.returncode,"BINARY_SHA256",hashlib.sha256(binary.read_bytes()).hexdigest())
 for line in run.stdout.splitlines():
  if any(t in line for t in ("HOST_CALENDAR","PHYSICAL_BLOCK","PHYSICAL_CPU","Error")):print(line)
 print((case/"calendar.txt").read_text())
 from PIL import Image
 for frame in [1800,3510,3900,4400,4800]:
  fb=case/f"calib_{frame:04d}.bin"
  if fb.exists():Image.frombytes("1",(560,160),fb.read_bytes()).save(case/f"screen-{frame}.png")
 with wave.open(str(case/"audio.wav")) as wav:
  samples=array("h",wav.readframes(wav.getnframes()))
  print("AUDIO",wav.getnchannels(),wav.getframerate(),len(samples),
   "PEAK",max(map(abs,samples),default=0),"NONZERO",sum(v!=0 for v in samples))
 if run.returncode or any(t in run.stdout for t in ("DANA_PHYSICAL_BLOCKED",
  "Error in Lua", "Lua error", "[LUA ERROR]", "must survive", "must persist")):raise SystemExit(1)

if __name__=="__main__":main()
