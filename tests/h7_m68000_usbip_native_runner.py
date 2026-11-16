#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""One original MAME Dana CPU + real ISP1161 + DUSB + USB/IP user-space transaction.

The guest program is diagnostic firmware, not original Palm UK1.5/OS3K.
All device replies/descriptors are written by actual guest M68000 MMIO.
"""
import hashlib, json, os, pathlib, shutil, signal, socket, struct, subprocess, sys, time
ROOT=pathlib.Path('/home/spc/Projects/alphasmart/DANA-emu')
BASE=pathlib.Path(sys.argv[1])
BIN=ROOT/'runtime/diag/bin/dana-diag'
KNOWN='73550d0fc28c3189038e39fad2b5a4321dab59da8cfc416317fad18b875f4e41'
PORT_DUSB=39171
PORT_USBIP=39172

def exact(sock,n):
 out=bytearray()
 while len(out)<n:
  data=sock.recv(n-len(out))
  if not data: raise RuntimeError('USB/IP device disconnected')
  out.extend(data)
 return bytes(out)

def probe_usbip():
 with socket.create_connection(('127.0.0.1',PORT_USBIP),timeout=5) as sock:
  sock.settimeout(8)
  sock.sendall(struct.pack('!HHI',0x0111,0x8005,0))
  response=exact(sock,328)
  assert response[:12]==struct.pack('!HHII',0x0111,0x0005,0,1)
  assert response[312:316] == bytes.fromhex('12345678')
 with socket.create_connection(('127.0.0.1',PORT_USBIP),timeout=5) as sock:
  sock.settimeout(15)
  sock.sendall(struct.pack('!HHI',0x0111,0x8003,0)+b'1-1'.ljust(32,b'\x00'))
  assert exact(sock,8)==struct.pack('!HHI',0x0111,0x0003,0)
  data=exact(sock,312)
  assert data[300:304] == bytes.fromhex('12345678')
  setup=struct.pack('<BBHHH',0x80,6,0x0100,0,8)
  urb=struct.pack('!IIIII',1,77,0x10001,1,0)+struct.pack('!IIIII',0,8,0,0xffffffff,0)+setup
  sock.sendall(urb)
  response=exact(sock,48)
  assert struct.unpack('!II',response[:8]) == (3,77)
  status,actual=struct.unpack('!iI',response[20:28])
  assert (status,actual)==(0,8),(status,actual)
  payload=exact(sock,actual)
  expected=bytes.fromhex('12 01 00 02 ff 00 00 08')
  assert payload==expected,payload.hex()
  return {'usbip_devlist':'PASS','usbip_import':'PASS','native_urb_get_descriptor':'PASS',
   'guest_generated_test_vid':'1234','guest_generated_test_pid':'5678','descriptor_first8':payload.hex(),
   'operating_system_enumeration':'NOT_ACCREDITED','original_palm_uk15':'NOT_THIS_TEST'}

def main():
 assert hashlib.sha256(BIN.read_bytes()).hexdigest()==KNOWN
 assert not BASE.exists()
 BASE.mkdir(parents=True)
 for p in (PORT_DUSB,PORT_USBIP):
  with socket.socket() as s:s.bind(('127.0.0.1',p))
 cfg=BASE/'cfg';cfg.mkdir()
 for name in ('asmdana.cfg','default.cfg'):shutil.copy2(ROOT/'config/palm-uk15'/name,cfg/name)
 guest=BASE/'h7-m68000-diagnostic.dana'
 sys.path.insert(0,str(ROOT/'tests'))
 sys.path.insert(0,str(BASE.parent/'guest_source'))
 from h7_m68000_descriptor_fixture import fixture,DEVICE,CONFIG
 guest.write_bytes(fixture())
 (BASE/'computer.usb').write_text(f'socket.127.0.0.1:{PORT_DUSB}\n')
 observer=BASE/'observe.lua'
 observer.write_text('''local m=manager.machine
local cpu=m.devices[":maincpu"]
local b=cpu.spaces.program
local frame=0
local last=-1
emu.register_frame_done(function()
 frame=frame+1
 local marker=b:read_u16(0x20000)
 local phase=b:read_u16(0x20002)
 if phase~=last then
   local f=assert(io.open(os.getenv("H7_PROGRESS_PATH"),"w"))
   f:write(string.format('{"frame":%d,"phase":%d,"marker":%d,"pc":%d}',frame,phase,marker,cpu.state.CURPC.value));f:close()
   last=phase
 end
 if marker==0xa55a or marker==0xdead or frame>1200 then m:exit() end
end)
''')
 bcmd=[sys.executable,str(ROOT/'tools/h7_usbip_bridge.py'),'--dusb-port',str(PORT_DUSB),'-'+'-usbip-port',str(PORT_USBIP),'--timeout','120']
 b_env=os.environ.copy();b_env['PYTHONPATH']=str(ROOT/'tests')+os.pathsep+b_env.get('PYTHONPATH','')
 m_env=os.environ.copy();m_env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',H7_PROGRESS_PATH=str(BASE/'progress_guest.json'))
 mcmd=[str(BIN),'asmdana','-quickload',str(guest),'-usbcomputer',str(BASE/'computer.usb'),
   '-cfg_directory',str(cfg),'-nvram_directory',str(BASE/'nvram'),'-state_directory',str(BASE/'states'),
   '-video','none','-sound','none','-skip_gameinfo','-nowriteconfig','-throttle','-autoboot_script',str(observer),'-autoboot_delay','0','-oslog','-log']
 b_log=open(BASE/'bridge.log','w');m_log=open(BASE/'mame.log','w')
 b_proc=None;m_proc=None
 report={'status':'BLOCKED','binary_sha256':KNOWN,'host': 'USB/IP user-mode localhost',
   'guest': 'new M68000 diagnostic firmware from qualified USBCode',
   'original_palm_uk15':'NOT_THIS_TEST','usb_host_os_enumeration':'NOT_ACCREDITED'}
 try:
  b_proc=subprocess.Popen(bcmd,cwd=ROOT,stdout=b_log,stderr=subprocess.STDOUT,env=b_env,start_new_session=True)
  end=time.monotonic()+6
  while time.monotonic()<end:
   if b_proc.poll() is not None:raise RuntimeError('Bridge exited before MAME')
   if 'DUSB_IMAGE_TEXT' in (BASE/'bridge.log').read_text():break
   time.sleep(.05)
  else:raise RuntimeError('No DUSB bridge listener')
  m_proc=subprocess.Popen(mcmd,cwd=ROOT/'runtime/diag',stdout=m_log,stderr=subprocess.STDOUT,env=m_env,start_new_session=True)
  end=time.monotonic()+80
  while time.monotonic()<end:
   if m_proc.poll() is not None and 'GUEST_DESCRIPTOR_OBSERVED' not in (BASE/'bridge.log').read_text():
    raise RuntimeError('MAME exited before device descriptors from guest')
   if 'GUEST_DESCRIPTOR_OBSERVED' in (BASE/'bridge.log').read_text():break
   time.sleep(.1)
  else:raise RuntimeError('No guest Device+Config descriptors from real CPU')
  report.update(probe_usbip())
  report['status']='M68000_USBIP_END_TO_END_PASS'
 except Exception as e:
  report['reason']=str(e)
 finally:
  if m_proc and m_proc.poll() is None:
   try:os.killpg(m_proc.pid,signal.SIGTERM);m_proc.wait(timeout=5)
   except Exception:os.killpg(m_proc.pid,signal.SIGKILL)
  if b_proc and b_proc.poll() is None:
   try:os.killpg(b_proc.pid,signal.SIGTERM);b_proc.wait(timeout=5)
   except Exception:os.killpg(b_proc.pid,signal.SIGKILL)
  b_log.close();m_log.close()
  report['mame_rc']=m_proc.returncode if m_proc else 'NOT_STARTED'
  report['bridge_rc']=b_proc.returncode if b_proc else 'NOT_STARTED'
  if (BASE/'progress_guest.json').exists():
   try:report['guest_progress']=json.loads((BASE/'progress_guest.json').read_text())
   except Exception:pass
  report['bridge_tail']=(BASE/'bridge.log').read_text(errors='replace')[-2000:]
  report['guest_log_tail']=(BASE/'mame.log').read_text(errors='replace')[-1200:]
  (BASE/'result.json').write_text(json.dumps(report,indent=2)+'\n')
  print('H7_NATIVE_CPU_USBIP_RESULT='+json.dumps(report),flush=True)
 return 0 if report['status']=='M68000_USBIP_END_TO_END_PASS' else 2

if __name__=='__main__':raise SystemExit(main())
