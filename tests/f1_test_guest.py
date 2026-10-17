#!/usr/bin/env python3
"""Loader/input/observation negative tests; fixtures here are NOT EmuTOS builds."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'tools'))
from f1_guest import package,validate,symbols,sha,HEADER,PIN
from f1_emutos_run import verify

class Inputs(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='dana-f1-input-test-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.syms={'__text':0x2140,'_os_header':0x2140,'_main':0x2150,'_stktop':0x1000,
                   '__low_stram_end':0x2140,'__bss':0x2180,'__ebss':0x3000}
        self.image=bytearray(64);self.image[:2]=bytes.fromhex('600e')
        self.image[16:20]=bytes.fromhex('6000000e')
        (self.root/'emutos.img').write_bytes(self.image)
        (self.root/'emutos-dana.rom').write_bytes(b'test-only booter'+self.image)
        self.write_map();self.manifest=package(self.root,source_sha=PIN,compiler='SYNTHETIC UNIT FIXTURE ONLY')
    def write_map(self):
        (self.root/'emutos.map').write_text('\n'.join(f' 0x{v:08x} {k}' for k,v in self.syms.items()))
    def test_valid_synthetic_envelope(self):
        m=validate(self.root);self.assertEqual(m['symbols']['_realmain'],0x2160)
        self.assertEqual((self.root/'emutos.dana').read_bytes()[64:],self.image)
    def test_manual_packaging_requires_build_provenance(self):
        with self.assertRaises(FileNotFoundError):package(self.root)
    def test_corrupt_image(self):
        (self.root/'emutos.img').write_bytes(b'wrong')
        with self.assertRaises(ValueError):validate(self.root)
    def test_corrupt_package(self):
        data=bytearray((self.root/'emutos.dana').read_bytes());data[-1]^=1
        (self.root/'emutos.dana').write_bytes(data)
        with self.assertRaises(ValueError):validate(self.root)
    def test_corrupt_map(self):
        self.syms['_stktop']=0x400000;self.write_map()
        with self.assertRaises(ValueError):validate(self.root)
    def test_stack_overlap_rejected(self):
        self.syms['_stktop']=0x2142;self.write_map()
        with self.assertRaises(ValueError):package(self.root,source_sha=PIN)
    def test_out_of_ram_bss(self):
        self.syms['__ebss']=0x400001;self.write_map()
        with self.assertRaises(ValueError):package(self.root,source_sha=PIN)
    def test_wrong_entry(self):
        self.syms['_os_header']=0x2142;self.write_map()
        with self.assertRaises(ValueError):package(self.root,source_sha=PIN)
    def test_mismatched_rom(self):
        (self.root/'emutos-dana.rom').write_bytes(b'not the image')
        with self.assertRaises(ValueError):package(self.root,source_sha=PIN)
    def test_wrong_pin(self):
        with self.assertRaises(ValueError):package(self.root,source_sha='HEAD')
    def test_missing_or_ambiguous_map(self):
        with self.assertRaises(ValueError):symbols('0x2140 __text\n0x2150 __text')
    def test_bad_startup_branch(self):
        self.image[:2]=bytes.fromhex('600c');(self.root/'emutos.img').write_bytes(self.image)
        with self.assertRaises(ValueError):package(self.root,source_sha=PIN)
    def test_missing_observation_is_blocked(self):
        result=verify(self.root/'unrun',self.root)
        self.assertEqual(result['status'],'BLOCKED')
    def test_zero_exit_cannot_prove_cpu_execution(self):
        run=self.root/'run';run.mkdir()
        (run/'run.json').write_text(json.dumps({'exit_code':0,'binary_sha256':'test'}))
        (run/'observation.json').write_text(json.dumps({'first_instruction':False,
                'package_sha256':self.manifest['package']['sha256'],'binary_sha256':'test'}))
        result=verify(run,self.root)
        self.assertEqual((result['status'],result['reason']),('BLOCKED','BLOCKED_BOOTSTRAP'))

if __name__=='__main__':unittest.main()
