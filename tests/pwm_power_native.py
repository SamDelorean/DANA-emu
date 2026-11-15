#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""H5 real 68000 PWM/GPIO/SPI2 tests; observer never writes guest state."""
import argparse,hashlib,json,os,re,shutil,struct,subprocess,wave
from pathlib import Path
from d7_5_native import Code,ENTRY,MARKER
from nor_native import check,finish,wait,fixture as physical_fixture
from h2_native import timer,vector,enter,leave,bounds

CTRL=0xfffff500;SAMPLE=CTRL+2;PERIOD=CTRL+4;PB=0xfffff409;T1=0xfffff600
def rd(c,address):c.w(0x3039);c.l(address)
def byte(c,address,mask=255):c.w(0x1039);c.l(address);c.w(0x0240,mask)
def stage(c,n):c.move_w(n,MARKER+2)
def pin(c,high):
 name=c.unique();c.label(name);byte(c,PB,128);c.w(0x0c40,128 if high else 0,0x6706);c.jump(name)
def ticks(c,address):rd(c,T1+8);c.record(address)
def elapsed(c,address,out):rd(c,T1+8);c.w(0x9079);c.l(address);c.record(out)
def pwm(c,control=0x8010,period=30):
 c.move_b(0,0xfffff40b);c.move_w(control,CTRL);c.move_b(period,PERIOD)
def edge_period(c,out):
 pin(c,False);pin(c,True);ticks(c,MARKER+0x30)
 pin(c,False);pin(c,True);elapsed(c,MARKER+0x30,out)
def xch(c,value,width):
 c.move_w(value,0xfffff800);c.move_w(0x300|width-1,0xfffff802)
 rd(c,0xfffff802);c.w(0x0240,0x180);c.expect(0x80);rd(c,0xfffff800)
def adc(c,command,bits):
 xch(c,command>>1 if bits==7 else command,bits)
 if bits==7:xch(c,0,1)
 xch(c,0,16)

def payload(mode):
 c=Code();c.w(0x46fc,0x2700);c.move_w(0,0xfffffb0a)
 if mode=='reset':
  rd(c,MARKER);c.w(0x0c40,0x5a5a,0x6606);c.jump('after_reset')
 for i in range(128):c.move_w(0,MARKER+2*i)
 timer(c,0);stage(c,1)
 check(c,CTRL,0x20);check(c,PERIOD,0xfe00)
 c.move_b(31,PERIOD);check(c,PERIOD,0xfe00) # disabled writes ignored
 if mode.startswith('repeat') or mode=='save':
  repeat=int(mode[-1])if mode.startswith('repeat')else 3;factor=1<<repeat
  pwm(c,0x8010|(repeat<<2));c.move_b(99,SAMPLE);c.move_w(0x0408,SAMPLE);c.move_w(0x0c10,SAMPLE)
  rd(c,CTRL);c.w(0x0240,0x20);c.expect(0x20);c.move_w(0x1418,SAMPLE)
  rd(c,CTRL);c.w(0x0240,0x2c);c.expect(0) # full FIFO, REPEAT reads zero
  c.move_b(99,SAMPLE);c.move_w(0xaaaa,SAMPLE) # invalid high byte / full FIFO ignored
  if mode=='save':c.move_w(0x5a5a,MARKER)
  for sample in [4,8,12,16,20]:
   for r in range(factor):
    pin(c,False);pin(c,True);ticks(c,MARKER+0x30);pin(c,False)
    elapsed(c,MARKER+0x30,MARKER+0x32);bounds(c,2*sample-2,2*sample+2)
    rd(c,PERIOD);c.w(0x0240,255);bounds(c,sample-1,sample+2)
  stage(c,2)
 elif mode in ['counter','period-ff','duty0','duty100']:
  pwm(c,period=254 if mode=='period-ff'else 30)
  if mode=='counter':
   wait(c,16);rd(c,PERIOD);c.w(0x0240,255);bounds(c,7,10);c.record(MARKER+0x40)
   c.move_w(0x8010,CTRL);c.move_b(255,PERIOD+1)
   rd(c,PERIOD);c.w(0x0240,255);bounds(c,7,10)
  elif mode=='period-ff':
   c.move_b(255,PERIOD);c.move_w(0x8080,SAMPLE);edge_period(c,MARKER+0x40);bounds(c,511,513)
   check(c,PERIOD,0xff00,0xff00)
  else:
   if mode=='duty100':c.move_b(14,PERIOD);c.move_w(0x4040,SAMPLE);pin(c,True)
   c.w(0x7400,0x76ff,0x323c,4095);loop=len(c.data);byte(c,PB,128);c.w(0x8400,0xc600);c.w(0x51c9,(loop-(len(c.data)+2))&65535)
   c.w(0x3002);c.expect(128 if mode=='duty100'else 0);c.w(0x3003,0x0240,128);c.expect(128 if mode=='duty100'else 0)
  stage(c,2)
 elif mode=='irq-control':
  # The manufacturer's R/W IRQ bit supports software post/clear even when
  # the PWM counter is disabled; low-byte reads acknowledge the register.
  c.move_w(0x00c0,CTRL);check(c,0xfffff312,0x80,0x80)
  c.move_b(0x80,CTRL);check(c,0xfffff312,0x80,0x80)
  c.move_b(0x40,CTRL+1);check(c,0xfffff312,0,0x80)
  c.move_w(0x80c0,CTRL);rd(c,CTRL);c.w(0x0240,0x80);c.expect(0x80)
  check(c,0xfffff312,0,0x80);check(c,PERIOD,0xfe00);stage(c,2)
 elif mode in ['irq','mixed']:
  vector(c,6,'irq6');c.move_w(0xff7d,0xfffff306);c.w(0x46fc,0x2000)
  if mode=='mixed':timer(c,0,compare=128,irq=True,free=False)
  pwm(c,0x8050)
  loop=c.unique();c.label(loop);rd(c,MARKER+0x20);c.w(0x0c40,4,0x6406);c.jump(loop)
  check(c,MARKER+0x22,1 if mode=='mixed'else 0);c.jump('done')
  enter(c,'irq6');rd(c,0xfffff312);c.w(0x0240,0x80,0x6700);pos=len(c.data);c.w(0)
  rd(c,CTRL);c.w(0x0240,0x80);c.expect(0x80)
  c.move_w(0x0408,SAMPLE);c.move_w(0x0c10,SAMPLE);c.w(0x5279);c.l(MARKER+0x20)
  struct.pack_into('>H',c.data,pos,len(c.data)-pos)
  rd(c,0xfffff312);c.w(0x0240,2,0x6700);pos=len(c.data);c.w(0)
  rd(c,T1+10);c.move_w(0,T1+10);c.move_w(0,T1);c.w(0x5279);c.l(MARKER+0x22)
  struct.pack_into('>H',c.data,pos,len(c.data)-pos);leave(c)
 elif mode in ['clock','clock32']:
  pwm(c,0x8010 if mode=='clock32'else 0x7f13);c.move_w(0x0808,SAMPLE)
  for n in range(8):
   c.move_w(0x2093|(n<<8),0xfffff200);edge_period(c,MARKER+0x40+2*n)
  stage(c,2)
 elif mode in ['sleep','sleep32']:
  pwm(c,0x8010 if mode=='sleep32'else 0x7f13);c.move_w(0x1010,SAMPLE);pin(c,True)
  vector(c,6,'wake');c.move_w(0xfffd,0xfffff306);timer(c,0,compare=8208,irq=True,free=True)
  ticks(c,MARKER+0x30);rd(c,PERIOD);c.w(0x0240,255);c.record(MARKER+0x40)
  stage(c,2);c.move_w(0x249b,0xfffff200);c.w(0x4e72,0x2000)
  rd(c,PERIOD);c.w(0x0240,255);c.record(MARKER+0x42);ticks(c,MARKER+0x32)
  stage(c,3);c.jump('done');enter(c,'wake');rd(c,T1+10);c.move_w(0,T1+10);c.move_w(0,T1);leave(c)
 elif mode=='reset':
  pwm(c);c.move_w(0x1010,SAMPLE);pin(c,True);c.move_w(0x5a5a,MARKER);c.move_w(1,0xfffffb0a);c.w(0x4e72,0x2700)
  c.label('after_reset');check(c,CTRL,0x20);check(c,PERIOD,0xfe00);c.move_b(0,0xfffff40b);byte(c,PB,128);c.expect(0);stage(c,2)
 elif mode in ['adc7','adc8','adc-pen','power-low','power-high']:
  # Independent chip selects, as in authentic firmware: PE3 ST high, PG2 ADC low.
  c.move_b(8,0xfffff421);c.move_b(255,0xfffff433);c.move_b(0,0xfffff430);c.move_b(0,0xfffff431)
  if mode.startswith('power-'):
   byte(c,0xfffff431,2);c.expect(0 if mode=='power-low'else 2)
   c.move_b(2,0xfffff430);byte(c,0xfffff431,2);c.expect(0)
   c.move_b(0,0xfffff430);byte(c,0xfffff431,2);c.expect(0 if mode=='power-low'else 2)
  for command,raw in [(0xa4,0x600),(0xe4,0xc00)]:
   bits=8 if mode=='adc8'else 7;adc(c,command,bits);c.expect((raw<<(4 if bits==8 else 3))&65535)
  stage(c,2)
  if mode=='adc-pen':
   wait(c,4096);check(c,0xfffff310,0x10,0x10)
   byte(c,0xfffff431,2);c.expect(2)
   for command,raw in [(0xa4,0x600),(0xe4,0xc00)]:adc(c,command,7);c.expect(raw<<3)
   stage(c,3)
 else:raise ValueError(mode)
 return finish(c)

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',required=True);p.add_argument('--case',required=True);p.add_argument('--installed',action='store_true');a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.case)
 root=Path(__file__).resolve().parents[1];folder=root/'local-evidence/runtime-compare/h5-20261115'/a.case;folder.mkdir(parents=True,exist_ok=False)
 binary=root/('runtime/diag/bin/dana-diag'if a.installed else'runtime/diag/source/danadiagd');cfg=folder/'cfg';cfg.mkdir()
 for name in ['asmdana.cfg','default.cfg']:shutil.copy2(root/'config/palm-uk15'/name,cfg/name)
 path=cfg/'asmdana.cfg';s=path.read_text().replace('</input>','<port tag=":POWER_ADC_A4" type="CONFIG" mask="4095" defvalue="4095" value="1536"/><port tag=":POWER_ADC_E4" type="CONFIG" mask="4095" defvalue="4095" value="3072"/><port tag=":POWER_PG1" type="CONFIG" mask="2" defvalue="2" value="'+('0'if a.mode=='power-low'else'2')+'"/></input>');path.write_text(s)
 body=payload(a.mode);image=folder/('seed.bin'if a.mode=='reset'else'guest.dana')
 if a.mode=='reset':image.write_bytes(physical_fixture('pwm',body))
 else:
  header=bytearray(64);header[:8]=b'DANARAM1';end=ENTRY+len(body);struct.pack_into('>8I',header,8,ENTRY,ENTRY,len(body),0x1000,0x400000,0x2000,end,end);header[40:60]=hashlib.sha1(body).digest();struct.pack_into('>I',header,60,1);image.write_bytes(header+body)
 image.chmod(0o444);before=hashlib.sha256(image.read_bytes()).hexdigest()
 lua=r'''local m=manager.machine;local cpu=m.devices[":maincpu"];local b=cpu.spaces.program;local frames=0;local saved=false;local loaded=false;local restored=false;local events={};local states={};local done_frames=0;local pen_driven=false
local note=emu.add_machine_post_load_notifier(function()restored=true end)
local tap=b:install_write_tap(0x20000,0x200ff,"h5_native_journal",function(ad,d,mask)if #events<350 then events[#events+1]=string.format('{"address":%d,"data":%d,"time":%.12f}',ad,d,m.time:as_double())end end)
emu.register_frame_done(function()
 if not tap or not note then return end;frames=frames+1;local marker=b:read_u16(0x20000);local stage=b:read_u16(0x20002)
 if PEN_CASE and stage==2 and not pen_driven then
  for _,field in pairs(m.ioport.ports[":PEN"].fields)do field:set_value(1)end;pen_driven=true
 end
 local outputs=m.devices[":"].outputs;states[#states+1]=string.format('{"time":%.12f,"stage":%d,"cycles":%d,"samples":%d,"pin":%d}',m.time:as_double(),stage,outputs["dana_pwm1_cycles"]:get(),outputs["dana_pwm1_samples"]:get(),outputs["dana_pwm1_pin"]:get())
 if SAVING and marker==0x5a5a and not saved then saved=true;m:save(FOLDER.."/active.sta")end
 if SAVING and marker==0xa55a and not loaded then loaded=true;m:load(FOLDER.."/active.sta");return end
 if marker==0xa55a then done_frames=done_frames+1 else done_frames=0 end
 if marker==0xdead or(marker==0xa55a and done_frames>=6 and (not SAVING or restored))or frames>3000 then
  local words={};for a=0x20000,0x200fe,2 do words[#words+1]=tostring(b:read_u16(a))end
  local f=assert(io.open(FOLDER.."/cpu.json","w"));f:write(string.format('{"marker":%d,"stage":%d,"d0":%d,"restored":%s,"pen_driven":%s,"words":[%s],"events":[%s],"states":[%s]}',marker,stage,b:read_u16(0x20006),tostring(restored),tostring(pen_driven),table.concat(words,","),table.concat(events,","),table.concat(states,",")));f:close();m:exit()
 end
end)
'''.replace('FOLDER',json.dumps(str(folder))).replace('SAVING','true'if a.mode=='save'else'false').replace('PEN_CASE','true'if a.mode=='adc-pen'else'false');(folder/'observe.lua').write_text(lua)
 command=[str(binary),'asmdana','-video','none','-nothrottle','-skip_gameinfo','-nowriteconfig','-cfg_directory',str(cfg),'-nvram_directory',str(folder/'nvram'),'-state_directory',str(folder/'states'),'-rom'if a.mode=='reset'else'-quickload',str(image),'-autoboot_delay','0','-autoboot_script',str(folder/'observe.lua'),'-samplerate','48000','-wavwrite',str(folder/'audio.wav'),'-log','-oslog']
 env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',TMPDIR=str(folder))
 with(folder/'run.out').open('w')as f:r=subprocess.run(command,cwd=root/'runtime/diag',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=100)
 data=json.loads((folder/'cpu.json').read_text())if(folder/'cpu.json').exists()else{};text=(folder/'run.out').read_text()
 ok=data.get('marker')==0xa55a and r.returncode==0 and not any(t in text for t in ['LUA ERROR','Lua error','Error in Lua','PHYSICAL_BLOCKED'])
 if a.mode=='adc-pen':ok=ok and data.get('pen_driven')
 if a.mode=='save':ok=ok and data.get('restored')
 if a.mode in ['clock','clock32']:
  expected=[]
  for selector,value in enumerate(data.get('words',[])[32:40]):
   hz=33161216/(1 if selector>=4 else 2<<selector)
   want=64 if a.mode=='clock32'else 32768*128*16*32/hz
   expected.append(want);ok=ok and abs(value-want)<4
  data['expected_clock_ticks']=expected
 if a.mode in ['sleep','sleep32']:
  words=data.get('words',[]);before_count=words[32];after_count=words[33]
  if a.mode=='sleep':ok=ok and abs(after_count-before_count)<4
  else:
   delta=(words[25]-words[24])&65535;expected=delta/2;error=((after_count-before_count-expected+16)%32)-16;ok=ok and abs(error)<3;data['clock32_sleep_phase_error']=error
 if (folder/'audio.wav').exists():
  with wave.open(str(folder/'audio.wav'))as wav:
   pcm=wav.readframes(wav.getnframes());values=struct.unpack('<'+'h'*(len(pcm)//2),pcm);data['wav_peak']=max(map(abs,values),default=0);data['wav_frames']=len(values)
 data.update(mode=a.mode,installed=a.installed,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),seed_preserved=before==hashlib.sha256(image.read_bytes()).hexdigest(),returncode=r.returncode,pass_=bool(ok))
 (folder/'result.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({k:v for k,v in data.items()if k not in ['events','states','words']}),flush=True)
 if not ok:print(text[-2500:]);raise SystemExit(1)
if __name__=='__main__':main()
