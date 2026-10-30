-- license:BSD-3-Clause
-- Original ROM UI and ST/pen input only. USB results are never injected.
if _G.DANA_USB_APPLICATION then return end
_G.DANA_USB_APPLICATION=true
local root=assert(os.getenv("DANA_REPO_ROOT"))
local dest=assert(os.getenv("DANA_LCD_DUMP_DIR"))
local mode=os.getenv("DANA_USB_MODE")or"printer"
_G.DANA_PEN_SEQUENCE={{1900,1960,0x8000,0x8000},{2220,2280,0x8000,0x8000},
 {2560,2620,0x0600,0x0c00},{2900,2960,0xf900,0xf300},{3240,3300,0x8000,0x6600},
 {3780,3840,0x7a00,0xf200},{4210,4270,0x7a00,0xf200},{5010,5070,0x8b00,0xf200},
 {5500,5560,0x2200,0x3300}}
if mode=="printer"then
 _G.DANA_PEN_SEQUENCE[9]={5500,5530,0x3a00,0x6b00}
 local clicks={{5800,5830,0x9900,0xec00},{6100,6130,0x7200,0x3e00},
 {6400,6430,0x6900,0xa600},{6700,6730,0x9b00,0xe900},
 {7000,7030,0x8900,0x3300},{7300,7330,0x8d00,0x6200},
 {7600,7630,0x6600,0xf000},{7900,7930,0x6600,0xec00},
 {8200,8230,0x6400,0xe900},{8500,8530,0x2200,0x3300},
 {10000,10030,0x6f80,0xe680}}
 for _,c in ipairs(clicks)do if os.getenv("DANA_USB_INTERACTIVE")~="1"or c[1]<=6100 then _G.DANA_PEN_SEQUENCE[#_G.DANA_PEN_SEQUENCE+1]=c end end
else
 _G.DANA_PEN_SEQUENCE[9]={5500,5560,0x9770,0x3300}
 _G.DANA_PEN_SEQUENCE[#_G.DANA_PEN_SEQUENCE+1]={6100,6160,0x8000,0x8600}
end
_G.DANA_CAPTURE_FRAMES={[3510]=true,[5400]=true,[5800]=true,[6000]=true,[6200]=true,[6400]=true,[6700]=true,[7000]=true,[7400]=true,[7900]=true,[8400]=true,[9000]=true,[9600]=true,[10400]=true,[11200]=true,[12000]=true,[13000]=true,[13800]=true,[14600]=true,[15000]=true,[16000]=true,[18000]=true,[19800]=true}
_G.DANA_EXIT_FRAME=os.getenv("DANA_USB_INTERACTIVE")=="1"and 1000000000 or(mode=="device"and 7000 or 13000)
dofile(root.."/tests/palm_uk15_setup3_click_probe.lua")
local m=manager.machine
local cpu=m.devices[":maincpu"];local b=cpu.spaces.program
local fields={}
for tag,port in pairs(m.ioport.ports)do
 if tag==":KEYS"or tag:match("^:EXKEY")then for name,field in pairs(port.fields)do fields[name]=field end end
end
local events={}
local function key(frame,name,down)events[frame]=events[frame]or{};events[frame][#events[frame]+1]={name,down}end
local function stroke(frame,name)key(frame,name,true);key(frame+3,name,false)end
local words={"D","A","N","A","Space","U","S","B","Space","1","2","3"}
key(8800,"Left shift",true)
for i,name in ipairs(words)do stroke(8810+i*12,name)end
key(8915,"Left shift",false)
-- The original AlphaWord command-P action, through physical ST keys.
key(9500,"Command",true);stroke(9504,"P");key(9510,"Command",false)

if mode=="device"or os.getenv("DANA_USB_INTERACTIVE")=="1"then events={}end
local frame=0
local trace=assert(io.open(dest.."/usb-mmio.txt","w"));local count=0;local late=0
local write_tap=b:install_write_tap(0x1f000000,0x1f000007,"original_usb_writes",function(a,d,k)
 count=count+1
 if (count<=30000 or(frame>=9500 and late<5000))and frame<_G.DANA_EXIT_FRAME-100 then if frame>=9500 then late=late+1 end;trace:write(string.format("F=%d PC=%08X WRITE=%08X DATA=%04X\n",frame,cpu.state.CURPC.value,a,d));trace:flush()end
end)
local read_tap=b:install_read_tap(0x1f000000,0x1f000007,"original_usb_reads",function(a,d,k)
 count=count+1
 if (count<=30000 or(frame>=9500 and late<5000))and frame<_G.DANA_EXIT_FRAME-100 then if frame>=9500 then late=late+1 end;trace:write(string.format("F=%d PC=%08X READ=%08X DATA=%04X\n",frame,cpu.state.CURPC.value,a,d));trace:flush()end
end)
local report=assert(io.open(dest.."/calendar.txt","w"));report:write("Original Palm USB application probe\n");report:close()
emu.register_frame_done(function()
 frame=frame+1
 if not write_tap or not read_tap then return end
 if frame==6600 and os.getenv("DANA_USB_INTERACTIVE")=="1"then m.video.throttled=true end
 if events[frame]then for _,e in ipairs(events[frame])do
  local field=assert(fields[e[1]])
  if e[2]then field:set_value(1)else field:clear_value()end
 end end

 if frame%100==0 then
  local f=assert(io.open(dest.."/progress.json","w"));f:write(string.format('{"frame":%d,"pc":%d,"transactions":%d}',frame,cpu.state.CURPC.value,count));f:close()
 end
 if frame==_G.DANA_EXIT_FRAME-100 then trace:write("TRANSACTIONS="..count.."\n");trace:close()end
end)

-- Optional diagnostic operator: only physical pen/key input and passive LCD capture.
-- No guest RAM writes, Palm traps or USB result injection are used.
if os.getenv("DANA_USB_INTERACTIVE")=="1"then
 local pen=assert(m.ioport.ports[":PEN"]:field(1))
 local px=assert(m.ioport.ports[":PENX"]:field(0xffff))
 local py=assert(m.ioport.ports[":PENY"]:field(0xffff))
 local last=-1;local release=0
 emu.register_frame_done(function()
  if release>0 and frame>=release then pen:clear_value();release=0 end
  local f=io.open(dest.."/operator.lua","r");if not f then return end;f:close()
  local ok,command=pcall(dofile,dest.."/operator.lua")
  if not ok or type(command)~="table"or command.id==last then return end;last=command.id
  if command.x then px:set_value(command.x);py:set_value(command.y);pen:set_value(1);release=frame+30 end
  if command.capture then
   local a=b:read_u32(0xfffffa00);local bytes={}
   for i=a,a+11198,2 do local w=b:read_u16(i);bytes[#bytes+1]=string.char(w>>8,w&255)end
   local out=assert(io.open(dest.."/operator-"..last..".bin","wb"));out:write(table.concat(bytes));out:close()
  end
  if command.exit then m:exit()end
 end)
end
