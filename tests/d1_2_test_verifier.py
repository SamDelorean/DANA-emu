#!/usr/bin/env python3
"""Verifier unit tests with synthetic evidence; never emulator qualification."""
import copy
import json
from pathlib import Path
import tempfile
import struct
from unittest.mock import patch
import unittest

from d1_2_verify import check_run, initial_ram, MANIFEST, PIN, verify_suite

class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='dana-d1-2-verifier-')
        self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)
        self.case=json.loads(MANIFEST.read_text())['cases']['RAM-01']
        path=[i['pc'] for i in self.case['instructions']]
        state={'CURPC':0x4000,'PC':0x4002,'SP':0x8000,'SR':0x2700,'IR':0x207c,
               'D0':0,'D1':0,'D2':0,'D3':0,'A0':0}
        stops=[dict(state,CURPC=pc,PC=pc+2) for pc in path]
        stops[-1].update(D0=0xa5,D1=0xbeef,D2=0x12345678,D3=0x89abcdef,A0=0x10000)
        events=[{'seq':0,'kind':'prestart','origin':'fixture','virtual_seconds':0},
                {'seq':1,'kind':'prepared','origin':'fixture'},
                {'seq':2,'kind':'reset_notification','origin':'fixture'}]
        for address in (0,2,4,6):
            events.append({'seq':len(events),'kind':'read','address':address,'origin':'cpu','pc':0,'data':0,'mask':65535})
        for address in (0x10000,0x10002,0x10004,0x10006,0x1000a,0x1000c):
            events.append({'seq':len(events),'kind':'write','address':address,'origin':'cpu','pc':0x4006,'data':0,'mask':65535})
        self.observation={'schema':'dana-d1-2-observation-v1','case':'RAM-01','variant':'stable','run':1,
            'fixture_sha256':self.case['sha256'],'binary_sha256':'test-only-mock','source_sha':'test-only-mock',
            'reason':'ENDPOINT_OBSERVED','bootstrap_prepared':True,'reset_seen':True,
            'events':events,'stops':stops,'final':stops[-1],'virtual_seconds':0.001}
        before=initial_ram(self.case);after=bytearray(before)
        after[0x10000:0x10010]=bytes.fromhex('cc a5 be ef 12 34 56 78 cc cc 89 ab cd ef cc cc')
        (self.root/'initial.ram').write_bytes(before);(self.root/'final.ram').write_bytes(after)
        (self.root/'run.json').write_text(json.dumps({'exit_code':0,'mame_commit':PIN,
                'binary_sha256':'test-only-mock','source_sha':'test-only-mock'}))
        self.write()

    def write(self):
        (self.root/'observation.json').write_text(json.dumps(self.observation))

    def check(self):
        self.write();return check_run(self.root,'RAM-01','stable',1)

    def test_control_fixture_only(self):
        self.assertEqual(self.check()['status'],'PASS')

    def test_missing_observation(self):
        (self.root/'observation.json').unlink()
        self.assertEqual(check_run(self.root,'RAM-01','stable',1)['status'],'BLOCKED')

    def test_unproved_bootstrap(self):
        self.observation['bootstrap_prepared']=False
        self.assertEqual(self.check()['status'],'BLOCKED')

    def test_cpu_before_preparation(self):
        self.observation['events'][0]['kind']='prepared'
        self.observation['events'][1]['kind']='prestart'
        self.observation['events'][1]['virtual_seconds']=0
        self.observation['events'][2]['seq']=8
        self.assertEqual(self.check()['status'],'FAIL')

    def test_fixture_hash(self):
        self.observation['fixture_sha256']='bad'
        self.assertEqual(self.check()['status'],'FAIL')

    def test_host_write_is_not_cpu_write(self):
        for e in self.observation['events']:
            if e['kind']=='write':e['origin']='fixture'
        self.assertEqual(self.check()['status'],'FAIL')

    def test_guard_corruption(self):
        data=bytearray((self.root/'final.ram').read_bytes());data[0x10008]=0
        (self.root/'final.ram').write_bytes(data)
        self.assertEqual(self.check()['status'],'FAIL')

    def test_upper_register_half(self):
        self.observation['final']['D0']=0xffff00a5
        self.assertEqual(self.check()['status'],'FAIL')

    def test_zero_exit_without_assertions(self):
        self.observation['stops']=[]
        self.assertEqual(self.check()['status'],'BLOCKED')

    def exception_fixture(self, name='RAM-06'):
        case=json.loads(MANIFEST.read_text())['cases'][name]
        before=initial_ram(case);after=bytearray(before)
        opcode=int(case['instructions'][1]['hex'][:4],16)
        after[0x7ff2:0x8000]=struct.pack('>HIHHI',0x15,0x10001,opcode,0x2700,case['stop_pc'])
        first=copy.deepcopy(self.observation['stops'][0])
        second=dict(first,CURPC=0x4006,PC=0x4008,A0=0x10000)
        final=dict(second,CURPC=0x5000,PC=0x5002,SP=0x7ff2)
        self.observation.update(case=name,fixture_sha256=case['sha256'],stops=[first,second,final],final=final)
        events=self.observation['events'][:7]
        for address in (12,14):
            events.append({'seq':len(events),'kind':'read','address':address,'origin':'cpu','pc':0x4006,'data':0,'mask':65535})
        for address in range(0x7ff2,0x8000,2):
            events.append({'seq':len(events),'kind':'write','address':address,'origin':'cpu','pc':0x4006,'data':0,'mask':65535})
        self.observation['events']=events
        (self.root/'initial.ram').write_bytes(before);(self.root/'final.ram').write_bytes(after)
        self.write()
        return check_run(self.root,name,'stable',1)

    def test_exception_control_fixtures_only(self):
        for name in ('RAM-06','RAM-07'):
            with self.subTest(name=name):
                self.assertEqual(self.exception_fixture(name)['status'],'PASS')

    def test_missing_real_vector3_read(self):
        self.exception_fixture()
        for event in self.observation['events']:
            if event.get('address')==12:event['origin']='fixture'
        self.write()
        self.assertEqual(check_run(self.root,'RAM-06','stable',1)['status'],'FAIL')

    def test_wrong_exception_frame(self):
        self.exception_fixture()
        data=bytearray((self.root/'final.ram').read_bytes());data[0x7ff7]=2
        (self.root/'final.ram').write_bytes(data)
        self.assertEqual(check_run(self.root,'RAM-06','stable',1)['status'],'FAIL')

    def test_variant_parity_mismatch(self):
        def mocked(directory,name,variant,repeat):
            return {'status':'PASS','normalized':{'D0':1 if variant=='diag' else 0}}
        with patch('d1_2_verify.check_run',side_effect=mocked):
            result=verify_suite(self.root)
        self.assertEqual(result['status'],'FAIL')
        self.assertTrue(all(v['RAM-10']['status']=='FAIL' for v in result['variants'].values()))

    def test_clean_repeat_mismatch(self):
        def mocked(directory,name,variant,repeat):
            return {'status':'PASS','normalized':{'D0':repeat}}
        with patch('d1_2_verify.check_run',side_effect=mocked):
            result=verify_suite(self.root)
        self.assertEqual(result['status'],'FAIL')
        self.assertTrue(all(v['RAM-09']['status']=='FAIL' for v in result['variants'].values()))

    def test_incomplete_suite(self):
        result=verify_suite(self.root)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertTrue(all(len(cases)==10 for cases in result['variants'].values()))

if __name__=='__main__':
    unittest.main()
