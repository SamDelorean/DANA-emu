#!/usr/bin/env python3
"""One genuine MAME DIAG guest IVR test using LLVM-assembled MC68000 source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from d1_2_run import digest, lua, save
from d1_3_1_mmio01_verify import verify
from d1_2_verify import PIN

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
PCS = [0x4000, 0x4006, 0x400a, 0x400c, 0x4012, 0x4014, 0x401a, 0x401c]


def tool(*choices):
    return next((exe for name in choices if (exe := shutil.which(name))), None)


def assemble(directory):
    """Assemble from .s on the pinned LLVM M68k backend; no hand-coded opcodes."""
    mc = tool('llvm-mc-21', 'llvm-mc')
    copy = tool('llvm-objcopy-21', 'llvm-objcopy')
    if not mc or not copy:
        raise RuntimeError('BLOCKED_FIXTURE_TOOLCHAIN: LLVM M68k llvm-mc and llvm-objcopy required')
    source = HERE / 'd1_3_1_mmio01.s'
    shutil.copyfile(source, directory / 'fixture.s')
    obj = directory / 'fixture.o'
    build = subprocess.run([mc, '-triple=m68k-unknown-elf', '-filetype=obj',
                            '-o', str(obj), str(source)],
                           capture_output=True, text=True, timeout=90)
    (directory / 'assemble.log').write_text(build.stdout + build.stderr)
    if build.returncode:
        raise RuntimeError('BLOCKED_FIXTURE_ASSEMBLER: see assemble.log')
    extract = subprocess.run([copy, '-O', 'binary', '--only-section=.text',
                              str(obj), str(directory / 'fixture.bin')],
                             capture_output=True, text=True, timeout=90)
    with (directory / 'assemble.log').open('a') as f:
        f.write(extract.stdout + extract.stderr)
    if extract.returncode:
        raise RuntimeError('BLOCKED_FIXTURE_OBJCOPY: see assemble.log')
    code = (directory / 'fixture.bin').read_bytes()
    if len(code) != 32:
        raise RuntimeError(f'BLOCKED_FIXTURE_LAYOUT: expected 32 assembled bytes, got {len(code)}')
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('diag', type=Path)
    parser.add_argument('evidence', type=Path, help='New independent output directory')
    args = parser.parse_args()
    root = args.evidence.resolve()
    root.mkdir(parents=True, exist_ok=False)
    try:
        binary = args.diag.resolve()
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise RuntimeError('BLOCKED_EXECUTABLE_MISSING: '+str(binary))
        source_sha = subprocess.check_output(
            ['git', '-C', str(PROJECT), 'rev-parse', 'HEAD'], text=True).strip()
        code = assemble(root)
        plugin = root / 'plugin'
        plugin.mkdir()
        shutil.copyfile(HERE / 'd1_3_1_mmio01_boot.lua', plugin / 'boot.lua')
        cfg = dict(case='MMIO-01', variant='diag', run=1, hex=code.hex(),
                   fixture_sha256=hashlib.sha256(code).hexdigest(),
                   binary_sha256=digest(binary), source_sha=source_sha,
                   breakpoints=PCS, endpoint=PCS[-1], output=str(root))
        conf = root / 'config.lua'
        conf.write_text('return '+lua(cfg)+'\\n')
        env = dict(os.environ, DANA_MMIO01_CONFIG=str(conf))
        cmd = [str(binary), 'asmdana', '-noreadconfig', '-debug', '-debugger', 'none',
               '-pluginspath', str(plugin), '-plugins', '-video', 'none', '-sound', 'none',
               '-log', '-nothrottle', '-skip_gameinfo', '-seconds_to_run', '1']
        record = dict(mame_commit=PIN, source_sha=source_sha,
                      binary_sha256=cfg['binary_sha256'],
                      fixture_sha256=cfg['fixture_sha256'],
                      fixture_source_sha256=digest(HERE / 'd1_3_1_mmio01.s'),
                      driver_sha256=digest(PROJECT / 'src/mame/skeleton/alphasdana.cpp'),
                      boot_sha256=digest(HERE / 'd1_3_1_mmio01_boot.lua'),
                      command=cmd, host_timeout_seconds=180)
        try:
            with (root / 'console.log').open('wb') as output:
                result = subprocess.run(cmd, cwd=root, env=env,
                                        stdout=output, stderr=subprocess.STDOUT,
                                        timeout=180)
            record['exit_code'] = result.returncode
        except subprocess.TimeoutExpired:
            record.update(exit_code=None, reason='HOST_TIMEOUT')
        save(root / 'run.json', record)
        checked = verify(root)
        save(root / 'result.json', checked)
        print(checked['status'], checked.get('reason', ''))
        return {'PASS':0, 'FAIL':1, 'BLOCKED':2}[checked['status']]
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
        save(root / 'result.json', {'status':'BLOCKED', 'reason':str(exc)})
        print('BLOCKED:',exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())
