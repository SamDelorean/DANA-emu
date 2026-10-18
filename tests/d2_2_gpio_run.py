#!/usr/bin/env python3
"""Bounded Port C native DIAG fixture; no guest, reference emulator or ROM build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

from d1_2_run import lua
from f1_emutos_run import limits

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def diag_path(path):
    path = Path(path).absolute()
    # Resolve identity before invoking anything. No CLI probe of an arbitrary emulator.
    if path.name != 'dana-diag' or path.parent.name != 'bin' or path.parent.parent.name != 'diag':
        raise ValueError('BLOCKED_DIAG_STAGING_PATH_REQUIRED')
    if path.resolve()!=path or path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError('BLOCKED_STAGED_DIAG_EXECUTABLE_MISSING')
    return path


def fixture():
    data = bytearray()
    def byte(value, addr):
        data.extend(struct.pack('>HHI', 0x13fc, value, addr))
    def snapshot(offset):
        data.extend(bytes.fromhex('3039fffff412'))  # MOVE.W absolute,D0
        data.extend(struct.pack('>HI', 0x33c0, 0x10000+offset))
    byte(0x55, 0xfffff412); byte(0xaa, 0xfffff413); snapshot(0)
    data.extend(bytes.fromhex('33fc1234fffff412')); snapshot(2)
    byte(0xfe, 0xfffff412); snapshot(4)
    byte(0x81, 0xfffff413); snapshot(6)
    for addr in (0x00fff412, 0x00fff413, 0xfffff410, 0xfffff411, 0xfffff414):
        byte(0, addr)
    snapshot(8)
    endpoint = 0x4000+len(data)
    data.extend(bytes.fromhex('4e722700'))
    return bytes(data), endpoint


def verify(root):
    root = Path(root)
    try:
        record = json.loads((root/'run.json').read_text())
        obs = json.loads((root/'observation.json').read_text())
        payload, endpoint = fixture()
        wanted = hashlib.sha256(payload).hexdigest()
        if record['exit_code'] != 0:
            return {'status': 'BLOCKED', 'reason': 'NATIVE_PROCESS_EXIT_OR_TIMEOUT'}
        if obs['fixture_sha256'] != wanted or obs['binary_sha256'] != record['binary_sha256']:
            raise ValueError('Observation identity mismatch')
        if obs['status'] != 'PASS':
            return {'status': obs['status'], 'reason': obs['reason']}
        initial = (root/'initial.ram').read_bytes()
        final = (root/'final.ram').read_bytes()
        if len(initial) != 0x400000 or len(final) != 0x400000:
            raise ValueError('Incomplete RAM evidence')
        seed = bytearray(0x400000)
        seed[:8] = struct.pack('>II', 0x8000, 0x4000)
        seed[0x4000:0x4000+len(payload)] = payload
        seed[0x10010:0x10012] = bytes.fromhex('cafe')
        if initial != seed:
            raise ValueError('Fixture code identity mismatch')
        expected = bytearray(initial)
        expected[0x10000:0x1000a] = bytes.fromhex('55aa1234fe34fe81fe81')
        if final != expected:
            return {'status': 'FAIL', 'reason': 'NATIVE_LANES_ALIAS_OR_RAM_CORRUPTION'}
        events = obs['events']
        phases = {e['kind']: e for e in events if e['origin'] == 'host_observation'}
        if any(phases[k]['value'] != v for k, v in (
                ('profile_initial', 0), ('fixture_complete', 0xfe81),
                ('state_restored', 0xfe81), ('profile_reset', 0))):
            return {'status': 'FAIL', 'reason': 'NATIVE_RESET_OR_SAVE_STATE'}
        if phases['fixture_complete']['pc'] != endpoint or phases['fixture_complete']['sp'] != 0x8000:
            raise ValueError('Fixture endpoint/stack mismatch')
        bus = [e for e in events if e['origin'] == 'cpu']
        vectors = [(e['address'],e['data']) for e in bus if e['kind']=='read' and e['address']<8]
        if vectors[:4] != [(0,0), (2,0x8000), (4,0), (6,0x4000)]:
            raise ValueError('Missing native reset vector evidence')
        for mask, data in ((0xff00, 0x5500), (0x00ff, 0xaa), (0xffff, 0x1234),
                           (0xff00, 0xfe00), (0x00ff, 0x81)):
            if not any(e['kind']=='write' and e['address']==0xfffff412 and
                       e['mask']==mask and e['data'] & mask == data for e in bus):
                raise ValueError('Missing CPU-origin lane transaction')
        for address, mask in ((0x00fff412,0xff00), (0x00fff412,0x00ff),
                              (0xfffff410,0xff00), (0xfffff410,0x00ff), (0xfffff414,0xff00)):
            if not any(e['kind']=='write' and e['address']==address and e['mask']==mask for e in bus):
                raise ValueError('Missing native neighbor/alias negative control')
        trace = (root/'cpu.trace').read_text()
        pcs = {int(pc,16) for pc in re.findall(r'^\s*([0-9a-fA-F]+):', trace, re.M)}
        if not {0x4000, endpoint-6} <= pcs:
            raise ValueError('Missing native instruction evidence')
        return {'status': 'PASS', 'scope': 'R-direct Port C native lanes/reset/save/alias/RAM guards',
                'binary_sha256': record['binary_sha256'], 'fixture_sha256': wanted,
                'physical_reset': 'MOTOROLA_0xFF; R_DIRECT_SOFTWARE_PROFILE_0x00'}
    except FileNotFoundError as error:
        return {'status': 'BLOCKED', 'reason': str(error)}
    except (ValueError, KeyError, TypeError) as error:
        return {'status': 'FAIL', 'reason': str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('diag', type=Path); parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    root = args.evidence.resolve(); root.mkdir(parents=True, exist_ok=False)
    try:
        binary = diag_path(args.diag)
        payload, endpoint = fixture()
        plugin = root/'plugin'; plugin.mkdir()
        shutil.copyfile(HERE/'d2_2_gpio_boot.lua', plugin/'boot.lua')
        config = {'output': str(root), 'hex': payload.hex(), 'endpoint': endpoint,
                  'binary_sha256': digest(binary), 'fixture_sha256': hashlib.sha256(payload).hexdigest()}
        cfg = root/'config.lua'; cfg.write_text('return '+lua(config)+'\n')
        command = [str(binary), 'asmdana', '-noreadconfig', '-debug', '-debugger', 'none',
                   '-pluginspath', str(plugin), '-plugins', '-video', 'none', '-sound', 'none',
                   '-nothrottle', '-skip_gameinfo', '-seconds_to_run', '2']
        record = dict(command=command, binary_sha256=config['binary_sha256'],
                      fixture_sha256=config['fixture_sha256'])
        try:
            with (root/'console.log').open('wb') as log:
                proc = subprocess.run(command, cwd=root, env=dict(os.environ,DANA_PORTC_CONFIG=str(cfg)),
                                      stdout=log, stderr=subprocess.STDOUT, timeout=90, preexec_fn=limits)
            record['exit_code'] = proc.returncode
        except subprocess.TimeoutExpired:
            record['exit_code'] = None
        (root/'run.json').write_text(json.dumps(record, indent=2)+'\n')
        result = verify(root)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result = {'status': 'BLOCKED', 'reason': str(error)}
    (root/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return {'PASS':0, 'FAIL':1, 'BLOCKED':2}[result['status']]


if __name__ == '__main__':
    sys.exit(main())
