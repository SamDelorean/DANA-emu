# D1.1 implementation and T qualification — PASS (build/selectability only)

Base DANA-emu commit: `04fd93a4737abcb7466bdca5e1eb77d5eb1e914a`.
Pinned MAME commit: `c4e48388ca620472643110db2941ce70aa5f3c07`.

## Final supervisor qualification — R5, 2026-10-14

**D1.1: PASS, limited to the minimal MAME driver build/selectability contract.** The exact source candidate `92e39eff050fa7a62486569be6a34994682ce44c` passed independent real T builds of `dana-stable` and `dana-diag` and was integrated into `main` by [PR #5](https://github.com/SamDelorean/DANA-emu/pull/5). The separate English translation was integrated by [PR #4](https://github.com/SamDelorean/DANA-emu/pull/4). D1.2 remains PENDING and needs fresh authorization for executable source and remote testing.

- **R5 Drive evidence package:** [results](https://drive.google.com/file/d/1NLIydtsa6t2XTyeXG4SvleIZI-jfYeo7/view), package SHA-256 `2f697fdffb381b3ed2f82dba596a528a5fa8aa88be07735247b608f64a3847ff`; `dcjob` summary `STATUS=PASS`, exit 0, 4,740 seconds.
- **Stable:** compiled with Clang 21, `PRECOMPILE=0`, sequential `-j3`; binary SHA-256 `ec055d08b66d46181d26cd9371f7f961f52732ad36f468a8aae0a4e1b7bc83d1`.
- **Diag:** separately compiled with identical source, Clang 21, `PRECOMPILE=0`, `DEBUG=1`, sequential `-j3`; binary SHA-256 `dd877c9cb36c491e675b82ce2aba78548519cccf2bd16bf2a9c61cbd3000435c`.
- **Each binary independently passed** `-noreadconfig -listfull asmdana`, `-noreadconfig -listxml asmdana`, and `-noreadconfig -validate asmdana`; one `asmdana` machine registration, valid ROM-less/nonworking XML, exact source pins and preservation of AS2K/AS3K registrations.
- **Host-only failures resolved:** GCC 15 failed internally in GENie (R2); Clang 21 crashed generating the PCH `emu.h.gch` (R4). R5 disabled PCH via the pinned makefile's `PRECOMPILE=0` switch, without modifying MAME source.
- **T working environments:** persistent Dana Git at `/home/spc/Projects/alphasmart/DANA-emu` (tested feature head); pinned donor **read-only** at `/home/spc/Projects/alphasmart/as2k-stable-eeepc900-local/mame-as3k-donor`; completed R5 sandbox `/home/spc/DANA_EMU_ISOLATED/d1_1_clang_nopch_r5_20261014_eUxf5IMU`. T Git checkout is not assumed updated to merged `main` until the next approved job verifies it.
- **Not verified or implemented:** VZ SoC, 4 MiB guest RAM, EmuTOS-Dana image/loader, real CPU clock, LCD, keyboard, MMIO, interrupts, or guest boot. The 1 MHz `M68000` is a registration placeholder and retains `MACHINE_NOT_WORKING | MACHINE_NO_SOUND`.

**Preservation:** The remaining sections describe the original Codex implementation review and pre-R5 expectations. Historical `PENDING` and “not executed” statements below refer **only to the original candidate phase**, not this final qualified status.

The user explicitly authorized this bounded source implementation in Prompt 02.
Issue #3 and its source-access addendum were verified by the technical supervisor,
as reported in that prompt. This Codex environment could not read the issue
itself (API Forbidden, web 404). This is attributed external verification, not
direct verification or a product defect.

## Scope and reuse

The new `src/mame/skeleton/alphasdana.cpp` uses MAME's BSD-3-Clause
`driver_device`, `required_device<m68000_device>`, `M68000`, input/ROM macros and
`COMP` registration. Its 1 MHz clock is only a registration placeholder, not a
Dana timing assertion. The machine is explicitly nonworking and has no sound.
There is no RAM, VZ MMIO, LCD, keyboard, guest loader, storage, GUI or save-state
implementation. No third-party GPL or unverified-license NEO code was copied.

The driver list overlay contains exactly two lines. The preparation helper
inserts them before `@source:skeleton/alphasma.cpp`, rejects collisions and
asserts that removing the insertion restores the original list byte for byte.
Only the new driver and this list insertion alter the staged MAME sources.
Existing MAME/reference checkouts are never build or modification destinations.

## Reproducible preparation (historical Codex recipe; performed later on T in R5)

From the DANA-emu checkout, after execution authorization, choose a **new**
Dana-only destination outside reference checkouts:

```sh
tests/d1_1_build_select_smoke.sh prepare /absolute/path/to/pinned-mame /tmp/dana-d1-1-run
```

The helper reads `git archive` at the exact pinned commit and creates separate
`stable/source` and `diag/source` trees with identical driver bytes and list
patches. It records per-variant source manifests. It refuses an existing root
or a root inside the reference checkout. It does not install or build anything.
Do not point this example at T without separately verifying its paths.

The following commands are the **original unqualified GCC/PCH-enabled Codex recipe**, retained as historical input; they failed on the verified T host and **must not** be used as the qualified T build recipe:

Build sequentially in the corresponding prepared source directories:

```sh
# /tmp/dana-d1-1-run/stable/source
make -j3 TARGET=mame SUBTARGET=danastable SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-stable REGENIE=1 TOOLS=0
# /tmp/dana-d1-1-run/diag/source, only after stable has finished
make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag REGENIE=1 TOOLS=0 DEBUG=1
```

**Qualified T make options (R5):** use the pinned sources and source-list overlay above, compile in separate freshly staged variant directories, and pass the following overrides to **each** command: `OVERRIDE_CC=clang OVERRIDE_CXX=clang++ OVERRIDE_LD=clang++ PRECOMPILE=0` (also `CC=clang CXX=clang++ LD=clang++` in the runner environment). Stable uses `SUBTARGET=danastable BUILDDIR=build/dana-stable`; only after it finishes, diag uses `SUBTARGET=danadiag BUILDDIR=build/dana-diag DEBUG=1`. Preserve `TARGET=mame SOURCES=src/mame/skeleton/alphasdana.cpp REGENIE=1 TOOLS=0` and `-j3`. R5 supplied isolated build logs and hashes in the Drive evidence package; do not assume a new T invocation has been authorized.

Capture each command's actual exit status and separate build logs. Both source
trees come from one snapshot and overlay; there is only one maintained hardware
implementation. Separate trees prevent collisions in generated tools/resources
outside BUILDDIR, including GENie. Never compile the variants concurrently.

Static inspection of `scripts/src/main.lua` shows SOURCES mode uses the subtarget
as project name, a `d` suffix for Debug, and the staged source root as default
executable destination unless SEPARATE_BIN is enabled. On Linux the expected
candidates are `danastable` and `danadiagd`; these names and actual build outputs
were confirmed in the R5 build logs. On a future independently authorized build, discover real outputs again rather than assuming an unchanged layout.
Copy them into distinct final paths `stable/bin/dana-stable` and
`diag/bin/dana-diag`, preserving the source trees and manifests beside `bin`.
Record original output paths and build commands in the external run evidence.

## Binary smoke verification (executed successfully in R5)

```sh
tests/d1_1_build_select_smoke.sh verify \
  /tmp/dana-d1-1-run/stable/bin/dana-stable \
  /tmp/dana-d1-1-run/diag/bin/dana-diag \
  /tmp/dana-d1-1-evidence-new
```

The verifier requires a fresh evidence directory and distinct binary paths and
parent directories. It checks staged manifests/driver/list hashes, exact overlay
insertion, preservation of `asma2k`/`asma3k`, binary existence and executable
permissions. The verify interface needs no reference-checkout argument or mounted
Codex path: each executable must reside in its prepared `VARIANT/bin` directory,
with `VARIANT/source-manifest.json` and `VARIANT/source` retained. The manifest
must identify the pinned commit and correct variant; driver/list hashes must
match, removing the exact Dana insertion must recover the recorded baseline list
hash, and `asma2k`/`asma3k` must each remain registered once. Missing provenance
is BLOCKED; altered provenance or registrations are FAIL. Preparation alone uses
the explicitly supplied reference path through read-only Git commands. Manifest
provenance assumes a trusted preparation run; it is not a signed attestation.

It records separate binary hashes and executes real `-listfull
asmdana`, `-listxml asmdana` and `-validate asmdana` assertions for each variant,
with configuration reading disabled and separate working directories/logs.
XML must identify one expected nonworking, ROM-less Dana skeleton with one
placeholder CPU. A missing prerequisite produces BLOCKED; failed assertions or
commands produce FAIL. Exit codes are PASS=0, FAIL=1, BLOCKED=2.

Pinned `src/frontend/mame/clifront.cpp` explicitly accepts zero or one argument
for `-validate`, passing the argument to `check_all_matching`; therefore the
chosen targeted validation syntax is statically supported. Runtime success was subsequently established for this targeted CLI in R5; **no guest-visible function** is implied. A reduced Dana build need not enumerate AS2K/AS3K: their
registrations are checked in source, with no claim of AS2K runtime regression.
The verifier does not prove independent compilation from binary hashes alone:
separate successful build logs and source-diff guards remain mandatory evidence.
Its PASS describes only executed smoke assertions, never project qualification.

## Initial Codex-only verification (historical; superseded by the R5 qualification above)

Implementation validation is limited to shell/Python syntax, overlay/insertion
checks, and missing-input/failing-command paths. Both variants correctly reported
BLOCKED for missing executables; controlled mock executables returning exit 7
were correctly classified FAIL. The pinned makedep.py sourcesproject and
sourcesfilter commands succeeded on the unchanged alphasma3k reference, not on
a compiled Dana candidate.
Portability correction checks: shell/Python syntax and diff whitespace checks
passed. Five temporary fixtures verified missing binaries/manifests as BLOCKED
and wrong pins, altered registrations and command failures as FAIL for both
variants, with isolated manifests/results. Git was disabled through a test PATH
shim during verification; no reference-checkout access was needed. These fixtures
are harness checks, not successful MAME validation. The PR #5 supervisor comment
could not be read directly (GitHub GraphQL Forbidden); the requested portability
correction follows the user's explicit instructions.

At the **original Codex review stage** no binary smoke, compiler/link test or T execution had been claimed. These were subsequently executed and qualified by T R5 as documented at the top of this file.
The original Cloud environment had GCC/G++ 14.2, Make 4.4.1 and Python 3.12. SDL2/SDL3,
SDL2_ttf, fontconfig, ALSA, PulseAudio and Qt6 development discovery via pkg-config
failed in the audit. No dependencies were installed. Linux defaults to SDL2;
Qt debugger selection and dependencies must be settled in the later build job.
The default SDL3 paths in some platform-specific code are not a Linux requirement.

Previously outstanding T toolchain, both reduced builds, ROM-less/no-screen validation, DEBUG compatibility, binary paths and independent provenance **were resolved in R5**, using the full Drive-first workflow. EmuTOS artifacts were not required for D1.1 and remain unavailable. All previous Commander budgets were exhausted; any new T intervention requires separately scoped approval. **D1.1 is PASS; D1.2 is PENDING.**

## Rollback

PR #5 **has been merged** after R5 qualification, so rollback now requires a scoped new Git revert/PR on `main`, never a reset of the verified T checkout or removal of unrelated branches. Preserve R5 evidence and the Dana-owned completed sandbox. Never reset, clean or modify AS2K or reference workspaces. No future source changes, firmware publication, release, or remote execution are implied.
