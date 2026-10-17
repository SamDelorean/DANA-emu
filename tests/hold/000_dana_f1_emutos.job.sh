#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# HOLD ONLY. Never put this job in inbox or dispatch without fresh authorization.
# Immutable implementation source is checked out below; no AS2K/donor writes.
set -euo pipefail
# Authorization is enforced outside this job: audited Drive HOLD->inbox
# staging and the explicitly approved canonical dcjob launch. Never dispatch
# this source file on its own or assume a background consumer exists.
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

SOURCE='2321e47c3f2d5f19781e286c231119d8a6b2cbc3'
MAME='c4e48388ca620472643110db2941ce70aa5f3c07'
GUEST='9c42ef0f2c2fa9d1e217fced9da68901b2326e8b'
R7='5df95ba18e34580de8f33872c8fb343e67953108cd8c19133c966dbe5c4b5a70'
# Recorded from the preserved 9de5dfe6 production driver, not a guessed path.
R7_DRIVER='e104dc74da73b335c99a25397e9be77d409647e0c3bbb3550f226ce290dade56'
DONOR=Path('/home/spc/Projects/alphasmart/as2k-stable-eeepc900-local/mame-as3k-donor')
BASE=Path('/home/spc/DANA_EMU_ISOLATED')
BASE.mkdir(parents=True,exist_ok=True)
root=Path(tempfile.mkdtemp(prefix='f1_emutos_',dir=BASE))
evidence=root/'evidence';evidence.mkdir()
summary={'status':'BLOCKED','assignment':'F1','source_commit':SOURCE,'mame_commit':MAME,
         'guest_commit':GUEST,'work':str(root),'stages':{},'remote_actions':'authorized job only'}

def save():
    (evidence/'job_result.json').write_text(json.dumps(summary,indent=2)+'\n')

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def stage(name,command,cwd=None,env=None,timeout=300,accepted=(0,)):
    record={'command':command,'cwd':str(cwd) if cwd else None};summary['stages'][name]=record;save()
    try:
        with (evidence/(name+'.log')).open('wb') as log:
            p=subprocess.run(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        record['exit_code']=p.returncode;save()
        if p.returncode not in accepted:raise RuntimeError(name+' failed; see '+name+'.log')
        return p.returncode
    except subprocess.TimeoutExpired:
        record.update(exit_code=None,reason='HOST_TIMEOUT');save();raise

def checkout(url,commit,directory):
    directory.mkdir()
    stage('init-'+directory.name,['git','init',str(directory)])
    stage('fetch-'+directory.name,['git','-C',str(directory),'fetch','--depth=1',url,commit],timeout=300)
    stage('checkout-'+directory.name,['git','-C',str(directory),'checkout','--detach','FETCH_HEAD'])
    actual=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
    if actual!=commit:raise RuntimeError('SOURCE_PIN_MISMATCH: '+str(directory))

exit_code=2
try:
    code=root/'code';checkout('https://github.com/SamDelorean/DANA-emu.git',SOURCE,code)
    stage('unit-input',['python3','tests/f1_test_guest.py','-v'],cwd=code)
    stage('unit-ram',['python3','tests/d1_2_test_verifier.py'],cwd=code)
    stage('unit-mmio',['python3','tests/d1_3_1_mmio01_test_verifier.py'],cwd=code)
    guest=root/'emutos-source';checkout('https://github.com/davidgiven/emutos.git',GUEST,guest)
    requested_prefix=os.environ.get('DANA_F1_GUEST_PREFIX')
    prefix=requested_prefix or 'm68k-atari-mint-'
    tool_env=dict(os.environ)
    # BetaWise installs its cross compiler to $HOME/.local/bin by default.
    # Include that existing user-owned prefix only for this isolated job.
    local_bin=Path.home()/'.local/bin'
    if (local_bin/'m68k-elf-gcc').is_file():
        tool_env['PATH']=str(local_bin)+os.pathsep+tool_env.get('PATH','')
    # BetaWise already uses m68k-elf-gcc. Check it before downloading MiNT:
    # its source recipe disables multilib, so existing installs may not offer
    # a matching -mshort libgcc. Do not infer an ABI PASS from applet builds.
    if not requested_prefix and shutil.which('m68k-elf-gcc',path=tool_env.get('PATH')):
        probe=evidence/'betawise-elf-preflight.json'
        stage('betawise-elf-preflight',['python3','tools/f1_crossmint_preflight.py',
            '--prefix','m68k-elf-','--result',str(probe)],
            cwd=code,env=tool_env,timeout=120,accepted=(0,2))
        betawise_result=json.loads(probe.read_text())
        summary['betawise_elf_probe']=betawise_result;save()
        if betawise_result['status']=='PASS':
            prefix='m68k-elf-'
            summary['guest_toolchain_choice']='REUSE_VERIFIED_BETAWISE_ELF'
    if not shutil.which(prefix+'gcc'):
        if prefix!='m68k-atari-mint-':
            raise RuntimeError('BLOCKED_TOOLCHAIN_PREFIX: unavailable '+prefix+'gcc')
        command=['python3','tools/f1_crossmint_acquire.py',
                 '--out',str(root/'crossmint')]
        # Optional offline archives are permitted, but never assumed to exist.
        for envname,arg in [('DANA_F1_GCC_ARCHIVE','--gcc-archive'),
                            ('DANA_F1_BINUTILS_ARCHIVE','--binutils-archive')]:
            if os.environ.get(envname):command.extend([arg,os.environ[envname]])
        stage('acquire-crossmint',command,cwd=code,timeout=900)
        manifest=json.loads((root/'crossmint/toolchain_manifest.json').read_text())
        if manifest.get('status')!='READY_FOR_ABI_PREFLIGHT':
            raise RuntimeError('BLOCKED_CROSSMINT_ACQUISITION')
        tool_env['PATH']=manifest['bin_dir']+os.pathsep+tool_env.get('PATH','')
        summary['crossmint_archives']=manifest['archives']
    stage('crossmint-abi-preflight', ['python3','tools/f1_crossmint_preflight.py',
        '--prefix',prefix,'--result',str(evidence/'crossmint-preflight.json')],
        cwd=code,env=tool_env,timeout=120)
    guest_output=root/'guest'
    stage('build-guest',['python3','tools/f1_guest.py','build',str(guest),str(guest_output),'--prefix',prefix],
        cwd=code,env=tool_env,timeout=1800)
    stage('validate-guest',['python3','tools/f1_guest.py','validate',str(guest_output)],cwd=code)
    if subprocess.check_output(['git','-C',str(DONOR),'rev-parse','HEAD'],text=True).strip()!=MAME:
        raise RuntimeError('BLOCKED_DONOR_PIN')
    staging=root/'mame-stage'
    stage('prepare-diag',['bash','tests/d1_1_diag_smoke.sh','prepare',str(DONOR),str(staging)],cwd=code,timeout=300)
    target=staging/'diag/bin/dana-diag';target.parent.mkdir()
    driver=digest(code/'src/mame/skeleton/alphasdana.cpp')
    old=os.environ.get('DANA_F1_R7_BINARY')
    if driver==R7_DRIVER and old and Path(old).is_file() and digest(old)==R7:
        shutil.copy2(old,target);summary['binary_action']='REUSED_VERIFIED_R7'
    else:
        summary['binary_action']='REBUILD_PRODUCTION_DRIVER_CHANGED' if driver!=R7_DRIVER else 'REBUILD_NO_COMPATIBLE_LOCAL_R7'
        cc=next((shutil.which(x) for x in ('clang-21','clang') if shutil.which(x)),None)
        cxx=next((shutil.which(x) for x in ('clang++-21','clang++') if shutil.which(x)),None)
        if not cc or not cxx or not re.search(r'version\s+21\b',subprocess.check_output([cc,'--version'],text=True)):
            raise RuntimeError('BLOCKED_MAME_TOOLCHAIN: qualified Clang 21 unavailable')
        environment=dict(os.environ,CC=cc,CXX=cxx,LD=cxx)
        stage('build-diag',['make','-j3','TARGET=mame','SUBTARGET=danadiag',
            'SOURCES=src/mame/skeleton/alphasdana.cpp','BUILDDIR=build/dana-diag',
            'REGENIE=1','TOOLS=0','DEBUG=1','PRECOMPILE=0','USE_QTDEBUG=0',
            'OVERRIDE_CC='+cc,'OVERRIDE_CXX='+cxx,'OVERRIDE_LD='+cxx],
            cwd=staging/'diag/source',env=environment,timeout=7200)
        built=staging/'diag/source/danadiagd'
        if not built.is_file():raise RuntimeError('BLOCKED_OUTPUT_PATH: danadiagd missing after successful build')
        shutil.copy2(built,target)
    summary['binary_sha256']=digest(target);summary['driver_sha256']=driver;save()
    stage('diag-smoke',['bash','tests/d1_1_diag_smoke.sh','verify',str(target),str(evidence/'diag-smoke')],cwd=code)
    stage('ram-regression',['python3','tests/f1_regress.py',str(target),str(evidence/'ram')],cwd=code,timeout=600)
    stage('mmio-regression',['python3','tests/d1_3_1_mmio01_run.py',str(target),str(evidence/'mmio')],cwd=code,timeout=300)
    stage('authentic-guest',['python3','tests/f1_emutos_run.py',str(target),str(guest_output),str(evidence/'guest')],
          cwd=code,timeout=600,accepted=(0,1,2))
    result=json.loads((evidence/'guest/result.json').read_text())
    summary.update(status=result['status'],guest_result=result)
    exit_code=1 if result['status']=='FAIL' else 2 if result['status']=='BLOCKED' else 0
except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error:
    summary.update(status='BLOCKED',reason=str(error))
    # Preserve a failed *executed* regression as FAIL, not an input failure.
    for name in ('diag-smoke','ram-regression','mmio-regression'):
        if summary['stages'].get(name,{}).get('exit_code')==1:
            summary['status']='FAIL';exit_code=1
finally:
    save()
    inventory={}
    for path in evidence.rglob('*'):
        if path.is_file() and path.name!='artifacts.sha256.json':inventory[str(path.relative_to(evidence))]=digest(path)
    (evidence/'artifacts.sha256.json').write_text(json.dumps(inventory,indent=2)+'\n')
    archive=root/(root.name+'.tar.gz')
    with tarfile.open(archive,'w:gz') as bundle:
        bundle.add(evidence,arcname='evidence')
        for name in ('emutos.img','emutos-dana.rom','emutos.map','emutos.dana','guest_manifest.json','build.log','build_provenance.json'):
            path=root/'guest'/name
            if path.is_file():bundle.add(path,arcname='guest/'+name)
    archive_hash=digest(archive)
    (root/'archive.sha256').write_text(archive_hash+'  '+archive.name+'\n')
    # Canonical outbox transport; no inbox/queue changes and no Commander calls.
    upload_status='BLOCKED'
    try:
        if not shutil.which('rclone'):raise RuntimeError('rclone unavailable')
        remote='googledrive:AS2K_TEMP/COMMANDER_PIPELINE/outbox/'+root.name
        upload=subprocess.run(['rclone','copyto',str(archive),remote+'/'+archive.name],timeout=600)
        hash_upload=subprocess.run(['rclone','copyto',str(root/'archive.sha256'),remote+'/archive.sha256'],timeout=120)
        if upload.returncode or hash_upload.returncode:raise RuntimeError('rclone returned nonzero')
        upload_status='UPLOADED'
    except (OSError,RuntimeError,subprocess.SubprocessError) as error:
        print('BLOCKED_EVIDENCE_UPLOAD:',str(error),'preserved local evidence at',root)
        if exit_code==0:exit_code=2
    (root/'upload_receipt.json').write_text(json.dumps({'status':upload_status,'local_archive':str(archive)},indent=2)+'\n')
    print(json.dumps({'status':summary['status'],'evidence':str(root),'archive_sha256':archive_hash,'upload_status':upload_status}))
sys.exit(exit_code)
PY_JOB
