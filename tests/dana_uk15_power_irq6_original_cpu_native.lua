-- UK1.5 original CPU: genuine VZ SDIRQ polarity, native STOP, hardware power-key IRQ6.
-- Uses canonical single DANA-emu DIAG, unchanged private UK1.5 ROM, genuine ST key event.
-- No register writes, RAM patches, fake IRQs, or independent emulator build.
-- Requires explicit scratch MAME cfg: NOR_PROFILE=1, NOR_FACTORY=1, SDIRQ PD2/3=0.
-- Environment DANA_TRACE_FILE=/.../power_irq6_result.log
local m=manager.machine
local cpu=assert(m.devices[":maincpu"])
local mem=assert(cpu.spaces["program"])
local key=assert(m.ioport.ports[":EXKEY0"]:field(0x00008000))
local sd=assert(m.ioport.ports[":SDIRQ"])
local nor=assert(m.ioport.ports[":NOR_PROFILE"])
local virgin=assert(m.ioport.ports[":NOR_FACTORY"])
local f=assert(io.open(assert(os.getenv("DANA_TRACE_FILE")),"w"))
local frames=0
local saw_stop=false
local saw_post_stop_execution=false
local checkpoints={ [240]=true,[300]=true,[900]=true,[1380]=true,[1400]=true,
 [1590]=true,[1601]=true,[1625]=true,[1800]=true,[2400]=true,[3500]=true }
emu.register_frame_done(function()
 frames=frames+1
 if frames==1 then
  assert((sd:read()&0x0c)==0,"This UK1.5 qualification needs PD2 and PD3 LOW")
  assert((nor:read()&1)==1 and (virgin:read()&1)==1,"Explicit factory NOR diagnostic profiles required")
 end
 if frames==1600 then key:set_value(1);f:write("ORIGINAL_GUEST_POWER_PRESS frame=1600\n") end
 if frames==1624 then key:set_value(0);key:clear_value();f:write("ORIGINAL_GUEST_POWER_RELEASE frame=1624\n") end
 if frames>=1290 and frames<=1590 and cpu.state["CURPC"].value==0x10079776 then saw_stop=true end
 if frames>=1601 and frames<=1800 and cpu.state["CURPC"].value~=0x10079776 then saw_post_stop_execution=true end
 if checkpoints[frames] then
  local pc=cpu.state["CURPC"].value
  local lssa=(mem:read_u16(0xfffffa00)<<16)|mem:read_u16(0xfffffa02)
  local irq=mem:read_u16(0xfffff30e)
  local pd=mem:read_u8(0xfffff419)
  f:write(string.format("F=%d PC=%08X SR=%04X PCTLR=%02X PLLCR=%04X ICR=%04X ISR_LO=%04X PD=%02X LSSA=%08X\n",
    frames,pc,cpu.state["SR"].value,mem:read_u8(0xfffff207),
    mem:read_u16(0xfffff200),mem:read_u16(0xfffff302),irq,pd,lssa))
  if frames==900 then assert((irq&0x0c00)==0,"VZ active-high INT2/INT3 asserted despite both PD inputs LOW and PDPOL=0") end
  f:flush()
 end
 if frames>=3500 then
  key:clear_value()
  assert(saw_stop,"Original UK1.5 never entered first STOP")
  assert(saw_post_stop_execution,"Original UK1.5 did not execute after the physical power press")
  f:write("ORIGINAL_CPU_STOP_TO_WAKE_IRQ6_PASS; PALM_DESKTOP_NOT_ATTESTED\n")
  f:write("END_FRAMES=3500\n")
  f:close();m:exit()
 end
end)
