#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Native host input campaign on T's existing Xwayland display.
XTest produces host keyboard events. The Lua observer NEVER sets MAME inputs,
guest RAM, characters, Palm events or CPU registers. Restores previous focus.
"""
from pathlib import Path
import ctypes as C, ctypes.util, subprocess, os, time, tempfile, shutil, json, re
import argparse
from PIL import Image

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--installed",action="store_true")
 args=parser.parse_args()
 root=Path(__file__).resolve().parents[1]
 case=root/"local-evidence/runtime-compare/keyboard-20261030"/("sdl-installed"if args.installed else "sdl-candidate")
 case.mkdir(exist_ok=True,parents=True)
 for name in ["ready","stop","sdl-result.json","phrase.bin","dedicated.bin","menu.bin","command.bin","after-menu.bin","guest-menu.bin"]:
  (case/name).unlink(missing_ok=True)
 servers=subprocess.run(["ps","-eo","args"],capture_output=True,text=True,check=True).stdout.splitlines()
 server=next(l for l in servers if l.startswith("/usr/bin/Xwayland "))
 words=server.split();display=os.environ.get("DANA_TEST_DISPLAY",words[1]);auth=os.environ.get("DANA_TEST_XAUTHORITY",words[words.index("-auth")+1])
 env=os.environ.copy()
 env.update(DISPLAY=display,XAUTHORITY=auth,SDL_VIDEODRIVER="x11",DANA_KEYBOARD_STATE=os.environ.get("DANA_KEYBOARD_STATE",str(root/"local-evidence/runtime-compare/calendar-host/keyboard-application/alphaword-clean.sta")),SDL_AUDIODRIVER="dummy",LIBGL_ALWAYS_SOFTWARE="1",DANA_LCD_DUMP_DIR=str(case))
 # Xauthority is supplied as a path to Xlib; its contents are never read.
 os.environ.update(DISPLAY=display,XAUTHORITY=auth)
 x=C.CDLL(ctypes.util.find_library("X11"));xt=C.CDLL(ctypes.util.find_library("Xtst"))
 ptr=C.c_void_p;ulong=C.c_ulong;uint=C.c_uint
 def bind(lib,name,args,result):
  f=getattr(lib,name);f.argtypes=args;f.restype=result;return f
 open_display=bind(x,"XOpenDisplay",[C.c_char_p],ptr)
 close_display=bind(x,"XCloseDisplay",[ptr],C.c_int)
 root_window=bind(x,"XDefaultRootWindow",[ptr],ulong)
 query=bind(x,"XQueryTree",[ptr,ulong,C.POINTER(ulong),C.POINTER(ulong),C.POINTER(C.POINTER(ulong)),C.POINTER(uint)],C.c_int)
 atom=bind(x,"XInternAtom",[ptr,C.c_char_p,C.c_int],ulong)
 prop=bind(x,"XGetWindowProperty",[ptr,ulong,ulong,C.c_long,C.c_long,C.c_int,ulong,C.POINTER(ulong),C.POINTER(C.c_int),C.POINTER(ulong),C.POINTER(ulong),C.POINTER(C.POINTER(C.c_ubyte))],C.c_int)
 free=bind(x,"XFree",[ptr],C.c_int)
 getfocus=bind(x,"XGetInputFocus",[ptr,C.POINTER(ulong),C.POINTER(C.c_int)],C.c_int)
 setfocus=bind(x,"XSetInputFocus",[ptr,ulong,C.c_int,ulong],C.c_int)
 raise_window=bind(x,"XRaiseWindow",[ptr,ulong],C.c_int)
 sync=bind(x,"XSync",[ptr,C.c_int],C.c_int)
 keysym=bind(x,"XStringToKeysym",[C.c_char_p],ulong)
 keycode=bind(x,"XKeysymToKeycode",[ptr,ulong],C.c_ubyte)
 event=bind(xt,"XTestFakeKeyEvent",[ptr,uint,C.c_int,ulong],C.c_int)
 d=open_display(display.encode());assert d,"Cannot open authorized Xwayland display"
 old=ulong();revert=C.c_int();getfocus(d,C.byref(old),C.byref(revert))
 before_snapshots={str(p)for p in(case/"snapshots").glob("**/*.png")}
 pid_atom=atom(d,b"_NET_WM_PID",0)
 def owner(w):
  actual=ulong();fmt=C.c_int();count=ulong();after=ulong();data=C.POINTER(C.c_ubyte)()
  prop(d,w,pid_atom,0,1,0,0,C.byref(actual),C.byref(fmt),C.byref(count),C.byref(after),C.byref(data))
  value=C.cast(data,C.POINTER(ulong))[0]if count.value and fmt.value==32 else 0
  if data:free(data)
  return value
 def windows(w):
  rr=ulong();parent=ulong();children=C.POINTER(ulong)();count=uint()
  if not query(d,w,C.byref(rr),C.byref(parent),C.byref(children),C.byref(count)):return []
  result=[children[i]for i in range(count.value)]
  if children:free(children)
  return result
 def wait_file(name,limit=15):
  end=time.monotonic()+limit
  while time.monotonic()<end:
   if(case/name).exists():return
   if process.poll()is not None:raise RuntimeError("MAME exited before "+name)
   time.sleep(.05)
  raise TimeoutError(name)
 def press(name,down):
  code=keycode(d,keysym(name.encode()));assert code,"Unmapped host keysym "+name
  event(d,code,int(down),0);sync(d,0)
 def stroke(name):
  press(name,True);time.sleep(.045);press(name,False);time.sleep(.065)
 binary=root/("runtime/diag/bin/dana-diag"if args.installed else "runtime/diag/source/danadiagd")
 state=Path(env["DANA_KEYBOARD_STATE"])
 assert state.exists()
 process=None
 try:
  with tempfile.TemporaryDirectory(prefix=".keyboard-sdl-",dir=root/"runtime/diag/work")as cfg,(case/"run.out").open("w")as log:
   for name in ["asmdana.cfg","default.cfg"]:shutil.copy2(root/"config/palm-uk15"/name,Path(cfg)/name)
   command=[str(binary),"asmdana","-rom",str(root/"runtime/diag/work/uk15_qualify_20261025/UK15_private.raw"),"-cfg_directory",cfg,
    "-window","-nomaximize","-video","opengl","-resolution","1120x320","-aspect","7:2","-throttle","-skip_gameinfo","-nowriteconfig","-ui_active",
    "-lightgun","-lightgun_device","lightgun","-lightgunprovider","sdl","-nomouse","-seconds_to_run","240","-snapshot_directory",str(case/"snapshots"),"-autoboot_script",str(root/"tests/palm_uk15_keyboard_sdl.lua"),"-autoboot_delay","0","-verbose","-log","-oslog"]
   process=subprocess.Popen(command,cwd=root/"runtime/diag",env=env,stdout=log,stderr=subprocess.STDOUT)
   wait_file("ready")
   candidates=windows(root_window(d))
   found=None
   for _ in range(3):
    found=next((w for w in candidates if owner(w)==process.pid),None)
    if found:break
    candidates=[child for w in candidates for child in windows(w)]
   assert found,"No window owned by candidate MAME process"
   raise_window(d,found);setfocus(d,found,1,0);sync(d,0);time.sleep(.2)
   focused=ulong();rv=C.c_int();getfocus(d,C.byref(focused),C.byref(rv));print("FOCUS",hex(found),hex(focused.value),flush=True)
   for name in ["h","o","s","t","space"]:stroke(name)
   press("Shift_L",True);stroke("a");press("Shift_L",False)
   for name in ["b","1","period"]:stroke(name)
   press("Shift_R",True);stroke("slash");press("Shift_R",False)
   (case/"capture-phrase").touch();wait_file("phrase.bin")
   # Command remains accessible even when the desktop reserves Super.
   press("Control_R",True);stroke("a");press("Control_R",False)
   (case/"capture-command").touch();wait_file("command.bin")
   # Reserved guest keys must reach ST without opening MAME's menus/reset.
   for name in ["Tab","F3","F5","F7","F8","Escape"]:stroke(name)
   stroke("F12")
   time.sleep(.3)
   snapshots=[p for p in(case/"snapshots").glob("**/*.png")if str(p)not in before_snapshots];assert snapshots,"F12 must retain MAME screenshot"
   stroke("Alt_R");time.sleep(.25)
   (case/"capture-dedicated").touch();wait_file("dedicated.bin")
   # MAME menu remains available using the profile's configurable chord.
   press("Control_L",True);press("Alt_L",True);stroke("Tab");press("Alt_L",False);press("Control_L",False)
   time.sleep(.2);(case/"capture-menu").touch();wait_file("menu.bin");stroke("Escape");stroke("a");stroke("End")
   stroke("Prior");(case/"capture-guest-menu").touch();wait_file("guest-menu.bin");stroke("Escape")
   (case/"capture-after-menu").touch();wait_file("after-menu.bin")
   (case/"stop").touch();process.wait(timeout=15);assert process.returncode==0
  result=json.loads((case/"sdl-result.json").read_text())
  print(json.dumps(result,indent=2));print("F12_SNAPSHOTS",len(snapshots))
  assert result["ui_active"]and result["menu_frames"]>0
  required={43,13,30,5,11,19,83,98,110}
  assert required.issubset(result["codes"]),str(required-set(result["codes"]))
  text=(case/"run.out").read_text()
  assert "[LUA ERROR]"not in text and "DANA_PHYSICAL_BLOCKED"not in text
  for name in ["phrase","command","dedicated","menu","after-menu","guest-menu"]:Image.frombytes("1",(560,160),(case/(name+".bin")).read_bytes()).save(case/(name+".png"))
  print("SDL_HOST_TO_ORIGINAL_PALM_PASS")
 finally:
  if process is not None and process.poll()is None:
   (case/"stop").touch()
   try:process.wait(timeout=3)
   except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  if old.value>1:setfocus(d,old.value,revert.value,0);sync(d,0)
  close_display(d)
if __name__=="__main__":main()
