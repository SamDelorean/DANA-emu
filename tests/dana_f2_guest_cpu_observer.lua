-- SPDX-License-Identifier: BSD-3-Clause
-- Observe *natural* EmuTOS M68000 pen execution in the sole Dana DIAG.
-- No host program-space accesses, synthetic instruction calls, or MMIO pokes.
-- Source for symbol addresses: exact immutable emutos.map SHA256
-- 17cc980e675e2e1b50e713b9029f6fc3e51d3e55392deb99d53552d4b3af3e68
local output=assert(os.getenv("DANA_F2_GUEST_OBSERVATION"),"F2 guest receipt path missing")
local cpu,space,ready,pen_field=nil,nil,nil,nil
local started,finished,loaded_seen,host_field,pen_injected=false,false,false,false,false
local taps,subs,events={},{},{}
local max_events=20000
local milestones={
    [0x2140]="_os_header",[0x827e]="_dana_init",
    [0x8428]="_dana_kbd_init",[0x852c]="_dana_ts_rawread",
    [0x86a4]="_dana_poll_touchscreen"}
local counts={cpu_pf1_reads=0,cpu_pg2_writes=0,cpu_spi2_reads=0,
              cpu_spi2_writes=0,pen_input_events=0,overflow=0}
local reason="NOT_FINISHED"
local guest_state="NOT_LOADED"
local initial_cpu_pc=nil
-- autoboot_script is invoked by the pinned mame_machine_manager's
-- post-reset timer. It CANNOT rely on a prestart callback already passed.
-- Create an explicit early receipt, so a failed init never looks like
-- missing guest functionality.
local initial_receipt=assert(io.open(output,"wb"))
initial_receipt:write('{"schema":"dana-f2-natural-guest-bus-v1","status":"OBSERVER_LUA_LOADED_NOT_INITIALIZED","origin":"M68000_CPU_TAPS_AND_DEBUGGER_BREAKPOINTS"}\n')
initial_receipt:close()
local function json(v)
    local t=type(v)
    if t=="string" then
        return string.format("%q",v):gsub("\\\n","\\n")
    elseif t=="number" or t=="boolean" then
        return tostring(v)
    elseif t=="table" then
        local a={}
        if #v>0 then
            for _,x in ipairs(v) do a[#a+1]=json(x) end
            return "["..table.concat(a,",").."]"
        end
        local keys={}
        for k in pairs(v) do keys[#keys+1]=k end
        table.sort(keys)
        for _,k in ipairs(keys) do a[#a+1]=json(k)..":"..json(v[k]) end
        return "{"..table.concat(a,",").."}"
    end
    return "null"
end
local function save(final_reason)
    if finished then return end
    finished=true;reason=final_reason
    if pen_field then pcall(function()pen_field:clear_value()end) end
    local res={
        schema="dana-f2-natural-guest-bus-v1",status="CAPTURED",
        origin="M68000_CPU_TAPS_AND_DEBUGGER_BREAKPOINTS",
        natural_execution_only=true,guest_state=guest_state,
        exit_reason=reason,virtual_seconds=emu.time(),
        guest_manifest_map_sha256="17cc980e675e2e1b50e713b9029f6fc3e51d3e55392deb99d53552d4b3af3e68",
        expected_guest_image_sha256="ba590da2661bc582c19bb24d65db04667daf37a17d7aa51fb462b945933ba0a3",
        expected_guest_package_sha256="c201c8527df87fa6a8788d8ac59f43298666196fefeee12dcac68295cb281b9d",
        event_count=#events,counters=counts,
        initialization_cpu_pc=initial_cpu_pc,
        pen_injected_once=pen_injected,
        events=events,
        no_guest_pass_in_lua=true
    }
    local f=assert(io.open(output,"wb"))
    f:write(json(res),"\n");f:close()
end
local function fail(error)
    save("BLOCKED_HARNESS:"..tostring(error))
    manager.machine:exit()
end
local function record(event)
    if finished then return end
    if #events>=max_events then
        counts.overflow=counts.overflow+1
        reason="BLOCKED_EVENT_BUDGET"
        return
    end
    event.seq=#events
    event.time=emu.time()
    events[#events+1]=event
end
local function bytes_for(address,mask)
    -- MAME 16-bit big-endian debugger tap: address is even-aligned,
    -- 0xff00 selects the even byte; 0x00ff selects the following odd byte.
    assert(address%2==0 and (mask==0xff or mask==0xff00 or mask==0xffff),
           "Unexpected native tap mask/word alignment")
    if mask==0xffff then return {address,address+1} end
    if mask==0xff00 then return {address} end
    return {address+1}
end
local function traced(kind,lo,hi)
    taps[#taps+1]=space["install_"..kind.."_tap"](space,lo,hi,"f2_guest_"..kind,
        function(address,data,mask)
            if finished or not ready or ready:get()==0 or host_field
                    or manager.machine:side_effects_disabled() then return end
            local ok,err=pcall(function()
                local selected=bytes_for(address,mask)
                local pc=cpu.state.CURPC.value
                local e={origin="cpu",kind=kind,address=address,
                         data=data,mask=mask,lanes=selected,
                         pc=pc,ir=cpu.state.IR.value,sr=cpu.state.SR.value}
                record(e)
                for _,a in ipairs(selected) do
                    if a==0xfffff429 and kind=="read" then counts.cpu_pf1_reads=counts.cpu_pf1_reads+1 end
                    if a==0xfffff431 and kind=="write" then counts.cpu_pg2_writes=counts.cpu_pg2_writes+1 end
                    if 0xfffff800<=a and a<=0xfffff803 then
                        if kind=="read" then counts.cpu_spi2_reads=counts.cpu_spi2_reads+1
                        else counts.cpu_spi2_writes=counts.cpu_spi2_writes+1 end
                    end
                end
            end)
            if not ok then reason="BLOCKED_TAP:"..tostring(err) end
        end)
end
local function initialize_after_autoboot()
    local ok,err=pcall(function()
        cpu=assert(manager.machine.devices[":maincpu"],"No M68000")
        space=assert(cpu.spaces["program"],"No program space")
        initial_cpu_pc=cpu.state.CURPC.value
        assert(space.data_width==16,"No native 16-bit CPU bus")
        ready=assert(manager.machine.devices[":"]:output("dana_guest_loaded"),
                     "No loader output")
        pen_field=assert(manager.machine.ioport.ports[":PEN"].fields["Dana Stylus Contact"],
                         "No actual pen host input")
        assert(cpu.debug and manager.machine.debugger,"Native debugger unavailable")
        manager.machine.debugger.visible_cpu=cpu
        -- Exact selective ranges, NO host read/write of MMIO registers.
        for _,kind in ipairs({"read","write"}) do
            traced(kind,0xfffff428,0xfffff429) -- PF1/PFDATA
            traced(kind,0xfffff430,0xfffff431) -- PG2/PGDATA
            traced(kind,0xfffff800,0xfffff803) -- SPI2 data/control
        end
        cpu.debug:bpclear()
        for address in pairs(milestones) do cpu.debug:bpset(address,"","") end
        started=true
    end)
    if not ok then fail(err) end
end
subs[#subs+1]=emu.add_machine_reset_notifier(function()
    if cpu and not finished then cpu.debug:go(0xffffffff) end
end)
emu.register_periodic(function()
    if finished then return end
    local ok,err=pcall(function()
        if not started then initialize_after_autoboot() end
        if finished or not started then return end
        if reason:match("^BLOCKED") then save(reason);manager.machine:exit();return end
        local now=emu.time()
        if ready:get()~=0 then loaded_seen=true;guest_state="ORIGINAL_QUICKLOAD_ACTIVE" end
        if loaded_seen and now>=3 and not pen_injected then
            -- Real input field, not a fabricated PF1 CPU bus read.
            host_field=true
            pen_injected=true
            pen_field:set_value(1)
            counts.pen_input_events=counts.pen_input_events+1
            -- Capture the exact host-controlled ADC inputs, but never MMIO.
            local px=assert(manager.machine.ioport.ports[":PENX"],"No PENX")
            local py=assert(manager.machine.ioport.ports[":PENY"],"No PENY")
            record({origin="host_input",kind="PEN_DOWN",value=1,
                    penx_raw=px:read() & 0xffff,peny_raw=py:read() & 0xffff})
            host_field=false
        end
        if manager.machine.debugger.execution_state=="stop" and loaded_seen then
            local pc=cpu.state.CURPC.value
            local label=milestones[pc]
            if label then
                record({origin="debugger_breakpoint",kind="PC_REACHED",
                        label=label,pc=pc,ir=cpu.state.IR.value,sr=cpu.state.SR.value})
                for id,bp in pairs(cpu.debug:bplist()) do
                    if bp.address==pc then cpu.debug:bpclear(id) end
                end
            end
            cpu.debug:go(0xffffffff)
        end
        if now>=12 then
            save(loaded_seen and "OBSERVATION_LIMIT_TIME" or "BLOCKED_GUEST_NOT_LOADED")
            manager.machine:exit()
        end
    end)
    if not ok then fail(err) end
end)
subs[#subs+1]=emu.add_machine_stop_notifier(function()
    if not finished then save("STOP_BEFORE_COMPLETION") end
end)
