#!/usr/bin/env python3
"""One native guest-CPU campaign for the ENTIRE Dana physical keyboard.

Checks every raw ST scan from the 81 MAME input callbacks and several
simultaneous-key packets. No peripheral shortcuts, no guest OS key injection,
no MAME source edits, no extra executable. Requires an explicitly authorized
T run; this script never runs on its own.
"""
import argparse
import json
import re
import subprocess
import time
from pathlib import Path

PORT = re.compile(r'PORT_START\("(KEYS|EXKEY[0-3])"\)')
LABEL = re.compile(r'PORT_NAME\("((?:\\.|[^"\\])*)"\)')
SCAN = re.compile(r'st_key_changed\),(\d+)\)')
MASK = re.compile(r'PORT_BIT\(0x([0-9a-f]+),', re.IGNORECASE)


def inventory(source):
    tag = None
    result = []
    for line in source.splitlines():
        p = PORT.search(line)
        if p:
            tag = p.group(1)
        if tag and 'PORT_BIT(' in line and 'st_key_changed' in line:
            m, n, b = LABEL.search(line), SCAN.search(line), MASK.search(line)
            if not m or not n or not b:
                raise ValueError('Unparseable physical key mapping: '+line)
            result.append((tag, json.loads('"'+m.group(1)+'"'), int(n.group(1)), int(b.group(1), 16)))
    codes = [scan for _, _, scan, _ in result]
    if len(codes) != 81 or len(set(codes)) != 81:
        raise ValueError('Expected 81 distinct physical Dana scan codes')
    if not all(0 < x < 128 for x in codes):
        raise ValueError('Invalid Dana ST scan code')
    return result


def lua_program(keys, result_path):
    # Host input only. The observer is passive and accepts ONLY guest 68000
    # memory reads of SPI2: 0xfffff800, with ST packet header followed by codes.
    encoded = ',\n'.join(
        ('{tag='+json.dumps(':'+tag)+',name='+json.dumps(label)+
         ',scan='+str(scan)+',mask='+str(mask)+'}') for tag, label, scan, mask in keys)
    return """local machine=manager.machine
local cpu=assert(machine.devices[":maincpu"])
local bus=assert(cpu.spaces["program"])
local entries={%s}
local inputs={}
for i,e in ipairs(entries) do
    inputs[i]=assert(machine.ioport.ports[e.tag].fields[e.name],
        "MAME key missing "..e.tag.." "..e.name)
end
local frames=0
local seen={}
local host_seen={}
local host_samples=0
local headers=0
local releases=0
local physical=0
local guest_data_reads=0
local guest_control_reads=0
local guest_pc_first=-1
local guest_pc_last=-1
local guest_pc_changed=false
local expected=0
local current={}
local chords={}
local combos={{9,43},{123,109},{114,112},{19,52},{70,11}}
local tap=bus:install_read_tap(0xfffff800,0xfffff801,
    "st81_all_cpu_spi2",function(offset,data,mask)
    guest_data_reads=guest_data_reads+1
    local v=data & 255
    if expected>0 then
        physical=physical+1
        seen[v]=true
        current[#current+1]=v
        expected=expected-1
        if expected==0 then
            for i,pair in ipairs(combos) do
                local has0=false
                local has1=false
                for _,x in ipairs(current) do
                    if x==pair[1] then has0=true end
                    if x==pair[2] then has1=true end
                end
                if has0 and has1 then chords[i]=true end
            end
        end
    elseif v>=0x40 and v<=0x48 then
        headers=headers+1
        expected=v-0x40
        current={}
        if expected==0 then releases=releases+1 end
    end
end)
local control_tap=bus:install_read_tap(0xfffff802,0xfffff803,
    "st81_cpu_spi2_ctrl",function(offset,data,mask)
    guest_control_reads=guest_control_reads+1
end)
local start=240
local interval=96
local hold=64
local gap=96
local combo_start=start+#entries*interval+gap
local combo_interval=136
local combo_hold=90
local ending=combo_start+#combos*combo_interval+gap
local last_key=0
local active_combo=0
local combo_indexes={}
for i,pair in ipairs(combos) do
    combo_indexes[i]={}
    for n,e in ipairs(entries) do
        if e.scan==pair[1] or e.scan==pair[2] then
            combo_indexes[i][#combo_indexes[i]+1]=n
        end
    end
    assert(#combo_indexes[i]==2,"Both chord keys must be mapped")
end
emu.register_frame_done(function()
    frames=frames+1
    if frames==start then guest_pc_first=cpu.state["PC"].value end
    if frames%120==0 then
        local pc=cpu.state["PC"].value
        if guest_pc_last>=0 and pc~=guest_pc_last then guest_pc_changed=true end
        guest_pc_last=pc
    end
    if frames>=start and frames<combo_start-gap then
        local idx=math.floor((frames-start)/interval)+1
        local t=(frames-start)%%interval
        if idx~=last_key and last_key>0 then
            inputs[last_key]:set_value(0)
        end
        last_key=idx
        if idx<=#entries then
            inputs[idx]:set_value(t<hold and 1 or 0)
            if t>=5 and t<hold then
                local port=machine.ioport.ports[entries[idx].tag]:read()
                host_samples=host_samples+1
                if (port & entries[idx].mask)~=0 then
                    host_seen[entries[idx].scan]=true
                end
            end
        end
    elseif frames>=combo_start and frames<ending-gap then
        if last_key>0 then
            inputs[last_key]:set_value(0)
            last_key=0
        end
        local idx=math.floor((frames-combo_start)/combo_interval)+1
        local t=(frames-combo_start)%%combo_interval
        if idx~=active_combo and active_combo>0 then
            for _,n in ipairs(combo_indexes[active_combo]) do
                inputs[n]:set_value(0)
            end
        end
        active_combo=idx
        if idx<=#combos then
            for _,n in ipairs(combo_indexes[idx]) do
                inputs[n]:set_value(t<combo_hold and 1 or 0)
            end
        end
    else
        if last_key>0 then
            inputs[last_key]:set_value(0)
            last_key=0
        end
        if active_combo>0 then
            for _,n in ipairs(combo_indexes[active_combo]) do
                inputs[n]:set_value(0)
            end
            active_combo=0
        end
    end
    if frames>=ending then
        local f=assert(io.open(%s,"w"))
        local found={}
        local absent={}
        for _,e in ipairs(entries) do
            if seen[e.scan] then
                found[#found+1]=e.scan
            else
                absent[#absent+1]=e.scan
            end
        end
        table.sort(found)
        local host_count=0
        for _,e in ipairs(entries) do
            if host_seen[e.scan] then host_count=host_count+1 end
        end
        local pairs={}
        for i=1,#combos do
            if chords[i] then pairs[#pairs+1]=i end
        end
        f:write('{"scans_seen":['..table.concat(found,',')..
            '],"missing":['..table.concat(absent,',')..
            '],"chords_seen":['..table.concat(pairs,',')..
            '],"headers":'..headers..',"releases":'..releases..
            ',"host_inputs_seen":'..host_count..
            ',"host_samples":'..host_samples..
            ',"physical_reads":'..physical..
            ',"guest_data_reads":'..guest_data_reads..
            ',"guest_control_reads":'..guest_control_reads..
            ',"guest_pc_first":'..guest_pc_first..
            ',"guest_pc_last":'..guest_pc_last..
            ',"guest_pc_changed":'..tostring(guest_pc_changed)..
            ',"frames":'..frames..'}')
        f:close()
        machine:exit()
    end
end)
""" % (encoded, json.dumps(str(result_path)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--diag', required=True, type=Path)
    p.add_argument('--guest', required=True, type=Path)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    if a.output.exists():
        raise SystemExit('Output exists; never overwrite earlier evidence')
    source = a.source.read_text()
    keys = inventory(source)
    a.output.mkdir(parents=True)
    report = a.output/'keyboard.json'
    script = a.output/'keyboard.lua'
    script.write_text(lua_program(keys, report))
    cmd = [str(a.diag), 'asmdana', '-quickload', str(a.guest),
           '-autoboot_script', str(script), '-autoboot_delay', '0',
           '-video', 'none', '-sound', 'none', '-nothrottle',
           '-skip_gameinfo', '-nowriteconfig', '-log', '-oslog']
    started_at = time.time_ns()
    finished = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd='/tmp')
    (a.output/'mame.stdout').write_text(finished.stdout[-200000:])
    (a.output/'mame.stderr').write_text(finished.stderr[-200000:])
    machine_log = Path('/tmp/error.log')
    extra = ''
    if machine_log.is_file() and machine_log.stat().st_mtime_ns >= started_at:
        extra = machine_log.read_text(errors='replace')[-250000:]
        (a.output/'machine.log').write_text(extra)
    boot_confirmed = (
        'DANA_GUEST_LOAD entry=00002140' in
        (finished.stdout + finished.stderr + extra)
    )
    if finished.returncode or not report.exists():
        raise SystemExit('BLOCKED: native guest CPU campaign did not finish')
    obs = json.loads(report.read_text())
    obs['expected_physical_keys'] = len(keys)
    obs['guest_boot_trace_confirmed'] = boot_confirmed
    obs['candidate_exit_code'] = finished.returncode
    # All evidence belongs to this ONE native whole-keyboard guest session.
    if not boot_confirmed:
        obs['status'] = 'BLOCKED_GUEST_BOOT'
    elif obs.get('host_inputs_seen', 0) != 81:
        obs['status'] = 'FAIL_HOST_81_INPUTS'
    elif obs.get('guest_data_reads', 0) == 0:
        obs['status'] = 'FAIL_GUEST_SPI2_POLL'
    elif obs.get('guest_control_reads', 0) == 0:
        obs['status'] = 'FAIL_GUEST_SPI2_CONTROL'
    elif obs['missing'] or len(obs['chords_seen']) != 5 or obs['releases'] < len(keys):
        obs['status'] = 'FAIL_GUEST_SCAN_PACKETS'
    else:
        obs['status'] = 'PASS'
    report.write_text(json.dumps(obs, indent=2)+'\n')
    print(json.dumps(obs, indent=2))
    if obs['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
