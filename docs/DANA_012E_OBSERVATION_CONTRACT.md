# 012-E — Integrated native observation and peripheral qualification

**012_E_STATIC_PASS / NATIVE_PENDING.** One source-only candidate on existing
PR #7, branch `codex/dana-d1-2-ram-bus`. No production peripheral, donor, build
overlay, ROM or historical job was changed. Exact source/job pins and hashes
are in [candidate status](../tests/dana_012e_candidate_status.json).

## Continuity and evidence boundary

Reviewed 012-D implementation `be16f21f6e1d8102a6d0b5542f720d87ecd590ee`
and job/base `d1dc3e9b3ca7b1208193c977fc64e81010aadfa8`.
Canonical main `e147c940741363af186dae9026d9788f0566fea9` supplied the General
Work Plan, anti-gate plan and DIAG-exclusive policy absent from the feature
tree; branch continuity rules, HANDOFF and source lock were read as well.
The anti-gate plan is now present in this branch with a new current checkpoint
and the original canonical body preserved as historical context.

**VERIFIED:** the seven previously supplied 012-C subset members still match
their original 40-member index. This does not supply the 012-D native traces.
The requested [012-D evidence folder](https://drive.google.com/drive/folders/19hRLZwBGKchwdBHmJZpc8VG3_arkx9ls)
returned HTTP 403 on direct read-only access, including the environment's
required permission retry. No alternate credentials, access bypass, Commander
or T access was used. No further access attempt followed the user's restriction.

**PROVISIONAL:** the user's reported two native 012-D outcomes
`BLOCKED_TRACE_BUDGET` / `NO_NEW_CPU_DEPENDENCY_WITHIN_BOUND` and repeated
`$FFFFF202` polling. Both authentic raw traces, their PC/SR/SP, instruction and
event totals, timing, Lua outputs, original archive hash and peripheral results
are unavailable here. Exact native boundary attribution remains unverified.
No old native result is upgraded, revoked or replayed by this delivery.

## Verified source findings and correction

The 012-D Lua recorder allowed 20,000 events or 4 MiB encoded events; native
trace capture stopped above 4 MiB, and the old Python verifier additionally
limited instruction trace lines to 20,000. The process had a 5 MiB file cap,
5-second virtual observation and 180-second host timeout. Native instruction
loop compression does not compress the separate MMIO tap stream. A poll can
therefore consume the observation budget without discovering unsupported MMIO.
The old independent verifier also required a new dependency to accept a run;
a bounded run without one could not qualify otherwise observed capabilities.

A demonstrated configuration defect is corrected in the existing F1 runner:
the imported old serializer emitted Python `True`/`False` as Lua identifiers,
yielding `nil`. In particular, `integrated_recovery=True` did not enable the
native IACK tap. Real Lua round-trip tests reproduce and fix this. The
historical D1.2 serializer and qualified fixtures remain unchanged. This source
defect is not asserted to explain a specific inaccessible native run.

Pinned donor `c4e48388ca620472643110db2941ce70aa5f3c07` was inspected read-only:

- `src/emu/debug/debugcpu.cpp` exports the native `totalcycles` symbol and
  implements loop/interrupt trace records. Closing the tracer does not emit
  its pending final loop count: instruction totals are explicitly a **lower
  bound**, with exact total `null`; cycles are observed independently.
- `src/emu/debug/debugcmd.cpp` and
  `src/frontend/mame/luaengine_debug.cpp` provide debugger `printf`, command
  and console buffer APIs. Checkpoints preserve token-bound raw native output;
  no guessed Lua counter or elapsed-time estimate substitutes for CPU cycles.
- `src/devices/cpu/m68000/m68000.cpp` exports CURPC/PC/IR/SR/SP, all D registers,
  A0–A6 and USP. `m68000-sdf.cpp:rte_df` reads the six-byte exception frame,
  updates SR/SP and prefetches before CURPC changes. The observer distinguishes
  those prefetches from a real successor instruction; production is untouched.
- Original EmuTOS `bios/dana.c:delay_us` counts CLK32 transitions at F202.
  Observed cycles and repeated reads alone cannot prove delay completion,
  guest progress or a deadlock. Historical D0 research remains authoritative.

## Loss-accounted observation contract

The opt-in `--observation-012e --pfsel-build ORIGINAL_QUALIFICATION` interface
uses the existing F1 runner and Lua observer, with a pure helper for aggregation.
Only consecutive CPU-origin 16-bit reads at F202 with identical data, all
21 captured CPU state fields, epoch and deferred-dependency status are combined.
Each span retains exact count, first/last raw ordinals, first/last PC and time,
maximum inter-read gap, lane, operation and constant CPU state. No timing model
is substituted. Register/value/PC changes split spans. All writes, other reads,
IACKs, RTE accesses and checkpoints remain individual records and split spans.
Both physical row sequence and logical pre-compression sequence are verified.

Counts apply to the declared observation filter: low-memory vectors, MMIO and
RTE/resume accesses plus debugger milestones/checkpoints. They are not a claim
to capture all RAM or opcode bus cycles. On storage exhaustion, the full first
omitted event and the number of subsequent omitted eligible events are retained.
Only the complete accepted prefix can qualify capabilities; the missing tail
cannot establish a dependency, output or framebuffer chronology. There is no
sampling, reconstructed bus data, synthetic IRQ or host-origin replacement read.

**Measured offline control:** the actual Lua helper encoded 100,000 identical
synthetic F202 reads as one 580-byte event, preserving count 100,000. The local
measurement took 1.675358 seconds; this is a helper workload, not emulator
throughput, a native trace measurement or a promise of this compression ratio
when CPU registers change. No emulator was executed.

## Termination policy and measurable bounds

Values are frozen in [the limits contract](../tests/dana_012e_limits.json).
Stop at first unsupported CPU dependency or the first observed bound:

| Bound | Per native process |
| --- | --- |
| Virtual observation | 12 seconds |
| Native cycle delta | 400,000,000 |
| Eligible raw observations | 100,000,000 |
| Retained rows / encoded event reservation | 100,000 / 32 MiB |
| Native trace / each native log soft trigger | 8 MiB / 8 MiB |
| Native checkpoints | 512 |
| Hard file-size cap | 64 MiB per file, RLIMIT_FSIZE |
| Emulator safety timeout / host timeout | 13 virtual seconds / 240 host seconds |
| Pair stage timeout | 540 host seconds |
| Original archive audit | 256 members, 128 MiB uncompressed maximum |
| Final evidence size audit | 768 MiB; excess classifies BLOCKED |

Tap storage limits are checked per accepted observation. Cycle/time/trace/log
triggers are checked by the periodic callback and may overshoot until it runs;
the verifier allows at most 0.25 virtual seconds and 10 million extra cycles.
The 8 MiB thresholds are soft triggers, not hard file caps. Native tracer flush
may add bytes. Host timeout or hard file termination without a valid final
capture remains BLOCKED. Raw files are preserved, never truncated to pass a
limit. The final archive audit classifies oversize before packaging; it does
not delete evidence or claim a hard 768 MiB allocation limit.

Native `totalcycles` checkpoints are read outside taps with unique hexadecimal
tokens and an independently matched `cycles.log`. Missing/stale/reordered output
blocks verification. Native trace loop counts and interrupt markers are parsed
without a line-count gate; unrecognized records block verification. An ordinary
delay is supported by real cycles and CLK32 edges; exit requires subsequent
causal output. Polls without edges are reported as such, not labelled a proven
stall. A genuine IRQ requires the chain below. A bounded prefix with no new
dependency remains useful observation and never implies full boot.

## Independent capability criteria

Each capability is scored separately in each process and then across the pair.
Both processes must satisfy their own causal criteria for a scoped PASS; one
process, missing evidence or a capability name cannot imply another PASS.

| Capability | Native causal requirement | Current 012-E status |
| --- | --- | --- |
| PFSEL | C5 read at PC83A2, then C5 write at PC83A8, correct lane | BLOCKED / NATIVE_PENDING |
| Timer1 programming | Ordered TPRER=2, TCMP=D7E4, TCTL=0033 CPU writes | BLOCKED / NATIVE_PENDING |
| Timer1 compare | Native compare plus CPU TSTAT compare bit or completed IRQ6 | BLOCKED / NATIVE_PENDING |
| UART1 registers | Actual CPU accesses; register-access scope only | BLOCKED / NATIVE_PENDING |
| UART1 TX | CPU ready read, UTX1D writes and matching ordered native TX bytes | BLOCKED / NATIVE_PENDING |
| IRQ6 | Timer setup, CPU IACK46, vector118/11A, handler/native IRQ trace, RTE frame reads and restored SR/SP/PC at actual resume | BLOCKED / NATIVE_PENDING |
| LCD controller | CPU writes of LSSA/stride/geometry/format/enable and native configured state | BLOCKED / NATIVE_PENDING |
| LCD RAM frame | Configured 11,200-byte real RAM snapshot and matching metadata; nonzero pixels, no unsupported/lost tail | BLOCKED / NATIVE_PENDING |
| SPI2 registers | Actual CPU register accesses; access scope only | BLOCKED / NATIVE_PENDING |
| SPI2 exchange | CPU data/control writes, completion and receive read | BLOCKED / NATIVE_PENDING |
| ST greeting | SPI2 chain yielding AA, CPU-observed ready and prior asserted chip select | BLOCKED / NATIVE_PENDING |

A configured blank frame is not proof of a displayed EmuTOS UI. LCD window,
keyboard interaction, UART RX and full boot remain outside qualified scope.
After native execution the available classifications are PASS, PARTIAL,
BLOCKED and NOT_REACHED. Top-level observation is PARTIAL even when some scoped
capabilities pass; `full_boot=false` is mandatory. Missing global provenance or
ambiguous sequences are BLOCKED. An actual first unsupported access must agree
between independent processes in address, lane, operation, CURPC and IR, and
include its native disassembly. No predicted next peripheral becomes a fault.

## Immutable reuse and single HOLD job

The job freezes the implementation commit separately from its own final job
commit. It audits the full original archive, verifies unchanged production
trees and original binary/manifest/qualification, and reads the existing guest
and caches without alteration. No alternate emulator or compilation fallback:

| Artifact | Immutable identity |
| --- | --- |
| Existing DIAG build source | `581601b49acb6603af2a100817d0f06fed17ed96` |
| Existing dana-diag SHA256 | `caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37` |
| Original manifest SHA256 | `504530b8ba90549fc6cfd5dc7ec7505ff013ee025daceec9c60dc26a4e4988de` |
| Original qualification SHA256 | `6fda7a9474c7594ae1019fea33766ad65c99d9e81a5d323ec1e1f6b5ba914131` |
| Authentic EmuTOS source | `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b` |

The existing four guest hashes remain in `tools/f1_guest.py:QUALIFIED_ARTIFACTS`;
image/map/build-provenance validation is mandatory. The new job performs
before/after qualification probes, offline controls, exactly two fresh authentic
guest processes and independent verification. Historical PFSEL reset/save and
other closed campaigns are preserved without native replay. The job records
hashes, bounded raw traces/logs, real PC/SR/SP, cycles, counters, each component
and first unsupported dependency, and validates its evidence inventory/archive.
Transport code is dormant until separately authorized execution.

**LOCAL GIT HOLD, NOT UPLOADED OR LAUNCHED.** Guard:
`DANA_012E_AUTHORIZED=YES` only after fresh scoped native authorization. Old
authorization flags cannot run it. Commander calls, T executions, emulator
executions, MAME/ROM builds and Drive dispatches in this delivery: **zero**.

## Validation, continuity and next action

The exact executed suite and outcomes are recorded in candidate status. Tests
exercise the real Lua helper, serialization, cycle parser, native RTE tagging,
independent verifier and adversarial synthetic evidence, plus prior 012-D,
guest input and isolated production logic regressions. Synthetic positive
controls test the evidence contract; they are not native evidence. Bash/Python/
Lua syntax, HOLD guards, source/hash audits and unchanged production are checked.

[Rector records](DANA_012E_RECTOR_UPDATES.csv) are exact proposed updates for
CONTROL, HITOS, CAMPAÑAS, CONTRATOS, RIESGOS, BITACORA and FUENTES in the existing
workbook. Its binary/column schema is unavailable: records are prepared, not
applied, and no replacement workbook was created. HANDOFF and the anti-gate
plan carry the current checkpoint. Source rollback is the reviewed 012-D base;
immutable native/guest inputs and historical campaign artifacts are preserved.

**ONE NEXT ACTION:** obtain fresh authorization for the single frozen 012-E
existing-DIAG native HOLD job; independently audit its one returned evidence
package and apply the prepared records to the existing rector workbook. No
new native PASS or exact next unsupported dependency is claimed before that.
