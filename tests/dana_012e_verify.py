#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Loss-accounted 012-E native observation verifier. Never executes an emulator."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

import f1_emutos_run as f1
from f1_guest import validate_qualified
from d2_2_gpio_run import staged_identity
import dana_012d_verify as prior

LIMITS=json.loads((f1.HERE/'dana_012e_limits.json').read_text())
LIMITS_SHA=f1.sha(f1.HERE/'dana_012e_limits.json')
OBS_SHA=f1.sha(f1.HERE/'dana_012e_observer.lua')
BOOT_SHA=f1.sha(f1.HERE/'f1_emutos_boot.lua')
STATE_FIELDS=('CURPC','PC','SR','SP','IR')+tuple('D'+str(i) for i in range(8))+tuple('A'+str(i) for i in range(7))+('USP',)
BOUND_REASONS={
    'OBSERVATION_LIMIT_RAW','OBSERVATION_LIMIT_EVENTS','OBSERVATION_LIMIT_EVENT_BYTES',
    'OBSERVATION_LIMIT_CHECKPOINTS','OBSERVATION_LIMIT_CYCLES','OBSERVATION_LIMIT_LOG',
    'OBSERVATION_LIMIT_TRACE','OBSERVATION_LIMIT_TIME'}


def check(condition,message):
    if not condition:raise ValueError(message)


def cap(status,scope,**facts):return dict(status=status,scope=scope,**facts)


def trace_info(path):
    check(0<path.stat().st_size<=LIMITS['max_file_bytes'],'Trace hard size bound')
    pcs=[];instructions=[];interrupts=[];suppressed=0
    with path.open() as stream:
        for number,line in enumerate(stream):
            line=line.rstrip('\n')
            pc=re.match(r'^\s*([0-9a-fA-F]+):\s*(\S.*)$',line)
            loop=re.fullmatch(r'\s*\(loops for ([0-9]+) instructions\)\s*',line)
            irq=re.fullmatch(r'\s*\(interrupted at ([0-9a-fA-F]+), IRQ ([0-7])\)\s*',line)
            if pc:
                pcs.append(int(pc[1],16));instructions.append(dict(PC=int(pc[1],16),text=pc[2],line=number))
            elif loop:suppressed+=int(loop[1])
            elif irq:interrupts.append(dict(PC=int(irq[1],16),level=int(irq[2]),line=number))
            else:check(not line.strip(),'Unknown native trace record')
    check(pcs,'No native instructions')
    return dict(pcs=pcs,instructions=instructions,interrupts=interrupts,
        emitted_instructions=len(pcs),reported_loop_instructions=suppressed,
        instruction_lower_bound=len(pcs)+suppressed,exact_instruction_count=None,
        pending_native_loop_tail='NOT_REPORTED_BY_PINNED_TRACER_ON_CLOSE',sha256=f1.sha(path))


def rows_info(obs):
    rows=obs['events'];stats=obs['compression_stats']
    check(isinstance(rows,list) and 0<len(rows)<=LIMITS['max_retained_events'],'Retained event bound')
    check(obs.get('event_count')==len(rows),'Observation event count')
    check(len(json.dumps(rows,separators=(',',':')).encode())<=LIMITS['max_event_bytes'],'Event byte bound')
    check(stats.get('compression')=='exact_full_state_F202_RLE_v1','Unknown compression contract')
    cursor=0;last_time=0;epoch=0;counts=dict(native_reads=0,native_writes=0,native_iacks=0,poll_reads=0)
    bus=[];progress=[];polls=[]
    for seq,e in enumerate(rows):
        check(type(e.get('seq')) is int and type(e.get('raw_first')) is int and e['seq']==seq and e['raw_first']==cursor,'Missing/replayed compressed sequence')
        state=e['state'];check(all(type(state.get(k)) is int for k in STATE_FIELDS),'CPU state missing')
        check(type(e['virtual_seconds']) in (int,float),'Missing virtual time')
        stop=e.get('last_virtual_seconds',e['virtual_seconds'])
        check(last_time<=e['virtual_seconds']<=stop<=obs['virtual_seconds'],'Overlapping/reordered compression interval')
        last_time=stop
        kind=e['kind'];n=e.get('count',1)
        check(type(n) is int and 1<=n<=LIMITS['max_raw_observations'],'Invalid raw count')
        check(e.get('raw_last')==cursor+n-1,'Incorrect compressed raw range')
        if kind=='iack':epoch+=1
        check(type(e.get('epoch')) is int and e['epoch']==epoch,'Compression crossed an interrupt boundary')
        if kind in ('read','write','iack','poll_span'):
            operation='read' if kind=='poll_span' else kind
            wanted_tap='f1_iack' if kind=='iack' else 'f1_'+operation
            check(e.get('origin')=='cpu' and e.get('side_effects_disabled') is False and e.get('tap_id')==wanted_tap,'Forged native bus origin')
            selected=f1.selected_bytes(e)
            check(e.get('byte_addresses')==selected and e.get('width_bits')==8*len(selected),'Wrong bus lane')
            check(type(e['data']) is int and 0<=e['data']<=65535,'Invalid native data')
            check(type(e.get('after_dependency')) is bool,'Ambiguous deferred bus status')
            if kind=='poll_span':
                check((e['address'],e['mask'],e.get('operation'))==(0xfffff202,65535,'read'),'Unapproved compressed MMIO')
                check(e.get('role') is None and e.get('first_pc')==e.get('last_pc')==state['CURPC'],'Poll PC/role changed')
                check(0<=e['max_gap_seconds']<=stop-e['virtual_seconds']+1e-12,'Invalid poll gap')
                check(n>1 or stop==e['virtual_seconds'],'Singleton poll interval')
                counts['poll_reads']+=n;polls.append(e)
            else:check(n==1,'Causal event compressed')
            counts['native_iacks' if kind=='iack' else 'native_writes' if kind=='write' else 'native_reads']+=n
            bus.append(e)
        else:
            check(n==1 and kind in ('first_instruction','milestone','progress'),'Unknown observation kind')
            check(e.get('origin')=='debugger_observation','Forged instruction/progress observation')
            if kind=='progress':progress.append(e)
        cursor+=n
    check(all(type(stats.get(k)) is int for k in ('accepted_raw','attempted_raw','retained_events','native_reads','native_writes','native_iacks','poll_reads','reserved_bytes')),'Non-integer native accounting')
    check(cursor<=LIMITS['max_raw_observations'],'Raw observation bound')
    check(stats.get('accepted_raw')==cursor and stats.get('retained_events')==len(rows),'Raw/retained count mismatch')
    for name,value in counts.items():check(stats.get(name)==value,'Lost native count: '+name)
    dropped=stats.get('dropped_raw');check(type(dropped) is int and dropped>=0,'Missing loss accounting')
    check(stats.get('attempted_raw')==cursor+dropped,'Attempted count mismatch')
    check(stats.get('reserved_bytes',LIMITS['max_event_bytes']+1)<=LIMITS['max_event_bytes'],'Reservation budget')
    if dropped:
        overflow=stats.get('overflow') or {}
        check(overflow.get('reason')==obs['reason'] and obs['reason'] in BOUND_REASONS,'Undeclared observation loss')
        check(overflow.get('first_unrecorded',{}).get('raw_first')==cursor,'Unknown first omitted observation')
    else:check(not stats.get('overflow'),'Spurious overflow')
    return bus,progress,polls,counts


def irq_service(bus,trace,base):
    acks=[e for e in bus if e['kind']=='iack' and (e['address'],e['mask'],e['data']&255)==(0xfffffffc,255,0x46)]
    delivered=[];rte_text={e['PC'] for e in trace['instructions'] if re.match(r'rte\b',e['text'],re.I)}
    for ack in acks:
        following=[e for e in bus if e['seq']>ack['seq'] and e['epoch']==ack['epoch']]
        vectors=[e for e in following if e['kind']=='read' and e['address'] in (0x118,0x11a)]
        if len(vectors)<2 or [(e['address'],e['mask']) for e in vectors[:2]]!=[(0x118,65535),(0x11a,65535)]:continue
        handler=vectors[0]['data']<<16|vectors[1]['data']
        frame=[e for e in following if e.get('role')=='rte' and e['kind']=='read' and e['mask']==65535 and e['state']['IR']==0x4e73 and e['seq']>vectors[1]['seq']]
        for i in range(len(frame)-2):
            words=frame[i:i+3];a=words[0]['address'];pc=words[0]['state']['CURPC']
            if not (0<=a<0x400000-6 and [e['address'] for e in words]==[a,a+2,a+4]
                    and all(e['state']['CURPC']==pc for e in words) and pc in rte_text):continue
            # Reject opcode/data fetches accidentally resembling a frame.
            if not any(abs(e['state']['SP']-a)<=6 for e in words):continue
            restored_sr=words[0]['data'];restored_pc=words[1]['data']<<16|words[2]['data']
            resumed=[e for e in following if e.get('role')=='resume' and e['seq']>words[2]['seq']
                and e['state']['SP']==a+6 and e['state']['SR']==restored_sr and e['state']['CURPC']==restored_pc]
            markers=[e for e in trace['interrupts'] if e['level']==6]
            if resumed and handler in trace['pcs'] and markers:
                delivered.append(dict(iack_seq=ack['seq'],handler=handler,rte_pc=pc,frame_address=a,
                                      resume_seq=resumed[0]['seq'],restored_pc=restored_pc,restored_sr=restored_sr));break
    status='PASS' if delivered and base['irq6']['status']=='PASS' else 'PARTIAL' if acks else 'NOT_REACHED'
    return cap(status,'CPU_IACK_VECTOR_HANDLER_RTE_FRAME_AND_RESUME',ack_count=len(acks),completed=delivered)


def verify_run(folder,guest,qualification,expected_source=None):
    folder=Path(folder)
    try:
        manifest=validate_qualified(guest);syms=manifest['symbols']
        run=json.loads((folder/'run.json').read_text());obs=json.loads((folder/'observation.json').read_text())
        staged_identity(run);source=expected_source or subprocess.check_output(['git','-C',str(f1.PROJECT),'rev-parse','HEAD'],text=True).strip()
        build=f1.qualify_pfsel_build(Path(run['command'][0]),qualification,source)
        hardware=run.get('integrated_hardware')
        if hardware is not None:
            check(hardware is True and obs.get('integrated_hardware') is True,'Unbound hardware profile')
            check(build['source_commit']==source and build['binary_sha256']!=f1.REUSE_012C['binary_sha256'],'New same-source hardware build required')
            compiled=subprocess.check_output(['git','-C',str(f1.PROJECT),'show',source+':src/mame/skeleton/alphasdana.cpp'])
            check(hashlib.sha256(compiled).hexdigest()==build['driver_sha256'],'Build differs from frozen Git hardware')
        else:
            check(obs.get('integrated_hardware') is None,'Unbound hardware profile')
            check(build['source_commit']==f1.REUSE_012C['source_commit'] and build['binary_sha256']==f1.REUSE_012C['binary_sha256'],'012-C runtime required')
        identities=dict(observation_profile='012-E',revision='F1-E5',variant='diag',source_commit=source,
            build_source_commit=build['source_commit'],binary_sha256=build['binary_sha256'],
            qualification_sha256=f1.sha(Path(qualification)),package_sha256=manifest['package']['sha256'],
            image_sha256=manifest['artifacts']['emutos.img']['sha256'],limits_sha256=LIMITS_SHA,
            observer_sha256=OBS_SHA,boot_sha256=BOOT_SHA,full_boot=False)
        for key,value in identities.items():check(run.get(key)==obs.get(key)==value,'Unbound '+key)
        check(run.get('full_boot') is False and obs.get('full_boot') is False,'False full-boot claim')
        check(type(run.get('exit_code')) is int and run['exit_code']==0 and type(run.get('pid')) is int and run['pid']>0,'Native exit/identity')
        check(re.fullmatch('[0-9a-f]{32}',run.get('execution_id','')) and run['execution_id']==obs.get('execution_id'),'Execution identity')
        check(obs.get('status')=='CAPTURED' and obs.get('schema')=='dana-012e-observation-v1','Missing native observation')
        check(obs.get('trace_mode')=='native_loop_compression_no_sampling','Sampled instruction trace')
        check(obs.get('observation_limits')==LIMITS,'Changed/unbounded observation limits')
        check(obs['reason'] in BOUND_REASONS|{'BLOCKED_HARDWARE','BLOCKED_GUEST_ADDRESS'},'Unknown termination policy')
        check(0<=obs['virtual_seconds']<=LIMITS['max_virtual_seconds']+0.25,'Virtual-time bound/overshoot')
        check(f1.sha(folder/'initial-image.bin')==identities['image_sha256'],'Unverified native loaded image')
        bus,progress,polls,counts=rows_info(obs)
        vector=[(e['kind'],e['address'],e['mask'],e['data']) for e in bus[:4]]
        check(vector==[('read',a,65535,v) for a,v in ((0,syms['_stktop']>>16),(2,syms['_stktop']&65535),(4,syms['_os_header']>>16),(6,syms['_os_header']&65535))],'CPU reset vector reads')
        first=[e for e in obs['events'] if e['kind']=='first_instruction']
        check(len(first)==1 and first[0]['state']==obs['first_instruction'],'Unbound CPU entry')
        check((first[0]['state']['CURPC'],first[0]['state']['SP'],first[0]['state']['SR'])==(syms['_os_header'],syms['_stktop'],0x2700),'Map-bound entry')
        check(bus[3]['seq']<first[0]['seq'] and [e for e in bus if e['seq']<first[0]['seq']]==bus[:4],'Pre-entry replay/extra vectors')
        trace=trace_info(folder/'guest.trace')
        check(trace['pcs'][0]==syms['_os_header'] and trace['pcs'].count(syms['_os_header'])==1,'Guest trace replay')
        check(obs['trace_bytes']==(folder/'guest.trace').stat().st_size,'Trace byte mismatch')
        startup=['_os_header','_main','_realmain']+(['_dana_init'] if '_dana_init' in syms else [])
        indexes=[trace['pcs'].index(syms[k]) for k in startup]
        check(indexes==sorted(set(indexes)),'Startup path order')
        for name in startup[1:]:
            hits=[e for e in obs['events'] if e['kind']=='milestone' and e['state']['CURPC']==syms[name]]
            check(len(hits)==1,'Missing/replayed startup milestone')
        for name in ('console.log','error.log'):
            path=folder/name
            if path.exists():check(path.stat().st_size<=LIMITS['max_file_bytes'],'Native log hard bound')
        check(0<len(progress)<=LIMITS['max_checkpoints'],'Missing native cycle checkpoints')
        cycle_lines=(folder/'cycles.log').read_text().splitlines()
        check(len(cycle_lines)==len(progress),'Lost/duplicated native cycle output')
        cycles=[]
        for token,(row,line) in enumerate(zip(progress,cycle_lines),1):
            match=re.fullmatch(r'\s*DANA012E token=([0-9A-Fa-f]+) cycles=([0-9A-Fa-f]+)\s*',line)
            check(match and int(match[1],16)==row.get('token')==token and int(match[2],16)==row.get('totalcycles'),'Forged/stale native cycles')
            check(row.get('cycle_api')=='native_debugger_totalcycles','Estimated cycle counter')
            cycles.append(row['totalcycles'])
        check(cycles==sorted(cycles),'CPU cycles reversed')
        check(cycles[-1]-cycles[0]<=LIMITS['max_cycles']+10000000,'Cycle bound overshoot')
        reason=obs['reason']
        if reason=='OBSERVATION_LIMIT_TIME':check(obs['virtual_seconds']>=LIMITS['max_virtual_seconds'],'Unreached virtual-time limit')
        if reason=='OBSERVATION_LIMIT_CYCLES':check(cycles[-1]-cycles[0]>=LIMITS['max_cycles'],'Unreached native-cycle limit')
        if reason=='OBSERVATION_LIMIT_TRACE':check(obs['trace_bytes']>LIMITS['max_trace_bytes'],'Unreached trace trigger')
        if reason=='OBSERVATION_LIMIT_LOG':check(any((folder/n).exists() and (folder/n).stat().st_size>LIMITS['max_log_bytes'] for n in ('console.log','error.log')),'Unreached log trigger')
        if reason=='OBSERVATION_LIMIT_CHECKPOINTS':check(len(progress)==LIMITS['max_checkpoints'],'Unreached checkpoint limit')
        if reason in ('OBSERVATION_LIMIT_RAW','OBSERVATION_LIMIT_EVENTS','OBSERVATION_LIMIT_EVENT_BYTES'):
            check(obs['compression_stats']['dropped_raw']>0,'Unrecorded budget boundary required')
        if reason=='OBSERVATION_LIMIT_RAW':check(obs['compression_stats']['accepted_raw']==LIMITS['max_raw_observations'],'Unreached raw limit')
        if reason=='OBSERVATION_LIMIT_EVENTS':check(len(obs['events'])==LIMITS['max_retained_events'],'Unreached retained-event limit')
        check(all(type(obs['final'].get(k)) is int for k in ('CURPC','PC','SP','SR','IR')),'Missing terminal CPU state')
        missing=[]
        for e in bus:
            if e['kind']=='iack':continue
            for address in f1.selected_bytes(e):
                if address>=0x400000 and not f1.implemented_byte(address,'read' if e['kind']=='poll_span' else e['kind'],True,hardware is True):missing.append((e,address))
        dep=None;instruction=None
        if missing:
            event,effective=missing[0];dep=obs.get('dependency')
            check(isinstance(dep,dict) and dep.get('event_seq')==event['seq'] and dep.get('effective_address')==effective,'Invented/misordered first dependency')
            for key in ('kind','address','data','mask','state','byte_addresses','width_bits','origin','tap_id'):check(dep.get(key)==event[key],'Dependency raw evidence mismatch')
            instruction=prior.dependency_instruction(folder,dict(state=event['state']))
            cutoff=event['seq']
        else:
            check(obs.get('dependency') is None and obs['reason'] in BOUND_REASONS,'Manufactured dependency/termination')
            cutoff=len(obs['events'])-1
        for e in bus:check(e['after_dependency'] is (e['seq']>cutoff),'Hidden deferred tail')
        prefix=[e for e in bus if e['seq']<=cutoff]
        check(all(e['state']['CURPC'] in trace['pcs'] for e in prefix[4:]),'CPU bus PC absent from native trace')
        base=prior.per_run(folder,dict(status='VERIFIED_012E_PREFIX',prefix_last_seq=cutoff))
        components={name:cap(value['status'],value['reason'],evidence=value) for name,value in base.items()}
        pfread=[e for e in prefix if e['kind']=='read' and (e['address'],e['mask'],e['data']&255,e['state']['CURPC'])==(0xfffff42a,255,0xc5,0x83a2)]
        pfwrite=[e for e in prefix if e['kind']=='write' and (e['address'],e['mask'],e['data']&255,e['state']['CURPC'])==(0xfffff42a,255,0xc5,0x83a8)]
        pfseen=any(e['address']==0xfffff42a for e in prefix)
        components['pfsel']=cap('PASS' if len(pfread)==len(pfwrite)==1 and pfread[0]['seq']<pfwrite[0]['seq'] else 'PARTIAL' if pfseen else 'NOT_REACHED','AUTHENTIC_C5_READ_ORI_WRITE')
        components['irq6']=irq_service(prefix,trace,base)
        # A native compare log alone may belong to a deferred capture tail.
        status_read=any(e['kind']=='read' and e['address']==0xfffff60a and e['mask']&1 and e['data']&1 for e in prefix)
        log=(folder/'error.log').read_text(errors='replace') if (folder/'error.log').exists() else (folder/'console.log').read_text(errors='replace')
        compare=bool(re.search(r'DANA_VZ_TIMER1_COMPARE count=[1-9][0-9]* ',log))
        components['timer1_compare']=cap('PASS' if compare and (status_read or components['irq6']['status']=='PASS') else 'PARTIAL' if compare else 'NOT_REACHED','NATIVE_COMPARE_WITH_CPU_STATUS_OR_COMPLETED_IRQ')
        for name,lo,hi in (('uart1_tx',0xfffff900,0xfffff90b),('uart1_registers',0xfffff900,0xfffff90b),('timer1',0xfffff600,0xfffff60b),('spi2_registers',0xfffff800,0xfffff803),('st_greeting',0xfffff800,0xfffff803)):
            if components[name]['status']=='BLOCKED':components[name]['status']='PARTIAL' if any(lo<=e['address']<=hi for e in prefix) else 'NOT_REACHED'
        # Controller programming and captured pixels have separate causal scopes.
        lcd=obs.get('guest_lcd') or {};written={}
        for e in prefix:
            if e['kind']=='write':
                for a in e['byte_addresses']:
                    if 0xfffffa00<=a<=0xfffffa37:written[a]=(e['data']>>(8 if a%2==0 else 0))&255
        expected={}
        for address,value,size in ((0xfffffa00,lcd.get('lssa',0),4),(0xfffffa05,35,1),
                (0xfffffa08,560,2),(0xfffffa0a,159,2),(0xfffffa20,8,1),(0xfffffa27,0x80,1)):
            for offset in range(size):expected[address+offset]=(value>>(8*(size-offset-1)))&255
        controller=bool(lcd.get('geometry_configured') and all(written.get(a)==value for a,value in expected.items()))
        components['lcd_controller']=cap('PASS' if controller else 'PARTIAL' if written else 'NOT_REACHED','CPU_LCD_REGISTER_BYTES_AND_NATIVE_GEOMETRY')
        if components['uart1_tx']['status']=='PASS':
            tx=[e for e in prefix if e['kind']=='write' and e['address']==0xfffff906 and e['mask']==255]
            if not all(any(r['kind']=='read' and r['address']==0xfffff906 and r['mask']&0x2000 and r['data']&0x2000 and r['seq']<e['seq'] for r in prefix) for e in tx):
                components['uart1_tx']['status']='PARTIAL'
        if components['st_greeting']['status']=='PASS':
            transactions=base['st_greeting']['transactions']
            def selected_before(seq):
                rows=[e for e in prefix if e['kind']=='write' and 0xfffff421 in e['byte_addresses'] and e['seq']<seq]
                return bool(rows and not rows[-1]['data']&8)
            ready=lambda seq:any(e['kind']=='read' and 0xfffff441 in e['byte_addresses'] and e['data']&4 and e['seq']<seq for e in prefix)
            if not any(selected_before(t['exchange']) and ready(t['exchange']) for t in transactions):components['st_greeting']['status']='PARTIAL'
        exchanges=[]
        previous_control=-1
        for control in prefix:
            if not (control['kind']=='write' and control['address']==0xfffff802 and control['mask']==65535 and control['data']&(0x030f if hardware else 0x210f)==(0x0307 if hardware else 0x2107)):continue
            next_control=next((e['seq'] for e in prefix if e['kind']=='write' and e['address']==0xfffff802 and e['data']&0x100 and e['seq']>control['seq']),len(obs['events']))
            data=[e for e in prefix if e['kind']=='write' and e['address']==0xfffff800 and e['mask']&255 and previous_control<e['seq']<control['seq']]
            done=[e for e in prefix if e['kind']=='read' and e['address']==0xfffff802 and e['mask']&255 and e['data']&0x80 and control['seq']<e['seq']<next_control]
            if data and done:
                received=[e for e in prefix if e['kind']=='read' and e['address']==0xfffff800 and e['mask']&255 and done[0]['seq']<e['seq']<next_control]
                if received:exchanges.append(dict(data=data[-1]['seq'],exchange=control['seq'],complete=done[0]['seq'],received=received[0]['seq'],value=received[0]['data']&255))
            previous_control=control['seq']
        components['spi2_exchange']=cap('PASS' if exchanges else 'PARTIAL' if any(0xfffff800<=e['address']<=0xfffff803 for e in prefix) else 'NOT_REACHED','CPU_DATA_CONTROL_COMPLETION_AND_RX_READ',transactions=exchanges)
        if components['st_greeting']['status']=='PASS' and not any(e['value']==0xaa for e in exchanges):components['st_greeting']['status']='PARTIAL'
        if components['lcd_frame']['status']=='PASS' and (dep or obs['compression_stats']['dropped_raw']):components['lcd_frame']['status']='PARTIAL'
        if components['lcd_frame']['status']=='BLOCKED' and not any(0xfffffa00<=e['address']<=0xfffffa37 for e in prefix):components['lcd_frame']['status']='NOT_REACHED'
        if hardware:
            # Register acceptance and completed native MAME serial frames are
            # distinct. Old immediate-TX logs cannot qualify the new engine.
            tx=[e for e in prefix if e['kind']=='write' and e['address']==0xfffff906 and e['mask']&255]
            emitted=[(int(n),int(b,16),float(t)) for n,b,t in re.findall(
                r'DANA_VZ_UART1_SERIAL_TX count=([0-9]+) data=([0-9a-fA-F]{2}) time=([0-9.]+)',log)]
            check([n for n,_,_ in emitted]==list(range(1,len(emitted)+1)),'Replayed serial completions')
            completed=[(b,t) for _,b,t in emitted if t<=(prefix[-1]['virtual_seconds'] if dep else obs['virtual_seconds'])]
            enabled=0;tx_control=0;misc=0;eligible=[]
            for e in prefix:
                if e['kind']=='write' and e['address']==0xfffff900:enabled=(enabled & ~e['mask']) | (e['data'] & e['mask'])
                if e['kind']=='write' and e['address']==0xfffff908:misc=(misc & ~e['mask']) | (e['data'] & e['mask'])
                if e['kind']=='write' and e['address']==0xfffff906:tx_control=(tx_control & ~e['mask']) | (e['data'] & e['mask'])
                if e in tx and enabled&0xa000==0xa000 and (tx_control&0x800 or misc&0x1000):eligible.append(e)
            exact=bool(eligible and len(eligible)==len(tx)==len(completed) and
                all(e['data']&255==b and e['virtual_seconds']<=t and any(
                    r['kind']=='read' and r['address']==0xfffff906 and r['mask']&0x2000 and r['data']&0x2000 and r['seq']<e['seq']
                    for r in prefix) for e,(b,t) in zip(eligible,completed)))
            components['uart1_tx']=cap('PASS' if exact and not dep else 'PARTIAL' if tx else 'NOT_REACHED',
                'CPU_ENABLED_TX_AND_TIME_BOUND_NATIVE_SERIAL_COMPLETION',completed_frames=len(completed))
            # A saved MAME screen is separate evidence from a host-decoded RAM
            # illustration. Compare every native pixel to the captured RAM;
            # frame-update skew remains PARTIAL, never a fabricated match.
            rendered=lcd.get('native_pixels');frame=folder/'lcd-frame.bin';pixels=folder/'lcd-native-pixels.bin'
            components['lcd_presentation']=cap('NOT_REACHED','NATIVE_MAME_PIXELS_VS_GUEST_RAM')
            if rendered:
                check(rendered.get('width')==560 and rendered.get('height')==160 and rendered.get('bytes')==358400,'Native LCD dimensions')
                check(rendered.get('byte_order') in ('little','big'),'Native LCD byte order')
                raw=pixels.read_bytes();fb=frame.read_bytes()
                check(len(raw)==358400 and len(fb)==11200,'Native LCD payload bounds')
                png=(folder/'lcd-native.png').read_bytes()
                check(png[:8]==b'\x89PNG\r\n\x1a\n' and len(png)>=24 and png[12:16]==b'IHDR'
                    and int.from_bytes(png[16:20],'big')==560 and int.from_bytes(png[20:24],'big')==160,'Invalid native screen snapshot')
                powered=bool(lcd.get('pkdata',0)&0x80)
                expected=[0x404040 if powered and bool((b>>bit)&1)^bool(lcd.get('lpolcf',0)&1) else 0xbdbdaa
                    for b in fb for bit in range(7,-1,-1)]
                actual=[int.from_bytes(raw[i:i+4],rendered['byte_order'])&0xffffff for i in range(0,len(raw),4)]
                exact=not lcd.get('lposr') and actual==expected
                components['lcd_presentation']=cap('PASS' if exact and powered and controller and not dep else 'PARTIAL',
                    'NATIVE_MAME_PIXELS_VS_GUEST_RAM',all_pixels_match=exact,powered=powered,
                    pixel_sha256=f1.sha(pixels),png_sha256=f1.sha(folder/'lcd-native.png'))
            requests=[e for e in obs['events'] if e['kind']=='host_input']
            for e in requests:check(e.get('origin')=='host_request' and e.get('field')=='A' and e.get('value') in (0,1),'Forged input request')
            check([e['value'] for e in requests] in ([],[1],[1,0]),'Replayed input requests')
            for e in requests:
                target=4 if e['value'] else 4.25
                check(target<=e['virtual_seconds']<=target+0.25,'Unbound input schedule')
            values=[(e['received'],e['value']) for e in exchanges]
            press=requests[0]['seq'] if requests else len(obs['events'])
            release=requests[1]['seq'] if len(requests)==2 else len(obs['events'])
            down=any(press<h<k<release and a==0x41 and b==0x2b for (h,a),(k,b) in zip(values,values[1:]))
            up=any(s>release and value==0x40 for s,value in values)
            components['st_keyboard']=cap('PASS' if down and up and not dep else 'PARTIAL' if requests else 'NOT_REACHED',
                'HOST_INPUT_THROUGH_CPU_SPI2_ST_PRESS_RELEASE',press_snapshot=down,release_snapshot=up,
                os_consumption_proven=False)
        active=cycles[-1]>cycles[0]
        edges=sum(bool((a['data']^b['data'])&0x8000) for a,b in zip(polls,polls[1:]) if a['epoch']==b['epoch'])
        activity=dict(native_cycle_delta=cycles[-1]-cycles[0],native_bus_reads=counts['native_reads'],poll_reads=counts['poll_reads'],clock_value_transitions=edges,
            classification=('ACTIVE_CLOCK_POLL_WAIT' if edges else 'POLLING_WITHOUT_OBSERVED_CLOCK_TRANSITION') if active and polls else 'CPU_ACTIVITY' if active else 'QUIESCENT_UNCLASSIFIED',
            repeated_polls_count_as_forward_progress=False,stall_proven=False)
        components['timer1_programming']=components.pop('timer1')
        complete_irq=components['irq6']['status']=='PASS'
        activity['functional_progress_proven']=complete_irq or any(components[k]['status']=='PASS' for k in ('uart1_tx','st_greeting'))
        output_seqs=base['uart1_tx'].get('events',[])+[x['greeting'] for x in base['st_greeting'].get('transactions',[])]
        activity['wait_exit_with_output_proven']=bool(polls and output_seqs and max(output_seqs)>max(e['seq'] for e in polls))
        check(obs['compression_stats']['dropped_raw']==0 or obs['reason'] in BOUND_REASONS,'Unexplained lost causal evidence')
        return dict(status='VERIFIED_012E_PREFIX',components=components,activity=activity,
            dependency=dep,first_unsupported_instruction=instruction,termination=obs['reason'],
            compression_stats=obs['compression_stats'],trace_accounting={k:v for k,v in trace.items() if k not in ('pcs','instructions','interrupts')},
            pid=run['pid'],execution_id=run['execution_id'],binary_sha256=run['binary_sha256'],source_commit=source,full_boot=False)
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError,subprocess.SubprocessError) as exc:
        return dict(status='BLOCKED',reason=str(exc),full_boot=False)


def verify_pair(root,guest,qualification,expected_source=None):
    runs=[verify_run(Path(root)/name,guest,qualification,expected_source) for name in ('run-1','run-2')]
    if any(r['status']!='VERIFIED_012E_PREFIX' for r in runs):return dict(status='BLOCKED',runs=runs,reason='TWO_AUTHENTIC_VERIFIED_PREFIXES_REQUIRED',full_boot=False)
    a,b=runs
    if a['pid']==b['pid'] or a['execution_id']==b['execution_id']:return dict(status='BLOCKED',runs=runs,reason='PROCESS_REPLAY',full_boot=False)
    def depkey(d):return None if d is None else tuple(d[k] for k in ('effective_address','address','mask','kind'))+(d['state']['CURPC'],d['state']['IR'])
    if depkey(a['dependency'])!=depkey(b['dependency']):return dict(status='BLOCKED',runs=runs,reason='NONREPRODUCIBLE_DEPENDENCY',full_boot=False)
    components={}
    for name in a['components']:
        values=[r['components'][name] for r in runs];states=[v['status'] for v in values]
        status='PASS' if states==['PASS','PASS'] else 'NOT_REACHED' if states==['NOT_REACHED','NOT_REACHED'] else 'BLOCKED' if 'BLOCKED' in states else 'PARTIAL'
        components[name]=cap(status,'BOTH_AUTHENTIC_RUNS_SCOPED',runs=values)
    return dict(status='PARTIAL',scope='BOUNDED_NATIVE_OBSERVATION_AND_INDEPENDENT_CAPABILITIES',components=components,runs=runs,
        reason='NO_FULL_BOOT_CLAIM',dependency=a['dependency'],first_unsupported_instruction=a['first_unsupported_instruction'],full_boot=False)
