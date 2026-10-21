#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Local Git HOLD. ONE integrated 012-E observation, zero builds and no fallback.
set -euo pipefail
if [[ "${DANA_012E_AUTHORIZED:-}" != YES ]]; then
    echo 'HOLD: fresh scoped 012-E native authorization required; nothing executed or transported.'
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

SOURCE='096099119eef630651c6b242ae873ebd0ab3f26e'
BUILD_SOURCE='581601b49acb6603af2a100817d0f06fed17ed96'
HISTORICAL_SOURCE='56a0a0040edfc161e45c1131692a64c3649fe3af'
BINARY_SHA='caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37'
MANIFEST_SHA='504530b8ba90549fc6cfd5dc7ec7505ff013ee025daceec9c60dc26a4e4988de'
QUALIFICATION_SHA='6fda7a9474c7594ae1019fea33766ad65c99d9e81a5d323ec1e1f6b5ba914131'
ARCHIVE_SHA='1fc1d8417eea975c80f29a74aa53e6ccc8fd835b2d2cc924951afec748364a18'
BASE=Path('/home/spc/DANA_EMU_ISOLATED')
PRIOR=BASE/'dana_timer_uart_irq_hmkem769'
ORIGINAL_ARCHIVE=PRIOR/(PRIOR.name+'.tar.gz')
QUALIFICATION=PRIOR/'evidence/binary_qualification.json'
BINARY=PRIOR/'mame-stage/diag/bin/dana-diag'
MANIFEST=BINARY.parent.parent/'source-manifest.json'
GUEST=BASE/'f1_e1e2_baldoi9k/emutos-built'
root=Path(tempfile.mkdtemp(prefix='dana_012e_observe_',dir=BASE))
evidence=root/'evidence';evidence.mkdir()
summary=dict(scope='012-E_BOUNDED_INTEGRATED_NATIVE_OBSERVATION',status='BLOCKED',reason='NOT_RUN',
             native_status='NATIVE_PENDING',source_commit=SOURCE,binary_build_source=BUILD_SOURCE,
             binary_sha256=BINARY_SHA,MAME_builds=0,ROM_builds=0,Commander_calls_in_job=0,full_boot=False,stages={})

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(): (evidence/'job_result.json').write_text(json.dumps(summary,indent=2)+'\n')
def stage(name,command,cwd=None,timeout=180,accepted=(0,),env=None):
    summary['stages'][name]=dict(command=command,timeout_seconds=timeout);save()
    try:
        with (evidence/(name+'.log')).open('wb') as log:
            run=subprocess.run(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        code=run.returncode
    except subprocess.TimeoutExpired:code=None
    summary['stages'][name]['exit_code']=code;save()
    if code not in accepted:raise RuntimeError('BLOCKED_STAGE:'+name+':'+str(code))

def require_hash(path,expected):
    if not path.is_file() or path.is_symlink() or digest(path)!=expected:raise ValueError('IMMUTABLE_INPUT:'+str(path))

exit_code=2
try:
    source=root/'code';source.mkdir()
    stage('git-init',['git','init',str(source)])
    # Shallow source/build fetches do not bring the historical regression pin.
    # Recover it explicitly; keep the original Port C / PLLFSR test unchanged.
    for label,pin in (('harness',SOURCE),('binary-source',BUILD_SOURCE),('historical-regression',HISTORICAL_SOURCE)):
        stage('fetch-'+label,['git','-C',str(source),'fetch','--depth=1','https://github.com/SamDelorean/DANA-emu.git',pin],timeout=400)
    stage('checkout-harness',['git','-C',str(source),'checkout','--detach',SOURCE])
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=SOURCE:raise ValueError('HARNESS_SOURCE_PIN')
    if subprocess.check_output(['git','-C',str(source),'diff','--name-only',BUILD_SOURCE,SOURCE,'--','src','overlays'],text=True).strip():raise ValueError('PRODUCTION_CHANGED_REBUILD_REQUIRES_SEPARATE_AUTHORIZATION')
    # Audit precisely the same live selection used by the original integrity
    # assertion. A pristine archive cannot excuse a changed selected RAM file.
    # Run ALL offline controls even when this audit discovers an input block.
    stage('offline-regression',['python3','tests/dana_012e_offline.py','--evidence',str(PRIOR/'evidence'),
          '--evidence-scope','full','--archive',str(ORIGINAL_ARCHIVE),'--output',str(evidence/'offline')],
          cwd=source,env=dict(os.environ,PYTHONPATH=str(source/'tests')),accepted=(0,1,2))
    offline=json.loads((evidence/'offline/result.json').read_text())
    summary['offline_result']=offline
    if offline['status']!='PASS':raise ValueError('OFFLINE_PREPARATION_'+offline['status'])
    # Audit the original archive without extraction or alteration. No donor,
    # build-cache copy, compiler, dependency install or binary-copy fallback.
    require_hash(ORIGINAL_ARCHIVE,ARCHIVE_SHA)
    with tarfile.open(ORIGINAL_ARCHIVE,'r:gz') as archive:
        members=[m for m in archive.getmembers() if not m.isdir()]
        if len(members)>256 or sum(m.size for m in members)>128*1024*1024:raise ValueError('ARCHIVE_BUDGET')
        if any(not m.isfile() or not m.name.startswith('evidence/') or '..' in Path(m.name).parts for m in members):raise ValueError('ARCHIVE_MEMBER')
        if len({m.name for m in members})!=len(members):raise ValueError('DUPLICATE_ARCHIVE_MEMBER')
        contents={m.name[9:]:archive.extractfile(m).read() for m in members}
    index=json.loads(contents['evidence_sha256.json'])
    if set(index)!=set(contents)-{'evidence_sha256.json'}:raise ValueError('ARCHIVE_INVENTORY')
    if any(hashlib.sha256(contents[n]).hexdigest()!=h for n,h in index.items()):raise ValueError('ARCHIVE_MEMBER_HASH')
    require_hash(QUALIFICATION,QUALIFICATION_SHA);require_hash(MANIFEST,MANIFEST_SHA);require_hash(BINARY,BINARY_SHA)
    if QUALIFICATION.read_bytes()!=contents['binary_qualification.json'] or MANIFEST.read_bytes()!=contents['source-manifest.json']:raise ValueError('ARCHIVE_STAGE_DISAGREEMENT')
    previous=evidence/'prior012c';previous.mkdir()
    for name in ('binary_qualification.json','source-manifest.json','job_result.json','native-pfsel.log'):
        (previous/name).write_bytes(contents[name])  # Exact copies into NEW evidence only.
    summary['prior_archive']=dict(sha256=ARCHIVE_SHA,verified_members=len(index),original_status=json.loads(contents['job_result.json'])['status'])
    sys.path.insert(0,str(source/'tests'));sys.path.insert(0,str(source/'tools'))
    from dana_012e_prepare import preflight
    from dana_012d_verify import probe
    from dana_012e_verify import verify_pair,LIMITS
    from f1_guest import validate_qualified,QUALIFIED_ARTIFACTS
    def guest_facts():
        validate_qualified(GUEST)
        return {n:dict(bytes=(GUEST/n).stat().st_size,sha256=digest(GUEST/n)) for n in (*QUALIFIED_ARTIFACTS,'guest_manifest.json','build_provenance.json')}
    original_guest=guest_facts();summary['guest_inputs']=original_guest
    def provenance_probe(label):
        result=probe(BINARY,QUALIFICATION)
        (evidence/(label+'.json')).write_text(json.dumps(result,indent=2)+'\n')
        if result['status']!='PASS':raise ValueError('FIRST_QUALIFICATION_PREDICATE:'+str(result['first_failing_predicate']))
    provenance_probe('qualification-before')
    summary['historical_pfsel']='PRESERVED_NOT_REPLAYED; new guest C5 read/write independently scored'
    stage('authentic-integrated-guests',['python3','tests/f1_emutos_run.py','--observation-012e','--pfsel-build',str(QUALIFICATION),str(BINARY),str(GUEST),str(evidence/'guest')],
          cwd=source,timeout=LIMITS['host_timeout_seconds']*2+60,accepted=(0,2))
    provenance_probe('qualification-after-guest')
    result=verify_pair(evidence/'guest',GUEST,QUALIFICATION)
    summary['observation_limits']=LIMITS
    (evidence/'independent_result.json').write_text(json.dumps(result,indent=2)+'\n')
    summary.update(status=result['status'],native_status=result['status'],reason=result['reason'],
                   components=result.get('components',{}),
                   next_dependency=result.get('dependency'),first_unsupported_instruction=result.get('first_unsupported_instruction'))
    if guest_facts()!=original_guest:raise ValueError('GUEST_INPUT_CHANGED')
    require_hash(BINARY,BINARY_SHA);require_hash(MANIFEST,MANIFEST_SHA);require_hash(QUALIFICATION,QUALIFICATION_SHA)
    require_hash(ORIGINAL_ARCHIVE,ARCHIVE_SHA)
    after=preflight(source,PRIOR/'evidence',archive=ORIGINAL_ARCHIVE)
    (evidence/'preparation-after-native.json').write_text(json.dumps(after,indent=2)+'\n')
    if after!=json.loads((evidence/'offline/preparation.json').read_text()):raise ValueError('PREPARATION_INPUT_CHANGED_DURING_NATIVE')
    exit_code=0 if result['status'] in ('PASS','PARTIAL') else 2
except (OSError,ValueError,RuntimeError,KeyError,TypeError,subprocess.SubprocessError,tarfile.TarError) as exc:
    summary.update(status='BLOCKED',reason=str(exc));exit_code=2
    if summary['stages'].get('offline-regression',{}).get('exit_code')==1:
        summary.update(status='FAIL');exit_code=1
    if 'authentic-integrated-guests' in summary['stages']:summary['native_status']=summary['status']
finally:
    summary['archive_input_bytes']=sum(p.stat().st_size for p in evidence.rglob('*') if p.is_file())
    if summary['archive_input_bytes']>768*1024*1024:
        summary.update(status='BLOCKED',reason='EVIDENCE_BUNDLE_SIZE_BOUND');exit_code=2
    save()
    inventory={str(p.relative_to(evidence)):digest(p) for p in evidence.rglob('*') if p.is_file()}
    (evidence/'evidence_sha256.json').write_text(json.dumps(inventory,indent=2,sort_keys=True)+'\n')
    archive=root/(root.name+'.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:tar.add(evidence,arcname='evidence')
    checksum=root/'archive.sha256';checksum.write_text(digest(archive)+'  '+archive.name+'\n')
    transport=dict(status='BLOCKED',upload='NOT_COMPLETE',native_status=summary['native_status'],archive_sha256=digest(archive),full_boot=False)
    receipt=root/'transport_result.json'
    try:
        remote='googledrive:AS2K_TEMP/COMMANDER_PIPELINE/outbox/'+root.name
        for item in (archive,checksum):subprocess.run(['rclone','copyto',str(item),remote+'/'+item.name],check=True,timeout=800)
        if subprocess.check_output(['rclone','cat',remote+'/archive.sha256'],text=True,timeout=160)!=checksum.read_text():raise ValueError('TRANSPORT_READBACK_MISMATCH')
        transport.update(status=summary['status'],upload='UPLOADED')
        receipt.write_text(json.dumps(transport,indent=2)+'\n')
        subprocess.run(['rclone','copyto',str(receipt),remote+'/'+receipt.name],check=True,timeout=160)
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        transport.update(status='BLOCKED',upload='BLOCKED',reason=str(exc));exit_code=2
        receipt.write_text(json.dumps(transport,indent=2)+'\n')
    print(json.dumps(dict(transport,exit_code=exit_code),sort_keys=True))
sys.exit(exit_code)
PY_JOB
