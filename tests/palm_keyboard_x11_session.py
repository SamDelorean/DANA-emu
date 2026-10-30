#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Own a temporary local Xwayland test display; run the SAME Dana executable.
No emulator copy, no TCP listener, no changes to the user's display settings.
"""
from pathlib import Path
import os,secrets,subprocess,tempfile,time,sys

def main():
 root=Path(__file__).resolve().parents[1]
 evidence=root/"local-evidence/runtime-compare/keyboard-20261030"
 evidence.mkdir(parents=True,exist_ok=True)
 number=next(n for n in range(55,70)if not Path(f"/tmp/.X11-unix/X{n}").exists())
 display=f":{number}"
 with tempfile.TemporaryDirectory(prefix="x11-session-",dir=evidence)as tmp:
  auth=Path(tmp)/"Xauthority";auth.touch(mode=0o600)
  result=subprocess.run(["xauth","-f",str(auth),"add",display,".",secrets.token_hex(16)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  assert result.returncode==0,"Cannot create private test display authorization"
  env=os.environ.copy()
  env.update(XDG_RUNTIME_DIR=f"/run/user/{os.getuid()}",WAYLAND_DISPLAY="wayland-0",TMPDIR=tmp)
  with(evidence/"test-xwayland.log").open("w")as log:
   # Xserver -displayfd is the standard unprivileged compositor startup
   # protocol. Keep its notification pipe scoped to this test session.
   ready_read,ready_write=os.pipe()
   server=subprocess.Popen(["/usr/bin/Xwayland",display,"-geometry","1120x320",
    "-displayfd",str(ready_write),"-noreset","-nolisten","tcp","-auth",str(auth)],env=env,pass_fds=(ready_write,),stdout=log,stderr=subprocess.STDOUT)
   os.close(ready_write)
   try:
    deadline=time.monotonic()+10
    while not Path(f"/tmp/.X11-unix/X{number}").exists():
     if server.poll()is not None:raise RuntimeError("Temporary Xwayland failed; see private test-xwayland.log")
     if time.monotonic()>deadline:raise TimeoutError("Temporary Xwayland startup")
     time.sleep(.05)
    client=os.environ.copy()
    client.update(DANA_TEST_DISPLAY=display,DANA_TEST_XAUTHORITY=str(auth))
    run=subprocess.run([sys.executable,"-u",str(root/"tests/palm_uk15_keyboard_sdl.py")]+sys.argv[1:],env=client,timeout=65)
    return run.returncode
   finally:
    os.close(ready_read)
    if server.poll()is None:
     server.terminate()
     try:server.wait(timeout=3)
     except subprocess.TimeoutExpired:server.kill();server.wait(timeout=3)
if __name__=="__main__":raise SystemExit(main())
