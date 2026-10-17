#!/usr/bin/env python3
"""Independent verifier: no CPU execution or host mutation of observed RAM."""
import hashlib
import json
from pathlib import Path
import struct

PIN = 'c4e48388ca620472643110db2941ce70aa5f3c07'
SIZE = 4194304
MANIFEST = Path(__file__).with_name('d1_2_fixture_manifest.json')

class Blocked(Exception):
    pass

class Failed(Exception):
    pass

def require(condition, reason):
    if not condition:
        raise Failed(reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def initial_ram(case):
    result = bytearray(SIZE)
    result[0x10000:0x10010] = b'\xcc' * 16
    for address, value in ((0, 0x8000), (4, 0x4000), (12, 0x5000)):
        struct.pack_into('>I', result, address, value)
    code = bytes.fromhex(case['hex'])
    result[0x4000:0x4000 + len(code)] = code
    result[0x5000:0x5004] = bytes.fromhex('4e722700')
    return result

def check_run(directory, name, variant, repeat):
    directory = Path(directory)
    report = {'status': 'BLOCKED', 'case': name, 'variant': variant, 'run': repeat}
    try:
        manifest = json.loads(MANIFEST.read_text())
        case = manifest['cases'][name]
        observation = json.loads((directory / 'observation.json').read_text())
        if observation.get('reason', '').startswith('BLOCKED_BOOTSTRAP'):
            raise Blocked(observation['reason'])
        if observation.get('reason') != 'ENDPOINT_OBSERVED':
            raise Blocked(observation.get('reason', 'Missing endpoint observation'))
        require(observation['schema'] == 'dana-d1-2-observation-v1', 'Observation schema mismatch')
        require((observation['case'], observation['variant'], observation['run']) == (name, variant, repeat), 'Run identity mismatch')
        require(observation['fixture_sha256'] == case['sha256'] == sha(bytes.fromhex(case['hex'])), 'Fixture hash mismatch')
        runner = json.loads((directory / 'run.json').read_text())
        require(runner['binary_sha256'] == observation['binary_sha256'], 'Binary identity mismatch')
        require(runner['source_sha'] == observation['source_sha'], 'Source identity mismatch')
        if runner.get('reason')=='HOST_TIMEOUT':
            raise Blocked('HOST_TIMEOUT')
        require(runner['exit_code'] == 0, 'Emulator command failed')
        require(runner['mame_commit'] == PIN, 'Donor mismatch')
        if not observation['bootstrap_prepared']:
            raise Blocked('BLOCKED_BOOTSTRAP: preparation not observed')
        events, stops = observation['events'], observation['stops']
        if not isinstance(events, list) or not isinstance(stops, list) or not stops:
            raise Blocked('BLOCKED_BOOTSTRAP: missing first instruction evidence')
        require(len(events) <= 20000 and len(json.dumps(events).encode()) <= 5*1024*1024, 'Trace budget exceeded')
        require(0 <= observation['virtual_seconds'] <= 0.02 and len(stops) <= 32, 'Execution budget exceeded')
        require([e['seq'] for e in events] == list(range(len(events))), 'Trace sequence truncated')
        prestarts = [e for e in events if e['kind'] == 'prestart']
        preparations = [e for e in events if e['kind'] == 'prepared']
        require(len(prestarts) == len(preparations) == 1, 'Prestart/prepared event count mismatch')
        require(prestarts[0]['origin'] == preparations[0]['origin'] == 'fixture',
                'Bootstrap event origin mismatch')
        require(prestarts[0]['virtual_seconds'] == 0, 'Initial prestart not at virtual time zero')
        prepared = preparations[0]['seq']
        require(prestarts[0]['seq'] < prepared, 'Preparation order mismatch')
        cpu_events = [e for e in events if e['origin'] == 'cpu' and e['kind'] in ('read', 'write')]
        if not cpu_events or cpu_events[0]['seq'] <= prepared:
            raise Blocked('BLOCKED_BOOTSTRAP: native CPU activity after preparation not observed')
        # These four ordered, CPU-origin 16-bit bus reads are the native
        # M68000 reset SSP and PC fetches; unlike a Lua notifier they cannot
        # be inferred from host-seeded vectors or manufactured by this verifier.
        if len(cpu_events) < 4:
            raise Blocked('BLOCKED_BOOTSTRAP: incomplete native CPU reset vector fetches')
        vector_reads = cpu_events[:4]
        vector_words = ((0, 0x0000), (2, 0x8000), (4, 0x0000), (6, 0x4000))
        require(all(e['kind'] == 'read' and e['address'] == address
                    and e['data'] == value and e['mask'] == 0xffff
                    and e['pc'] == 0 for e, (address, value) in zip(vector_reads, vector_words)),
                'Native CPU reset vector read order/data mismatch')
        notifications = [e for e in events if e['kind'] == 'reset_notification']
        require(observation['reset_seen'] == bool(notifications),
                'Reset notifier flag contradicts actual event log')
        require(len(notifications) <= 1, 'Duplicate reset notification')
        if notifications:
            require(notifications[0]['origin'] == 'fixture'
                    and prepared < notifications[0]['seq'] < cpu_events[0]['seq'],
                    'Reset notification ordering/origin mismatch')
        first = stops[0]
        report['reset_evidence'] = {
            'basis': 'native_m68000_cpu_reset_vector_reads',
            'addresses': [e['address'] for e in vector_reads],
            'reset_notification_observed': bool(notifications)}

        require(first['CURPC'] == 0x4000 and first['SP'] == 0x8000 and first['SR'] == 0x2700, 'Initial PC/SSP/SR mismatch')
        require(all(first['D'+str(n)] == 0 for n in range(4)), 'Initial data registers not zero')
        expected_pcs = [i['pc'] for i in case['instructions']]
        if name in ('RAM-06','RAM-07'):
            expected_pcs = expected_pcs[:2] + [0x5000]
        require([s['CURPC'] for s in stops] == expected_pcs, 'Unexpected CPU instruction path')
        require(observation['final'] == stops[-1], 'Final snapshot mismatch')
        before = (directory / 'initial.ram').read_bytes()
        after = (directory / 'final.ram').read_bytes()
        require(len(before) == len(after) == SIZE, 'RAM dump extent mismatch')
        expected = initial_ram(case)
        require(before == expected, 'Fixture installation or initial guard mismatch')
        final = observation['final']
        expected_regs = [0,0,0,0]
        target, written = None, None
        if name == 'RAM-01':
            expected[0x10000:0x10010] = bytes.fromhex('cc a5 be ef 12 34 56 78 cc cc 89 ab cd ef cc cc')
            expected_regs = [0xa5,0xbeef,0x12345678,0x89abcdef]
            require(final['A0'] == 0x10000, 'A0 changed')
            for address in (0x10000,0x10002,0x10004,0x10006,0x1000a,0x1000c):
                require(any(e['kind']=='write' and e['address']==address for e in cpu_events), 'Missing CPU data write')
        elif name in ('RAM-02','RAM-03','RAM-04','RAM-05'):
            target, written, value = {
                'RAM-02': (0x80, bytes.fromhex('12345678'), 0x12345678),
                'RAM-03': (0x3ffffe, bytes.fromhex('beef'), 0xbeef),
                'RAM-04': (0x3ffffc, bytes.fromhex('12345678'), 0x12345678),
                'RAM-05': (0x3fffff, bytes.fromhex('a5'), 0xa5)}[name]
            expected[target:target+len(written)] = written
            expected_regs[0] = value
            for kind in ('read','write'):
                require(any(e['kind']==kind and e['address']==(target & ~1) for e in cpu_events), 'Missing CPU boundary/vector transfer')
        elif name in ('RAM-06','RAM-07'):
            require(final['CURPC']==0x5000 and final['SP']==0x7ff2, 'Address-error handler/frame missing')
            require(all(any(e['kind']=='read' and e['address']==a for e in cpu_events) for a in (12,14)), 'No actual vector 3 fetch')
            for address in range(0x7ff2, 0x8000, 2):
                require(any(e['kind']=='write' and e['address']==address for e in cpu_events), 'Missing CPU exception-frame write')
            frame=after[0x7ff2:0x8000]
            ssw, fault, ir, sr, pc = struct.unpack('>HIHHI', frame)
            opcode=int(case['instructions'][1]['hex'][:4],16)
            require(fault==0x10001 and ir==opcode and sr==0x2700, 'Fault address/IR/SR frame mismatch')
            require(case['instructions'][1]['pc']+2 <= pc <= case['stop_pc']+2 and pc%2==0, 'Unexpected pipeline exception PC')
            require(ssw & 0x17 == 0x15, 'Expected supervisor-data read special status word')
            report['exception_frame']={'ssw':ssw,'fault':fault,'ir':ir,'sr':sr,'pc':pc}
            expected[0x7ff2:0x8000]=frame
        elif name == 'RAM-08':
            for kind in ('read','write'):
                require(any(e['kind']==kind and e['address']==0x400000 for e in cpu_events), 'No actual unmapped access')
            require(final['A0']==0x400000, 'Unmapped target address mismatch')
            # Native unmapped value is evidence, not a manufactured bus error.
            expected_regs[0]=final['D0']; report['unmapped_read']=final['D0']
        require([final['D'+str(n)] for n in range(4)] == expected_regs, 'Data registers/high halves mismatch')
        if name not in ('RAM-06','RAM-07'):
            require(final['SP']==0x8000, 'Unexpected stack use/exception')
        require(after==expected, 'RAM corruption, alias, byte ordering or guard mismatch')
        normalized={'registers':final, 'ram_sha256':sha(after),
                    'cpu_bus':[{k:e[k] for k in ('kind','address','data','mask','pc')} for e in cpu_events],
                    'instruction_path':expected_pcs}
        report.update(status='PASS', normalized=normalized, binary_sha256=runner['binary_sha256'])
    except (FileNotFoundError, Blocked) as error:
        report['reason']=str(error)
    except Failed as error:
        report.update(status='FAIL', reason=str(error))
    except (ValueError, KeyError, TypeError, StopIteration, struct.error) as error:
        report['reason']='EVIDENCE_INVALID: '+str(error)
    return report

def verify_suite(root):
    root=Path(root); variant='diag'; cases={}
    for number in range(1,9):
        name=f'RAM-{number:02}'
        cases[name]=check_run(root/variant/name, name, variant, 1)
    repeat=check_run(root/variant/'RAM-09', 'RAM-01', variant, 2)
    if repeat['status']=='PASS' and cases['RAM-01']['status']=='PASS':
        repeat['status']='PASS' if repeat['normalized']==cases['RAM-01']['normalized'] else 'FAIL'
        if repeat['status']=='FAIL': repeat['reason']='Clean-run determinism mismatch'
    elif cases['RAM-01']['status']!='PASS':
        repeat.update(status='BLOCKED',reason='RAM-01 not qualified for comparison')
    cases['RAM-09']=repeat
    # RAM-10 stable/diag parity is deferred to stable activation (R3.4 owns
    # its final manifest/unit-test disposition). It is not counted as PASS.
    all_status=[r['status'] for r in cases.values()]
    status='FAIL' if 'FAIL' in all_status else 'BLOCKED' if 'BLOCKED' in all_status else 'PASS'
    return {'status':status,
            'scope':'Observed DIAG fixture assertions only; independent T qualification required',
            'variants':{variant:cases},
            # Deferred cases are never included in the status aggregation.
            'deferred_cases':{
                'RAM-10':{
                    'status':'DEFERRED_STABLE_PARITY',
                    'reason':'Stable/DIAG parity belongs to later stable activation',
                    'counts_for_pass':False}}}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('evidence',type=Path)
    args=parser.parse_args(); result=verify_suite(args.evidence)
    (args.evidence/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status']);raise SystemExit({'PASS':0,'FAIL':1,'BLOCKED':2}[result['status']])
