#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""H6 board-storage check using existing H3 native 68000 bootstrap.

Exercises physical 8/16 MiB SDRAM aliasing and the selected H3 NOR socket.
Synthetic firmware only. The observer never writes guest memory or registers.
This is a candidate/installed test: it does not build or install anything.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from d7_5_native import Code, MARKER
from nor_native import check, finish, fixture

NOR_SIZE = {"m29w320db": 0x400000, "m28w640hcb": 0x800000}
BOARD_RAM = {1: 8, 2: 16, 3: 16}
BOARD_NOR = {1: 4, 2: 8, 3: 8}


def ram_payload(expected_mib: int) -> bytes:
    """H4-proven physical DDR addresses; all writes are 68000 opcodes."""
    c = Code()
    c.w(0x46fc, 0x2700)  # supervisor, IRQ mask
    c.move_w(0, 0xfffffb0a)  # disable watchdog
    # Identical DRAM/CS initialization used in H4 ram8/ram16 checks.
    c.move_w(0x0040, 0xfffff10a)
    c.move_w(0x0283, 0xfffff116)
    c.move_w(0xa55a, 0x00430002)
    c.move_w(0x0123, 0x00c30002)
    check(c, 0x00430002, 0x0123 if expected_mib == 8 else 0xa55a)
    check(c, 0x00c30002, 0x0123)
    # Inspect the known 8/16 MiB physical boundary, not host-side RAM.
    c.move_w(expected_mib, MARKER+2)
    return finish(c)


def set_port(config: Path, tag: str, mask: str, default: str, value: int) -> None:
    tree = ET.parse(config)
    root = tree.getroot()
    node = root.find('./system/input')
    if node is None:
        raise RuntimeError('MAME asmdana.cfg lacks /system/input')
    for el in list(node):
        if el.get('tag') == ':' + tag:
            node.remove(el)
    ET.SubElement(node, 'port', tag=':' + tag, type='CONFIG', mask=mask,
                  defvalue=default, value=str(value))
    tree.write(config, encoding='utf-8', xml_declaration=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--case', required=True)
    p.add_argument('--board', type=int, choices=range(4), required=True)
    p.add_argument('--chip', choices=sorted(NOR_SIZE), required=True)
    p.add_argument('--manual-ram', type=int, choices=[8, 16], default=16)
    p.add_argument('--expect-reject', action='store_true')
    p.add_argument('--installed', action='store_true')
    a = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', a.case):
        p.error('Unsafe test-case name')
    if a.expect_reject and a.board == 0:
        p.error('Manual diagnostic profile must not impose a NOR capacity guard')
    root = Path(__file__).resolve().parents[1]
    folder = root/'local-evidence/runtime-compare/h6-storage-20261115'/a.case
    folder.mkdir(parents=True, exist_ok=False)
    effective_ram = BOARD_RAM.get(a.board, a.manual_ram)
    nor_bytes = NOR_SIZE[a.chip]
    binary = root/('runtime/diag/bin/dana-diag' if a.installed else 'runtime/diag/source/danadiagd')
    if not binary.is_file():
        raise SystemExit(f'Binary not found: {binary}')
    cfg = folder/'cfg'
    cfg.mkdir()
    for name in ('asmdana.cfg', 'default.cfg'):
        shutil.copy2(root/'config/palm-uk15'/name, cfg/name)
    conf = cfg/'asmdana.cfg'
    set_port(conf, 'DANA_STORAGE', '3', '0', a.board)
    # Deliberately challenge profile override in selected positive scenarios.
    set_port(conf, 'PHYSRAM', '1', '1', a.manual_ram // 8 - 1)
    body = ram_payload(effective_ram)
    seed = folder/'seed.bin'
    seed.write_bytes(fixture('h6-ram', body, size=nor_bytes))
    seed.chmod(0o444)
    seed_sha = hashlib.sha256(seed.read_bytes()).hexdigest()
    lua = r'''local m=manager.machine
local cpu=m.devices[":maincpu"]
local bus=cpu.spaces.program
local count=0
emu.register_frame_done(function()
 count=count+1
 local marker=bus:read_u16(0x20000)
 if marker==0xa55a or marker==0xdead or count>5000 then
  local f=assert(io.open(OUTPUT,"w"))
  f:write(string.format('{"marker":%d,"stage":%d,"pc":%d,"frames":%d}',marker,bus:read_u16(0x20002),cpu.state.CURPC.value,count))
  f:close()
  m:exit()
 end
end)
'''.replace('OUTPUT', json.dumps(str(folder/'cpu.json')))
    (folder/'observe.lua').write_text(lua)
    command = [str(binary), 'asmdana', '-video', 'none', '-sound', 'none',
               '-nothrottle', '-skip_gameinfo', '-nowriteconfig',
               '-cfg_directory', str(cfg), '-nvram_directory', str(folder/'nvram'),
               '-state_directory', str(folder/'states'), '-rom', str(seed),
               '-autoboot_delay', '0', '-autoboot_script', str(folder/'observe.lua'),
               '-log', '-oslog', '-nor', a.chip]
    env = os.environ.copy()
    env.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', TMPDIR=str(folder))
    with (folder/'run.out').open('w') as out:
        try:
            process = subprocess.run(command, cwd=root/'runtime/diag', env=env,
                                     stdout=out, stderr=subprocess.STDOUT, timeout=160)
        except subprocess.TimeoutExpired:
            process = subprocess.CompletedProcess(command, 124)
    trace = (folder/'run.out').read_text(errors='replace')
    cpu_file = folder/'cpu.json'
    cpu = json.loads(cpu_file.read_text()) if cpu_file.exists() else {}
    expected_nor = BOARD_NOR.get(a.board)
    mismatch = bool(expected_nor and expected_nor != nor_bytes // (1 << 20))
    expected_rejection = a.expect_reject and mismatch
    if a.expect_reject and not mismatch:
        p.error('Rejection case does not actually have NOR geometry mismatch')
    if expected_rejection:
        passed = (process.returncode != 0 and
                  'DANA_STORAGE NOR capacity mismatch' in trace and
                  'DANA_STORAGE_PROFILE board=' not in trace and not cpu)
    else:
        marker = f'DANA_STORAGE_PROFILE board={a.board} sdram={effective_ram * (1 << 20)} nor={nor_bytes}'
        passed = (process.returncode == 0 and cpu.get('marker') == 0xa55a
                  and cpu.get('stage') == effective_ram and
                  (a.board == 0 or marker in trace) and
                  'DANA_PHYSICAL_BLOCKED' not in trace)
    passed = passed and hashlib.sha256(seed.read_bytes()).hexdigest() == seed_sha
    receipt = dict(case=a.case, board=a.board, chip=a.chip,
                   manual_ram_mib=a.manual_ram, effective_ram_mib=effective_ram,
                   flash_mib=nor_bytes >> 20, expected_reject=expected_rejection,
                   returncode=process.returncode, cpu=cpu,
                   guest_cpu_test='PASS' if passed and not expected_rejection else 'NOT_RUN_EXPECTED_GUARD' if passed else 'FAIL',
                   seed_sha256=seed_sha, binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                   pass_=bool(passed))
    (folder/'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2), flush=True)
    if not passed:
        print(trace[-2800:], file=sys.stderr)
    return 0 if passed else 1

if __name__ == '__main__':
    raise SystemExit(main())
