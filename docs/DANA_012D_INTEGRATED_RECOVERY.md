# 012-D — Integrated qualification recovery using the existing DIAG

**012_D_STATIC_PASS / NATIVE_PENDING.** Existing PR #7 branch
`codex/dana-d1-2-ram-bus`, reviewed remote base
`5bbff40bd1fd2ccb257c27ab7618706cd487db4e`; canonical main read
`e147c940741363af186dae9026d9788f0566fea9`. This is one integrated delivery,
with no production source, MAME donor, build overlay or guest modification.

## Exact evidence and historical failure boundary

The supplied `DANA_012C_Para_Codex.zip` SHA256 is
`718abbd0253f35b052f5e52b7ae89adeecfaecbebb181ac38ef5766498790a7c`.
All **seven supplied evidence files** match their original `evidence_sha256.json`
entries. That original index contains **40 files**; the ZIP is a subset, not
another copy of the full native archive. The supplied full archive identity is
`dana_timer_uart_irq_hmkem769.tar.gz`, SHA256
`1fc1d8417eea975c80f29a74aa53e6ccc8fd835b2d2cc924951afec748364a18`.
The full tar.gz was not available to rehash in Cloud.

Verified from the exact supplied bytes:

| Input / predicate | Result |
| --- | --- |
| `binary_qualification.json`, SHA `6fda7a9474c7594ae1019fea33766ad65c99d9e81a5d323ec1e1f6b5ba914131` | Matches original index |
| Manifest content SHA vs qualification | Both `504530b8ba90549fc6cfd5dc7ec7505ff013ee025daceec9c60dc26a4e4988de`; PASS |
| Manifest status | `BUILT_DIAG`; PASS |
| Manifest/source revision | Both `581601b49acb6603af2a100817d0f06fed17ed96`; PASS |
| Manifest/MAME pin | Both `c4e48388ca620472643110db2941ce70aa5f3c07`; PASS |
| Manifest/variant | `diag`; PASS |
| Manifest/recorded executable SHA | Both `caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37`; recorded identity agrees; actual executable bytes are on T |
| Manifest/driver SHA | `e8211be78dfb2bf4cdc0ccabd444c97d715dc37d189d4f113f2f1cbf05b573e2`; independently matches actual Git driver bytes at 581601b |
| Recorded build command | DIAG `make -j3`, correct source, DEBUG=1, successful exit; no static command mismatch |

**No failing historical content predicate can honestly be identified from this
subset.** The original error is emitted by a seven-way combined condition,
not a missing-file exception. A missing manifest would have produced an OS
exception instead. The source runner's initial qualification precedes its two
native fixture attempts; the index lists their run/observation/trace/RAM files,
but those files and live resolver inputs were not included. The two supplied
results only retain `Missing matching staged PFSEL build manifest`.

Therefore the exact historical first predicate remains **UNDETERMINED**, not
"manifest missing", "corrupt SHA", or a demonstrated hardware failure. This
limitation is part of the delivery, not replaced by a guessed root cause. The
confirmed harness defect is loss of predicate identity in that combined error.
The new read-only probe records the resolved paths, actual hashes, PROJECT,
harness revision and named first failure, before and after native work.

## Implemented repair and source-compatible reuse

`qualify_pfsel_build()` retains every manifest, source, driver, executable,
subtarget and build-command check and reports its first failing condition as
`PFSEL_QUALIFICATION:<predicate>`. Hash validation is not weakened. Neither a
manifest nor an executable is fabricated, repaired in place or substituted.

Harness revision and binary build revision are now separate contracts. Only the
explicitly pinned 012-C artifact may be reused across a harness-only change:
all original source/binary/manifest/qualification hashes must match; actual Git
driver bytes at the compiled source must match the current driver; the entire
production/overlay Git diff must be empty. An arbitrary old binary or branch
HEAD cannot qualify. Both native PFSEL and guest records bind
`build_source_commit=581601b...` separately from the new `source_commit` and
observation-bound qualification hash. Original files stay read only at their
original paths. No MAME rebuild is needed for these instrumentation changes.

The single new job verifies the complete original archive and all its members,
compares original archived and staged manifest/qualification bytes, checks the
live existing executable, and fails closed with a precise probe if any input
is missing or differs. It never copies a replacement manifest into the old
stage, relocates the binary, reinstalls dependencies, rebuilds MAME/EmuTOS or
replays 011. Existing 011/012 jobs, qualified images and caches are untouched.

## One integrated native sequence and independent evidence

After fresh separate native authorization, the one frozen job runs PFSEL native
save/restore and reset on the same 012-C DIAG, verifies both independently and
requires distinct process identities. It then runs the original unmodified
EmuTOS twice, with original hashes/map/provenance, on the same executable.

The new verifier first rechecks both authentic runs and identical raw bus
prefixes. Each component has its own causal evidence and status:

- Timer1: ordered CPU word writes TPRER=2, TCMP1=D7E4, TCTL1=33. This qualifies
  programming only, not timer timing or interrupt delivery.
- UART1: register access separately from TX. TX requires a CPU low-byte UTX1D
  write and matching actual native `DANA_VZ_UART1_TX` emission.
- IRQ6: a new read-only Lua **CPU-space** tap records actual aligned IACK
  FFFFFFFC/00FF, vector 46 on the same sequence axis as MMIO. Qualification
  requires IACK after Timer1 programming and before the first dependency,
  actual 46-vector fetches, handler instruction trace and genuine timer/IACK
  diagnostics with pending bit1 unmasked. Late log lines alone cannot pass.
- SPI2/ST: access alone is distinct from greeting. A greeting requires CPU DATA
  write, enabled eight-bit exchange, observed completion and native low-lane
  AA data read in order; an unrelated AA read cannot pass.
- LCD: validate actual native controller geometry and the 11,200-byte guest RAM
  snapshot, preserve its hash, convert those bytes directly to PNG. This is
  explicitly a deferred-capture RAM image, not proof of pre-block frame timing,
  a host-painted screen, MAME window presentation or full visual correctness.

Raw events, PC/SR/SP, lanes, exceptions/vector reads, process identities,
original logs, bounded traces and snapshots remain in the result archive.
First new unsupported byte/address/operation/PC/instruction is taken from the
independently verified raw guest trace, never preselected. Missing, ambiguous,
post-dependency or synthetic observations cannot produce native PASS. Serial
RX, interactive keys, physical LCD and full boot remain unqualified.

## Executed validation

The old 012-C job's **68 tests passed locally** unchanged in scope. The new
20-test protocol/causality group also passed. Broader checking exposed one
stale pre-Timer source assertion: it compared the intentionally integrated
PLLFSR writer against pre-Timer 56a0a00. The assertion now compares **that
writer only** to compiled 012-C 581601b; Port C and PLLFSR reader comparisons
retain their old baseline. No assertion is disabled and no production code
changed. Two more regressions bind reused build identity in PFSEL and both
synthetic guest records. Final result: **97 tests in 6.228s, OK, exit 0; zero skips**. Command:

```sh
DANA_012C_EVIDENCE_DIR=/workspace/scratch/012d/original/evidence PYTHONPATH=tests python3 -m unittest dana_012d_test f1_test_guest d2_3_test.SourceContracts d2_3_test.NativeEvidence d2_3_test.E5 d2_3_test.IntegratedGPIOAndLCD d2_3_test.IntegratedSPI2AndKeyboard d2_3_test.IntegratedTimerUARTIRQ f1_e4_test -v
```

Bash syntax, embedded job Python AST, changed Python AST, three unauthorized
HOLD/exit2 cases and `git diff --check` pass. Production and old jobs are byte
identical to the reviewed base. Exact hashes are in
[`tests/dana_012d_candidate_status.json`](../tests/dana_012d_candidate_status.json).

Tests include actual supplied metadata, every named manifest field, missing
path/hash/build mismatch, arbitrary old source, source-compatible reuse,
missing build identities, host/late/wrong-vector IACK, missing vector/handler,
UART read versus TX, unrelated AA/wrong lane, LCD geometry/bytes, unequal native
prefixes, real Lua parsing and a mocked actual IACK callback with no host effects.
These are **offline/synthetic/source tests**, never native functional PASS.

## Sources and license boundaries

| Reference consumed | Use |
| --- | --- |
| 012-C source `581601b`, original producer 012 and supplied exact JSON/log subset | Actual provenance/error contract and build reuse, no guesses |
| Pinned MAME `c4e48388`, `src/devices/cpu/m68000/m68000.cpp:28,193-194` and existing Dana CPU-space mapping | Native `cpu_space` name, 16-bit tap shape and IRQ acknowledge infrastructure; read only |
| Existing integrated Dana source/D0.2/Timer-UART design | Existing VZ, GPIO/LCD/SPI2/ST contract; no new peripheral behavior |
| Original EmuTOS `9c42ef0`, existing pinned research/cache; POSE/Retro68 references in source lock | Preserve actual guest order, hardware research and licensing; no GPL implementation copied |

No emulator, MAME/ROM build, T/Commander, alternate launcher, Drive dispatch or
PR merge occurred. Historical safety refusals remain intact; this job does not
authorize or provide a workaround for remote execution.

## Rector workbook and exact next action

Existing workbook: `AS2K_TEMP/DANA_EMU/DANA_EMU_Control_Rector_Auditoria_2026-10-20.xlsx`,
ID `1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l`. The supplied location lists CONTROL,
HITOS, CAMPAÑAS, CONTRATOS, DIRECTRICES, RIESGOS, BITACORA and FUENTES.
[Exact update material](DANA_012D_RECTOR_UPDATES.csv) covers these existing tabs.
No Drive connector/workbook bytes or column schema are available here; no claim
is made that the workbook itself was edited or that a replacement was created.

**One next action:** separately authorize and execute the single source-pinned
012-D HOLD recovery on T using existing 012-C artifacts, then independently
consume that one result bundle and apply its capability results to the existing
rector workbook. No rebuild or per-peripheral ticket series. Reverting this harness delivery or
leaving its job in HOLD does not alter the original driver/build/evidence.

Frozen recovery harness source: `be16f21f6e1d8102a6d0b5542f720d87ecd590ee`.
Job SHA256: `99bddd2c4494f12f498a5ffa9f0a2f5c98c86fdee9e697497ec9b556db4a8894`. Job remains local Git HOLD.
