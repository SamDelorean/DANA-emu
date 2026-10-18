#!/usr/bin/env python3
"""Independent lane-aware checks of fresh F1 evidence for the Port C continuation."""
import argparse
import json
from pathlib import Path
import sys

from f1_emutos_run import verify


def selected_bytes(event):
    address, mask = event['address'], event['mask']
    if address % 2 or mask not in (0xff00,0x00ff,0xffff):
        raise ValueError('Unsupported M68000 bus shape')
    return [address+i for i, lane in enumerate((0xff00,0x00ff)) if mask & lane]


def supported(address, kind):
    return (0xfffff202<=address<=0xfffff203 or address==0xfffff300 or
            0xfffff302<=address<=0xfffff307 or 0xfffff30c<=address<=0xfffff30f or
            (kind=='read' and 0xfffff310<=address<=0xfffff313) or
            address in (0xfffff412,0xfffff413))


def assess(observations):
    """No PASS from counters, a zero process exit or an uncorroborated dependency."""
    if len(observations)!=2:
        raise ValueError('Two actual observations required')
    normalized, dependencies = [], []
    counts = []
    for obs in observations:
        if obs.get('reason')!='BLOCKED_HARDWARE':
            raise ValueError('Next real unsupported hardware transaction required')
        writes = {0xfffff412:[],0xfffff413:[]}
        first_missing = None
        bus = []
        for event in obs['events']:
            if event['kind'] not in ('read','write'):
                continue
            if event.get('origin')!='cpu':
                raise ValueError('Non-CPU bus evidence')
            selected = selected_bytes(event)
            if event.get('byte_addresses')!=selected or event.get('width_bits')!=len(selected)*8:
                raise ValueError('Missing/mismatched effective byte-lane evidence')
            for address in selected:
                if address>=0x400000 and not supported(address,event['kind']):
                    if first_missing is None:
                        first_missing = (event,address)
                if event['kind']=='write' and address in writes:
                    byte = (event['data'] >> (8 if address%2==0 else 0)) & 255
                    writes[address].append((byte,event['state']['CURPC']))
            bus.append({k:event[k] for k in ('kind','address','data','mask','state')})
        # Guest source has explicit byte writes of zero to BOTH registers.
        for address, seen in writes.items():
            if not any(byte==0 for byte,pc in seen):
                raise ValueError(f'No actual guest zero write to {address:08x}')
        dep = obs.get('dependency')
        if first_missing is None or not dep:
            raise ValueError('Missing next hardware evidence')
        event, address = first_missing
        if address<0xfffff000 or address in (0xfffff412,0xfffff413):
            raise ValueError('Guest did not advance to the next VZ dependency')
        if dep.get('effective_address')!=address or any(dep.get(k)!=event[k] for k in
                ('address','kind','data','mask','state','byte_addresses','width_bits')):
            raise ValueError('Dependency does not match first actual unsupported byte')
        # No continued trace after the stop dependency; a skipped device is a defect.
        if bus[-1] != {k:event[k] for k in ('kind','address','data','mask','state')}:
            raise ValueError('Guest observer continued after missing hardware')
        dependencies.append(dep)
        counts.append({f'{a:08x}':len(v) for a,v in writes.items()})
        normalized.append(bus)
    if normalized[0]!=normalized[1] or dependencies[0]!=dependencies[1]:
        raise ValueError('Non-repeatable CPU/bus hardware continuation')
    return {'status':'PASS','scope':'Authentic CPU-origin Port C continuation only',
            'next_dependencies':dependencies,'zero_write_counts':counts,
            'manufacturer_reset':'MOTOROLA_0xFF_PHYSICAL_R_DIRECT_0x00_SOFTWARE',
            'manufacturer_source':'MC68VZ328UM_D_10.4.3.4-10.4.3.5_TABLES_10-15_10-16'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',type=Path);p.add_argument('guest',type=Path)
    args=p.parse_args()
    try:
        result=json.loads((args.evidence/'result.json').read_text())
        if result.get('status')=='FAIL' or result.get('repeat')=='FAIL' or result.get('native_rejection',{}).get('status')=='FAIL':
            raise ValueError('Original F1 verification/repeat/native negative did not pass')
        if result.get('repeat')!='PASS' or result.get('native_rejection',{}).get('status')!='PASS':
            raise RuntimeError('BLOCKED_F1_REPEAT_OR_NATIVE_REJECTION_UNPROVED')
        for run in ('run-1','run-2'):
            validated=verify(args.evidence/run,args.guest)
            if validated.get('status')=='FAIL':
                raise ValueError('Independent F1 verifier found invalid evidence')
            if validated.get('domain')!='HARDWARE' or validated.get('guest_execution',{}).get('status')!='PASS':
                raise RuntimeError('BLOCKED_REAL_GUEST_EXECUTION_UNPROVED')
        verdict=assess([json.loads((args.evidence/run/'observation.json').read_text())
                        for run in ('run-1','run-2')])
    except (FileNotFoundError,RuntimeError) as exc:
        verdict={'status':'BLOCKED','reason':str(exc)}
    except (OSError,ValueError,KeyError,TypeError) as exc:
        verdict={'status':'FAIL','reason':str(exc)}
    (args.evidence/'portc_result.json').write_text(json.dumps(verdict,indent=2)+'\n')
    print(json.dumps(verdict,indent=2))
    return {'PASS':0,'FAIL':1,'BLOCKED':2}[verdict['status']]


if __name__=='__main__':
    sys.exit(main())
