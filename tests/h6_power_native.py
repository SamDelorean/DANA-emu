#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""H6 passive monitor: CPU-owned GPIO/USB/clock journal, no radio peer.

Original cleanup mode consumes the private, unchanged NetIF on T only.
Generated firmware containing private bytes must never be published.
"""
import argparse,hashlib,json,os,re,shutil,struct,subprocess,sys
from pathlib import Path
from d7_5_native import Code,ENTRY,MARKER
from nor_native import check,finish,fixture,wait,rd
from h2_native import movel,bytecheck,timer,vector,enter,leave
from h6_storage_native import set_port

PM=0xfffff440
def payload(mode,private_code=None):
 c=Code();c.w(0x46fc,0x2700);c.move_w(0,0xfffffb0a)
 for i in range(64):c.move_w(0,MARKER+2*i)
 c.move_b(1,PM);c.move_b(1,PM+3);c.move_b(0,PM+1);bytecheck(c,PM+1,0,1)
 c.move_b(1,PM+1);bytecheck(c,PM+1,1,1)
 # The USB silicon ID belongs to the existing ISP1161, never a radio ACK.
 c.move_w(0x27,0x1f000002);check(c,0x1f000000,0x6123)
 if mode=='bound':
  for i in range(600):c.move_b(i&1,PM+1)
 elif mode=='save':
  c.move_w(0x5a5a,MARKER);wait(c,2048)
  c.move_w(0x27,0x1f000002);check(c,0x1f000000,0x6123)
 elif mode=='sleep':
  vector(c,6,'wake');c.move_w(0xfffd,0xfffff306)
  timer(c,0,compare=8208,irq=True,free=True);c.move_w(0x249b,0xfffff200);c.w(0x4e72,0x2000)
  bytecheck(c,PM+1,1,1);c.move_w(3,MARKER+2);c.jump('after_wake')
  enter(c,'wake');rd(c,0xfffff60a);c.move_w(0,0xfffff60a);c.move_w(0,0xfffff600);leave(c);c.label('after_wake')
 if mode=='original-cleanup':
  # Genuine original routine, with a valid guest-RAM context in an already
  # detached state. No Palm trap/USB reply stub and no ROM or PRC modification.
  movel(c,0x30100,0x3005c);movel(c,0x30200,0x30064)
  movel(c,0x1ff,0x3010a);c.move_w(0,0x3010e);movel(c,0,0x3012a);c.move_b(1,0x30200)
  c.w(0x4879);c.l(0x30000);c.w(0x4eb9);c.l(0x8000+0x3394);c.w(0x588f);c.expect(0)
  bytecheck(c,0x30200,0);check(c,0x3010e,0);bytecheck(c,PM+1,0,1)
 else:c.move_b(0,PM+1)
 bytecheck(c,PM+1,0,1)
 rd(c,0xfffff310);c.record(MARKER+0x20);rd(c,0xfffff312);c.record(MARKER+0x22)
 check(c,0xfffff200,0x2493 if mode=='sleep'else 0x24b3,0xfff3)
 # Deterministic register/IRQ/pad journal is compared with monitoring disabled.
 for i,a in enumerate([PM,PM+1,PM+3]):
  c.w(0x1039);c.l(a);c.w(0x0240,255);c.record(MARKER+0x30+2*i)
 c.move_w(4,MARKER+2);body=finish(c)
 if private_code is not None:
  assert len(body)<0x8000-ENTRY;body+=b'\0'*(0x8000-ENTRY-len(body))+private_code
 return body

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--board',type=int,choices=range(4),default=3);p.add_argument('--monitor',type=int,choices=[0,1],default=1);p.add_argument('--mode',choices=['basic','save','sleep','bound','original-cleanup'],default='basic');p.add_argument('--installed',action='store_true');p.add_argument('--network-audit',action='store_true');a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.case)
 root=Path(__file__).resolve().parents[1];e=root/'local-evidence/runtime-compare/h6-20261116';folder=e/a.case;folder.mkdir(parents=True,exist_ok=False);cfg=folder/'cfg';cfg.mkdir()
 for name in ['asmdana.cfg','default.cfg']:shutil.copy2(root/'config/palm-uk15'/name,cfg/name)
 for tag,mask,default,value in [('DANA_STORAGE','3','0',a.board),('H6_MONITOR','1','0',a.monitor)]:set_port(cfg/'asmdana.cfg',tag,mask,default,value)
 private=None;original={}
 if a.mode=='original-cleanup':
  prc=root/'local-evidence/runtime-compare/h6-20261115/package/FUENTES_PRIVADAS_NO_PUBLICAR/WiFi_NetIF_AlphaSmart_Dana.prc';b=prc.read_bytes();assert hashlib.sha256(b).hexdigest()=='6948b018b7926062ab25bfa6d2e142ff62a03f57167d52af403677714cf61726';private=b[190:21136]
  rom=root/'runtime/diag/work/uk15_qualify_20261025/UK15_private.raw';rb=rom.read_bytes();assert hashlib.sha256(rb).hexdigest()=='2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3'
  original=dict(prc_sha256=hashlib.sha256(b).hexdigest(),rom_cleanup_same_bytes=private[0x3394:0x343e]==rb[0x3086d8:0x308782],resource_entry_offset='0x3394',guest_relocation_base='0x8000',originals_unchanged=True)
 body=payload(a.mode,private);seed=folder/'seed.bin';chip='m29w320db'if a.board==1 else'm28w640hcb';seed.write_bytes(fixture('h6-power',body,size=0x400000 if a.board==1 else 0x800000));seed.chmod(0o444);before=hashlib.sha256(seed.read_bytes()).hexdigest()
 lua=r'''local m=manager.machine;local b=m.devices[":maincpu"].spaces.program;local frames=0;local saved=false;local loaded=false;local restored=false
local note=emu.add_machine_post_load_notifier(function()restored=true end)
emu.register_frame_done(function()
 if not note then return end;frames=frames+1;local mark=b:read_u16(0x20000)
 if SAVING and mark==0x5a5a and not saved then saved=true;m:save(FOLDER.."/active.sta")end
 if SAVING and mark==0xa55a and not loaded then loaded=true;m:load(FOLDER.."/active.sta");return end
 if mark==0xdead or(mark==0xa55a and(not SAVING or restored))or frames>1000 then
  local words={};for a=0x20000,0x2007e,2 do words[#words+1]=tostring(b:read_u16(a))end
  local f=assert(io.open(FOLDER.."/cpu.json","w"));f:write(string.format('{"marker":%d,"restored":%s,"words":[%s]}',mark,tostring(restored),table.concat(words,",")));f:close();m:exit()
 end
end)
'''.replace('FOLDER',json.dumps(str(folder))).replace('SAVING','true'if a.mode=='save'else'false');(folder/'observe.lua').write_text(lua)
 binary=root/('runtime/diag/bin/dana-diag'if a.installed else'runtime/diag/source/danadiagd')
 command=[str(binary),'asmdana','-rom',str(seed),'-nor',chip,'-cfg_directory',str(cfg),'-nvram_directory',str(folder/'nvram'),'-state_directory',str(folder/'states'),'-video','none','-sound','none','-nothrottle','-skip_gameinfo','-nowriteconfig','-autoboot_delay','0','-autoboot_script',str(folder/'observe.lua'),'-log','-oslog']
 if a.network_audit:
  assert shutil.which('strace');command=['strace','-f','-qq','-e','trace=network','-o',str(folder/'network.trace'),'--']+command
 env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',TMPDIR=str(folder))
 with(folder/'run.out').open('w')as f:r=subprocess.run(command,cwd=root/'runtime/diag',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120)
 text=(folder/'run.out').read_text();cpu=json.loads((folder/'cpu.json').read_text())if(folder/'cpu.json').exists()else{};events=[l[l.index('DANA_H6 '):]for l in text.splitlines()if'DANA_H6 'in l]
 ok=r.returncode==0 and cpu.get('marker')==0xa55a and before==hashlib.sha256(seed.read_bytes()).hexdigest() and not any(t in text for t in ['LUA ERROR','Error in Lua','DANA_PHYSICAL_BLOCKED'])
 if a.monitor:
  ok=ok and 1<=len(events)<=512 and all('verified_board_rail=NO_VERIFICADO measured_current=NO_VERIFICADO'in l for l in events)
  if a.board==3:ok=ok and any('software_request=ACTIVE_REQUESTED'in l for l in events)and any('software_request=OFF_REQUESTED'in l for l in events)
  else:ok=ok and all('software_request=UNKNOWN'in l for l in events)
 else:ok=ok and not events
 if a.mode=='bound':ok=ok and len(events)==512
 if a.mode=='save':ok=ok and cpu.get('restored') and sum('event=ISP1161_CONTROLLER_WRITE'in l and'software_request=ACTIVE_REQUESTED'in l for l in events)>=3
 network=(folder/'network.trace').read_text()if a.network_audit else''
 if a.network_audit:ok=ok and not re.search(r'AF_INET6?\b',network)
 result=dict(network_audit=a.network_audit,internet_socket_calls=0 if a.network_audit else None,case=a.case,mode=a.mode,board=a.board,monitor=a.monitor,installed=a.installed,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),returncode=r.returncode,cpu=cpu,trace_events=len(events),original_cleanup=original,seed_preserved=True,pass_=bool(ok));(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
 if not ok:print(text[-3000:]);raise SystemExit(1)
if __name__=='__main__':main()
