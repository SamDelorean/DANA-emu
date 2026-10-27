-- Original UK1.5 MAME bus-level Flash NOR read-only regression.
-- Requires explicitly selected :NOR_PROFILE=1 in test cfg; never patches firmware.
-- Invoke on canonical DIAG with -rom <private-original> -cfg_directory <test_cfg>.
-- Set DANA_TRACE_FILE to an output path. The guest still may not boot Palm OS.
local cpu=assert(manager.machine.devices[":maincpu"])
local bus=assert(cpu.spaces["program"])
local f=assert(io.open(assert(os.getenv("DANA_TRACE_FILE")),"w"))
local frame=0
emu.register_frame_done(function()
 frame=frame+1
 if frame==300 then
  local profile=assert(manager.machine.ioport.ports[":NOR_PROFILE"]):read() & 1
  assert(profile==1,"NOR_PROFILE must be explicitly enabled for this regression")
  local base=0x10000000
  local original=bus:read_u16(base)
  for i=1,3 do bus:write_u8(base,0xff) end
  bus:write_u8(base,0x90)
  local manufacturer,device=bus:read_u16(base),bus:read_u16(base+2)
  f:write(string.format("NOR_IDENTIFICATION manufacturer=%04X device=%04X\n",manufacturer,device))
  assert(manufacturer==0x0020 and device==0x8849,"16-bit NOR identification failed")
  bus:write_u8(base,0xff)
  assert(bus:read_u16(base)==original,"NOR reset did not restore exact ROM")
  bus:write_u8(base,0x70)
  local status=bus:read_u16(base)
  f:write(string.format("NOR_STATUS=%04X\n",status))
  assert(status==0x0080,"NOR status register not ready")
  bus:write_u8(base,0x50)
  bus:write_u8(base,0xff)
  assert(bus:read_u16(base)==original,"NOR clear/reset modified ROM array")
  f:write("NOR_MODEL_NATIVE_READONLY_PASS\n");f:flush()
 end
 if frame>=720 then f:write("END_FRAMES=720\n");f:close();manager.machine:exit() end
end)
