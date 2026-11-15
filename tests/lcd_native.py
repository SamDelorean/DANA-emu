#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""H4: real 68000 framebuffer/MMIO, read-only Lua pixel/timing observer.

Synthetic diagnostics only. No host RAM/register writes or private ROM data.
The physical-mode cases reuse the qualified H3 reset/CS/SDRAM bootstrap.
"""
import argparse,hashlib,json,os,re,shutil,struct,subprocess
from pathlib import Path
from d7_5_native import Code,ENTRY,MARKER
from nor_native import finish,fixture as physical_fixture,check,wait

NUM=[0,1,1,1,1,2,4,1,5,3,2,3,4,7,14,1]
DEN=[1,8,5,4,3,5,9,2,9,5,3,4,5,8,15,1]

def mode_config(mode):
 bpp=1 if mode=='bpp1' else 2 if mode in ['bpp2','cursor2'] or mode.startswith('palette') else 4
 return dict(bpp=bpp,pan=15 if mode=='pan' else 0,stride=255 if mode=='pagewrap' else ((560+(15 if mode=='pan'else 0))*bpp+15)//16+2,
             base=0x1f8002 if mode=='pagewrap' else 0xc30002 if mode=='ram16' else 0x630002 if mode=='ram8' else 0x30002)

def fill(c,cfg,invert=0):
 bpp=cfg['bpp'];n=16//bpp;stride=cfg['stride'];base=cfg['base']
 for y in range(160):
  words=[]
  for w in range(stride):
   value=0
   for p in range(n):
    x=w*n+p;v=x% (1<<bpp)
    if y&1:v^=(1<<bpp)-1
    v^=invert;value=value<<bpp|v
   words.append(value)
  # The CPU explicitly addresses both sides of the documented 20-bit DMA
  # counter boundary. Ordinary CPU writes themselves must never be mirrored.
  i=0
  while i<stride:
   address=(base&0xfff00000)|((base+y*2*stride+2*i)&0xffffe)
   c.w(0x207c);c.l(address) # movea.l #address,a0
   count=min(stride-i,(0x100000-(address&0xfffff))//2)
   # Emit short repeating patterns with an actual DBRA guest loop.
   period=4 if bpp==4 else 1
   groups=count//period
   if groups:
    c.w(0x323c,groups-1);loop=len(c.data)
    for p in range(period):c.w(0x30fc,words[i+p])
    c.w(0x51c9,(loop-(len(c.data)+2))&65535)
    i+=groups*period
   for p in range(count%period):c.w(0x30fc,words[i]);i+=1

def regs(c,cfg):
 for a,v in [(0xfffffa08,560),(0xfffffa0a,159),(0xfffffa28,80),(0xfffffa36,0)]:c.move_w(v,a)
 c.move_w(cfg['base']>>16,0xfffffa00);c.move_w(cfg['base']&65535,0xfffffa02)
 for a,v in [(0xfffffa05,cfg['stride']),(0xfffffa20,8+{1:0,2:1,4:2}[cfg['bpp']]),(0xfffffa21,0),(0xfffffa23,0),(0xfffffa25,3),(0xfffffa2d,cfg['pan']),(0xfffffa33,0x84),(0xfffffa38,0),(0xfffffa39,0x62)]:c.move_b(v,a)
 c.move_w(0,0xfffffa18);c.move_b(0x7f,0xfffffa1f);c.move_b(0x82,0xfffffa27)

def stage(c,n):c.move_w(n,MARKER+2);wait(c,8192)

def build(mode):
 cfg=mode_config(mode);c=Code();c.w(0x46fc,0x2700);c.move_w(0,0xfffffb0a)
 if mode=='watchdog':
  c.w(0x3039);c.l(MARKER);c.w(0x0c40,0x5a5a,0x6606);c.jump('after_reset')
 for i in range(64):c.move_w(0,MARKER+2*i)
 if mode in ['ram8','ram16']:
  c.move_w(0x0040,0xfffff10a);c.move_w(0x0283,0xfffff116)
 if mode=='ram16':c.move_w(0xa55a,0x430002)
 # Reset and masks/byte lanes are checked by instructions before display enable.
 check(c,0xfffffa28,0xff);check(c,0xfffffa36,0)
 c.w(0x1039);c.l(0xfffffa39);c.w(0x0240,255);c.expect(0x62)
 c.move_w(65535,0xfffffa08);check(c,0xfffffa08,0x3f0)
 c.move_b(0x01,0xfffffa08);c.move_b(0x23,0xfffffa09);check(c,0xfffffa08,0x120)
 c.move_w(65535,0xfffffa28);check(c,0xfffffa28,1023)
 c.move_w(65535,0xfffffa36);check(c,0xfffffa36,0x7ff)
 c.move_w(0,0xfffffa36);c.move_w(0x3001,0xfffffa02);check(c,0xfffffa02,0x3000)
 fill(c,cfg);regs(c,cfg)
 if mode=='ram8':check(c,0xe30002,0x0123)
 if mode=='ram16':check(c,0x430002,0xa55a);check(c,0xc30002,0x0123)
 if mode.startswith('palette'):c.move_b(int(mode[7:],16)*17,0xfffffa33)
 if mode in ['bus1','bus2','bus8']:c.move_b({1:0,2:4,8:12}[int(mode[3:])]+2,0xfffffa20)
 stage(c,1)
 if mode=='lanes':
  c.move_w(0xffff,0xfffffa38);check(c,0xfffffa38,0x80f7)
  c.move_b(0x62,0xfffffa39);check(c,0xfffffa38,0x8062)
  c.move_b(0,0xfffffa38);check(c,0xfffffa38,0x0062)
 if mode=='timing':
  c.move_b(0,0xfffff413)
  def edge():
   for v in [0,16]:
    label=c.unique();c.label(label);c.w(0x1039);c.l(0xfffff411);c.w(0x0240,16,0x0c40,v,0x6706);c.jump(label)
  edge();c.w(0x3039);c.l(0xfffff608);c.record(MARKER+0x30)
  for _ in range(3):edge()
  c.w(0x3039);c.l(0xfffff608);c.w(0x9079);c.l(MARKER+0x30);c.record(MARKER+0x32)
 if mode in ['dynamic','live','clock','self-refresh','off','save','cursor','blink','polarity','dma','pins','contrast','contrast-line','contrast-pixel','mux','acd-line','acd-frame','cursor2','watchdog','sleep','sleep-save']:
  if mode=='dynamic':
   for n,bpp in [(2,1),(3,2),(4,4)]:
    c.move_b(0,0xfffffa27);cfg=mode_config('bpp'+str(bpp));fill(c,cfg);regs(c,cfg);stage(c,n)
  elif mode=='live':fill(c,cfg,15);stage(c,2)
  elif mode=='clock':
   c.move_b(7,0xfffffa25);stage(c,2)
   c.move_w(0x2747,0xfffff202);stage(c,3)
   c.move_w(0x2c93,0xfffff200);stage(c,4)
  elif mode=='self-refresh':
   c.move_b(128,0xfffffa38);stage(c,2);fill(c,cfg,15);stage(c,3)
   c.move_b(0,0xfffffa38);stage(c,4)
  elif mode=='off':
   c.move_b(2,0xfffffa27);stage(c,2);c.move_b(0x82,0xfffffa27);stage(c,3)
  elif mode=='save':
   c.move_w(0x5a5a,MARKER);stage(c,2);fill(c,cfg,15);stage(c,3)
  elif mode in ['cursor','blink','cursor2']:
   c.move_w(0x1f1f,0xfffffa1c);c.move_w(4,0xfffffa1a)
   for n,ctrl in [(2,0x4000),(3,0x8000),(4,0xc000),(5,0)]:
    c.move_w(ctrl|7,0xfffffa18);stage(c,n)
   if mode=='blink':c.move_w(0x4007,0xfffffa18);c.move_b(0x80,0xfffffa1f);stage(c,6)
  elif mode=='polarity':
   c.move_b(0,0xfffff413);c.move_b(63,0xfffffa25)
   for v in [0,64]:
    label=c.unique();c.label(label);c.w(0x1039);c.l(0xfffff411);c.w(0x0240,64,0x0c40,v,0x6706);c.jump(label)
   c.w(0x1039);c.l(0xfffff411);c.w(0x3600);c.move_b(15,0xfffffa21)
   c.w(0x1039);c.l(0xfffff411);c.w(0xb740,0x0240,127);c.expect(127);stage(c,2)
  elif mode in ['acd-line','acd-frame']:
   c.move_b(0,0xfffff413);c.move_b(0x83 if mode=='acd-line'else 3,0xfffffa23)
   def edge():
    for v in [0,128]:
     label=c.unique();c.label(label);c.w(0x1039);c.l(0xfffff411);c.w(0x0240,128,0x0c40,v,0x6706);c.jump(label)
   edge();c.w(0x3039);c.l(0xfffff608);c.record(MARKER+0x34)
   for _ in range(64 if mode=='acd-line'else 4):edge()
   c.w(0x3039);c.l(0xfffff608);c.w(0x9079);c.l(MARKER+0x34);c.record(MARKER+0x36);stage(c,2)
  elif mode=='dma':
   for n,v in [(2,0x71),(3,0x26),(4,0x62)]:c.move_b(v,0xfffffa39);stage(c,n)
  elif mode in ['pins','contrast','contrast-line','contrast-pixel','mux']:
   c.move_b(0,0xfffff413) # PCSEL dedicated LCD pins
   if mode.startswith('contrast'):
    c.move_b(0,0xfffff42b);c.move_w({'contrast':0x0580,'contrast-line':0x0180,'contrast-pixel':0x0380}[mode],0xfffffa36)
   if mode=='mux':
    c.move_b(14,0xfffffa20);c.move_b(0xf0,0xfffff440);c.move_b(0xa0,0xfffff441);c.move_b(0xf0,0xfffff443)
    c.w(0x1039);c.l(0xfffff441);c.w(0x0240,0xf0);c.expect(0xa0);c.move_b(0,0xfffff443)
   c.w(0x7400,0x76ff,0x323c,65535);loop=len(c.data)
   c.w(0x1039);c.l(0xfffff429 if mode.startswith('contrast') else 0xfffff441 if mode=='mux' else 0xfffff411)
   c.w(0x8400,0xc600);c.w(0x51c9,(loop-(len(c.data)+2))&65535) # or.b d0,d2; and.b d0,d3
   c.w(0x33c2);c.l(MARKER+0x20);c.w(0x33c3);c.l(MARKER+0x22)
   if mode.startswith('contrast'):
    def edge():
     for v in [0,1]:
      label=c.unique();c.label(label);c.w(0x1039);c.l(0xfffff429);c.w(0x0240,1,0x0c40,v,0x6706);c.jump(label)
    edge();c.w(0x3039);c.l(0xfffff608);c.record(MARKER+0x34)
    for _ in range({'contrast':256,'contrast-line':4,'contrast-pixel':64}[mode]):edge()
    c.w(0x3039);c.l(0xfffff608);c.w(0x9079);c.l(MARKER+0x34);c.record(MARKER+0x36)
   stage(c,2)
  elif mode in ['sleep','sleep-save']:
   from h2_native import timer,vector,enter,leave
   vector(c,6,'lcd_wake');c.move_w(0xfffd,0xfffff306)
   timer(c,0,compare=8192,irq=True,free=False);c.move_w(2,MARKER+2)
   if mode=='sleep-save':c.move_w(0x5a5a,MARKER)
   c.move_w(0x249b,0xfffff200);c.w(0x4e72,0x2000)
   check(c,MARKER+0x28,1);stage(c,3);c.jump('done')
   enter(c,'lcd_wake');c.w(0x3039);c.l(0xfffff60a);c.move_w(0,0xfffff60a);c.move_w(0,0xfffff600)
   c.w(0x5279);c.l(MARKER+0x28);leave(c)
  elif mode=='watchdog':
   c.move_w(0x5a5a,MARKER);c.move_w(1,0xfffffb0a);c.w(0x4e72,0x2700)
   c.label('after_reset');check(c,0xfffffa00,0);check(c,0xfffffa02,0);check(c,0xfffffa28,255);check(c,0xfffffa36,0)
   c.w(0x1039);c.l(0xfffffa27);c.w(0x0240,255);c.expect(0)
   c.w(0x1039);c.l(0xfffffa39);c.w(0x0240,255);c.expect(0x62)
   c.move_w(0,0xfffffb0a);fill(c,cfg);regs(c,cfg);stage(c,2)
 return finish(c)

def expected(mode,st):
 cfg=mode_config(mode)
 if mode=='dynamic':cfg=mode_config('bpp'+str({1:4,2:1,3:2,4:4}[st]))
 bpp=cfg['bpp'];pan=cfg['pan'];palette=int(mode[7:],16)*17 if mode.startswith('palette')else 0x84
 invert=15 if (mode in ['live','save']and st>= (3 if mode=='save'else 2))or(mode=='self-refresh'and st==4)else 0
 out=bytearray()
 for y in range(160):
  for x in range(560):
   v=(x+pan)% (1<<bpp)
   if y&1:v^=(1<<bpp)-1
   v^=invert
   d=(15 if v else 0)if bpp==1 else([0,palette&15,palette>>4,15][v]if bpp==2 else v)
   if mode in ['cursor','blink','cursor2']and 7<=x<38 and 4<=y<35:
    if st==2:d=15
    elif st==3:d=([0,palette&15,palette>>4,15][3-v] if bpp==2 else 15-v)
    elif st==4:d=0
   if mode=='off'and st==2:d=0
   n,q=NUM[d],DEN[d];r=(189*(q-n)+64*n)//q;b=(170*(q-n)+64*n)//q
   out+=struct.pack('<I',0xff000000|r<<16|r<<8|b)
 return bytes(out)

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',required=True);p.add_argument('--case',required=True);p.add_argument('--installed',action='store_true');p.add_argument('--panel',type=int,default=1);a=p.parse_args()
 assert re.fullmatch('[A-Za-z0-9_-]+',a.case);root=Path(__file__).resolve().parents[1];folder=root/'local-evidence/runtime-compare/h4-20261115'/a.case;folder.mkdir(parents=True,exist_ok=False)
 binary=root/('runtime/diag/bin/dana-diag'if a.installed else'runtime/diag/source/danadiagd');cfg=folder/'cfg';cfg.mkdir()
 for n in ['asmdana.cfg','default.cfg']:shutil.copy2(root/'config/palm-uk15'/n,cfg/n)
 path=cfg/'asmdana.cfg';s=path.read_text();s=s.replace('</input>',f'<port tag=":LCD_PANEL" type="CONFIG" mask="3" defvalue="1" value="{a.panel}"/></input>')
 if a.mode in ['ram8','ram16']:
  import xml.etree.ElementTree as ET
  tree=ET.fromstring(s);input_node=tree.find('./system/input');assert input_node is not None
  for node in list(input_node):
   if node.get('tag')==':PHYSRAM':input_node.remove(node)
  ET.SubElement(input_node,'port',tag=':PHYSRAM',type='CONFIG',mask='1',defvalue='1',value='0'if a.mode=='ram8'else'1')
  s=ET.tostring(tree,encoding='unicode')
 path.write_text(s);body=build(a.mode);physical=a.mode in ['ram8','ram16','watchdog']
 image=folder/('seed.bin'if physical else'guest.dana')
 if physical:image.write_bytes(physical_fixture('lcd',body))
 else:
  header=bytearray(64);header[:8]=b'DANARAM1';end=ENTRY+len(body);struct.pack_into('>8I',header,8,ENTRY,ENTRY,len(body),0x1000,0x400000,0x2000,end,end);header[40:60]=hashlib.sha1(body).digest();struct.pack_into('>I',header,60,1);image.write_bytes(header+body)
 image.chmod(0o444);seed=hashlib.sha256(image.read_bytes()).hexdigest()
 lua=r'''local m=manager.machine;local cpu=m.devices[":maincpu"];local b=cpu.spaces.program;local screen=m.screens[":screen"]
local frames=0;local st=-1;local age=0;local samples={};local events={};local saved=false;local loaded=false;local restored=false
local note=emu.add_machine_post_load_notifier(function()restored=true end)
local tap=b:install_write_tap(0x20000,0x2007f,"h4_guest_journal",function(ad,d,mask)
 if #events<150 then events[#events+1]=string.format('{"address":%d,"data":%d,"time":%.12f}',ad,d,m.time:as_double())end
end)
local function out(n)return m.devices[":"].outputs["dana_lcd_"..n]:get()end
emu.register_frame_done(function()
 if not note or not tap then return end;frames=frames+1;local stage=b:read_u16(0x20002);local marker=b:read_u16(0x20000)
 if stage~=st then st=stage;age=0 else age=age+1 end
 if st>0 and age==3 then
  local pixels,w,h=screen:pixels();local f=assert(io.open(FOLDER.."/stage-"..st..".pixels","wb"));f:write(pixels);f:close()
  samples[st]=string.format('{"stage":%d,"time":%.12f,"refresh":%.12f,"frames":%d,"words":%d,"bursts":%d,"faults":%d,"line":%d,"bpp":%d,"pixel_hz":%d,"running":%d,"self_refresh":%d,"panel":%d,"width":%d,"height":%d,"pllcr":%d,"pllfsr":%d,"lpxcd":%d,"lrra":%d}',st,m.time:as_double(),screen.refresh,out("frames"),out("dma_words"),out("dma_bursts"),out("dma_faults"),out("line"),out("bpp"),out("pixel_hz"),out("running"),out("self_refresh"),out("panel_profile"),w,h,b:read_u16(0xfffff200),b:read_u16(0xfffff202),b:read_u8(0xfffffa25),b:read_u16(0xfffffa28))
 end
 if SAVING and marker==0x5a5a and not saved then saved=true;m:save(FOLDER.."/lcd.sta")end
 if SAVING and marker==0xa55a and not loaded then loaded=true;m:load(FOLDER.."/lcd.sta");return end
 if marker==0xdead or(marker==0xa55a and age>4 and (not SAVING or restored))or frames>4000 then
  local list={};for i=1,20 do if samples[i]then list[#list+1]=samples[i]end end
  local f=assert(io.open(FOLDER.."/cpu.json","w"));f:write(string.format('{"marker":%d,"stage":%d,"d0":%d,"pin_or":%d,"pin_and":%d,"frame_ticks":%d,"contrast_ticks":%d,"restored":%s,"samples":[%s],"events":[%s]}',marker,st,b:read_u16(0x20006),b:read_u16(0x20020),b:read_u16(0x20022),b:read_u16(0x20032),b:read_u16(0x20036),tostring(restored),table.concat(list,","),table.concat(events,",")));f:close();m:exit()
 end
end)
'''.replace('FOLDER',json.dumps(str(folder))).replace('SAVING','true'if a.mode in ['save','sleep-save']else'false')
 (folder/'observe.lua').write_text(lua)
 command=[str(binary),'asmdana','-video','none','-sound','none','-nothrottle','-skip_gameinfo','-nowriteconfig','-cfg_directory',str(cfg),'-nvram_directory',str(folder/'nvram'),'-state_directory',str(folder/'states'),'-rom'if physical else'-quickload',str(image),'-autoboot_delay','0','-autoboot_script',str(folder/'observe.lua'),'-log','-oslog']
 env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',TMPDIR=str(folder))
 with(folder/'run.out').open('w')as f:r=subprocess.run(command,cwd=root/'runtime/diag',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 data=json.loads((folder/'cpu.json').read_text())if(folder/'cpu.json').exists()else{};text=(folder/'run.out').read_text()
 ok=data.get('marker')==0xa55a and r.returncode==0 and not any(t in text for t in ['LUA ERROR','Lua error','Error in Lua','PHYSICAL_BLOCKED'])
 checks=[]
 for sample in data.get('samples',[]):
  st=sample['stage'];pixels=(folder/f'stage-{st}.pixels').read_bytes();want=expected(a.mode,st)
  valid=pixels==want if not(a.mode=='blink'and st==6)else pixels in [expected('cursor',1),expected('cursor',2)]
  sample.update(pixels_sha256=hashlib.sha256(pixels).hexdigest(),expected_sha256=hashlib.sha256(want).hexdigest(),pixels_pass=valid)
  cr=sample['pllcr'];fs=sample['pllfsr'];pll=2*(14*((fs&255)+1)+((fs>>8)&15)+1)*32768
  dma=pll/(2 if cr&128 else 1)/(2 if cr&32 else 1);selector=(cr>>11)&7
  hz=dma/(1 if selector>=4 else 2<<selector)/(sample['lpxcd']+1)
  refresh=hz/((12+560+sample['lrra'])*160)
  timing_ok=abs(sample['refresh']/refresh-1)<1e-9
  sample.update(expected_refresh=refresh,timing_pass=timing_ok)
  checks.append(valid and timing_ok and sample['width']==560 and sample['height']==160 and sample['panel']==a.panel and sample['faults']==0)
  if not valid:sample['first_mismatches']=[i//4 for i in range(0,len(pixels),4)if pixels[i:i+4]!=want[i:i+4]][:12]
 required=4 if a.mode in ['dynamic','clock','self-refresh','dma']else 6 if a.mode=='blink'else 5 if a.mode in ['cursor','cursor2']else 3 if a.mode in ['off','save','sleep','sleep-save']else 2 if a.mode in ['live','polarity','pins','contrast','contrast-line','contrast-pixel','mux','acd-line','acd-frame','watchdog']else 1
 ok=ok and len(checks)==required and all(checks)
 if a.mode in ['save','sleep-save']:ok=ok and data.get('restored')
 if a.mode=='pins':ok=ok and (data.get('pin_or',0)&0x70)==0x70 and(data.get('pin_and',255)&0x70)==0
 if a.mode.startswith('contrast'):
  ok=ok and(data.get('pin_or',0)&1)==1 and(data.get('pin_and',255)&1)==0
  sample=data['samples'][0];pixel=sample['expected_refresh']*(12+560+sample['lrra'])*160
  source=pixel*(sample['lpxcd']+1)if a.mode=='contrast'else pixel if a.mode=='contrast-pixel'else pixel/(12+560+sample['lrra'])
  cycles={'contrast':256,'contrast-line':4,'contrast-pixel':64}[a.mode];ticks=cycles*256/source*32768
  data['contrast_expected_ticks']=ticks;ok=ok and abs(data.get('contrast_ticks',0)-ticks)<4
 if a.mode in ['acd-line','acd-frame']:
  refresh=data['samples'][0]['expected_refresh'];ticks=32768/refresh*(512/160 if a.mode=='acd-line'else 32)
  data['acd_expected_ticks']=ticks;ok=ok and abs(data.get('contrast_ticks',0)-ticks)<4
 if a.mode=='mux':ok=ok and (data.get('pin_or',0)&0xf0)==0xf0 and (data.get('pin_and',255)&0xf0)==0
 if a.mode=='timing':ok=ok and abs(data.get('frame_ticks',0)-3*32768/data['samples'][0]['refresh'])<4
 if a.mode=='off':ok=ok and data['samples'][1]['running']==0
 if a.mode=='self-refresh':ok=ok and data['samples'][1]['self_refresh']==1 and data['samples'][2]['self_refresh']==1 and data['samples'][1]['words']==data['samples'][2]['words']
 data.update(mode=a.mode,panel=a.panel,installed=a.installed,returncode=r.returncode,seed_preserved=seed==hashlib.sha256(image.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),pass_=bool(ok))
 (folder/'result.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({k:v for k,v in data.items()if k!='events'}),flush=True)
 if not ok:print(text[-2500:]);raise SystemExit(1)
if __name__=='__main__':main()
