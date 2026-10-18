# D2.2-R1 — independent native Port C save/restore and reset qualification

> **2026-10-18 checkpoint:** Independent native review reports A PASS, B BLOCKED/VIRTUAL_TIMEOUT despite vectors and fixture replay. This R1 document is historical. [R2](D2_2_R2_CPU_RESET.md) preserves qualified A and uses a CPU marker/read/store/STOP path for B, without requiring the absent post-reset callback or a post-reset breakpoint. R2_STATIC_PASS / NATIVE_PENDING; no new native execution or production change.

**2026-10-17 local. Harness implementation and offline checks complete; native R1 qualification PENDING.** Continue `codex/dana-d1-2-ram-bus`, draft [PR #7](https://github.com/SamDelorean/DANA-emu/pull/7), from `e9a71dbbac609197aa84042081bfde842a516d4b`. No production source, register handler, reset profile, guest, toolchain or reference checkout changed.

## Trigger and bounded correction

The independently reviewed original [D2.2 archive](https://drive.google.com/file/d/1emoamiFbzPFi1RrIWf5Oy1d0D6UQEkOj/view), SHA256 `414cf94089dd0571cd91dcbd275de247227f15aedc702d5f202038803d9a941b`, used source `749517b2f48c9788e5555071561e738017ac5f7c` and DIAG SHA256 `d7bcdf513289a73b8a5c7ab1d258eeac45dc8dd6d89dd7d568cf7784900e6fe5`. The supplied/canonical review reports successful compilation, preserved regressions, correct native Port C transactions/RAM and restored `FE81`, followed by **BLOCKED / VIRTUAL_TIMEOUT**, phase `reset_pending`, with no verified `profile_reset`. Those facts are reused; the private archive was not fetched again here. The result does not establish a PCPDEN/PCSEL product defect or a completed reset.

The old harness had two source-confirmed hazards: its unguarded `register_prestart` callback reran initialization and installed additional taps on every soft reset, and it requested a scheduler-driven reset immediately after synchronous buffer restoration, whose MAME wrappers explicitly warn about timer/synchronization problems. Repeated vector observations and replayed instructions cannot distinguish those effects from one complete verified reset. The precise runtime interaction is not claimed as independently reproduced in this cloud task.

The corrected runner launches **two fresh sequential processes of the same staged DIAG binary**, with different process IDs, execution IDs, plugin directories and raw evidence. Both use the **unchanged original 144-byte fixture**, entry `4000`, endpoint `408C`, stack `8000`, original RAM snapshots and alias/neighbor controls.

- **A / `save_restore`:** original CPU lane/word/readback sequence, complete RAM comparison, actual native `buffer_save`, intentional host mutation to `CDEF`, native `buffer_load`, verified restoration of `FE81` and full RAM. Finish immediately; no soft reset follows load.
- **B / `reset`:** no buffer save/load. Independently verify initial profile `0000`, execute the original fixture to native `FE81`, save final RAM, mark an explicit reset request and call MAME `soft_reset`. The one-shot initialization guard records a new native pre-reset epoch without reseeding memory, changing CPU registers or reinstalling taps. The post-device reset notification reads the profile before fixture replay. The process then allows real vector fetches and stops at the original entry breakpoint before executing the fixture again. Full post-reset RAM must equal the pre-reset final RAM.

Both physical manufacturer resets remain **FF**; the tested synthetic R-direct software profile remains **00**. The Motorola verification already recorded in [the Port C contract](D2_2_PORTC_IMPLEMENTATION.md) is preserved, not reopened.

## Pinned source-to-claim evidence

All MAME paths below were read from the actual local donor at **`c4e48388ca620472643110db2941ce70aa5f3c07`**, verified with `git rev-parse HEAD`. These are source observations, not a new native execution.

| Pinned MAME source | Verified behavior | Consequence for this correction |
| --- | --- | --- |
| [`luaengine.cpp:736`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/frontend/mame/luaengine.cpp#L736), `:853–856`, `:981`, `:1026` | `register_prestart` populates `LUA_ON_PRESTART`; `attach_notifiers` registers its callback **first for MACHINE_NOTIFY_RESET**, and exposes the separate Lua reset notifier. | Prestart is not startup-only. Initialization/tap installation must be guarded; subsequent prestart is a genuine native reset-transition observation. |
| [`machine.cpp:282`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/emu/machine.cpp#L282), `:330`; [`mame.cpp:106`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/frontend/mame/mame.cpp#L106); `machine.cpp:822–839,935–939` | Device reset callback is registered before `manager.update_machine()` attaches Lua notifiers. First callbacks are prepended; normal callbacks retain registration order. | Lua prestart runs before `reset_all_devices`; Lua reset notification runs afterward. Read the actual register state in the latter before CPU replay. This ordering was checked, not assumed from API names. |
| [`machine.cpp:522`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/emu/machine.cpp#L522), `:1035–1047,1124`; [`device.cpp:346`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/emu/device.cpp#L346) | `schedule_soft_reset` schedules a zero-time timer, resumes and eats CPU cycles. Actual `soft_reset` enters RESET and invokes notifiers; device traversal resets root and children. | A host request is not completion. Require separately recorded request, native transition and post-device state; allow the scheduler to run with the entry breakpoint armed. |
| [`luaengine.cpp:1534`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/frontend/mame/luaengine.cpp#L1534); [`save.cpp:368`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/emu/save.cpp#L368), `:388,455–492` | Buffer wrappers synchronously call actual MAME save-manager serialization/deserialization; both contain explicit FIXME warnings about asynchronous scheduling/timers. Loading dispatches postload callbacks. | Keep genuine serialization and mutation controls in A, but isolate B completely from restoration. No invented host-side register copy substitutes for `save_item`. |
| [`m68000.cpp:399`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/cpu/m68000/m68000.cpp#L399); [`m68000-sdf.cpp:8`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/cpu/m68000/m68000-sdf.cpp#L8); `luaengine_debug.cpp` | Device reset selects `S_RESET`; native reset reads words at `0,2,4,6`, builds supervisor stack/PC and enters supervisor mode with interrupt mask 7. CCR bits can be retained. Native debugger supplies breakpoints/go. | Require a new CPU-origin vector sequence, SP `8000`, PC `4000`, supervisor/mask/trace bits; record SR without incorrectly demanding that reset clears CCR. Never force PC or inject vector transactions. |

## Evidence and acceptance

`tests/d2_2_gpio_run.py DIAG NEW_EVIDENCE` retains its CLI, now producing `save_restore/`, `reset/` and aggregate `result.json`. Each process records its absolute staged `.../diag/bin/dana-diag` path/hash, source commit, fixture hash, PID, execution ID, command, bounded console/instruction trace, raw events, full initial/final RAM, plus `restored.ram` or `reset.ram`.

Raw events retain origin, sequence, reset epoch and request ID. The verifier requires this ordered B chain:

`initial vectors → initial 0000 → CPU fixture/readback FE81 → host reset_request → native reset_transition → native profile_reset 0000 → new CPU vectors → reset_entry 0000/SP8000/PC4000`.

Both vector sequences must independently contain exactly `(0,0000),(2,8000),(4,0000),(6,4000)` with native 16-bit masks. A startup zero, host vector read, unmatched epoch/request ID, copied summary, timer expiry or duplicated callbacks cannot prove reset. Raw duplicate observations are retained and rejected as ambiguous; the verifier **does not deduplicate tuples or invent missing events**. Repeated raw sequence IDs, extra vector sequences or duplicate MMIO callbacks yield BLOCKED. Confirmed incorrect native post-reset register/CPU/vector values yield FAIL. Missing evidence or failed/unconfirmed save/load is BLOCKED; incorrect confirmed restoration or RAM corruption is FAIL. Invalid binary/fixture/source/variant records are rejected. Aggregate PASS requires both verified fresh processes and consistent binary/source/fixture identity.

The original 90-second per-process host limit, one-second virtual limit, 256-event budget and 5 MiB individual file limit remain bounded. No firmware, production hardware or test-owned fixture bytes changed.

## Offline validation

```sh
PYTHONPATH=tests python3 -m unittest d2_2_gpio_contract_test d2_2_test_verifiers d2_2_r1_test_reset -v
python3 -m compileall -q tests/d2_2_gpio_run.py tests/d2_2_test_verifiers.py tests/d2_2_r1_test_reset.py
git diff --check
```

Actual output: **`Ran 40 tests in 3.385s` / `OK`, exit 0**. This includes the previous 16 focused contract/verifier checks and 24 R1 checks. The two Lua lifecycle tests execute the actual Lua chunk through local Lua 5.4 with **explicitly mocked callbacks**, demonstrating A never schedules reset and B does not reseed/reinstall taps. They are not CPU or hardware emulation. Adversarial cases cover absent request/transition/post-request vectors, pre-existing zero, wrong confirmed values, duplicate raw observations, host substitution, wrong binary/fixture/source/variant, save/load failure, full RAM corruption and lack of process independence. Historical RAM/EmuTOS campaigns were not rerun.

Python compilation, full Lua syntax checks (included above), unchanged-fixture comparison against `e9a71db`, and whitespace checks passed. The native driver diff against qualified source `749517b` is empty; `src`/`overlays` Git trees and the DIAG build-preparer blob match. No native emulator or test was launched in this task. **Native R1: PENDING; original D2.2: still BLOCKED until independent runtime qualification.**

## Future job — HOLD, reuse only

`tests/hold/006_dana_portc_reset_r1_reuse_diag.job.sh` is the one prepared R1 job. It pins this implementation's commit internally and requires **separate explicit D2.2-R1 native authorization** plus both environment values:

```text
DANA_D2_2_R1_AUTHORIZED=YES
DANA_D2_2_R1_BINARY=/absolute/verified/existing/diag/bin/dana-diag
```

The reference path must be explicitly supplied, non-symlinked, executable and match the already qualified SHA256 `d7bcdf...e6fe5`. The job reads/copies that binary into an isolated DIAG stage, verifies its hash again, and checks the implementation's production/build trees against `749517b`. Any mismatch is BLOCKED; **there is no build fallback**. It runs Python evidence-verifier negatives, then only the corrected native A/B fixture and an independent aggregate readback. It archives raw evidence, manifests and hashes using the existing outbox transport. It never runs another emulator, builds MAME/ROMs/toolchains, replays old campaigns, touches the inbox, invokes Commander or accesses other workspaces.

The SH is **LOCAL HOLD / NOT UPLOADED / NOT LAUNCHED** in this environment. The old `005` and its Drive evidence remain historical and untouched. Exact source pin/job SHA are recorded in `tests/d2_2_candidate_status.json` after freezing the implementation. Before any future run, review and verify the exact SH in authorized private Drive HOLD and obtain new runtime authorization; no prior budget or authorization carries over.

Git push updates the existing PR's reviewable diff. The direct `gh pr view` API call returned `Post https://api.github.com/graphql: Forbidden`; PR body access/update is unavailable here. No alternative credential extraction or messaging route was attempted. The committed report supplies the review material and precise limitation.

Changed files: `tests/d2_2_gpio_boot.lua`, `tests/d2_2_gpio_run.py`, `tests/d2_2_test_verifiers.py`, new `tests/d2_2_r1_test_reset.py`, `tests/d2_2_candidate_status.json`, new `tests/hold/006_dana_portc_reset_r1_reuse_diag.job.sh`, `docs/D2_2_PORTC_IMPLEMENTATION.md`, new `docs/D2_2_R1_RESET_HARNESS.md`, and `docs/HANDOFF.md`. All other source and historical jobs remain unchanged.
