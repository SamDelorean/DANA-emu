if _G.DANA_CALENDAR_PRESERVATION_STARTED then return end
_G.DANA_CALENDAR_PRESERVATION_STARTED=true
-- SPDX-License-Identifier: BSD-3-Clause
-- Native PEN input changes the date through Palm's original date picker.
-- Emulator save/load/reset exercise persistence; no guest RAM or PC writes.
_G.DANA_PEN_SEQUENCE={{1900,1960,0x8000,0x8000},{2220,2280,0x8000,0x8000},
 {2560,2620,0x0600,0x0c00},{2900,2960,0xf900,0xf300},{3240,3300,0x8000,0x6600},
 {3780,3840,0x8D00,0xA300},{4100,4160,0x8800,0xC000}}
_G.DANA_CAPTURE_FRAMES={[3510]=true,[3900]=true,[4400]=true,[12300]=true,[12900]=true,[13200]=true}
_G.DANA_EXIT_FRAME=13200
dofile(assert(os.getenv("DANA_REPO_ROOT")).."/tests/palm_uk15_host_calendar.lua")
local m=manager.machine
local b=m.devices[":maincpu"].spaces.program
local dest=assert(os.getenv("DANA_LCD_DUMP_DIR"))
local nv_tap=b:install_write_tap(0x8004c,0x80053,"calendar_nv_write",function(a,d,k)
 local f=assert(io.open(dest.."/nv-writes.txt","a"))
 f:write(string.format("TIME=%s PC=%08X A=%08X D=%04X\n",tostring(m.time),m.devices[":maincpu"].state.CURPC.value,a,d));f:close()
end)
local frame=0
local out=assert(io.open(dest.."/preservation.txt","w"))
local function r32(a)return b:read_u16(a)*65536+b:read_u16(a+2)end
emu.register_frame_done(function()
 frame=frame+1
 if frame==4400 or frame==12300 or frame==12900 then
  local tg=r32(0x178)
  local store=r32(r32(0x102)+28)
  local hours=r32(tg)
  out:write(string.format("FRAME=%d HOURS=%08X NVH=%08X RTC=%08X\n",frame,hours,r32(store+0x4c),r32(0xfffffb00)));out:flush()
  assert(hours==0x00106dd0,"Palm-selected 29 October 2026 must survive")
  if frame>4400 then assert(r32(store+0x4c)==hours,"Palm must persist its own date") end
 end
 if frame==10000 then m:save(dest.."/calendar-user.sta") end
 if frame==10300 then m:soft_reset() end
 if frame==12500 then m:load(dest.."/calendar-user.sta") end
 if frame==13200 and nv_tap then out:close() end
end)
