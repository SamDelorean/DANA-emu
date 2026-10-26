local cpu=assert(manager.machine.devices[':maincpu'])
local bus=cpu.spaces['program']
local logfile=assert(io.open(assert(os.getenv('DANA_PALM_TRACE')),'w'))
local function log(s) logfile:write(s..'\n');logfile:flush() end
local tests=0
local function eq(name,got,want)
 tests=tests+1
 if got~=want then
  log(string.format('FAIL %s got=%04x want=%04x',name,got,want))
  manager.machine:exit(); error(name)
 end
 log(string.format('PASS %s value=%04x',name,got))
end
local function cmdh(val) bus:write_u16(0x1f000002,val) end
local function datah(val) bus:write_u16(0x1f000000,val) end
local function readh() return bus:read_u16(0x1f000000) end
local function cmdd(val) bus:write_u16(0x1f000006,val) end
local function datad(val) bus:write_u16(0x1f000004,val) end
local function readd() return bus:read_u16(0x1f000004) end
local done=false
emu.register_frame_done(function()
 if done then return end
 done=true
 cmdh(0x27); eq('host_chip_id',readh(),0x6123)
 cmdh(0xa8);datah(0x4321)
 cmdh(0x28);eq('host_scratch',readh(),0x4321)
 cmdh(0x00);eq('host_ohci_rev_lo',readh(),0x0010)
 eq('host_ohci_rev_hi',readh(),0)
 cmdh(0xa4); datah(0x0032)
 cmdh(0x24);eq('host_irq_status_idle',readh(),0)
 cmdh(0xa5); datah(0x0032)
 cmdh(0x25);eq('host_irq_enable',readh(),0x32)
 cmdh(0xaa);datah(0x0200)
 cmdh(0xab);datah(0x0200)
 cmdh(0x2a);eq('itl_allocation',readh(),0x0200)
 cmdh(0x2b);eq('atl_allocation',readh(),0x0200)
 -- Exercise the entire indexed 32-bit register transaction, not only ID.
 cmdh(0x92);datah(0x0202);datah(0x1234)
 cmdh(0x12);eq('root_hub_descriptor_low',readh(),0x0202)
 eq('root_hub_descriptor_high',readh(),0x1234)
 cmdh(0x8d);datah(0x2edf);datah(0x2778)
 cmdh(0x0d);eq('frame_interval_low',readh(),0x2edf)
 eq('frame_interval_high',readh(),0x2778)
 -- Hardware RAM PIO preserves words. 2*ITL offset separates ATL/ITL.
 cmdh(0xa2);datah(4)
 cmdh(0xc1);datah(0x3412);datah(0x7856)
 cmdh(0xa2);datah(4)
 cmdh(0x41);eq('atl_fifo_word0',readh(),0x3412)
 eq('atl_fifo_word1',readh(),0x7856)
 cmdh(0x2c);eq('atl_fifo_full_not_done',readh(),0x0004)
 cmdd(0xb0);datad(0xaa37)
 cmdd(0xb2);datad(0x1234)
 cmdd(0xb3);eq('device_scratch',readd(),0x1234)
 cmdd(0xb6);datad(0x0082)
 cmdd(0xb7);eq('device_address',readd(),0x82)
 cmdd(0xb5);eq('device_chip_id',readd(),0x6123)
 cmdd(0xb8);datad(0x0020)
 cmdd(0xb9);eq('device_mode_susp_request',readd(),0x0020)
 cmdd(0xb8);datad(0)
 cmdd(0xb9);eq('device_mode_resume_command',readd(),0)
 cmdd(0xba);datad(0x0f04)
 cmdd(0xbb);eq('device_hardware_configuration',readd(),0x0f04)
 cmdd(0x22);datad(0x0088)
 cmdd(0x32);eq('device_endpoint_configuration',readd(),0x88)
 cmdd(0x52);eq('device_endpoint_status_idle',readd(),0)
 cmdd(0xd2);eq('device_endpoint_status_image',readd(),0)
 cmdd(0xc0);eq('device_irq_low_idle',readd(),0)
 eq('device_irq_high_idle',readd(),0)
 cmdd(0xf0);datad(0x10)
 cmdd(0xf1);eq('device_dma_configuration',readd(),0x10)
 cmdd(0xc2);datad(0x5678);datad(0x0001)
 cmdd(0xc3);eq('device_interrupt_enable_lo',readd(),0x5678)
 eq('device_interrupt_enable_hi',readd(),1)
 -- Independent reset domains.
 cmdh(0xa9);datah(0xf6)
 cmdh(0x28);eq('host_scratch_after_hc_reset',readh(),0)
 cmdd(0xb3);eq('device_scratch_survives_hc_reset',readd(),0x1234)
 cmdh(0xa8);datah(0x9876)
 cmdd(0xf6)
 cmdd(0xb3);eq('device_scratch_after_dc_reset',readd(),0)
 cmdh(0x28);eq('host_scratch_survives_dc_reset',readh(),0x9876)
 log('USB_DIRECTED_TOTAL_PASS='..tests)
 manager.machine:exit()
end)
