-- SPDX-License-Identifier: BSD-3-Clause
-- Focused native DIAG fixture. Host operations are explicitly separated from CPU bus evidence.
local cfg=dofile(assert(os.getenv('DANA_PORTC_CONFIG')))
local cpu,space,phase,done=nil,nil,'initial',false
local taps,subscriptions,events={},{},{}
local host=false
local function json(x)
    if type(x)=='string' then return string.format('%q',x):gsub('\\\n','\\n') end
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
    f:write(json({status=status,reason=reason,events=events,phase=phase,
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
                events[#events+1]={kind=kind,address=address,data=data,mask=mask,
                    pc=cpu.state.CURPC.value,origin='cpu'}
            end
        end)
    end
    manager.machine.debugger:command('trace "'..cfg.output..'/cpu.trace"')
    host=false
end))
subscriptions[#subscriptions+1]=emu.add_machine_reset_notifier(safe(function()
    if phase=='reset_pending' then
        host=true
        local value=pair()
        events[#events+1]={kind='profile_reset',origin='host_observation',value=value}
        finish(value==0 and 'PASS' or 'FAIL','NATIVE_PROFILE_RESET_AND_SAVE_TEST')
    elseif cpu then cpu.debug:go(0xffffffff) end
end))
emu.register_periodic(safe(function()
    if done or not cpu then return end
    if emu.time()>1 then finish('BLOCKED','VIRTUAL_TIMEOUT');return end
    if manager.machine.debugger.execution_state~='stop' then return end
    host=true
    if phase=='initial' then
        assert(cpu.state.CURPC.value==0x4000,'Wrong first fixture PC')
        if pair()~=0 then finish('FAIL','PROFILE_INITIAL_STATE');return end
        events[#events+1]={kind='profile_initial',origin='host_observation',value=pair()}
        phase='fixture';cpu.debug:go(0xffffffff)
    elseif phase=='fixture' then
        assert(cpu.state.CURPC.value==cfg.endpoint,'Unexpected fixture stop')
        dump('final.ram')
        events[#events+1]={kind='fixture_complete',origin='host_observation',pc=cpu.state.CURPC.value,
            sr=cpu.state.SR.value,sp=cpu.state.SP.value,value=pair()}
        if pair()~=0xfe81 then finish('FAIL','NATIVE_BYTE_LANES_OR_ALIAS');return end
        -- Exercise MAME's real save registration, not an invented register copy.
        -- API errors remain BLOCKED_HARNESS; incorrect restoration is product FAIL.
        local saved=manager.machine:buffer_save()
        space:write_u16(0xfffff412,0xabcdef & 0xffff)
        if pair()~=0xcdef then finish('FAIL','SAVE_MUTATION_CONTROL');return end
        assert(manager.machine:buffer_load(saved),'Native state load failed')
        events[#events+1]={kind='state_restored',origin='host_observation',value=pair()}
        if pair()~=0xfe81 then finish('FAIL','NATIVE_SAVE_RESTORE');return end
        phase='reset_pending';manager.machine:soft_reset()
    end
    host=false
end))
