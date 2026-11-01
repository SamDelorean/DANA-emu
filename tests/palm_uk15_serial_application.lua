-- SPDX-License-Identifier: BSD-3-Clause
-- Original UK1.5 Beam action; only physical ST/pen input and passive MMIO taps.
local root=assert(os.getenv("DANA_REPO_ROOT"))
local dest=assert(os.getenv("DANA_LCD_DUMP_DIR"))
_G.DANA_PEN_SEQUENCE={{1900,1960,0x8000,0x8000},{2220,2280,0x8000,0x8000},
 {2560,2620,0x0600,0x0c00},{2900,2960,0xf900,0xf300},{3240,3300,0x8000,0x6600},
 {3780,3840,0x7a00,0xf200},{4210,4270,0x7a00,0xf200},{5010,5070,0x8b00,0xf200},
 {5500,5560,0x2200,0x3300},{7000,7030,0x1000,0x5400},{8300,8330,0x1000,0x7800}}
_G.DANA_CAPTURE_FRAMES={[3510]=true,[5800]=true,[6400]=true,[6700]=true,[7100]=true,[7700]=true,[8400]=true,[7400]=true,[8000]=true,[9000]=true,[11000]=true,[12000]=true}
_G.DANA_EXIT_FRAME=tonumber(os.getenv("DANA_SERIAL_FRAMES")) or 9100
local close_frame=_G.DANA_EXIT_FRAME-100
dofile(root.."/tests/palm_uk15_setup3_click_probe.lua")
local m=manager.machine
local cpu=m.devices[":maincpu"];local b=cpu.spaces.program
local fields={}
for tag,port in pairs(m.ioport.ports)do
 if tag==":KEYS"or tag:match("^:EXKEY")then for name,f in pairs(port.fields)do fields[name]=f end end
end
local f=assert(io.open(dest.."/serial-mmio.txt","w"))
local c=assert(io.open(dest.."/calendar.txt","w"));c:write("Original Palm Beam / UART observation\n");c:close()
local count=0;local frame=0
local function record(kind,a,d,k)
 count=count+1
 if (kind=="WRITE" or (a==0xfffff914 and (d&0x2000)~=0)) and count<=1000000 and frame<close_frame then
  f:write(string.format("FRAME=%d PC=%08X %s=%08X DATA=%04X MASK=%04X\n",frame,cpu.state.CURPC.value,kind,a,d,k));f:flush()
 end
end
local wt=b:install_write_tap(0xfffff900,0xfffff91d,"serial_original_w",function(a,d,k)record("WRITE",a,d,k)end)
local rt=b:install_read_tap(0xfffff900,0xfffff91d,"serial_original_r",function(a,d,k)record("READ",a,d,k)end)
local function press(name,down)local x=assert(fields[name]);if down then x:set_value(1)else x:clear_value()end end
local text={"D","A","N","A","Space","I","R","D","A","Space","1","2","3"}
emu.register_frame_done(function()
 if not wt or not rt then return end
 frame=frame+1
 if frame==6000 then press("Left shift",true)end
 if frame==6125 then press("Left shift",false)end
 for i,name in ipairs(text)do
  if frame==6010+i*12 then press(name,true)end
  if frame==6013+i*12 then press(name,false)end
 end
 if frame>=7310 and frame<=7370 then
  local keys={"I","R","D","O","C"};for i,name in ipairs(keys)do
   if frame==7300+i*12 then press(name,true)end
   if frame==7303+i*12 then press(name,false)end
  end
 end
 if frame==7500 then press("Return",true)end
 if frame==7504 then press("Return",false)end
 if frame==7900 then press("Menu (Undo)",true)end
 if frame==7904 then press("Menu (Undo)",false)end
 if frame==8100 then
  local link=os.getenv("DANA_IR_LINK")
  if not link then local wire=assert(io.open(dest.."/irda-wire.bin","wb"));wire:close();link=dest.."/irda-wire.bin"end
  m.images[":serial1:stream"]:load(link)
  assert(m.images[":serial1:stream"].filename~="","IR stream mount failed")
 end
 if frame==6500 then press("Menu (Undo)",true)end
 if frame==6504 then press("Menu (Undo)",false)end
 if frame==close_frame then f:write("TRANSACTIONS="..count.."\n");f:close()end
end)
