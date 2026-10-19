-- SPDX-License-Identifier: BSD-3-Clause
-- Observations only. Native quickload owns initialization and native CPU reset.
local cfg=dofile(assert(os.getenv('DANA_F1_CONFIG')))
local cpu,space,ready,done,first=false,false,false,false,false
local events,taps,subscriptions={}, {}, {}
local bytes,host=0,false
local pending,pending_dependency,initialized=nil,nil,false
local e4=cfg.revision=='F1-E4'
local e5=cfg.revision=='F1-E5' and type(cfg.qualification_sha256)=='string' and #cfg.qualification_sha256==64
assert(cfg.revision~='F1-E5' or e5,'Missing new PFSEL build qualification')
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
    local trace=io.open(cfg.output..'/guest.trace','rb')
    local trace_bytes=trace and trace:seek('end') or 0;if trace then trace:close() end
    local result={schema=e5 and 'dana-f1-e5-observation-v1' or e4 and 'dana-f1-e4-observation-v1' or 'dana-f1-observation-v1',
        status='CAPTURED',reason=reason,dependency=dependency,
        first_instruction=first,events=events,final=cpu and state() or {},
        virtual_seconds=emu.time(),package_sha256=cfg.package_sha256,binary_sha256=cfg.binary_sha256,
        revision=cfg.revision,source_commit=cfg.source_commit,execution_id=cfg.execution_id,
        image_sha256=cfg.image_sha256,variant='diag',trace_bytes=trace_bytes,
        qualification_sha256=cfg.qualification_sha256,
        event_count=#events,trace_mode='native_loop_compression_no_sampling',full_boot=false}
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
local function record(e,origin)
    if done then return end
    e.seq=#events;e.origin=origin or 'debugger_observation';e.virtual_seconds=emu.time();e.state=state()
    local n=#encode(e)
    if #events>=20000 or bytes+n>4*1024*1024 then pending='BLOCKED_TRACE_BUDGET';return end
    events[#events+1]=e;bytes=bytes+n
    return e
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
local function implemented_byte(address,kind)
    -- The VZ-specific PLLFSR word is now genuinely decoded in the driver.
    -- Do not mistake this register for a missing peripheral. Other 0xF2xx
    -- addresses (including PLLCR) remain real dependencies if accessed.
    return (address>=0xfffff202 and address<=0xfffff203)
        or address==0xfffff300 or (address>=0xfffff302 and address<=0xfffff307)
        or (address>=0xfffff30c and address<=0xfffff30f)
        or (kind=='read' and address>=0xfffff310 and address<=0xfffff313)
        or address==0xfffff412 or address==0xfffff413
        or (e5 and (address==0xfffff42b or (address>=0xfffff408 and address<=0xfffff40b)
            or (address>=0xfffff418 and address<=0xfffff41b)
            or (address>=0xfffff420 and address<=0xfffff423)
            or (address>=0xfffff428 and address<=0xfffff433)
            or (address>=0xfffff438 and address<=0xfffff43b)
            or (address>=0xfffff440 and address<=0xfffff443)
            or (address>=0xfffff448 and address<=0xfffff44b)
            or (address>=0xfffffa00 and address<=0xfffffa03)
            or address==0xfffffa05
            or (address>=0xfffffa08 and address<=0xfffffa0b)
            or (address>=0xfffffa20 and address<=0xfffffa21)
            or address==0xfffffa23
            or address==0xfffffa25
            or (address>=0xfffffa27 and address<=0xfffffa29)
            or address==0xfffffa2d
            or address==0xfffffa33
            or (address>=0xfffffa36 and address<=0xfffffa37)))
end
local function bus_bytes(address,mask)
    -- MAME's 16-bit tap address is word-aligned, even for byte accesses.
    -- In this big-endian space 00FF at F412 selects F413, NOT PCPDEN.
    assert(address%2==0 and (mask==0xff or mask==0xff00 or mask==0xffff),
           'Unsupported native bus shape')
    local selected={}
    if (mask & 0xff00)~=0 then selected[#selected+1]=address end
    if (mask & 0x00ff)~=0 then selected[#selected+1]=address+1 end
    return selected
end
local function first_unsupported(selected,kind)
    for _,address in ipairs(selected) do
        if address>=0x400000 and not implemented_byte(address,kind) then return address end
    end
end
emu.register_prestart(safe(function()
    if initialized then pending='BLOCKED_UNEXPECTED_MACHINE_RESET';return end
    initialized=true
    cpu=manager.machine.devices[':maincpu'];space=cpu.spaces['program']
    assert(space.data_width==16,'Expected native 16-bit M68000 bus')
    ready=manager.machine.devices[':']:output('dana_guest_loaded')
    assert(cpu.debug and manager.machine.debugger,'Native debugger required')
    manager.machine.debugger.visible_cpu=cpu
    -- Before quickload runs there must be no CPU instruction. The production
    -- driver suspends a mounted guest until complete validation and RAM seed.
    cpu.debug:bpclear();cpu.debug:bpset(cfg.symbols._os_header,'','')
    for _,kind in ipairs({'read','write'}) do
        taps[#taps+1]=space['install_'..kind..'_tap'](space,0,0xffffffff,'f1_'..kind,function(address,data,mask)
            -- No finish/exit/debugger operation, even on error or budget paths.
            if done or host or (pending and pending~='BLOCKED_HARDWARE' and pending~='BLOCKED_GUEST_ADDRESS') then return end
            local ok,err=pcall(function()
                if manager.machine:side_effects_disabled() or not loaded() then return end
                if address<0x800 or address>=0x400000 then
                    local selected=bus_bytes(address,mask)
                    local width=#selected*8
                    local e=record({kind=kind,address=address,data=data,mask=mask,byte_addresses=selected,
                        width_bits=width,tap_id='f1_'..kind,side_effects_disabled=false,
                        after_dependency=pending_dependency~=nil},'cpu')
                    local missing=first_unsupported(selected,kind)
                    if missing and not pending_dependency and e then
                        pending=missing>=0xfffff000 and 'BLOCKED_HARDWARE' or 'BLOCKED_GUEST_ADDRESS'
                        pending_dependency={address=address,effective_address=missing,byte_addresses=selected,
                             width_bits=width,kind=kind,data=data,mask=mask,state=e.state,event_seq=e.seq,
                             origin='cpu',tap_id=e.tap_id}
                    end
                end
            end)
            if not ok then pending='BLOCKED_TAP: '..tostring(err) end
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
    -- Retain the complete native trace through capture, including any deferred
    -- tail. Never silently sample away the instruction causing a dependency.
    do
        local f=io.open(cfg.output..'/guest.trace','rb')
        if f then
            local size=f:seek('end');f:close()
            if size>4*1024*1024 then finish('BLOCKED_TRACE_BUDGET');return end
        end
    end
    if pending then finish(pending,pending_dependency);return end
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
