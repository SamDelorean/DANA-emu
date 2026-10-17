#!/usr/bin/env python3
"""Synthetic MMIO-01 verifier tests only; fabricated observations are NEVER guest qualification."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from d1_3_1_mmio01_verify import verify, PCS, IVR, NONPAGE, ODD_NEIGHBOR
from d1_2_verify import PIN, SIZE


class MMIO01VerifierTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='dana-mmio01-synthetic-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.fixture = bytes([0x4e]) * 30  # deliberately NOT an executable guest fixture
        self.binary_hash = 'synthetic-only-not-a-real-binary'
        state = dict(CURPC=PCS[0], SP=0x8000, SR=0x2700, D0=0, A0=0)
        self.stops = [dict(state, CURPC=pc) for pc in PCS]
        self.stops[3]['A0'] = IVR
        self.stops[3]['D0'] = 0x40
        self.stops[4]['A0'] = NONPAGE
        self.stops[6]['A0'] = ODD_NEIGHBOR
        self.stops[-1]['A0'] = ODD_NEIGHBOR
        self.events = [
            {'seq':0, 'kind':'prestart', 'origin':'fixture'},
            {'seq':1, 'kind':'prepared', 'origin':'fixture'}]
        def bus(kind, address, data, mask):
            self.events.append(dict(seq=len(self.events),kind=kind,origin='cpu',
                                    address=address,data=data,mask=mask,pc=0))
        for address, data in ((0,0),(2,0x8000),(4,0),(6,0x4000)):
            bus('read', address, data, 0xffff)
        bus('write',IVR,0x4000,0xff00)
        bus('read',IVR,0x4000,0xff00)
        bus('read',NONPAGE,0xffff,0xff00)
        bus('read',IVR,0xffff,0x00ff)
        self.obs = dict(schema='dana-d1-3-mmio01-observation-v1',
                        case='MMIO-01',variant='diag',run=1,reason='ENDPOINT_OBSERVED',
                        bootstrap_prepared=True,source_sha='synthetic-revision',
                        binary_sha256=self.binary_hash,
                        fixture_sha256=hashlib.sha256(self.fixture).hexdigest(),
                        events=self.events,stops=self.stops,final=self.stops[-1])
        self.run = dict(mame_commit=PIN,exit_code=0,source_sha='synthetic-revision',
                        binary_sha256=self.binary_hash,
                        fixture_sha256=self.obs['fixture_sha256'])
        ram = bytearray(SIZE)
        ram[0x10000:0x10010] = bytes([0xcc])*16
        for address,value in ((0,0x8000),(4,0x4000),(12,0x5000)):
            struct.pack_into('>I',ram,address,value)
        ram[0x4000:0x401e] = self.fixture
        ram[0x5000:0x5004] = bytes.fromhex('4e722700')
        (self.root/'initial.ram').write_bytes(ram)
        (self.root/'final.ram').write_bytes(ram)
        (self.root/'fixture.bin').write_bytes(self.fixture)
        (self.root/'error.log').write_text('DANA_VZ_IVR_WRITE data=40 state=40\n'
                                           'DANA_VZ_IVR_READ state=40\n')
        self.save()

    def save(self):
        (self.root/'observation.json').write_text(json.dumps(self.obs))
        (self.root/'run.json').write_text(json.dumps(self.run))

    def checked(self):
        self.save()
        return verify(self.root)

    def test_synthetic_contract_accepts_consistent_observation(self):
        self.assertEqual(self.checked()['status'],'PASS')

    def test_missing_guest_observation_blocks(self):
        (self.root/'observation.json').unlink()
        self.assertEqual(verify(self.root)['status'],'BLOCKED')

    def test_false_24_bit_low_alias_fails(self):
        self.events[6]['address'] = IVR & 0xffffff
        self.assertEqual(self.checked()['status'],'FAIL')

    def test_undecoded_other_page_fails(self):
        self.events[8]['address'] = NONPAGE & 0xffffff
        self.assertEqual(self.checked()['status'],'FAIL')

    def test_wrong_byte_lane_fails(self):
        self.events[6]['mask'] = 0x00ff
        self.assertEqual(self.checked()['status'],'FAIL')

    def test_host_bus_provenance_fails(self):
        self.events[6]['origin'] = 'host'
        self.assertEqual(self.checked()['status'],'FAIL')

    def test_wrong_guest_readback_fails(self):
        self.stops[3]['D0'] = 0x41
        self.assertEqual(self.checked()['status'],'FAIL')

    def test_spurious_handler_dispatch_fails(self):
        with (self.root/'error.log').open('a') as fd:
            fd.write('DANA_VZ_IVR_READ state=40\n')
        self.assertEqual(self.checked()['status'],'FAIL')

    def test_invalid_register_mask_readback_fails(self):
        (self.root/'error.log').write_text('DANA_VZ_IVR_WRITE data=40 state=41\n'
                                           'DANA_VZ_IVR_READ state=40\n')
        self.assertEqual(self.checked()['status'],'FAIL')

    def test_ram_alias_corruption_fails(self):
        ram = bytearray((self.root/'final.ram').read_bytes())
        ram[0x10002] = 0x55
        (self.root/'final.ram').write_bytes(ram)
        self.assertEqual(self.checked()['status'],'FAIL')

    def test_source_binary_identity_fails(self):
        self.run['binary_sha256']='wrong-binary'
        self.assertEqual(self.checked()['status'],'FAIL')


if __name__ == '__main__':
    unittest.main()
