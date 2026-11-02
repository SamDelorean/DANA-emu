-- SPDX-License-Identifier: BSD-3-Clause
-- Reuse original UK1.5 power regression; only observe hardware registers.
local m=manager.machine;local cpu=m.devices[":maincpu"];local b=cpu.spaces.program
local root=assert(os.getenv("DANA_REPO_ROOT"));local dest=assert(os.getenv("DANA_LCD_DUMP_DIR"))
local log=assert(io.open(dest.."/h2-mmio.tsv","w"));local count=0
local tap=b:install_write_tap(0xfffff200,0xfffffb1d,"h2_palm_mmio",function(a,d,k)
 if (a>=0xfffff200 and a<=0xfffff207) or (a>=0xfffffb00 and a<=0xfffffb1d) then
  count=count+1;if count<=256 then log:write(string.format("%.9f %08X %08X %04X %04X\n",m.time:as_double(),cpu.state.CURPC.value,a,d,k));log:flush()end
 end
end)
dofile(root.."/tests/dana_uk15_power_irq6_original_cpu_native.lua")
local frame=0;emu.register_frame_done(function()
 frame=frame+1;if frame==3500 and tap then
  local f=assert(io.open(dest.."/calendar.txt","w"));f:write("Original UK1.5 power regression completed; native assertions in trace.txt\n");f:close();log:close()
 end
end)
