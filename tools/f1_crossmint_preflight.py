#!/usr/bin/env python3
"""Offline preflight for a MiNT or ELF -mshort compiler and libgcc (no installs)."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def check(prefix):
    gcc = shutil.which(prefix + 'gcc')
    result = {'status': 'BLOCKED', 'compiler': gcc, 'prefix': prefix, 'checks': {}}
    if not gcc:
        result['reason'] = 'CROSS_GCC_NOT_INSTALLED'
        return result
    for program in (prefix + 'as', prefix + 'ld', prefix + 'objcopy'):
        if not shutil.which(program):
            result['reason'] = 'MISSING_BINUTIL: ' + program
            return result

    def run(command):
        completed = subprocess.run(command, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, timeout=90)
        if completed.returncode:
            raise RuntimeError('COMMAND_FAILED: ' + command[0] + ' ' + completed.stdout[:500])
        return completed.stdout.strip()

    try:
        result['checks']['version'] = run([gcc, '--version']).splitlines()[0]
        target = run([gcc, '-dumpmachine'])
        result['checks']['target'] = target
        expected = {'m68k-atari-mint-': 'm68k-atari-mint',
                    'm68k-elf-': 'm68k-elf'}.get(prefix)
        if not expected or target != expected:
            raise RuntimeError('WRONG_TARGET: expected ' + str(expected) + ', got ' + target)
        multilib = run([gcc, '-print-multi-lib'])
        result['checks']['multilib'] = multilib
        if 'mshort' not in multilib:
            raise RuntimeError('MISSING_MSHORT_MULTILIB')
        libgcc = run([gcc, '-m68000', '-mshort', '-print-libgcc-file-name'])
        result['checks']['libgcc'] = libgcc
        if libgcc == 'libgcc.a' or not Path(libgcc).is_file():
            raise RuntimeError('MISSING_MSHORT_LIBGCC')
        with tempfile.TemporaryDirectory(prefix='dana_f1_cross_probe_') as directory:
            source = Path(directory) / 'probe.c'
            object_file = Path(directory) / 'probe.o'
            binary = Path(directory) / 'probe.prg'
            source.write_text(
                'typedef char abi_int2[(sizeof(int)==2)?1:-1];\n'
                'typedef char abi_long4[(sizeof(long)==4)?1:-1];\n'
                'volatile long a=12345,b=6789;\n'
                'void _start(void) { volatile long c=a*b; (void)c; for(;;) {} }\n')
            run([gcc, '-m68000', '-mshort', '-ffreestanding',
                 '-c', str(source), '-o', str(object_file)])
            run([gcc, '-m68000', '-mshort', '-nostartfiles', '-nostdlib',
                 str(object_file), '-lgcc', '-o', str(binary)])
            if not object_file.is_file() or not binary.is_file() or not binary.stat().st_size:
                raise RuntimeError('MISSING_PROBE_OUTPUT')
            result['checks']['compiled_abi_int2_long4'] = 'PASS'
            result['checks']['linked_libgcc_mshort'] = 'PASS'
        result['status'] = 'PASS'
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        result['reason'] = str(error)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', default='m68k-atari-mint-')
    parser.add_argument('--result', type=Path)
    args = parser.parse_args()
    result = check(args.prefix)
    encoded = json.dumps(result, indent=2) + '\n'
    if args.result:
        args.result.write_text(encoded)
    print(encoded, end='')
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
