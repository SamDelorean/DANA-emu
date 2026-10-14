#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Prepare isolated source trees or verify two real, separately built products.
set -euo pipefail
exec python3 - "$0" "$@" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

PIN = 'c4e48388ca620472643110db2941ce70aa5f3c07'
DRIVER = 'src/mame/skeleton/alphasdana.cpp'
LIST = 'src/mame/mame.lst'
PROJECT = Path(sys.argv[1]).resolve().parents[1]
FRAGMENT = (PROJECT / 'overlays/mame-driverlist/alphasdana.lst.fragment').read_bytes()
assert FRAGMENT == b'@source:skeleton/alphasdana.cpp\nasmdana\n'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

args = sys.argv[2:]
if len(args) == 3 and args[0] == 'prepare':
    reference, root = Path(args[1]).resolve(), Path(args[2]).resolve()
    if root.exists() or root == reference or reference in root.parents:
        sys.exit('Refusing existing destination or destination inside reference checkout')
    subprocess.run(['git', '-C', str(reference), 'cat-file', '-e', PIN + '^{commit}'], check=True)
    original = subprocess.check_output(['git', '-C', str(reference), 'show', PIN + ':' + LIST])
    if b'asmdana' in original or b'alphasdana.cpp' in original:
        sys.exit('Pinned source has a Dana registration collision')
    anchor = b'@source:skeleton/alphasma.cpp\n'
    if original.count(anchor) != 1:
        sys.exit('Expected unique insertion anchor missing')
    updated = original.replace(anchor, FRAGMENT + b'\n' + anchor, 1)
    assert updated.replace(FRAGMENT + b'\n', b'', 1) == original
    for variant, target, debug in [('stable', 'danastable', ''), ('diag', 'danadiag', ' DEBUG=1')]:
        source = root / variant / 'source'
        source.mkdir(parents=True)
        archive = subprocess.Popen(['git', '-C', str(reference), 'archive', PIN], stdout=subprocess.PIPE)
        try:
            unpack = subprocess.run(['tar', '-x', '-C', str(source)], stdin=archive.stdout)
        finally:
            archive.stdout.close()
        archive_rc = archive.wait()
        if unpack.returncode or archive_rc:
            sys.exit('BLOCKED: source extraction failed; preserve partial staging for diagnosis')
        if (source / DRIVER).exists():
            sys.exit('Pinned source driver collision')
        (source / DRIVER).write_bytes((PROJECT / DRIVER).read_bytes())
        (source / LIST).write_bytes(updated)
        save(root / variant / 'source-manifest.json', {
            'mame_commit': PIN, 'driver_sha256': digest(source / DRIVER),
            'baseline_list_sha256': hashlib.sha256(original).hexdigest(),
            'list_sha256': digest(source / LIST), 'variant': variant,
            'status': 'PREPARED_NOT_BUILT'})
        command = ('make -j3 TARGET=mame SUBTARGET=' + target + ' SOURCES=' + DRIVER
                   + ' BUILDDIR=build/dana-' + variant + ' REGENIE=1 TOOLS=0' + debug)
        print('Working directory:', source)
        print(command)
    print('Prepared identical overlays in separate trees. Build stable, then diag; never concurrently.')
    sys.exit(0)

if len(args) != 4 or args[0] != 'verify':
    sys.exit('Usage: d1_1_build_select_smoke.sh prepare REFERENCE NEW_STAGE_ROOT\n'
             '   or: d1_1_build_select_smoke.sh verify STABLE_BINARY DIAG_BINARY NEW_EVIDENCE_ROOT')

stable, diag, evidence = map(lambda p: Path(p).resolve(), args[1:])
if evidence.exists():
    sys.exit('Refusing existing evidence destination; use a fresh run directory')
evidence.mkdir(parents=True)
results = {}
shared = stable == diag or stable.parent == diag.parent
for variant, binary in [('stable', stable), ('diag', diag)]:
    work = evidence / variant
    work.mkdir()
    result = {'variant': variant, 'binary': str(binary), 'binary_sha256': None,
              'status': 'BLOCKED', 'checks': {}, 'reason': None}
    if shared:
        result['reason'] = 'Executable destinations must be distinct, with separate directories'
    elif not binary.is_file() or not os.access(binary, os.X_OK):
        result['reason'] = 'Compiled executable missing or not executable'
    else:
        result['binary_sha256'] = digest(binary)
        try:
            stage = binary.parent.parent
            provenance = json.loads((stage / 'source-manifest.json').read_text())
            source = stage / 'source'
            assert provenance['mame_commit'] == PIN and provenance['variant'] == variant, 'Wrong source provenance'
            assert provenance['driver_sha256'] == digest(source / DRIVER) == digest(PROJECT / DRIVER), 'Driver hash mismatch'
            assert provenance['list_sha256'] == digest(source / LIST), 'Staged registration list changed'
            listing = (source / LIST).read_bytes()
            assert listing.count(FRAGMENT) == 1, 'Missing or duplicated Dana registration'
            assert hashlib.sha256(listing.replace(FRAGMENT + b'\n', b'', 1)).hexdigest() == provenance['baseline_list_sha256'], 'Existing registrations changed'
            assert all(listing.splitlines().count(name) == 1 for name in (b'asma2k', b'asma3k')), 'AS2K/AS3K registration missing'
            result['source_provenance'] = provenance
            result['checks']['registration_preservation'] = {'status': 'PASS'}
            commands = [('listfull', ['-listfull', 'asmdana']),
                        ('listxml', ['-listxml', 'asmdana']),
                        ('validate', ['-validate', 'asmdana'])]
            for name, flags in commands:
                with (work / (name + '.log')).open('wb') as log:
                    run = subprocess.run([str(binary), '-noreadconfig', *flags], cwd=work,
                                         stdout=log, stderr=subprocess.STDOUT, timeout=120)
                result['checks'][name] = {'exit_code': run.returncode}
                if run.returncode:
                    raise ValueError(name + ' command failed')
            rows = [line for line in (work / 'listfull.log').read_text().splitlines()
                    if line.split() and line.split()[0] == 'asmdana']
            assert len(rows) == 1, 'Expected exactly one asmdana enumeration'
            # MAME also emits device definitions; only machine drivers count.
            machines = [m for m in ET.fromstring((work / 'listxml.log').read_text()).findall('machine')
                        if m.get('isdevice') != 'yes']
            assert len(machines) == 1 and machines[0].get('name') == 'asmdana', 'Unexpected machine'
            machine = machines[0]
            assert machine.get('sourcefile') == 'skeleton/alphasdana.cpp', 'Unexpected source driver'
            assert machine.findtext('description') == 'AlphaSmart Dana (D1.1 skeleton)', 'Unexpected description'
            assert not machine.findall('rom'), 'Skeleton must not require guest ROM'
            cpus = [chip for chip in machine.findall('chip') if chip.get('type') == 'cpu']
            assert len(cpus) == 1 and cpus[0].get('clock') == '1000000' and cpus[0].get('name') == 'Motorola MC68000', 'Unexpected placeholder CPU configuration'
            assert machine.find('driver').get('status') == 'preliminary', 'Expected nonworking skeleton'
            result['status'] = 'PASS'
        except subprocess.TimeoutExpired:
            result['reason'] = 'Command timed out'
        except FileNotFoundError as error:
            result['reason'] = 'Missing prerequisite: ' + str(error)
        except (OSError, ValueError, AssertionError, ET.ParseError, AttributeError, KeyError) as error:
            result['status'] = 'FAIL'
            result['reason'] = str(error)
    save(work / 'manifest.json', result)
    save(work / 'result.json', result)
    results[variant] = result
# Registration preservation is established from each prepared tree and its
# pinned-source manifest above; verification never opens a reference checkout.
registration_results = {
    variant: result['checks'].get('registration_preservation', {
        'status': 'FAIL' if result['status'] == 'FAIL' else 'BLOCKED',
        'reason': result['reason']})
    for variant, result in results.items()
}
registration_statuses = [r['status'] for r in registration_results.values()]
regression = {
    'status': ('FAIL' if 'FAIL' in registration_statuses else
               'BLOCKED' if 'BLOCKED' in registration_statuses else 'PASS'),
    'scope': 'Prepared pinned-source manifests and staged lists only; no AS2K runtime claim',
    'variants': registration_results}
statuses = [r['status'] for r in results.values()] + [regression['status']]
status = 'FAIL' if 'FAIL' in statuses else 'BLOCKED' if 'BLOCKED' in statuses else 'PASS'
save(evidence / 'result.json', {'status': status, 'scope': 'Binary smoke assertions only; not D1.1 qualification',
                             'variants': results, 'registration_preservation': regression})
print(status + ': ' + str(evidence / 'result.json'))
sys.exit({'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[status])
PY
