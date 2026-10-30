-- Original ROM native contact and coordinates. No guest injection or GUI shortcuts.
local machine=manager.machine
local bus=assert(machine.devices[":maincpu"].spaces.program)
local pen=assert(machine.ioport.ports[":PEN"]:field(1))
local x=assert(machine.ioport.ports[":PENX"]:field(0xffff))
local y=assert(machine.ioport.ports[":PENY"]:field(0xffff))
local dest=assert(os.getenv("DANA_LCD_DUMP_DIR"))
local trace=assert(io.open(assert(os.getenv("DANA_TRACE_FILE")),"w"))
local sequence={{1900,1960,0x8000,0x8000},{2220,2280,0x8000,0x8000},{2560,2620,0x0600,0x0c00},{2900,2960,0xf900,0xf300},{3240,3300,0x8000,0x6600}}
local frame=0
local function capture()
 local base=bus:read_u16(0xfffffa00)*65536+bus:read_u16(0xfffffa02)
 local buf={},2166136261
 local h=2166136261
 for address=base,base+11198,2 do
  local w=bus:read_u16(address)
  h=((h ~ w)*16777619)&0xffffffff
  buf[#buf+1]=string.char((w>>8)&255,w&255)
 end
 local out=assert(io.open(string.format("%s/calib_%04d.bin",dest,frame),"wb"))
 out:write(table.concat(buf));out:close()
 trace:write(string.format("FRAME=%d HASH=%08X PC=%08X IRQ=%08X X=%04X Y=%04X PEN=%u\n",frame,h,machine.devices[":maincpu"].state.CURPC.value,bus:read_u16(0xfffff310)*65536+bus:read_u16(0xfffff312),machine.ioport.ports[":PENX"]:read(),machine.ioport.ports[":PENY"]:read(),machine.ioport.ports[":PEN"]:read()&1))
 local penstate=bus:read_u16(0x16c)*65536+bus:read_u16(0x16e)
 trace:write(string.format("PENSTATE PTR=%08X FLAG=%02X ",penstate,bus:read_u8(0x253)))
 if penstate>0 and penstate<0x800000 then
  for i=0,0x38,2 do trace:write(string.format("%02X=%04X ",i,bus:read_u16(penstate+i))) end
 end
 trace:write("\n");trace:flush()
end
local caps={[1800]=true,[2080]=true,[2340]=true,[2490]=true,[2570]=true,[2590]=true,[2610]=true,[2690]=true,[2840]=true,[2910]=true,[2930]=true,[2950]=true,[3030]=true,[3180]=true,[3370]=true,[3510]=true,[3710]=true,[3900]=true}
emu.register_frame_done(function()
 frame=frame+1
 for i,evt in ipairs(sequence) do
  if frame==evt[1] then
   x:set_value(evt[3]);y:set_value(evt[4]);pen:set_value(1)
   trace:write(string.format("DOWN=%d X=%04X Y=%04X\n",frame,evt[3],evt[4]))
  end
  if frame==evt[2] then pen:clear_value();trace:write("UP="..frame.."\n") end
 end
 if caps[frame] then capture() end
 if frame==3510 then trace:close();machine:exit() end
end)
