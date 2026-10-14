# D0.4 — Virtual CPU, low RAM, vector and VZ bus entry contract

**Status: SPEC_READY — documentary evidence only.** Recorded 2026-10-13. This contract answers D0.4 without introducing source code, a guest image, a build, T execution or Commander calls. Functional emulator milestones remain PENDING. The next increment after this document is **D0.5** (deterministic test harness and trace format).

## 1. Scope and boot-mode definitions

The first MAME Dana target is a **synthetic post-bootstrap RAM environment** for the historical EmuTOS-Dana guest. This is **not** a simulated electrical reset, a Palm OS boot, or a reconstruction of the real Dana Flash layout.

The two experiments are distinct:

| Profile | Source file | CPU entry | Guarantee / omission |
|---|---|---|---|
| **R-direct (primary)** | Exact-built **emutos.img** | Start of linked EmuTOS image at **__text / _os_header**, expected by the booter at **0x00002140** | A documented host-assisted entry into a guest executing real 68k instructions. No DanaRun, trap bootstrap, or physical reset is claimed |
| **R-booter (secondary)** | Exact-built **emutos-dana.rom** (first-stage + embedded emutos.img) | First-stage **entry** at the actual chosen RAM staging address | Validates the 68k relocation/copy to 0x2140, but still does **not** emulate Palm OS or its allocator; the staging address, incoming CPU state and safe overlap region require separate proof |

**Mandatory source constraint:** the ROM-looking filename does not make either file a physical Flash image. The source loader performs longword **copy**, not decompression, and branches to 0x2140. Both profiles require the **emutos.map from the same build** before they are accepted for execution. Never invent an input image hash, staging address or linked _stktop address.

## 2. Virtual address space and low-memory reservations

The first validated Dana guest RAM configuration is **4 MiB**: **0x00000000–0x003FFFFF inclusive**, with end-exclusive top **0x00400000**. This is explicitly the **post-bootstrap usable RAM profile** stated by EmuTOS-Dana and dbztool, not verified physical reset decoding or a promise that no further RAM exists.

| Address interval / symbol | Meaning | MAME contract / conflict guard |
|---|---|---|
| **0x00000000–0x000003FF** | 68000 exception/vector table: **256 x 4-byte entries**. First two longwords are reset SSP and reset PC when hardware reset is modeled | Writable, big-endian RAM for this profile. Do **not** mark as immutable ROM. Must support writes to individual vectors, including **trap #0 vector 32 at 0x80** and Timer1/user vectors |
| **0x00000380–0x000003FF** | TOS crash-related fixed variables in **tosvars.ld**, overlapping the upper part of the nominal vector table | Treat as guest-owned low RAM. Never overwrite indiscriminately in host test harness |
| **0x00000400–0x000007FF** | EmuTOS/Atari system variables; memory validity/status, pointers, vblank etc. | Writable. Linker .first_stram covers 0x0000–0x07FF; initial values/protocol below |
| **0x00000800–0x00000FFF** | Expected **2 KiB BIOS stack** if built with current low ST-RAM linker placement | **__stkbot / _stktop are the authority from emutos.map**. Protect from booter/image overwrite; do not assume a host hardcoded SSP |
| **from approx. 0x1000 to __low_stram_end** | Linker .low_stram BSS/common and Line-A variables, after stack | Bounds determined by emutos.map; linker asserts that **__low_stram_end <= 0x8000**. Cannot assume all of this space is free |
| **__text = linked image base** | EmuTOS header, branch to _main, executable/rodata payload | Historical booter expects **0x2140**. Require map equality, exact payload length, alignment and range checks before executing |
| **__bss–__ebss** | Guest zero-initialized data, destination of guest meminit | Check in-RAM bounds and no overlap with image or stack; let **guest initialization** clear it |
| **through 0x003FFFFF** | Guest RAM including future heap and LCD framebuffer | Do not assume framebuffer base until guest writes VZ LSSA. Bound accesses based on actual guest memory, not host-only display buffers |
| **0xFFFFF000 MMIO window** | DragonBall VZ internal registers; LCD registers at 0xFFFFFAxx and DRAM regs at 0xFFFFFCxx | **Distinct device-backed bus mapping**, no alias into 4 MiB RAM. Register accesses must be byte-lane/endian correct |

**Key source-derived nuance:** EmuTOS linker declares a **14 MiB virtual ST-RAM region**, but this is linker capacity, **not** the available Dana RAM size. The running Dana port explicitly later sets **phystop = 4 MiB**. An image linking beyond the true 4 MiB must be rejected regardless of linker-region size.

**Another nuance:** EmuTOS itself later writes the first 8 bytes at address zero using the beginning of its OS header on non-Atari hardware and initializes the exception vectors. This is a **guest write to writable RAM**, not an instruction for MAME to reset the CPU or to replace the current PC/SSP.

## 3. CPU and exception-state entry contract

The CPU is MAME's **Motorola 68000-compatible core** as used in the MC68328 family, running in 68k **big-endian** semantics. For the first version, we do not implement an alternative Rust 68k core or mask hardware defects by intercepting EmuTOS OS calls.

| State | R-direct proposal | R-booter proposal | Evidence versus hypothesis |
|---|---|---|---|
| **PC** | **__text / _os_header**, **only after the real map confirms 0x2140** | Address of the real first-stage booter entry **in a non-overlapping RAM staging region** | 0x2140 is grounded by util/danaboot.S; exact map/staging address still **UNVERIFIED** |
| **SR / privilege** | **0x2700 is the specified synthetic initial supervisor/masked-IRQ policy**, subject to a real guest test | The original Palm handoff explicitly writes SR=0x2700 before trap #0, but the full inherited context is not yet reproduced | R-direct SR value is **a design choice**, not a measurement of Dana reset; EmuTOS _realmain itself writes 0x2700 |
| **SSP / A7** | Select verified **_stktop** address from emutos.map, 2-byte aligned and inside RAM; log it. The guest will execute **lea _stktop,sp** in startup | Needs a proven safe stack at entry, then first-stage executes **lea entry,sp**, and EmuTOS later moves to _stktop | Exact numerical SSP **UNKNOWN until map**. Do not borrow a Palm heap pointer as a constant |
| **USP** | Non-authoritative, deliberately initialized deterministic value, log guest changes; exact baseline to be frozen by D0.5 | UNKNOWN inherited Palm state; log rather than invent | Not essential to the first supervisor-only instructions |
| **D0–D7, A0–A6** | Deterministic declared initial fixture values, **not presented as real hardware defaults** | Palm inherited values UNKNOWN except values explicitly overwritten in loader | Do not write magic host answers into registers to force success |
| **VBR** | 68000 exception table physically rooted at **0x00000000** (no 68010+ VBR). Watch illegal-instruction handling during EmuTOS attempted MOVEC | Same 68000 vector architecture | bios/startup.S temporarily writes illegal-instruction vector at **0x10** then attempts MOVEC; MAME must produce a true illegal-instruction exception on 68000 |
| **Reset mechanism** | MAME synthetic post-reset **entry configuration**: either seed SSP/PC vectors before CPU reset or set CPU state via the standard MAME state interface after device reset. Choose one **and record it** in D1; ensure VZ device/MMIO init precedes guest fetch | First stage may require trap #0 vector/stack setup equivalent to Palm handoff; do not assume stock MAME power-on entry | A synthetic loader/reset bridge must be explicit in test metadata, never implied as real physical reset |

**Early exception hazards that require a real test:**

1. **Illegal instruction vector at 0x10** must be writable and used by the core when the 68000 attempts MOVEC VBR/CACR. The guest's handler jumps onward; hardcoding "68020 succeeds" or treating MOVEC as NOP would invalidate the test.
2. For **trap #0** from historical Palm handoff, **vector 32 is at 0x80**. This is needed only when testing that handoff. R-direct skips it **openly**, never claims a simulated Palm trap.
3. **Guest IRQ vectors** are installed later, not already present at synthetic entry. EmuTOS Dana sets IVR=0x40, then uses **0x44 at 0x110** for UART1 and **0x46 at 0x118** for timer 1. These are observable vector writes, not hooks MAME should pre-fill with guessed handlers.
4. **Address error/bus error** must preserve 68000 semantics for invalid accesses; do not alias all invalid addresses into RAM or convert odd-aligned word accesses into legal writes.
5. Exception entry needs an accessible supervisor stack. Do not accept a synthetic PC=0x2140 with an invalid stack just because the first instruction is a branch.

## 4. Pre-bootstrap versus reset: memory and VZ register ownership

Do not conflate these states:

| State | Meaning | Treatment |
|---|---|---|
| **Physical VZ reset** | Manufacturer-defined MC68VZ328 reset values, default chip-select windows/DRAM and vector sourcing | Not the initial R-direct profile. Consult MC68VZ328UM **and addendum**. No fake Flash location |
| **dbztool bootstrap RAM state** | External debugger setup using **danainit.sh**; explicitly programs SCR, GPIO, CS groups, DRAMMC, DRAMC, SDCTRL, ending SDCTRL=**0xD43F** | Useful source of a **known 4 MiB RAM configuration**. Must label it *dbztool-specific*, not Palm-specific or generic reset |
| **Palm/DanaRun handoff** | Real Dana Palm OS and helpers allocate chunks, select external peripherals, set UART1, and hand off with SR=0x2700 and trap #0 | Historical behavior visible only partially in source. RAM heap locations, all pins and remaining register values UNKNOWN |
| **R-direct synthetic profile** | Deliberately provisioned 4 MiB RAM, valid guest linked image, supervisor entry and selected VZ MMIO state | A **third, explicitly virtual state**. Freeze each chosen MMIO value as a test-fixture assumption; do not claim it matches Palm or dbztool 1:1 |

**Concrete source-derived initialization dependency:** [bios/memory.S](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/memory.S) uses the **RAM-lives-in-RAM path**, skips hardware RAM detection/reconfiguration, and **reads the preexisting _phystop variable at 0x42E** before the later **dana_init()** assigns it 4 MiB. It also checks **_warm_magic at 0x6FC** against **0x5741524D ("WARM")** to distinguish first boot, then may clear system variables **0x400–0x7FF** and BSS. **D0.5/D1 must explicitly capture this ordering.**

**Do not silently inject a fabricated Palm-style _phystop value to hide this dependency.** Either define a documented bootstrap RAM fixture including _phystop = 0x00400000, with provenance marked synthetic, or test the effect of pristine zero RAM in a separate negative/diagnostic fixture. Whether one choice is necessary for successful startup must be established through guest execution and trace.

Other important low-RAM symbols from [tosvars.ld](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/tosvars.ld): memvalid at 0x420, memctrl at 0x424, resvalid at 0x426, resvector at 0x42A, phystop at 0x42E, warm_magic at 0x6FC. They are guest state, **not VZ MMIO**.

## 5. Ordered first observable guest sequence

| Phase | Source-controlled event | Acceptance trace / no-host-shortcut rule |
|---|---|---|
| **S0 / fixture** | Loader has validated image SHA, 4 MiB allocation and map layout; CPU enters R-direct guest | Log image SHA, length, loaded range, PC/SSP/SR, complete MMIO assumptions. No executable or hash exists yet; this is a future requirement |
| **S1 / OS header** | **_os_header: bra.s _main**, then **_main: bra.w _realmain** | Actual 68000 instruction trace proves PC transition from linked image into _realmain |
| **S2 / CPU early init** | **move #0x2700,sr**, **lea _stktop,sp**; write illegal vector at **0x10**, probe 68000 MOVEC | Instruction/exception trace shows real supervisor stack and illegal-instruction vector delivery |
| **S3 / memory setup** | **jmp meminit**; read guest low-memory _phystop and _warm_magic; possibly clear sysvars/BSS/low_stram | Trace of guest RAM accesses and branch path, including zero-length/address guard; no host clearing on behalf of the guest |
| **S4 / BIOS entry** | Return to startup.S **memdone**, then **jmp _biosmain**. bios_init calls **dana_init()**, then processor_init(), vecs_init() and remaining initialization | PC and memory log prove guest reached BIOS; **do not claim an initialized screen or keyboard yet** |
| **S5 / first VZ MMIO** | dana_init writes **IVR 0xFFFFF300 = 0x40**, **ICR 0xFFFFF302 = 0x8000**, **IMR 0xFFFFF304 = 0x00FFFFFF**, **ISR 0xFFFFF30C = 0**; reads **PLLFSR 0xFFFFF202** and assigns **phystop 4 MiB** | Observe the exact guest MMIO transaction direction, width, PC and value; no pre-recorded "success" stub |
| **S6 / later peripherals** | Screen, Timer1, UART1, SPI2/ST, SD0 as subsequent phases | Defer implementation to D2–D7. It is acceptable for D1.5 to stop with a **precisely identified unimplemented MMIO**, never pretend EmuTOS has booted fully |

**Ordering caution:** some startup exception and memory reads precede the first VZ MMIO write. A test that observes IVR but misses earlier invalid memory accesses cannot prove correctness of the bootstrap contract.

## 6. Invariants and failure classification to be tested later

| Assertion (future automated test) | Expected result | Failure classification |
|---|---|---|
| A1: image source is exact pinned EmuTOS commit; hash, length, map symbols match | **Reject missing image/hash or different map; no synthetic PASS** | BLOCKED_FIXTURE |
| A2: __text equals requested PC entry, historical destination matches map if using 0x2140 | Start instruction is actual _os_header branch; no offset guess | FAIL_LOADER |
| A3: image, _stkbot–_stktop, low_stram, BSS and framebuffer allocation are within 4 MiB and correctly overlapping only per linker intent | No image overrun, no unsafe stack collision | FAIL_LAYOUT |
| A4: aligned 68000 big-endian reads and writes; odd word/long address must not silently succeed | Real guest exception reported with vector and PC | FAIL_CPU_OR_BUS |
| A5: guest rewrites vector 0x10, later 0x110 and 0x118, with correct exception dispatch | All vector writes observable and backed by real RAM | FAIL_VECTOR |
| A6: _warm_magic/_phystop values and transitions are logged rather than hidden | Reproducible S3 path, deterministic fixture; alternatives compared separately | FAIL_BOOTSTRAP |
| A7: first MMIO sequence S5 comes from guest execution and right register widths | Same trace ordering and register effects independent of DIAG probes | FAIL_MMIO |
| A8: second identical run starts from a new or restored controlled initial state | Repeatable PC/vector/MMIO event sequence | FAIL_NONDETERMINISTIC |
| A9: DIAG on/off preserves guest-visible results | Exact same CPU/peripheral semantics, extra trace only | FAIL_INSTRUMENTATION |

These are **acceptance requirements**, **not** claims about an existing run.

## 7. Unresolved inputs (do not conceal them)

- No locally obtained **emutos.img**, **emutos-dana.rom**, **emutos.map** or SHA. Thus exact linked **__text, _stktop, __bss** addresses are unverified.
- No verified Dana guest input stream or Palm-inherited memory dump; boot-time RAM/PC/SR/SSP snapshot from physical hardware unavailable.
- No verified MAME Dana checkout path/build on T; MAME source SHA on GitHub is only a **candidate baseline**.
- Exact manufacturer reset and bus electrical decoding belong to VZ source/datasheet/errata; only post-bootstrap guest-RAM mode specified here.
- Which _phystop fixture branch is sufficient, and whether R-direct first boot succeeds, **must be tested**; the contract does not manufacture an answer.
- R-booter placement and size must not overlap its relocation destination; no arbitrary staging address is asserted.

## 8. D0.4 closure and exact handoff

**D0.4 = SPEC_READY, documentation ONLY.** Source-derived RAM structure, CPU entry decisions, low vector offsets, initial MMIO checkpoints and unknowns are all explicitly mapped. This does **not** close D1, compile anything, or prove boot.

**Next increment D0.5, not D1:** freeze deterministic fixture schema, bounded trace format, independent verification rules, PASS/FAIL/BLOCKED evidence bundle and regression contract. No remote work is implicitly authorized.

### Immutable sources

- [EmuTOS-Dana at pinned SHA](https://github.com/davidgiven/emutos/tree/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b)
- [util/danaboot.S](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/util/danaboot.S)
- [bios/startup.S](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/startup.S)
- [bios/memory.S](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/memory.S)
- [bios/bios.c](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/bios.c)
- [emutos.ld](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/emutos.ld)
- [tosvars.ld](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/tosvars.ld)
- [bios/dana.c](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c)
- [dbztool/danainit.sh](https://github.com/davidgiven/dbztool/blob/d32702383c2ea3523ea58599c52345435c74e900/danainit.sh)
- [D0.3 build/loader contract](D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md)
- [D0.2 MMIO and Motorola errata](D0_2_EZ_VZ_REGISTER_CONTRACT.md)
