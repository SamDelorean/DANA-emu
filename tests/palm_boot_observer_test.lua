-- SPDX-License-Identifier: BSD-3-Clause
-- Mock API contract test only. Does not run a guest or emulate a CPU.
local callbacks, tap_callbacks = {}, {}
local output = ''
local closed = false
local cpu = {state = {SP = {value = 0x48fe}, PC = {value = 0x1000c812}}, spaces = {}}
local bus = {}
function bus:install_read_tap(_, _, _, callback)
    tap_callbacks.read = callback
    return {}
end
function bus:install_write_tap(_, _, _, callback)
    tap_callbacks.write = callback
    return {}
end
cpu.spaces.program = bus
manager = {machine = {devices = {[':maincpu'] = cpu}}}
emu = {
    register_start = function(f) callbacks.start = f end,
    register_frame_done = function(f) callbacks.frame = f end,
    register_stop = function(f) callbacks.stop = f end
}
os.getenv = function(name) assert(name == 'DANA_PALM_TRACE'); return 'mock-private-trace' end
io.open = function(path, mode)
    assert(path == 'mock-private-trace' and mode == 'w')
    return {
        write = function(_, text) output = output .. text end,
        flush = function() end,
        close = function() closed = true end
    }
end
dofile('tools/palm_boot_observer.lua')
callbacks.start()
assert(tap_callbacks.read(0, 0x48fe, 0xffff) == nil)
assert(tap_callbacks.write(0, 0, 0xff00) == nil)
callbacks.frame()
for _ = 1, 600 do tap_callbacks.write(0, 0, 0xff00) end
callbacks.stop()
assert(closed)
assert(output:find('sp=000048fe', 1, true))
assert(output:find('curpc=unavailable', 1, true))
assert(output:find('mask=0000ff00', 1, true))
assert(output:find('events=512 full_boot=UNPROVEN', 1, true))
assert(cpu.state.SP.value == 0x48fe and cpu.state.PC.value == 0x1000c812)
print('PASS: observer mock API, SP binding, missing optional state, lane mask, limit, unchanged CPU')
