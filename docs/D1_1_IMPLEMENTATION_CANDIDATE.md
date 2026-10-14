# D1.1 implementation candidate — PENDING

Base DANA-emu commit: `04fd93a4737abcb7466bdca5e1eb77d5eb1e914a`.
Pinned MAME commit: `c4e48388ca620472643110db2941ce70aa5f3c07`.

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

## Reproducible preparation (not executed during implementation)

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

Build sequentially in the corresponding prepared source directories:

```sh
# /tmp/dana-d1-1-run/stable/source
make -j3 TARGET=mame SUBTARGET=danastable SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-stable REGENIE=1 TOOLS=0
# /tmp/dana-d1-1-run/diag/source, only after stable has finished
make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag REGENIE=1 TOOLS=0 DEBUG=1
```

Capture each command's actual exit status and separate build logs. Both source
trees come from one snapshot and overlay; there is only one maintained hardware
implementation. Separate trees prevent collisions in generated tools/resources
outside BUILDDIR, including GENie. Never compile the variants concurrently.

Static inspection of `scripts/src/main.lua` shows SOURCES mode uses the subtarget
as project name, a `d` suffix for Debug, and the staged source root as default
executable destination unless SEPARATE_BIN is enabled. On Linux the expected
candidates are `danastable` and `danadiagd`; these names and actual build outputs
remain unverified. Discover the real successful outputs rather than guessing.
Copy them into distinct final paths `stable/bin/dana-stable` and
`diag/bin/dana-diag`, preserving the source trees and manifests beside `bin`.
Record original output paths and build commands in the external run evidence.

## Binary smoke verification (deferred)

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
chosen targeted validation syntax is statically supported. Runtime success is
not established. A reduced Dana build need not enumerate AS2K/AS3K: their
registrations are checked in source, with no claim of AS2K runtime regression.
The verifier does not prove independent compilation from binary hashes alone:
separate successful build logs and source-diff guards remain mandatory evidence.
Its PASS describes only executed smoke assertions, never project qualification.

## Verification and remaining uncertainty

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

No successful binary smoke, compiler/link test or T execution is claimed.
Cloud GCC/G++ 14.2, Make 4.4.1 and Python 3.12 are present. SDL2/SDL3,
SDL2_ttf, fontconfig, ALSA, PulseAudio and Qt6 development discovery via pkg-config
failed in the audit. No dependencies were installed. Linux defaults to SDL2;
Qt debugger selection and dependencies must be settled in the later build job.
The default SDL3 paths in some platform-specific code are not a Linux requirement.

Remaining checks: actual toolchain prerequisites on T, both reduced builds,
ROM-less/no-screen validity, DEBUG compatibility, actual binary paths and
independent build provenance. EmuTOS artifacts are not required for D1.1.
T/Commander execution requires a new explicit authorization and the canonical
Drive-first workflow. D1.1 remains **PENDING**, not PASS.

## Rollback

Before integration, discard or revert only this feature branch's candidate
changes. After any later approved execution, preserve evidence before removing
only the owned disposable staging area. Never reset, clean or modify AS2K or
reference workspaces. No default-branch changes, merge or publication are implied.
