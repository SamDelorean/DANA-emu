-- Native CPU/GPIO/SPI2 observer: one deliberate input event AFTER Setup 1 of 4.
-- No guest PC alteration, no forced IRQ, no fabricated user acceptance.
local m=manager.machine
local cpu=assert(m.devices[":maincpu"])
local b=assert(cpu.spaces.program)
local pen=assert(m.ioport.ports[":PEN"]:field(1))
local x=assert(m.ioport.ports[":PENX"]:field(0xffff))
local y=assert(m.ioport.ports[":PENY"]:field(0xffff))
local f=assert(io.open(assert(os.getenv("DANA_TRACE_FILE")),"w"))
local frame=0
local marks={[1400]=true,[1700]=true,[1799]=true,[1800]=true,[1900]=true,[1901]=true,[1902]=true,[1905]=true,[1910]=true,[1920]=true,[1930]=true,[1945]=true,[1960]=true,[1980]=true,[2000]=true,[2100]=true,[2400]=true,[2600]=true}
local function state()
 local lcd=b:read_u16(0xfffffa00)*65536+b:read_u16(0xfffffa02)
 local hash=2166136261
 for p=lcd,lcd+11198,2 do hash=((hash ~ b:read_u16(p))*16777619)&0xffffffff end
 return string.format("F=%d PEN=%d PC=%08X SR=%04X PCTLR=%02X IRQ=%08X MASK=%08X ICR=%04X PF DIR=%02X DATA=%02X SEL=%02X PG DIR=%02X DATA=%02X SEL=%02X SPI2=%04X/%04X LCD=%08X HASH=%08X",
frame,m.ioport.ports[":PEN"]:read() & 1,cpu.state.CURPC.value,cpu.state.SR.value,b:read_u8(0xfffff207),
b:read_u16(0xfffff310)*65536+b:read_u16(0xfffff312),
b:read_u16(0xfffff304)*65536+b:read_u16(0xfffff306),b:read_u16(0xfffff302),
b:read_u8(0xfffff428),b:read_u8(0xfffff429),b:read_u8(0xfffff42b),
b:read_u8(0xfffff430),b:read_u8(0xfffff431),b:read_u8(0xfffff433),
b:read_u16(0xfffff802),b:read_u16(0xfffff800),lcd,hash)
end
emu.register_frame_done(function()
 frame=frame+1
 if frame==1900 then x:set_value(0x8000);y:set_value(0x8000);pen:set_value(1);f:write("PEN_DOWN\n") end
 if frame==1960 then pen:clear_value();f:write("PEN_UP\n") end
 if marks[frame] then f:write(state().."\n");f:flush() end
 if frame==1799 or frame==2000 or frame==2400 then
   local base=b:read_u16(0xfffffa00)*65536+b:read_u16(0xfffffa02)
   local buf={}
   for addr=base,base+11198,2 do
     local w=b:read_u16(addr)
     buf[#buf+1]=string.char((w>>8)&255,w&255)
   end
   local out=assert(io.open(string.format("%s/touch_%04d.bin",assert(os.getenv("DANA_LCD_DUMP_DIR")),frame),"wb"))
   out:write(table.concat(buf));out:close()
 end
 if frame==2600 then f:write("DONE\n");f:close();m:exit() end
end)
