-- Native MAME ISP1161 HC bus/PTD regression (manufacturer Rev03).
-- One 8-byte IN PTD with no downstream USB device. Genuine chip must
-- produce DeviceNotResponding (CC=5), not fabricated data or a USB gadget.
local cpu=assert(manager.machine.devices[':maincpu'])
local mem=cpu.spaces['program']
local f=assert(io.open(assert(os.getenv('DANA_PALM_TRACE')),'w'))
local function cmd(x) mem:write_u16(0x1f000002,x) end
local function data(x) mem:write_u16(0x1f000000,x) end
local function read() return mem:read_u16(0x1f000000) end
local function check(n,x,y)
 f:write(string.format('%s got=%04x expect=%04x\n',n,x,y));f:flush()
 if x~=y then error('PTD fail '..n) end
end
local phase=0;local frames=0
emu.register_frame_done(function()
 frames=frames+1
 if phase==0 then
  cmd(0xab);data(0x40)  -- HC ATL partition
  cmd(0xa2);data(16)    -- 8-byte PTD plus 8-byte payload
  cmd(0xc1)
  data(0x0800) -- Actual=0, Active=1
  data(0x0808) -- MPS=8, Last PTD
  data(0x0808) -- Total=8, IN PID
  data(0)      -- USB address=0
  for i=1,4 do data(0) end
  cmd(0x2c);check('ATL_FULL_UPLOAD',read()&4,4)
  cmd(0x81);data(0x0080);data(0) -- HC operational
  phase=1
 elseif phase==1 and frames>=5 then
  cmd(0x2c);local status=read()
  check('ATL_DONE_AFTER_FRAME',status&0x20,0x20)
  check('ATL_NOT_FULL',status&0x04,0)
  cmd(0xa2);data(16)
  cmd(0x41)
  check('PTD_DISCONNECTED_CC5',read(),0x5000)
  check('PTD_MPS_LAST_UNCHANGED',read(),0x0808)
  check('PTD_LENGTH_PID_UNCHANGED',read(),0x0808)
  check('PTD_ADDR_UNCHANGED',read(),0)
  f:write('ISP1161_HC_PTD_NATIVE_BUS_PASS frame='..frames..'\n')
  f:flush();phase=2;manager.machine:exit()
 elseif frames>=30 then error('PTD SOF timeout') end
end)
