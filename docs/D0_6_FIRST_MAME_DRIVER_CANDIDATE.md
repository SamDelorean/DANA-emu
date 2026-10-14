# D0.6 — Frozen first D1.1 MAME reduced-driver candidate

**Status: SPEC_READY (documentation only), 2026-10-13.** This is the final D0 specification increment, not a software implementation or authorisation to execute. **Next: D1.1 PENDING — explicit approval required before changes to executable source or any T/Commander intervention.**

## 1. Single objective, exclusions and decision

**D1.1 objective:** build and enumerate one new **AlphaSmart Dana skeleton machine driver** in a minimal MAME target without disturbing the existing AS2K, AlphaSmart 3000, Palm or DragonBall EZ implementations.

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
| **tests/d1_1_build_select_smoke.sh** | Optional short local smoke/verifier invoked by the separately authorised job. Only build/selectability, list/validate and existing-driver integrity checks | Independent reporting rather than relying on a successful shell exit alone |

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

## 4. Minimal target build: proposal to validate on the first approved T run

The pinned MAME Makefile exposes **SOURCES**, **SUBTARGET**, **REGENIE**, **TOOLS** and **-j**. scripts/genie.lua confirms SOURCE-filtered projects; scripts/src/main.lua generates a filtered driver list. The following is a **candidate command**, NOT a command already executed:

`make -j3 TARGET=mame SUBTARGET=danadev SOURCES=src/mame/skeleton/alphasdana.cpp REGENIE=1 TOOLS=0`

**D1.1 must first check** that this combination is accepted by the actual pinned snapshot/toolchain on T, that only the intended driver is selected, and that the output executable's actual path/name can be obtained from generated build logs. **Do not hardcode a presumed `mamedanadev` path** in a runner. If this exact build mode fails because of build syntax or environment, classify **BLOCKED_BUILD_INFRA** and fix the build fixture without broadening driver implementation.

The first build is **one developmental reduced target** (`danadev`). The final stable/diag variants are a D6.1 product milestone. The eventual split should reuse one C++ hardware core while placing configs, trace output, RAM/ROM/SD media, NVRAM and snapshots in separate roots; instrumentation must not modify guest-visible behavior. D1.1 does not need two separate executables yet.

## 5. First approved productive job: ordered stages, no exploratory Commander calls

**Preconditions (not yet satisfied):** explicit user's authorisation for D1.1 code implementation and, separately, actual T/Commander execution with budget; a single approved self-contained job staged through Drive; no conflicting foreign job in the shared inbox.

Future job contract:

1. **PRECHECK:** identify the actual, accessible source revision through read-only Git metadata or a vetted pinned archive; verify required MAME files and toolchain; validate the DANA overlay provenance; check shared Drive inbox occupancy **outside Commander**. If pinned baseline is missing, stop **BLOCKED_SOURCE**, never invent a checkout path, reclone over another tree or reset an existing worktree.
2. **STAGE:** create a unique isolated work area (record its resolved path); obtain read-only pinned source material without changing any existing working tree; overlay the driver and apply precisely the master-list two-line insertion. Record SHA-256 for driver, list, source base and applied diff.
3. **STATIC DIFF GUARD:** assert only the two permitted MAME source paths changed; verify existing `alphasma.cpp`, `alphasma3k.cpp` and `mc68328.cpp/h` bytes match baseline and prior machine list entries remain unchanged. Unrelated edits are automatic **FAIL_SCOPE** and abort before compiling.
4. **BUILD:** execute the bounded reduced make invocation using exactly **-j3**, capture build tool versions, command, output executable path, compile/link status, first error and exit code.
5. **ENUMERATE/VALIDATE:** run actual built executable's machine enumeration (candidate commands `-listfull asmdana` and `-validate`, to be checked against the installed MAME revision). Verify exactly one `asmdana` entry, owner/source association and correct not-working status; existing `asma3k`/`asma2k` definitions must still be present in the staged master list. No guest execution, image loading or claim of VZ peripheral support.
6. **EVIDENCE:** publish manifest.json, build.log, selected_driver_list.txt, validation.log, scope_diff.patch, integrity hashes and machine-readable result.json through Drive. If no guest ran, mark all guest-state/trace/framebuffer artifacts `not_applicable` — never fabricate them.
7. **GATE:** only a build, source-diff, enumeration and validation with objective evidence can mark **D1.1 PASS (build/selectability scope only)**. A failed toolchain/launcher/connector is **BLOCKED** with reason; an actual source compile failure is **FAIL_BUILD**. No merge of untested candidate as functional product; record qualified commit and retain rollback checkpoint.

**Regression boundary:** D1.1 must demonstrate that existing source/registration entries were not damaged; full AS2K firmware runtime regression is **not** required or falsely claimed for a source-isolated driver addition. No AS2K binary or checkout may be written. Any unexpected global script/header change requires a new explicit scope decision.

## 6. Future evidence and rollback

**Evidence root:** a unique, Dana-only run bundle under a verified Drive destination, in the format defined by [D0.5](D0_5_DETERMINISTIC_TEST_HARNESS_CONTRACT.md); the shared AS2K queue is only a transport if unoccupied and explicitly authorised, never a destination for unscoped data.

Mandatory first-run evidence:

- Source lock SHAs, checked MAME revision, overlay source SHA, fixture ID, host toolchain/build environment and **actual** built executable SHA-256, or null on failure.
- Generated build/regeneration logs; stage/compile/validation exit codes separately.
- One-line source-diff scope: exactly `src/mame/skeleton/alphasdana.cpp` and `src/mame/mame.lst`.
- Actual machine list evidence, precisely `asmdana`, and regression inventory of old AlphaSmart MAME entries.
- Result verdict with `overall_status = PASS / FAIL / BLOCKED`, `stage_status` and `reason_code`.
- Reproducible staging script provenance, not just an asserted "it compiled".
- Guest execution evidence `not_applicable`, since D1.1 is an enumerability test only.

**Rollback:** discard only the **isolated candidate work area after preserving its evidence and verifying ownership**, or restore the exact pinned source snapshot **within that isolated work area**; no `git clean/reset` in AS2K, the T's unknown default checkout, or DANA-OS3K. Preserve a DANA-emu branch/candidate identifier and pre-change commit; integrate only after PASS.

## 7. Authorisation and residual risks

**D0.6 approves NOTHING operational.** It only freezes the first future scope. "Siguiente" after D0.6 identifies D1.1 and may prepare the requested source change in Git, but **does not carry any earlier Commander authorisation** or imply permission to execute a remote job/compile. Any T use requires a fresh explicit, bounded approval. The universal default maximum is **three Commander calls per authorised intervention**, preferably a single bundled `dcjob launch`; Drive is used to retrieve results, not Commander polling. Host builds use **-j3**.

Open dependencies, without guesswork:

1. Actual accessible MAME snapshot/path, OS/compiler and binary generation on T **unknown**.
2. `emutos.img`, `emutos-dana.rom`, `emutos.map`, exact linked symbols and image hashes **missing**; **not needed for D1.1**, mandatory later D1.4/D1.5.
3. MC68VZ328 MMIO/reset/IRQ/PLL/LCD/SPI implementations **not built**; M68000 skeleton does not implement these.
4. No live stable/diag parity, device traces, guest runtime assertions or test fixtures exist.
5. Subtarget command syntax/output path and no-screen/no-ROM skeleton acceptability remain **runtime/build checks**, not established results.
6. Third-party GPL software must not be vendored into MAME; only MAME-licensed new code or separately licensed references may be used.

**D0.6 documentary closure criterion:** this document fixes minimal source and registration changes, pinned baseline, source ownership, target build proposal, independent D1.1 scope validation, isolated staging/reversal, failure taxonomy and authorisation boundary. D0.6 is **SPEC_READY (documentary)**, not a compiled candidate.

**Exact next cursor: D1.1 PENDING, not READY or PASS.** No MAME C++ source, SH job, target machine, compiler or Commander tool has been touched.

## Source references

- [MAME pinned source tree](https://github.com/SamDelorean/mame-as3k/tree/c4e48388ca620472643110db2941ce70aa5f3c07)
- [MAME driver list](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/mame/mame.lst)
- [MAME source-filter and generated project logic](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/scripts/genie.lua)
- [MAME generated machine list](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/scripts/src/main.lua)
- [MAME makefile build controls](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/makefile)
- [Existing AlphaSmart 3000 skeleton](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/mame/skeleton/alphasma3k.cpp)
- [DANA-emu D0.1–D0.5 specifications](DANA_EMU_INCREMENTAL_WORK_PLAN.md)
