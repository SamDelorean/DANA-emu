#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Audit a private Palm resource updater. Never creates or repairs a Flash image.

Reports hashes, checksums and header fields; optional disassembly stays in the
explicit private report. A candidate payload base is an analysis hypothesis,
never a loader instruction or a claim of recovered physical reset contents.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile


def resources(data):
    if len(data) < 78 or not (int.from_bytes(data[32:34], 'big') & 1):
        raise ValueError('Not a Palm resource database')
    count = int.from_bytes(data[76:78], 'big')
    table_end = 78 + 10 * count
    if table_end > len(data):
        raise ValueError('Truncated resource table')
    entries = [struct.unpack_from('>4sHI', data, 78 + 10 * i) for i in range(count)]
    offsets = [entry[2] for entry in entries] + [len(data)]
    if offsets[0] < table_end or any(a >= b for a, b in zip(offsets, offsets[1:])):
        raise ValueError('Invalid or nonmonotonic resource bounds')
    result = {}
    for i, (kind, number, _) in enumerate(entries):
        key = (kind, number)
        if key in result:
            raise ValueError('Duplicate resource identity')
        result[key] = data[offsets[i]:offsets[i + 1]]
    return result


def payload(entries):
    chunks = sorted((number, data) for (kind, number), data in entries.items() if kind == b'Flas')
    if not chunks:
        raise ValueError('No Flas resources')
    ids = [number for number, _ in chunks]
    if ids != list(range(ids[0], ids[0] + len(ids))):
        raise ValueError('Nonconsecutive Flas IDs; cannot concatenate')
    for number, data in chunks:
        if len(data) < 5 or sum(data[:-4]) & 0xffffffff != int.from_bytes(data[-4:], 'big'):
            raise ValueError(f'Invalid byte-sum checksum in Flas {number}')
    return b''.join(data[:-4] for _, data in chunks), ids


def disassemble(objdump, data, start, count=100):
    if not 0 <= start < len(data):
        raise ValueError('Disassembly target outside supplied payload')
    # Temporary bytes are private input to binutils, never a physical image.
    with tempfile.TemporaryDirectory(prefix='dana-private-audit-') as directory:
        raw = Path(directory) / 'payload'
        raw.write_bytes(data)
        result = subprocess.run([
            objdump, '-D', '-b', 'binary', '-m', 'm68k:68000',
            f'--start-address={start}', f'--stop-address={min(len(data), start + count * 12)}',
            str(raw)], check=True, capture_output=True, text=True)
    instructions = []
    for line in result.stdout.splitlines():
        match = re.match(r'^\s*([0-9a-f]+):\s+(?:[0-9a-f]{4}\s+)+\s*([^\s].*)$', line)
        if match:
            instructions.append({'payload_offset': int(match[1], 16), 'instruction': match[2].strip()})
    return instructions[:count]


def audit(data, candidate_base=None, objdump=None):
    entries = resources(data)
    raw, ids = payload(entries)
    if len(raw) < 0x88 or raw[8:12] != bytes.fromhex('feedbeef'):
        raise ValueError('Missing Palm card signature or incomplete header')
    word = lambda offset: int.from_bytes(raw[offset:offset + 4], 'big')
    pc = word(4)
    report = {
        'status': 'STATIC_ANALYSIS_ONLY', 'full_boot': False,
        'updater_sha256': hashlib.sha256(data).hexdigest(),
        'payload_sha256': hashlib.sha256(raw).hexdigest(), 'payload_bytes': len(raw),
        'flas_count': len(ids), 'flas_first_id': ids[0], 'flas_last_id': ids[-1],
        'all_byte_sum_checksums_valid': True,
        'header_first_longword': word(0), 'header_reset_pc_field': pc,
        'header_longwords': {f'0x{offset:02x}': word(offset) for offset in (0x64, 0x68, 0x6c, 0x7a)},
        'physical_reset_prefix': 'NOT_RECOVERED',
        'candidate_payload_base': candidate_base,
    }
    code = entries.get((b'code', 1), b'')
    report['updater_code1_sha256'] = hashlib.sha256(code).hexdigest()
    if candidate_base is not None:
        report['candidate_entry_payload_offset'] = pc - candidate_base
        report['candidate_base_literal_code1_offsets'] = [
            i for i in range(len(code) - 3) if code[i:i + 4] == candidate_base.to_bytes(4, 'big')]
    if objdump:
        # The existing loader aliases the supplied power-of-two array from zero.
        # 8/4 MiB test arrays do not alter these low 24 address bits.
        report['flat_entry_disassembly'] = disassemble(objdump, raw, pc & 0xffffff)
        if candidate_base is not None:
            report['candidate_entry_disassembly'] = disassemble(objdump, raw, pc - candidate_base)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('updater', type=Path)
    parser.add_argument('--candidate-base', type=lambda value: int(value, 0))
    parser.add_argument('--objdump', help='Optional m68k-capable GNU objdump')
    parser.add_argument('--output', type=Path, required=True, help='Private JSON report; keep outside Git')
    args = parser.parse_args()
    report = audit(args.updater.read_bytes(), args.candidate_base, args.objdump)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f"STATIC_ONLY: {report['flas_count']} resources verified; full_boot=false")


if __name__ == '__main__':
    main()
