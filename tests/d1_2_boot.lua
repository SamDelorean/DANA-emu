-- SPDX-License-Identifier: BSD-3-Clause
-- Test-only plugin bootstrap, loaded as pluginspath/boot.lua before machine.run.
-- Never install via autoboot_script. No runtime hardware or guest loader code.
local cfg = dofile(assert(os.getenv('DANA_D1_2_CONFIG'), 'Missing test configuration'))
local events, stops, subscriptions, taps = {}, {}, {}, {}
local cpu, space, done, prepared, reset_seen = nil, nil, false, false, false
local origin, trace_bytes, next_stop = 'fixture', 0, 1
local function json(v)
    if type(v) == 'string' then
        return '"' .. v:gsub('\\','\\\\'):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r'):gsub('\t','\\t') .. '"'
    elseif type(v) == 'number' or type(v) == 'boolean' then return tostring(v)
    elseif type(v) == 'table' then
        local out = {}
        if #v > 0 then for _, x in ipairs(v) do out[#out+1] = json(x) end
            return '[' .. table.concat(out, ',') .. ']'
        end
        local keys = {}; for k in pairs(v) do keys[#keys+1] = k end; table.sort(keys)
        for _, k in ipairs(keys) do out[#out+1] = json(k) .. ':' .. json(v[k]) end
        return '{' .. table.concat(out, ',') .. '}'
    end
    return 'null'
end
local function state()
    local result = {}
    for _, k in ipairs({'CURPC','PC','SP','SR','IR','D0','D1','D2','D3','A0'}) do
        result[k] = cpu.state[k].value
    end
    return result
end
local function dump(name)
    local previous = origin; origin = 'host'
    local f = assert(io.open(cfg.output .. '/' .. name .. '.ram', 'wb'))
    for base=0,0x3fffff,4096 do
        local chunk={}; for i=0,4095 do chunk[#chunk+1]=string.char(space:read_u8(base+i)) end
        f:write(table.concat(chunk))
    end
    f:close(); origin = previous
end
local function finish(reason)
    if done then return end
    done = true; origin = 'host'
    local result = {schema='dana-d1-2-observation-v1', case=cfg.case,
        variant=cfg.variant, run=cfg.run, fixture_sha256=cfg.fixture_sha256,
        binary_sha256=cfg.binary_sha256, source_sha=cfg.source_sha,
        bootstrap_prepared=prepared, reset_seen=reset_seen,
        reason=reason, events=events, stops=stops, virtual_seconds=emu.time()}
    if cpu then result.final=state(); if prepared then dump('final') end end
    local f=assert(io.open(cfg.output .. '/observation.json','w')); f:write(json(result),'\n'); f:close()
    manager.machine:exit()
end
local function event(e)
    if done then return end
    e.seq=#events; e.origin=origin; e.schema_version='dana-trace-v1'
    e.case_id=cfg.case; e.variant=cfg.variant; e.run_id=tostring(cfg.run)
    e.vcycle=math.floor(emu.time()*1000000)
    local length=#json(e)
    if #events >= 20000 or trace_bytes+length > 5*1024*1024 then
        finish('EVIDENCE_TRUNCATED'); return
    end
    events[#events+1]=e; trace_bytes=trace_bytes+length
end
local function protect(fn)
    return function(...)
        local ok,err=pcall(fn,...)
        if not ok then finish('BLOCKED_BOOTSTRAP: ' .. tostring(err)) end
    end
end
emu.register_prestart(protect(function()
    if prepared then error('Unexpected second reset') end
    cpu=manager.machine.devices[':maincpu']; space=cpu.spaces['program']
    assert(cpu.debug and manager.machine.debugger, 'Debugger required')
    event({kind='prestart',virtual_seconds=emu.time()})
    -- Entire RAM is cleared before any CPU timeslice; describe bulk host writes.
    for a=0,0x3ffffc,4 do space:write_u32(a,0) end
    event({kind='seed',address=0,length=4194304,value=0})
    for a=0x10000,0x1000f do space:write_u8(a,0xcc) end
    event({kind='seed',address=0x10000,length=16,value=0xcc})
    for _,v in ipairs({{0,0x8000},{4,0x4000},{12,0x5000}}) do
        space:write_u32(v[1],v[2]); event({kind='seed_vector',address=v[1],value=v[2],width=32})
    end
    for _,seed in ipairs({{0x4000,cfg.hex},{0x5000,'4e722700'}}) do
        for i=1,#seed[2],2 do space:write_u8(seed[1]+(i-1)//2,tonumber(seed[2]:sub(i,i+1),16)) end
        event({kind='seed_code',address=seed[1],hex=seed[2]})
    end
    for n=0,7 do cpu.state['D'..n].value=0 end
    for n=0,6 do cpu.state['A'..n].value=0 end
    cpu.state.SR.value=0x2700; cpu.state.SP.value=0x8000
    -- Reset state machine, not host PC mutation, will fetch SSP/PC from vectors.
    for _,kind in ipairs({'read','write'}) do
        local callback=function(address,data,mask)
            if origin=='cpu' then
                local width=(mask==0xff00 or mask==0xff) and 8 or 16
                event({kind=kind,address=address,data=data,mask=mask,width_bits=width,pc=cpu.state.CURPC.value})
            end
            -- No returned replacement data: observe native bus behavior only.
        end
        taps[#taps+1]=space['install_'..kind..'_tap'](space,0,0xffffff,'d1_2_'..kind,callback)
    end
    cpu.debug:bpclear()
    for _,pc in ipairs(cfg.breakpoints) do cpu.debug:bpset(pc,nil,nil) end
    prepared=true; event({kind='prepared',virtual_seconds=emu.time()})
    origin='cpu'
end))
subscriptions[#subscriptions+1]=emu.add_machine_reset_notifier(protect(function()
    assert(prepared,'Reset notification before fixture preparation')
    local previous=origin; origin='fixture'; reset_seen=true
    event({kind='reset_notification',virtual_seconds=emu.time()}); origin=previous
    cpu.debug:go(0xffffffff)
end))
emu.register_periodic(protect(function()
    if done or not prepared then return end
    if emu.time()>0.02 then finish('VIRTUAL_CYCLE_BUDGET'); return end -- 20,000 placeholder cycles
    if manager.machine.debugger.execution_state~='stop' then return end
    local previous=origin; origin='host'
    local current=state(); stops[#stops+1]=current
    if next_stop==1 then
        assert(reset_seen and current.CURPC==0x4000 and current.SP==0x8000 and current.SR==0x2700,
               'Initial CPU state/first instruction mismatch')
        assert(current.D0==0 and current.D1==0 and current.D2==0 and current.D3==0,'Dirty CPU registers')
        dump('initial')
    end
    assert(current.CURPC==cfg.breakpoints[next_stop], 'Unexpected instruction boundary')
    event({kind='instruction_boundary',pc=current.CURPC,index=next_stop})
    next_stop=next_stop+1
    if current.CURPC==cfg.endpoint then finish('ENDPOINT_OBSERVED'); return end
    if #stops>32 then finish('INSTRUCTION_BUDGET'); return end
    cpu.debug:bpclear()
    for i=next_stop,#cfg.breakpoints do cpu.debug:bpset(cfg.breakpoints[i],nil,nil) end
    origin=previous; cpu.debug:go(0xffffffff)
end))
