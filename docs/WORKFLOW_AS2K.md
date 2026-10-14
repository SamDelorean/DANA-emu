# Operational directives inherited from the AS2K emulator

**MANDATORY FOR NEW CONVERSATIONS:** [CANONICAL_CONTINUITY_AND_RULES.md](CANONICAL_CONTINUITY_AND_RULES.md). It consolidates the verified Drive operating records, canonical T deviceId, dcjob launcher, three-call maximum subject to new explicit authorization, English Git rule and exact D1.1 checkpoint with two independent Dana builds. No Commander for static documentary work.

**Objective:** produce reduced stable and diagnostic emulators, using MAME as an independent testing platform.

## Authoritative plan

The complete plan, containing atomic increments and their tests, is maintained in [DANA_EMU_INCREMENTAL_WORK_PLAN.md](DANA_EMU_INCREMENTAL_WORK_PLAN.md). **No document-only increment may be marked as functional PASS.** D0.1–D0.6 are SPEC_READY documentation; **D1.1 is pending explicit approval**. Dana-stable and Dana-diag are independent MAME builds from D1.1; this document authorizes no Commander calls.

## Established methodology

**Static reuse → increment design → frozen candidate → explicit execution approval → self-contained job → T → Drive evidence → PASS/FAIL/BLOCKED → integration of PASS items only.**

GitHub hosts source and documentation; it does not replace real compilation and execution on machine T. Upstream MAME acceptance is not required, and GitHub Actions tests do not replace the local test bench.

## Machine T and execution

- T environment: `spc-HP-t640-Thin-Client`, user `spc`.
- Known AS2K working repositories under `/home/spc/Projects/alphasmart`; Ghidra 12.1.3 at `/home/spc/.local/opt/ghidra_12.1.3_PUBLIC`; Ghidra project directory `/home/spc/GhidraProjects`.
- **Do not invent a local DANA-emu checkout path or Dana MAME binary path**: neither has been established and verified.
- For T compilation, the user's policy is **exactly three cores (`-j3`)**.
- Commander requires **explicit authorization**; an approved budget in another workstream or conversation does not automatically transfer.
- Drive transports the single self-contained SH/job, results, failures and evidence. Use the documented real launcher **`/home/spc/.local/bin/dcjob launch`** only after preparing the job and verifying that no more than one job is pending.
- **Do not spend Commander calls** on path exploration, polling, repeated log reading, connectivity testing, exploratory installations, or static information available through GitHub/Drive.
- One job autonomously executes the authorized scope and deposits logs, hashes, a manifest, results, and its verdict in Drive. Temporary areas must be isolated; do not delete or alter other projects' objects.
- No job may write physical Dana firmware or modify AS2K repositories without a separate express instruction.

## Stable/diagnostic separation

- From **D1.1**, compile **two separate Dana-stable and Dana-diag MAME targets**, independently of AS2K, with one shared CPU/hardware source code model; use distinct SUBTARGET and BUILDDIR settings. D6.1 later hardens runtime integration, not the first dual build.
- Isolate executables, profiles, external RAM/ROM images, SD, snapshots, logs and temporary files.
- **Stable:** daily-use experience and session-state controls.
- **Diag:** MMIO/CPU/IRQ/SPI traces, guards/snapshots, machine-readable logs, and test scripts; always opt-in when a probe can produce high-volume output.
- Diagnostic evidence may qualify stable; a DIAG PASS does not replace a stable smoke test.

## Provenance and rights

Record the exact MAME source revision and test-binary hashes. An executable hash establishes provenance; it is not grounds to block a test solely because a legitimately rebuilt executable has another hash. Do not commit commercial firmware or extracted Palm/Dana binaries to GitHub. Do not copy GPL EmuTOS/POSE code directly into MAME without reviewing licenses.

## Existing user references

- [DANA-OS3K: T environment and Ghidra](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/07-ENTORNO-T-Y-GHIDRA.md)
- [DANA-OS3K: reduced emulator directive](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/11-ALCANCE-EMULADOR-REDUCIDO.md)
- [DANA-OS3K: EmuTOS emulator architecture](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/08-EMULADOR-ARQUITECTURA-EMUTOS.md)

These rules apply from preparation through every increment. Do not replace them with an improvised workflow.
