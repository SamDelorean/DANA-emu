-- Evidence for VZ EMUBRK active bootstrap with Motorola B-record payload-0.
-- Requires env DANA_PALM_TRACE=/absolute/path/to/metrics.txt
local cpu=assert(manager.machine.devices[':maincpu'])
local mem=cpu.spaces['program']
local f=assert(io.open(assert(os.getenv('DANA_PALM_TRACE')),'w'))
local frames=0
emu.register_frame_done(function()
 frames=frames+1
 if frames==1 or frames==3 or frames==12 then
  local pc=cpu.state['CURPC'].value
  f:write(string.format('FRAME %d curpc=%08x pc=%08x ibuff=%04x,%04x vec=%08x\n',
    frames,pc,cpu.state['PC'].value,
    mem:read_u16(0x00ffffc0),mem:read_u16(0x00ffffc2),mem:read_u32(4)))
  f:flush()
 end
 if frames>=12 then manager.machine:exit() end
end)
