-- SPDX-License-Identifier: BSD-3-Clause
-- Native save/restore of a held modifier, repeat, and prolonged original-ROM typing.
if _G.DANA_KEYBOARD_ROBUST then return end
_G.DANA_KEYBOARD_ROBUST=true
local m=manager.machine
local cpu=m.devices[":maincpu"]
local b=cpu.spaces.program
local dest=assert(os.getenv("DANA_LCD_DUMP_DIR"))
local state=assert(os.getenv("DANA_KEYBOARD_STATE"))
local a=m.ioport.ports[":KEYS"].fields["A"]
local other=m.ioport.ports[":KEYS"].fields["B"]
local shift=m.ioport.ports[":EXKEY0"].fields["Left shift"]
local log=assert(io.open(dest.."/robust.txt","w"))
local c=assert(io.open(dest.."/calendar.txt","w"));c:write("Keyboard robustness\n");c:close()
local frame=0
local stale=false
local writes=0
local function capture(name)
 local base=b:read_u16(0xfffffa00)*65536+b:read_u16(0xfffffa02)
 local bytes={}
 for p=base,base+11198,2 do local w=b:read_u16(p);bytes[#bytes+1]=string.char(w>>8,w&255)end
 local f=assert(io.open(dest.."/"..name..".bin","wb"));f:write(table.concat(bytes));f:close()
end
local tap=b:install_read_tap(0xfffff800,0xfffff801,"keyboard_restore_probe",function(addr,data,mask)
 local pc=cpu.state.CURPC.value
 if pc==0x1007e896 then
  writes=writes+1
  local hostshift=(m.ioport.ports[":EXKEY0"]:read()&0x200)~=0
  if frame>160 and frame<260 and data==9 and not hostshift then stale=true end
  log:write(string.format("F=%d CODE=%02X HOST_SHIFT=%u\n",frame,data&255,hostshift and 1 or 0));log:flush()
 end
end)
emu.register_frame_done(function()
 frame=frame+1
 if frame==10 then m:load(state)end
 if frame==100 then shift:set_value(1)end
 if frame==101 then a:set_value(1)end
 if frame==110 then m:save(dest.."/held-modifier.sta")end
 if frame==130 then a:clear_value();shift:clear_value()end
 if frame==160 then m:load(dest.."/held-modifier.sta")end
 if frame==180 then a:set_value(1)end
 if frame==184 then a:clear_value()end
 if frame==190 then other:set_value(1)end
 if frame==194 then other:clear_value()end
 if frame==230 then capture("restore")end
 -- A long press is repeated by Palm OS, not synthesized by the host fixture.
 if frame==300 then m:load(state)end
 if frame==330 then a:set_value(1)end
 if frame==480 then a:clear_value()end
 if frame==500 then capture("repeat")end
 if frame==550 then m:load(state)end
 if frame>=600 and frame<2200 then
  local t=(frame-600)%8
  if t==0 then a:set_value(1)end
  if t==3 then a:clear_value()end
 end
 if frame==2250 then capture("prolonged")end
 if frame==2300 then m:soft_reset()end
 if frame==4000 then a:set_value(1)end
 if frame==4004 then a:clear_value()end
 if frame==4100 then capture("after-reset")end
 if frame==4200 and tap then
  local out=assert(io.open(dest.."/robust.json","w"));out:write('{"stale_modifier":'..tostring(stale)..',"native_codes":'..writes..'}');out:close()
  log:close();m:exit()
  assert(not stale,"Restored ST must reconcile released physical modifiers")
  assert(writes>200,"Prolonged typing must remain live")
 end
end)
