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
from pathlib import Path

PORT = re.compile(r'PORT_START\("(KEYS|EXKEY[0-3])"\)')
LABEL = re.compile(r'PORT_NAME\("((?:\\.|[^"\\])*)"\)')
SCAN = re.compile(r'st_key_changed\),(\d+)\)')


def inventory(source):
    tag = None
    result = []
    for line in source.splitlines():
        p = PORT.search(line)
        if p:
            tag = p.group(1)
        if tag and 'PORT_BIT(' in line and 'st_key_changed' in line:
            m, n = LABEL.search(line), SCAN.search(line)
            if not m or not n:
                raise ValueError('Unparseable physical key mapping: '+line)
            result.append((tag, json.loads('"'+m.group(1)+'"'), int(n.group(1))))
    codes = [scan for _, _, scan in result]
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
         ',scan='+str(scan)+'}') for tag, label, scan in keys)
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
local headers=0
local releases=0
local physical=0
local expected=0
local current={}
local chords={}
local combos={{9,43},{123,109},{114,112},{19,52},{70,11}}
local tap=bus:install_read_tap(0xfffff800,0xfffff801,
    "st81_all_cpu_spi2",function(offset,data,mask)
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
local start=180
local interval=70
local hold=44
local combo_start=start+#entries*interval+70
local combo_interval=90
local ending=combo_start+#combos*combo_interval+180
emu.register_frame_done(function()
    frames=frames+1
    if frames>=start and frames<combo_start then
        local idx=math.floor((frames-start)/interval)+1
        if idx<=#entries then
            local t=(frames-start)%%interval
            inputs[idx]:set_value(t<hold and 1 or 0)
        end
    elseif frames>=combo_start and frames<ending-180 then
        local idx=math.floor((frames-combo_start)/combo_interval)+1
        local t=(frames-combo_start)%%combo_interval
        if idx<=#combos then
            for _,x in ipairs(combos[idx]) do
                for n,e in ipairs(entries) do
                    if e.scan==x then
                        inputs[n]:set_value(t<56 and 1 or 0)
                    end
                end
            end
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
        local pairs={}
        for i=1,#combos do
            if chords[i] then pairs[#pairs+1]=i end
        end
        f:write('{"scans_seen":['..table.concat(found,',')..
            '],"missing":['..table.concat(absent,',')..
            '],"chords_seen":['..table.concat(pairs,',')..
            '],"headers":'..headers..',"releases":'..releases..
            ',"physical_reads":'..physical..',"frames":'..frames..'}')
        f:close()
        machine:exit()
    end
end)
""" % (encoded, '%', '%', json.dumps(str(result_path)))


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
           '-skip_gameinfo', '-nowriteconfig']
    finished = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    (a.output/'mame.stdout').write_text(finished.stdout[-200000:])
    (a.output/'mame.stderr').write_text(finished.stderr[-200000:])
    if finished.returncode or not report.exists():
        raise SystemExit('BLOCKED: native guest CPU campaign did not finish')
    obs = json.loads(report.read_text())
    obs['expected_physical_keys'] = len(keys)
    obs['status'] = ('PASS' if not obs['missing'] and
                     len(obs['chords_seen']) == 5 and
                     obs['releases'] >= len(keys) else 'FAIL')
    report.write_text(json.dumps(obs, indent=2)+'\n')
    print(json.dumps(obs, indent=2))
    if obs['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
