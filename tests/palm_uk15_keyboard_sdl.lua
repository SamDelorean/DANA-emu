-- SPDX-License-Identifier: BSD-3-Clause
-- Passive observation only: host X11/XTest -> SDL -> physical MAME inputs.
if _G.DANA_SDL_OBSERVER then return end
_G.DANA_SDL_OBSERVER=true
local m=manager.machine
local cpu=m.devices[":maincpu"]
local b=cpu.spaces.program
local dest=assert(os.getenv("DANA_LCD_DUMP_DIR"))
local log=assert(io.open(dest.."/sdl-keyboard.txt","w"))
local frames=0
local seen={}
local menus,paused=0,0
local function exists(name)local f=io.open(dest.."/"..name,"r");if f then f:close();return true end return false end
local function capture(name)
 local base=b:read_u16(0xfffffa00)*65536+b:read_u16(0xfffffa02)
 local bytes={}
 for a=base,base+11198,2 do local w=b:read_u16(a);bytes[#bytes+1]=string.char(w>>8,w&255)end
 local f=assert(io.open(dest.."/"..name..".bin","wb"));f:write(table.concat(bytes));f:close()
end
local tap=b:install_read_tap(0xfffff800,0xfffff801,"physical_sdl_keyboard",function(a,d,k)
 if cpu.state.CURPC.value==0x1007e896 then
  seen[d&255]=true;log:write(string.format("FRAME=%d CODE=%02X\n",frames,d&255));log:flush()
 end
end)
emu.register_frame_done(function()
 frames=frames+1
 if manager.ui.menu_active then menus=menus+1 end
 if m.paused then paused=paused+1 end
 if frames==2 then m:load(assert(os.getenv("DANA_KEYBOARD_STATE")))end
 if frames==30 then
  for _,token in ipairs({"UI_MENU","UI_SNAPSHOT","UI_SOFT_RESET"})do
   local t,player=m.ioport:token_to_input_type(token)
   log:write(token.."="..m.input:seq_to_tokens(m.ioport:type_seq(t,player,"standard")).."\n")
  end
 end
 if frames<300 and frames%2==0 then
  for _,token in ipairs({"KEYCODE_H","KEYCODE_A","KEYCODE_F12"})do
   if m.input:code_pressed(m.input:code_from_token(token))then log:write("HOST_RAW "..token.."\n");log:flush()end
  end
 end
 if frames==30 then local f=assert(io.open(dest.."/ready","w"));f:write("ready");f:close()end
 for _,name in ipairs({"phrase","command","dedicated","menu","after-menu","guest-menu"})do
  if exists("capture-"..name)then capture(name);os.remove(dest.."/capture-"..name)end
 end
 if exists("stop")or frames==1800 then
  local keys={};for k in pairs(seen)do keys[#keys+1]=k end;table.sort(keys)
  local f=assert(io.open(dest.."/sdl-result.json","w"))
  f:write('{"frames":'..frames..',"codes":['..table.concat(keys,",")..'],"menu_frames":'..menus..',"paused_frames":'..paused..',"ui_active":'..tostring(manager.ui.ui_active)..'}');f:close()
  if tap then log:close();m:exit()end
 end
end)
