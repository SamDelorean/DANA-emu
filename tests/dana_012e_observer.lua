-- SPDX-License-Identifier: BSD-3-Clause
-- Loss-accounted observations only. No CPU/peripheral emulation or mutation.
local M={}
function M.new(encode,limits)
    local o={events={},accepted_raw=0,attempted_raw=0,dropped_raw=0,reserved_bytes=2,
        native_reads=0,native_writes=0,native_iacks=0,poll_reads=0,epoch=0}
    local last_key=nil
    local function key(e)
        if e.kind~='read' or e.address~=0xfffff202 or e.mask~=0xffff or e.role
            or e.origin~='cpu' or e.tap_id~='f1_read' or e.side_effects_disabled~=false then return nil end
        local values={e.data,e.epoch,tostring(e.after_dependency)}
        local names={};for name in pairs(e.state) do names[#names+1]=name end;table.sort(names)
        for _,name in ipairs(names) do values[#values+1]=name..'='..e.state[name] end
        return table.concat(values,'|')
    end
    function o:push(e)
        self.attempted_raw=self.attempted_raw+1
        if self.overflow then self.dropped_raw=self.dropped_raw+1;return nil end
        if e.kind=='iack' then self.epoch=self.epoch+1 end
        e.epoch=self.epoch;e.raw_first=self.accepted_raw;e.raw_last=self.accepted_raw
        local k=key(e);local previous=self.events[#self.events]
        local reason=nil
        if self.accepted_raw>=limits.max_raw_observations then reason='OBSERVATION_LIMIT_RAW' end
        if not reason and k and k==last_key then
            previous.count=previous.count+1;previous.raw_last=e.raw_last
            previous.max_gap_seconds=math.max(previous.max_gap_seconds,e.virtual_seconds-previous.last_virtual_seconds)
            previous.last_virtual_seconds=e.virtual_seconds;previous.last_pc=e.state.CURPC
        elseif not reason then
            e.seq=#self.events
            if k then
                e.kind='poll_span';e.operation='read';e.count=1
                e.first_pc=e.state.CURPC;e.last_pc=e.state.CURPC
                e.last_virtual_seconds=e.virtual_seconds;e.max_gap_seconds=0
            end
            -- Reserve enough growth for run counts, timestamps and raw ordinals.
            local size=#encode(e)+128
            if #self.events>=limits.max_retained_events then reason='OBSERVATION_LIMIT_EVENTS'
            elseif self.reserved_bytes+size>limits.max_event_bytes then reason='OBSERVATION_LIMIT_EVENT_BYTES'
            else self.events[#self.events+1]=e;self.reserved_bytes=self.reserved_bytes+size;last_key=k end
        end
        if reason then
            self.overflow={reason=reason,first_unrecorded=e};self.dropped_raw=1;return nil
        end
        self.accepted_raw=self.accepted_raw+1
        if e.origin=='cpu' then
            if e.kind=='write' then self.native_writes=self.native_writes+1
            elseif e.kind=='iack' then self.native_iacks=self.native_iacks+1
            else self.native_reads=self.native_reads+1 end
            if k then self.poll_reads=self.poll_reads+1 end
        end
        return self.events[#self.events]
    end
    function o:stats()
        return {compression='exact_full_state_F202_RLE_v1',accepted_raw=self.accepted_raw,
            attempted_raw=self.attempted_raw,dropped_raw=self.dropped_raw,
            native_reads=self.native_reads,native_writes=self.native_writes,native_iacks=self.native_iacks,
            poll_reads=self.poll_reads,retained_events=#self.events,reserved_bytes=self.reserved_bytes,
            overflow=self.overflow}
    end
    return o
end
return M
