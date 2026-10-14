# D0.6 — Frozen first D1.1 MAME reduced-driver candidate

**Status: SPEC_READY (documentation only), 2026-10-13.** This is the final D0 specification increment, not a software implementation or authorisation to execute. **Next: D1.1 PENDING — explicit approval required before changes to executable source or any T/Commander intervention.**

## 1. Single objective, exclusions and decision

**D1.1 objective:** create one new **AlphaSmart Dana skeleton machine driver** and independently compile **two reduced Dana executables from the first build**: **Dana-stable** and **Dana-diag**. Both must enumerate the same driver and share precisely one source/hardware model. Builds and artifacts must be separate from AS2K, AlphaSmart 3000, Palm and DragonBall EZ trees and outputs.

**First-candidate architecture decision:** the D1.1 skeleton uses the existing **MAME M68000 CPU core**, explicitly as a placeholder for machine registration and build verification. It **must not claim to implement a DragonBall VZ**. A dedicated VZ device/MMIO integration is part of D1.3; D1.2 supplies guest RAM first. This is the smallest honest scope under the authoritative sequence, even though DANA ultimately requires the MC68VZ328. A skeleton CPU clock used solely to instantiate the device is an arbitrary test parameter, **not** a measured Dana clock and not allowed as a timing reference in later tests.

**Not permitted in D1.1:** new mc68vz328.cpp/.h, inherited or copied EZ MMIO, virtual RAM, ROM/Flash, EmuTOS loader, synthetic OS calls, CPU debug hooks, LCD, keyboard, ST, SPI, UART, scheduler tweaks, touchscreen, SD, UI, save states, guest-boot claims, upstream MAME submission or publication.

MAME official acceptance is optional. MAME is the only emulator engine; POSE/Retro68 and Neo work remain behavioral references subject to licensing and source provenance.

## 2. Pinned baseline and source ownership

| Property | Frozen choice | Proof / condition |
|---|---|---|
| Product/source-of-change repository | **SamDelorean/DANA-emu**, default branch main | D1.1 will own only its minimal driver overlay, master-list patch specification, and isolated smoke job source (if needed) |
| MAME baseline for compilation | **SamDelorean/mame-as3k @ c4e48388ca620472643110db2941ce70aa5f3c07** | GitHub source lock, **not** proof that a matching checkout or build already exists on T |
| MAME reference: 68000 CPU | src/devices/cpu/m68000/m68000.h | Already imported by existing AlphaSmart 3000 skeleton |
| MAME integration patterns | src/mame/skeleton/alphasma3k.cpp and src/mame/palm/palm.cpp | Read-only templates; **do not edit or fork their device definitions** |
| MAME build/discovery | makefile; scripts/genie.lua; scripts/build/makedep.py; scripts/src/main.lua; src/mame/mame.lst | Verified SOURCE selection path and dependency on the master driver list |
| T workspace | **UNKNOWN — deliberately not invented** | Use a verified, isolated, temporary/staged workspace in the first separately approved productive job |
| OS guest input | **None for D1.1** | emutos.img, emutos-dana.rom and emutos.map have not been built/verified and **do not block D1.1 build/selectability** |

Do not commit a complete copy of MAME to DANA-emu. A future approved test may stage a pinned MAME source archive or read-only snapshot into an isolated work directory and apply the DANA-emu overlay. Never git reset/clean/stash/update the existing AS2K tree.

## 3. Exact D1.1 change allowlist — no source writes in D0.6

### 3A. Product files to create in DANA-emu ONLY after D1.1 approval

| File | D1.1 content permitted | Reason |
|---|---|---|
| **src/mame/skeleton/alphasdana.cpp** | One short machine driver class, required M68000 CPU, empty/input definitions, ROM-less test-only declaration, COMP registration and honest MACHINE_NOT_WORKING / no-audio flags | Machine discovery and skeleton build |
| **overlays/mame-driverlist/alphasdana.lst.fragment** | Exactly two lines: `@source:skeleton/alphasdana.cpp` and `asmdana`, with application point defined below | Reproducible, narrow edit to MAME master driver list; do not vendor the ~50,000-line list |
| **tests/d1_1_build_select_smoke.sh** | Optional short local smoke/verifier for **both** variants. Only build/selectability, list/validate and old-driver integrity checks | Independent per-variant PASS/FAIL/BLOCKED reports; a single passing executable is insufficient |

A standalone self-contained Drive `.job.sh` may be generated separately as a **transient execution artifact**, with source SHA recorded in evidence, once a future D1.1 execution is explicitly approved. It is not part of D0.6 and must not be placed in the shared inbox yet.

### 3B. Only permitted modifications INSIDE an isolated staged MAME candidate

| MAME path | Allowed edit | Absolutely forbidden in D1.1 |
|---|---|---|
| **src/mame/skeleton/alphasdana.cpp** | Add the exact new DANA-emu driver file | Editing alphasma.cpp, alphasma3k.cpp, Palm drivers, internal MAME CPUs |
| **src/mame/mame.lst** | Insert **`@source:skeleton/alphasdana.cpp` then `asmdana`** adjacent to other alphabetically sorted skeleton entries | Rewriting the entire file, removing existing machine names, changing unrelated registration |
| **Generated isolated build files** | Allow MAME's normal isolated build generator to emit target artifacts | Treating generated files as MAME source edits or committing them |

**Shortname:** `asmdana`, chosen to avoid confusion with `asma3k` and `asma2k`. At the pinned SHA the source and shortname do **not** already exist in the master list. If a newer source snapshot has one, stop with a name collision and revise this contract, do not silently overwrite.

**Source integration insight confirmed statically:** in scripts/genie.lua the `SOURCES` mode runs `makedep.py sourcesproject` and `sourcesfilter` against `src/mame/mame.lst`. Therefore creating only the .cpp file without registering the shortname in the master list is insufficient. The registration list is an explicit necessary component, not an optional later polish.

**MAME driver code constraints (source-only, for D1.1):** inherit `driver_device`; instantiate `M68000` as the temporary CPU class; use no required LCD or cartridge/ROM region; no fake 4 MiB RAM, VZ model or arbitrary interrupt response; register as **not working**. A self-contained C++ driver source with minimal machine_config/input/COMP sections is sufficient to establish discoverability. Whether an empty ROM declaration or absent screen passes the pinned MAME validation must be verified by the actual compiled tool rather than assumed.

## 4. Two independent Dana builds from D1.1 (new binding requirement)

**Binding decision of 2026-10-13:** There is **NO single developmental `danadev` executable**. Both named products must be built independently from D1.1 onward, rather than postponing the build split until D6.1. They use **one pinned source snapshot, one Dana driver and one hardware implementation**; no duplicated MAME CPU/SoC code or borrowed AS2K checkout.

The pinned MAME makefile provides `TARGET`, `SUBTARGET`, `SOURCES`, `BUILDDIR`, `DEBUG`, `REGENIE` and `TOOLS`. `BUILDDIR` determines generated/build project paths; the actual produced executable location must be determined from the first build, not guessed. Proposed **sequential** commands, only for a separately approved T job:

```sh
# Isolated Dana source snapshot, not the existing AS2K tree
make -j3 TARGET=mame SUBTARGET=danastable SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-stable REGENIE=1 TOOLS=0
make -j3 TARGET=mame SUBTARGET=danadiag   SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag   REGENIE=1 TOOLS=0 DEBUG=1
```

**Naming:** user-facing deliverables are **Dana-stable** and **Dana-diag** (or lowercase `dana-stable`/`dana-diag` when installed); MAME build subtarget IDs `danastable` and `danadiag` are implementation identifiers, not proof of executable filenames. Explicitly install/copy verified resulting binaries into distinct Dana-only output folders, recording their real names and SHA-256 values. Use isolated configuration, NVRAM, input mapping, guest media, snapshots and test artifacts, with no shared mutable runtime state.

**Differences for D1.1:** both may use the **same skeleton C++ and hardware behavior**. DIAG is initially a **debug-symbol/configuration build**, not a second CPU/device implementation; detailed bounded probes follow their allocated increments. DEBUG=1 is an **unverified candidate configuration**, not proof that this exact revision builds successfully. If unsupported, fix build flags in the same D1.1 build contract; do not omit the second executable or silently defer it to D6.

**Important isolation:** invoke the builds **sequentially**, one at a time with `-j3`, because the underlying MAME source tree and tools may share intermediate/generated resources outside `BUILDDIR`. Separate build directories, final executable destinations and explicit source SHA checks are mandatory. An even stronger option, if the first build exposes shared mutable paths, is **two distinct disposable Dana-only staged source trees** extracted from the *same pinned archive*; both remain entirely independent of AS2K. Never build concurrently until no collision has been demonstrated.

**Acceptance for both builds:** the real generated executable for **each variant** must individually enumerate exactly one `asmdana` driver and report the declared nonworking skeleton. D1.1 is not PASS if only Dana-stable or only Dana-diag compiles. Record variant-specific compile/enumeration/validation results and binary hashes. The exact make syntax, DEBUG behavior, binary paths and ROM-less/no-screen skeleton validity remain unverified until the approved T job runs.

**Later D6.1 does not create the two builds for the first time.** It upgrades already-independent binaries with production launchers, full persistent runtime media isolation and daily-use behavior. The required two-artifact build contract begins at D1.1.

## 5. First approved productive job: ordered stages, no exploratory Commander calls

**Preconditions (not yet satisfied):** explicit user's authorisation for D1.1 code implementation and, separately, actual T/Commander execution with budget; a single approved self-contained job staged through Drive; no conflicting foreign job in the shared inbox.

Future job contract:

1. **PRECHECK:** identify the actual, accessible source revision through read-only Git metadata or a vetted pinned archive; verify required MAME files and toolchain; validate the DANA overlay provenance; check shared Drive inbox occupancy **outside Commander**. If pinned baseline is missing, stop **BLOCKED_SOURCE**, never invent a checkout path, reclone over another tree or reset an existing worktree.
2. **STAGE:** create a unique isolated work area (record its resolved path); obtain read-only pinned source material without changing any existing working tree; overlay the driver and apply precisely the master-list two-line insertion. Record SHA-256 for driver, list, source base and applied diff.
3. **STATIC DIFF GUARD:** assert only the two permitted MAME source paths changed; verify existing `alphasma.cpp`, `alphasma3k.cpp` and `mc68328.cpp/h` bytes match baseline and prior machine list entries remain unchanged. Unrelated edits are automatic **FAIL_SCOPE** and abort before compiling.
4. **BUILD:** run **both independently configured reduced builds sequentially**, each using exactly **-j3** and its own BUILDDIR, capturing per-variant build flags, tools, actual executable path, compile/link status, first error and exit code. Stop on unsafe shared-path collision without modifying AS2K.
5. **ENUMERATE/VALIDATE:** for **each executable**, run real machine enumeration (candidate commands `-listfull asmdana` and `-validate`, verified against MAME revision). Both must list exactly one `asmdana`, with expected source and nonworking status. Existing `asma3k`/`asma2k` entries remain unmodified in master list. No guest run or VZ peripheral claim.
6. **EVIDENCE:** publish per-variant manifest.json, build.log, selected_driver_list.txt, validation.log, binary SHA-256 and result.json, plus shared source diff and master result through Drive. If no guest ran, mark guest-state/trace/framebuffer artifacts `not_applicable`. Preserve separate stable/diag build roots and evidence.
7. **GATE:** only successful source-diff guard, **both independent builds**, **both enumerations** and both validation reports can mark **D1.1 PASS (build/selectability scope only)**. A failed toolchain/launcher/connector is **BLOCKED** with reason; an actual source compile failure is **FAIL_BUILD**. No merge of untested candidate as functional product; record qualified commit and retain rollback checkpoint.

**Regression boundary:** D1.1 must demonstrate that existing source/registration entries were not damaged; full AS2K firmware runtime regression is **not** required or falsely claimed for a source-isolated driver addition. No AS2K binary or checkout may be written. Any unexpected global script/header change requires a new explicit scope decision.

## 6. Future evidence and rollback

**Evidence root:** a unique, Dana-only run bundle under a verified Drive destination, in the format defined by [D0.5](D0_5_DETERMINISTIC_TEST_HARNESS_CONTRACT.md); the shared AS2K queue is only a transport if unoccupied and explicitly authorised, never a destination for unscoped data.

Mandatory first-run evidence:

- Source lock SHAs, checked MAME revision, overlay source SHA, fixture ID, host toolchain/build environment and **both independently built executable SHA-256 values**, or null separately on failure.
- Separate stable/diag generated build/regeneration logs, stage/compile/validation exit codes, configuration and runtime-state directories.
- One-line source-diff scope: exactly `src/mame/skeleton/alphasdana.cpp` and `src/mame/mame.lst`.
- Actual machine list evidence for **both** executables, precisely `asmdana`, and regression inventory of old AlphaSmart MAME entries.
- Result verdict with `overall_status = PASS / FAIL / BLOCKED`, `stage_status` and `reason_code`.
- Reproducible staging script provenance, not just an asserted "it compiled".
- Guest execution evidence `not_applicable`, since D1.1 is an enumerability test only.

**Rollback:** discard only the **isolated candidate work area after preserving its evidence and verifying ownership**, or restore the exact pinned source snapshot **within that isolated work area**; no `git clean/reset` in AS2K, the T's unknown default checkout, or DANA-OS3K. Preserve a DANA-emu branch/candidate identifier and pre-change commit; integrate only after PASS.

## 7. Authorisation and residual risks

**D0.6 approves NOTHING operational.** It only freezes the first future scope. "Siguiente" after D0.6 identifies D1.1 **for explicit implementation authorization**; it does not silently permit executable source edits or carry prior Commander authorisation, and does not imply permission to execute a remote job/compile. Any T use requires a fresh explicit, bounded approval. The universal default maximum is **three Commander calls per authorised intervention**, preferably a single bundled `dcjob launch`; Drive is used to retrieve results, not Commander polling. Host builds use **-j3**.

Open dependencies, without guesswork:

1. Actual accessible MAME snapshot/path, OS/compiler and binary generation on T **unknown**.
2. `emutos.img`, `emutos-dana.rom`, `emutos.map`, exact linked symbols and image hashes **missing**; **not needed for D1.1**, mandatory later D1.4/D1.5.
3. MC68VZ328 MMIO/reset/IRQ/PLL/LCD/SPI implementations **not built**; M68000 skeleton does not implement these.
4. No existing Dana-stable or Dana-diag executables, parity, device traces, guest runtime assertions or test fixtures; D1.1 must produce **two distinct binaries**, but guest parity tests begin later.
5. Two-subtarget command syntax, DEBUG=1 compatibility, shared build-tools safety, produced executable paths and no-screen/no-ROM skeleton acceptability remain **runtime/build checks**, not established results.
6. Third-party GPL software must not be vendored into MAME; only MAME-licensed new code or separately licensed references may be used.

**D0.6 documentary closure criterion:** this document fixes minimal source and registration changes, pinned baseline, source ownership, **two independently compiled Dana-stable and Dana-diag artifacts from D1.1**, independent test/rollback, staged build isolation, failure taxonomy and authorisation boundary. D0.6 is **SPEC_READY (documentary)**, not a compiled candidate.

**Exact next cursor: D1.1 PENDING, not READY or PASS.** No MAME C++ source, SH job, target machine, compiler or Commander tool has been touched.

## Source references

- [MAME pinned source tree](https://github.com/SamDelorean/mame-as3k/tree/c4e48388ca620472643110db2941ce70aa5f3c07)
- [MAME driver list](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/mame/mame.lst)
- [MAME source-filter and generated project logic](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/scripts/genie.lua)
- [MAME generated machine list](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/scripts/src/main.lua)
- [MAME makefile build controls](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/makefile)
- [Existing AlphaSmart 3000 skeleton](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/mame/skeleton/alphasma3k.cpp)
- [DANA-emu D0.1–D0.5 specifications](DANA_EMU_INCREMENTAL_WORK_PLAN.md)
