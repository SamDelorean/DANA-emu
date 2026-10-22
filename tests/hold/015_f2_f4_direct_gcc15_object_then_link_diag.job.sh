#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# SINGLE user-authorized F2-F4 recovery: translate generated Clang recipe to direct GCC15 one-object compile, then link only; one attempt, no fallbacks.
# Historic jobs 008/009/010 must not be replayed, and no other workstream touched.
# No emulator/build/transport action before fresh authorization.
set -euo pipefail
if [[ "${DANA_HARDWARE_NATIVE_AUTHORIZED:-}" != YES || "${DANA_HARDWARE_BUILD_AUTHORIZED:-}" != YES ]]; then
    echo 'HOLD: fresh integrated Dana hardware build AND native authorization required; no action.'
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
import struct
import zlib
import tarfile
import tempfile

SOURCE = '87e26793ff4743d5fef5539def994872e2291739'
DRIVER_SHA='c10fa1303eb9f608e219bc9c9afa7ea6f8f4afd37c34526e3a523b5f8b6fe578'
BUILD_SOURCE = '581601b49acb6603af2a100817d0f06fed17ed96'
HISTORICAL_SOURCE='56a0a0040edfc161e45c1131692a64c3649fe3af'
MAME_PIN = 'c4e48388ca620472643110db2941ce70aa5f3c07'
GUEST_PIN = '9c42ef0f2c2fa9d1e217fced9da68901b2326e8b'
BINARY_SHA = 'caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37'
# Immutable verified 012C baseline for incremental object reuse only.
PRIOR_012C_SOURCE = '581601b49acb6603af2a100817d0f06fed17ed96'
PRIOR_012C_DRIVER_SHA = 'e8211be78dfb2bf4cdc0ccabd444c97d715dc37d189d4f113f2f1cbf05b573e2'
PRIOR_012C_DIAG_SHA = 'caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37'
PRIOR_012C_STAGE = Path('/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag')
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
root = Path(tempfile.mkdtemp(prefix='dana_integrated_hardware_', dir=BASE))
evidence = root/'evidence'
evidence.mkdir()
summary = dict(scope='F2_F4_PRODUCT_ONLY_INCREMENTAL_BUILD_GUEST', status='BLOCKED', reason='NOT_RUN',
               native_status='NATIVE_PENDING', full_boot=False, source_commit=SOURCE,
               prior_binary_build_source=BUILD_SOURCE, binary_build_source=SOURCE, mame_pin=MAME_PIN, guest_source=GUEST_PIN,
               E4_archive_sha256=E4_ARCHIVE_SHA, MAME_builds=0, ROM_builds=0, stages={})


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def write_verified_guest_png(frame_bytes,out):
    # Pure-stdlib representation of the actual 560x160x1bpp RAM snapshot.
    # This is not an image of the MAME host window. No synthetic text/pixels.
    if len(frame_bytes)!=11200:raise ValueError('INVALID_LCD_FRAME_SIZE')
    scan=bytearray()
    for row in range(160):
        scan.append(0)  # PNG filter type 0
        for value in frame_bytes[row*70:(row+1)*70]:
            scan.extend(48 if value & (1 << bit) else 240 for bit in range(7,-1,-1))
    def chunk(kind,data):
        return (struct.pack('!I',len(data))+kind+data+
                struct.pack('!I',zlib.crc32(kind+data)&0xffffffff))
    png=(b'\x89PNG\r\n\x1a\n'+
         chunk(b'IHDR',struct.pack('!2I5B',560,160,8,0,0,0,0))+
         chunk(b'IDAT',zlib.compress(scan,9))+chunk(b'IEND',b''))
    out.write_bytes(png)
    if not png.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('INVALID_DERIVED_PNG')
    return digest(out)


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
    for label,pin in (('harness',SOURCE),('qualified-build',BUILD_SOURCE),('historical-regression',HISTORICAL_SOURCE)):
        stage('fetch-'+label,['git','-C',str(source),'fetch','--depth=1',
              'https://github.com/SamDelorean/DANA-emu.git',pin],timeout=400)
    stage('checkout-source',['git','-C',str(source),'checkout','--detach',SOURCE])
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=SOURCE:
        raise RuntimeError('BLOCKED_SOURCE_PIN')
    changed=subprocess.check_output(['git','-C',str(source),'diff','--name-only',BUILD_SOURCE,SOURCE,'--','src'],text=True).splitlines()
    if changed!=['src/mame/skeleton/alphasdana.cpp']:raise RuntimeError('BLOCKED_UNEXPECTED_PRODUCTION_SCOPE')
    if digest(source/'src/mame/skeleton/alphasdana.cpp')!=DRIVER_SHA:raise RuntimeError('BLOCKED_FROZEN_DRIVER_SHA')
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
    # This request concerns ONLY changed driver bytes. Historic 012-C test
    # evidence stays untouched and is not an input to this build or guest.
    # Validate the pinned guest and 012-C immutable cached objects normally.
    summary['historical_forensic_directory']='NOT_USED_FOR_F2_F4_PRODUCT_BUILD'
    donor=Path('/home/spc/Projects/alphasmart/as2k-stable-eeepc900-local/mame-as3k-donor')
    stage('donor-pin',['git','-C',str(donor),'cat-file','-e',MAME_PIN+'^{commit}'])
    # Incremental Dana-only build: reuse the qualified 012C object tree,
    # *without* rewriting the old 012C source/evidence/binary. The old full
    # donor unpack/prepare path is deliberately not a fallback.
    stage_root=root/'mame-stage'
    staged_diag=stage_root/'diag'
    staged_diag.mkdir(parents=True)
    old_source=PRIOR_012C_STAGE/'source'
    old_manifest_file=PRIOR_012C_STAGE/'source-manifest.json'
    old_diag=PRIOR_012C_STAGE/'bin/dana-diag'
    driver='src/mame/skeleton/alphasdana.cpp'
    if not old_source.is_dir() or old_source.is_symlink():
        raise RuntimeError('BLOCKED_PRIOR_012C_BUILD_CACHE_MISSING')
    if not old_manifest_file.is_file() or old_manifest_file.is_symlink() or not old_diag.is_file():
        raise RuntimeError('BLOCKED_PRIOR_012C_BUILD_EVIDENCE_MISSING')
    if digest(old_manifest_file)!='504530b8ba90549fc6cfd5dc7ec7505ff013ee025daceec9c60dc26a4e4988de':
        raise RuntimeError('BLOCKED_PRIOR_MANIFEST_IDENTITY')
    original_qualification=BASE/'dana_timer_uart_irq_hmkem769/evidence/binary_qualification.json'
    if digest(original_qualification)!='6fda7a9474c7594ae1019fea33766ad65c99d9e81a5d323ec1e1f6b5ba914131':
        raise RuntimeError('BLOCKED_PRIOR_QUALIFICATION_IDENTITY')
    old_manifest=json.loads(old_manifest_file.read_text())
    for key,value in (('mame_commit',MAME_PIN),('variant','diag'),('status','BUILT_DIAG'),
                      ('source_commit',PRIOR_012C_SOURCE),
                      ('binary_sha256',PRIOR_012C_DIAG_SHA),
                      ('driver_sha256',PRIOR_012C_DRIVER_SHA)):
        if old_manifest.get(key)!=value:
            raise RuntimeError('BLOCKED_PRIOR_012C_PROVENANCE_MISMATCH:'+key)
    if digest(old_source/driver)!=PRIOR_012C_DRIVER_SHA or digest(old_diag)!=PRIOR_012C_DIAG_SHA:
        raise RuntimeError('BLOCKED_PRIOR_012C_SOURCE_OR_BINARY_CHANGED')
    # The published 012-C DIAG under bin/ is the SHA-qualified artifact.
    # The original source-tree linker output may differ and is NOT a second
    # qualified executable. Preserve its actual identity without rejecting
    # a valid, read-only incremental object cache.
    prior_internal_output=old_source/'danadiagd'
    if not prior_internal_output.is_file() or prior_internal_output.is_symlink():
        raise RuntimeError('BLOCKED_PRIOR_012C_INTERNAL_OUTPUT_MISSING')
    prior_internal_output_sha=digest(prior_internal_output)
    old_list=old_source/'src/mame/mame.lst'
    if digest(old_list)!=old_manifest.get('list_sha256'):
        raise RuntimeError('BLOCKED_PRIOR_012C_DRIVER_LIST_CHANGED')
    if any(p.is_symlink() and (p.readlink().is_absolute() or not p.resolve().is_relative_to(old_source.resolve()))
           for p in old_source.rglob('*')):
        raise RuntimeError('BLOCKED_SYMLINKED_CACHE_NO_WRITES_ALLOWED')
    objects=old_source/'build/dana-diag'
    if not objects.is_dir() or objects.is_symlink():
        raise RuntimeError('BLOCKED_PRIOR_012C_OBJECT_CACHE_MISSING')
    old_object_count=sum(1 for p in objects.rglob('*.o') if p.is_file() and not p.is_symlink())
    if old_object_count<100:
        raise RuntimeError('BLOCKED_PRIOR_012C_OBJECT_CACHE_INCOMPLETE')
    summary['incremental_build']=dict(
        mode='COPY_ON_WRITE_REUSE_012C_THEN_DRIVER_ONLY_INCREMENTAL_MAKE',
        prior_source_commit=PRIOR_012C_SOURCE,prior_binary_sha256=PRIOR_012C_DIAG_SHA,
        prior_internal_unqualified_output_sha256=prior_internal_output_sha,
        donor_commit=MAME_PIN,cached_object_count=old_object_count,
        prior_stage=str(PRIOR_012C_STAGE),full_donor_reextraction=False,
        full_mame_rebuild_fallback=False,only_modified_production_file=driver)
    save()
    # cp -a retains every 012C object/dependency timestamp; reflinks when
    # available. Unlike hardlinks, it cannot mutate the qualified old stage.
    stage('copy-012C-compiled-cache',
          ['cp','-a','--reflink=auto',str(old_source),str(staged_diag/'source')],
          timeout=1200)
    mame=staged_diag/'source'
    # Verify the cache copy against BOTH original byte identities before
    # aligning only the NEW staged output with the published qualified DIAG.
    if digest(mame/driver)!=PRIOR_012C_DRIVER_SHA or digest(mame/'danadiagd')!=prior_internal_output_sha:
        raise RuntimeError('BLOCKED_INCREMENTAL_CACHE_COPY_CHANGED')
    shutil.copy2(old_diag,mame/'danadiagd')
    if digest(mame/'danadiagd')!=PRIOR_012C_DIAG_SHA:
        raise RuntimeError('BLOCKED_INCREMENTAL_QUALIFIED_OUTPUT_COPY')
    if digest(mame/'src/mame/mame.lst')!=old_manifest['list_sha256']:
        raise RuntimeError('BLOCKED_INCREMENTAL_DRIVER_LIST_CHANGED')
    shutil.copy2(old_manifest_file,staged_diag/'source-manifest.json')
    # Only the Dana driver was modified between pinned builds. Preserve all
    # other MAME source/objects; writing bytes here updates its mtime so make
    # detects the changed skeleton driver and relinks danadiagd.
    # Generated dependency/project files can refer to the *absolute* 012C
    # staging directory. Rebase only those paths in the COPIED cache, not
    # original MAME source/object files or the immutable 012C directory.
    previous_root=os.fsencode(str(old_source))
    copied_root=os.fsencode(str(mame))
    rewritten=[]
    for p in (mame/'build/dana-diag').rglob('*'):
        if not p.is_file() or p.is_symlink() or not (
                p.name=='Makefile' or p.suffix in ('.d','.make','.mk','.mak')):
            continue
        blob=p.read_bytes()
        if previous_root in blob:
            p.write_bytes(blob.replace(previous_root,copied_root))
            rewritten.append(str(p.relative_to(mame)))
    summary['incremental_build']['rebased_cache_metadata_files']=rewritten[:128]
    summary['incremental_build']['rebased_metadata_count']=len(rewritten)
    if len(rewritten)>128:summary['incremental_build']['rebased_metadata_truncated']=True
    # Preserve object metadata before running the incremental make. The
    # resulting evidence reports EXACTLY which object files were replaced.
    cache_objects={str(p.relative_to(mame)):(p.stat().st_size,p.stat().st_mtime_ns)
                   for p in (mame/'build/dana-diag').rglob('*.o')
                   if p.is_file() and not p.is_symlink()}
    if len(cache_objects)!=old_object_count:
        raise RuntimeError('BLOCKED_INCREMENTAL_OBJECT_CACHE_CHANGED')
    (mame/driver).write_bytes((source/driver).read_bytes())
    if digest(mame/driver)!=digest(source/driver):
        raise RuntimeError('BLOCKED_STAGED_DRIVER_MISMATCH')
    # Verified single GCC15 alternative: preflight confirmed installed and
    # sharing x86_64 libstdc++ with the pinned cached-Clang21 MAME objects.
    import re
    import shlex
    cc=shutil.which('clang-21') or shutil.which('clang')
    link_cxx=shutil.which('clang++-21') or shutil.which('clang++')
    gcc_cxx=shutil.which('g++-15')
    if not cc or not link_cxx or not gcc_cxx:
        raise RuntimeError('BLOCKED_SINGLE_ALTERNATIVE_TOOLCHAIN_MISSING_NO_INSTALL')
    gcc_ver=subprocess.check_output([gcc_cxx,'--version'],text=True,timeout=15).splitlines()[0]
    link_ver=subprocess.check_output([link_cxx,'--version'],text=True,timeout=15).splitlines()[0]
    if not gcc_ver.startswith('g++-15 (Ubuntu 15.2.0') or 'clang version 21.' not in link_ver:
        raise RuntimeError('BLOCKED_COMPILER_VERSION_CHANGED')
    gcc_arch=subprocess.check_output([gcc_cxx,'-dumpmachine'],text=True,timeout=15).strip()
    link_arch=subprocess.check_output([link_cxx,'-dumpmachine'],text=True,timeout=15).strip()
    if not gcc_arch.startswith('x86_64-') or not link_arch.startswith('x86_64-'):
        raise RuntimeError('BLOCKED_ALTERNATE_OBJECT_ARCH_MISMATCH')
    gcc_cpp=subprocess.check_output([gcc_cxx,'-print-file-name=libstdc++.so'],text=True,timeout=15).strip()
    link_cpp=subprocess.check_output([link_cxx,'-print-file-name=libstdc++.so'],text=True,timeout=15).strip()
    if not Path(gcc_cpp).is_file() or Path(gcc_cpp).resolve()!=Path(link_cpp).resolve():
        raise RuntimeError('BLOCKED_ALTERNATE_CXX_STDLIB_MISMATCH')
    summary['toolchain']=dict(object_cxx=gcc_cxx,object_cxx_version=gcc_ver,
        link_cxx=link_cxx,link_cxx_version=link_ver,
        object_arch=gcc_arch,link_arch=link_arch,shared_libstdcxx=str(Path(gcc_cpp).resolve()))

    # Use make -n ONLY to obtain the generated driver compile recipe.
    # Do not execute it: the old MAME project has Clang-specific flags.
    command=['make','-j3','TARGET=mame','SUBTARGET=danadiag','SOURCES='+driver,
             'BUILDDIR=build/dana-diag','TOOLS=0','DEBUG=1','PRECOMPILE=0','USE_QTDEBUG=0',
             'OVERRIDE_CC='+cc,'OVERRIDE_CXX='+link_cxx,'OVERRIDE_LD='+link_cxx,
             'CXX='+link_cxx]
    summary['incremental_build']['regenie_forced']=False
    build_env=dict(os.environ,CC=cc,CXX=link_cxx,LD=link_cxx)
    build_env.pop('REGENIE',None)
    stage('plan-driver-only',['make','-n']+command[1:],cwd=mame,timeout=300,env=build_env)
    plan=evidence/'plan-driver-only.log'
    if plan.stat().st_size>33554432:raise RuntimeError('BLOCKED_BUILD_PLAN_BOUND')
    planned=[line for line in plan.read_text(errors='replace').splitlines()
             if re.search(r'(?:^|\\s)-c(?:\\s|$)',line)]
    if len(planned)!=1 or 'alphasdana.cpp' not in planned[0]:
        raise RuntimeError('BLOCKED_PLAN_IS_NOT_EXACTLY_ONE_DANA_DRIVER')
    summary['incremental_build']['planned_compilation_units']=len(planned)

    # The printed command runs in the generated make project's own cwd.
    # Validate exact source and destination: do not compile other units.
    project_files=list((mame/'build/dana-diag').rglob('mame_danadiag.make'))
    if len(project_files)!=1:raise RuntimeError('BLOCKED_GENERATED_PROJECT_MISSING_OR_DUPLICATE')
    project_dir=project_files[0].parent
    original=shlex.split(planned[0])
    if Path(original[0]).resolve()!=Path(link_cxx).resolve():
        raise RuntimeError('BLOCKED_UNEXPECTED_DRIVER_COMPILER')
    if original.count('-c')!=1 or original.count('-o')!=1:
        raise RuntimeError('BLOCKED_DRIVER_COMMAND_SHAPE')
    old_source_arg=original[original.index('-c')+1]
    old_object_arg=original[original.index('-o')+1]
    if (project_dir/old_source_arg).resolve()!=(mame/driver).resolve():
        raise RuntimeError('BLOCKED_DRIVER_SOURCE_RESOLUTION')
    output_obj=(project_dir/old_object_arg).resolve()
    old_objects=list((mame/'build/dana-diag').rglob('alphasdana.o'))
    if len(old_objects)!=1 or output_obj!=old_objects[0].resolve():
        raise RuntimeError('BLOCKED_DRIVER_OBJECT_RESOLUTION')
    old_obj_sha=digest(output_obj)

    # Translate an already-observed Clang recipe to GCC15 without fabricating
    # include paths or silently allowing unreviewed ABI-affecting flags.
    # Existing -D and -I are retained verbatim. Clang diagnostics, original
    # optimization and warning-as-error are removed; actual C++ errors remain.
    translated=[gcc_cxx]
    omitted=[]
    def passthrough(arg):
        return (arg.startswith('-D') or arg.startswith('-I') or
                arg in ('-MMD','-MP','-m64','-pipe','-fno-strict-aliasing',
                        '-std=c++20','-pthread'))
    index=1
    while index<len(original):
        arg=original[index]
        if arg in ('-c','-o'):
            if index+1>=len(original):raise RuntimeError('BLOCKED_MISSING_COMPILE_PATH')
            translated.extend((arg,original[index+1]))
            index+=2
            continue
        if passthrough(arg):
            translated.append(arg)
        elif arg.startswith('-W') or re.fullmatch(r'-O[0-9sz]',arg):
            omitted.append(arg)
        else:
            raise RuntimeError('BLOCKED_UNKNOWN_DRIVER_FLAG:'+arg)
        index+=1
    if not any(x.startswith('-I') for x in translated) or not any(x.startswith('-D') for x in translated):
        raise RuntimeError('BLOCKED_TRANSLATION_DROPPED_INCLUDES_OR_DEFINES')
    if '-std=c++20' not in translated:raise RuntimeError('BLOCKED_CXX20_FLAG_MISSING')
    translated.extend(('-O1','-Wall','-Wno-error'))
    summary['incremental_build']['compiler_translation']=dict(
        origin='PINNED_GENERATED_MAME_CLANG_DRIVER_RECIPE',
        compiler_gcc15=gcc_cxx,linker_clang21=link_cxx,driver_object=str(output_obj),
        source=str((mame/driver).resolve()),original_command=original,
        gcc_command=translated,filtered_warning_and_opt_flags=omitted)
    save()
    summary['MAME_builds']=1
    # EXACTLY ONE actual source compile in this intervention.
    stage('compile-dana-object-gcc15',translated,cwd=project_dir,timeout=1200,env=build_env)
    if not output_obj.is_file() or digest(output_obj)==old_obj_sha:
        raise RuntimeError('BLOCKED_NO_NEW_DANA_OBJECT')
    if output_obj.read_bytes()[:4]!=b'\\x7fELF':
        raise RuntimeError('BLOCKED_NOT_ELF_DANA_OBJECT')
    summary['incremental_build']['direct_object_sha256']=digest(output_obj)
    save()

    # Dry-run the unchanged generated MAME link AFTER the new object exists.
    # Zero further C/C++ compilations allowed; never auto-regenerate MAME.
    stage('plan-link-only',['make','-n']+command[1:],cwd=mame,timeout=300,env=build_env)
    post=(evidence/'plan-link-only.log').read_text(errors='replace').splitlines()
    if any(re.search(r'(?:^|\\s)-c(?:\\s|$)',line) for line in post):
        raise RuntimeError('BLOCKED_LINK_WOULD_RECOMPILE_OTHER_OBJECTS')
    if not any('danadiagd' in line for line in post):
        raise RuntimeError('BLOCKED_NO_DANA_DIAG_LINK_PLANNED')
    # Only the existing MAME linker invocation; objects are already compiled.
    stage('link-only-diag',command,cwd=mame,timeout=1200,env=build_env)
    # Record objective reused-versus-touched object metadata, not an
    # unsupported assertion that a full MAME rebuild did not happen.
    updated_objects={str(p.relative_to(mame)):(p.stat().st_size,p.stat().st_mtime_ns)
                     for p in (mame/'build/dana-diag').rglob('*.o')
                     if p.is_file() and not p.is_symlink()}
    touched=sorted(k for k,v in updated_objects.items() if cache_objects.get(k)!=v)
    summary['incremental_build'].update(
        cached_objects_reused=len(set(cache_objects)&set(updated_objects))-len(
            set(touched)&set(cache_objects)),
        object_files_updated=len(touched),object_files_added=len(set(updated_objects)-set(cache_objects)),
        updated_object_files=touched[:128],updated_object_list_truncated=len(touched)>128,
        resulting_binary_sha256=None)
    save()
    # Hard acceptance bound: 012C built 1,130 source units from scratch; a
    # Dana driver-only incremental build must touch a tiny subset. Keep the
    # precise list above and reject a broad rebuild, never claim cache reuse
    # merely because make returned exit zero.
    if len(touched)>16:
        raise RuntimeError('BLOCKED_EXCESSIVE_OBJECT_REBUILD_NOT_INCREMENTAL:'+str(len(touched)))
    # Require exactly one modified object: the actual Dana driver. Other
    # source units are not authorized for this single-attempt incremental build.
    if len(touched)!=1 or not touched[0].endswith('/alphasdana.o'):
        raise RuntimeError('BLOCKED_OBJECT_SCOPE_NOT_SINGLE_DANA_DRIVER:'+repr(touched[:16]))
    if len(updated_objects)<old_object_count:
        raise RuntimeError('BLOCKED_INCREMENTAL_OBJECT_CACHE_SHRANK')
    # Original qualified 012C stage, binary and manifest are immutable. This
    # catches accidental writes through a symlink or an unsafe clone.
    if (digest(old_source/driver)!=PRIOR_012C_DRIVER_SHA
            or digest(old_diag)!=PRIOR_012C_DIAG_SHA
            or digest(old_source/'danadiagd')!=prior_internal_output_sha
            or json.loads(old_manifest_file.read_text())!=old_manifest):
        raise RuntimeError('BLOCKED_PRIOR_012C_BUILD_EVIDENCE_MUTATED')
    built=mame/'danadiagd'
    if not built.is_file() or not os.access(built,os.X_OK):raise RuntimeError('BLOCKED_DIAG_OUTPUT_MISSING')
    binary=stage_root/'diag/bin/dana-diag';binary.parent.mkdir();shutil.copy2(built,binary)
    new_sha=digest(binary)
    summary['incremental_build']['resulting_binary_sha256']=new_sha
    save()
    if new_sha in (BINARY_SHA,PRIOR_012C_DIAG_SHA):
        raise RuntimeError('BLOCKED_INCREMENTAL_BUILD_REUSED_OBSOLETE_BINARY')
    if not touched:
        raise RuntimeError('BLOCKED_INCREMENTAL_BUILD_NO_OBJECTS_RECOMPILED')
    source_manifest=stage_root/'diag/source-manifest.json'
    staged=json.loads(source_manifest.read_text())
    staged.update(status='BUILT_DIAG',source_commit=SOURCE,binary_sha256=new_sha,
                  driver_sha256=digest(source/driver))
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
    # Run actual extracted production-method regressions on exactly this
    # source. A FAIL stops before the expensive native guest; no retries.
    stage('targeted-source-tests',['python3','-m','unittest','-q','dana_hardware_test.Hardware'],
          cwd=source,timeout=500,env=dict(os.environ,PYTHONPATH=str(source/'tests')+':'+str(source/'tools')))
    stage('authentic-guest-two-processes',['python3','tests/f1_emutos_run.py','--pfsel-build',str(qualification),
          '--observation-012e','--integrated-hardware',str(binary),str(guest),str(evidence/'guest')],
          cwd=source,timeout=520,accepted=(0,2))
    from dana_012e_verify import verify_pair
    native=verify_pair(evidence/'guest',guest,qualification,expected_source=SOURCE)
    (evidence/'independent_result.json').write_text(json.dumps(native,indent=2)+'\n')
    summary['native']=native
    summary['native_status']=native['status']
    if facts(PRESERVED)!=summary['original_inputs'] or facts(guest)!=summary['staged_inputs']:
        raise RuntimeError('BLOCKED_GUEST_MUTATED')
    summary.update(status='PARTIAL' if native['status'] in ('PASS','PARTIAL') else 'BLOCKED',
        reason='BOUNDED_GENUINE_GUEST_RESULTS_NOT_FULL_BOOT',Commander_calls_in_job=0)
    exit_code=0 if summary['status']=='PARTIAL' else 2
except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as exc:
    summary.update(status='BLOCKED',reason=str(exc))
    exit_code=2
    if summary['stages'].get('targeted-source-tests',{}).get('exit_code')==1:
        summary['status']='FAIL';exit_code=1
finally:
    save()
    inventory={str(p.relative_to(evidence)):digest(p) for p in evidence.rglob('*') if p.is_file()}
    (evidence/'evidence_sha256.json').write_text(json.dumps(inventory,indent=2,sort_keys=True)+'\n')
    archive=root/(root.name+'.tar.gz')
    with tarfile.open(archive,'w:gz') as f:f.add(evidence,arcname='evidence')
    # Read back every archived member and exact inventory. No index regeneration
    # after discrepancies, no evidence substitution, no automatic upload/dispatch.
    with tarfile.open(archive,'r:gz') as f:
        names={m.name for m in f.getmembers() if m.isfile()}
        expected={'evidence/'+n for n in inventory}|{'evidence/evidence_sha256.json'}
        if names!=expected:raise RuntimeError('ARCHIVE_INVENTORY_MISMATCH')
        for name,wanted in inventory.items():
            if hashlib.sha256(f.extractfile('evidence/'+name).read()).hexdigest()!=wanted:
                raise RuntimeError('ARCHIVE_CONTENT_MISMATCH:'+name)
    (root/'archive.sha256').write_text(digest(archive)+'  '+archive.name+'\n')
    print(json.dumps(dict(status=summary['status'],source_commit=SOURCE,archive=str(archive),
        archive_sha256=digest(archive),exit_code=exit_code),sort_keys=True))
sys.exit(exit_code)
PY_JOB
