#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Integrated source regressions; original evidence is read-only and independent."""
import argparse
import json
import os
from pathlib import Path
import unittest
from dana_012e_offline import TEST_MODULES
import dana_012e_prepare as prep


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.resolve().is_relative_to(args.evidence.resolve()):parser.error('Output inside original evidence')
    os.environ['DANA_012C_EVIDENCE_DIR']=str(args.evidence.absolute())
    before=prep.audit_directory(args.evidence)
    # Preserve the exact selection in a NEW private file; never repair or swap it.
    retained=prep.preserve_selection(args.evidence,args.output.with_suffix('.selection-before.tar'),before)
    suite=unittest.defaultTestLoader.loadTestsFromNames((*TEST_MODULES,'dana_hardware_test'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    after=prep.audit_directory(args.evidence)
    problems=[dict(test=t.id(),detail=detail) for t,detail in result.failures+result.errors]
    input_problems=[p for p in problems if p['test'].endswith('.test_actual_supplied_subset_when_available') and before['status']=='BLOCKED']
    regressions=[p for p in problems if p not in input_problems]
    status='FAIL' if regressions else 'BLOCKED' if problems or result.skipped else 'PASS'
    if before!=after or retained['status']!='PRESERVED':status='FAIL' if regressions else 'BLOCKED'
    report=dict(status=status,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        skips=len(result.skipped),problems=problems,source_regressions=len(regressions),original_input_problems=input_problems,
        selected_evidence_before=before,selected_evidence_after=after,selection_preserved=retained,
        original_archive_integrity='ACCREDITED_USER_REVIEW_NOT_REHASHED_HERE',
        emulator_executions=0,MAME_builds=0,ROM_builds=0,native_status='NATIVE_PENDING',full_boot=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','tests_run','failures','errors','skips','source_regressions','native_status')},indent=2))
    return 1 if status=='FAIL' else 2 if status=='BLOCKED' else 0

if __name__=='__main__':raise SystemExit(main())
