-- Exact original UK1.5 MAME native PCM/IRQ6 wake qualification.
-- No ROM modification and no fake PC/interrupt patch. Run in the
-- canonical single DIAG with explicit test NOR/SDIRQ configuration.
-- The test proves PCM PCEN auto-clear, NOT Palm desktop completion.
local machine=manager.machine
local cpu=assert(machine.devices[":maincpu"])
local program=assert(cpu.spaces["program"])
local onoff=assert(machine.ioport.ports[":EXKEY0"]:field(0x00008000))
local dest=assert(os.getenv("DANA_TRACE_FILE"))
local out=assert(io.open(dest,"w"))
local frame=0
local saw_stop=false
local saw_pcm_release=false
local baseline_rom=program:read_u16(0x10000000)
local function record(label)
 local pc=cpu.state.CURPC.value
 local pctlr=program:read_u8(0xfffff207)
 local pllcr=program:read_u16(0xfffff200)
 local ipr=program:read_u16(0xfffff310)*65536+program:read_u16(0xfffff312)
 local lcd=program:read_u16(0xfffffa00)*65536+program:read_u16(0xfffffa02)
 out:write(string.format("%s frame=%d pc=%08X pctlr=%02X pllcr=%04X ipr=%08X lcd=%08X\n",
    label,frame,pc,pctlr,pllcr,ipr,lcd));out:flush()
 return pc,pctlr,pllcr,lcd
end
emu.register_frame_done(function()
 frame=frame+1
 if frame==1500 then
  local pc,pctlr=record("BEFORE_POWER")
  assert(pc==0x10079776 and pctlr==0x80,
    "The original guest has not reached the known STOP/PCM precondition")
  saw_stop=true
 end
 if frame==1600 then
  onoff:set_value(1);out:write("POWER_PRESS\n")
 end
 if frame==1624 then
  onoff:clear_value();out:write("POWER_RELEASE\n")
 end
 if frame==1800 then
  local pc,pctlr,pllcr=record("AFTER_POWER")
  assert(saw_stop,"No qualifying original STOP observed")
  assert(pc==0x1007a19a and pctlr==0x00,
    "PCM PCEN did not auto-clear on actual guest wake-up")
  assert(pllcr==0x238b,
    "The original firmware power state changed: requalify test")
  saw_pcm_release=true
 end
 if frame==2400 then
  local pc,pctlr,_,lcd=record("END")
  assert(saw_pcm_release and pctlr==0x00,"PCM post-wake regression")
  assert(program:read_u16(0x10000000)==baseline_rom,
    "The original ROM array content was modified")
  out:write("PCM_PCEN_GUEST_WAKE_PASS\n")
  if lcd==0x00072a10 then
   out:write("PALM_DESKTOP_NOT_REACHED\n")
  end
  out:close();machine:exit()
 end
end)
