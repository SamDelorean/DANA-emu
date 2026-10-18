-- SPDX-License-Identifier: BSD-3-Clause
-- R2 B only. The guest owns marker/Port C/result operations. No post-reset breakpoint.
local cfg=dofile(assert(os.getenv('DANA_PORTC_CONFIG')))
assert(cfg.execution=='reset' and cfg.revision=='R2')
local cpu,space,initialized,done=nil,nil,false,false
local phase,epoch,request_id='initial',0,0
local host,pending,ready=false,nil,false
local taps,subscriptions,events={},{},{}
local post_cpu={}
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
    if #events>=256 then pending='BUS_TRACE_LIMIT';return end
    e.seq=#events;e.epoch=epoch;e.request_id=request_id;e.virtual_seconds=emu.time()
    events[#events+1]=e
end
local function post_ready()
    if #post_cpu>7 then pending='AMBIGUOUS_POST_RESET_OBSERVATIONS';return false end
    if #post_cpu~=7 then return false end
    local expected={{'read',0,0},{'read',2,0x8000},{'read',4,0},{'read',6,0x4000},
        {'read',0x20000,1},{'read',0xfffff412},{'write',0x20002}}
    for i,wanted in ipairs(expected) do
        local e=post_cpu[i]
        if e.kind~=wanted[1] or e.address~=wanted[2] or e.mask~=0xffff
            or e.request_id~=1 or (wanted[3] and e.data~=wanted[3]) then return false end
    end
    return post_cpu[5].pc==0x4000 and post_cpu[6].pc==0x40a2 and post_cpu[7].pc==0x40a8
        and post_cpu[6].data==post_cpu[7].data
end
local function dump(name)
    local f=assert(io.open(cfg.output..'/'..name,'wb'))
    for base=0,0x3fffff,4096 do
        local chunk={};for a=base,base+4095 do chunk[#chunk+1]=string.char(space:read_u8(a)) end
        f:write(table.concat(chunk))
    end
    f:close()
end
local function finish(status,reason)
    if done then return end;done=true;host=true
    manager.machine.debugger:command('trace off')
    local f=assert(io.open(cfg.output..'/observation.json','w'))
    f:write(json({schema='dana-portc-reset-cpu-r2',status=status,reason=reason,events=events,phase=phase,
        revision='R2',execution='reset',variant='diag',execution_id=cfg.execution_id,
        source_commit=cfg.source_commit,binary_sha256=cfg.binary_sha256,fixture_sha256=cfg.fixture_sha256}),'\n')
    f:close();manager.machine:exit()
end
local function safe(fn)
    return function(...)
        local ok,err=pcall(fn,...)
        if not ok then finish('BLOCKED','HARNESS: '..tostring(err)) end
    end
end
emu.register_prestart(safe(function()
    if initialized then
        if phase~='reset_requested' then pending='UNEXPECTED_NATIVE_RESET';return end
        host=true;epoch=1
        event({kind='reset_transition',origin='native_notification',value=space:read_u16(0xfffff412),
            api='LUA_ON_PRESTART',point='before_device_reset'})
        phase='reset_transition';host=false
        return
    end
    initialized=true;host=true
    cpu=manager.machine.devices[':maincpu'];space=cpu.spaces['program']
    assert(space.data_width==16 and cpu.debug,'Expected native 16-bit debugger')
    for a=0,0x3ffffc,4 do space:write_u32(a,0) end
    space:write_u32(0,0x8000);space:write_u32(4,0x4000)
    for i=1,#cfg.hex,2 do space:write_u8(0x4000+(i-1)//2,tonumber(cfg.hex:sub(i,i+1),16)) end
    space:write_u16(0x10010,0xcafe)
    -- One-time host bootstrap; subsequent marker/result updates must be CPU-origin.
    space:write_u16(0x20000,0);space:write_u16(0x20002,0xa55a)
    cpu.state.SR.value=0x2700;dump('initial.ram')
    manager.machine.debugger.visible_cpu=cpu
    cpu.debug:bpclear();cpu.debug:bpset(0x4000,'','');cpu.debug:bpset(cfg.endpoint,'','')
    for _,kind in ipairs({'read','write'}) do
        taps[#taps+1]=space['install_'..kind..'_tap'](space,0,0xffffffff,'portc_r2_'..kind,function(address,data,mask)
            -- No exit/finish/debugger command in a tap, including error paths.
            if done or host or pending then return end
            if address<8 or address>=0x400000 or address==0x20000 or address==0x20002 then
                local ok,err=pcall(function()
                    local e={kind=kind,address=address,data=data,mask=mask,pc=cpu.state.CURPC.value,
                        origin='cpu',tap_id='portc_r2_'..kind}
                    event(e)
                    if epoch==1 then post_cpu[#post_cpu+1]=e end
                    if epoch==1 and kind=='write' and address==0x20002 then ready=true end
                    if epoch==1 and kind=='write' and address==0xfffff412 then pending='POST_RESET_PORTC_WRITE_OR_REPLAY' end
                end)
                if not ok then pending='TAP_ERROR: '..tostring(err) end
            end
        end)
    end
    manager.machine.debugger:command('trace "'..cfg.output..'/cpu.trace"')
    host=false
end))
-- Optional diagnostic only. Neither completion nor the value proof depends on it.
subscriptions[#subscriptions+1]=emu.add_machine_reset_notifier(function()
    if not done and epoch==1 then event({kind='reset_notification',origin='native_notification'}) end
    if cpu then cpu.debug:go(0xffffffff) end
end)
emu.register_periodic(safe(function()
    if done or not cpu then return end
    if pending then finish('BLOCKED',pending);return end
    if emu.time()>1 then finish('BLOCKED','VIRTUAL_TIMEOUT');return end
    if phase=='reset_transition' then
        -- STOP, not a breakpoint: native CURPC/PC must reach the observation STOP.
        if ready and post_ready() and cpu.state.PC.value==cfg.stop_pc+4 then
            host=true
            event({kind='cpu_reset_complete',origin='host_observation',pc=cpu.state.CURPC.value,
                next_pc=cpu.state.PC.value,ir=cpu.state.IR.value,sp=cpu.state.SP.value,sr=cpu.state.SR.value,
                marker=space:read_u16(0x20000),result=space:read_u16(0x20002)})
            dump('reset.ram');phase='cpu_observation_complete'
            finish('CAPTURED','CPU_POST_RESET_OBSERVATION_CAPTURED')
        end
        return
    end
    if manager.machine.debugger.execution_state~='stop' then return end
    host=true
    if phase=='initial' then
        assert(cpu.state.CURPC.value==0x4000,'Wrong fixture entry')
        event({kind='profile_initial',origin='host_observation',value=space:read_u16(0xfffff412),
            pc=cpu.state.CURPC.value,sp=cpu.state.SP.value,sr=cpu.state.SR.value})
        phase='fixture';cpu.debug:go(0xffffffff)
    elseif phase=='fixture' then
        assert(cpu.state.CURPC.value==cfg.endpoint,'Wrong first-boot endpoint')
        dump('final.ram')
        local value=space:read_u16(0xfffff412)
        event({kind='fixture_complete',origin='host_observation',value=value,
            pc=cpu.state.CURPC.value,sp=cpu.state.SP.value,sr=cpu.state.SR.value})
        if value~=0xfe81 then finish('FAIL','FIRST_BOOT_PORTC_VALUE');return end
        request_id=1;event({kind='reset_request',origin='host_request',value=value,api='soft_reset'})
        -- Remove all initial breakpoints. The CPU branches around the old body.
        cpu.debug:bpclear();phase='reset_requested';manager.machine:soft_reset();cpu.debug:go(0xffffffff)
    end
    host=false
end))
