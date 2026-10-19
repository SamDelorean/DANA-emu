#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Git HOLD only. No emulator/build/transport action before fresh authorization.
set -euo pipefail
if [[ "${DANA_D2_3_AUTHORIZED:-}" != YES || "${DANA_D2_3_BUILD_AUTHORIZED:-}" != YES ]]; then
    echo 'HOLD: fresh D2.3 native AND build authorization required; nothing launched or uploaded.'
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

SOURCE = '11cb0d3f46c787f0a5061118b324f2bcedc4a712'
BUILD_SOURCE = '749517b2f48c9788e5555071561e738017ac5f7c'
MAME_PIN = 'c4e48388ca620472643110db2941ce70aa5f3c07'
GUEST_PIN = '9c42ef0f2c2fa9d1e217fced9da68901b2326e8b'
BINARY_SHA = 'd7bcdf513289a73b8a5c7ab1d258eeac45dc8dd6d89dd7d568cf7784900e6fe5'
E4_ARCHIVE_SHA = '55b60457439105b7fd01a7c927222a1654eccc36523be0dbda12ddb59775f5e0'
PRESERVED = Path('/home/spc/DANA_EMU_ISOLATED/f1_e1e2_baldoi9k/emutos-built')
EXPECTED = {
    'emutos.img': (223748, 'ba590da2661bc582c19bb24d65db04667daf37a17d7aa51fb462b945933ba0a3'),
    'emutos-dana.rom': (223792, 'efb055e5ac02526db069aec23c4b71b092fc48317aa4305e93a4a2f4e369243c'),
    'emutos.map': (124540, '17cc980e675e2e1b50e713b9029f6fc3e51d3e55392deb99d53552d4b3af3e68'),
    'emutos.dana': (223812, 'c201c8527df87fa6a8788d8ac59f43298666196fefeee12dcac68295cb281b9d'),
}
BASE = Path('/home/spc/DANA_EMU_ISOLATED')
BASE.mkdir(exist_ok=True)
root = Path(tempfile.mkdtemp(prefix='d23_pfsel_', dir=BASE))
evidence = root/'evidence'
evidence.mkdir()
summary = dict(scope='D2_3_PFSEL_DIAG_BUILD_AND_F1_E5', status='BLOCKED', reason='NOT_RUN',
               native_status='NATIVE_PENDING', full_boot=False, source_commit=SOURCE,
               prior_binary_build_source=BUILD_SOURCE, binary_build_source=SOURCE, mame_pin=MAME_PIN, guest_source=GUEST_PIN,
               E4_archive_sha256=E4_ARCHIVE_SHA, MAME_builds=0, ROM_builds=0, stages={})


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def facts(directory):
    result={}
    for name in (*EXPECTED,'guest_manifest.json','build_provenance.json'):
        p=directory/name
        if not p.is_file() or p.is_symlink():raise RuntimeError('MISSING_IMMUTABLE_INPUT:'+name)
        entry=(p.stat().st_size,digest(p))
        if name in EXPECTED and entry!=EXPECTED[name]:raise RuntimeError('GUEST_SIZE_OR_SHA_MISMATCH:'+name)
        result[name]=dict(bytes=entry[0],sha256=entry[1])
    return result


def save():
    (evidence/'job_result.json').write_text(json.dumps(summary,indent=2)+'\n')


def stage(name,command,cwd=None,timeout=180,env=None,accepted=(0,)):
    rec=dict(command=command,cwd=str(cwd) if cwd else None,timeout_seconds=timeout)
    summary['stages'][name]=rec;save()
    try:
        with (evidence/(name+'.log')).open('wb') as log:
            p=subprocess.run(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        rec['exit_code']=p.returncode
    except subprocess.TimeoutExpired:
        rec.update(exit_code=None,reason='HOST_TIMEOUT')
    save()
    if rec['exit_code'] not in accepted:raise RuntimeError('BLOCKED_STAGE:'+name+':'+str(rec['exit_code']))


exit_code=2
try:
    # Immutable guest reuse. Exactly one fresh DIAG build, no fallback.
    summary['original_inputs']=facts(PRESERVED)
    source=root/'code';source.mkdir()
    stage('git-init',['git','init',str(source)])
    for label,pin in (('harness',SOURCE),('qualified-build',BUILD_SOURCE)):
        stage('fetch-'+label,['git','-C',str(source),'fetch','--depth=1',
              'https://github.com/SamDelorean/DANA-emu.git',pin],timeout=400)
    stage('checkout-source',['git','-C',str(source),'checkout','--detach',SOURCE])
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=SOURCE:
        raise RuntimeError('BLOCKED_SOURCE_PIN')
    changed=subprocess.check_output(['git','-C',str(source),'diff','--name-only',BUILD_SOURCE,SOURCE,'--','src'],text=True).splitlines()
    if changed!=['src/mame/skeleton/alphasdana.cpp']:raise RuntimeError('BLOCKED_UNEXPECTED_PRODUCTION_SCOPE')
    for path in ('overlays','tests/d1_1_diag_smoke.sh'):
        pair=[subprocess.check_output(['git','-C',str(source),'rev-parse',pin+':'+path],text=True).strip() for pin in (BUILD_SOURCE,SOURCE)]
        if pair[0]!=pair[1]:raise RuntimeError('BLOCKED_UNEXPECTED_BUILD_INPUT_CHANGE:'+path)
    sys.path.insert(0,str(source/'tests'));sys.path.insert(0,str(source/'tools'))
    from f1_guest import validate_qualified
    validate_qualified(PRESERVED)  # Read-only map/envelope/manifest/build provenance.
    guest=root/'guest';guest.mkdir()
    for name in summary['original_inputs']:
        shutil.copyfile(PRESERVED/name,guest/name);(guest/name).chmod(0o444)
    if facts(guest)!=summary['original_inputs']:raise RuntimeError('BLOCKED_GUEST_COPY_CHANGED')
    manifest=validate_qualified(guest)
    summary['map_verified_symbols']=manifest['symbols']
    summary['staged_inputs']=facts(guest)
    # Python evidence/input checks only. No compiler or Lua-library fallback on T.
    stage('offline-evidence',['python3','-m','unittest','f1_test_guest','d2_3_test.NativeEvidence','d2_3_test.E5','-v'],
          cwd=source,env=dict(os.environ,PYTHONPATH=str(source/'tests')))
    donor=Path('/home/spc/Projects/alphasmart/as2k-stable-eeepc900-local/mame-as3k-donor')
    stage('donor-pin',['git','-C',str(donor),'cat-file','-e',MAME_PIN+'^{commit}'])
    stage_root=root/'mame-stage'
    stage('prepare-diag',['bash','tests/d1_1_diag_smoke.sh','prepare',str(donor),str(stage_root)],cwd=source,timeout=900)
    mame=stage_root/'diag/source'
    driver='src/mame/skeleton/alphasdana.cpp'
    if digest(mame/driver)!=digest(source/driver):raise RuntimeError('BLOCKED_STAGED_DRIVER_MISMATCH')
    cc=shutil.which('clang-21') or shutil.which('clang')
    cxx=shutil.which('clang++-21') or shutil.which('clang++')
    if not cc or not cxx:raise RuntimeError('BLOCKED_CLANG21_MISSING_NO_INSTALL')
    import re
    summary['toolchain']={}
    for compiler in (cc,cxx):
        version=subprocess.check_output([compiler,'--version'],text=True,timeout=15)
        if len(version)>32768 or not re.search(r'\bversion 21\.',version):raise RuntimeError('BLOCKED_CLANG21_VERSION')
        summary['toolchain'][compiler]=version.splitlines()[:8]
    command=['make','-j3','TARGET=mame','SUBTARGET=danadiag','SOURCES='+driver,'BUILDDIR=build/dana-diag',
             'REGENIE=1','TOOLS=0','DEBUG=1','PRECOMPILE=0','USE_QTDEBUG=0',
             'OVERRIDE_CC='+cc,'OVERRIDE_CXX='+cxx,'OVERRIDE_LD='+cxx]
    summary['MAME_builds']=1;save()
    stage('build-diag',command,cwd=mame,timeout=7200,env=dict(os.environ,CC=cc,CXX=cxx,LD=cxx))
    built=mame/'danadiagd'
    if not built.is_file() or not os.access(built,os.X_OK):raise RuntimeError('BLOCKED_DIAG_OUTPUT_MISSING')
    binary=stage_root/'diag/bin/dana-diag';binary.parent.mkdir();shutil.copy2(built,binary)
    new_sha=digest(binary)
    if new_sha==BINARY_SHA:raise RuntimeError('BLOCKED_OLD_E4_BINARY_CANNOT_QUALIFY_PFSEL')
    source_manifest=stage_root/'diag/source-manifest.json'
    staged=json.loads(source_manifest.read_text())
    staged.update(status='BUILT_DIAG',source_commit=SOURCE,binary_sha256=new_sha)
    source_manifest.write_text(json.dumps(staged,indent=2)+'\n')
    qualification=evidence/'binary_qualification.json'
    build=dict(schema='dana-d23-build-v1',source_commit=SOURCE,driver_sha256=digest(source/driver),
               mame_commit=MAME_PIN,subtarget='danadiag',variant='diag',build_exit_code=0,build_command=command,
               binary=str(binary),binary_sha256=new_sha,source_manifest_sha256=digest(stage_root/'diag/source-manifest.json'))
    qualification.write_text(json.dumps(build,indent=2)+'\n')
    shutil.copyfile(stage_root/'diag/source-manifest.json',evidence/'source-manifest.json')
    summary['binary']=build
    for name in ('guest_manifest.json','build_provenance.json','emutos.map'):
        shutil.copyfile(guest/name,evidence/name)
    summary['harness_sha256']={name:digest(source/name) for name in
        ('tests/f1_emutos_run.py','tests/f1_emutos_boot.lua','tests/d2_3_pfsel_run.py','tests/d2_3_pfsel_boot.lua','tests/d2_3_test.py')}
    save()
    stage('native-pfsel',['python3','tests/d2_3_pfsel_run.py',str(binary),str(qualification),str(evidence/'pfsel')],cwd=source,timeout=220,accepted=(0,1,2))
    from d2_3_pfsel_run import verify as verify_pfsel
    pf_results=[verify_pfsel(evidence/'pfsel'/mode,binary,qualification,mode) for mode in ('save_restore','reset')]
    summary['pfsel_results']=pf_results
    if any(r['status']!='PASS' for r in pf_results):raise RuntimeError('BLOCKED_NATIVE_PFSEL_QUALIFICATION')
    if pf_results[0]['pid']==pf_results[1]['pid'] or pf_results[0]['execution_id']==pf_results[1]['execution_id']:
        raise RuntimeError('BLOCKED_NATIVE_PFSEL_PROCESS_IDENTITIES')
    stage('authentic-guest-two-processes',['python3','tests/f1_emutos_run.py','--pfsel-build',str(qualification),
          str(binary),str(guest),str(evidence/'guest')],cwd=source,timeout=400,accepted=(0,2))
    # Do not trust runner summaries or exit zero: recompute from original evidence.
    from f1_emutos_run import verify_e4_pair
    native=verify_e4_pair(evidence/'guest',guest,expected_source=SOURCE,qualification=qualification)
    (evidence/'independent_result.json').write_text(json.dumps(native,indent=2)+'\n')
    summary.update(native_result=native,native_status=native['status'],reason=native['reason'])
    summary['status']='BLOCKED_TRANSPORT_PENDING' if native['status']=='REAL_PROGRESS_PASS_SCOPED' else native['status']
    exit_code=0 if native['status']=='REAL_PROGRESS_PASS_SCOPED' else 2
    if (facts(PRESERVED)!=summary['original_inputs'] or facts(guest)!=summary['staged_inputs']
            or digest(binary)!=new_sha or digest(mame/driver)!=build['driver_sha256']):
        summary.update(status='BLOCKED_INPUT',reason='INPUT_IMMUTABILITY_VIOLATION');exit_code=2
except (OSError,ValueError,RuntimeError,KeyError,TypeError,subprocess.SubprocessError) as exc:
    summary.update(status='BLOCKED',reason=str(exc))
    exit_code=2
    if summary['stages'].get('offline-evidence',{}).get('exit_code')==1 or any(r.get('status')=='FAIL' for r in summary.get('pfsel_results',[])):
        summary['status']='FAIL';exit_code=1
finally:
    save()
    inventory={str(p.relative_to(evidence)):digest(p) for p in evidence.rglob('*') if p.is_file()}
    (evidence/'evidence_sha256.json').write_text(json.dumps(inventory,indent=2,sort_keys=True)+'\n')
    archive=root/(root.name+'.tar.gz')
    with tarfile.open(archive,'w:gz') as f:f.add(evidence,arcname='evidence')
    checksum=root/'archive.sha256';checksum.write_text(digest(archive)+'  '+archive.name+'\n')
    transport=dict(status='BLOCKED',upload='NOT_COMPLETE',native_status=summary['native_status'],
                   archive_sha256=digest(archive),evidence=str(root),full_boot=False)
    receipt=root/'transport_result.json'
    try:
        if not shutil.which('rclone'):raise RuntimeError('RCLONE_MISSING')
        remote='googledrive:AS2K_TEMP/COMMANDER_PIPELINE/outbox/'+root.name
        for local in (archive,checksum):
            subprocess.run(['rclone','copyto',str(local),remote+'/'+local.name],check=True,timeout=800)
        readback=subprocess.check_output(['rclone','cat',remote+'/archive.sha256'],text=True,timeout=160)
        if readback!=checksum.read_text():raise RuntimeError('OUTBOX_CHECKSUM_READBACK_MISMATCH')
        transport.update(upload='UPLOADED',status=summary['native_status'] if exit_code==0 else summary['status'])
        receipt.write_text(json.dumps(transport,indent=2)+'\n')
        subprocess.run(['rclone','copyto',str(receipt),remote+'/'+receipt.name],check=True,timeout=160)
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
        transport.update(status='BLOCKED',upload='BLOCKED',reason=str(exc));exit_code=2
        receipt.write_text(json.dumps(transport,indent=2)+'\n')
    print(json.dumps(dict(transport,exit_code=exit_code),sort_keys=True))
sys.exit(exit_code)
PY_JOB
