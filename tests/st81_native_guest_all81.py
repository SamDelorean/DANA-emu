#!/usr/bin/env python3
"""One real M68000 SPI2 full 81-key fixture, no shortcut MAME reads."""
import importlib.util, json, subprocess, hashlib, os
from pathlib import Path
SRC=Path('/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag/source')
BIN=SRC/'danadiagd'
OUT=Path(os.environ.get('ST81_NATIVE_OUTPUT', '/tmp/DANA_ST81_M68K_ALL81_20261024'))
assert not OUT.exists(), 'Existing evidence, refuse overwrite'
assert hashlib.sha256(BIN.read_bytes()).hexdigest()=='0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a'
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path)
 mod=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(mod)
 return mod
d7=load(SRC/'tests/d7_5_native.py','d7_keyboard_fixture')
runner=load(SRC/'tests/st81_full_keyboard_native.py','st81_inventory')
keys=runner.inventory((SRC/'src/mame/skeleton/alphasdana.cpp').read_text())
assert len(keys)==81 and len(set(row[2] for row in keys))==81
c=d7.Code()
c.move_b(0x40,0xfffff409)
c.move_b(0,0xfffff409)
c.move_b(0,0xfffff421)
c.move_w(0,d7.MARKER+6)  # initialise real guest poll counter
c.label('poll')
c.move_w(0,0xfffff800)
c.move_w(0x2200,0xfffff802)
c.move_w(0x2307,0xfffff802)
c.w(0x3039);c.l(0xfffff800)
# The real M68000 guest records each SPI2 response to RAM independently
# from the passive Lua observer.
c.record(d7.MARKER+4)
c.w(0x5279);c.l(d7.MARKER+6)  # ADDQ.W #1,absolute long
c.w(0x3e3c,127)  # bounded short delay; avoid starving subsequent host frame events
c.label('delay')
c.w(0x51cf,(c.labels['delay']-(d7.ENTRY+len(c.data)+2))&65535)
c.jump('poll')
fixture=c.finish()
OUT.mkdir()
(OUT/'cpu_st81.dana').write_bytes(fixture)
entries=',\n'.join('{tag='+json.dumps(':'+tag)+',name='+json.dumps(name)+',scan='+str(scan)+',mask='+str(mask)+'}' for tag,name,scan,mask in keys)
template=r'''
local machine=manager.machine
local ui=manager.ui
ui.ui_active=false
local cpu=assert(machine.devices[":maincpu"])
local bus=assert(cpu.spaces["program"])
local keys={__ENTRIES__}
local fields={}
for i,k in ipairs(keys) do
 fields[i]=assert(machine.ioport.ports[k.tag].fields[k.name],"Missing "..k.name)
end
local seen,chords={},{}
local frames=0
local last_guest_spi2_frame=0
local host_seen={}
local host_sample_frames=0
local ui_menu_frames=0
local first_menu_frame=0
local ui_active_frames=0
local paused_frames=0
local header_count,release_count,read_count,remaining=0,0,0,0
local guest_last_reply,guest_poll_count=0,0
local buffer={}
local combos={{9,43},{123,109},{114,112},{19,52},{70,11}}
local pairfields={}
for i,pair in ipairs(combos) do
 pairfields[i]={}
 for j,k in ipairs(keys) do
  if k.scan==pair[1] or k.scan==pair[2] then
   pairfields[i][#pairfields[i]+1]=j
  end
 end
 assert(#pairfields[i]==2)
end
local tap=bus:install_read_tap(0xfffff800,0xfffff801,"st81_cpu_spi2",function(offset,data,mask)
 local v=data & 255
 read_count=read_count+1
 last_guest_spi2_frame=frames
 if remaining>0 then
  seen[v]=true
  buffer[#buffer+1]=v
  remaining=remaining-1
  if remaining==0 then
   for i,pair in ipairs(combos) do
    local a,b=false,false
    for _,x in ipairs(buffer) do
     if x==pair[1] then a=true end
     if x==pair[2] then b=true end
    end
    if a and b then chords[i]=true end
   end
  end
 elseif v>=0x40 and v<=0x48 then
  header_count=header_count+1
  remaining=v-0x40
  buffer={}
  if remaining==0 then release_count=release_count+1 end
 end
end)
local first,interval,hold=60,32,19
local first_combo=first+#keys*interval+45
local combo_interval,combo_hold=55,34
local stop=first_combo+#combos*combo_interval+80
local previous,active_combo=0,0
emu.register_frame_done(function()
 frames=frames+1
 if ui.menu_active then
  ui_menu_frames=ui_menu_frames+1
  if first_menu_frame==0 then first_menu_frame=frames end
 end
 if ui.ui_active then ui_active_frames=ui_active_frames+1 end
 if machine.paused then paused_frames=paused_frames+1 end
 if frames>=first and frames<first_combo-45 then
  local idx=math.floor((frames-first)/interval)+1
  local t=(frames-first)%interval
  if previous~=idx and previous>0 then fields[previous]:set_value(0) end
  previous=idx
  if idx<=#keys then
   fields[idx]:set_value(t<hold and 1 or 0)
   if t>3 and t<hold then
    local v=machine.ioport.ports[keys[idx].tag]:read()
    host_sample_frames=host_sample_frames+1
    if (v & keys[idx].mask)~=0 then host_seen[keys[idx].scan]=true end
   end
  end
 elseif frames>=first_combo and frames<stop-80 then
  if previous>0 then fields[previous]:set_value(0);previous=0 end
  local idx=math.floor((frames-first_combo)/combo_interval)+1
  local t=(frames-first_combo)%combo_interval
  if idx~=active_combo and active_combo>0 then
   for _,j in ipairs(pairfields[active_combo]) do fields[j]:set_value(0) end
  end
  active_combo=idx
  if idx<=#combos then
   for _,j in ipairs(pairfields[idx]) do
    fields[j]:set_value(t<combo_hold and 1 or 0)
   end
  end
 elseif frames>=stop-80 then
  if previous>0 then fields[previous]:set_value(0);previous=0 end
  if active_combo>0 then
   for _,j in ipairs(pairfields[active_combo]) do fields[j]:set_value(0) end
   active_combo=0
  end
 end
 if frames>=stop then
  guest_last_reply=bus:read_u16(131076)
  guest_poll_count=bus:read_u16(131078)
  local found,missing,matched={},{},{}
  for _,k in ipairs(keys) do
   if seen[k.scan] then found[#found+1]=k.scan else missing[#missing+1]=k.scan end
  end
  for i=1,#combos do if chords[i] then matched[#matched+1]=i end end
  local host_missing={}
  local host_count=0
  for _,k in ipairs(keys) do
   if host_seen[k.scan] then host_count=host_count+1
   else host_missing[#host_missing+1]=k.scan end
  end
  local out=assert(io.open(__RESULT__,"w"))
  out:write('{"seen":['..table.concat(found,',')..'],"missing":['..
   table.concat(missing,',')..'],"chords":['..table.concat(matched,',')..
   '],"releases":'..release_count..',"headers":'..header_count..
   ',"cpu_spi2_reads":'..read_count..
   ',"last_guest_spi2_frame":'..last_guest_spi2_frame..
   ',"cpu_guest_poll_count_mod65536":'..guest_poll_count..
   ',"cpu_guest_last_spi2_reply":'..guest_last_reply..
   ',"host_seen_count":'..host_count..
   ',"host_missing":['..table.concat(host_missing,',')..']'..
   ',"host_sample_frames":'..host_sample_frames..
   ',"ui_menu_frames":'..ui_menu_frames..
   ',"first_ui_menu_frame":'..first_menu_frame..
   ',"ui_active_frames":'..ui_active_frames..
   ',"paused_frames":'..paused_frames..
   ',"frames":'..frames..'}')
  out:close()
  machine:exit()
 end
end)
'''
(OUT/'keyboard.lua').write_text(template.replace('__ENTRIES__',entries).replace('__RESULT__',json.dumps(str(OUT/'keyboard.json'))))
cmd=[str(BIN),'asmdana','-quickload',str(OUT/'cpu_st81.dana'),
 '-autoboot_script',str(OUT/'keyboard.lua'),'-autoboot_delay','0',
 '-video','none','-sound','none','-nothrottle','-skip_gameinfo','-nowriteconfig','-noui_active','-log','-oslog']
p=subprocess.run(cmd,capture_output=True,text=True,cwd='/tmp',timeout=180)
(OUT/'native.stdout').write_text(p.stdout[-200000:])
(OUT/'native.stderr').write_text(p.stderr[-200000:])
print('ST81_CPU_GUEST_EXIT',p.returncode,flush=True)
if p.returncode or not (OUT/'keyboard.json').is_file():
 print('ST81_NATIVE_STDERR_TAIL',p.stderr[-16000:],flush=True)
 print('ST81_NATIVE_STDOUT_TAIL',p.stdout[-1600:],flush=True)
 raise SystemExit('No valid native CPU guest keyboard result')

j=json.loads((OUT/'keyboard.json').read_text())
j['expected']=81
if j.get('ui_menu_frames', 0)>0:
 j['status']='FAIL_MAME_UI_MENU'
elif j.get('host_seen_count', -1)!=81 or j.get('host_missing'):
 j['status']='FAIL_HOST_KEY_INPUT'
elif j.get('last_guest_spi2_frame',0)<j.get('frames',0)-100:
 j['status']='FAIL_GUEST_POLL_STALL'
elif j.get('cpu_guest_poll_count_mod65536',0)==0:
 j['status']='FAIL_GUEST_CPU_SPI2'
elif len(j['seen'])!=81 or j['missing'] or len(j['chords'])!=5 or j['releases']<81:
 j['status']='FAIL_ST_KEY_PACKETS'
else:
 j['status']='PASS'
(OUT/'keyboard.json').write_text(json.dumps(j,indent=2)+'\n')
print(json.dumps(j,indent=2),flush=True)
if j['status']!='PASS':raise SystemExit(1)
