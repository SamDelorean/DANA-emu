# F1-E4 — Post-Port-C authentic EmuTOS continuation

**2026-10-18: F1_E4_STATIC_PASS / NATIVE_PENDING; implementation PREPARED.**
Source-only issue #11, existing branch `codex/dana-d1-2-ram-bus`, draft PR #7.
Clean starting HEAD `4fb362a01b2531701376c22b041d348a5e6608cd` matched the
remote. Canonical main `16bc5cf4d2e5dd09034b209f925191c9009d7d1c` was read,
including its R2.1 native PASS checkpoint
`c5f76ccc45fdc4f3198b75806395a67b648b9c94`. No new emulator or hardware.

## Preserve the genuine baseline

Supervisor-reviewed native R2.1 archive `portc_reset_r21_9bqe2gzh.tar.gz`,
44,411 bytes, SHA256
`b365c0672574383e586f8fac886182811f11281a7e345d65d043ebbd072e8268`,
has 32/32 verified manifest members and independent A/B PIDs 310239/310254 PASS.
This closes Port C save/restore and CPU-origin R-direct reset observation.
Historical R2 remains BLOCKED. This work consumed the supplied full contract
and canonical HANDOFF evidence index; it did not re-download the private archive
or independently repeat that native audit.

The existing DIAG SHA256 is
`d7bcdf513289a73b8a5c7ab1d258eeac45dc8dd6d89dd7d568cf7784900e6fe5`,
compiled from `749517b2f48c9788e5555071561e738017ac5f7c`. All `src`, `overlays`
and `tests/d1_1_diag_smoke.sh` Git identities remain equal to that build source.
Driver SHA256 remains
`6bff19e0ae1e6c7a1f99a86fcfa2fbe235ac096c6624a10f6600fbd8851ddcf0`.
The donor, guest sources, loader, hardware/reset profile and qualified R2.1
scripts/fixtures/jobs are unchanged. No prior native campaign is rerun.

## Existing F1 instrumentation, narrowly extended

`tests/f1_emutos_run.py --post-portc` uses the existing Lua plugin and native
quickload. It accepts only an explicit absolute staged `diag/bin/dana-diag`
with the exact qualified hash and starts **two** processes with distinct PIDs
and execution IDs. It never calls the historical third corrupt-image run in
E4; the original rejection implementation and offline checks remain available.
`tools/f1_guest.py:validate_qualified` is read-only: it checks all four fixed
artifact hashes/sizes, existing manifest, successful original source-pinned
Dana build provenance, generated map, startup branches and native envelope.
Entry `2140` remains verified against actual map/image, not substituted for it.

The Lua audit found that the previous observer could exit inside a memory tap
and silently stop tracing at 512 KiB. Taps now only capture/defer, including
budget/error paths, and never return replacement data. They exclude loader/
host activity and MAME side-effects-disabled debugger reads. The first
unsupported selected byte is latched once with raw event sequence, aligned
bus address, effective byte address, mask, data, kind, tap identity and native
CPU state. Any subsequent CPU bus activity before periodic finalization is
retained as an explicitly marked **deferred tail**. It cannot replace the first
dependency or count as supported guest progress; the CPU is not instructed to
skip anything, and no missing device response is supplied by the observer.

Dependency finalization closes the trace and captures evidence in the periodic callback.
There is no new breakpoint, PC rewrite, mandatory reset notification, or guest
RAM mutation. First-instruction and existing milestone breakpoints are reused.
Debugger milestones are labelled `debugger_observation`; only taps are CPU bus
events. Native loop compression is retained and explicitly declared; the trace
is no longer intentionally sampled/truncated before a dependency. This is a
complete native trace **with MAME loop compaction**, not a claim of expanded
per-iteration instruction logging. Missing startup/crossing/dependency trace
PCs, sampled traces, or overruns cannot qualify.

Bounds: 20,000 bus/milestone events, 4 MiB encoded event budget, periodic trace
budget 4 MiB, independent trace limit 20,000 lines / 5 MiB, native per-file
trace/console/error-log limit 5 MiB, virtual observer bound 5 seconds, emulator
bound 6 seconds, host timeout 180 seconds per process. Exhaustion is BLOCKED,
including an overlong deferred tail. No sampling is substituted to force PASS.

## Independent E4 acceptance

Each run must bind to the current source SHA, unchanged driver hash, actual
process/DIAG identity and pinned guest image/package. It must prove native
reset vectors, map-verified first PC/SP/SR, initial RAM image hash, ordered
`_os_header -> _main -> _realmain` and `_dana_init` when available in the map,
with matching native trace and milestone evidence.

The old stop must be crossed by one actual **CPU write** at `PC=8392`, raw
aligned address `FFFFF412`, mask `00FF`, selected byte **PCSEL `FFFFF413`**,
value zero. A high-lane PCPDEN write, a host event or a trace PC alone cannot
substitute. Python independently scans every captured CPU bus transaction to
find the **first** unsupported selected byte, requires it after that crossing,
matches every dependency field to its raw event and corroborates its PC in the
post-crossing trace. A single run is `OBSERVED_UNQUALIFIED_SINGLE_RUN`.

Only two genuine independent runs with identical pinned source/binary/guest
and agreeing normalized dependencies produce `REAL_PROGRESS_PASS_SCOPED`.
Normalization retains address/effective lane, kind, mask, selected data and
CURPC/PC/SR/SP/IR; raw data and all other diagnostic registers remain preserved.
Both complete raw bus prefixes are also returned and their equality is reported;
unrelated timing/diagnostic differences do not fabricate a new dependency.
No PFSEL address or next PC is hardcoded as an expected outcome.

Missing, forged, duplicate, contradictory or non-repeatable evidence is
`BLOCKED_HARNESS`; unavailable/corrupt guest input, no new dependency within
the bound, or an address outside the confidently identified VZ window is
`BLOCKED_GUEST`. Without a new dependency, valid milestones and proven PCSEL
crossing are retained without declaring boot PASS. Unsupported peripherals are
not PRODUCT_FAIL. The E4 verifier does not infer a product malfunction from
missing evidence; actual offline assertion failures remain FAIL of the harness.
All results explicitly retain `full_boot=false`.

## Source/path/commit to verified claim

| Pinned source | Lines / claim used |
| --- | --- |
| `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b`, `bios/dana.c` | 42-82: register widths/addresses; 201-215: interrupt prefix and PLLFSR; 270-276: PCSEL, then PCPDEN, then PFSEL in screen initialization. PFSEL is source order, not a new native result. |
| Same pin, `bios/dana.h`, `bios/dana2.S`, `bios/screen.c` | Header 21-27: Dana entry points; assembly 16-21, 67+: later UART/timer/contrast references; screen line 756: Dana-specific VRAM sizing. No implementation imported. |
| Same pin, `util/danaboot.S` | 35-42: historical image copy/jump to `2140`; map/envelope still independently checked. |
| `davidgiven/dbztool@d32702383c2ea3523ea58599c52345435c74e900`, `danainit.sh` | 16-19: software bootstrap PCSEL/PCPDEN zero; not a physical reset rule. Script read only, never run. |
| `SamDelorean/mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`, `src/mame/skeleton/alphasma3k.cpp`, `src/devices/machine/mc68328.cpp` | Existing EZ/AS3K foundation and individual register maps/IVR mask; no assumption of identical Dana board or EZ PLL behavior. |
| Same MAME pin, `src/frontend/mame/luaengine_mem.cpp:270-299`, `luaengine.cpp:1577`, `src/emu/emumem_het.cpp` | Tap callbacks may replace data only if they return it; read taps see native result, write taps precede handler. Side-effects-disabled exclusion and deferred finalization preserve native handling. |
| Same MAME pin, `src/emu/debug/debugcmd.cpp:4222-4287`, `debugcpu.cpp:1823-1830,2085-2145` | Native trace/loop compaction, instruction hook and synchronous stream closure on `trace off`. |

All requested source files were accessible at exact pins and read. Their
downloaded SHA256 identities are recorded in candidate status. The mounted
`/workspace/emutos` HEAD was a different source and lacked the pinned object;
immutable raw source files were used instead, without modifying that reference.
No GPL EmuTOS/POSE/Retro68 implementation was copied into MAME. No new register
was observed/implemented, so a new Motorola register contract is deferred until
actual native evidence identifies it. Private binary/map artifacts are absent
from Cloud; their fixed expected hashes come from qualified E1/E2, not a new
local byte verification. Metadata sidecar SHAs were not supplied externally:
the job checks their semantics and records/compares all six original/staged
file hashes before and after execution, without inventing an external hash.

## Executed offline checks and next HOLD job

```sh
PYTHONPATH=tests python3 -m unittest f1_test_guest f1_e4_test -v
python3 -m py_compile tests/f1_emutos_run.py tests/f1_e4_test.py tools/f1_guest.py
bash -n tests/hold/009_dana_f1_e4_emutos_post_portc_reuse_diag.job.sh
git diff --check
```

Actual full-suite output: **`Ran 44 tests in 1.068s` / `OK`, exit 0** (recorded
in candidate status and local `scratch/f1_e4/offline_tests.log`). It includes original input/rejection
checks; forged crossing, swapped lanes, CPU/host substitution, missing/duplicate
events, skipped earlier access, wrong guest/binary/source, corrupted RAM image,
non-repeatable dependency, unbounded/missing trace, false full-boot claims and
same process/ID. Lua-only mocks exercise real observer callbacks, including
deferred errors/budget, first-dependency preservation and host exclusions;
they are not an emulator or native guest proof. The production input gate
explicitly rejects the suite's synthetic artifacts.

The new `009_dana_f1_e4_emutos_post_portc_reuse_diag.job.sh` is **Git HOLD only**.
Its immutable harness source pin is `e38dcbe56dfaba6191de93ebd6d7f85105fb471f`; SHA256 is
`fc75e2f1cb22f4e0c71d4b54cfc08e601163dcb90e394011d28ca84bf02508e7`. Both are in candidate status.
It requires fresh `DANA_F1_E4_AUTHORIZED=YES` and
`DANA_F1_E4_BINARY=/absolute/existing/diag/bin/dana-diag`. Both no-authorization
and old R2.1 authorization tests return HOLD/exit 2 before any Python/T action.
Embedded Python AST and full Lua parsing pass. The job verifies source/build
tree compatibility, stages read-only copies of the exact existing DIAG and six
private guest/provenance files, validates the real map, runs only focused Python
tests and two authentic E4 processes, then independently recomputes results.
There is no MAME/guest/compiler download or build fallback, donor access, prior
RAM/Port C/PLLFSR campaign or third native rejection run.

Complete original observations/traces, native image snapshots, original map,
provenance, source/input hashes and independent comparison go into a hashed
private evidence archive. The archive's job status stays transport-pending
until outbox uploads/checksum readback succeed. A separate `transport_result.json`
receipt completes the job; upload problems return BLOCKED/exit 2 and preserve
local evidence. Only the established private outbox is used; no inbox action.

**Remaining qualification:** real post-Port-C EmuTOS execution has NOT been
performed here. Exact next native dependency is UNKNOWN. Fresh separate native
authorization is required. No emulator, T/Commander, MAME/ROM compilation,
Drive dispatch, binary publication or merge occurred. The known GitHub GraphQL
Forbidden limitation from R2.1 was not repeatedly retried; PR diff is updated
through branch push and this committed report supplies the review material.

Changed files: `tests/f1_emutos_run.py`, `tests/f1_emutos_boot.lua`,
`tools/f1_guest.py`, new `tests/f1_e4_test.py`, new `tests/hold/009_*job.sh`,
`tests/f1_candidate_status.json`, `tests/d2_2_candidate_status.json`, this
report, `docs/D2_2_R2_CPU_RESET.md` and `docs/HANDOFF.md`. All four qualified
guest hashes/sizes, source-file hashes and the final job binding are in
`tests/f1_candidate_status.json`; no guest binary or generated log is in Git.

---

## Historical F1 implementation report (superseded checkpoints below)

The original report is retained for provenance. Its old missing-toolchain,
unimplemented PLL/GPIO, trace-sampling and rebuild instructions are historical;
current native truth and E4 scope are above and in canonical main HANDOFF.

Work order: issue #8. Active product: dana-diag only. Parent implementation:
9de5dfe6b1a06a417ae4384fa48a99c5113dfafe, including the CPU-name correction.
D1.2 remains independently qualified 9/9 PASS; this delivery does not reopen it.
The General Work Plan and DIAG-FIRST policies on main govern this assignment.
No T access, Commander call, Drive dispatch, stable build or PR merge occurred.

## Implemented behavior

The existing native 32-bit-address MAME M68000 and single 4 MiB RAM map are
preserved. A standard MAME QUICKLOAD image device mounts `emutos.dana`. When an
image is mounted, machine reset suspends the CPU before its first timeslice.
The quickload callback validates the complete envelope and image digest before
writing any RAM. On failure the CPU stays disabled. On success it clears RAM,
copies the original linked image, installs reset SSP/PC, sets the documented
synthetic `_phystop=0x400000`, `_warm_magic=0`, clears D/A registers, sets SR=2700,
and resets/resumes the native CPU. PC is fetched through native reset vectors;
there is no host-side execution substitute or CPU interpreter.

No-image operation uses the previous qualified reset/fixture path. Fresh process
boots are required for independent repetition; hot media replacement and save
state with external guest media are not qualified in this delivery.

The 64-byte big-endian DANARAM1 envelope contains entry, base, length, stack,
phystop, low-RAM end, BSS extent, image SHA-1 and profile flags. SHA-256 binds the
original image, booter ROM, linker map and complete envelope in the external
manifest; native MAME's existing SHA-1 helper also detects changed image bytes
inside the quickload callback. The loader is not a signed software distribution
format. All inputs must pass `f1_guest.py validate` before execution.

The loader requires the map-confirmed pinned R-direct entry/base 0x2140, stack
below low RAM/image, bounded BSS and at most 4 MiB RAM. It does not emulate Palm,
physical Flash reset or the historical DanaRun unsafe 256 KiB block table.
The original booter is preserved/hashed as an input artifact, not executed in
R-direct mode. Its embedded image must exactly match the linked `emutos.img`.

The native IVR remains intact. The initial interrupt configuration prefix adds
16-bit ICR and word-lane-correct 32-bit IMR/ISR/IPR. Masks/reset state follow the
D0.2 VZ contract, Motorola register definitions and existing MAME interrupt-word
handler pattern. ICR includes edge/polarity bits, IMR combines selected lanes,
and ISR acknowledges only edge-enabled external sources. No interrupt source
is invented: pending is zero because timer/UART/GPIO IRQ producers are not yet
implemented. This is not a complete VZ interrupt controller.

PLL, timer, UART, GPIO, LCD, ST and SD remain genuinely unmapped. Based on the
pinned guest's `dana_init`, the next expected unsupported transaction after the
implemented interrupt prefix is PLLFSR at 0xFFFFF202. **That is a source prediction,
not an observed functional dependency.** The runner records whichever actual
unsupported transaction the CPU makes first, with PC/SR/SP, direction, lanes
and data. It never fabricates PLL alternation, UART readiness or OS calls.

## Source reuse and implementation references

- Pinned MAME c4e48388ca620472643110db2941ce70aa5f3c07:
  `imagedev/snapquik.h/.cpp` for standard quickload lifecycle, timer and callback;
  `m68000.cpp` reset/state machinery; `mc68328.cpp/.h` for native word register
  handling; `util/hashing.h` for SHA-1; `output.h/.ipp` for native loader-ready
  output; `debugcmd.cpp` native trace; existing qualified DIAG Lua harness.
- Pinned EmuTOS 9c42ef0f2c2fa9d1e217fced9da68901b2326e8b:
  real Makefile dana target, startup.S, memory.S, dana.c, emutos.ld, tosvars.ld
  and util/danaboot.S/.ld. Original guest sources are built only in isolated
  output; no GPL implementation was copied into MAME code.
- Completed D0.1–D0.5 contracts and Motorola VZ UM/addendum links therein.
  POSE pinned M68VZ328Hwr.h was consulted for ICR edge/polarity definitions;
  the recorded Retro68 Dana references remain the authority for later board
  peripherals. No NEO/POSE/GPL peripheral implementation is pasted here.

## Actual guest build contract

```sh
python3 tools/f1_guest.py build /absolute/pinned-emutos-checkout /absolute/new-guest-output
# An already-installed matching bare-metal ELF toolchain is also supported:
# ... --prefix m68k-elf-
```

The helper checks the exact source SHA, archives it into a new private build
area, checks the actual compiler/mshort multilib, runs `make -j3 dana`, records
compiler/options/status and retains actual emutos.img, emutos-dana.rom, emutos.map.
No reference checkout is cleaned or built in place. Native MiNT is preferred;
ELF=1 is used only with the actual m68k-elf toolchain. Linux m68k GCC with no
mshort runtime is rejected, not relabeled as a qualified guest compiler.

`f1_guest.py package DIRECTORY` requires a successful recorded original build
provenance (it does not infer a source SHA from filenames), validates build outputs and creates the
manifest/container; `validate DIRECTORY` rechecks sizes, SHA-256, linker symbols,
startup branches, native envelope and image bytes. `_realmain` is a local label
that need not appear in GNU maps: its exact target is decoded from the built
`_main` BRA.w, and checked against a map symbol if present. The first header
BRA.s must reach the actual exported `_main`. Missing/ambiguous maps, wrong
entry, bounds, stack overlap, booter mismatch and corruption are rejected.

## First real guest execution test

```sh
python3 tests/f1_emutos_run.py /absolute/diag/bin/dana-diag \
    /absolute/guest-output /absolute/new-evidence
```

The native loader, not Lua, initializes the guest. The test-only plugin installs
breakpoints/taps before the machine starts. The loader-ready native output marks
fixture writes as distinct from CPU operations. Native reset word fetches at
0,2,4,6 must match actual linked stack/entry. The first instruction must have
PC=_os_header, SP=_stktop and SR=2700. The initial RAM image is read independently
and must exactly match the original guest SHA-256.

Native debugger instruction trace and actual `_main`/`_realmain` breakpoint
snapshots corroborate instruction execution. Optional meminit/BIOS/dana_init map
symbols become further one-shot breakpoints. Vector-table reads/writes and MMIO
transactions retain CPU state/lane data; the final stack is retained for exception
inspection. No instruction/register/guest memory modifications are performed by
the observation harness. The native exception engine remains untouched.

The instruction trace uses native loop compaction and an explicitly bounded
prefix (sampling ends at 512 KiB); milestones/MMIO continue afterward. Event
limits are 20,000 / 4 MiB, virtual execution at most 5 seconds at the placeholder
clock, host timeout 180 seconds, and native per-file safety limit 5 MiB. An
oversized/incomplete trace cannot qualify execution. The verifier requires real
trace PCs at the three startup labels, not a host PASS string or exit 0.

Two fresh processes must reach the same normalized CPU/MMIO boundary. A third
negative run corrupts the mounted envelope payload: the native callback must
reject its digest and produce no guest instruction trace. Missing bootstrap or
unavailable inputs are BLOCKED, contradictory executed assertions FAIL. Actual
startup can be PASS for its narrow observed scope while overall delivery remains
BLOCKED_HARDWARE at an actual missing VZ device. No full EmuTOS boot is claimed.

## Qualification job and R7 reuse

One complete job is retained in `tests/hold/000_dana_f1_emutos.job.sh`, HOLD only.
It pins the implementation commit, checks out an isolated source copy, builds
and validates the exact guest, runs existing Python checks, and compares the
production driver with R7 before choosing reuse or a DIAG-only rebuild.
Because this delivery changes production code, R7's known binary SHA
5df95ba18e34580de8f33872c8fb343e67953108cd8c19133c966dbe5c4b5a70 cannot contain
this loader/register prefix; rebuilding is necessary. There is no speculative
rebuild for the old CPU-name harness correction.

Only Clang 21, PRECOMPILE=0, DEBUG=1, make -j3, separate Dana-owned DIAG staging
are allowed by the job. Existing DIAG CLI, real MMIO-01 and targeted RAM-01/RAM-08
regressions are retained. Both authentic guest repeats and native corrupt-load
rejection follow, with logs/hashes/result JSON and a final archive uploaded via
the documented rclone outbox route. The job never dispatches itself. Uploading
or executing this local HOLD script remains a separate authorized action.

## Executed local validation and exact blockers

- Native driver C++20 `-fsyntax-only -Werror` against the pinned MAME headers
  passed, including actual image callback, address-map delegate and output APIs.
- Pinned makedep sourcesproject successfully discovered the reduced driver and
  image-device dependencies in an isolated read-only source view.
- 14 new input/verifier tests passed; 25 qualified RAM verifier tests and 11
  MMIO verifier tests passed unchanged. These use synthetic evidence and prove
  test behavior, not real guest execution. Python/Lua/shell checks are recorded
  in the local report; no source donor was modified.
- The exact EmuTOS source was retrieved. The installed host had no MiNT or
  bare-metal cross compiler. A private, signature-verified Debian cross-GCC14
  extraction was investigated: its `-print-multi-lib` reports only the default
  ABI, not mshort. ELF-mode compilation additionally encountered GCC internal
  compiler errors with -mshort; an -fno-ivopts diagnosis proceeded to an ABI-
  sensitive format error. This unsupported Linux cross compiler is **not** used
  to manufacture accepted guest artifacts. The final build helper honestly
  reports BLOCKED_TOOLCHAIN (m68k-atari-mint-gcc unavailable).
- No emutos.img, emutos-dana.rom or emutos.map was successfully built or validated.
  No image sizes/hashes or observed guest dependency are invented.
- No compatible DIAG executable exists in Cloud; R7 is on T and was not accessed.
  Thus first guest execution, native rejection and runtime regressions are UNRUN.

Precise next step: provide a compatible installed MiNT (or bare-metal m68k-elf)
compiler with mshort runtime, then independently authorize the single HOLD job
on T. It will build the genuine image and changed DIAG executable and collect
actual startup/dependency evidence. Qualification is BLOCKED_TOOLCHAIN and
BLOCKED_EXECUTABLE_MISSING, not a guest hardware PASS/FAIL.

Rollback: revert this bounded F1 source change on the existing branch. Preserve
independent D1.2 evidence and 9de5dfe6. Never reset/clean AS2K or donor checkouts.
Generated guest binaries, package and large logs stay outside Git; no release or
binary publication is authorized by this candidate.
