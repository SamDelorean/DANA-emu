#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Complete offline battery plus explicit, read-only 012-E prerequisite audit."""
import argparse
import json
import os
from pathlib import Path
import unittest

from dana_012e_prepare import preflight,preserve_selection

TEST_MODULES=('dana_012e_prepare_test','dana_012e_test','dana_012d_test','f1_test_guest',
    'd2_3_test.SourceContracts','d2_3_test.NativeEvidence','d2_3_test.E5',
    'd2_3_test.IntegratedGPIOAndLCD','d2_3_test.IntegratedSPI2AndKeyboard',
    'd2_3_test.IntegratedTimerUARTIRQ','f1_e4_test')
def classification(preparation,result):
    problems=[dict(test=t.id(),detail=text) for t,text in result.failures+result.errors]
    def input_block(problem):
        if problem['test'].endswith('.test_actual_supplied_subset_when_available'):
            return preparation.get('selected_evidence',{}).get('status')=='BLOCKED'
        if problem['test'].endswith('.test_preserved_qualified_portc_and_pllfsr_methods'):
            return any(p.get('status')=='BLOCKED' for p in preparation.get('source',{}).get('pins',[]))
        return False
    regression=[p for p in problems if not input_block(p)]
    state='FAIL' if regression else 'BLOCKED' if problems or result.skipped or preparation['status']!='PASS' else 'PASS'
    return state,problems


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--evidence-scope',choices=('full','provided-subset'),default='full')
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--preserve-selection',action='store_true',help='Preserve actual selected bytes in NEW forensic archives before testing, including mismatches')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.resolve().is_relative_to(args.evidence.resolve()):parser.error('Output must be outside original evidence')
    args.output.mkdir(parents=True,exist_ok=False)
    project=Path(__file__).resolve().parents[1]
    # This exact path is audited and supplied to the original integrity test.
    os.environ['DANA_012C_EVIDENCE_DIR']=str(args.evidence.absolute())
    preparation=preflight(project,args.evidence,args.evidence_scope,args.archive)
    (args.output/'preparation.json').write_text(json.dumps(preparation,indent=2)+'\n')
    preserved=None
    if args.preserve_selection:
        preserved=preserve_selection(args.evidence,args.output/'selected-directory-before.tar',preparation['selected_evidence'])
        (args.output/'preservation-before.json').write_text(json.dumps(preserved,indent=2)+'\n')
    suite=unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    state,problems=classification(preparation,result)
    summary=dict(status=state,preparation_status=preparation['status'],tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
        problems=problems,skipped=[dict(test=t.id(),reason=r) for t,r in result.skipped],
        evidence_scope=args.evidence_scope,selected_evidence=str(args.evidence.absolute()),
        forensic_preservation=preserved,
        preparation_report='preparation.json',emulator_executions=0,native_runtime='NATIVE_PENDING',full_boot=False)
    (args.output/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    # Detect any evidence mutation by the battery; never repair it afterwards.
    after=preflight(project,args.evidence,args.evidence_scope,args.archive)
    (args.output/'preparation-after.json').write_text(json.dumps(after,indent=2)+'\n')
    if after!=preparation:
        if args.preserve_selection:
            retained=preserve_selection(args.evidence,args.output/'selected-directory-after.tar',after['selected_evidence'])
            (args.output/'preservation-after.json').write_text(json.dumps(retained,indent=2)+'\n')
            summary['forensic_preservation_after']=retained
        if summary['status']!='FAIL':summary['status']='BLOCKED'
        summary['reason']='PREREQUISITE_CHANGED_DURING_OFFLINE_BATTERY'
    if preserved and preserved['status']!='PRESERVED':
        if summary['status']!='FAIL':summary['status']='BLOCKED'
        summary['preservation_status']='BLOCKED'
    if after!=preparation or preserved and preserved['status']!='PRESERVED':
        (args.output/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return 0 if summary['status']=='PASS' else 1 if summary['status']=='FAIL' else 2


if __name__=='__main__':raise SystemExit(main())
