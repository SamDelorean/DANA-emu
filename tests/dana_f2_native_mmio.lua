-- SPDX-License-Identifier: BSD-3-Clause
-- F2 authentic MAME DIAG MMIO exercise, driven by a host Lua observer.
-- These host-origin transactions never masquerade as EmuTOS CPU transactions.
-- Requires -autoboot_script in the ONE existing dana-diag binary.
local output=assert(os.getenv("DANA_F2_MMIO_RESULT"),"Missing result file")
local finished=false
local ticks=0
local pen_field=nil
local pen_port=nil
local space=nil
local phase=0

local function save(status,detail)
    if finished then return end
    finished=true
    if pen_field then pcall(function() pen_field:clear_value() end) end
    local file=assert(io.open(output,"wb"))
    file:write("probe=F2_SINGLE_DIAG_NATIVE_HOST_MMIO\n")
    file:write("origin=HOST_LUA_NOT_GUEST_CPU\n")
    file:write("status=",status,"\n")
    file:write("detail=",tostring(detail):gsub("[\r\n]"," "),"\n")
    file:write("periodic_ticks=",tostring(ticks),"\n")
    file:close()
end

local function mmio_test()
    assert(space and pen_port and pen_field,"probe initialization incomplete")
    assert(space.data_width==16,"native VZ program data bus width not 16")
    local read8=function(address) return space:read_u8(address) end
    local write8=function(address,value) space:write_u8(address,value) end
    local read16=function(address) return space:read_u16(address) end
    local write16=function(address,value) space:write_u16(address,value) end
    assert(read8(0xfffff429)&0x02==0,"PF1 did not assert low on touch")
    assert(read8(0xfffff421)&0x08==0x08,"ST PE3 must stay deasserted")
    assert(read8(0xfffff431)&0x04==0x04,"PG2 ADC must initially be deselected")
    local coords=manager.machine.ioport.ports[":PENX"]
    local coordy=manager.machine.ioport.ports[":PENY"]
    assert(coords and coordy,"missing real pen coordinate input ports")
    local xraw=coords:read()&0xffff
    local yraw=coordy:read()&0xffff
    local expected_x=290+(xraw*3470)//65535
    local expected_y=200+(yraw*3450)//65535
    local function rawread(command)
        -- EXACT EmuTOS sequence, preserving one PG2 selected window:
        -- SPICONT2=0x2247, data cmd, PG2 LOW, XCH 0x2347,
        -- SPIDATA2=0, SPICONT2=0x224F, XCH 0x234F, PG2 HIGH.
        write16(0xfffff802,0x2247)
        write16(0xfffff800,command)
        write8(0xfffff431,read8(0xfffff431)&(~0x04))
        write16(0xfffff802,0x2347)
        assert(read16(0xfffff802)&0x0080==0x0080,"8-bit SPI2 completion absent")
        local idle=read16(0xfffff800)&0xff
        assert(idle==0xff,"pen command phase did not return idle FF")
        write16(0xfffff800,0)
        write16(0xfffff802,0x224f)
        write16(0xfffff802,0x234f)
        assert(read16(0xfffff802)&0x0080==0x0080,"16-bit SPI2 completion absent")
        local result=read16(0xfffff800)
        write8(0xfffff431,read8(0xfffff431)|0x04)
        return result
    end
    local rx=rawread(0x90)
    local ry=rawread(0xd0)
    assert(rx==expected_x*16,string.format("X mismatch expected=%04X got=%04X",expected_x*16,rx))
    assert(ry==expected_y*16,string.format("Y mismatch expected=%04X got=%04X",expected_y*16,ry))
    assert(rawread(0x55)==0xffff,"unknown ADC command emitted a conversion")
    -- Motorola enable=0x0200, XCH=0x0100; speed bit 0x2000 is irrelevant.
    write8(0xfffff431,read8(0xfffff431)&(~0x04))
    write16(0xfffff800,0x90)
    write16(0xfffff802,0x0347)
    assert(read16(0xfffff802)&0x0100==0,"SPI2 legal low-speed transfer not completed")
    assert(read16(0xfffff800)&0xff==0xff,"unexpected low-speed command response")
    write8(0xfffff431,read8(0xfffff431)|0x04)
    assert(read8(0xfffff421)&0x08==0x08,"ST CS perturbed by ADC")
    return string.format("X=%04X,Y=%04X,PG2=separate,PF1=low,SPI2=8+16,rate_independent",rx,ry)
end

emu.register_periodic(function()
    if finished then return end
    ticks=ticks+1
    local ok,err=pcall(function()
        if phase==0 then
            local cpu=assert(manager.machine.devices[":maincpu"],"native 68000 missing")
            space=assert(cpu.spaces["program"],"program MMIO space missing")
            pen_port=assert(manager.machine.ioport.ports[":PEN"],"PEN port missing")
            pen_field=assert(pen_port.fields["Dana Stylus Contact"],"PEN field missing")
            assert((pen_port:read()&1)==0,"pen was not idle at start")
            assert(space:read_u8(0xfffff429)&2==2,"PF1 idle level is not high")
            pen_field:set_value(1)
            phase=1
        elseif phase==1 then
            assert((pen_port:read()&1)==1,"host PEN field was not activated")
            save("PASS_HOST_NATIVE_MMIO_ONLY",mmio_test())
        end
    end)
    if not ok then save("FAIL_HOST_NATIVE_MMIO",err) end
end)

emu.register_stop(function()
    if not finished then save("BLOCKED_NO_NATIVE_PEN_SAMPLE","MAME stopped before two periodic callbacks") end
end)
