#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Real 68000 UART/IrDA qualification in the canonical Dana MAME binary.

The Lua observer never writes registers, CPU state or guest RAM. Host bytes
cross MAME bitbanger -> an independent timed peer -> physical UART pins.
"""
import argparse,hashlib,json,os,shutil,socket,subprocess,time
from pathlib import Path
from d7_5_native import Code,ENTRY,MARKER

def rd(c,address,mask=65535):
 c.w(0x3039);c.l(address)
 if mask!=65535:c.w(0x0240,mask)
def check(c,address,value,mask=65535):rd(c,address,mask);c.expect(value)
def delay(c,count=65535):
 c.w(0x3e3c,count);loop=ENTRY+len(c.data);c.w(0x51cf,(loop-(ENTRY+len(c.data)+2))&65535)
def poll(c,address,mask,value):
 c.w(0x3e3c,65535);name=c.unique();c.label(name)
 if address in [0xfffff904,0xfffff914] and mask&0xff00:
  c.w(0x1039);c.l(address);c.w(0x0240,mask>>8);value>>=8
 else:rd(c,address,mask)
 c.w(0x0c40,value,0x6606)
 end=c.unique();c.jump(end)
 c.w(0x51cf,(c.labels[name]-(ENTRY+len(c.data)+2))&65535);c.jump('fail');c.label(end)
def stage(c,value):c.move_w(value,MARKER+2)
def setup(c,n,ir=False,ctl=0xe100,misc=None,baud=0x020b):
 b=0xfffff900+16*n
 c.move_b(0x0f,0xfffff423 if n==0 else 0xfffff43b)
 c.move_w(0,b);c.move_w(baud,b+2);c.move_w(0x0320,b+10)
 c.move_w(0x0800,b+6);c.move_w(misc if misc is not None else (0x00e0 if ir else 0x0040),b+8)
 c.move_w(ctl,b)
 return b
def fixture(mode,n):
 c=Code()
 if mode=='reset':
  rd(c,MARKER);c.w(0x0c40,0x5a5a,0x6606);c.jump('reset_check')
 c.w(0x46fc,0x2700);c.move_w(0xffff,0xfffff304);c.move_w(0xffff,0xfffff306)
 b=0xfffff900+16*n;stage(c,1)
 for off,value in [(0,0),(2,2),(8,0),(10,0)]:check(c,b+off,value)
 if n:check(c,b+12,0x0102)
 check(c,b+6,0,0xe000)
 if mode in ['backend','irda','irtest']:
  b=setup(c,n,mode=='irda',misc=0x1440 if mode=='irtest' else None);stage(c,2)
  if mode=='irtest':c.move_b(0,b+6);poll(c,b+6,0x200,0)
  # CPU waits for independently timed physical RX. Echo only after reading URX.
  for value in b'Dana UART'+bytes([49+n])+b'\x00\x55\xaa\xff':
   if mode=='irtest':c.move_b(value,b+7)
   poll(c,b+4,0x2000,0x2000);rd(c,b+4);c.record(MARKER+8);c.w(0x0240,255);c.expect(value)
   if mode!='irtest':c.w(0x3200);poll(c,b+6,0x2000,0x2000);c.w(0x13c1);c.l(b+7)
  poll(c,b+6,0x400,0);delay(c,20000);stage(c,3)
 elif mode in ['loop','save','saveir']:
  b=setup(c,n,misc=0x1040);stage(c,2)
  for value in [0,0x55,0xaa,0xff]:
   c.move_b(value,b+7);poll(c,b+4,0x2000,0x2000);check(c,b+4,value,0xff)
  # High-byte-only UTX write must not enqueue, nor high-byte URX read pop.
  c.move_b(0x08,b+6);check(c,b+4,0,0x2000)
  c.move_b(0x63,b+7);poll(c,b+4,0x2000,0x2000)
  c.w(0x1039);c.l(b+4);check(c,b+4,0x2063,0x20ff)
  check(c,b+4,0,0x2000)
  # 7-bit, even and odd parity through the actual shifter.
  for ctl in [0xe800,0xec00,0xeb00]:
   stage(c,ctl)
   c.move_w(ctl,b);c.move_b(0xb5,b+7);poll(c,b+4,0x2000,0x2000)
   check(c,b+4,0x35 if not ctl&0x100 else 0xb5,0x7ff)
  # Force parity error on TX, leave receiver parity unchanged.
  c.move_w(0xe900,b);c.move_w(0x3040,b+8);c.move_b(0x55,b+7)
  poll(c,b+4,0x2000,0x2000);check(c,b+4,0x155,0x7ff)
  # Return to 8N1; FIFO capacity and overrun via timed loopback.
  c.move_w(0xe100,b);c.move_w(0x1040,b+8);stage(c,3)
  size=64 if n else 12
  for value in range(size+1):
   c.move_b(value,b+7);poll(c,b+6,0x400,0)
  c.w(0x1039);c.l(b+4);c.w(0x0240,0xe0);c.expect(0xe0)
  for value in range(1,size+1):check(c,b+4,value|(0x800 if value==size else 0),0xfff)
  check(c,b+4,0,0x2000)
  # RX-disable flush; data-old is a timed condition, not always asserted.
  c.move_b(0x75,b+7);poll(c,b+4,0x2000,0x2000);delay(c,65535)
  check(c,b+4,0x3075,0x30ff);check(c,b+4,0,0x3000)
  c.move_b(0x76,b+7);poll(c,b+4,0x2000,0x2000);c.move_w(0xa100,b);check(c,b+4,0,0x2000)
  c.move_w(0xe100,b)
  if mode in ['save','saveir']:
   if mode=='saveir':c.move_w(0x0070,b+8)
   # Slow in-flight frame, then STOP so save occurs during that frame.
   c.move_w(0x0700,b+2);c.move_b(0x39,b+7);c.move_w(0x5a5a,MARKER)
   delay(c);delay(c);poll(c,b+4,0x2000,0x2000);check(c,b+4,0x39,0xff)
  stage(c,4)
 elif mode=='reset':
  b=setup(c,n,misc=0x1040,ctl=0xe108);c.move_b(0x57,b+7);poll(c,b+4,0x2000,0x2000)
  c.move_w(0,4);c.move_w(ENTRY,6);c.move_w(0x5a5a,MARKER);c.w(0x4e72,0x2700)
  c.label('reset_check')
  for off,value in [(0,0),(2,2),(8,0),(10,0)]:check(c,b+off,value)
  check(c,b+4,0,0xff00);check(c,b+6,0,0xe500);check(c,0xfffff312,0,0x1004)
  if n:check(c,b+12,0x0102)
  stage(c,81)
 elif mode=='rts':
  b=setup(c,n,misc=0x10c0);g=0xfffff439 if n else 0xfffff421
  threshold=12 if n else 8
  if n:c.move_w(0x0203,b+12)
  for i in range(threshold):
   check(c,b+6,0,0x400)
   c.move_b(i,b+7);poll(c,b+6,0x400,0)
   c.w(0x1039);c.l(g);c.w(0x0240,0x40);c.expect(0x40 if i+1==threshold else 0)
  rd(c,b+4);c.w(0x1039);c.l(g);c.w(0x0240,0x40);c.expect(0)
  if n:
   # TRIG chooses near-full independently of the programmed RX marker.
   c.move_w(0x11c0,b+8)
   for i in range(threshold-1,63):c.move_b(i,b+7);poll(c,b+6,0x400,0)
   c.w(0x1039);c.l(g);c.w(0x0240,0x40);c.expect(0x40)
   rd(c,b+4);c.w(0x1039);c.l(g);c.w(0x0240,0x40);c.expect(0)
  stage(c,91)
 elif mode=='dual':
  stage(c,70);c.move_b(0x40,0xfffff300);c.move_w(0x6533,0xfffff314)
  for ch in range(2):
   u=setup(c,ch,misc=0x1040,ctl=0xe108);level=4+ch;handler=0x18000+ch*0x100;counter=MARKER+0x20+ch*2
   c.move_w(0,counter);c.move_w(handler>>16,4*(0x40+level));c.move_w(handler&65535,4*(0x40+level)+2)
   words=[0x2f00,0x3039,u>>16,(u+4)&65535,0x5279,counter>>16,counter&65535,0x201f,0x4e73]
   for i,word in enumerate(words):c.move_w(word,handler+2*i)
  c.move_b(0x41,0xfffff907);c.move_b(0x42,0xfffff917)
  poll(c,0xfffff904,0x2000,0x2000);poll(c,0xfffff914,0x2000,0x2000)
  check(c,0xfffff312,0x1004,0x1004);c.move_w(0xeffb,0xfffff306);c.w(0x46fc,0x2000)
  poll(c,MARKER+0x20,65535,1);poll(c,MARKER+0x22,65535,1);c.w(0x46fc,0x2700)
  check(c,0xfffff312,0,0x1004);stage(c,71)
 elif mode=='deep':
  b=setup(c,n,misc=0x1040);stage(c,40)
  c.move_b(0x18,b+6);c.move_b(0,b+7);poll(c,b+4,0x2000,0x2000)
  check(c,b+4,0x600,0x6ff);poll(c,b+6,0x400,0);c.move_b(8,b+6)
  c.move_b(0x55,b+7);poll(c,b+4,0x2000,0x2000);check(c,b+4,0x55,0x7ff);poll(c,b+6,0x400,0)
  stage(c,41)
  for i in range(6):c.move_b(i+1,b+7)
  c.move_w(0xc100,b);poll(c,b+6,0x400,0);check(c,b+4,1,0xff);check(c,b+4,0,0x2000)
  stage(c,42);c.move_w(0xe100,b)
  # Mask-only and RTS writes during a frame must preserve that frame.
  c.move_b(0x69,b+7);c.move_w(0xe180,b);c.move_w(0x1000,b+8)
  poll(c,b+4,0x2000,0x2000);check(c,b+4,0x69,0x7ff);poll(c,b+6,0x400,0)
  stage(c,43)
  # Direct SIR encoder/decoder loop, including TX and RX polarity reversal.
  c.move_w(0x0070,b+8);c.move_b(0xa5,b+7);poll(c,b+4,0x2000,0x2000);check(c,b+4,0xa5,0x7ff);poll(c,b+6,0x400,0)
  c.move_w(0x007c,b+8);c.move_b(0x3c,b+7);poll(c,b+4,0x2000,0x2000);check(c,b+4,0x3c,0x7ff);poll(c,b+6,0x400,0)
  stage(c,44)
  # UART2 SELECT=7 means divide-by-one (manufacturer addendum).
  if n:
   c.move_w(0x1040,b+8);c.move_w(0x8700,b+10);c.move_w(0x0700,b+2)
   c.move_b(0x66,b+7);poll(c,b+4,0x2000,0x2000);check(c,b+4,0x66,0x7ff)
  stage(c,45)
 elif mode=='clock':
  b=setup(c,n,misc=0x1040);stage(c,50)
  # Fixed external UCLK is a real configured board input, independent of SYSCLK.
  c.move_b(7,0xfffff423);c.move_w(0x0835,b+2)
  c.move_b(0xa6,b+7);poll(c,b+4,0x2000,0x2000);check(c,b+4,0xa6,0x7ff);poll(c,b+6,0x400,0)
  stage(c,51)
  # Direct 1x UCLK; in CLKM=1 the receiver samples global clock edges.
  c.move_w(0x5040,b+8);c.move_w(0xf100,b)
  c.move_b(0x96,b+7);poll(c,b+4,0x2000,0x2000);c.w(0x33c7);c.l(MARKER+0x30);check(c,b+4,0x96,0x7ff);poll(c,b+6,0x400,0)
  stage(c,52)
  # PE3 GPIO disconnects external clock; pending TX resumes when mux reconnects.
  c.move_b(15,0xfffff423);c.move_b(0x57,b+7);delay(c,5000);check(c,b+6,0x400,0x400);check(c,b+4,0,0x2000)
  c.move_b(7,0xfffff423);poll(c,b+4,0x2000,0x2000);check(c,b+4,0x57,0x7ff);poll(c,b+6,0x400,0)
  stage(c,53)
  c.move_b(0x42,b+7);c.move_b(15,0xfffff423);delay(c,5000)
  check(c,b+6,0x400,0x400);check(c,b+4,0,0x2000)
  c.move_b(7,0xfffff423);poll(c,b+4,0x2000,0x2000);check(c,b+4,0x42,0x7ff);poll(c,b+6,0x400,0)
  stage(c,54)
  # Cross-channel clock output and PCR selection, independent of external input.
  other=setup(c,1-n,ctl=0x8100,misc=0x40,baud=0x220b)
  c.move_b(0x10 if n==0 else 0,0xfffff003);c.move_b(7,0xfffff423)
  c.move_b(0x35,b+7);poll(c,b+4,0x2000,0x2000)
  rd(c,MARKER+0x30);c.w(0xbe40,0x6506);c.jump('fail')
  check(c,b+4,0x35,0x7ff);poll(c,b+6,0x400,0);stage(c,55)
 elif mode=='flow':
  b=setup(c,n,misc=0x10c0);c.move_b(0,b+6);stage(c,60)
  size=64 if n else 8
  for i in range(size+1):c.move_b(i,b+7)
  check(c,b+6,0x400,0xa400);check(c,b+6,0,0x2000)
  # CTS remains high while CPU observes FIFO saturation. UI input changes it later.
  c.move_w(0x5a5a,MARKER)
  poll(c,b+6,0x200,0);poll(c,b+6,0x400,0)
  for i in range(size):check(c,b+4,i,0xff)
  check(c,b+4,0,0x2000);stage(c,61)
 elif mode=='irq':
  b=setup(c,n,misc=0x1040);c.move_b(0x40,0xfffff300)
  # Real vectored interrupt level, CPU mask and peripheral condition clearing.
  for level in ([1,2,3,4,5,6] if n else [4]):
   stage(c,level+10);c.move_w(0,MARKER+0x20)
   handler=0x18000
   c.move_w(handler>>16,4*(0x40+level));c.move_w(handler&65535,4*(0x40+level)+2)
   # Install a tiny 68000 ISR using CPU instructions, not observer injection.
   words=[0x2f00,0x3039,b>>16,(b+4)&65535,0x5279,(MARKER+0x20)>>16,(MARKER+0x20)&65535,0x201f,0x4e73]
   for i,word in enumerate(words):c.move_w(word,handler+2*i)
   if n:c.move_w(0x6033|(level<<8),0xfffff314)
   c.move_w(0xe108,b);c.move_w(0xffff,0xfffff306);c.move_b(0x51,b+7)
   poll(c,b+4,0x2000,0x2000);check(c,0xfffff312,0x1000 if n else 4,0x1004)
   check(c,MARKER+0x20,0);c.move_w(0xffff^(0x1000 if n else 4),0xfffff306)
   c.w(0x46fc,0x2000);poll(c,MARKER+0x20,65535,1);c.w(0x46fc,0x2700)
   check(c,b+4,0,0x2000);check(c,0xfffff312,0,0x1004)
  # CTS-delta write/read and IRQ under UART enable, even with TX disabled.
  c.move_w(0x8040,b);c.move_b(1,b+6);check(c,0xfffff312,0x1000 if n else 4,0x1004)
  c.move_b(0,b+6);check(c,0xfffff312,0,0x1004)
  stage(c,30)
 return c.finish()

def main():
 p=argparse.ArgumentParser();p.add_argument('--installed',action='store_true');p.add_argument('--case',required=True)
 p.add_argument('--mode',choices=['loop','irq','backend','irda','save','deep','clock','flow','irtest','dual','saveir','reset','rts'],required=True);p.add_argument('--uart',type=int,choices=[1,2],required=True)
 a=p.parse_args();root=Path(__file__).resolve().parents[1];n=a.uart-1
 folder=root/'local-evidence/runtime-compare/serial-20261101'/a.case;folder.mkdir(parents=True,exist_ok=False)
 binary=root/('runtime/diag/bin/dana-diag'if a.installed else'runtime/diag/source/danadiagd')
 cfg=folder/'cfg';cfg.mkdir()
 for name in ['asmdana.cfg','default.cfg']:shutil.copy2(root/'config/palm-uk15'/name,cfg/name)
 if a.mode=='clock':
  q=cfg/'asmdana.cfg';q.write_text(q.read_text().replace('</input>','<port tag=":UCLK" type="CONFIG" mask="67108863" defvalue="0" value="1843200"/></input>'))
 if a.mode=='flow':
  q=cfg/'asmdana.cfg';q.write_text(q.read_text().replace('</input>',f'<port tag=":serial{n}:LINES" type="CONFIG" mask="1" defvalue="0" value="1"/></input>'))
 (folder/'guest.dana').write_bytes(fixture(a.mode,n))
 path=folder/'cpu.json';saved=folder/'saved.sta'
 lua='''local m=manager.machine;local b=m.devices[":maincpu"].spaces.program;local frame=0;local saved=false;local reset_sent=false;local loaded=false;local load_seen=false
local f=assert(io.open(RESULT..".mmio","w"));local count=0
local tap=b:install_read_tap(0xfffff900,0xfffff91d,"uart_cpu_read",function(a,d,k)count=count+1;if count<2000 then f:write(string.format("%08x %08x %04x %04x",m.devices[":maincpu"].state.CURPC.value,a,d,k)..string.char(10));f:flush()end end)
local notifier=emu.add_machine_post_load_notifier(function()load_seen=true end)
emu.register_frame_done(function()
 if not tap or not notifier then return end;frame=frame+1
 local v=b:read_u16(0x20000)
 if RESET and v==0x5a5a and not reset_sent then reset_sent=true;m:soft_reset();return end
 if SAVE and v==0x5a5a and not saved then saved=true;m:save(STATE)end
 if SAVE and v==0xa55a and not loaded then loaded=true;m:load(STATE);return end
 if v==0xa55a or v==0xdead or frame>600 then
  if SAVE and v==0xa55a and not load_seen and frame<600 then return end
  local f=assert(io.open(RESULT,"w"));f:write(string.format('{"marker":%d,"stage":%d,"failure_d0":%d,"frames":%d,"restored":%s}',v,b:read_u16(0x20002),b:read_u16(0x20006),frame,tostring(load_seen)));f:close();m:exit()
 end
end)
'''.replace('RESET','true'if a.mode=='reset'else'false').replace('SAVE','true'if a.mode in ['save','saveir']else'false').replace('STATE',json.dumps(str(saved))).replace('RESULT',json.dumps(str(path)))
 if a.mode=='flow':
  wire=folder/'peer.bin';wire.write_bytes(b'')
  action='if frame==1 then m.images[":serial%d:stream"]:load(%s)end;if frame==2 then m.ioport.ports[":serial%d:LINES"].fields["Serial peer CTS"].user_value=0 end'%(n,json.dumps(str(wire)),n)
  lua=lua.replace('local v=b:',action+';local v=b:')
 (folder/'observe.lua').write_text(lua)
 command=[str(binary),'asmdana','-video','none','-sound','none','-skip_gameinfo','-nowriteconfig','-cfg_directory',str(cfg),'-nvram_directory',str(folder/'nvram'),'-state_directory',str(folder/'states'),'-autoboot_delay','0','-autoboot_script',str(folder/'observe.lua'),'-quickload',str(folder/'guest.dana'),'-log','-oslog']
 listener=None;payload=b'Dana UART'+bytes([49+n])+b'\x00\x55\xaa\xff';received=b''
 if a.mode in ['backend','irda','irtest']:
  listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(15)
  command+=['-throttle']
  script=(folder/'observe.lua').read_text()
  attach='if frame==1 then m.images[":serial%d:stream"]:load(%s)end'%(n,json.dumps('socket.127.0.0.1:'+str(listener.getsockname()[1])))
  (folder/'observe.lua').write_text(script.replace('local v=b:',attach+';local v=b:'))
  text=(cfg/'asmdana.cfg').read_text();text=text.replace('</input>',f'<port tag=":serial{n}:FORMAT" type="CONFIG" mask="24" defvalue="0" value="{24 if a.mode in ["irda","irtest"]else 8}"/></input>');(cfg/'asmdana.cfg').write_text(text)
 else:command+=['-nothrottle']
 env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',TMPDIR=str(folder))
 with(folder/'run.out').open('w')as out:
  process=subprocess.Popen(command,cwd=root/'runtime/diag',env=env,stdout=out,stderr=subprocess.STDOUT)
  try:
   if listener:
    peer,_=listener.accept();peer.settimeout(12)
    with peer:
     if a.mode!='irtest':peer.sendall(payload)
     while len(received)<len(payload):
      d=peer.recv(256)
      if not d:break
      received+=d
   process.wait(timeout=60)
  finally:
   if process.poll()is None:process.kill();process.wait()
   if listener:listener.close()
 result=json.loads(path.read_text())if path.exists()else{}
 result.update(mode=a.mode,uart=a.uart,returncode=process.returncode,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),host_tx=payload.hex()if listener else'',host_rx=received.hex())
 result['lua_errors']=any(x in (folder/'run.out').read_text()for x in ['LUA ERROR','Lua error','Error in Lua'])
 result['pass']=not result['lua_errors']and result.get('marker')==0xa55a and process.returncode==0 and (not listener or received==payload)and(a.mode not in ['save','saveir']or result.get('restored'))
 (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
 if not result['pass']:print((folder/'run.out').read_text()[-2500:]);raise SystemExit(1)
if __name__=='__main__':main()
