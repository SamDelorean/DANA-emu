#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Guest-origin 68000 VZ PWM2 / PCR test, same installed Dana emulator.
Original CPU writes MMIO; Lua only observes guest-owned result marker.
"""
import argparse, hashlib, json, os, re, shutil, struct, subprocess, sys
from pathlib import Path
from d7_5_native import Code, ENTRY, MARKER
from nor_native import finish, check

PWM2=0xfffff510
PCR=0xfffff003
IPR=0xfffff312

def build():
 c=Code();c.w(0x46fc,0x2700)
 c.move_w(0,0xfffffb0a)
 for a in range(MARKER,MARKER+32,2):c.move_w(0,a)
 check(c,PWM2,0);check(c,PWM2+2,0);check(c,PWM2+4,0);check(c,PWM2+6,0)
 c.move_b(0x1f,PCR)
 c.w(0x1039);c.l(PCR);c.w(0x0240,0xff);c.expect(0x1f)
 c.move_b(0,PCR)
 c.move_w(0x0010,PWM2+2) # period=16
 c.move_w(0x0008,PWM2+4) # width=8
 c.move_w(0x4010,PWM2) # PWM2 on, IRQ enabled
 c.move_b(0x04,PCR)    # PWM2 selected on PWMO1
 # Poll for actual PWM2 rollover from VZ scheduler (not host MMIO injection).
 loop=c.unique();c.label(loop)
 c.w(0x3039);c.l(IPR);c.w(0x0240,0x2000)
 c.w(0x4a40,0x6706);c.jump('saw_irq')
 c.jump(loop)
 c.label('saw_irq')
 check(c,IPR,0x2000,0x2000)
 # Disable the source before acknowledging: with period=16, another
 # *genuine* rollover may occur between the control read and IPR read.
 c.move_w(0,PWM2)
 c.w(0x3039);c.l(PWM2);c.w(0x0240,0x8000);c.expect(0x8000)
 check(c,IPR,0,0x2000)
 c.move_b(0,PCR)
 check(c,PWM2,0,0x4010)
 return finish(c)

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--installed',action='store_true');a=p.parse_args()
 assert re.fullmatch(r'[A-Za-z0-9_-]+',a.case)
 root=Path(__file__).resolve().parents[1]
 folder=root/'local-evidence/runtime-compare/hw-final-20261117'/a.case
 folder.mkdir(parents=True,exist_ok=False)
 raw=build()
 header=bytearray(64);header[:8]=b'DANARAM1';end=ENTRY+len(raw)
 struct.pack_into('>8I',header,8,ENTRY,ENTRY,len(raw),0x1000,0x400000,0x2000,end,end)
 header[40:60]=hashlib.sha1(raw).digest();struct.pack_into('>I',header,60,1)
 image=folder/'guest.dana';image.write_bytes(header+raw);image.chmod(0o444)
 hash_before=hashlib.sha256(image.read_bytes()).hexdigest()
 cfg=folder/'cfg';cfg.mkdir()
 for name in ['asmdana.cfg','default.cfg']:shutil.copy2(root/'config/palm-uk15'/name,cfg/name)
 lua='''local m=manager.machine
local b=m.devices[":maincpu"].spaces.program
local frame=0
emu.register_frame_done(function()
 frame=frame+1
 local marker=b:read_u16(0x20000)
 if marker==0xa55a or marker==0xdead or frame>180 then
 local f=assert(io.open(FILENAME,"w"))
 f:write(string.format('{"marker":%d,"frame":%d,"guest_d0":%d}',marker,frame,b:read_u16(0x20006)))
 f:close();m:exit()
 end
end)
'''.replace('FILENAME',json.dumps(str(folder/'guest.json')))
 (folder/'observe.lua').write_text(lua)
 binary=root/('runtime/diag/bin/dana-diag' if a.installed else 'runtime/diag/source/danadiagd')
 cmd=[str(binary),'asmdana','-video','none','-nothrottle','-skip_gameinfo','-nowriteconfig','-cfg_directory',str(cfg),'-nvram_directory',str(folder/'nvram'),'-quickload',str(image),'-autoboot_delay','0','-autoboot_script',str(folder/'observe.lua'),'-log']
 env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',TMPDIR=str(folder))
 with (folder/'run.log').open('w') as f:r=subprocess.run(cmd,cwd=root/'runtime/diag',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90)
 observed=json.loads((folder/'guest.json').read_text()) if (folder/'guest.json').exists() else {}
 log=(folder/'run.log').read_text()
 ok=observed.get('marker')==0xa55a and r.returncode==0 and hash_before==hashlib.sha256(image.read_bytes()).hexdigest() and not any(s in log for s in ['LUA ERROR','PHYSICAL_BLOCKED','Fatal error'])
 observed.update(ok=ok,returncode=r.returncode,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
 (folder/'result.json').write_text(json.dumps(observed,indent=2)+'\n')
 print(json.dumps(observed),flush=True)
 if not ok:print(log[-2200:]);sys.exit(1)
if __name__=='__main__':main()
