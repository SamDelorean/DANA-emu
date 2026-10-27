-- CPU bus MMIO regression: the 16-bit SPI1 shift-engine must complete XCH
-- regardless of PJSEL routing. No SD images mounted / no ROM mutation.
local cpu=assert(manager.machine.devices[':maincpu'])
local bus=assert(cpu.spaces['program'])
local out=assert(io.open(assert(os.getenv('DANA_TRACE_FILE')),'w'))
local frame=0
local function trigger(pj)
 bus:write_u8(0xfffff43b,pj)
 bus:write_u16(0xfffff704,0x063f) -- master, SPIEN, 16 bits, mode3, no XCH
 bus:write_u16(0xfffff702,0xa5a5) -- TX FIFO
 bus:write_u16(0xfffff704,0x073f) -- initiate XCH
end
emu.register_frame_done(function()
 frame=frame+1
 if frame==300 then
  trigger(0xcf) -- SPI1 GPIO-multiplexed, no external serial bits
  out:write('GPIO_MUX_XCH_START\n');out:flush()
 elseif frame==305 then
  local ctrl=bus:read_u16(0xfffff704)
  local rx=bus:read_u16(0xfffff700)
  out:write(string.format('GPIO_MUX_COMPLETE ctrl=%04X rx=%04X\n',ctrl,rx))
  assert(ctrl&0x0100==0,'GPIO-selected SPI1 did not complete')
  assert(rx==0xffff,'GPIO-disconnected default MISO was not high')
  trigger(0xc8) -- PJ0, PJ1, PJ2 dedicated SPI; no external SD media
 elseif frame==310 then
  local ctrl=bus:read_u16(0xfffff704)
  local rx=bus:read_u16(0xfffff700)
  out:write(string.format('DEDICATED_MUX_COMPLETE ctrl=%04X rx=%04X\n',ctrl,rx))
  assert(ctrl&0x0100==0,'dedicated SPI1 did not complete')
  assert(rx==0xffff,'unselected SD idle bus is not high')
  out:write('SPI1_INTERNAL_XCH_AND_ISOLATION_PASS\n');out:flush()
 elseif frame==450 then
  out:write('END_FRAME=450\n');out:close();manager.machine:exit()
 end
end)
