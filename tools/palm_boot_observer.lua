-- SPDX-License-Identifier: BSD-3-Clause
-- Read-only observer for the existing dana-diag -rom profile. No CPU writes.
-- DANA_PALM_TRACE must name a private output file outside the repository.
local trace, cpu, taps
local count = 0
local limit = 512

local function state(name)
    local entry = cpu.state[name]
    return entry and string.format('%08x', entry.value) or 'unavailable'
end

local function record(kind, address, data, mask)
    if count >= limit then return end
    count = count + 1
    trace:write(string.format(
        '%s address=%08x data=%08x mask=%08x pc=%s curpc=%s sp=%s usp=%s sr=%s ir=%s a4=%s\n',
        kind, address, data, mask, state('PC'), state('CURPC'), state('SP'),
        state('USP'), state('SR'), state('IR'), state('A4')))
    trace:flush()
end

emu.register_start(function()
    local path = assert(os.getenv('DANA_PALM_TRACE'), 'DANA_PALM_TRACE is required')
    cpu = assert(manager.machine.devices[':maincpu'], 'Dana CPU missing')
    assert(cpu.state['SP'], 'Native M68000 SP binding missing')
    trace = assert(io.open(path, 'w'))
    trace:write('OBSERVATION_ONLY full_boot=UNPROVEN\n')
    local names = {}
    for name in pairs(cpu.state) do names[#names + 1] = name end
    table.sort(names)
    trace:write('state_names=' .. table.concat(names, ',') .. '\n')
    local bus = cpu.spaces['program']
    -- Keep tap handles alive for the entire run. Callbacks do not change data.
    taps = {
        bus:install_read_tap(0, 7, 'palm_reset_vectors', function(a, d, m)
            record('VECTOR_READ', a, d, m)
        end),
        bus:install_write_tap(0, 0xffffffff, 'palm_boot_writes', function(a, d, m)
            record('WRITE', a, d, m)
        end)
    }
end)

emu.register_frame_done(function()
    if trace then record('FRAME_SAMPLE', 0, 0, 0) end
end)

emu.register_stop(function()
    if trace then
        trace:write('observer_stopped events=' .. count .. ' full_boot=UNPROVEN\n')
        trace:close()
        trace = nil
    end
    taps = nil
end)
