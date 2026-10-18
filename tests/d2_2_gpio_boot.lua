-- SPDX-License-Identifier: BSD-3-Clause
-- Two independent DIAG processes: save_restore OR reset. Never restore then reset.
local cfg=dofile(assert(os.getenv('DANA_PORTC_CONFIG')))
assert(cfg.execution=='save_restore' or cfg.execution=='reset','Invalid Port C execution')
local cpu,space,phase,done=nil,nil,'initial',false
local taps,subscriptions,events={},{},{}
local host,initialized=false,false
local epoch,request_id=0,0
local function json(x)
    if type(x)=='string' then
        return '"'..x:gsub('\\','\\\\'):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r'):gsub('\t','\\t')..'"'
    end
    if type(x)=='number' or type(x)=='boolean' then return tostring(x) end
    if type(x)=='table' then
        local out={}
        if #x>0 then for _,v in ipairs(x) do out[#out+1]=json(v) end;return '['..table.concat(out,',')..']' end
        local keys={};for k in pairs(x) do keys[#keys+1]=k end;table.sort(keys)
        for _,k in ipairs(keys) do out[#out+1]=json(k)..':'..json(x[k]) end
        return '{'..table.concat(out,',')..'}'
    end
    return 'null'
end
local function event(e)
    e.seq=#events;e.epoch=epoch;e.request_id=request_id
    e.virtual_seconds=emu.time()
    events[#events+1]=e
end
local function pair() return space:read_u16(0xfffff412) end
local function dump(name)
    local f=assert(io.open(cfg.output..'/'..name,'wb'))
    for base=0,0x3fffff,4096 do
        local chunk={}
        for a=base,base+4095 do chunk[#chunk+1]=string.char(space:read_u8(a)) end
        f:write(table.concat(chunk))
    end
    f:close()
end
local function finish(status,reason)
    if done then return end;done=true;host=true
    manager.machine.debugger:command('trace off')
    local f=assert(io.open(cfg.output..'/observation.json','w'))
    f:write(json({schema='dana-portc-observation-v2',status=status,reason=reason,events=events,phase=phase,
        execution=cfg.execution,execution_id=cfg.execution_id,variant='diag',source_commit=cfg.source_commit,
        binary_sha256=cfg.binary_sha256,fixture_sha256=cfg.fixture_sha256}), '\n');f:close()
    manager.machine:exit()
end
local function safe(f)
    return function(...)
        local ok,err=pcall(f,...)
        if not ok then finish('BLOCKED','HARNESS: '..tostring(err)) end
    end
end
emu.register_prestart(safe(function()
    -- Pinned MAME invokes this FIRST on EVERY reset, not only at startup.
    -- Never re-seed RAM, change CPU state, or install duplicate taps here.
    if initialized then
        if cfg.execution~='reset' or phase~='reset_requested' then
            finish('BLOCKED','UNEXPECTED_NATIVE_RESET');return
        end
        host=true;epoch=epoch+1
        event({kind='reset_transition',origin='native_notification',value=pair(),
            api='LUA_ON_PRESTART',point='before_device_reset'})
        phase='reset_transition';host=false
        return
    end
    initialized=true
    cpu=manager.machine.devices[':maincpu'];space=cpu.spaces['program']
    assert(space.data_width==16 and cpu.debug,'Expected native 16-bit debugger')
    host=true
    for a=0,0x3ffffc,4 do space:write_u32(a,0) end
    space:write_u32(0,0x8000);space:write_u32(4,0x4000)
    for i=1,#cfg.hex,2 do space:write_u8(0x4000+(i-1)//2,tonumber(cfg.hex:sub(i,i+1),16)) end
    space:write_u16(0x10010,0xcafe)
    cpu.state.SR.value=0x2700
    dump('initial.ram')
    manager.machine.debugger.visible_cpu=cpu
    cpu.debug:bpclear();cpu.debug:bpset(0x4000,'','');cpu.debug:bpset(cfg.endpoint,'','')
    for _,kind in ipairs({'read','write'}) do
        taps[#taps+1]=space['install_'..kind..'_tap'](space,0,0xffffffff,'portc_'..kind,function(address,data,mask)
            if not host and not done and (address<8 or address>=0x400000) then
                if #events>=256 then finish('BLOCKED','BUS_TRACE_LIMIT');return end
                event({kind=kind,address=address,data=data,mask=mask,
                    pc=cpu.state.CURPC.value,origin='cpu',tap_id='portc_'..kind})
            end
        end)
    end
    manager.machine.debugger:command('trace "'..cfg.output..'/cpu.trace"')
    host=false
end))
subscriptions[#subscriptions+1]=emu.add_machine_reset_notifier(safe(function()
    if done then return end
    if phase=='reset_transition' then
        -- Registered after MAME's reset_all_devices; observe the actual driver
        -- profile here, before allowing CPU vector fetches / fixture replay.
        host=true
        local value=pair()
        event({kind='profile_reset',origin='native_notification',value=value,
            api='on_machine_reset',point='after_device_reset'})
        if value~=0 then finish('FAIL','CONFIRMED_POST_RESET_PORTC_VALUE');return end
        phase='await_reset_entry';host=false
    end
    if cpu then cpu.debug:go(0xffffffff) end
end))
emu.register_periodic(safe(function()
    if done or not cpu then return end
    if emu.time()>1 then finish('BLOCKED','VIRTUAL_TIMEOUT');return end
    if manager.machine.debugger.execution_state~='stop' then return end
    host=true
    if phase=='initial' then
        assert(cpu.state.CURPC.value==0x4000,'Wrong first fixture PC')
        if pair()~=0 then finish('FAIL','PROFILE_INITIAL_STATE');return end
        event({kind='profile_initial',origin='host_observation',value=pair(),
            pc=cpu.state.CURPC.value,sp=cpu.state.SP.value,sr=cpu.state.SR.value})
        phase='fixture';cpu.debug:go(0xffffffff)
    elseif phase=='fixture' then
        assert(cpu.state.CURPC.value==cfg.endpoint,'Unexpected fixture stop')
        dump('final.ram')
        event({kind='fixture_complete',origin='host_observation',pc=cpu.state.CURPC.value,
            sr=cpu.state.SR.value,sp=cpu.state.SP.value,value=pair()})
        if pair()~=0xfe81 then finish('FAIL','NATIVE_BYTE_LANES_OR_ALIAS');return end
        if cfg.execution=='save_restore' then
            local saved=manager.machine:buffer_save()
            assert(type(saved)=='string' and #saved>0,'Empty native save buffer')
            event({kind='state_saved',origin='host_observation',bytes=#saved,value=pair()})
            space:write_u16(0xfffff412,0xcdef)
            event({kind='state_mutated',origin='host_request',value=pair()})
            if pair()~=0xcdef then finish('FAIL','SAVE_MUTATION_CONTROL');return end
            assert(manager.machine:buffer_load(saved),'Native state load failed')
            event({kind='state_restored',origin='host_observation',value=pair(),load_ok=true})
            dump('restored.ram')
            if pair()~=0xfe81 then finish('FAIL','NATIVE_SAVE_RESTORE');return end
            -- Nothing is scheduled after synchronous load. Execution B is fresh.
            phase='save_complete';finish('PASS','REGISTER_AND_SAVE_RESTORE_COMPLETE');return
        else
            request_id=1
            event({kind='reset_request',origin='host_request',value=pair(),api='soft_reset'})
            phase='reset_requested'
            manager.machine:soft_reset()
            -- The scheduler must run to service the zero-time reset timer.
            cpu.debug:go(0xffffffff)
        end
    elseif phase=='await_reset_entry' then
        assert(cpu.state.CURPC.value==0x4000,'Wrong post-reset entry PC')
        local value=pair()
        event({kind='reset_entry',origin='host_observation',value=value,
            pc=cpu.state.CURPC.value,sp=cpu.state.SP.value,sr=cpu.state.SR.value})
        dump('reset.ram')
        if value~=0 then finish('FAIL','POST_RESET_FIXTURE_REPLAY_OR_STATE');return end
        phase='reset_complete';finish('PASS','NATIVE_RESET_COMPLETE');return
    end
    host=false
end))
