# Port C continuation candidate — issue #9

## Manufacturer verification after network authorization — 2026-10-17

**RESOLVED: the two official Motorola/NXP PDF documents are accessible and were independently read.** The earlier `CONNECT 403` limitation documented below describes Codex's **former sandbox**, not the current validity of the reference material. Preserve that provenance but **supersede every earlier `BLOCKED_SPEC` claim concerning the PCPDEN/PCSEL register-reset and writable-mask contract**.

Primary authority: [MC68VZ328UM/D, Rev.0](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), §§10.4.3.4–10.4.3.5, Tables **10-15 and 10-16**, PDF pages **183–184** (0-based 182–183), and programmer memory map in chapter 3. Checked against [MC68VZ328UMAD/D, Rev.7](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf): its GPIO/LCD mnemonic erratum changes `LFLM` to `LFRM`, but it does **not replace the PCPDEN/PCSEL reset values or byte widths**.

| Register | Manufacturer address | Width | Physical hardware reset | Allowed byte bits | Meaning |
| --- | --- | --- | --- | --- | --- |
| **PCPDEN** | `0xFFFFF412` | 8 bits | **`0xFF`** | **7–0 rw** | `0` disables, `1` enables each Port C pull-down resistor. |
| **PCSEL** | `0xFFFFF413` | 8 bits | **`0xFF`** | **7–0 rw** | `0` connects dedicated peripheral function; `1` selects GPIO signal. |

The source code **intentionally does not emulate a cold boot**. Its `portc_reset()` value `0x00` is the **synthetic R-direct post-bootstrap software profile**, justified by pinned dbztool `danainit.sh` configuring both registers to zero before the RAM guest. **Do not silently replace it with `0xFF` on the currently qualified R-direct path**, which would change the fixture's bootstrap contract. A future separately scoped cold-reset implementation must start at physical `0xFF`, then execute the required software transitions.

**Scope now verified:** exact addresses, byte width, writable 8-bit masks, reset values, and documented bit meanings. **Not claimed:** physical pin voltages, analog resistor network, actual connected LCD frame signal, or full GPIO data/direction multiplexing. Keep those models separate from the register latch contract. The verified bit semantics support the already written minimal independent `u8` handlers; no production code rewrite or ROM rebuild is needed solely for this specification issue.

**Boundary of subsequent testing:** native `dana-diag` build and CPU-origin guest continuation remain **UNRUN**. A real PASS still requires the future T job's own tests and independent Drive evidence; resolving the manual access does not manufacture a runtime PASS.

**Status: source and isolated checks complete; native DIAG UNRUN; manufacturer contract BLOCKED_SPEC.**

Continue `codex/dana-d1-2-ram-bus`, draft [PR #7](https://github.com/SamDelorean/DANA-emu/pull/7), from `4494a7e702244e744d21908a4661550a86f560de`. The branch was advanced with a fast-forward, preserving CPU-name correction `9de5dfe`, the independently qualified RAM/bus, interrupt prefix, loader and PLLFSR. Canonical instructions were read from `main@ba40acd7b50a2322398cf0e0493228d4f3b255d0` where absent from this feature branch. [Issue #9](https://github.com/SamDelorean/DANA-emu/issues/9) supplies the current work contract. E1/E2/E3/D2.1 remain closed under the latest canonical HANDOFF; no old guest or toolchain build was repeated.

## Scope and specification limitation

Two individually decoded eight-bit configuration registers are implemented with native MAME handlers:

| Register | Address | Modeled reads/writes | Modeled reset | Physical reset and limitations |
| --- | --- | --- | --- | --- |
| PCPDEN | `0xFFFFF412` | Eight independent pulldown-enable configuration bits; full `0xFF` storage mask; readback without read side effects | **R-direct software profile `0x00`**, from pinned dbztool | **UNVERIFIED** against Motorola. POSE initializes `0xFF`; this is secondary emulator evidence only. Actual resistor/pin voltages are not modeled. |
| PCSEL | `0xFFFFF413` | Eight GPIO/dedicated-function selection bits; full `0xFF` storage mask; readback without read side effects | **R-direct software profile `0x00`**, from pinned dbztool | **UNVERIFIED** against Motorola. POSE initializes `0xFF`; MAME's EZ/classic reset differs. PCDIR/PCDATA and connected LCD pin signals remain unsupported. |

These are configuration latches in the existing synthetic RAM/post-bootstrap machine, **not a completed physical GPIO or cold-reset model**. `machine_reset()` explicitly reapplies the R-direct profile, just as this machine already supplies preconfigured RAM. It does not claim Motorola resets either register to zero. Both bytes are registered with MAME `save_item`. Native `u8` address handlers delegate high/even, low/odd and spanning-word accesses to MAME's existing bus decoder; there is no manual byte swapping or generic MMIO RAM.

The official [MC68VZ328UM](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf) and [MC68VZ328UMAD](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf) were both requested before editing. The cloud proxy returned **HTTP CONNECT 403 Forbidden** for `www.nxp.com`, which is absent from the enforced allowlist. Neither PDF was obtained. Therefore this delivery **does not satisfy manufacturer-backed physical reset/mask/electrical qualification** and cannot claim complete issue #9 acceptance. No section number, reset measurement or erratum is invented. A saved environment draft adds `www.nxp.com` and Drive API destinations; it requires user review/save and publication and has not changed this runtime's policy. The pending manual/addendum comparison must confirm or correct the full-byte mask and pin effects before physical-model acceptance.

The remaining initialization is intentionally not guessed. The pinned guest path in `screen.c` calls `dana_screen_init()`: `PCSEL=0`, `PCPDEN=0`, PFSEL read/modify/write bit0, PKSEL read/modify/write bits7/4, PKDATA read/modify/write bits7/4, followed by LCKCON/LPICF/LVPW/LXMAX/LYMAX/LPOLCF/LACDRC/LPXCD/LRRA/LPOSR and contrast. **PFSEL, PKSEL, PKDATA and LCD remain unmapped.** Their detailed VZ masks/reset/pin contracts could not be independently established from the manufacturer here. In particular PKDATA is a pin/direction/multiplexer read, not an output latch that may safely return a fabricated ready value. The next source-predicted dependency is PFSEL `0xFFFFF42B`; **no new CPU execution has established the next actual dependency**.

## Bus-observer correction

The canonical D2.1 report identifies raw tap address `0xFFFFF412`, mask `0x00FF`, data `0x00`, PC `0x8392`, twice. The pinned M68000 uses a **16-bit big-endian space**, and Lua forwards the native tap's aligned address/data/mask unchanged. Consequently the active low byte of that transaction is **`0xFFFFF413` (PCSEL)**. A PCPDEN byte write would have active mask `0xFF00`. This interpretation agrees with the guest's PCSEL-before-PCPDEN source order; it is a **source-derived lane correction**, not a new audit of the unavailable private runtime archive. D2.1's PLLFSR qualification is preserved.

`f1_emutos_boot.lua` now retains raw address/data/mask plus selected `byte_addresses` and `width_bits`. It checks **every active byte** against the exact native decode list, including read-only IPR restrictions. A word touching an implemented byte and an unmapped neighbor stops at the latter. Dependencies include `effective_address`; raw fields remain available for comparison with prior evidence. No replacement read data, CPU mutation or guest patch is added.

## Source-to-claim evidence

All secondary source files below were actually retrieved at the stated immutable commit before editing. Their code was consulted for behavior only; no GPL implementation was copied into the BSD driver.

| Authority / immutable source | Files and findings | Claim and boundary |
| --- | --- | --- |
| Motorola MC68VZ328UM + UMAD, official links above | Neither PDF accessible: cloud network policy 403 | Highest authority; **physical reset, exact writable/reserved masks and corrected electrical details remain unverified**. No POSE reset is promoted to manufacturer truth. |
| [EmuTOS `9c42ef0`](https://github.com/davidgiven/emutos/tree/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b) | `bios/dana.c` definitions and complete `dana_screen_init`, `dana_setphys`, contrast and ST paths; `bios/dana.h`; `bios/screen.c` caller | PCPDEN/PCSEL byte addresses and real initialization sequence. Software writes do not prove physical reset. GPL-2.0-or-later; guest unchanged. |
| [POSE `97b1071`](https://github.com/cloudpilot-emu/pose-original/tree/97b10711fe4ca50c1bd47072378eaab26ba8e81d) | `SrcShared/Hardware/EmRegsVZ.cpp/.h`; `SrcShared/Palm/Platform/Core/Hardware/IncsPrv/M68VZ328Hwr.h`: Port C offsets `410/411/412/413`; initial `00/00/FF/FF`; PCPDEN/PCSEL standard read/write handlers; data reads combine SEL, DIR, inputs and dedicated function | Supports separate configuration storage, not a dummy data page. No independent physical reset proof. GPL-2.0-or-later; no source copy. |
| [Retro68 `d917b67`](https://github.com/csnover/Retro68/tree/d917b67b16bef7bcf5c75a74f617710c32addcbc) | `PalmUtils/poser/SrcShared/Hardware/EmRegsVZAlphaSmart.cpp/.h`, `EmRegsVZ.cpp`, `EmSPISlaveSTMicro.cpp`: PK7 display, PK4 backlight, specialized PK input/direction and ST communication | Actual Dana-specific wiring differs from generic GPIO and NEO. No PKDATA constant, ST handshake or LCD success is fabricated. GPL-2.0-or-later; no source copy. |
| [dbztool `d327023`](https://github.com/davidgiven/dbztool/blob/d32702383c2ea3523ea58599c52345435c74e900/danainit.sh) | `danainit.sh`: PCSEL, PCDIR, PCDATA, PCPDEN configured to zero before RAM entry | Supports **software post-bootstrap profile zero**, never physical reset zero. Script was read, never executed. BSD-2-Clause. |
| [MAME `c4e4838`](https://github.com/SamDelorean/mame-as3k/tree/c4e48388ca620472643110db2941ce70aa5f3c07) | `src/devices/machine/mc68328.cpp/.h`, `src/devices/video/mc68328lcd.cpp`; also `src/devices/cpu/m68000/m68000.cpp`, `src/frontend/mame/luaengine_mem.cpp`, `luaengine.cpp` | Reuse native byte maps, CPU/bus, save-state, debugger, scheduler and Lua taps. EZ/classic reset is not VZ reset; no VZ PCPDEN exists in that donor mapping. Generic LCD primitive is available for a separately specified display model. Per-file BSD-3-Clause; donor source only, never executed. |

Local reference MAME `/workspace/mame-as3k` is exactly the pinned commit. The pinned reference snippets are kept outside Git in `/workspace/scratch/d2_2_sources`; their retrieval inventory is local audit material. No reference checkout or source lock changed. The optional modern cloudpilot cross-check was unnecessary for the supported two-byte scope and was not retrieved.

## Verification interfaces and limits

From the repository root:

```sh
python3 tests/d2_2_gpio_contract_test.py
python3 tests/d2_2_test_verifiers.py
python3 tests/d2_1_pllfsr_contract_test.py
python3 tests/f1_test_guest.py
python3 tests/d1_2_test_verifier.py
python3 tests/d1_3_1_mmio01_test_verifier.py
```

**69/69 local tests passed**: 4 Port C contract checks, 12 adversarial verifier checks, 3 PLLFSR checks and 50 unchanged input/RAM/MMIO checks. The Port C contract compiles the actual production C++ handlers and exercises all 65,536 byte pairs; the real Lua classifier is executed via Lua 5.4 for both lanes, mixed words, unmapped neighbors, read-only writes and aliases. Synthetic records used by verifier tests are explicitly labeled and are **not native execution evidence**. Driver `g++ -std=c++20 -fsyntax-only -Werror` against pinned MAME headers, Python compilation and both Lua chunk syntax checks also passed. These checks do not build or run an emulator.

Future native interfaces (staged absolute **`.../diag/bin/dana-diag` only**):

```sh
python3 tests/d2_2_gpio_run.py /absolute/stage/diag/bin/dana-diag /new/portc-evidence
python3 tests/f1_emutos_run.py /absolute/stage/diag/bin/dana-diag /validated/guest /new/guest-evidence
python3 tests/d2_2_qualify.py /new/guest-evidence /validated/guest
```

The focused fixture uses actual M68000 instructions for byte/word readback, lane independence, 24-bit aliases and unmapped neighbors; compares the complete 4 MiB RAM before/after; retains native vector reads and instruction/bus traces; exercises native MAME buffer save/load and a soft reset. Host bootstrap/save/reset observations have a distinct origin and cannot substitute for CPU transactions. Native API problems are BLOCKED; incorrect register/RAM restoration is FAIL. The fixture has 90-second host and 1-second virtual limits and bounded trace files. Its machine code is test-owned, not a private ROM.

The continuation verifier independently reruns the F1 evidence verifier, requires two real guest zero writes to **both effective byte addresses**, native corruption rejection, normalized repeatability and a corroborated first unsupported byte. A raw low-lane event can never count as PCPDEN. The qualification remains scoped to R-direct behavior; it cannot certify manufacturer reset or full EmuTOS boot.

## Single future qualification job

`tests/hold/005_dana_portc_native_diag.job.sh` adapts the proven D2.1 job. It is bound to the implementation commit recorded inside it, MAME `c4e4838`, and the four already authenticated EmuTOS hashes. It has an explicit `DANA_D2_2_AUTHORIZED=YES` execution gate and must remain **HOLD only** until separate authorization. Do not execute the gate on T without that authorization.

The job reads the donor's pinned Git object without checkout mutation, prepares only `SUBTARGET=danadiag`, builds with LLVM21 and `make -j3`, copies the linked `danadiagd` to the single staged `diag/bin/dana-diag`, runs the focused fixture plus smoke/RAM-01/RAM-08/MMIO-01, then two fresh immutable guests and corrupted-image rejection. It does not rebuild guest images or a toolchain. Lua-only contract checks can use an isolated shared Lua 5.4 library compiled from the pinned donor's bundled sources; that is a logic-test dependency, not another emulator. The result archive includes hashes, process commands, native CPU/bus traces, full focused RAM guards and the next actual dependency. Actual native profile progress and unresolved manufacturer qualification have separate result fields. Even successful native progress leaves overall **BLOCKED_SPEC** until the primary contract is verified.

**No native executable is available in this cloud checkout, no T/Commander call was made, and no emulator ran.** The Drive connector is unavailable and `rclone listremotes` reports no configured remote. Thus the new SH is **LOCAL_HOLD_NOT_UPLOADED_NOT_LAUNCHED**, not in Drive HOLD or inbox. Do not claim the required private Drive placement was completed. The prepared job uses the existing canonical outbox workflow only after authorized execution. The user must enable the saved network draft via review/save/publication for future NXP retrieval; private Drive also needs an existing authorized connection.

Remaining work: verify UM+AD against the candidate contract, place/read back the exact job in private Drive HOLD, obtain separately scoped T authorization, compile and execute DIAG, then audit the genuine first unsupported device. No new hardware dependency or native PASS is claimed in this delivery.
