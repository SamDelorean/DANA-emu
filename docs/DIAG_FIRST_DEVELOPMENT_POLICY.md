# DANA-emu — Diagnostic-first development policy and AS2K operating method

**AUTHORITATIVE USER DECISION — 2026-10-16. ACTIVE IMMEDIATELY.**

This document supersedes any older requirement in this repository to build, execute, compare, or qualify both `dana-stable` and `dana-diag` at every D1–D5 development increment. Read it together with `CANONICAL_CONTINUITY_AND_RULES.md`, `DANA_EMU_INCREMENTAL_WORK_PLAN.md`, `WORKFLOW_AS2K.md`, and `HANDOFF.md`. The project remains a reduced MAME-based Dana hardware emulator, independent of AS2K and DANA-OS3K.

## 1. Active development product

- **Only `dana-diag` is active during development.** All new MAME compilation, guest execution, memory/peripheral qualification, instrumentation, automated regressions and debugging run on `dana-diag` alone.
- **`dana-stable` is deferred** until the user expressly opens the everyday-use/production hardening phase. Do not compile, run, package, install, or modify its interface as part of current increments. Its previously qualified D1.1 binary remains an immutable historical reference, **not** a mandatory current regression target.
- Maintain **one shared, faithful Dana hardware model**, not a diagnostic-only guest-visible hardware fork. Diagnostic instrumentation must be opt-in, bounded, non-invasive, and demonstrably independent of the guest-visible results.
- The diagnostic MAME target has a single canonical Dana-owned build tree/output per active revision. Do not proliferate redundant stable/diag worktrees, executables or build artifacts. Isolated disposable staging is permitted when essential for reproducible jobs, but it must not alter AS2K or the pinned donor.
- Later stable creation should reuse the already qualified common hardware engine and be separately verified for everyday use. It is **not** a D1.2–D5 acceptance prerequisite. Its precise activation increment must be planned and approved then; do not silently reopen the historical D1.1 dual-build gate.

## 2. D1.2 scope and updated acceptance

D1.1 stays **CLOSED/PASS solely for the historical build/selectability contract**. D0.1–D0.6 remain documentary SPEC_READY. **D1.2 remains PENDING**, not product FAIL or PASS.

D1.2's hardware contract is unchanged: 4 MiB RAM `0x00000000..0x003FFFFF`, native M68000 8/16/32-bit big-endian reads/writes, alignment/address-error vector 3, upper-bound and non-alias tests, deterministic repeat, no new VZ MMIO, firmware loader, LCD, keyboard or OS3K work.

**New qualification matrix:**
- Compile only `dana-diag` using pinned Clang 21, `PRECOMPILE=0`, `OVERRIDE_CC=clang OVERRIDE_CXX=clang++ OVERRIDE_LD=clang++`, `DEBUG=1`, `SUBTARGET=danadiag`, and `make -j3` in Dana-owned staging.
- Preserve the D1.1 diagnostic CLI/provenance smoke and execute **RAM-01..RAM-09** against the actual `dana-diag` MAME binary; include fresh-run repeatability and all real CPU/bus/RAM assertions. Do not replace CPU observations with host-side fabrication.
- **RAM-10's historical stable/diag parity check is DEFERRED, not PASS and not a D1.2 blocker.** Replace its development-phase role with a diagnostic instrumentation on/off equivalence check on the **same `dana-diag` hardware binary**, if instrumentation toggling exists and is testable without changing the hardware model. Otherwise record `RAM-10=DEFERRED_STABLE_PARITY` explicitly, and do not count it as a pass.
- A diagnostic-only verifier/runner change is necessary because the current `tests/d1_2_run.py` expects two binary paths and `RAM-10` compares stable/diag. Perform STATIC_FIRST source audit and update runner, verifier, manifest and acceptance documentation **in one separately scoped increment** before the next execution. Do not pass the same binary twice merely to satisfy the old two-binary API or forge parity.
- Actual runtime evidence and independent PASS/FAIL/BLOCKED remain mandatory. No source plausibility or synthetic verifier tests count as a guest-runtime PASS. Regress previously closed **diagnostic** behavior affected by each change.

## 3. AS2K method imported, without importing AS2K hardware assumptions

1. **STATIC_FIRST / stock-first reuse.** Read the current source and authoritative manuals, identify existing MAME primitives, relevant DragonBall VZ/Dana documentation, tested AS2K harness patterns and the pinned donor. Reuse a verified facility instead of duplicating it. Do not assume AS2K's HC11, banking, DictROM, LCD or keyboard architecture matches Dana's M68000/MC68VZ328/ST peripherals.
2. **One atomic increment.** Define objective, current baseline SHA, allowed files, guest fixture, expected CPU/MMIO/IRQ/bus events, non-invasive probes, exact PASS/FAIL/BLOCKED conditions, regressions, and rollback. Close or explicitly block it before opening the next. No speculative gates, side projects, re-audits of CLOSED/PASS, or unrelated feature additions.
3. **Design and verify before Codex.** Freeze a source-backed specification and an emulator test matrix first; use actual `dana-diag` evidence to establish behavior where required. Prepare bounded Codex instructions only for a defined implementation increment; review Codex's diff and requalify it independently. A Codex report is not acceptance.
4. **Local worker roles, when used:** A = Supervisor, chooses and approves exactly the next increment and publishes a bounded SH; B = local executor, distinguishes NEW/SENT/NO_TASK and executes only the approved job; C = independent verification/integration, reports PASS/FAIL/BLOCKED and prepares a Codex prompt if needed; D = transport/injector, forwards only the approved prompt. A must consume the previous result before another cycle. No uncontrolled autonomous advancement.
5. **One canonical diagnostic executable and deliberate instrumentation.** Prefer native MAME debugger, precise PC/register/memory probes, scoped event triggers, bounded traces and machine-readable snapshots. No tap or hook may manufacture guest behavior or modify test outcomes. Headless tests may precede UI work; debug usability improvements must be separate approved increments.
6. **T/Commander/Drive discipline.** Canonical T device ID `dee0b4b6-578a-41a5-88de-73dbeb808983`; canonical launcher `/home/spc/.local/bin/dcjob launch`; shared Drive `AS2K_TEMP/COMMANDER_PIPELINE` has exactly-one-job inbox. Commander is reserved for expressly authorized bounded launches (maximum 3 calls per intervention by default), never polling or exploratory shell probes. Stage one syntax-checked self-contained SH; verify the inbox and SHA; retrieve actual logs/results via Drive; classify infrastructure vs product failures. Do not touch foreign jobs, AS2K worktrees or read-only donor sources.
7. **Durable continuity.** Source, English documentation, decisions and reviewed diffs live in Git; large traces and test evidence live in Drive. Every handoff records exact commit, executable hashes if built, toolchain, job ID, result files, outstanding blocker, next single action and call budget. User conversation remains in Spanish; Git artifacts remain in English.
8. **Scope and security.** No proprietary firmware, private ROMs, personal data, credentials or unreviewed third-party code in Git. No physical Dana writes, no Palm OS diversion, no DANA-OS3K firmware implementation in this repo, no changes to AS2K or other projects.

## 4. Pending R2 dual-build job: superseded, not reusable

R1 `000_dana_emu_d1_2_ram_bus_r1_20261015.job.sh` failed early (exit 1; Bash `variant: unbound variable`) **before MAME compilation**. This was an infrastructure/script error, not a demonstrated product failure.

R2 `000_dana_emu_d1_2_ram_bus_r2_20261016.job.sh` fixed the Bash declaration and was submitted to the shared Drive inbox. A `dcjob launch` command was started as PID 189618, **but no accepted job PID, compilation, archive or result was confirmed**. Its script still requests **both stable and diag**, contrary to the new decision. On 2026-10-16, while the exact R2 file was still in inbox, the file was moved through Google Drive's native metadata update to `hold` and renamed `SUPERSEDED_DUAL_BUILD__000_dana_emu_d1_2_ram_bus_r2_20261016.job.sh` (Drive file ID `1CDP8J3ljlqHcexQkO6WQCh74-nKUwldD`). Drive readback confirmed inbox empty and the renamed file in hold. **Never launch R2 or reuse it as-is.** Recheck archive/failed/outbox for any asynchronous race before drawing conclusions; do not assert no execution occurred merely because the file was moved.

R2 SHA-256 `5079ef6d509439e0e56adaefc3a618036b819c5423b3a89ecf7ab59b27972b4c`; original size 12,399 bytes. Historical dual-build D1.1 PASS remains unchanged.

**Exact next action:** STATIC_FIRST inspect the existing D1.2 runner, verifier, fixture manifest and source, then design a **diag-only R3** with a clear RAM-10 deferred/equivalence disposition. Do not create or launch R3 until its scope is independently reviewed and the user explicitly authorizes remote execution. Do not merge draft PR #7 until D1.2 diagnostic acceptance is supported by actual evidence.

## 5. Deferred stable activation

After the diagnostic emulator can genuinely boot and exercise its intended reference guest with required peripherals, present a separately approved stable-release plan: build from the qualified shared source, strip/disable high-volume diagnostic UI and probes without changing hardware behavior, add everyday-use image/keyboard/display/session controls, and independently qualify functional parity and installation. Preserve this future scope; do not treat it as current work.
