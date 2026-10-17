#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# DANA D2.1 PLLFSR — HOLD until separately authorized. DIAG-only; never rebuild ROM / EmuTOS.
set -euo pipefail
exec python3 - <<'PY_JOB'
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

# Exact previously qualified production source and hardware donor.
SOURCE = '621c83df2aa1a1b614f3f4b5351a59ef8365f537'
DONOR_PIN = 'c4e48388ca620472643110db2941ce70aa5f3c07'
GUEST_PIN = '9c42ef0f2c2fa9d1e217fced9da68901b2326e8b'
BASE = Path('/home/spc/DANA_EMU_ISOLATED')
DONOR = Path('/home/spc/Projects/alphasmart/as2k-stable-eeepc900-local/mame-as3k-donor')
PRIVATE = Path('/home/spc/Projects/alphasmart/private/roms/dana')
PRESERVED = BASE / 'f1_e1e2_baldoi9k' / 'emutos-built'
EXPECTED = {
    'emutos.img': ('ba590da2661bc582c19bb24d65db04667daf37a17d7aa51fb462b945933ba0a3', 223748),
    'emutos-dana.rom': ('efb055e5ac02526db069aec23c4b71b092fc48317aa4305e93a4a2f4e369243c', 223792),
    'emutos.map': ('17cc980e675e2e1b50e713b9029f6fc3e51d3e55392deb99d53552d4b3af3e68', 124540),
    'emutos.dana': ('c201c8527df87fa6a8788d8ac59f43298666196fefeee12dcac68295cb281b9d', 223812),
}
BASE.mkdir(exist_ok=True)
root = Path(tempfile.mkdtemp(prefix='d2_1_pllfsr_', dir=BASE))
evidence = root / 'evidence'
evidence.mkdir()
summary = {
    'scope': 'D2_1_VZ_PLLFSR_REAL_DIAG_ONLY',
    'status': 'BLOCKED',
    'reason': 'NOT_RUN',
    'source_commit': SOURCE,
    'mame_donor_commit': DONOR_PIN,
    'original_guest_commit': GUEST_PIN,
    'emutos_build_policy': 'STRICT_REUSE_NO_RECOMPILE',
    'private_rom_path': str(PRIVATE),
    'run_root': str(root),
    'stages': {},
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save():
    (evidence / 'job_result.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')


def stage(name, argv, cwd=None, env=None, timeout=300, accepted=(0,)):
    rec = {'command': argv, 'cwd': str(cwd) if cwd else None, 'time_limit': timeout}
    summary['stages'][name] = rec
    save()
    try:
        with (evidence / (name + '.log')).open('wb') as f:
            proc = subprocess.run(argv, cwd=cwd, env=env, stdout=f,
                                  stderr=subprocess.STDOUT, timeout=timeout)
        rec['exit_code'] = proc.returncode
        save()
        if proc.returncode not in accepted:
            raise RuntimeError('STAGE_' + name.upper().replace('-', '_') + '_EXIT_' + str(proc.returncode))
        return proc.returncode
    except subprocess.TimeoutExpired:
        rec['reason'] = 'HOST_TIMEOUT'
        rec['exit_code'] = None
        save()
        raise RuntimeError('STAGE_' + name.upper().replace('-', '_') + '_TIMEOUT')


def verify_pin(checkout, sha):
    got = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    if got != sha:
        raise RuntimeError('PIN_MISMATCH:' + str(checkout))


def verify_files(directory, category):
    if not directory.is_dir():
        raise RuntimeError('MISSING_' + category + '_DIRECTORY:' + str(directory))
    facts = {}
    for name, (wanted, size) in EXPECTED.items():
        p = directory / name
        if not p.is_file() or p.stat().st_size != size:
            raise RuntimeError('MISSING_OR_SIZE_MISMATCH_' + category + ':' + name)
        sha = digest(p)
        if sha != wanted:
            raise RuntimeError('SHA256_MISMATCH_' + category + ':' + name)
        facts[name] = {'bytes': size, 'sha256': sha}
    summary['inputs_' + category.lower()] = facts
    save()

exit_code = 2
try:
    # E1/E2 are immutable inputs now. Verify BOTH canonical private copy and
    # original build before reading any source or spending time on MAME.
    verify_files(PRIVATE, 'PRIVATE')
    verify_files(PRESERVED, 'PRESERVED')
    guest = root / 'guest'
    guest.mkdir()
    for name in EXPECTED:
        shutil.copyfile(PRESERVED / name, guest / name)
    for name in ('guest_manifest.json', 'build_provenance.json'):
        src = PRESERVED / name
        if not src.is_file():
            raise RuntimeError('MISSING_PRESERVED_PROVENANCE:' + name)
        shutil.copyfile(src, guest / name)
    verify_files(guest, 'STAGED')
    prov = json.loads((guest / 'build_provenance.json').read_text())
    if prov.get('source_commit') != GUEST_PIN or prov.get('exit_code') != 0:
        raise RuntimeError('GUEST_PROVENANCE_MISMATCH')
    # The shared donor may legitimately have moved its active HEAD. Never
    # reset/checkout/mutate it. Qualification uses only the immutable pinned
    # MAME object via the existing d1_1_diag_smoke.sh git-archive workflow.
    active_donor_head = subprocess.check_output(
        ['git', '-C', str(DONOR), 'rev-parse', 'HEAD'], text=True).strip()
    pinned_donor_object = subprocess.check_output(
        ['git', '-C', str(DONOR), 'rev-parse', '--verify', DONOR_PIN + '^{commit}'],
        text=True).strip()
    if pinned_donor_object != DONOR_PIN:
        raise RuntimeError('BLOCKED_DONOR_PINNED_OBJECT_UNAVAILABLE')
    summary['donor'] = {'active_head': active_donor_head,
        'pinned_archive_commit': pinned_donor_object,
        'mutated_shared_donor': False}
    save()

    source = root / 'code'
    source.mkdir()
    stage('git-init', ['git', 'init', str(source)])
    stage('fetch-pinned-source', ['git', '-C', str(source), 'fetch', '--depth=1',
                                   'https://github.com/SamDelorean/DANA-emu.git', SOURCE], timeout=400)
    stage('checkout-pinned-source', ['git', '-C', str(source), 'checkout', '--detach', 'FETCH_HEAD'])
    verify_pin(source, SOURCE)
    stage('validate-original-guest', ['python3', 'tools/f1_guest.py', 'validate', str(guest)], cwd=source)
    stage('unit-input', ['python3', 'tests/f1_test_guest.py', '-v'], cwd=source)
    stage('unit-ram', ['python3', 'tests/d1_2_test_verifier.py'], cwd=source)
    stage('unit-mmio', ['python3', 'tests/d1_3_1_mmio01_test_verifier.py'], cwd=source)
    # Compile/run the actual PLLFSR handlers before the costly native MAME build.
    stage('unit-pllfsr-actual-cpp', ['python3', 'tests/d2_1_pllfsr_contract_test.py'], cwd=source, timeout=180)

    cc = next((shutil.which(x) for x in ('clang-21', 'clang') if shutil.which(x)), None)
    cxx = next((shutil.which(x) for x in ('clang++-21', 'clang++') if shutil.which(x)), None)
    mc = next((shutil.which(x) for x in ('llvm-mc-21', 'llvm-mc') if shutil.which(x)), None)
    objcopy = next((shutil.which(x) for x in ('llvm-objcopy-21', 'llvm-objcopy') if shutil.which(x)), None)
    if not all((cc, cxx, mc, objcopy)):
        raise RuntimeError('BLOCKED_MAME_LLVM21_TOOLCHAIN_MISSING')
    # LLVM tools do not guarantee the version appears on the FIRST line:
    # llvm-objcopy typically first prints 'compatible with GNU objcopy' and
    # names its LLVM version on a subsequent line. Keep strict v21 pinning,
    # but inspect the complete bounded --version output, not line zero.
    executables = {'cc': cc, 'cxx': cxx, 'mc': mc, 'objcopy': objcopy}
    versions = {}
    for name, exe in executables.items():
        version_text = subprocess.check_output([exe, '--version'], text=True, timeout=15)
        if len(version_text) > 32768 or not version_text.strip():
            raise RuntimeError('BLOCKED_MAME_LLVM_TOOL_OUTPUT_INVALID:' + name)
        versions[name] = {'executable': exe, 'version_lines': version_text.splitlines()[:8],
                          'is_llvm21': bool(re.search(r'\b21(?:\.|\b)', version_text))}
    summary['llvm21_tools'] = versions
    save()
    if not all(entry['is_llvm21'] for entry in versions.values()):
        raise RuntimeError('BLOCKED_MAME_LLVM21_TOOLCHAIN_VERSION:' +
                           ','.join(name for name,entry in versions.items() if not entry['is_llvm21']))

    stage_root = root / 'mame-stage'
    stage('prepare-diag', ['bash', 'tests/d1_1_diag_smoke.sh', 'prepare', str(DONOR), str(stage_root)],
          cwd=source, timeout=900)
    binary = stage_root / 'diag' / 'bin' / 'dana-diag'
    binary.parent.mkdir()
    mame_root = stage_root / 'diag' / 'source'
    stage('build-updated-diag', ['make', '-j3', 'TARGET=mame', 'SUBTARGET=danadiag',
           'SOURCES=src/mame/skeleton/alphasdana.cpp', 'BUILDDIR=build/dana-diag',
           'REGENIE=1', 'TOOLS=0', 'DEBUG=1', 'PRECOMPILE=0', 'USE_QTDEBUG=0',
           'OVERRIDE_CC=' + cc, 'OVERRIDE_CXX=' + cxx, 'OVERRIDE_LD=' + cxx],
          cwd=mame_root, env=dict(os.environ, CC=cc, CXX=cxx, LD=cxx), timeout=7200)
    built = mame_root / 'danadiagd'
    if not built.is_file() or not os.access(built, os.X_OK):
        raise RuntimeError('BLOCKED_DIAG_BUILT_BINARY_NOT_FOUND')
    shutil.copy2(built, binary)
    summary['binary'] = {'path': str(binary), 'sha256': digest(binary),
                         'driver_sha256': digest(source / 'src/mame/skeleton/alphasdana.cpp')}
    save()

    # Functional regression checks run on the freshly built linked production
    # binary only. No result is promoted from unit tests or the old R7 build.
    stage('diag-smoke', ['bash', 'tests/d1_1_diag_smoke.sh', 'verify', str(binary), str(evidence / 'smoke')],
          cwd=source, timeout=400)
    stage('ram-regression', ['python3', 'tests/f1_regress.py', str(binary), str(evidence / 'ram')],
          cwd=source, timeout=650)
    stage('mmio-regression', ['python3', 'tests/d1_3_1_mmio01_run.py', str(binary), str(evidence / 'mmio')],
          cwd=source, timeout=400)
    stage('authentic-guest', ['python3', 'tests/f1_emutos_run.py', str(binary), str(guest),
                              str(evidence / 'guest')],
          cwd=source, timeout=650, accepted=(0, 1, 2))
    actual = json.loads((evidence / 'guest' / 'result.json').read_text())
    summary['guest_result'] = actual
    if actual['status'] == 'FAIL' or actual.get('repeat') == 'FAIL':
        summary['status'] = 'FAIL'
        summary['reason'] = 'GUEST_PRODUCT_OR_DETERMINISM_REGRESSION'
        exit_code = 1
    else:
        valid_runs = (len(actual.get('runs', [])) == 2 and
            all(run.get('guest_execution', {}).get('status') == 'PASS' for run in actual['runs']))
        rejected = actual.get('native_rejection', {}).get('status') == 'PASS'
        reproducible = actual.get('repeat') == 'PASS'
        hardware = all(run.get('domain') == 'HARDWARE' for run in actual.get('runs', []))
        # Do not claim a PLLFSR PASS merely because the next unimplemented
        # peripheral was hit; demand a genuine 16-bit, CPU-origin PLLFSR read
        # in BOTH saved real MAME execution traces.
        cpu_pll_reads = [
            [e for e in run.get('normalized', {}).get('bus', [])
             if e.get('kind') == 'read' and e.get('address') == 0xfffff202
             and (e.get('mask') == 0xffff or e.get('mask') is None)]
            for run in actual.get('runs', [])]
        pll_observed = len(cpu_pll_reads) == 2 and all(cpu_pll_reads)
        next_dependencies = [run.get('dependency') for run in actual.get('runs', [])]
        pll_no_longer_blocker = all(dep and dep.get('address') != 0xfffff202
                                   for dep in next_dependencies)
        summary['pllfsr_d2_1'] = {
            'native_word_read_in_each_run': bool(pll_observed),
            'cpu_word_read_counts': [len(a) for a in cpu_pll_reads],
            'next_dependencies': next_dependencies,
            'no_repeat_of_original_blocker': bool(pll_no_longer_blocker),
            'reset': '0x0347',
            'clock_source': 'virtual_time_32768_hz',
            'rom_rebuilds': 0,
        }
        if valid_runs and rejected and reproducible and hardware and pll_observed and pll_no_longer_blocker:
            summary['status'] = 'PASS_PLLFSR_GUEST_ADVANCED_TO_NEXT_HARDWARE'
            summary['reason'] = 'NEXT_REAL_VZ_DEVICE_DEPENDENCY_REPRODUCED'
            exit_code = 0
        else:
            summary['status'] = 'BLOCKED'
            summary['reason'] = 'PLLFSR_NATIVE_ADVANCE_NOT_YET_PROVED'
            exit_code = 2
except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyError) as exc:
    summary['reason'] = str(exc)
    # Genuine failed regression is a FAIL; missing preconditions are BLOCKED.
    for label in ('unit-input', 'unit-ram', 'unit-mmio', 'unit-pllfsr-actual-cpp', 'diag-smoke', 'ram-regression', 'mmio-regression'):
        if summary['stages'].get(label, {}).get('exit_code') == 1:
            summary['status'] = 'FAIL'
            exit_code = 1
finally:
    save()
    checksum = {}
    for p in evidence.rglob('*'):
        if p.is_file() and p.name != 'evidence_sha256.json':
            checksum[str(p.relative_to(evidence))] = digest(p)
    (evidence / 'evidence_sha256.json').write_text(json.dumps(checksum, indent=2, sort_keys=True) + '\n')
    archive = root / (root.name + '.tar.gz')
    with tarfile.open(archive, 'w:gz') as output:
        output.add(evidence, arcname='evidence')
        for name in ('guest_manifest.json', 'build_provenance.json'):
            p = root / 'guest' / name
            if p.is_file():
                output.add(p, arcname='guest/' + name)
    archive_sha = digest(archive)
    (root / 'archive.sha256').write_text(archive_sha + '  ' + archive.name + '\n')
    upload_status = 'BLOCKED'
    try:
        if not shutil.which('rclone'):
            raise RuntimeError('RCLONE_MISSING')
        remote = 'googledrive:AS2K_TEMP/COMMANDER_PIPELINE/outbox/' + root.name
        send = subprocess.run(['rclone', 'copyto', str(archive), remote + '/' + archive.name], timeout=800)
        send_hash = subprocess.run(['rclone', 'copyto', str(root / 'archive.sha256'), remote + '/archive.sha256'], timeout=160)
        if send.returncode or send_hash.returncode:
            raise RuntimeError('EVIDENCE_UPLOAD_FAILED')
        upload_status = 'UPLOADED'
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        summary['upload_problem'] = str(exc)
        save()
        if exit_code == 0:
            exit_code = 2
    print(json.dumps({'job_status': summary['status'], 'exit_code': exit_code,
                      'evidence': str(root), 'archive_sha256': archive_sha,
                      'upload': upload_status}, sort_keys=True))
sys.exit(exit_code)
PY_JOB
