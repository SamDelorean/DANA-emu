#!/usr/bin/env python3
"""Independent MMIO-01 verifier: native M68000 bus + handler dispatch; no host-generated PASS."""
import hashlib
import json
from pathlib import Path

from d1_2_verify import initial_ram, PIN, SIZE

START = 0x4000
# Actual instruction-boundary PCs of the assembler-source fixture.
PCS = (0x4000, 0x4006, 0x400a, 0x400c, 0x4012, 0x4014, 0x401a, 0x401c)
IVR = 0xfffff300
NONPAGE = 0xfffef300
ODD_NEIGHBOR = 0xfffff301


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(root):
    root = Path(root)
    report = {'status': 'BLOCKED', 'test': 'MMIO-01',
              'scope': 'D1.3.1 32-bit IVR decode; not VZ IRQ or physical reset'}
    try:
        obs = json.loads((root / 'observation.json').read_text())
        meta = json.loads((root / 'run.json').read_text())
        fixture = (root / 'fixture.bin').read_bytes()
        logs = (root / 'error.log').read_text(errors='replace')
        if obs.get('reason', '').startswith('BLOCKED_BOOTSTRAP'):
            report['reason'] = obs['reason']
            return report
        if obs.get('reason') != 'ENDPOINT_OBSERVED':
            report['reason'] = obs.get('reason', 'No guest endpoint')
            return report
        if not obs.get('bootstrap_prepared'):
            report['reason'] = 'Bootstrap not prepared'
            return report
        if meta.get('exit_code') is None or meta.get('reason') == 'HOST_TIMEOUT':
            report['reason'] = 'No successful bounded MAME invocation'
            return report
        if meta['exit_code'] != 0:
            report.update(status='FAIL', reason='MAME nonzero exit')
            return report

        def check(yes, reason):
            if not yes:
                raise ValueError(reason)

        check(meta['mame_commit'] == PIN, 'Pinned MAME donor mismatch')
        check(obs['schema'] == 'dana-d1-3-mmio01-observation-v1', 'Observation schema')
        check((obs['case'], obs['variant'], obs['run']) == ('MMIO-01', 'diag', 1),
              'Guest fixture identity mismatch')
        check(obs['source_sha'] == meta['source_sha']
              and obs['binary_sha256'] == meta['binary_sha256'], 'Source/binary identity mismatch')
        check(digest(fixture) == obs['fixture_sha256'] == meta['fixture_sha256'],
              'Assembled fixture hash mismatch')
        check(len(fixture) == 30, 'Unexpected assembled fixture extent; inspect M68k disassembly')

        events, stops = obs['events'], obs['stops']
        check(isinstance(events, list) and isinstance(stops, list), 'Missing CPU trace')
        check(len(events) <= 20000 and len(json.dumps(events)) <= 5*1024*1024,
              'CPU trace budget exceeded')
        check([e['seq'] for e in events] == list(range(len(events))), 'Truncated event stream')
        check(len(stops) == len(PCS) and tuple(s['CURPC'] for s in stops) == PCS,
              'Instruction boundary path did not match assembled fixture')
        check(obs['final'] == stops[-1], 'Final CPU state mismatch')
        check(stops[0]['SP'] == 0x8000 and stops[0]['SR'] == 0x2700,
              'Initial supervisor state mismatch')
        check(stops[3]['A0'] == IVR and (stops[3]['D0'] & 0xff) == 0x40,
              'Guest IVR readback/32-bit A0 mismatch')
        check(stops[4]['A0'] == NONPAGE and stops[6]['A0'] == ODD_NEIGHBOR,
              'Guest negative decode target mismatch')

        prepared = [e for e in events if e['kind'] == 'prepared' and e['origin'] == 'fixture']
        check(len(prepared) == 1, 'Fixture preparation not uniquely recorded')
        cpu = [e for e in events if e['origin'] == 'cpu' and e['kind'] in ('read', 'write')]
        check(len(cpu) >= 4 and cpu[0]['seq'] > prepared[0]['seq'],
              'No native CPU activity after preparation')
        vectors = [(e['address'], e['data'], e['mask'], e['kind'])
                   for e in cpu[:4]]
        check(vectors == [(0, 0, 0xffff, 'read'), (2, 0x8000, 0xffff, 'read'),
                          (4, 0, 0xffff, 'read'), (6, 0x4000, 0xffff, 'read')],
              'Native CPU reset vectors incorrect')

        # The MAME 68000 program space is 16-bit, so byte-lane masks are
        # 0xff00 (even) and 0x00ff (odd). Preserve actual CPU bus addresses.
        selected = [e for e in cpu if e['address'] == IVR
                    and e.get('mask') == 0xff00]
        check([e['kind'] for e in selected] == ['write', 'read'],
              'Canonical IVR byte-lane bus write/read not observed in order')
        wrong_page = [e for e in cpu if e['address'] == NONPAGE and e['kind'] == 'read']
        check(len(wrong_page) == 1, 'Other 4-KiB page not reached by native CPU')
        neighbor = [e for e in cpu if e['kind'] == 'read'
                    and (e['address'] == ODD_NEIGHBOR
                         or (e['address'] == IVR and e.get('mask') == 0x00ff))]
        check(len(neighbor) == 1, 'Odd non-register byte not reached by native CPU')
        check(not any(e['kind'] == 'write' and e['address'] in (NONPAGE, ODD_NEIGHBOR)
                      for e in cpu), 'Guest wrote a reserved/unmapped test address')
        check(not any(e['address'] == (IVR & 0xffffff) for e in cpu),
              '24-bit-truncated IVR traffic masqueraded as canonical MMIO')
        check(not any(e['address'] == (NONPAGE & 0xffffff) for e in cpu),
              '24-bit-truncated negative page masqueraded as high MMIO')

        # Only the actual Dana driver handlers, not the Lua tap, log these.
        writes = [line for line in logs.splitlines() if 'DANA_VZ_IVR_WRITE' in line]
        reads = [line for line in logs.splitlines() if 'DANA_VZ_IVR_READ' in line]
        check(len(writes) == 1 and len(reads) == 1,
              'Wrong IVR handler dispatch count (including negative accesses)')
        check('data=40 state=40' in writes[0] and 'state=40' in reads[0],
              'IVR handler storage/mask/readback incorrect')

        initial = (root / 'initial.ram').read_bytes()
        final = (root / 'final.ram').read_bytes()
        check(len(initial) == len(final) == SIZE, 'Full RAM proof unavailable')
        expected = bytearray(SIZE)
        expected[0x10000:0x10010] = b'\xcc'*16
        import struct
        for address, value in ((0, 0x8000), (4, START), (12, 0x5000)):
            struct.pack_into('>I', expected, address, value)
        expected[START:START + len(fixture)] = fixture
        expected[0x5000:0x5004] = bytes.fromhex('4e722700')
        check(initial == expected and final == initial,
              'IVR access aliased/modified synthetic 4-MiB RAM')

        report.update(status='PASS', native_ivrw='one byte write and one byte read',
                      high_address=IVR, guest_readback=0x40,
                      cpu_bus_count=len(cpu), no_ram_alias=True,
                      fixture_sha256=digest(fixture), binary_sha256=meta['binary_sha256'])
    except FileNotFoundError as exc:
        report['reason'] = f'Missing observation or handler log: {exc}'
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        report.update(status='FAIL', reason=str(exc))
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    result = verify(args.run_dir)
    (args.run_dir / 'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'], result.get('reason',''))
    raise SystemExit({'PASS':0, 'FAIL':1, 'BLOCKED':2}[result['status']])
