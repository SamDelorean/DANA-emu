-- SPDX-License-Identifier: BSD-3-Clause
-- Passive original IRQ1 vector observation from the qualified guest state.
local m=manager.machine
local b=m.devices[":maincpu"].spaces.program
local dest=assert(os.getenv("DANA_LCD_DUMP_DIR"))
local frame=0
emu.register_frame_done(function()
 frame=frame+1
 if frame==10 then m:load(assert(os.getenv("DANA_KEYBOARD_STATE")))end
 if frame==40 then
  local ivr=b:read_u8(0xfffff300)
  local vector=ivr|1
  local address=vector*4
  local target=b:read_u16(address)*65536+b:read_u16(address+2)
  local table=b:read_u16(0x122)*65536+b:read_u16(0x124)
  local impl=b:read_u16(table+0x944)*65536+b:read_u16(table+0x946)
  local out=assert(io.open(dest.."/calendar.txt","w"))
  out:write(string.format("IVR=%02X IRQ1_VECTOR=%02X HANDLER=%08X IMPLEMENTATION=%08X\n",ivr,vector,target,impl));out:close()
  local out=assert(io.open(dest.."/vector.txt","w"));out:write(string.format("%08X %08X\n",target,impl));out:close()
 end
 if frame==50 then m:exit()end
end)
