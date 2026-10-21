#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Offline preparation controls. Synthetic fixtures never repair real inputs."""
import hashlib
import json
import ast
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import dana_012e_prepare as prep
from dana_012e_offline import classification

PROJECT=Path(__file__).resolve().parents[1]


class HistoricalSource(unittest.TestCase):
    def test_real_historical_and_compiled_pins_are_available(self):
        report=prep.source_report(PROJECT)
        self.assertEqual(report['status'],'PASS',report)
        self.assertEqual([r['actual_sha256'] for r in report['pins']],
                         [prep.HISTORICAL_DRIVER_SHA,prep.DRIVER_SHA])

    def test_missing_historical_object_blocks_and_explicit_fetch_recovers(self):
        # No alternates, shared objects or parent history: reproduce the shallow job.
        with tempfile.TemporaryDirectory(prefix='012e-history-control-') as temp:
            path=Path(temp)
            def git(*args):return subprocess.run(['git','-C',str(path),*args],capture_output=True,text=True,check=True,timeout=60)
            git('init')
            source=subprocess.check_output(['git','-C',str(PROJECT),'rev-parse','HEAD'],text=True).strip()
            for pin in (source,prep.BUILD_SOURCE):git('fetch','--depth=1',PROJECT.as_uri(),pin)
            git('checkout','--detach',source)
            before=prep.source_report(path)
            self.assertEqual(before['status'],'BLOCKED')
            self.assertEqual(before['pins'][0]['status'],'BLOCKED')
            self.assertEqual(before['pins'][1]['status'],'PASS')
            git('fetch','--depth=1',PROJECT.as_uri(),prep.HISTORICAL_SOURCE)
            self.assertEqual(prep.source_report(path)['status'],'PASS')
            # Run the unchanged original seven-method equality assertions too.
            output=subprocess.run(['python3','-m','unittest',
                'd2_3_test.SourceContracts.test_preserved_qualified_portc_and_pllfsr_methods'],
                cwd=path/'tests',capture_output=True,text=True,timeout=60)
            self.assertEqual(output.returncode,0,output.stderr)

    def test_fetched_historical_driver_cannot_be_relabelled(self):
        with patch.object(prep,'HISTORICAL_DRIVER_SHA','0'*64):
            result=prep.source_report(PROJECT)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('PINNED_DRIVER_SHA256',result['pins'][0]['reason'])


class Procedure(unittest.TestCase):
    def test_missing_input_is_blocked_not_regression_fail_or_pass(self):
        good=SimpleNamespace(failures=[],errors=[],skipped=[])
        self.assertEqual(classification(dict(status='PASS'),good)[0],'PASS')
        self.assertEqual(classification(dict(status='BLOCKED'),good)[0],'BLOCKED')
        for name in ('test_actual_supplied_subset_when_available','test_preserved_qualified_portc_and_pllfsr_methods'):
            test=SimpleNamespace(id=lambda:'original.'+name)
            bad=SimpleNamespace(failures=[(test,'original assertion fails')],errors=[],skipped=[])
            blocked=dict(status='BLOCKED',selected_evidence=dict(status='BLOCKED'),source=dict(pins=[dict(status='BLOCKED')]))
            self.assertEqual(classification(blocked,bad)[0],'BLOCKED')
            self.assertEqual(classification(dict(status='PASS'),bad)[0],'FAIL')
        skipped=SimpleNamespace(failures=[],errors=[],skipped=[(self,'unavailable input')])
        self.assertEqual(classification(dict(status='PASS'),skipped)[0],'BLOCKED')

    def test_real_regression_is_fail_even_with_a_separate_input_block(self):
        bad=SimpleNamespace(failures=[(self,'unexpected control failure')],errors=[],skipped=[])
        self.assertEqual(classification(dict(status='BLOCKED'),bad)[0],'FAIL')

    def test_job_fetches_history_and_tests_same_selected_evidence_and_archive(self):
        text=(PROJECT/'tests/hold/012_e_dana_integrated_observation_diag.job.sh').read_text()
        code=text.split("<<'PY_JOB'\n",1)[1].rsplit('\nPY_JOB',1)[0];ast.parse(code)
        self.assertIn("HISTORICAL_SOURCE='"+prep.HISTORICAL_SOURCE+"'",code)
        self.assertIn("('historical-regression',HISTORICAL_SOURCE)",code)
        self.assertIn("'tests/dana_012e_offline.py','--evidence',str(PRIOR/'evidence')",code)
        self.assertIn("'--evidence-scope','full','--archive',str(ORIGINAL_ARCHIVE)",code)
        self.assertIn("if offline['status']!='PASS':raise",code)
        self.assertNotIn("'--evidence-scope','provided-subset'",code)

    def test_old_authorization_flags_never_launch_the_corrected_job(self):
        job=PROJECT/'tests/hold/012_e_dana_integrated_observation_diag.job.sh'
        env={k:v for k,v in os.environ.items() if not k.startswith('DANA_')}
        for flags in ({},{'DANA_012D_AUTHORIZED':'YES'},{'DANA_TIMER_UART_IRQ_AUTHORIZED':'YES'},
                      {'DANA_D2_3_AUTHORIZED':'YES','DANA_D2_3_BUILD_AUTHORIZED':'YES'}):
            run=subprocess.run(['bash',str(job)],env=dict(env,**flags),capture_output=True,text=True,timeout=5)
            self.assertEqual(run.returncode,2);self.assertTrue(run.stdout.startswith('HOLD:'));self.assertFalse(run.stderr)


class EvidenceSelection(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='012e-integrity-SYNTHETIC-');self.addCleanup(temp.cleanup)
        self.temp=Path(temp.name);self.root=self.temp/'evidence';self.root.mkdir()
        names=sorted(prep.SUBSET_MEMBERS)+['pfsel/reset/final.ram','pfsel/save_restore/final.ram','pfsel/save_restore/restored.ram']
        names += ['synthetic-control-'+str(i) for i in range(40-len(names))]
        self.index={}
        for name in names:
            content=('SYNTHETIC OFFLINE CONTROL ONLY: '+name).encode()
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
            self.index[name]=hashlib.sha256(content).hexdigest()
        self.index_bytes=json.dumps(self.index,sort_keys=True).encode()
        (self.root/prep.INDEX).write_bytes(self.index_bytes)
        # Only synthetic controls use a synthetic anchor. Real input pins stay fixed.
        mocked=patch.object(prep,'INDEX_SHA',hashlib.sha256(self.index_bytes).hexdigest());mocked.start();self.addCleanup(mocked.stop)
        self.snapshot=lambda:{str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_full_selection_is_explicit_and_read_only(self):
        before=self.snapshot();report=prep.audit_directory(self.root)
        self.assertEqual(report['status'],'PASS',report);self.assertEqual(before,self.snapshot())
        self.assertEqual(len(report['files']),40)
        self.assertEqual(report['selected_root'],str(self.root))

    def test_corrupt_each_disputed_ram_keeps_original_index_and_blocks(self):
        for name in ('pfsel/reset/final.ram','pfsel/save_restore/final.ram','pfsel/save_restore/restored.ram'):
            p=self.root/name;original=p.read_bytes();p.write_bytes(b'SYNTHETIC CORRUPTION')
            before=self.snapshot();report=prep.audit_directory(self.root)
            self.assertEqual(report['status'],'BLOCKED')
            row=next(e for e in report['files'] if e['relative_path']==name)
            self.assertEqual(row['expected_sha256'],self.index[name]);self.assertNotEqual(row['actual_sha256'],self.index[name])
            self.assertEqual(row['selected_path'],str(p));self.assertEqual(row['index'],str(self.root/prep.INDEX))
            self.assertEqual(row['origin'],'EXPLICIT_SELECTED_DIRECTORY')
            self.assertEqual(before,self.snapshot());self.assertEqual((self.root/prep.INDEX).read_bytes(),self.index_bytes)
            p.write_bytes(original)  # Restore only this synthetic test control.

    def test_original_integrity_assertion_keeps_hash_check_and_names_selection(self):
        from dana_012d_test import Provenance
        p=self.root/'pfsel/reset/final.ram';p.write_bytes(b'SYNTHETIC CORRUPTION')
        case=Provenance()
        with patch.dict(os.environ,DANA_012C_EVIDENCE_DIR=str(self.root)):
            with self.assertRaises(AssertionError) as error:case.test_actual_supplied_subset_when_available()
        message=str(error.exception)
        self.assertIn(str(p),message);self.assertIn(str(self.root/prep.INDEX),message)
        self.assertIn(prep.digest(p),message);self.assertIn(self.index['pfsel/reset/final.ram'],message)
        self.assertEqual((self.root/prep.INDEX).read_bytes(),self.index_bytes)

    def test_all_three_missing_ram_files_are_named_without_attributing_reported_hash(self):
        for name in prep.RAM_MEMBERS:(self.root/name).unlink()
        result=prep.preflight(PROJECT,self.root)
        self.assertEqual([e['relative_path'] for e in result['ram_comparison']],list(prep.RAM_MEMBERS))
        self.assertTrue(all(e['actual_sha256'] is None and e['status']=='BLOCKED' for e in result['ram_comparison']))
        self.assertTrue(all(e['assessment']=='BLOCKED_SELECTED_BYTES_UNAVAILABLE' for e in result['ram_comparison']))
        self.assertEqual(result['reported_discrepancy']['reported_actual_sha256'],prep.DISPUTED_ACTUAL)

    def test_a_good_alternate_directory_does_not_replace_bad_selection(self):
        good=prep.audit_directory(self.root);self.assertEqual(good['status'],'PASS')
        wrong=self.temp/'wrong';wrong.mkdir();(wrong/prep.INDEX).write_bytes(self.index_bytes)
        report=prep.audit_directory(wrong)
        self.assertEqual(report['status'],'BLOCKED');self.assertEqual(report['selected_root'],str(wrong))
        self.assertEqual(len(report['missing_required']),40)

    def test_full_selection_cannot_omit_ram_or_use_subset_scope(self):
        (self.root/'pfsel/reset/final.ram').unlink()
        self.assertEqual(prep.audit_directory(self.root)['status'],'BLOCKED')
        self.assertEqual(prep.audit_directory(self.root,'provided-subset')['status'],'BLOCKED')

    def test_original_seven_file_scope_is_explicit_and_never_full_pass(self):
        for name in self.index:
            if name not in prep.SUBSET_MEMBERS:(self.root/name).unlink()
        result=prep.audit_directory(self.root,'provided-subset')
        self.assertEqual(result['status'],'PASS');self.assertEqual(len(result['absent_indexed_members']),33)
        self.assertEqual(prep.audit_directory(self.root,'full')['status'],'BLOCKED')

    def test_reindexing_corrupt_content_is_rejected_by_original_anchor(self):
        p=self.root/'pfsel/reset/final.ram';p.write_bytes(b'SYNTHETIC CORRUPTION')
        changed=dict(self.index);changed['pfsel/reset/final.ram']=prep.digest(p)
        (self.root/prep.INDEX).write_text(json.dumps(changed,sort_keys=True))
        self.assertIn('ORIGINAL_INDEX_SHA256',prep.audit_directory(self.root)['errors'])
        report=prep.preflight(PROJECT,self.root)
        row=next(e for e in report['ram_comparison'] if e['relative_path']=='pfsel/reset/final.ram')
        self.assertEqual(row['actual_sha256'],prep.digest(p))
        self.assertFalse(row['selection_index_verified'])
        self.assertIn('WRONG_DIRECTORY_OR_INDEX_UNRESOLVED',row['assessment'])

    def test_symlink_extra_file_and_duplicate_index_are_blocked(self):
        p=self.root/'pfsel/reset/final.ram';p.unlink();p.symlink_to(self.root/'binary_qualification.json')
        self.assertIn('SYMLINK_OR_SPECIAL_EVIDENCE',prep.audit_directory(self.root)['errors'])
        p.unlink();p.write_text('synthetic');(self.root/'unindexed').write_text('synthetic')
        self.assertIn('unindexed',prep.audit_directory(self.root)['unexpected'])
        with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON_KEY'):json.loads('{"x":1,"x":2}',object_pairs_hook=prep.unique_object)

    def archive(self):
        path=self.temp/'SYNTHETIC_CONTROL.tar.gz'
        with tarfile.open(path,'w:gz') as tar:tar.add(self.root,arcname='evidence')
        return path

    def test_archive_and_selected_directory_must_both_pass(self):
        archive=self.archive()
        with patch.object(prep,'ARCHIVE_SHA',prep.digest(archive)):
            self.assertEqual(prep.audit_archive(archive)['status'],'PASS')
            (self.root/'pfsel/reset/final.ram').write_bytes(b'SYNTHETIC CORRUPTION')
            report=prep.preflight(PROJECT,self.root,archive=archive)
            self.assertEqual(report['archive']['status'],'PASS')
            self.assertEqual(report['selected_evidence']['status'],'BLOCKED')
            self.assertEqual(report['status'],'BLOCKED')
            ram=next(e for e in report['ram_comparison'] if e['relative_path']=='pfsel/reset/final.ram')
            self.assertIn('ALTERATION_OR_WRONG_SELECTION_UNRESOLVED',ram['assessment'])

    def test_archive_byte_corruption_is_not_repaired(self):
        archive=self.archive();expected=prep.digest(archive)
        archive.write_bytes(archive.read_bytes()+b'SYNTHETIC CORRUPTION');before=archive.read_bytes()
        with patch.object(prep,'ARCHIVE_SHA',expected):result=prep.audit_archive(archive)
        self.assertEqual(result['status'],'BLOCKED');self.assertIn('ORIGINAL_ARCHIVE_SHA256',result['errors'])
        self.assertEqual(archive.read_bytes(),before)

    def test_repacked_corrupt_member_still_fails_its_unchanged_index(self):
        (self.root/'pfsel/reset/final.ram').write_bytes(b'SYNTHETIC CORRUPTION');archive=self.archive()
        with patch.object(prep,'ARCHIVE_SHA',prep.digest(archive)):result=prep.audit_archive(archive)
        self.assertEqual(result['status'],'BLOCKED');self.assertIn('ARCHIVE_MEMBER_SHA256:pfsel/reset/final.ram',result['errors'])

    def test_full_preparation_requires_original_archive_even_with_good_directory(self):
        result=prep.preflight(PROJECT,self.root)
        self.assertEqual(result['selected_evidence']['status'],'PASS');self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('ORIGINAL_ARCHIVE_REQUIRED_FOR_FULL_PREPARATION',result['archive']['errors'])


if __name__=='__main__':unittest.main()
