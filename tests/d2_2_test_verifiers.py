#!/usr/bin/env python3
"""Adversarial verifier tests. ALL records in this file are synthetic, not runtime evidence."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from d2_2_gpio_run import fixture, verify, diag_path
from d2_2_qualify import assess


def guest_observation():
    events=[]
    for address,mask,pc in ((0xfffff412,0xff,0x1000), (0xfffff412,0xff00,0x1008),
                            (0xfffff42a,0xff,0x1010)):
        selected=[address+(mask==0xff)]
        events.append(dict(kind='write' if pc!=0x1010 else 'read',address=address,mask=mask,
                           data=0,origin='cpu',state={'CURPC':pc},byte_addresses=selected,width_bits=8))
    dep={k:events[-1][k] for k in ('address','kind','data','mask','state','byte_addresses','width_bits')}
    dep['effective_address']=0xfffff42b
    return dict(reason='BLOCKED_HARDWARE',events=events,dependency=dep)


class GuestVerifier(unittest.TestCase):
    def test_valid_synthetic_lane_observation(self):
        obs=guest_observation()
        self.assertEqual(assess([obs,copy.deepcopy(obs)])['status'],'PASS')

    def test_low_lane_never_counts_as_pcpden(self):
        obs=guest_observation();obs['events'].pop(1)
        with self.assertRaisesRegex(ValueError,'fffff412'):
            assess([obs,copy.deepcopy(obs)])

    def test_host_fake_origin_and_wrong_effective_address_rejected(self):
        for mutate in (lambda o:o['events'][0].update(origin='host'),
                       lambda o:o['dependency'].update(effective_address=0xfffff42a),
                       lambda o:o['events'][0].update(byte_addresses=[0xfffff412]),
                       lambda o:o['events'][0].update(width_bits=16),
                       lambda o:o.update(reason='BLOCKED_TRACE_BUDGET')):
            obs=guest_observation();mutate(obs)
            with self.assertRaises(ValueError):assess([obs,copy.deepcopy(obs)])

    def test_first_missing_byte_cannot_be_skipped(self):
        obs=guest_observation()
        e=copy.deepcopy(obs['events'][0]);e.update(address=0xfffff300,mask=0xff,
                                                byte_addresses=[0xfffff301])
        obs['events'].insert(0,e)
        with self.assertRaises(ValueError):assess([obs,copy.deepcopy(obs)])

    def test_nonrepeatable_and_single_execution_rejected(self):
        a=guest_observation();b=copy.deepcopy(a);b['events'][0]['state']['CURPC']+=2
        with self.assertRaisesRegex(ValueError,'Non-repeatable'):assess([a,b])
        with self.assertRaises(ValueError):assess([a])


class NativeVerifier(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory(prefix='portc-synthetic-verifier-')
        self.addCleanup(td.cleanup);self.root=Path(td.name)
        payload,endpoint=fixture()
        ram=bytearray(0x400000);ram[:8]=struct.pack('>II',0x8000,0x4000)
        ram[0x4000:0x4000+len(payload)]=payload;ram[0x10010:0x10012]=bytes.fromhex('cafe')
        (self.root/'initial.ram').write_bytes(ram)
        ram[0x10000:0x1000a]=bytes.fromhex('55aa1234fe34fe81fe81')
        (self.root/'final.ram').write_bytes(ram)
        (self.root/'cpu.trace').write_text(f'4000: synthetic\n{endpoint-6:x}: synthetic\n')
        events=[dict(origin='cpu',kind='read',address=a,data=d,mask=0xffff)
                for a,d in ((0,0),(2,0x8000),(4,0),(6,0x4000))]
        for address,mask,data in ((0xfffff412,0xff00,0x5500),(0xfffff412,0xff,0xaa),
                (0xfffff412,0xffff,0x1234),(0xfffff412,0xff00,0xfe00),(0xfffff412,0xff,0x81),
                (0xfff412,0xff00,0),(0xfff412,0xff,0),(0xfffff410,0xff00,0),
                (0xfffff410,0xff,0),(0xfffff414,0xff00,0)):
            events.append(dict(origin='cpu',kind='write',address=address,mask=mask,data=data))
        for kind,value in (('profile_initial',0),('fixture_complete',0xfe81),
                           ('state_restored',0xfe81),('profile_reset',0)):
            events.append(dict(origin='host_observation',kind=kind,value=value,
                               pc=endpoint,sp=0x8000,sr=0x2700))
        self.obs=dict(status='PASS',reason='SYNTHETIC UNIT RECORD',events=events,
                      fixture_sha256=hashlib.sha256(payload).hexdigest(),binary_sha256='unit-only')
        (self.root/'run.json').write_text(json.dumps(dict(exit_code=0,binary_sha256='unit-only')))
        self.write()

    def write(self):
        (self.root/'observation.json').write_text(json.dumps(self.obs))

    def test_complete_synthetic_fixture_accepted_by_verifier(self):
        self.assertEqual(verify(self.root)['status'],'PASS')

    def test_unrelated_ram_corruption_is_product_fail(self):
        data=bytearray((self.root/'final.ram').read_bytes());data[0x20000]^=1
        (self.root/'final.ram').write_bytes(data)
        self.assertEqual(verify(self.root)['status'],'FAIL')

    def test_missing_native_lane_or_alias_control_rejected(self):
        self.obs['events']=[e for e in self.obs['events'] if e.get('address')!=0xfff412]
        self.write();self.assertEqual(verify(self.root)['status'],'FAIL')

    def test_host_activity_cannot_replace_native_cpu_write(self):
        self.obs['events'][4]['origin']='host'
        self.write();self.assertEqual(verify(self.root)['status'],'FAIL')

    def test_wrong_native_save_restore_rejected(self):
        next(e for e in self.obs['events'] if e['kind']=='state_restored')['value']=0
        self.write();self.assertEqual(verify(self.root)['status'],'FAIL')

    def test_zero_exit_without_observation_is_blocked(self):
        (self.root/'observation.json').unlink()
        self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_other_emulator_path_is_blocked_before_invocation(self):
        with self.assertRaisesRegex(ValueError,'STAGING_PATH'):
            diag_path('/usr/bin/mame')


if __name__=='__main__':unittest.main(verbosity=2)
