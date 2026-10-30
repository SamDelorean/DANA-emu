-- SPDX-License-Identifier: BSD-3-Clause
-- Original UK1.5 and AlphaWord. All keys enter via MAME physical input fields.
if _G.DANA_KEYBOARD_CAMPAIGN_STARTED then return end
_G.DANA_KEYBOARD_CAMPAIGN_STARTED=true
local root=assert(os.getenv("DANA_REPO_ROOT"))
local dest=assert(os.getenv("DANA_LCD_DUMP_DIR"))
_G.DANA_PEN_SEQUENCE={{1900,1960,0x8000,0x8000},{2220,2280,0x8000,0x8000},
 {2560,2620,0x0600,0x0c00},{2900,2960,0xf900,0xf300},{3240,3300,0x8000,0x6600},
 {3780,3840,0x7a00,0xf200},{4210,4270,0x7a00,0xf200},{5010,5070,0x8b00,0xf200},
 {5500,5560,0x2200,0x3300}}
_G.DANA_CAPTURE_FRAMES={[3510]=true,[5800]=true,[7000]=true,[7110]=true,[7190]=true,[7230]=true,[7280]=true,[7310]=true,[7400]=true,[7900]=true,[8300]=true,[9000]=true}
_G.DANA_EXIT_FRAME=9000
dofile(root.."/tests/palm_uk15_setup3_click_probe.lua")
local m=manager.machine
local cpu=m.devices[":maincpu"]
local b=cpu.spaces.program
local out=assert(io.open(dest.."/keyboard.txt","w"))
local c=assert(io.open(dest.."/calendar.txt","w"))
c:write("Original Palm keyboard qualification; passive SPI2/IRQ1 observer.\n");c:close()
local fields={}
for tag,port in pairs(m.ioport.ports)do
 for name,field in pairs(port.fields)do
  if tag==":KEYS" or tag:match("^:EXKEY")then fields[name]=field end
 end
end
local events={}
local function key(frame,name,down)
 events[frame]=events[frame]or{}
 events[frame][#events[frame]+1]={name,down}
end
local function stroke(frame,name)
 key(frame,name,true);key(frame+3,name,false)
end
local phrase={"A","B","C","Space","Left shift","D","A","N","A","Left shift","Space","1","2","3",".","/"}
-- Modifiers are held around their dependent physical keys.
stroke(6000,"A");stroke(6012,"B");stroke(6024,"C");stroke(6036,"Space")
key(6048,"Left shift",true)
stroke(6052,"D");stroke(6064,"A");stroke(6076,"N");stroke(6088,"A")
key(6095,"Left shift",false)
stroke(6110,"Space");stroke(6122,"1");stroke(6134,"2");stroke(6146,"3")
stroke(6158,".");key(6170,"Right shift",true);stroke(6174,"/");key(6180,"Right shift",false)
-- Check editing, both physical Enter and Delete, and native selection.
stroke(7100,"Return");stroke(7120,"X");stroke(7140,"Backspace")
stroke(7160,"A");stroke(7180,"B");stroke(7200,"Left");stroke(7220,"Delete")
stroke(7600,"Home")
key(7260,"Left shift",true);stroke(7264,"Left");key(7270,"Left shift",false);stroke(7290,"Backspace")
stroke(6500,"Caps lock");stroke(6512,"A");stroke(6524,"Caps lock");stroke(6536,"B")
local frame=0
local headers,releases,codes=0,0,0
local tap=b:install_read_tap(0xfffff800,0xfffff801,"palm_original_keyboard",function(a,d,k)
 local pc=cpu.state.CURPC.value
 if pc==0x1007d6ec then out:write(string.format("ST_VERSION_BYTE=%02X\n",d&255));out:flush()end
 if pc==0x1007e648 or pc==0x1007e896 then
  if pc==0x1007e648 then headers=headers+1;if(d&255)==0x40 then releases=releases+1 end
  else codes=codes+1 end
  out:write(string.format("F=%d PC=%08X DATA=%02X\n",frame,pc,d&255));out:flush()
 end
end)
emu.register_frame_done(function()
 frame=frame+1
 if events[frame]then
  for _,e in ipairs(events[frame])do
   local f=assert(fields[e[1]],"Unmapped "..e[1])
   if e[2]then f:set_value(1)else f:clear_value()end
  end
 end
 if frame==5900 then m:save(dest.."/alphaword-clean.sta")end
 if frame==8500 then m:load(dest.."/alphaword-clean.sta")end
 if frame==8700 then stroke(8710,"A")end
 if frame==9000 and tap then
  out:write(string.format("HEADERS=%d RELEASES=%d CODES=%d\n",headers,releases,codes));out:close()
  assert(headers>20 and releases>15 and codes>20,"Original Palm must consume physical keyboard packets")
 end
end)
