#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Actual 68000 clock/power/RTC/watchdog/GPIO tests in the canonical MAME.

Lua observes CPU-owned journals and operates explicit external input pins.
It never patches CPU state, guest memory, peripheral registers or Palm traps.
"""
import argparse,hashlib,json,os,re,shutil,struct,subprocess
from pathlib import Path
from d7_5_native import Code,ENTRY,MARKER
from serial_native import rd,check,poll,delay,stage,setup

T1=0xfffff600;T2=0xfffff610;RTC=0xfffffb00;WD=RTC+10
COUNT=MARKER+0x20
def movel(c,value,address):c.w(0x23fc);c.l(value);c.l(address)
def bytecheck(c,address,value,mask=255):c.w(0x1039);c.l(address);c.w(0x0240,mask);c.expect(value)
def bounds(c,low,high):
 c.w(0x0c40,low,0x6406);c.jump('fail');c.w(0x0c40,high,0x6306);c.jump('fail')
def relative(c,expected_address,tolerance=4):
 c.w(0x3239);c.l(expected_address);c.w(0x3401)
 c.w(0x0442,tolerance,0xb042,0x6406);c.jump('fail')
 c.w(0x3401,0x0642,tolerance,0xb042,0x6306);c.jump('fail')
def timer(c,n,source=8,pre=0,compare=65535,irq=False,free=True):
 b=T2 if n else T1;c.move_w(0,b);rd(c,b+10);c.move_w(0,b+10)
 c.move_w(pre,b+2);c.move_w(compare,b+4);c.move_w(source|1|(0x100 if free else 0)|(0x10 if irq else 0),b)
def vector(c,level,name):
 c.move_b(0x40,0xfffff300);c.w(0x23fc);c.fixups.append((len(c.data),name));c.l(0);c.l(4*(0x40+level))
def enter(c,label):c.label(label);c.w(0x2f00,0x2f01)
def leave(c):c.w(0x221f,0x201f,0x4e73)
def inc(c,address=COUNT):c.w(0x5279);c.l(address)
def stop(c):c.w(0x4e72,0x2000)
def timed_loop(c,base,count=4095,output=MARKER+0x40):
 rd(c,base+8);c.record(MARKER+0x3e);delay(c,count);rd(c,base+8)
 c.w(0x9079);c.l(MARKER+0x3e);c.record(output)

def fixture(mode,rate):
 c=Code()
 if mode=='watchdog-reset':
  rd(c,MARKER);c.w(0x0c40,0x5a5a,0x6606);c.jump('after_reset')
 c.w(0x46fc,0x2700);c.move_w(0xffff,0xfffff304);c.move_w(0xffff,0xfffff306);c.move_w(0,WD);stage(c,1)
 if mode=='clock':
  timer(c,0);timer(c,1,source=2,pre=255)
  c.move_w(0x2493,0xfffff200);timed_loop(c,T1,output=MARKER+0x30)
  timed_loop(c,T2,output=MARKER+0x32)
  for selector in range(8):
   stage(c,10+selector);c.move_w(0x2093|(selector<<8),0xfffff200)
   # Same instruction sequence: CLK32 sees CPU slowing with SYSCLK.
   rd(c,MARKER+0x30)
   for _ in range(selector+1 if selector<4 else 0):c.w(0xd040)
   c.record(MARKER+0x34);timed_loop(c,T1);relative(c,MARKER+0x34,5+(2<<selector)if selector<4 else 5)
   # A SYSCLK timer and CPU keep their ratio while SYSCLK changes.
   timed_loop(c,T2);relative(c,MARKER+0x32,3)
  c.move_w(0x2493,0xfffff200);c.move_w(0x053f,0xfffff202)
  rd(c,MARKER+0x30);c.w(0xc0fc,2024,0x80fc,1804);c.record(MARKER+0x34)
  timed_loop(c,T1);relative(c,MARKER+0x34,5)
  c.move_w(0x453f,0xfffff202);c.move_w(0x0347,0xfffff202);check(c,0xfffff202,0x453f,0x7fff);stage(c,20)
 elif mode=='pcm':
  timer(c,0);timed_loop(c,T1,32767,MARKER+0x30)
  for width in [1,3,15,30,31]:
   stage(c,30+width);rd(c,MARKER+0x30);c.w(0xc0fc,31,0x80fc,width);c.record(MARKER+0x34)
   c.move_b(0x80|width,0xfffff207);timed_loop(c,T1,32767)
   c.move_b(0x1f,0xfffff207);rd(c,MARKER+0x40);relative(c,MARKER+0x34,40)
  stage(c,70)
 elif mode in ['sleep','doze','sleep-save']:
  timer(c,1,source=2,pre=1023);vector(c,6,'wake6')
  c.move_w(0xfffd,0xfffff306);c.w(0x46fc,0x2000);timer(c,0,compare=8192 if mode=='sleep-save' else 128,irq=True,free=False)
  stage(c,80)
  if mode in ['sleep','sleep-save']:
   if mode=='sleep-save':c.move_w(0x5a5a,MARKER)
   c.move_w(0x2498|rate,0xfffff200);stop(c)
  else:c.move_b(0x80,0xfffff207)
  check(c,COUNT,1);bytecheck(c,0xfffff207,0,0x80);check(c,0xfffff200,0,8)
  rd(c,T2+8)
  if mode in ['sleep','sleep-save']:bounds(c,0,20) # SYSCLK timer froze during PLL-off/wake delay.
  else:bounds(c,115,145) # Peripheral SYSCLK continued while CPUCLK was off.
  c.jump('done');enter(c,'wake6');rd(c,T1+10);c.move_w(0,T1+10);c.move_w(0,T1);inc(c);leave(c)
 elif mode=='rtc-rate':
  timer(c,0);vector(c,4,'rate4');c.move_w(1<<(8+rate),RTC+16);c.move_w(0xffff,RTC+14)
  c.move_w(0xffbf,0xfffff304);c.move_w(0xffff,0xfffff306)
  for _ in range(3):stop(c)
  check(c,COUNT,3);rd(c,MARKER+0x32);c.w(0x9079);c.l(MARKER+0x30)
  ticks=2*(8192>>rate);bounds(c,ticks-3,ticks+3);check(c,0xfffff310,0,0x40)
  c.jump('done');enter(c,'rate4')
  rd(c,COUNT);c.w(0x4a40,0x6706);skip=c.unique();c.jump(skip)
  rd(c,T1+8);c.record(MARKER+0x30);c.label(skip)
  rd(c,T1+8);c.record(MARKER+0x32);inc(c)
  check(c,0xfffff310,0x40,0x40);c.move_b(255,RTC+15);check(c,0xfffff310,0x40,0x40)
  c.move_b(1<<rate,RTC+14);check(c,0xfffff310,0,0x40)
  rd(c,COUNT);c.w(0x0c40,3,0x6706);end=c.unique();c.jump(end);c.move_w(0,RTC+16);c.label(end);leave(c)
 elif mode=='rtc-ref':
  timer(c,0);vector(c,4,'ref4');movel(c,0,RTC);c.move_w(0xa0,RTC+12);c.move_w(0xffff,RTC+14)
  c.move_w(0x10,RTC+16);c.move_w(0xffef,0xfffff306);stop(c)
  rd(c,T1+8);bounds(c,38397,38404);check(c,RTC+2,1);check(c,COUNT,1)
  c.jump('done');enter(c,'ref4');c.move_w(0,RTC+16);c.move_w(0xffff,RTC+14);inc(c);leave(c)
 elif mode=='watchdog-irq':
  timer(c,0,pre=3);vector(c,4,'wd4');movel(c,5,RTC);c.move_w(0,RTC+12)
  c.move_w(3,WD);c.move_w(0xfff7,0xfffff306);stop(c)
  rd(c,T1+8);bounds(c,16370,16400);check(c,RTC+2,5);check(c,COUNT,1);check(c,MARKER+0x22,0x80,0x80)
  check(c,0xfffff312,0,8);c.move_w(0,WD)
  c.jump('done');enter(c,'wd4');rd(c,WD);c.record(MARKER+0x22);c.move_b(0x83,WD+1);c.move_b(0,WD);inc(c);leave(c)
 elif mode=='watchdog-reset':
  setup(c,1,misc=0x1040);c.move_b(0x57,0xfffff917);poll(c,0xfffff914,0x2000,0x2000)
  movel(c,0x173b003b,RTC);c.move_w(6,RTC+26);c.move_w(0xf00d,MARKER+0x60)
  c.move_w(1,WD);c.move_w(0x5a5a,MARKER);c.w(0x4e72,0x2700)
  c.label('after_reset');check(c,WD,1);check(c,0xfffff910,0);check(c,0xfffff202,0x347,0x7fff)
  check(c,0xfffff200,0x24b3);bytecheck(c,0xfffff207,31);check(c,MARKER+0x60,0xf00d)
  check(c,RTC,0);check(c,RTC+2,1);check(c,RTC+26,7);c.move_w(0,WD);stage(c,90)
 elif mode=='watchdog-service':
  vector(c,6,'feed6');c.move_w(1,WD);c.move_w(0xfffd,0xfffff306)
  timer(c,0,pre=31,compare=512,irq=True,free=False)
  for _ in range(6):stop(c)
  check(c,COUNT,6);c.move_w(0,T1);c.move_w(0,WD);stage(c,91)
  c.jump('done');enter(c,'feed6');c.move_b(0x55,WD);rd(c,T1+10);c.move_w(0,T1+10);inc(c);leave(c)
 elif mode=='rtc-calendar':
  vector(c,4,'calendar4');c.move_w(0xffef,0xfffff306);c.move_w(7,RTC+26)
  c.move_w(1,RTC+18);movel(c,0x003b003b,RTC);c.move_w(7,RTC+28);movel(c,0x01000000,RTC+4)
  c.move_w(0x24,RTC+16);stop(c)
  check(c,RTC,0x0100);check(c,RTC+2,0);check(c,RTC+18,0);check(c,MARKER+0x24,0x24,0x24)
  # A second real minute rollover times out the stopwatch.
  movel(c,0x0100003b,RTC);c.move_w(1,RTC+16);stop(c)
  check(c,RTC+18,63);check(c,MARKER+0x24,1,1);check(c,COUNT,2)
  c.jump('done');enter(c,'calendar4');rd(c,RTC+14);c.record(MARKER+0x24);c.move_w(0,RTC+16);c.move_w(0xffff,RTC+14);inc(c);leave(c)
 elif mode=='gpio':
  # PDSEL low four bits are reserved: they do not disable GPIO outputs.
  c.move_b(0,0xfffff41b);c.move_b(3,0xfffff418);c.move_b(0,0xfffff419)
  bytecheck(c,0xfffff419,0,3);c.move_b(3,0xfffff419);bytecheck(c,0xfffff419,3,3)
  c.move_b(0,0xfffff418)
  c.move_b(255,0xfffff413);c.move_b(0,0xfffff410);c.move_b(0xf0,0xfffff412)
  bytecheck(c,0xfffff411,5);c.move_b(0xa0,0xfffff411);bytecheck(c,0xfffff411,5)
  c.move_b(0xf0,0xfffff410);bytecheck(c,0xfffff411,0xa5)
  c.move_b(255,0xfffff412);bytecheck(c,0xfffff411,0xa5)
  # LCD function overrides GPIO direction/latch: physical LCLK is not a latch.
  c.move_b(0xbf,0xfffff413);c.move_b(8,0xfffffa20);c.move_b(63,0xfffffa25);c.move_b(0x80,0xfffffa27)
  c.w(0x7200,0x3e3c,4095,0x1039);c.l(0xfffff411);c.w(0x0240,0x40,0x3400)
  loop=c.unique();c.label(loop);c.w(0x1039);c.l(0xfffff411);c.w(0x0240,0x40,0xb042,0x6702,0x5241,0x3400)
  c.w(0x51cf,(c.labels[loop]-(ENTRY+len(c.data)+2))&65535)
  c.w(0x3001);bounds(c,1,4095);stage(c,92)
 elif mode=='clock-cross':
  vector(c,4,'cross4');c.move_w(0x100,RTC+16);c.move_w(0xffff,RTC+14)
  c.move_w(0xffbf,0xfffff304);timer(c,0)
  c.w(0x3c3c,999);loop=c.unique();c.label(loop)
  c.move_w(0x2393,0xfffff200);delay(c,15);c.move_w(0x2493,0xfffff200)
  c.w(0x51ce,(c.labels[loop]-(ENTRY+len(c.data)+2))&65535)
  stop(c);rd(c,MARKER+0x30);bounds(c,8188,8196);stage(c,94)
  c.jump('done');enter(c,'cross4');rd(c,T1+8);c.record(MARKER+0x30)
  c.move_w(0,RTC+16);c.move_w(0xffff,RTC+14);leave(c)
 elif mode=='timer-mask':
  n=rate;b=T2 if n else T1;level=3 if n else 6;bit=32 if n else 2
  vector(c,level,'maskirq');timer(c,n,compare=16,irq=False,free=True)
  poll(c,b+10,1,1);check(c,0xfffff312,0,bit)
  c.move_w(0xffff^bit,0xfffff306);c.move_w(0x119,b);stop(c)
  check(c,COUNT,1);check(c,0xfffff312,0,bit);stage(c,96)
  c.jump('done');enter(c,'maskirq');rd(c,b+10);c.move_w(0,b+10);c.move_w(0,b);inc(c);leave(c)
 elif mode=='irq-mixed':
  for level in [6,5,4]:vector(c,level,'mixed'+str(level))
  b=setup(c,1,ctl=0xe108,misc=0x1040);c.move_w(0x6533,0xfffff314)
  timer(c,0,compare=16,irq=True,free=True);c.move_b(0x51,b+7)
  c.move_w(0x8000,RTC+16);c.move_w(0xffff,RTC+14)
  poll(c,0xfffff310,0x40,0x40);poll(c,0xfffff312,0x1002,0x1002)
  c.move_w(0xffbf,0xfffff304);c.move_w(0xeffd,0xfffff306)
  c.w(0x46fc,0x2000);poll(c,COUNT,65535,3);c.w(0x46fc,0x2700)
  check(c,MARKER+0x30,0x0654);stage(c,97);c.jump('done')
  for level in [6,5,4]:
   enter(c,'mixed'+str(level));rd(c,MARKER+0x30);c.w(0xe948,0x0040,level);c.record(MARKER+0x30)
   if level==6:rd(c,T1+10);c.move_w(0,T1+10);c.move_w(0,T1)
   elif level==5:rd(c,b+4)
   else:c.move_w(0,RTC+16);c.move_w(0xffff,RTC+14)
   inc(c);leave(c)
 elif mode=='gpio-doze':
  vector(c,4,'edge4');c.move_b(0,0xfffff418);c.move_b(0,0xfffff41c)
  c.move_b(1,0xfffff41d);c.move_b(0,0xfffff41e);c.move_b(1,0xfffff41f)
  c.move_w(0xfeff,0xfffff306);stage(c,95);c.move_b(0x80,0xfffff207)
  # IMR allows the source even while the CPU SR masks its ISR.
  bytecheck(c,0xfffff207,0,0x80);check(c,COUNT,0);check(c,0xfffff312,0x100,0x100)
  c.w(0x46fc,0x2000);check(c,COUNT,1);stage(c,99)
  c.jump('done');enter(c,'edge4');check(c,0xfffff312,0x100,0x100)
  c.move_w(0x100,0xfffff30e);inc(c);leave(c)
 elif mode=='gpio-wake':
  vector(c,4,'gpio4');c.move_b(0,0xfffff418);c.move_b(0,0xfffff41c)
  c.move_b(1,0xfffff41d);c.move_b(2,0xfffff41e);c.move_b(1,0xfffff41f)
  c.move_w(0xfebf,0xfffff306);stage(c,95);c.move_w(0x249b,0xfffff200);stop(c)
  check(c,COUNT,1);check(c,0xfffff30e,0,0x140);check(c,0xfffff200,0,8);stage(c,98)
  c.jump('done');enter(c,'gpio4');check(c,0xfffff30e,0x140,0x140)
  c.move_w(0x140,0xfffff30e);check(c,0xfffff30e,0x40,0x140)
  c.move_b(0,0xfffff41e);inc(c);leave(c)
 elif mode=='save':
  vector(c,4,'save4');c.move_w(0xffe7,0xfffff306);movel(c,0x003b003a,RTC);c.move_w(7,RTC+26)
  c.move_w(0xffff,RTC+14);c.move_w(0x10,RTC+16);c.move_w(3,WD);stop(c)
  check(c,COUNT,1);check(c,WD,0x100,0x300);c.move_w(0x5a5a,MARKER);c.move_b(0x8f,0xfffff207);stop(c)
  check(c,COUNT,2);check(c,MARKER+0x22,0x80,0x80);check(c,RTC,0x100);check(c,RTC+2,0);check(c,RTC+26,7)
  c.move_w(0,WD);stage(c,93);c.jump('done')
  enter(c,'save4');rd(c,WD);c.record(MARKER+0x22);c.w(0x0240,0x80,0x6708);c.move_w(0x83,WD)
  c.move_w(0xffff,RTC+14);inc(c);rd(c,COUNT);c.w(0x0c40,2,0x6608);c.move_w(0,RTC+16);leave(c)
 else:raise ValueError(mode)
 return c.finish()

def main():
 p=argparse.ArgumentParser();p.add_argument('--installed',action='store_true');p.add_argument('--case',required=True)
 p.add_argument('--mode',choices=['clock','pcm','sleep','doze','rtc-rate','rtc-ref','watchdog-irq','watchdog-reset','watchdog-service','rtc-calendar','gpio','save','clock-cross','timer-mask','irq-mixed','gpio-wake','sleep-save','gpio-doze'],required=True)
 p.add_argument('--rate',type=int,default=0);a=p.parse_args();assert re.fullmatch(r'[A-Za-z0-9_-]+',a.case)
 root=Path(__file__).resolve().parents[1];folder=root/'local-evidence/runtime-compare/h2-20261101'/a.case;folder.mkdir(parents=True,exist_ok=False)
 binary=root/('runtime/diag/bin/dana-diag'if a.installed else'runtime/diag/source/danadiagd')
 cfg=folder/'cfg';cfg.mkdir()
 for name in ['asmdana.cfg','default.cfg']:shutil.copy2(root/'config/palm-uk15'/name,cfg/name)
 if a.mode=='gpio':
  f=cfg/'asmdana.cfg';s=f.read_text().replace('</input>','<port tag=":PCDRIVE" type="CONFIG" mask="255" defvalue="0" value="15"/><port tag=":PCVALUE" type="CONFIG" mask="255" defvalue="0" value="5"/></input>');f.write_text(s)
 if a.mode in ['gpio-wake','gpio-doze']:
  f=cfg/'asmdana.cfg';s=f.read_text().replace('</input>','<port tag=":GPIO1DRIVE" type="CONFIG" mask="255" defvalue="0" value="3"/><port tag=":GPIO1VALUE" type="CONFIG" mask="255" defvalue="0" value="2"/></input>');f.write_text(s)
 (folder/'guest.dana').write_bytes(fixture(a.mode,a.rate));result_path=folder/'cpu.json';state=folder/'in-flight.sta'
 lua='''local m=manager.machine;local cpu=m.devices[":maincpu"];local b=cpu.spaces.program;local frame=0
local edge=false;local level=false;local pinok=true;local saved=false;local loaded=false;local restored=false;local events={};local count=0
local note=emu.add_machine_post_load_notifier(function()restored=true end)
local function event(addr,data,mask)
 if cpu.state.CURPC.value<0x2140 or cpu.state.CURPC.value>0x10000 then return end
 if addr==0xfffff600 or addr==0xfffff200 or (addr==0x20020 and data~=0) or addr==0x20002 then
  count=count+1;if count<=120 then table.insert(events,string.format('{"address":%d,"data":%d,"mask":%d,"time":%.12f}',addr,data,mask,m.time:as_double()))end
 end
end
local tap=b:install_write_tap(0x20000,0x2007f,"h2_cpu_journal",event)
local clocks=b:install_write_tap(0xfffff200,0xfffff619,"h2_cpu_clocks",event)
emu.register_frame_done(function()
 if not tap or not clocks or not note then return end;frame=frame+1;local v=b:read_u16(0x20000)
 if GPIOEDGE and b:read_u16(0x20002)==95 and not edge then
  edge=true;pinok=b:read_u8(0xfffff207)==0x80
  m.ioport.ports[":GPIO1VALUE"].fields["Port D external input levels"].user_value=3
 end
 if GPIOWAKE and b:read_u16(0x20002)==95 then
  if not edge then edge=true;m.ioport.ports[":GPIO1VALUE"].fields["Port D external input levels"].user_value=3
  elseif not level then
   pinok=b:read_u16(0xfffff200)&8~=0 and b:read_u16(0xfffff30e)&0x140==0x100
   level=true;m.ioport.ports[":GPIO1VALUE"].fields["Port D external input levels"].user_value=1
  end
 end
 if SAVE and v==0x5a5a and not saved then saved=true;m:save(STATE)end
 if SAVE and v==0xa55a and not loaded then loaded=true;m:load(STATE);return end
 if v==0xa55a or v==0xdead or frame>900 then
  if GPIOWAKE and (not pinok or not edge or not level) then v=0xdead end
  if GPIOEDGE and (not pinok or not edge) then v=0xdead end
  if SAVE and v==0xa55a and not restored and frame<900 then return end
  local f=assert(io.open(RESULT,"w"));f:write(string.format('{"marker":%d,"stage":%d,"failure_d0":%d,"frames":%d,"restored":%s,"events":[%s]}',v,b:read_u16(0x20002),b:read_u16(0x20006),frame,tostring(restored),table.concat(events,",")));f:close();m:exit()
 end
end)
'''.replace('GPIOEDGE','true'if a.mode=='gpio-doze'else'false').replace('GPIOWAKE','true'if a.mode=='gpio-wake'else'false').replace('SAVE','true'if a.mode in ['save','sleep-save']else'false').replace('STATE',json.dumps(str(state))).replace('RESULT',json.dumps(str(result_path)))
 (folder/'observe.lua').write_text(lua)
 command=[str(binary),'asmdana','-video','none','-sound','none','-nothrottle','-skip_gameinfo','-nowriteconfig','-cfg_directory',str(cfg),'-nvram_directory',str(folder/'nvram'),'-state_directory',str(folder/'states'),'-quickload',str(folder/'guest.dana'),'-autoboot_delay','0','-autoboot_script',str(folder/'observe.lua'),'-log','-oslog']
 env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',TMPDIR=str(folder))
 with(folder/'run.out').open('w')as out:r=subprocess.run(command,cwd=root/'runtime/diag',env=env,stdout=out,stderr=subprocess.STDOUT,timeout=100)
 data=json.loads(result_path.read_text())if result_path.exists()else{}
 text=(folder/'run.out').read_text();data.update(mode=a.mode,rate=a.rate,returncode=r.returncode,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
 data['pass']=data.get('marker')==0xa55a and r.returncode==0 and not any(t in text for t in ['LUA ERROR','Lua error','PHYSICAL_BLOCKED'])and(a.mode not in ['save','sleep-save']or data.get('restored'))
 if data['pass'] and a.mode in ['rtc-rate','sleep']:
  ev=data['events'];irqs=[x['time']for x in ev if x['address']==COUNT]
  if a.mode=='rtc-rate':
   period=(8192>>a.rate)/32768;data['irq_period_s']=(irqs[2]-irqs[0])/2;data['pass']=abs(data['irq_period_s']/period-1)<.02
  else:
   enabled=next(x['time']for x in ev if x['address']==T1 and x['data']&0x10)
   data['wake_elapsed_ticks']=(irqs[0]-enabled)*32768;expected=128+[32,48,64,96][a.rate];data['pass']=abs(data['wake_elapsed_ticks']-expected)<4
 (folder/'result.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({k:v for k,v in data.items()if k!='events'}))
 if not data['pass']:print(text[-2500:]);raise SystemExit(1)
if __name__=='__main__':main()
