-- SPDX-License-Identifier: BSD-3-Clause
-- Read-only Time Manager observation; reuses the qualified native PEN sequence.
dofile(assert(os.getenv("DANA_REPO_ROOT")).."/tests/palm_uk15_setup3_click_probe.lua")
local m=manager.machine
local cpu=m.devices[":maincpu"]
local b=cpu.spaces.program
local out=assert(io.open(assert(os.getenv("DANA_CALENDAR_PROBE")),"w"))
local n=0
local function r32(a) return b:read_u16(a)*65536+b:read_u16(a+2) end
local function snapshot(kind,a,d,mask)
 local pc=cpu.state.CURPC.value
 if n>=80 or (kind=="READ" and pc~=0x1007fd26) or (pc<0x1007fc00 or pc>0x10080200) then return end
 n=n+1
 local fp=cpu.state.A6.value
 local tg=r32(0x178)
 out:write(string.format("%s PC=%08X A=%08X DATA=%08X MASK=%04X TG=%08X HOURS=%08X FP=%08X RET=%08X ARG=%08X NVH=%08X NVT=%08X\n",kind,pc,a,d,mask,tg,(tg>0 and tg<0x800000) and r32(tg) or 0,fp,(fp>0 and fp<0x800000) and r32(fp+4) or 0,(fp>0 and fp<0x800000) and r32(fp+8) or 0,(fp>32 and fp<0x800000) and r32(fp-30) or 0,(fp>32 and fp<0x800000) and r32(fp-26) or 0))
 out:flush()
end
local taps={
 b:install_read_tap(0xfffffb00,0xfffffb03,"calendar_clock_read",function(a,d,k)snapshot("READ",a,d,k)end),
 b:install_write_tap(0xfffffb00,0xfffffb03,"calendar_clock_write",function(a,d,k)snapshot("WRITE",a,d,k)end)
}
local frame=0
emu.register_frame_done(function()
 frame=frame+1
 if frame==120 or frame==1800 or frame==3510 or frame==4400 or (DANA_CAPTURE_FRAMES and DANA_CAPTURE_FRAMES[frame]) then
  out:write(string.format("FRAME=%d TG=%08X LOWMEM=",frame,r32(0x178)))
  for a=0xc8,0x120,4 do out:write(string.format("%X:%08X ",a,r32(a)))end
  local table=r32(0x122)
  if table>0 and table<0x800000 then
   for _,t in ipairs({0x3f,0xf5,0xf6,0xfc,0xfd})do out:write(string.format("TRAP_%X=%08X ",t,r32(table+4*t)))end
  end
  out:write(string.format(" HOURS=%08X RTC=%08X CARDS=%08X RAMSTORE=%08X NVH=%08X\n",r32(r32(0x178)),r32(0xfffffb00),r32(0x102),r32(r32(0x102)+28),r32(r32(r32(0x102)+28)+0x4c)));out:flush()
 end
 if frame==(DANA_EXIT_FRAME or 4800) and taps[1] then out:close() end
end)
