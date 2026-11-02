#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Use the existing GNOME headless backend for an isolated SDL qualification.
No installation, global display changes, emulator copy or guest injection.
The existing Xwayland/XTest test still drives the actual MAME window.
"""
import argparse,os,re,shutil,signal,subprocess,tempfile,time
from pathlib import Path


def cleanup(runtime,leader):
 # Only terminate services inheriting THIS private runtime, never a user session.
 expected=("XDG_RUNTIME_DIR="+str(runtime)).encode()
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
  try:
   if proc.stat().st_uid==os.getuid() and expected in (proc/'environ').read_bytes().split(b'\0'):
    os.kill(int(proc.name),signal.SIGTERM)
  except (OSError,ProcessLookupError):pass
 if leader is not None:
  try:os.killpg(leader.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:leader.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(leader.pid,signal.SIGKILL);leader.wait(timeout=5)
 # Private document/GVFS portals can leave FUSE mounts after their bus exits.
 for line in Path('/proc/self/mountinfo').read_text().splitlines():
  point=line.split()[4]
  if point.startswith(str(runtime)+'/') and 'fuse' in line.split(' - ',1)[1]:
   subprocess.run(['fusermount3','-uz',point],check=True,stdout=subprocess.DEVNULL)

def main():
 p=argparse.ArgumentParser();p.add_argument('--prefix',required=True)
 p.add_argument('--installed',action='store_true');p.add_argument('--sdl-only',action='store_true');p.add_argument('--state',type=Path)
 a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.prefix)
 root=Path(__file__).resolve().parents[1]
 assert shutil.which('gnome-shell')and shutil.which('dbus-run-session'),'Existing GNOME headless backend required'
 if a.sdl_only:assert a.state and a.state.is_file(),'Supply a save-state produced by the binary under test'
 dest=root/'local-evidence/runtime-compare/keyboard-20261030'/(a.prefix+'-display');dest.mkdir(parents=True,exist_ok=False)
 for n in ['config','cache','data']:(dest/n).mkdir(mode=0o700)
 # AF_UNIX paths are limited to 108 bytes. Keep the runtime socket path short.
 with tempfile.TemporaryDirectory(prefix='h2-wl-',dir=root/'runtime/diag/work')as runtime:
  os.chmod(runtime,0o700);assert len(runtime+'/h2')<108
  env=os.environ.copy();env.update(XDG_RUNTIME_DIR=runtime,WAYLAND_DISPLAY='h2',XDG_SESSION_TYPE='wayland',LIBGL_ALWAYS_SOFTWARE='1',GIO_USE_VFS='local',GVFS_DISABLE_FUSE='1')
  for n in ['config','cache','data']:env['XDG_'+n.upper()+'_HOME']=str(dest/n)
  if a.state:env['DANA_KEYBOARD_STATE']=str(a.state.resolve())
  with(dest/'compositor.log').open('w')as log:
   server=subprocess.Popen(['dbus-run-session','--','gnome-shell','--wayland','--headless','--virtual-monitor=1120x320','--wayland-display=h2'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    deadline=time.monotonic()+25
    while not Path(runtime,'h2').exists():
     if server.poll()is not None:raise RuntimeError('Private compositor failed; inspect '+str(dest/'compositor.log'))
     if time.monotonic()>deadline:raise TimeoutError('Private compositor startup')
     time.sleep(.2)
    if a.sdl_only:command=['python3','-u',str(root/'tests/palm_keyboard_x11_session.py')]+(['--installed']if a.installed else[])
    else:command=['python3','-u',str(root/'tests/run_keyboard_campaign.py'),'--prefix',a.prefix]+([]if a.installed else['--candidate'])
    result=subprocess.run(command,cwd=root,env=env,timeout=90 if a.sdl_only else 800)
    if result.returncode:raise SystemExit(result.returncode)
   finally:
    cleanup(runtime,server)
 print('PRIVATE_COMPOSITOR_CLEANUP_PASS')
if __name__=='__main__':main()
