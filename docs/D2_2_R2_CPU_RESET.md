# D2.2-R2.1 — CPU-origin Port C reset capture completion

> **Native checkpoint superseding the old pending status below — 2026-10-18:**
> canonical main commit `c5f76ccc45fdc4f3198b75806395a67b648b9c94` independently
> qualified R2.1 A/B PASS, PIDs 310239/310254, existing qualified DIAG reused.
> Archive `portc_reset_r21_9bqe2gzh.tar.gz`, 44,411 bytes, SHA256
> `b365c0672574383e586f8fac886182811f11281a7e345d65d043ebbd072e8268`,
> 32/32 manifest members verified by the supervisor. Historical R2 remains
> BLOCKED. No native campaign was repeated by the F1-E4 source delivery.
> Authentic guest continuation is now separately PREPARED / NATIVE_PENDING:
> [F1-E4 report](F1_EMUTOS_EXECUTION_CANDIDATE.md).

**2026-10-18: R2.1_STATIC_PASS / NATIVE_PENDING.** Reviewed HEAD
`5065259a651face37a6cd7b363f4080bb0b741ca` matched the clean feature branch
and remote before editing. Canonical `main` at
`e05d28e9c34d8bd7100a949791c0581754250631` and the complete supplied R2.1
contract were read. This is a B-only diagnostic capture correction on draft
[PR #7](https://github.com/SamDelorean/DANA-emu/pull/7), not new hardware.

## Historical native R2 remains BLOCKED

The supplied contract and canonical HANDOFF report archive
`portc_reset_r2_2dl7aw59.tar.gz`, SHA256
`7acacf0e542d72e9a21c34db8eab1cfd696452c8abc8c37531b2fde4a310fe52`,
with 31/31 internal hashes independently verified by the supervisor. A PID
309035 passed; B PID 309045 timed out after the seven correct post-reset CPU
events, including Port C read zero and CPU result store zero, and trace STOP
at `40AE` followed by two `ori.b #$0,D0` entries at `40B2`. B never emitted
`cpu_reset_complete` or `reset.ram`. Its result stays **BLOCKED**. These are
carried-forward review findings, not a new private archive download/audit.
The exact-PC gate is a probable cause; sampled periodic PC was absent, so the
precise native cause remains unconfirmed.

## Bounded R2.1 correction

The periodic callback now captures once `ready and post_ready()` establishes
the same seven raw CPU events. No sampled PC is a Lua completion prerequisite.
It closes/flushes the native trace through existing MAME `trace off`, records
its byte count, samples CPU/RAM diagnostics and dumps the entire 4 MiB RAM.
`pc` means CURPC, `next_pc` means PC; IR, SR, SP, marker, result, total event
count before capture, total CPU event count, post-reset CPU count, epoch,
request ID and virtual time accompany the capture. Host snapshot reads are
excluded from CPU taps. No exit, finish or debugger operation runs inside a
tap. No post-reset breakpoint or mandatory reset notifier was added. Event
limit 256, one-second virtual bound, two-second emulator bound, 90-second host
bound and existing file limits are preserved. Lua reports **CAPTURED**, never
qualification PASS; captures before STOP remain independently BLOCKED.

Python still requires the complete genuine request/transition/vector/marker/
read/store chain, only one post-reset MMIO read, all three exact 4 MiB RAM
comparisons, original-body execution once, separate process/execution IDs,
matching source identities and the qualified DIAG SHA. A nonzero Port C value
is FAIL only after every other evidence check passes.

The replacement terminal rule additionally requires:

- A final periodic capture event with exact raw/CPU/post-reset counts and a
  trace file of the recorded byte length; no instructions appended later.
- The native post-reset trace `4000,4006,40A2,40A8,40AE`, with an actual
  `stop #$2700` disassembly at `40AE`. No original-body replay is allowed.
- Only zero, one or two `ori.b #$0,D0` tail entries at `40B2`, matching the
  previously observed tail and zero bytes in the fully checked RAM. Any other
  tail instruction/address or longer tail is BLOCKED.
- CURPC at the last traced instruction or its next word, PC zero/two/four
  bytes ahead of CURPC and at least `40B0`, SP `8000`, and a valid 16-bit IR
  sample. This corroborates pipeline diagnostics without exact `PC=40B2`.
- SR `2700` after STOP. If the observed zero-ORI tail is present, its N/Z flags
  derived from the CPU-read result's low byte are also allowed, preserving
  supervisor mode, interrupt mask and X/V/C. A pre-STOP sample or contradictory
  SR/SP/trace remains BLOCKED. IR is recorded, not used as an opcode gate.

This rule establishes a bounded observation-path terminal state, not permanent
physical STOP/halt behavior. Sampling outside the corroborated path is BLOCKED
and retains diagnostics; no arbitrary PC is accepted. R2 records are not
silently upgraded to the R2.1 schema or reclassified PASS.

## Pinned source-to-claim evidence

All MAME inspection used the read-only donor at
`c4e48388ca620472643110db2941ce70aa5f3c07`.

| Source | Verified use |
| --- | --- |
| `src/emu/debug/debugcpu.cpp`, `device_debug::trace`, tracer destructor/update | `trace off` destroys/closes the stream; trace is native disassembly before dispatch, not proof of physical halt |
| `src/emu/debug/debugcmd.cpp`, `execute_trace` | Existing command closes tracing without a breakpoint or CPU state mutation |
| `src/devices/cpu/m68000/m68000.cpp`, `execute_run`, `state_add` | Native instruction hook, CURPC=`m_ipc`, PC=`m_pc`, IR=`m_ir`; PC is pipeline state |
| `src/devices/cpu/m68000/m68000-sdf.cpp`, `stop_i16u_df` | STOP loads SR from its operand and invokes the existing debugger wait hook |
| `src/devices/cpu/m68000/m68kdasm.cpp`, `d68000_stop`, `d68000_ori_8` | Actual native STOP and zero-ORI disassembly spelling accepted by the verifier |

No POSE/Retro68/EmuTOS code was copied. Production GPIO, physical FF versus
R-direct 00 profiles, CPU/RAM/IRQ/PLLFSR/loader, source lock and donor are
unchanged. Qualified A functions/Lua, both fixtures and displacement `009A`
remain exactly unchanged, verified by the frozen hash checks below.

## R2.1 executed offline validation

```sh
PYTHONPATH=tests python3 -m unittest d2_2_gpio_contract_test d2_2_test_verifiers d2_2_r1_test_reset d2_2_r2_test_reset_cpu -v
bash -n tests/hold/008_dana_portc_reset_r21_reuse_diag.job.sh
bash tests/hold/008_dana_portc_reset_r21_reuse_diag.job.sh
git diff --check
```

Actual full-suite output: **`Ran 93 tests in 11.733s` / `OK`, exit 0**:
40 preserved checks plus 53 R2/R2.1 checks. Callback mocks execute only Lua
observer logic; Python negatives use synthetic evidence, never an emulator.
Cases cover differing sampled PC; missing/wrong STOP; premature/false terminal
capture; trace growth or wrong counts; bounded/wrong tail; missing/duplicate/
wrong vectors; forged host read/store; duplicate Port C read or preceding
write; marker/sentinel/result corruption; missing RAM; fixture replay;
missing request/transition; malformed/mismatching source/executable identity;
same PID/execution ID; historical incomplete R2; coherent nonzero FAIL and
incoherent nonzero BLOCKED. Lua mocks also enforce no tap exit/debug commands,
no required reset notifier or extra breakpoint, and deferred budget/replay
errors. Python compilation, full Lua parse and embedded job Python AST pass.
The unauthorised job invocation returns expected **HOLD / exit 2**, before
Python or any machine access. Full log: local scratch `d2_2_r21/offline_tests.log`.

## Next qualification: Git HOLD only

New job: `tests/hold/008_dana_portc_reset_r21_reuse_diag.job.sh`. The final
source pin is `a880969424968c0cf01907e7d0978b22e9f0728a`; job SHA256 is
`b08851cfb42883bd877ad210c82b094d83d7ef151dfd23a65de40ad25230f372`. Both are recorded in `tests/d2_2_candidate_status.json`.
Its independent authorization/reference interface is:

```text
DANA_D2_2_R21_AUTHORIZED=YES
DANA_D2_2_R21_BINARY=/absolute/existing/diag/bin/dana-diag
```

It requires the exact existing binary SHA, verifies production tree identity
against build source `749517b2f48c9788e5555071561e738017ac5f7c`, copies the
reference read-only into an isolated stage, runs the Python negatives and two
independent DIAG processes, re-verifies raw evidence, archives all results and
hashes and uses only the existing private outbox transport. No build fallback.
Old `007` is preserved unchanged as historical R2. `008` is LOCAL_GIT_HOLD,
not uploaded, dispatched or run on T. No emulator, T, Commander, MAME/ROM
build, binary publication or PR merge occurred in this delivery.

Changed files: B Lua, R2 Python runner/verifier, R2 offline tests, this report,
HANDOFF, candidate status and new `008` job. Next action: independent source
review followed by fresh explicit native authorization. No functional R2.1
PASS is claimed and authentic EmuTOS continuation has not advanced.

PR #7 receives the reviewable diff through the existing feature branch push.
Direct `gh pr view` returned GraphQL `Forbidden` both normally and on the
required escalated retry; a PR description edit cannot be claimed. This
committed report supplies the complete review material without overwriting an
unread PR body.

---

The following R2 implementation report is retained as historical context;
its old pending/runtime and exact-PC statements are superseded above.

# D2.2-R2 — CPU-origin Port C reset observation (historical report)

**2026-10-18. R2_STATIC_PASS / NATIVE_PENDING.** Branch `codex/dana-d1-2-ram-bus`, reviewed base `d3742bc37f42e4ed68c0ef89ee64134f0d797cd9`, draft [PR #7](https://github.com/SamDelorean/DANA-emu/pull/7). The complete self-contained user specification supersedes the inaccessible Drive link; that link was not retried after this clarification. Canonical `main` HANDOFF was read before editing.

## Evidence carried forward

The supplied/canonical R1 review identifies archive `portc_reset_r1_oxhx9ryu.tar.gz`, SHA256 `2e8b9d0472f4bf803093f0339263c730306e308e31835694ecb64ed5c987b29c`, with all 31 members verified by the independent reviewer. R1 A native save/restore **PASS**; R1 B **BLOCKED / VIRTUAL_TIMEOUT** despite a reset request, prestart transition and four new CPU vector reads. No `profile_reset` or validated post-reset register value was observed; the fixture replayed. This task uses those supplied results, without claiming a new download/audit of the private archive or a new product failure.

The original build source remains `749517b2f48c9788e5555071561e738017ac5f7c`, MAME donor `c4e48388ca620472643110db2941ce70aa5f3c07`, and the only future runtime executable is the already qualified **dana-diag**:

`d7bcdf513289a73b8a5c7ab1d258eeac45dc8dd6d89dd7d568cf7784900e6fe5`.

No emulator, native guest, MAME build, ROM build, T or Commander was executed in this task. Static assembly/disassembly of a test-owned fixture is not emulator execution or an EmuTOS build. Physical Motorola reset **FF/FF** and synthetic R-direct software profile **00/00** remain distinct and unchanged.

## Preserve A, change B

The existing A fixture, `fixture()`, `execute()`, `verify_execution()` and `tests/d2_2_gpio_boot.lua` remain byte-identical to the qualified R1 implementation. Automated SHA checks freeze those function bodies and the Lua file. Only the CLI entrypoint in `tests/d2_2_gpio_run.py` delegates the new campaign to `tests/d2_2_r2_gpio.py`; it calls the existing A implementation directly. The old R1 functions/tests remain usable for historical evidence. `tests/d2_2_reset_r2_boot.lua` supplies **B-only test instrumentation**, not another emulator or build variant.

B initializes diagnostic RAM once: marker `0x20000=0000`, result sentinel `0x20002=A55A`, outside the code, vector, stack and original snapshot regions. The CPU reads the marker and writes `1` on first boot, then executes the original 144-byte body unchanged. At its relocated endpoint `409E`, the existing native lane/readback/RAM guards establish `FE81` before one genuine soft-reset request.

On reset, the retained prestart callback records the native transition and increments epoch/request context without reseeding RAM, installing taps or changing CPU state. **All first-boot breakpoints are cleared before reset.** The CPU fetches its native vectors, reads the surviving marker, branches around the original body, reads the native Port C word, stores it in diagnostic RAM and executes STOP. No post-reset breakpoint or required `on_machine_reset` callback is used. The optional reset notification is diagnostic only, without a fabricated `profile_reset` event or host Port C read after reset.

Pinned `luaengine.cpp`, `luaengine.ipp` and `util/notifier.h` were inspected: `register_prestart` and the separate subscription callback have different dispatch paths, and subscriptions are retained. This does not establish garbage collection or a defective register handler as the R1 root cause. The new strategy does not depend on resolving that unknown interaction.

## Independently verified encoding

| Address | Bytes | Instruction / boundary |
| --- | --- | --- |
| `4000` | `4A79 0002 0000` | TST.W `$00020000.l` (6 bytes) |
| `4006` | `6600 009A` | BNE.W to `40A2` (4 bytes) |
| `400A` | `33FC 0001 0002 0000` | MOVE.W `#1,$00020000.l` (8 bytes) |
| `4012..40A1` | Original body, 144 unchanged bytes | First-boot STOP is at `409E` |
| `40A2` | `3039 FFFF F412` | MOVE.W `$FFFFF412.l,D0` (6 bytes) |
| `40A8` | `33C0 0002 0002` | MOVE.W `D0,$00020002.l` (6 bytes) |
| `40AE` | `4E72 2700` | STOP `#$2700` (4 bytes), next PC `40B2` |

**Correction to the proposed displacement:** MC68000 Bcc.w is relative to the extension-word address `4008`. Therefore `40A2−4008=009A`. The proposed `0098` would target `40A0`, inside the original STOP immediate. The 178-byte layout is retained. Explicit `.l` addressing is required: a generic assembler may shorten `$FFFFF412` to an absolute word, producing 176 bytes and moving the final STOP.

Independent GNU MC68000 `as -m68000` and `objcopy` assembled `tests/d2_2_r2_reset.s` with a private `portc_a.bin` generated from the original fixture; all 178 output bytes matched the Python fixture. `objdump -m m68k:68000 --adjust-vma=0x4000` independently confirmed the branch and instruction boundaries. None of these tools executes a guest.

- Original A/body SHA256: `d2aa7123b85ee0bfeece050b88f2e801a7fd0cd8dc443791b8c1f821685052a9`.
- New B SHA256: `8cb8a9a943301f36a1bec27c9b0e1b7fc874e1642705926c1c156358096e0512`.

## Capture and independent acceptance

Taps capture raw CPU-origin marker/result RAM accesses, Port C and other original MMIO controls, and reset vectors. They retain sequence, epoch, request ID, PC, mask and data. They only record or set deferred flags, including error/budget paths: **no tap calls `exit`, `finish` or a debugger command**. The periodic callback completes capture only after the seven ordered post-reset CPU transactions and native next-PC `40B2` have appeared. Native STOP can retain/advance debug CURPC within its idle loop, so exact post-reset CURPC or a breakpoint is not a completion gate. The instruction trace independently must show STOP at `40AE`; complete snapshots retain PC, CURPC, IR, SR and SP.

The seven required post-reset CPU events are exactly:

`vector(0,0000), vector(2,8000), vector(4,0000), vector(6,4000), marker_read(20000,0001), PortC_read(FFFFF412,value), result_write(20002,value)`.

The periodic capture writes **CAPTURED**, not a native qualification PASS. The Python verifier independently requires:

- One reset request after first-boot native `FE81`, followed by one native transition and the new vector sequence.
- CPU marker read `0`, CPU write `1`, then a post-reset CPU read `1`; one-time initial `A55A` sentinel verified in the full baseline and still present immediately before reset.
- Exactly one post-reset Port C read at instruction `40A2`, before any Port C write; its value must match the CPU store at `40A8` and final RAM.
- Full 4 MiB initial/final/reset RAM comparisons. Only original snapshot bytes, the CPU marker and the actual CPU result may differ at the appropriate phases.
- Native instruction trace showing the prefix twice, original body once, and direct post-reset path `4000,4006,40A2,40A8,40AE`; no second body execution.
- Independent process/execution IDs and consistent source/qualified executable identity. A and B intentionally have different fixture hashes.

Missing, duplicated, ambiguous, host-substituted or contradictory evidence is **BLOCKED**, without tuple deduplication. A confirmed nonzero CPU Port C read is **FAIL only after** the native read/store/RAM/trace chain agrees. Aggregate native PASS requires both independent A and B qualifications. No such runtime result is claimed here. Authentic EmuTOS continuation remains a later separate qualification.

## Actual static results

```sh
PYTHONPATH=tests python3 -m unittest d2_2_gpio_contract_test d2_2_test_verifiers d2_2_r1_test_reset d2_2_r2_test_reset_cpu -v
```

Actual output: **`Ran 76 tests in 11.383s` / `OK`, exit 0**: 40 preserved R1/contract checks plus 36 R2 checks. The R2 cases include forged/duplicate/missing vectors and transitions, host reads/stores/marker changes, wrong vectors, sentinel zero/staleness, lost marker, result/RAM forgery, fixture replay, conflicting read/store values, wrong identities, shared process IDs, corroborated nonzero FAIL, and callback logic with the reset notifier deliberately never called. Lua mocks are explicitly offline callback tests, not another emulator and not native evidence. A result store without vectors cannot complete capture.

Python compilation, complete Lua parsing, `git diff --check`, assembler/disassembler byte comparison, unchanged production/build input comparisons and the non-DIAG CLI guard passed. The no-authorization job gate returned the expected **HOLD / exit 2** without launching anything. Local details remain outside Git under `/workspace/scratch/d2_2_r2`; no generated executable or guest binary is committed.

## One future local Git HOLD job

`tests/hold/007_dana_portc_reset_r2_reuse_diag.job.sh` is pinned to the implementation commit and records its own SHA in `tests/d2_2_candidate_status.json`. It requires new separate authorization and an explicitly supplied existing reference:

```text
DANA_D2_2_R2_AUTHORIZED=YES
DANA_D2_2_R2_BINARY=/absolute/existing/diag/bin/dana-diag
```

The exact qualified binary hash is mandatory before copy and execution. The job checks production/build inputs against `749517b`, creates an isolated DIAG stage, runs offline Python evidence negatives, executes only the same existing DIAG for A/B, independently verifies raw results and archives complete private evidence through the existing outbox transport. **No compilation fallback, new emulator, ROM build, inbox mutation or automatic dispatch.** The SH remains **LOCAL_GIT_HOLD / NOT_UPLOADED / NOT_LAUNCHED**. No prior T authorization carries over.

The existing PR diff is updated by branch push. Direct `gh pr view` API access returned `Forbidden` both normally and with the required escalated retry, so a PR body edit cannot be claimed. This committed report is the review material; native R2 still requires independent authorized execution.

Changed files: `tests/d2_2_gpio_run.py` (CLI delegation only), new `tests/d2_2_r2_gpio.py`, new `tests/d2_2_reset_r2_boot.lua`, new `tests/d2_2_r2_reset.s`, new `tests/d2_2_r2_test_reset_cpu.py`, `tests/d2_2_candidate_status.json`, new `tests/hold/007_dana_portc_reset_r2_reuse_diag.job.sh`, new `docs/D2_2_R2_CPU_RESET.md`, `docs/D2_2_R1_RESET_HARNESS.md`, and `docs/HANDOFF.md`. The qualified A Lua, original tests, all old jobs, source lock, donor and production files remain unchanged.
