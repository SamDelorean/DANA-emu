#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Git HOLD only: ONE DIAG build for Timer1+UART1+IRQ6/4 and existing GPIO/LCD/SPI2/ST, two authentic EmuTOS processes.
# Historic jobs 008/009/010 must not be replayed, and no other workstream touched.
# No emulator/build/transport action before fresh authorization.
set -euo pipefail
if [[ "${DANA_TIMER_UART_AUTHORIZED:-}" != YES || "${DANA_TIMER_UART_BUILD_AUTHORIZED:-}" != YES ]]; then
    echo 'HOLD: fresh Dana Timer1 UART1 IRQ native and build authorization required; no action.'
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

SOURCE = 'e726cc6c0858b6122513060e22dece6adc6c5e5b'
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
root = Path(tempfile.mkdtemp(prefix='dana_timer_uart_irq_', dir=BASE))
evidence = root/'evidence'
evidence.mkdir()
summary = dict(scope='DANA_TIMER_UART_IRQ_LCD_SPI2_ST_AUTHENTIC_GUEST', status='BLOCKED', reason='NOT_RUN',
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
    stage('offline-evidence',['python3','-m','unittest','f1_test_guest','d2_3_test.NativeEvidence','d2_3_test.E5',
           'd2_3_test.IntegratedGPIOAndLCD','d2_3_test.IntegratedSPI2AndKeyboard',
           'd2_3_test.IntegratedTimerUARTIRQ',
           'f1_e4_test','-v'],
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
    # Capture guest-origin MMIO and unmodified 11,200-byte framebuffer, if
    # real EmuTOS configured an eligible LCD frame before the first new block.
    integrated=[]
    for which in ('run-1','run-2'):
        folder=evidence/'guest'/which
        observation=json.loads((folder/'observation.json').read_text())
        mmio=observation['events']
        def count_mmio(lo,hi):
            # Only CPU bus transactions up to the FIRST unsupported peripheral
            # qualify native forward progress. Deferred post-block activity is
            # retained in the raw trace but not scored as working hardware.
            return sum(e.get('origin')=='cpu' and e.get('kind') in ('read','write')
                       and not e.get('after_dependency',False)
                       and lo<=e.get('address',-1)<=hi for e in mmio)
        lcd=observation.get('guest_lcd') or {}
        item=dict(run=which,spi2_cpu_events=count_mmio(0xfffff800,0xfffff803),
                  lcd_cpu_events=count_mmio(0xfffffa00,0xfffffa37),
                  timer1_cpu_events=count_mmio(0xfffff600,0xfffff60b),
                  uart1_cpu_events=count_mmio(0xfffff900,0xfffff90b),
                  guest_lcd=lcd,lcd_frame_present=False)
        framebuffer=folder/'lcd-frame.bin'
        if lcd.get('geometry_configured'):
            if not framebuffer.is_file() or framebuffer.stat().st_size!=11200:
                raise RuntimeError('BLOCKED_GUEST_LCD_FRAME_SNAPSHOT_MISSING:'+which)
            blob=framebuffer.read_bytes()
            if sum(v!=0 for v in blob)!=lcd.get('nonzero_bytes') or lcd.get('frame_bytes')!=11200:
                raise RuntimeError('BLOCKED_GUEST_LCD_FRAME_METADATA_MISMATCH:'+which)
            screen=folder/'lcd-screen.png'
            screen_sha=write_verified_guest_png(blob,screen)
            item.update(lcd_frame_present=True,lcd_frame_sha256=digest(framebuffer),
                        lcd_png_sha256=screen_sha,
                        lcd_png_class='VERIFIED_GUEST_RAM_DERIVED_NOT_MAME_WINDOW')
        elif framebuffer.exists() or (folder/'lcd-screen.png').exists():
            raise RuntimeError('BLOCKED_UNPROGRAMMED_LCD_FRAME_WRITTEN:'+which)
        # A bus readback of 0xAA is evidence of the ST greeting only if
        # the authentic 68000 performed it before any unsupported dependency.
        item['st_greeting_cpu_read'] = any(
            e.get('origin')=='cpu' and e.get('kind')=='read'
            and not e.get('after_dependency',False)
            and e.get('address')==0xfffff800
            and (e.get('data',0)&0xff)==0xaa for e in mmio)
        # Genuine 68000 low-byte write to UTX1D at effective F907. A
        # generic UART register access is insufficient for TX qualification.
        item['uart1_tx_cpu_write'] = any(
            e.get('origin')=='cpu' and e.get('kind')=='write'
            and e.get('after_dependency') is False
            and e.get('address')==0xfffff906 and e.get('mask')==0x00ff
            and e.get('byte_addresses')==[0xfffff907] for e in mmio)
        item['lcd_snapshot_class'] = (
            'UNCONFIGURED' if not lcd.get('geometry_configured') else
            'FRAME_SNAPSHOT_NONBLANK' if lcd.get('nonzero_bytes',0)>0 else
            'FRAME_SNAPSHOT_BLANK')
        integrated.append(item)
    # Genuine pre-block CPU Timer1 programming, never an 011 deferred tail.
    timer_programming=[]
    for which in ('run-1','run-2'):
        events=json.loads((evidence/'guest'/which/'observation.json').read_text())['events']
        def actual_write(addr,value):
            return [e['seq'] for e in events
                if e.get('origin')=='cpu' and e.get('kind')=='write'
                and not e.get('after_dependency',False)
                and e.get('address')==addr and e.get('mask')==0xffff
                and (e.get('data',0)&0xffff)==value]
        writes=dict(TPRER=actual_write(0xfffff602,0x0002),
                    TCMP1=actual_write(0xfffff604,0xd7e4),
                    TCTL1=actual_write(0xfffff600,0x0033))
        observed=all(writes.values())
        ordering=bool(observed and writes['TPRER'][0]<writes['TCMP1'][0]<writes['TCTL1'][0])
        timer_programming.append(dict(run=which,events=writes,pass_scoped=ordering))
    summary['timer1_cpu_programming']=timer_programming
    summary['timer1_programming_scoped_pass']=all(x['pass_scoped'] for x in timer_programming)
    # IRQ6 CPU-vector processing and UART receive must be independently
    # observed. Neither is inferred from enabled masks or register maps.
    # Real native CPU-space IACK only, not a synthetic IRQ flag, indicates
    # CPU acknowledged Timer1. Capture independently for each original run.
    import re
    irq6_runs=[]
    for which in ('run-1','run-2'):
        console=evidence/'guest'/which/'console.log'
        log=console.read_text(errors='replace')
        ack=re.findall(r'DANA_VZ_IACK level=6 vector=46 pending=([0-9a-fA-F]+) imr=([0-9a-fA-F]+) ack6=([0-9]+)',log)
        comparisons=re.findall(r'DANA_VZ_TIMER1_COMPARE count=([0-9]+) ',log)
        ack_valid=[int(n) for pending,masked,n in ack
            if int(pending,16)&2 and not int(masked,16)&2 and int(n)>0]
        irq6_runs.append(dict(run=which,compare_log_entries=len(comparisons),
                              qualifying_iacks=len(ack_valid),first_iack=ack_valid[0] if ack_valid else None))
    summary['irq6_native_evidence']=irq6_runs
    summary['timer1_irq6_delivery']=(
        'IACK_CPU_SPACE_OBSERVED_SCOPED' if all(v['qualifying_iacks']>0 and v['compare_log_entries']>0 for v in irq6_runs)
        else 'NOT_NATIVE_QUALIFIED')
    summary['uart1_serial_rx']='NOT_QUALIFIED'
    summary['integrated_observations']=integrated
    # Full system/peripheral qualification is never implied by an early
    # authentic EmuTOS first-dependency result. Interactive host keys, native
    # keyboard events and LCD graphical correctness require independent proof.
    summary['component_verdicts'] = dict(
        pfsel_A_B='PASS_SCOPED',
        timer1_guest_register_programming=('CPU_ORIGIN_PASS_SCOPED'
            if summary['timer1_programming_scoped_pass'] else 'NATIVE_PENDING'),
        timer1_irq6_delivery=summary['timer1_irq6_delivery'],
        uart1_tx=('CPU_UTX1D_WRITE_OBSERVED' if all(
            r['uart1_tx_cpu_write'] for r in integrated) else 'NATIVE_PENDING'),
        emutos_continuation=native['status'],
        spi2_st_greeting=('CPU_ORIGIN_OBSERVED'
                          if all(r['st_greeting_cpu_read'] for r in integrated)
                          else 'NATIVE_PENDING'),
        lcd_guest_frame=('CAPTURED_NONBLANK'
                         if all(r['lcd_snapshot_class']=='FRAME_SNAPSHOT_NONBLANK' for r in integrated)
                         else 'CAPTURED_BLANK' if all(r['lcd_frame_present'] for r in integrated)
                         else 'NATIVE_PENDING'),
        lcd_visual_correctness='NOT_QUALIFIED',
        keyboard_interactive='NOT_QUALIFIED',
        lcd_dma_timing='NOT_QUALIFIED',
        touchscreen='NOT_QUALIFIED',
        full_emutos_boot='NOT_QUALIFIED')
    save()
    # A scoped authentic EmuTOS continuation PASS requires two exact,
    # correctly ordered PRE-BLOCK CPU Timer1 write sequences.
    if not summary['timer1_programming_scoped_pass']:
        raise RuntimeError('BLOCKED_NATIVE_TIMER1_CPU_PROGRAMMING_NOT_PROVED')
    if native.get('status')=='REAL_PROGRESS_PASS_SCOPED' and native.get('raw_bus_prefix_equal') is not True:
        raise RuntimeError('BLOCKED_NONIDENTICAL_NATIVE_BUS_PREFIX')
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
