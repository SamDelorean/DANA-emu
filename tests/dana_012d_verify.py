#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Independent integrated evidence verification. Never launches an emulator."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import zlib

import f1_emutos_run as f1

SOURCE_012C=f1.REUSE_012C['source_commit']
ARCHIVE_012C_SHA='1fc1d8417eea975c80f29a74aa53e6ccc8fd835b2d2cc924951afec748364a18'
QUALIFICATION_012C_SHA='6fda7a9474c7594ae1019fea33766ad65c99d9e81a5d323ec1e1f6b5ba914131'
DRIVER_012C_SHA='e8211be78dfb2bf4cdc0ccabd444c97d715dc37d189d4f113f2f1cbf05b573e2'


def probe(binary,qualification):
    """Capture the live resolver inputs and FIRST failing predicate, read only."""
    result=dict(status='BLOCKED',first_failing_predicate=None,binary=str(binary),
                qualification=str(qualification),PROJECT=str(f1.PROJECT),
                manifest=str(Path(binary).parent.parent/'source-manifest.json'))
    for key,path in (('binary',Path(binary)),('qualification',Path(qualification)),
                     ('manifest',Path(result['manifest'])),('driver',f1.PROJECT/'src/mame/skeleton/alphasdana.cpp')):
        result[key+'_facts']=dict(path=str(path),resolved=str(path.resolve()),exists=path.is_file(),symlink=path.is_symlink())
        if path.is_file():result[key+'_facts']['sha256']=f1.sha(path)
    try:
        result['harness_commit']=subprocess.check_output(['git','-C',str(f1.PROJECT),'rev-parse','HEAD'],text=True).strip()
        build=f1.qualify_pfsel_build(binary,qualification)
        result.update(status='PASS',build_source_commit=build['source_commit'],binary_sha256=build['binary_sha256'])
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        result['first_failing_predicate']=str(exc)
    return result


def verdict(status,reason,**facts):return dict(status=status,reason=reason,**facts)


def png(frame,path):
    """Verbatim 560x160 monochrome RAM conversion, never host-painted content."""
    if len(frame)!=11200:raise ValueError('Incorrect framebuffer size')
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\0'+frame[y*70:(y+1)*70] for y in range(160))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',560,160,1,0,0,0,0))
        +chunk(b'tEXt',b'Provenance\0guest RAM SHA256 '+hashlib.sha256(frame).hexdigest().encode())
        +chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
    return f1.sha(Path(path))


def per_run(folder,accepted):
    """Score only an independently verified authentic run, up to its raw cutoff."""
    folder=Path(folder);obs=json.loads((folder/'observation.json').read_text())
    if accepted.get('status')=='VERIFIED_012E_PREFIX':
        cutoff=accepted['prefix_last_seq']
    else:
        if accepted.get('status')!='OBSERVED_UNQUALIFIED_SINGLE_RUN':raise ValueError('Unverified authentic run')
        cutoff=accepted['dependency_event_seq']
    rows=[e for e in obs['events'] if e['seq']<=cutoff]
    bus=[e for e in rows if e['kind'] in ('read','write') and e.get('origin')=='cpu']
    def writes(address,value):return [e for e in bus if e['kind']=='write' and e['address']==address and e['mask']==65535 and e['data']==value]
    timer=[writes(0xfffff602,2),writes(0xfffff604,0xd7e4),writes(0xfffff600,0x33)]
    programmed=all(timer) and timer[0][0]['seq']<timer[1][0]['seq']<timer[2][0]['seq']
    answer=dict(timer1=verdict('PASS' if programmed else 'BLOCKED','CPU_TIMER1_PROGRAMMING_ONLY',
                             events=[[e['seq'] for e in group] for group in timer]))
    for name,lo,hi in (('uart1_registers',0xfffff900,0xfffff90b),('spi2_registers',0xfffff800,0xfffff803)):
        seen=[e for e in bus if lo<=e['address']<=hi]
        answer[name]=verdict('PASS' if seen else 'BLOCKED','CPU_REGISTER_ACCESSES_ONLY',events=[e['seq'] for e in seen])
    # -log writes native model diagnostics to error.log. Do not concatenate a
    # mirrored console and count the same emission twice. Retain both originals.
    log_path=folder/'error.log'
    if not log_path.is_file():log_path=folder/'console.log'
    log=log_path.read_text(errors='replace') if log_path.is_file() else ''
    tx=[e for e in bus if e['kind']=='write' and e['address']==0xfffff906 and e['mask']==255
        and e['byte_addresses']==[0xfffff907]]
    emitted=[int(v,16) for v in re.findall(r'DANA_VZ_UART1_TX data=([0-9a-fA-F]{2})\b',log)]
    expected=[e['data']&255 for e in tx]
    answer['uart1_tx']=verdict('PASS' if expected and emitted[:len(expected)]==expected else 'BLOCKED',
        'CPU_UTX1D_AND_MATCHING_NATIVE_TX_LOG_REQUIRED',events=[e['seq'] for e in tx],bytes=expected,log_source=log_path.name)
    # Raw CPU-space IACK is on the SAME sequence axis as first dependency.
    # A late log entry, Timer register write or asserted pending bit cannot pass.
    iacks=[e for e in rows if e['kind']=='iack']
    for e in iacks:
        if (e.get('origin')!='cpu' or e.get('tap_id')!='f1_iack' or e.get('side_effects_disabled') is not False
                or e.get('after_dependency') is not False or e.get('byte_addresses')!=f1.selected_bytes(e)
                or e.get('width_bits')!=8*len(e['byte_addresses'])
                or not 0xfffffff0<=e['address']<=0xfffffffe):raise ValueError('Invalid CPU-space IACK provenance')
    irq6=[e for e in iacks if e['address']==0xfffffffc and e['mask']==255 and e['data']&255==0x46
          and programmed and e['seq']>timer[2][0]['seq']]
    delivered=[]
    for ack in irq6:
        fetch=[e for e in bus if e['kind']=='read' and e['seq']>ack['seq'] and e['address'] in (0x118,0x11a)]
        if len(fetch)>=2 and [(e['address'],e['mask']) for e in fetch[:2]]==[(0x118,65535),(0x11a,65535)]:
            handler=(fetch[0]['data']<<16)|fetch[1]['data']
            pcs=[int(v,16) for v in re.findall(r'^\s*([0-9a-fA-F]+):',(folder/'guest.trace').read_text(),re.M)]
            if 0<=handler<0x400000 and handler in pcs:delivered.append(dict(ack=ack['seq'],handler=handler))
    compare=bool(re.search(r'DANA_VZ_TIMER1_COMPARE count=[1-9][0-9]* ',log))
    pending=any(int(p,16)&2 and not int(m,16)&2 and int(n)>0 for p,m,n in
        re.findall(r'DANA_VZ_IACK level=6 vector=46 pending=([0-9a-fA-F]+) imr=([0-9a-fA-F]+) ack6=([0-9]+)',log))
    answer['irq6']=verdict('PASS' if programmed and delivered and compare and pending else 'BLOCKED',
        'PRE_DEPENDENCY_CPU_IACK_VECTOR_FETCH_AND_HANDLER_TRACE',observed_iacks=[e['seq'] for e in irq6],delivery=delivered)
    answer['irq_other']=verdict('PASS' if any(e['address']!=0xfffffffc for e in iacks) else 'BLOCKED',
                                'RAW_CPU_IACK_OBSERVATION_ONLY',events=[e['seq'] for e in iacks if e['address']!=0xfffffffc])
    greetings=[]
    for e in bus:
        if e['kind']!='read' or e['address']!=0xfffff800 or not e['mask']&255 or e['data']&255!=0xaa:continue
        earlier=[x for x in bus if x['seq']<e['seq']]
        controls=[x for x in earlier if x['kind']=='write' and x['address']==0xfffff802 and x['mask']==65535
                  and x['data']&0x210f==0x2107]
        if not controls:continue
        control=controls[-1]
        data=[x for x in earlier if x['kind']=='write' and x['address']==0xfffff800 and x['seq']<control['seq'] and x['mask']&255]
        completion=[x for x in earlier if x['kind']=='read' and x['address']==0xfffff802
                    and control['seq']<x['seq'] and x['mask']&255 and x['data']&0x80]
        if data and completion:greetings.append(dict(data=data[-1]['seq'],exchange=control['seq'],complete=completion[-1]['seq'],greeting=e['seq']))
    answer['st_greeting']=verdict('PASS' if greetings else 'BLOCKED','CPU_SPI2_EXCHANGE_COMPLETION_AND_AA_READ',transactions=greetings)
    lcd=obs.get('guest_lcd') or {};frame=folder/'lcd-frame.bin'
    if lcd.get('geometry_configured'):
        valid=(lcd.get('lssa',1)&1)==0 and 0<=lcd['lssa']<=0x400000-11200 and all(lcd.get(k)==v for k,v in
             (('lvpw',35),('lxmax',560),('lymax',159),('lpicf',8))) and lcd.get('lckcon',0)&0x80
        if not valid or not frame.is_file() or frame.stat().st_size!=11200:raise ValueError('Missing/invalid native LCD snapshot')
        content=frame.read_bytes()
        if lcd.get('frame_bytes')!=11200 or lcd.get('nonzero_bytes')!=sum(v!=0 for v in content):raise ValueError('LCD metadata mismatch')
        answer['lcd_frame']=verdict('PASS' if any(content) else 'BLOCKED','NATIVE_GUEST_RAM_SNAPSHOT_AT_DEFERRED_CAPTURE',
            sha256=f1.sha(frame),bytes=11200,nonzero_bytes=lcd['nonzero_bytes'],pre_dependency_time_proven=False,
            png_sha256=png(content,folder/'lcd-screen.png'))
    else:
        if frame.exists():raise ValueError('Unconfigured framebuffer supplied')
        answer['lcd_frame']=verdict('BLOCKED','NO_CONFIGURED_NATIVE_FRAME')
    for name in ('uart1_rx','keyboard_interaction','full_boot','lcd_window'):
        answer[name]=verdict('BLOCKED','NOT_EXERCISED_OR_NOT_IN_SCOPE')
    return answer


def dependency_instruction(folder,dependency):
    pc=dependency['state']['CURPC']
    text=(Path(folder)/'guest.trace').read_text()
    for line in text.splitlines():
        match=re.match(r'^\s*([0-9a-fA-F]+):\s*(.*)$',line)
        if match and int(match[1],16)==pc:return dict(PC=pc,disassembly=match[2],raw_line=line)
    raise ValueError('First unsupported instruction absent from native trace')


def verify(root,guest,qualification):
    root=Path(root)
    try:
        native=f1.verify_e4_pair(root,guest,qualification=qualification)
        if native['status']!='REAL_PROGRESS_PASS_SCOPED' or native.get('raw_bus_prefix_equal') is not True:
            return verdict('BLOCKED','TWO_VERIFIED_EQUAL_NATIVE_BUS_PREFIXES_REQUIRED',native=native)
        instructions=[dependency_instruction(root/name,native['normalized_dependency']) for name in ('run-1','run-2')]
        if instructions[0]!=instructions[1]:raise ValueError('Nonreproducible first unsupported instruction')
        runs=[per_run(root/name,item) for name,item in zip(('run-1','run-2'),native['runs'])]
        components={name:verdict('PASS' if all(row[name]['status']=='PASS' for row in runs) else 'BLOCKED',
                               'BOTH_AUTHENTIC_PROCESSES_REQUIRED',runs=[row[name] for row in runs]) for name in runs[0]}
        status='PASS' if components['timer1']['status']=='PASS' else 'BLOCKED'
        return verdict(status,'AUTHENTIC_CONTINUATION_SCOPED_ONLY',components=components,
                       next_dependency=native['normalized_dependency'],first_unsupported_instruction=instructions[0],native=native,full_boot=False)
    except (OSError,ValueError,KeyError,TypeError,IndexError,subprocess.SubprocessError) as exc:
        return verdict('BLOCKED',str(exc),full_boot=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('guest_runs',type=Path);p.add_argument('guest',type=Path)
    p.add_argument('qualification',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    result=verify(args.guest_runs,args.guest,args.qualification);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='PASS' else 2)
