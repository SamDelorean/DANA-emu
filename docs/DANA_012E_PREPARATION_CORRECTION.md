# 012-E — Joint preparation correction

Source-only continuation of PR #7 from
`47a054cddfef865bd5dbe2035f40a5c155d5e961`. No peripheral increment, production
change, emulator execution, MAME/ROM build, Commander call, T access or dispatch.
The complete integrated 012-E observer and qualification criteria are unchanged.
Frozen correction source/job identities and actual results are recorded in
[candidate status](../tests/dana_012e_candidate_status.json).

## Historical regression source: verified omission and recovery

The previous job fetched only the harness commit and compiled source
`581601b49acb6603af2a100817d0f06fed17ed96`, each at depth one. Neither fetch
provides the independent historical object
`56a0a0040edfc161e45c1131692a64c3649fe3af` required by
`d2_3_test.SourceContracts.test_preserved_qualified_portc_and_pllfsr_methods`.
A long-lived Cloud clone contained this object; therefore its successful
historical test did not prove that the disposable job had sufficient history.

This was reproduced in a new isolated shallow checkout at the reviewed HEAD:
fetching only HEAD/build source produced the original test error (Git exit128).
Explicitly fetching `56a0a004...` then made the **same original test** pass.
The seven method-equality assertions were not edited. Port C and PLLFSR reader
comparisons retain the historical source; the PLLFSR writer retains its existing
approved compiled-012-C comparison. No assertion or regression was removed.

| Source | Actual inspected driver SHA256 | Use |
| --- | --- | --- |
| `56a0a0040edfc161e45c1131692a64c3649fe3af` | `6bff19e0ae1e6c7a1f99a86fcfa2fbe235ac096c6624a10f6600fbd8851ddcf0` | Original Port C / PLLFSR contract |
| `581601b49acb6603af2a100817d0f06fed17ed96` | `e8211be78dfb2bf4cdc0ccabd444c97d715dc37d189d4f113f2f1cbf05b573e2` | Compiled integrated driver and PLLFSR writer |

The corrected single job explicitly fetches all three commits into its own
new checkout. Read-only preflight verifies commit type, exact driver bytes and
unchanged production/overlays before qualification. Negative controls reproduce
the missing historical object in a separate shallow repository, recover it via
an explicit fetch and rerun the original assertion. No alternate object store,
shared history or HEAD substitution supplies the missing baseline implicitly.

## RAM hash discrepancy: exact known identity and unresolved raw evidence

The reported actual hash is
`56f40dfb00b27a33fe4fdf797cdb5c16e1c1910d8c0e441302bc19c8c6156e6a`.
The expected hash is
`6be10c77aa5b9c0c5b3ee4844568ffd071a158640e16bfe04c76e9ecdb0a626e`.
They must never be treated as equivalent.

**VERIFIED index:** original `evidence/evidence_sha256.json`, SHA256
`c804cbc536215a5eed3db6cf3025f64dde2ddbfce10dff5eddab3021d7ab40dd`,
obtained unchanged from user-supplied `DANA_012C_Para_Codex.zip`, SHA256
`718abbd0253f35b052f5e52b7ae89adeecfaecbebb181ac38ef5766498790a7c`.
It records 40 members and assigns the expected hash to exactly three files:

| Original index key / archive member | Original indexed SHA256 |
| --- | --- |
| `pfsel/reset/final.ram` / `evidence/pfsel/reset/final.ram` | `6be10c77aa5b9c0c5b3ee4844568ffd071a158640e16bfe04c76e9ecdb0a626e` |
| `pfsel/save_restore/final.ram` / `evidence/pfsel/save_restore/final.ram` | Same original hash |
| `pfsel/save_restore/restored.ram` / `evidence/pfsel/save_restore/restored.ram` | Same original hash |

**VERIFIED effective selection in the old job:**
`DANA_012C_EVIDENCE_DIR=/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/evidence`.
`test_actual_supplied_subset_when_available` recursively hashes that directory
and compares each file to the index in **that directory**. The original job
separately audited
`/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/dana_timer_uart_irq_hmkem769.tar.gz`
against SHA256
`1fc1d8417eea975c80f29a74aa53e6ccc8fd835b2d2cc924951afec748364a18`.
Only the qualification and manifest were then compared across archive/live
selection. A good archive does not establish integrity of selected live RAM.

**UNVERIFIED:** which of the three selected RAM paths produced the reported
actual hash; its bytes, size, physical origin, mutation history and whether the
same discrepancy exists inside the original tar.gz. The supplied ZIP contains
seven indexed metadata/result files and the index, **none of the three RAM
files**. All seven supplied files still match. The reported actual hash is not
present in the supplied index or available RAM files. The original assertion
reported two hash strings without naming the selected path; that diagnostic
omission prevented unique attribution from the supplied error alone.

The checksum failure remains a genuine **BLOCKED integrity condition**, not a
fixed corruption, a hardware FAIL, or proof of a particular wrong file. No
stale-copy, native RAM defect or archive mutation is invented as its cause.
Raw Drive evidence remains unavailable under the previously documented HTTP403;
no retry, bypass, credential change, T or Commander retrieval was used here.

## Corrected preparation and independent diagnostics

`dana_012e_prepare.py` is read-only. It anchors both the original full archive
and original index, rejects ambiguous paths/symlinks/extra or missing files, and
records for **every selected file**: relative key, selected and resolved paths,
index path/hash, expected hash, actual hash, size and status. The original hash
assertion is unchanged except for an expanded failure message naming its actual
selection, resolved file and index. Wrong bytes still fail the assertion.

The complete offline interface is:

```sh
PYTHONPATH=tests python3 tests/dana_012e_offline.py \
  --evidence ORIGINAL_SELECTED_EVIDENCE_DIRECTORY \
  --evidence-scope full --archive ORIGINAL_012C_TAR_GZ \
  --output NEW_OFFLINE_RESULT_DIRECTORY
```

The same explicit path is audited and passed to the original integrity test.
The **entire** offline battery runs even if the audit finds an input blocker;
there is no peripheral split or omitted test. Results are machine readable:
`preparation.json`, `result.json`, `preparation-after.json`, plus the original
test output. A true code regression is FAIL/exit1. Missing or mismatching input
is BLOCKED/exit2, including any skipped test. A complete battery with valid
prerequisites is offline PASS/exit0; it is never a functional emulator PASS.
A source assertion failure is classified as an input block only when an actual
pinned-source prerequisite failed, so unrelated failures are not hidden.

The per-RAM comparison separates index/selection identity, selected bytes and
archive bytes. An invalid selected index is reported as an unresolved selection
or index mismatch. If a verified original archive matches its index but selected
RAM differs, the selected copy has diverged; later alteration versus a wrong
directory remains unresolved without additional provenance. An archive member
that disagrees with its original index is an archive consistency failure.
Absent bytes remain unavailable, with calculated SHA `null`. None of these
cases licenses a repair or a guessed physical RAM corruption diagnosis.

Full native preparation requires **all 40 indexed selected files and the exact
original archive** to pass independently. The job stops before either authentic
guest process if they disagree. It never repairs or reindexes inputs, switches
to an alternate good directory, extracts replacement evidence or bypasses a
failed RAM check. Before/after reports detect changes during tests/native work.
The job's final index describes only its new output bundle; it is not a rewrite
of any original input index.

For Cloud's actual seven-file package only, an explicit
`--evidence-scope provided-subset` runs **the same full battery** and verifies
exactly those seven supplied members against the original pinned index. It
records 33 missing native members and cannot qualify the full archive. The
native job always requires `full`; it cannot select this scope as a fallback.

## Actually executed results and limits

The complete current battery includes the previous 118 tests and 20 additional
preparation controls. Actual counts, skips, timing and source hashes are frozen
in candidate status. Negative controls cover missing historical Git objects,
wrong pinned source, each disputed RAM path, wrong selected directory, missing
RAM, archive/index corruption, attempted reindexing, symlink/unindexed inputs,
explicit subset/full distinction, original assertion diagnostics, stale
authorization flags, and PASS/FAIL/BLOCKED classification.

The isolated historical failure/recovery is real Git/source verification, not
native emulator evidence. Synthetic corruption controls operate solely in new
temporary fixtures with explicit synthetic anchors; no historical evidence is
rewritten. The complete full-scope Cloud attempt remains BLOCKED because the
33 original files and full archive are absent, even when all offline tests pass.
It does not prove the reported RAM discrepancy has disappeared.

The existing `dana-diag` identity remains
`caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37`;
no live T rehash or execution occurred. All PFSEL, Timer1, UART1, IRQ6, LCD,
SPI2 and ST runtime instrumentation/criteria, observation limits, original
guest hashes and independently accredited historical results retain their scope.
New native outcomes are **NATIVE_PENDING**, with no functional PASS.

## Frozen single job, continuity and one next action

The existing `012_e_dana_integrated_observation_diag.job.sh` is corrected in
place and remains **GIT HOLD / NOT UPLOADED / NOT LAUNCHED**. Its old immutable
Git version remains historical; there is no second peripheral job or compilation
fallback. The final job freezes the correction source commit and hashes; fresh
independent authorization is still mandatory before native execution. Neither
an old approval flag nor an offline PASS authorizes a launch.

HANDOFF, the anti-gate ledger, observation contract and existing
`DANA_012E_RECTOR_UPDATES.csv` are updated. The same workbook remains
`AS2K_TEMP/DANA_EMU/DANA_EMU_Control_Rector_Auditoria_2026-10-20.xlsx`, ID
`1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l`. Exact records are prepared for its existing
CONTROL, HITOS, CAMPAÑAS, CONTRATOS, RIESGOS, BITACORA and FUENTES tabs. The workbook
itself is unavailable and was not edited; no replacement workbook was created.

**ONE NEXT ACTION:** independently inspect the complete authentic preparation
bundle and its selected RAM/index to uniquely attribute and resolve the reported
hash mismatch; keep the single corrected native job in HOLD until that integrity
block and separate execution authorization are satisfied.
