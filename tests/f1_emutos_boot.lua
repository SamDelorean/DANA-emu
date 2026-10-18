-- SPDX-License-Identifier: BSD-3-Clause
-- Observations only. Native quickload owns initialization and native CPU reset.
local cfg=dofile(assert(os.getenv('DANA_F1_CONFIG')))
local cpu,space,ready,done,first=false,false,false,false,false
local events,taps,subscriptions={}, {}, {}
local bytes,host=0,false
local function encode(x)
    if type(x)=='string' then return string.format('%q',x):gsub('\\\n','\\n') end
    if type(x)=='number' or type(x)=='boolean' then return tostring(x) end
    if type(x)=='table' then
        local out={}
        if #x>0 then for _,v in ipairs(x) do out[#out+1]=encode(v) end;return '['..table.concat(out,',')..']' end
        local keys={};for k in pairs(x) do keys[#keys+1]=k end;table.sort(keys)
        for _,k in ipairs(keys) do out[#out+1]=encode(k)..':'..encode(x[k]) end
        return '{'..table.concat(out,',')..'}'
    end
    return 'null'
end
local function state()
    local s={}
    for _,k in ipairs({'CURPC','PC','SR','SP','IR','D0','D1','D2','D3','A0'}) do s[k]=cpu.state[k].value end
    return s
end
local function finish(reason,dependency)
    if done then return end;done=true;host=true
    if cpu and cpu.debug then manager.machine.debugger:command('trace off') end
    local result={schema='dana-f1-observation-v1',reason=reason,dependency=dependency,
        first_instruction=first,events=events,final=cpu and state() or {},
        virtual_seconds=emu.time(),package_sha256=cfg.package_sha256,binary_sha256=cfg.binary_sha256}
    local f=assert(io.open(cfg.output..'/observation.json','w'));f:write(encode(result),'\n');f:close()
    if space then
        local stack=cpu.state.SP.value
        local dump=assert(io.open(cfg.output..'/stack.hex','w'))
        if stack>=0 and stack+64<=0x400000 then
            for addr=stack,stack+63 do dump:write(string.format('%02x',space:read_u8(addr))) end
        end
        dump:close()
    end
    manager.machine:exit()
end
local function record(e)
    if done then return end
    e.seq=#events;e.origin='cpu';e.virtual_seconds=emu.time();e.state=state()
    local n=#encode(e)
    if #events>=20000 or bytes+n>4*1024*1024 then finish('BLOCKED_TRACE_BUDGET');return end
    events[#events+1]=e;bytes=bytes+n
end
local function safe(f)
    return function(...)
        local ok,err=pcall(f,...)
        if not ok then finish('BLOCKED_HARNESS: '..tostring(err)) end
    end
end
local function loaded()
    return ready:get()~=0
end
local function implemented(address,kind)
    -- The VZ-specific PLLFSR word is now genuinely decoded in the driver.
    -- Do not mistake this register for a missing peripheral. Other 0xF2xx
    -- addresses (including PLLCR) remain real dependencies if accessed.
    return (address>=0xfffff202 and address<=0xfffff203)
        or address==0xfffff300 or (address>=0xfffff302 and address<=0xfffff307)
        or (address>=0xfffff30c and address<=0xfffff30f)
        or (kind=='read' and address>=0xfffff310 and address<=0xfffff313)
end
emu.register_prestart(safe(function()
    cpu=manager.machine.devices[':maincpu'];space=cpu.spaces['program']
    ready=manager.machine.devices[':']:output('dana_guest_loaded')
    assert(cpu.debug and manager.machine.debugger,'Native debugger required')
    manager.machine.debugger.visible_cpu=cpu
    -- Before quickload runs there must be no CPU instruction. The production
    -- driver suspends a mounted guest until complete validation and RAM seed.
    cpu.debug:bpclear();cpu.debug:bpset(cfg.symbols._os_header,'','')
    for _,kind in ipairs({'read','write'}) do
        taps[#taps+1]=space['install_'..kind..'_tap'](space,0,0xffffffff,'f1_'..kind,function(address,data,mask)
            if done or host then return end
            if not loaded() then return end -- Native loader writes are not CPU evidence.
            if address<0x800 or address>=0x400000 then
                record({kind=kind,address=address,data=data,mask=mask})
                if address>=0x400000 and not implemented(address,kind) then
                    finish(address>=0xfffff000 and 'BLOCKED_HARDWARE' or 'FAIL_GUEST_ADDRESS',{address=address,kind=kind,data=data,mask=mask,state=state()})
                end
            end
            -- No replacement data, no PC/register/memory mutation.
        end)
    end
    manager.machine.debugger:command('trace "'..cfg.output..'/guest.trace"')
end))
-- Same notifier API used by the independently qualified RAM harness. Its
-- presence is not a bootstrap gate; ordered native reset bus evidence is.
subscriptions[#subscriptions+1]=emu.add_machine_reset_notifier(safe(function()
    if cpu then cpu.debug:go(0xffffffff) end
end))
emu.register_periodic(safe(function()
    if done or not cpu then return end
    -- Stop native instruction recording at a bounded prefix; continue genuine
    -- execution and retain milestone/MMIO snapshots (explicit trace sampling).
    if not cfg.trace_stopped then
        local f=io.open(cfg.output..'/guest.trace','rb')
        if f then
            local size=f:seek('end');f:close()
            if size>512*1024 then
                manager.machine.debugger:command('trace off');cfg.trace_stopped=true
                record({kind='instruction_trace_sampling_end',byte_threshold=512*1024})
            end
        end
    end
    if emu.time()>5 then finish('BLOCKED_VIRTUAL_BUDGET');return end
    if manager.machine.debugger.execution_state~='stop' then return end
    host=true
    local s=state()
    if not first then
        assert(loaded(),'CPU stopped before native guest load')
        assert(s.CURPC==cfg.symbols._os_header and s.SP==cfg.symbols._stktop and s.SR==0x2700,
               'BLOCKED_BOOTSTRAP: wrong first instruction state')
        local f=assert(io.open(cfg.output..'/initial-image.bin','wb'))
        for start=cfg.symbols.__text,cfg.symbols.__text+cfg.image_length-1,4096 do
            local chunk={}
            for addr=start,math.min(start+4095,cfg.symbols.__text+cfg.image_length-1) do
                chunk[#chunk+1]=string.char(space:read_u8(addr))
            end
            f:write(table.concat(chunk))
        end
        f:close();first=s
        record({kind='first_instruction'})
        cpu.debug:bpclear()
        for _,name in ipairs({'_main','_realmain','meminit','_biosmain','_dana_init'}) do
            local pc=cfg.symbols[name]
            if pc and pc~=cfg.symbols._os_header then cpu.debug:bpset(pc,'','') end
        end
    else
        record({kind='milestone',pc=s.CURPC})
        -- A one-shot breakpoint: do not stall each iteration at the same PC.
        for index,bp in pairs(cpu.debug:bplist()) do if bp.address==s.CURPC then cpu.debug:bpclear(index) end end
    end
    host=false;cpu.debug:go(0xffffffff)
end))
