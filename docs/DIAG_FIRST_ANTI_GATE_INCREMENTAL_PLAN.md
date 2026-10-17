# DANA-emu — DIAG-FIRST incremental plan, anti-gate policy and zero-ramp handoff

**AUTHORITATIVE EXECUTION ROADMAP — user-requested continuity checkpoint, 2026-10-16.**
**Active target:** `dana-diag` only. **Cursor:** `D1.3.1-C` (authorize/launch R6 DIAG-only 32-bit IVR MMIO build and guest evidence; independently verify). **Status:** D1.3.1-B code and test harness STATIC_IMPLEMENTED/UNBUILT; D1.2 prior RAM CLOSE/PASS, no MMIO runtime PASS yet; stable deferred. **Commander: 0 calls in D1.3.1-B; previous 10-call R5 authorization consumed 2 and does not authorize this new remote job by itself.**

Read this document **first** in every new conversation, then [DIAG_FIRST_DEVELOPMENT_POLICY.md](DIAG_FIRST_DEVELOPMENT_POLICY.md), [CANONICAL_CONTINUITY_AND_RULES.md](CANONICAL_CONTINUITY_AND_RULES.md), [WORKFLOW_AS2K.md](WORKFLOW_AS2K.md), [DANA_EMU_INCREMENTAL_WORK_PLAN.md](DANA_EMU_INCREMENTAL_WORK_PLAN.md) for source-backed details. Where the older plan calls for stable/diag parallel builds, dual-binary parity, or stable packaging during development, **this plan and the diag-first policy supersede those requirements**. Preserve old records as history, not active gates.

**CHECKPOINT 2026-10-16 — D1.2-R3.1 CLOSED/PASS (STATIC_ONLY).** Source-backed audit on PR #7 branch `codex/dana-d1-2-ram-bus`: `tests/d1_1_build_select_smoke.sh` dual prepare/verify; `tests/d1_2_run.py` positional stable+diag, distinct-binary guard, dual regression and per-variant loop; `tests/d1_2_verify.py` loops both variants and computes RAM-10 parity; `tests/d1_2_test_verifier.py` has stable-coded observations and parity assertions; `tests/d1_2_boot.lua` accepts generic `cfg.variant` and needs no hardware change; `tests/d1_2_fixture_manifest.json` fixtures remain unchanged. Exact edit sequence: R3.2 DIAG-only D1.1 CLI/provenance smoke; R3.3 DIAG-only runner/verifier RAM-01..09; R3.4 defer RAM-10 and update unit tests; R3.5 prepare one DIAG build SH. No product code change justified by this audit. No Commander, build, Codex, or runtime PASS. **NEXT: D1.2-R3.2.**

**CHECKPOINT 2026-10-16 — D1.2-R3.2 IMPLEMENTED / STATIC_ONLY.** Added `tests/d1_1_diag_smoke.sh` on `codex/dana-d1-2-ram-bus`, commit `67f381f2fa51057bd8bfdd57d27a534e0bde184f`. This is an isolated derivative of the D1.1 historical smoke: `prepare REFERENCE NEW_STAGE_ROOT` stages DIAG only; `verify DIAG_BINARY NEW_EVIDENCE_ROOT` checks one executable, pinned source/driver/list hashes, unique Dana registration, preserved AS2K/AS3K registration, MAME listfull/listxml/validate, CPU and no-ROM metadata. Historical `tests/d1_1_build_select_smoke.sh` is unchanged. Static source checks PASS; **no execution or real binary PASS yet**. R3.3 must update `tests/d1_2_run.py` to invoke this new DIAG smoke. No Commander calls. **NEXT: D1.2-R3.3.**

**CHECKPOINT 2026-10-16 — D1.2-R3.3 IMPLEMENTED / STATIC_ONLY.** On `codex/dana-d1-2-ram-bus`: `tests/d1_2_run.py` commit `d85fb769969591bd638d57a93d20e90986aa59d7` now accepts `DIAG_BINARY EVIDENCE`, invokes `bash tests/d1_1_diag_smoke.sh verify DIAG_BINARY EVIDENCE/d1_1-regression`, and runs RAM-01..RAM-09 only on `diag`; `tests/d1_2_verify.py` commit `87b7b3403e0a62cac5275132069ed3d78d2eca01` independently checks only DIAG and excludes old stable/diag parity from aggregate status. `tests/d1_2_boot.lua` and fixture manifest unchanged. Existing synthetic unit tests are still old dual-variant and **must be updated at R3.4 before qualification**. Static edits verified by source inspection; no Python unit execution, MAME build or guest-runtime PASS yet. No Commander calls. **NEXT: D1.2-R3.4.**

**CHECKPOINT 2026-10-16 — D1.2-R3.4 IMPLEMENTED / STATIC VERIFIED, UNIT EXECUTION PENDING.** On PR #7 development branch: `tests/d1_2_verify.py` commit `99ef13ead45a1dabb013bfaadf9ec8947e047a59` now publishes top-level `deferred_cases.RAM-10.status=DEFERRED_STABLE_PARITY` with `counts_for_pass=false`, **excluded** from aggregate D1.2 result; `tests/d1_2_test_verifier.py` commit `418703eaff9ba63d8da8f46855b4a9a773e4cf84` migrated all normal synthetic observations to DIAG, replaced dual-variant parity test with positive DIAG suite and deferred parity, added negative DIAG-failure propagation and wrong-variant identity tests; retained missing-evidence, bootstrap, CPU-origin, frame and repeat-mismatch tests (**17 unit test methods in source, not yet executed**). `tests/d1_2_candidate_status.json` commit `ed3bb150d23bd0c503d568d7e224b59e384083f3` describes DIAG-only qualification, deferred RAM-10, and pending unit execution. Source fetched again from GitHub and static assertions verified; `tests/d1_2_fixture_manifest.json` blob SHA `e631b7d09c9676c13ed87ba6a8348ca34b54e011` unchanged, 8 fixture sources RAM-01..RAM-08 (RAM-09 is a clean repeat of RAM-01). No Python test execution, guest CPU evidence, T build, Commander or Codex. **NEXT: D1.2-R3.5** — prepare one DIAG-only build SH and arrange local/sandbox synthetic unit execution before launching, without creating a separate artificial approval gate.

**CHECKPOINT 2026-10-16 — D1.2-R3.5 SH PREPARED / BASH+DRIVE SHA VERIFIED; NO DISPATCH.** Source of truth: `/mnt/data/000_dana_emu_d1_2_ram_bus_r3_diag_20261016.job.sh` uploaded to `AS2K_TEMP/COMMANDER_PIPELINE/hold` Drive ID `1isvg7CAph4GHRhvvtXZdBFRLtdWQbmmh`, SHA-256 `396d74b6c49beaa681dddc247ec3b1d1ae1caab2816b1eb5f170bb1856501612`, **12,760 B**; exact Drive readback SHA and `cmp` pass, `bash -n` PASS, one DIAG build/runner only and no stable build. Branch head pinned `ed3bb150d23bd0c503d568d7e224b59e384083f3`; MAME donor pinned `c4e48388ca620472643110db2941ce70aa5f3c07`. Unit tests run within SH before build, pending authorization. The script first reuses SHA-matching R2 DIAG binary from retained T sandbox, bypassing unnecessary ~40-min build, and falls back to one Clang 21 `make -j3` DIAG compilation only if reuse unavailable; verifies original driver blob unchanged (GitHub blob `f192fdafd32d5b87c6c3ff0e5a2446dc9351a676` across prior and current branch commits). Driver SHA guard `ce103ff5cffbba3d9a9b1fc10cd06ce4126fe5d59c5c5970be3417c0bcc73716` matches real R2 evidence. No Commander used. Inbox verified empty before staging; job stored in HOLD to prevent an unattended launch.

**NEWLY RECOVERED R2 REAL-T EVIDENCE:** R2 outbox file `1H-S1YA0zefPFVapawUFe6iQnTUu0j_Ny` (wrapper summary file `16vZPHXvW9ChvymFtUZaoECTVnUaCZpKq`): wrapper `STATUS=FAIL EXIT_CODE=2` while **inner result is `BLOCKED`**, reason `RAM_FIXTURE_OR_RUNTIME_BLOCKED_INSPECT_FULL_EVIDENCE`. Both stable and DIAG MAME builds completed (build rc=0), diagnostic binary SHA `9af8b4216e14e0183352822c9abc5c27a0fc10c1d95f1ddebbc30249adde8c35`, historical D1.1 stable/DIAG smoke PASS. Guest RAM-01 MAME process exited **`-11` (SIGSEGV)** with only XDG_RUNTIME_DIR/ALSA warnings in captured console, and no `observation.json`; no guest RAM case PASSED. 15 **old dual-variant** synthetic unit tests passed, not the newer 17 DIAG-only unit tests. Avoid claiming a hardware defect without traceback. A second execution with same unmodified MAME invocation would be unjustified. **Next action is R3.6 focused static crash triage and minimal evidence-driven correction/command before remote qualification.** The previously prepared R3 SH remains in HOLD, not authorized to launch; if crash-relevant code/args change, revalidate its pinned revision/SHA and replace only the held artifact after review. No extra arbitrary gates; SIGSEGV is a concrete blocker.

**CHECKPOINT 2026-10-16 — D1.2-R3.6 CLOSED / STATIC EVIDENCE TRIAGE; NO PRODUCT PASS.** Correction to preceding R3.5 wording: **R2 RAM-01 SIGSEGV was `dana-stable`, NOT `dana-diag`.** Independent inspection of archived R2 `result/d1_2_runtime.tar.gz` from Drive outbox package `1H-S1YA0zefPFVapawUFe6iQnTUu0j_Ny` found exactly **one** runtime `run.json` (`runtime/stable/RAM-01/run.json`) with `command[0]=.../stage/stable/bin/dana-stable`, `exit_code=-11`, `variant=stable` in its Lua config. No DIAG RAM-01 runtime directory and no `observation.json` were present. Both builds exited 0; D1.1 registration/provenance smoke **PASS** on stable and DIAG. Thus SIGSEGV is localized to a **stable-only execution attempt**, with unknown precise crash cause (no backtrace in output); it is **not evidence of a DIAG runtime failure, RAM model defect, or justification for a new debug gate**. The R3 single-DIAG diagnostic binary SHA `9af8b4216e14e0183352822c9abc5c27a0fc10c1d95f1ddebbc30249adde8c35` passed prior DIAG CLI smoke, but RAM-01..09 have never executed on it. R3 SH in Drive HOLD SHA256 `396d74b6c49beaa681dddc247ec3b1d1ae1caab2816b1eb5f170bb1856501612` was revalidated using `bash -n`; its logic selects DIAG only, runs synthetic tests, uses exact SHA-based reuse, then executes RAM-01 first with fail-fast capture. No script modification or rebuild is justified by stable-only failure. **R3.6 STATIC PASS; next is R3.7 one guarded DIAG run only after explicit Commander authorization**, followed by independent Drive evidence audit. Calls consumed this increment: **0 Commander**. Do not propagate the previous incorrect claim that `dana-diag` crashed. R3.7 does not require any extra technical pre-gate.

**CHECKPOINT 2026-10-16 — D1.2-R3.7 EXECUTED / BLOCKED_HARNESS; CORRECTED R4 EXECUTED / BLOCKED_HARNESS; COMMANDER 5/5 EXHAUSTED.** Under explicit user budget of five Commander calls, the first R3 job `000_dana_emu_d1_2_ram_bus_r3_diag_20261016.job.sh` was enqueued (launcher PID `209726`, worker PID `209854`), independently read from Drive `AS2K_TEMP/DANA_EMU/D1_2_RAM_BUS_R3_DIAG/d1_2_r3_diag_20261016_0KcMzR50` (folder `1aPzSmxoprvNyxSbASrtMxtuIKcDwGzHY`). `result.json`: BLOCKED, `reason=DIAG_RAM_HARNESS_OR_BOOTSTRAP_BLOCKED`, `unit_tests_rc=0`, `ram_runner_rc=2`, `diag_origin=REUSED_VERIFIED_R2_DIAG`. All **17/17 DIAG-only synthetic verifier tests PASS** on real T (0.457s), and D1.1 DIAG CLI/provenance smoke PASS. Actual RAM-01 `observation.json` recorded `BLOCKED_BOOTSTRAP: stack index 3, expected string, received nil`, before `bootstrap_prepared`. Source-backed bug localized precisely using pinned MAME `src/frontend/mame/luaengine_debug.cpp`: `device_debug_type.set_function("bpset", [](device_debug &dev, offs_t address, char const *cond, char const *act){...})`, which disallows the two Lua `nil` arguments. PR #7 branch `tests/d1_2_boot.lua` was patched to `cpu.debug:bpset(pc,"","")` and `cpu.debug:bpset(cfg.breakpoints[i],"","")`, commit `c1436218aa0bb0d0dc4d7b819356c1603114b11d`; no product driver change.

A corrected second job R4 `000_dana_emu_d1_2_ram_bus_r4_diag_20261016.job.sh` was prepared, `bash -n` PASS, Google Drive HOLD readback `cmp` PASS, SHA256 `6ef8b47caa71e1249edb9775015f1f98e2fd5189c5b27c7f187c0bf1a8cd81ee`, then enqueued after inbox-only identity check (launcher PID `210125`, worker PID `210255`). Its real result is in `AS2K_TEMP/DANA_EMU/D1_2_RAM_BUS_R4_DIAG/d1_2_r4_diag_20261016_tCSXxbQh`, Drive folder `1uyHw8ObsBgLvW67HPgSTWd2bWlNC0pLt`, `result.json` file `1yelCpc4aw0FVIysbqQF1B8e5tb1inW7V`, and nested runtime package `1sHAwEG4Y0Nlik5hmvtiXHSGkRfbmL3Mw`. R4 again **17/17 synthetic tests PASS**, D1.1 DIAG smoke PASS, reused verified R2 DIAG binary SHA `9af8b4216e14e0183352822c9abc5c27a0fc10c1d95f1ddebbc30249adde8c35` with no rebuild. R4 RAM-01 now **prepared=true**, genuine native CPU reset vector bus reads at 0,2,4,6 appeared after preparation, PC reached `0x4000`, SP `0x8000`, SR `0x2700`, exactly as expected; however the Lua reset notifier **did not produce an observed event** (`reset_seen=false`). At `boot.lua:117`, the combined assertion `reset_seen and current.CURPC==0x4000 and current.SP==0x8000 and current.SR==0x2700` falsely reports `Initial CPU state/first instruction mismatch`. No guest instruction path was qualified; suite fail-fast left RAM-02..09 unrun. This is a **demonstrated harness contract mismatch**, not a demonstrated product memory failure. Native MAME reset handling and Lua notifier wrappers read at pinned source `src/frontend/mame/luaengine.cpp` and `src/emu/machine.cpp`. Avoid fabricating a notifier: use real CPU vector bus traffic, instruction-state evidence and deterministic ordering as reset proof and keep notifier absence explicit. R4's `final` snapshot is `CURPC=0x4000, SP=0x8000, SR=0x2700`; events include ordered CPU reset-vector reads and instruction fetches. Next atomic task R3.8 is harness validation adjustment, synthetic test updates, and new SH; **all 5 of the user-authorized Commander calls have been consumed; zero remaining**. No T probes/launches without explicit new authorization.

**CHECKPOINT 2026-10-16 — D1.2-R3.8 STATIC IMPLEMENTED; RESET PREDICATE CHECK PASS; REAL GUEST/25-UNIT SUITE PENDING.** Source-backed R4 trace was re-read from `AS2K_TEMP/DANA_EMU/D1_2_RAM_BUS_R4_DIAG` runtime archive: `bootstrap_prepared=true`, `reset_seen=false`, events `seq=9..12` show **native CPU** reads at addresses 0,2,4,6, words `0x0000,0x8000,0x0000,0x4000`, mask `0xffff`, PC=0 after fixture-prepared `seq=8`; initial snapshot `CURPC=0x4000, SP=0x8000, SR=0x2700`. At that point no guest instruction test completed and the old Lua notifier gate falsely raised. Changes committed **only on `codex/dana-d1-2-ram-bus`**: `tests/d1_2_boot.lua` commit `670fc7ba309b658464332c73cbff39bb5de89b38` removes mandatory `reset_seen` from first-state assertion but retains truthful `reset_seen`/events; `tests/d1_2_verify.py` commit `5ddaef9bf0f5b1c58e65077efbbd4e7e286c4224` replaces mandatory Lua reset notifier with ordered, CPU-origin, exact-data and mask native reset vector reads, prestart-preparation ordering, notifier consistency when present, and original PC/SSP/SR assertions; `tests/d1_2_test_verifier.py` commit `c9eeb8e92a9282ec3af3bb254c8963c31f12a1d8` adds positive missing-notifier and optional real-notifier tests plus negative altered/missing/out-of-order/host-supplied CPU evidence and contradictory notifier tests. The revised source has **25 Python unit test methods**, NOT YET RUN; R3/R4 previously passed **17/17 old tests**. Candidate status updated commit `7fcb66aaf1aa419bea7eb3d4d3784cc75f673ae0`; branch head independently confirmed equal to pinned SHA. In a local isolated Python predicate check, the **actual R4 CPU reset bus trace passed** and **four tampered variants were rejected**; this is **not** a full Python unit-suite run or guest-memory PASS.

**R5 JOB PREPARED IN HOLD (NOT DISPATCHED):** `000_dana_emu_d1_2_ram_bus_r5_diag_20261016.job.sh`, **12,993 bytes**, SHA256 `46edc4033168d3a2acb4f279f2508ca006ba68a4c9e36f1a5f371c89aa2d8a5f`, Drive HOLD ID `15T-nJ-eZJDPBNK-sP5EN-tNrDoBY5FVk`. `bash -n` PASS, Drive raw file byte-for-byte `cmp` and SHA PASS. Script is DIAG-only, pinned to exact source and donor, performs current synthetic unit suite before real CPU fixture run, and reuses verified DIAG binary SHA `9af8b4216e14e0183352822c9abc5c27a0fc10c1d95f1ddebbc30249adde8c35` where possible to avoid rebuild. Drive `inbox` confirmed empty; R5 verified in `hold`. Commander **0 calls in this increment**, historical budget **5/5 consumed**; fresh explicit user authorization required. **NEXT EXACT D1.2-R3.9: guarded single R5 launch and independent Drive evidence audit.**

**CHECKPOINT 2026-10-16 — D1.2 CLOSED/PASS (REAL T R5 + INDEPENDENT EVIDENCE AUDIT), NEXT D1.3.1.** The user established **10-call Commander authorization blocks** and authorized the R5 run; budget **2/10 used** (one canonical T `dcjob launch`, one `read_process_output` confirming accepted worker PID `211200`; launcher PID `211072`). One job only: `000_dana_emu_d1_2_ram_bus_r5_diag_20261016.job.sh`, SHA256 `46edc4033168d3a2acb4f279f2508ca006ba68a4c9e36f1a5f371c89aa2d8a5f`, source SHA `7fcb66aaf1aa419bea7eb3d4d3784cc75f673ae0`, MAME donor SHA `c4e48388ca620472643110db2941ce70aa5f3c07`; DRIVE result folder `https://drive.google.com/drive/folders/1CIbxw7nuftqs-M6l7Ap4I0-8MDerHWHV`. R5 `result.json` Drive file ID `1tt1f8pHm2j77C-fTY8mQbca5F0I3-6qg` reports `status=PASS`, `diag_origin=REUSED_VERIFIED_R2_DIAG`, `diag_build_rc=0`, `unit_tests_rc=0`, `ram_runner_rc=0`, `exit_code=0`, meaning **no recompilation**, verified prebuilt DIAG SHA `9af8b4216e14e0183352822c9abc5c27a0fc10c1d95f1ddebbc30249adde8c35`. `d1_2_result.json` Drive file ID `1uHQQ0f7fX79lMzPM0RQH4fXK_sBGE92g`: nine statuses RAM-01..RAM-09 **PASS**; deferred `RAM-10=DEFERRED_STABLE_PARITY` (excluded from status). Unit log confirmed **25/25 synthetic verifier tests PASS**, and `d1_1_diag_regression_result.json` PASS.

**Independent supervisor audit:** separately materialized R5 `d1_2_runtime.tar.gz` from Drive file ID `1GRDUghRLhWgAqsIOHFC4Qb8yXQyfPluz`, verified its SHA256 `76835ff2595d0a23b7bfd25c91bb7e21e19ea1a20e271002a2e5ce67f4fcbc1d` against uploaded `d1_2_runtime.tar.gz.sha256`, enumerated all 9 observation/config/run/verification and 4,194,304-byte initial/final RAM dumps (156 tar members), independently checked exact source and executable identities, fixture byte hashes, native 16-bit CPU-origin reset vector reads at 0,2,4,6 (words 0000,8000,0000,4000), initial PC=4000/SP=8000/SR=2700, complete endpoint/instruction stops, verified 8/16/32-bit values and byte-lane behavior, upper RAM addresses `0x3ffffe`, `0x3ffffc`, `0x3fffff`, full RAM dump guard integrity, native vector-3 address-error frames at `0x7ff2..0x7fff`, nonaliased unmapped access at `0x400000`, and exact normalized RAM-09 clean repeat of RAM-01. **Independent audit 9/9 PASS.** These confirm **D1.2's synthetic post-bootstrap M68000 4 MiB RAM/bus contract only** — NOT physical Dana reset memory decoding, VZ MMIO, guest EmuTOS, LCD, ST keyboard, SD or OS3K. Verified source result persisted as `tests/d1_2_candidate_status.json` commit `80e88e9967bf6608d102d91682d9b55a9cdd7943` on PR #7 branch. R1/R2/R3/R4 remain historical; do not rerun.

**NEXT EXACT D1.3.1:** STATIC_FIRST review pinned Dana VZ address mapping and native MAME MMIO primitives, define minimal CPU-origin MMIO read/write decode test and source limits; no unneeded gate. The 10-call unit is a per-authorization block, not a blanket grant to spend eight leftover calls on unrelated work.

**CHECKPOINT 2026-10-16 — D1.3.1-A CLOSED/STATIC_PASS; NEXT D1.3.1-B IMPLEMENTATION, NO MMIO RUNTIME PASS.** Static-first review completed against official Motorola [MC68VZ328UM/D](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf) rev. 0, 02/2000, and [MC68VZ328UMAD/D](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf) rev. 7, 10/2001; pinned [D0.2](D0_2_EZ_VZ_REGISTER_CONTRACT.md), [D0.4](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md), Dana-OS3K MMIO inventory and pinned donor `mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`. **Crucial source-backed address-width discrepancy:** current Dana `M68000(config,...)` is 24-bit by default (`m68000.cpp` constructor), whereas VZ MMIO canonical address window is `0xFFFFF000..0xFFFFFFFF`. Native MAME `mc68ez328_device` deliberately sets program/opcodes/user/CPU space widths to **32 bits** and maps `base_internal_map(0xfffff000,map)`, demonstrating reuse architecture only, **NOT equivalent VZ registers/reset behavior**. Motorola's SCR reset is 0x1C with DMAP bit2=1; address alias `0xXXFFF000` exists when DMAP enabled and only `0xFFFFF000` is canonical after clearing DMAP. Do **not** map `0x00FFFxxx` only and call that faithful high-bit decoding. For one minimal guest-origin decode target, official **IVR is 8-bit at `0xFFFFF300`, reset `0x00`**, and pinned EmuTOS-Dana writes `0x40`; no full IRQ behavior implied. **New canonical [D1.3.1 contract](D1_3_1_VZ_MMIO_ADDRESS_DECODE_CONTRACT.md)** was committed to main at `2e2f71f7f295f2a4f492fb7a020637b63d33858b`. It specifies native CPU MMIO-01 (write/read `0x40` at exact high IVR address, selective negative decode checks, real CPU bus events, no register bank or host-faked success), allowed source scope, targeted D1.2 regression RAM-01/RAM-08 and genuine DIAG build only when product code changes. No MMIO C++/fixture implemented yet; no compilation/Commander/remote run. **NEXT D1.3.1-B: code minimal MAME VZ IVR decode+fixture then qualify via an authorized T job. Parent D1.3.1 remains pending functional PASS.**

**CHECKPOINT 2026-10-16 — D1.3.1-B STATIC_IMPLEMENTED, UNBUILT/NOT FUNCTIONALLY QUALIFIED.** On PR #7 development branch, Dana-owned driver `src/mame/skeleton/alphasdana.cpp` now contains a minimal `dana_vz_cpu_device : m68000_device` using the exact **32-bit memory-space configuration** precedent of pinned MAME MC68EZ328, with `DECLARE_DEVICE_TYPE/DEFINE_DEVICE_TYPE` in global scope as MAME `src/emu/device.h` requires. The only mapped new register is **8-bit IVR at `0xFFFFF300`**, initial `0x00`, writes masked `&0xF8`, readback plus real handler `logerror` dispatch markers. **D1.2 4MiB RAM mapping, legacy driver display name and existing fixtures unchanged**; no LCD, IRQ sources, SPI, EmuTOS or unconditional SCR.DMAP alias model. C++ source code last changed at commit `5aed6d591d91f4e431ffb98b726d762876cd4a62`, pinned by the R6 SH.

**Guest/proof harness added:** `tests/d1_3_1_mmio01.s` LLVM MC68000 source; `tests/d1_3_1_mmio01_boot.lua` adapts the already-real-T-validated D1.2 reset/trace bootstrap to 32-bit bus address scope; `tests/d1_3_1_mmio01_run.py` assembles exact guest bytes via LLVM M68k assembler/objcopy, sets MAME DIAG plugins and collects actual guest execution; `tests/d1_3_1_mmio01_verify.py` independently demands real M68000 SSP/PC vectors, canonical high IVR CPU-origin byte write/read (`0x40`), two negative decodes (neighbor and other 4-KiB page), exact handler callback counts, initial/final full 4MiB RAM equality, source/binary/fixture identity and bounded trace; `tests/d1_3_1_mmio01_test_verifier.py` contains **11 new synthetic unit test methods** for false width/masks/origin/readback/dispatch/corruption, which have **not** been executed. These are not host-manufactured acceptance for guest MMIO, and the existing D1.2 25 synthetic test suite remains unchanged.

**One R6 DIAG SH staged in Drive HOLD (never launched):** `000_dana_emu_d1_3_1_r6_diag_20261016.job.sh`, Drive file `103PFOfnlA4Ig7NMOd_uXsUD_tuj8PDF2`, exact **SHA256 `77ef88cf4047f5cd400ac4ed710173f8fa05711272a9c6a378448aa01392d3e2`**, `bash -n` PASS and Drive readback `cmp` PASS, size 13,823 bytes. Pinned product code SHA `5aed6d591d91f4e431ffb98b726d762876cd4a62`; Git branch may advance with non-product status metadata, so SH checks that exact SHA exists and is ancestor of fetched branch, then detached-checks out exact pinned source. It must run the 36 synthetic unit methods, verify LLVM/M68k source assembly **before expensive build**, compile **one newly changed DIAG** with pinned Clang21 `PRECOMPILE=0 make -j3` (no reuse of obsolete D1.2 binary), perform actual guest MMIO-01 and RAM regression after global 32-bit CPU address-space change, archive logs/traces/hashes, and remain fail-fast. Full nine-case RAM regression is deliberate because **CPU-wide address-space width** changed, not an invented D0/D1 re-gate. **No code compiled or executed**. Older two R6 drafts were explicitly renamed `OBSOLETE...` in HOLD; only the file ID above is current. Exact candidate status is `tests/d1_3_1_candidate_status.json` on branch, updated commit `199a345208329805483cf6beb27ea63c82972d07`. **NEXT D1.3.1-C: guarded one-time R6 remote build/execute + independent Drive verification only after new explicit authorization. Commander this increment: 0.**

## A. State of record — resume without rediscovery

- Repository: `SamDelorean/DANA-emu`; development PR [#7](https://github.com/SamDelorean/DANA-emu/pull/7), branch `codex/dana-d1-2-ram-bus`, candidate commit `9a549d1d44b4114ace714b14f6338614bac8afc1`. Do not merge without real diagnostic evidence and user approval.
- MAME donor `SamDelorean/mame-as3k` pinned `c4e48388ca620472643110db2941ce70aa5f3c07` (read-only); source pins and licenses in `research/sources.lock.json`.
- D0.1–D0.6 = **SPEC_READY (documentary only)**. D1.1 = **CLOSED/PASS for historical MAME build/registration/selectability**, not guest functionality. D1.2 = **PENDING**; no real RAM test PASS yet.
- D1.2 candidate maps **4 MiB RAM `0x00000000..0x003FFFFF`**, 68000 big-endian 8/16/32-bit, odd-address exception vector 3, upper-bound and non-alias, repeatability. No new MMIO, loader, LCD, keyboard or firmware work in D1.2.
- R1 dual-build job: exited 1 after 29 s due to Bash `variant: unbound variable` (same-`local` expansion with `set -u`); MAME builds **never started**. Infrastructure/harness error, not hardware failure.
- R2 fixed Bash scope but remained **dual-build**, contrary to new policy. A `dcjob launch` was started (launcher PID `189618`) but no accepted job PID or R2 result was confirmed. The still-queued R2 SH was withdrawn to Drive `hold`, renamed `SUPERSEDED_DUAL_BUILD__000_dana_emu_d1_2_ram_bus_r2_20261016.job.sh` (file ID `1CDP8J3ljlqHcexQkO6WQCh74-nKUwldD`), and readback confirmed `inbox` empty. **Never relaunch R2.** Recheck results if needed before claiming no asynchronous execution.
- Canonical T: `dee0b4b6-578a-41a5-88de-73dbeb808983`; `/home/spc/.local/bin/dcjob launch`; Drive `AS2K_TEMP/COMMANDER_PIPELINE/{inbox,outbox,archive,failed,hold}`. Read Drive folder directly (advanced parent search previously gave false empty results). No Commander for polling. Do not inherit a past Commander budget.
- T paths: `/home/spc/Projects/alphasmart/DANA-emu`, donor `/home/spc/Projects/alphasmart/as2k-stable-eeepc900-local/mame-as3k-donor`, Dana-only sandbox `/home/spc/DANA_EMU_ISOLATED`.
- Proven build strategy: **Clang 21**, `PRECOMPILE=0`, `OVERRIDE_CC=clang OVERRIDE_CXX=clang++ OVERRIDE_LD=clang++`, `SUBTARGET=danadiag DEBUG=1`, sequential bounded `-j3`. Avoid GCC15 ICE and Clang PCH retry. Build **only one DIAG executable**.
- D1.2 tests already present on PR #7: `tests/d1_2_run.py`, `tests/d1_2_verify.py`, `tests/d1_2_test_verifier.py`, `tests/d1_2_fixture_manifest.json`, `tests/d1_2_boot.lua`, `tests/d1_1_build_select_smoke.sh`. The current D1.2 runner accepts both `stable` and `diag`; verifier loops both and RAM-10 compares them. This is **obsolete** and must be changed before R3; never pass the same binary twice to fake parity.
- Actual evidence in Drive, source/decisions in GitHub. No proprietary firmware/ROM, credentials or unrelated projects in Git.

## B. Anti-gate rules (AG-01 through AG-12)

1. **AG-01 — Only real dependencies block.** A gate is permitted only when its absence prevents a specified observable test or creates a concrete safety/integrity risk. Record the precise dependency and evidence. No extra review, approval, re-audit, committee, infrastructure refactor or speculative prerequisite.
2. **AG-02 — Closed work stays closed.** Do not reopen D0.x or D1.1, rerun all prior tests or re-research sources without new contradictory evidence. Regression scope follows affected behavior only.
3. **AG-03 — One bounded increment.** Define objective, source/commit, allowed files, fixture, expected CPU/bus/MMIO/IRQ events, PASS/FAIL/BLOCKED, regression and rollback. No unrelated feature or UI change.
4. **AG-04 — STATIC_FIRST and reuse.** Read pinned manuals, current MAME primitives, Dana VZ references and verified AS2K *methods* before coding; do not transplant HC11/DictROM/banked-RAM assumptions to M68000/VZ.
5. **AG-05 — Proportional qualification.** An isolated memory or UART function needs its own real fixture and impacted regressions, not an already complete OS boot or finished GUI. Source plausibility/synthetic host tests are not guest-runtime PASS.
6. **AG-06 — Localized failures.** Classify separately PRODUCT, HARNESS, BUILD/TOOLCHAIN, INFRA/QUEUE, SOURCE/INPUT. Repair only the demonstrated fault and rerun the smallest sufficient test; preserve unaffected evidence.
7. **AG-07 — Deferred work is not a gate.** Stable, Palm OS, OS3K firmware, USB/IR, SD, cosmetic GUI, broad instrumentation and unneeded peripherals are deferred until a concrete use case requires them.
8. **AG-08 — No fabricated results.** Never report PASS from an SH upload, launcher PID, compile success, host-side fabricated framebuffer, synthetic verifier output, same-binary dual parity, or missing log. Mark missing proof PENDING/BLOCKED.
9. **AG-09 — Preserve regression assets.** Keep deterministic fixtures and hashes; add one case for a newly discovered failure instead of replacing existing accepted cases.
10. **AG-10 — Evidence-first continuity.** After each increment record source SHA, toolchain, binary/fixture SHA, exact test invocation, expected/observed events, result location, outcome and **next single action**. Do not rely on conversational memory.
11. **AG-11 — Explicit bounded remote authorization.** Prevalidate one self-contained SH, check exactly-one-job inbox and SHA, launch via canonical T only when user authorizes and within their call budget; Drive-only results. Never touch foreign queue jobs, donor, AS2K worktrees or physical Dana.
12. **AG-12 — No auto-escalation.** A/B/C/D workers may execute only the approved atomic task. Supervisor A consumes prior results before dispatching next. B distinguishes NEW/SENT/NO_TASK; C independently checks PASS/FAIL/BLOCKED; D only transports an approved Codex prompt. No automatic advance to next technical increment or PR merge.

**State taxonomy:** PENDING (not executed), SPEC_READY (documentary), READY (authorized and prepared), PASS (specified real evidence), FAIL (verified wrong result), BLOCKED (cannot determine product outcome, reason and remedy recorded). A FAIL of the runner is not automatically a FAIL of emulated hardware.

## C. Atomic roadmap — the ONLY current development target is dana-diag

### C1. Immediate D1.2 / R3 — memory and bus

| ID | Single change or action | Completion evidence | Explicit exclusions |
| --- | --- | --- | --- |
| **D1.2-R3.1 — CURRENT** | STATIC_FIRST inspect exact PR #7 runner, verifier, D1.1 smoke, manifest and Lua; enumerate all stable/diag coupling and real DIAG prerequisites | Reviewed dependency inventory and exact edit/test matrix; no T call | No source edit, compile, launch or Codex |
| D1.2-R3.2 | Adapt historical D1.1 CLI/provenance regression to one genuine DIAG executable | Test verifies `asmdana` registration, binary identity and provenance without stable | Do not alter D1.1 historical PASS |
| D1.2-R3.3 | Change runner/verifier for one DIAG binary and RAM-01..RAM-09 | Deterministic fixture and verifier unit tests; no fake CPU observations | No hardware driver changes unless separately justified |
| D1.2-R3.4 | Update RAM-10 disposition and synthetic negative tests | `RAM-10=DEFERRED_STABLE_PARITY` (not PASS); optional same-diag instrumentation-on/off equivalence only if feasible and separately specified | No stable compilation, no passing diag as stable |
| D1.2-R3.5 | Prepare isolated one-build R3 SH | `bash -n`, `set -u` local-scope audit, diff scope, fixed hashes, one Clang21 DIAG build `-j3`, Drive output contract | No Commander or extra worktree |
| D1.2-R3.6 | User-authorized one-job T launch | Verified inbox identity, launch acceptance, real `dana-diag` MAME binary, RAM-01..RAM-09 CPU/bus evidence, diagnostic CLI regression | No duplicate launch or stable build |
| D1.2-R3.7 | Independent result audit and close | Machine-readable PASS/FAIL/BLOCKED, manifest, console, bounded trace, regression, rollback and exact next cursor | No PR merge on unproven result |

RAM-10's historical stable/diag parity is **deferred** until stable activation. If DIAG instrumented/uninstrumented equivalence is technically measurable, scope a separate diagnostic case; it must not silently become a prerequisite for D1.2's memory contract.

### C2. D1 — guest execution foundation

| ID | Atomic capability | Acceptance evidence |
| --- | --- | --- |
| D1.3.1 | MC68VZ328 MMIO address-window decoding | Guest read/write reaches correct register/address |
| D1.3.2 | MMIO 8/16/32-bit access and masks | Byte lanes, ordering and side effects match pinned reference |
| D1.3.3 | Reset values and unsupported accesses | Explicit documented behavior and localized unknowns; no invented MMIO success |
| D1.4.1 | Obtain/build and verify EmuTOS-Dana reference image | Real binary, SHA, source revision, link/load map; do not assume `0x2140` without image check |
| D1.4.2 | Load guest image into RAM | Exact contents, boundaries and entry placement |
| D1.4.3 | CPU handoff to guest | Actual SSP, PC, SR and first guest instruction trace |
| D1.5.1 | Execute until first unsupported peripheral | PC/register/address/operation and reason; identifies next needed component |

**Anti-gate:** the full EmuTOS UI is not needed to pass a single MMIO/register or loader fixture.

### C3. D2 — clock, IRQ, timers, UART

| ID | Atomic capability | Acceptance evidence |
| --- | --- | --- |
| D2.1 | Clock/PLL | Virtual timing and documented clock state |
| D2.2 | Interrupt controller | Mask, pending, vector, acknowledge in guest-visible trace |
| D2.3 | Timer1 | Count/compare/IRQ deterministically |
| D2.4 | UART1 TX | Ordered bytes from actual guest writes |
| D2.5 | UART1 RX | Guest input and IRQ when demanded by actual execution |
| D2.6 | Resume EmuTOS | Guest progresses beyond implemented devices; next fault localized |

**Anti-gate:** RX cannot block TX if the guest currently uses only TX.

### C4. D3 — Dana LCD, 560 x 160

| ID | Atomic capability | Acceptance evidence |
| --- | --- | --- |
| D3.1 | LCD registers | Real guest register writes |
| D3.2 | Framebuffer from guest RAM | 560x160 1-bpp known fixture, 11,200 minimum pixel-data bytes (before stride/padding) |
| D3.3 | Bit/line ordering and refresh | Reproducible pixel comparison |
| D3.4 | Enable/contrast GPIO and register behavior | Guest-driven observable changes |
| D3.5 | First guest-generated EmuTOS image | Capture generated by real guest execution |

**Anti-gate:** no host-painted substitute and no stable GUI required.

### C5. D4 — ST keyboard and SPI2

| ID | Atomic capability | Acceptance evidence |
| --- | --- | --- |
| D4.1 | ST reset/ready/chip-select GPIO | Correct line state transitions |
| D4.2 | SPI2 transfers | Ordered guest-visible transactions |
| D4.3 | ST initialization | Reference-backed protocol response (e.g. `0xAA` where applicable) |
| D4.4 | Key press/release packets | Letters, F1–F8 and release |
| D4.5 | Host key to virtual ST | Real guest consumes event and changes screen/state |
| D4.6 | No-key, multiple-key, reset and bounded queue | Deterministic edge cases |

**Anti-gate:** reuse AS2K's keyboard *testing method*, not its HC11/electrical/protocol model.

### C6. D5 — first interactive milestone

| ID | Atomic capability | Acceptance evidence |
| --- | --- | --- |
| D5.1 | EmuTOS starts | Guest-generated UI, no OS-call interception |
| D5.2 | End-to-end interaction | Host key -> ST/SPI2 -> EmuTOS -> changed guest framebuffer |
| D5.3 | Clean restart | Two reproducible runs |
| D5.4 | Basic redraw/timer/key load | No observed corruption under bounded test |
| D5.5 | Instrumentation neutrality | Same guest behavior with DIAG observation on/off where applicable |

**D5.2 is the first interactive functional milestone.** D5.3–D5.5 are reliability work, not reasons to deny the D5.2 milestone once proven.

### C7. D6 — debugger and observability usability

| ID | Atomic capability | Acceptance evidence |
| --- | --- | --- |
| D6.1 | CPU registers viewer | PC/SR/SP/general registers correct |
| D6.2 | Memory-region map and browser | RAM/MMIO addresses and contents, usable navigation |
| D6.3 | Selectable bounded trace | CPU/IRQ/MMIO/SPI/UART filters |
| D6.4 | Headless automation improvements | Deterministic reports from actual guest execution |
| D6.5 | Save/restore state | Complete repeatable state roundtrip |
| D6.6 | Diagnostic UI/help/menus | Simplified navigation, avoid permanent help footer where it obscures data |

**Anti-gate:** minimum headless probes are implemented when needed earlier; polished debugger UI waits for D6.

### C8. Later optional phases — never block D1–D5

- **D7 SD:** GPIO/card presence, SPI1, sector reads, filesystem, guarded writes, each only when guest needs it.
- **D8 additional hardware:** touch, RTC, power, USB, IR, additional RAM, Palm/Flash — separate demand-driven increments.
- **O0 OS3K guest compatibility:** test only after a verified independently sourced OS3K guest image and separately approved scope; do not implement DANA-OS3K here.
- **S stable activation:** only by user decision after the shared hardware model is functional; derive `dana-stable` from qualified code, simplify UI, disable noisy diagnostics without guest-visible change, independently qualify and package. Stable parity is **future S work**, not a current gate.

**Route critical:** D1.2 -> D1.3–D1.5 -> D2 (required devices only) -> D3 LCD -> D4 keyboard -> D5.2 interactive. The ordering of independent peripheral microincrements may be adjusted **only when actual guest traces prove a different immediate dependency**, with that evidence recorded; this is not license for scope drift.

## D. Minimum increment record (in existing workflow, not a new bureaucracy)

```text
ID / status / base commit:
One objective / permitted files / explicit exclusions:
Pinned reference and relevant existing primitive:
Exact fixture and test invocation:
Expected guest CPU, bus, MMIO, IRQ or framebuffer observation:
Actual result, evidence paths and SHA:
Regression scope and outcome:
PASS / FAIL / BLOCKED (specific cause):
Rollback/base preserved:
Commander calls used and remaining in this intervention:
NEXT EXACT ACTION:
```

For executed increments, retain `manifest.json`, `result.json`, `console.log`, bounded `guest-trace.log` if applicable, fixture/output artifacts and regression summary. **Do not create new review documents for every microincrement** when the existing ledger suffices.

## E. Mandatory new-chat bootstrap (direct continuation)

When the user says **"Continuemos DANA-emu"**, **"siguiente"**, or **"recupera el flujo"**:

1. Read this file and the four canonical references above; retrieve the latest PR #7 and result checkpoint **only to determine whether the cursor has advanced**. Do not assume a new result exists.
2. Restate in one compact sentence the last independently proven state, the active increment and any blocker. Do not re-explain D0/D1 history unless asked.
3. Execute **only** the exact next authorized action. If it is static, proceed without T; if remote execution is needed, check for fresh explicit authorization and call budget. Do not automatically reopen Codex or launch R2.
4. Verify evidence and update the current cursor in this file or a linked authoritative checkpoint before ending. Always leave a precise NEXT ACTION and keep the historical record.
5. User communication in Spanish; repository technical documentation in English.

**CURRENT CURSOR (2026-10-16): `D1.3.1-C` — after NEW explicit user permission for the prepared remote run, verify one R6 DIAG-only job in Drive HOLD (ID `103PFOfnlA4Ig7NMOd_uXsUD_tuj8PDF2`, SHA256 `77ef88cf4047f5cd400ac4ed710173f8fa05711272a9c6a378448aa01392d3e2`) and exactly-one-job empty inbox; move R6 alone into inbox, use canonical T `dcjob launch` and confirm acceptance with bounded Commander budget, then analyze Drive result/archived trace independently. Product source pin `5aed6d591d91f4e431ffb98b726d762876cd4a62`; subsequent branch metadata changes are allowed but job validates exact pinned commit and checkout. R6 preflights LLVM M68k assembler and the 25 old/11 new SYNTHETIC verifier tests before one NEW Clang21 DIAG build; checks D1.2 RAM regression after global CPU address-width change and real MMIO-01 IVR guest CPU data/handler dispatch and 4MiB RAM integrity. DIAG build, LLVM assembly and native tests have NOT been executed. If compiler/assembler evidence fails, classify precise cause; do not generate PASS. Preserve MAME donor and stable. No Commander used this increment.**
