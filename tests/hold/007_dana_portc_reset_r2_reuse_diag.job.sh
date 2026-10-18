#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# HOLD ONLY. Harness correction; no MAME/ROM build and no historical campaign replay.
set -euo pipefail
if [[ "${DANA_D2_2_R2_AUTHORIZED:-}" != YES ]]; then
    echo 'HOLD: separate D2.2-R2 native authorization required; nothing launched.'
    exit 2
fi
exec python3 - <<'PY_JOB'
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

SOURCE = 'a972f4dfa54bea1e67a212acf79df58c5bff279b'
BUILD_SOURCE = '749517b2f48c9788e5555071561e738017ac5f7c'
BINARY_SHA256 = 'd7bcdf513289a73b8a5c7ab1d258eeac45dc8dd6d89dd7d568cf7784900e6fe5'
PRIOR_ARCHIVE_SHA256 = '2e8b9d0472f4bf803093f0339263c730306e308e31835694ecb64ed5c987b29c'
MAME_PIN = 'c4e48388ca620472643110db2941ce70aa5f3c07'
GIT_URL = 'https://github.com/SamDelorean/DANA-emu.git'
BASE = Path('/home/spc/DANA_EMU_ISOLATED')
BASE.mkdir(exist_ok=True)
root = Path(tempfile.mkdtemp(prefix='portc_reset_r2_', dir=BASE))
evidence = root / 'evidence'
evidence.mkdir()
summary = {'scope': 'D2_2_R2_CPU_ORIGIN_RESET_ONLY',
           'status': 'BLOCKED', 'reason': 'NOT_RUN', 'native_status': 'PENDING',
           'source_commit': SOURCE, 'binary_build_source': BUILD_SOURCE,
           'mame_pin_from_qualified_baseline': MAME_PIN,
           'prior_archive_sha256': PRIOR_ARCHIVE_SHA256,
           'expected_binary_sha256': BINARY_SHA256,
           'MAME_builds': 0, 'ROM_builds': 0, 'stages': {}}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save():
    (evidence/'job_result.json').write_text(json.dumps(summary, indent=2)+'\n')


def stage(name, command, cwd=None, env=None, timeout=180, accepted=(0,)):
    rec = {'command': command, 'cwd': str(cwd) if cwd else None, 'timeout_seconds': timeout}
    summary['stages'][name] = rec
    save()
    with (evidence/(name+'.log')).open('wb') as log:
        try:
            p = subprocess.run(command, cwd=cwd, env=env, stdout=log,
                               stderr=subprocess.STDOUT, timeout=timeout)
            rec['exit_code'] = p.returncode
        except subprocess.TimeoutExpired:
            rec['exit_code'] = None
            rec['reason'] = 'HOST_TIMEOUT'
            save()
            raise RuntimeError('BLOCKED_'+name+'_TIMEOUT')
    save()
    if rec['exit_code'] not in accepted:
        raise RuntimeError('STAGE_'+name+'_EXIT_'+str(rec['exit_code']))
    return rec['exit_code']

exit_code = 2
try:
    # Explicit read-only reference path; no discovery on T and no rebuild fallback.
    supplied = os.environ.get('DANA_D2_2_R2_BINARY', '')
    if not supplied:
        raise RuntimeError('BLOCKED_EXPLICIT_STAGED_DIAG_REFERENCE_REQUIRED')
    original = Path(supplied)
    if (not original.is_absolute() or original.resolve()!=original or
        original.name!='dana-diag' or original.parent.name!='bin' or
        original.parent.parent.name!='diag' or not original.is_file() or
        not os.access(original, os.X_OK)):
        raise RuntimeError('BLOCKED_DIAG_REFERENCE_IDENTITY')
    if digest(original)!=BINARY_SHA256:
        raise RuntimeError('BLOCKED_QUALIFIED_DIAG_BINARY_SHA256_MISMATCH_NO_REBUILD')
    source = root/'code'
    source.mkdir()
    stage('git-init', ['git','init',str(source)])
    for name, sha in (('harness',SOURCE),('qualified-build',BUILD_SOURCE)):
        stage('fetch-'+name, ['git','-C',str(source),'fetch','--depth=1',GIT_URL,sha],timeout=400)
    stage('checkout-harness', ['git','-C',str(source),'checkout','--detach',SOURCE])
    got = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if got!=SOURCE:
        raise RuntimeError('BLOCKED_HARNESS_SOURCE_PIN_MISMATCH')
    # Prove the reused binary remains applicable: every production/build input
    # owned by DANA-emu has the same Git tree as the qualified build source.
    trees = {}
    for name in ('src','overlays','tests/d1_1_diag_smoke.sh'):
        pair = [subprocess.check_output(['git','-C',str(source),'rev-parse',sha+':'+name],
                                        text=True).strip() for sha in (BUILD_SOURCE,SOURCE)]
        if pair[0]!=pair[1]:
            raise RuntimeError('BLOCKED_PRODUCTION_SOURCE_CHANGED_NO_BINARY_REUSE:'+name)
        trees[name] = pair[0]
    summary['matching_production_trees'] = trees
    binary = root/'diag'/'bin'/'dana-diag'
    binary.parent.mkdir(parents=True)
    shutil.copy2(original,binary)
    if digest(binary)!=BINARY_SHA256 or digest(original)!=BINARY_SHA256:
        raise RuntimeError('BLOCKED_BINARY_CHANGED_DURING_READ_ONLY_COPY')
    summary['binary'] = {'reference_path':str(original),'staged_path':str(binary),
                         'sha256':digest(binary),'reference_modified':False}
    save()
    # Offline evidence tests use Python only. Lua lifecycle tests have already
    # been qualified before freezing this job; the existing DIAG embeds Lua.
    stage('offline-verifiers', ['python3','-m','unittest','d2_2_r2_test_reset_cpu.CPUResetVerifier',
          'd2_2_r2_test_reset_cpu.FixtureContract.test_qualified_A_code_and_Lua_are_unchanged',
          'd2_2_r2_test_reset_cpu.FixtureContract.test_independently_assembled_layout_and_corrected_displacement','-v'],cwd=source,
          env=dict(os.environ,PYTHONPATH=str(source/'tests')))
    stage('native-portc-two-processes', ['python3','tests/d2_2_gpio_run.py',str(binary),
          str(evidence/'portc')],cwd=source,timeout=220,accepted=(0,1,2))
    # Re-read raw evidence through the independent verifier; process exit and
    # the runner's summary alone cannot establish reset PASS.
    sys.path.insert(0,str(source/'tests'))
    from d2_2_r2_gpio import verify
    verified = verify(evidence/'portc')
    summary['native_result'] = verified
    summary['native_status'] = verified['status']
    summary['status'] = verified['status']
    summary['reason'] = verified['reason']
    exit_code = {'PASS':0,'FAIL':1,'BLOCKED':2}[verified['status']]
    if digest(original)!=BINARY_SHA256 or digest(binary)!=BINARY_SHA256:
        summary.update(status='FAIL',reason='BINARY_IDENTITY_CHANGED_DURING_QUALIFICATION')
        exit_code = 1
except (OSError,ValueError,RuntimeError,KeyError,subprocess.SubprocessError) as exc:
    summary['reason'] = str(exc)
    if summary['stages'].get('offline-verifiers',{}).get('exit_code')==1:
        summary['status'] = 'FAIL'
        exit_code = 1
finally:
    save()
    inventory = {str(p.relative_to(evidence)):digest(p) for p in evidence.rglob('*') if p.is_file()}
    (evidence/'evidence_sha256.json').write_text(json.dumps(inventory,indent=2,sort_keys=True)+'\n')
    archive = root/(root.name+'.tar.gz')
    with tarfile.open(archive,'w:gz') as output:
        output.add(evidence,arcname='evidence')
    checksum = root/'archive.sha256'
    checksum.write_text(digest(archive)+'  '+archive.name+'\n')
    # Preserve the proven Drive outbox transport only; never touch inbox or
    # dispatch/Commander. Upload errors leave the complete local evidence intact.
    upload = 'BLOCKED'
    try:
        if not shutil.which('rclone'):
            raise RuntimeError('RCLONE_MISSING')
        remote = 'googledrive:AS2K_TEMP/COMMANDER_PIPELINE/outbox/'+root.name
        for local, suffix in ((archive,archive.name),(checksum,'archive.sha256')):
            subprocess.run(['rclone','copyto',str(local),remote+'/'+suffix],check=True,timeout=800)
        upload = 'UPLOADED'
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
        (root/'upload_error.txt').write_text(str(exc)+'\n')
        if exit_code==0:exit_code=2
    print(json.dumps({'status':summary['status'],'native_status':summary['native_status'],
                      'exit_code':exit_code,'archive_sha256':digest(archive),
                      'evidence':str(root),'upload':upload},sort_keys=True))
sys.exit(exit_code)
PY_JOB
