# D0.3 — EmuTOS-Dana guest image and RAM bootstrap contract

**Status: SPEC_READY (source/build recipe only; binary fixture NOT YET AVAILABLE).** Static research completed on 2026-10-13. No build, Commander execution, physical Dana access, or emulator code change was performed. This document is the authoritative D0.3 output under the [incremental plan](DANA_EMU_INCREMENTAL_WORK_PLAN.md).

## 1. Question and finding

**Question:** Which precise artifact should the future MAME-reduced Dana emulator boot first, how is it built, and what memory/CPU handoff does the historical loader actually perform?

**Answer:** The EmuTOS-Dana source target is **make dana**, which generates **emutos-dana.rom**. Despite its extension, it is a **RAM-loadable, unheaded binary containing a position-independent first-stage loader followed by embedded emutos.img**, not the physical Flash ROM image of the Dana. Palm OS DanaRun temporarily stages it from the file named **/kernel.img**, launches the embedded first-stage loader, and hands control to the relocated EmuTOS image in RAM.

The first emulator profile will be explicitly **RAM/post-bootstrap**, not a claim to reproduce power-on reset, Palm OS execution, or Flash chip-selects.

## 2. Reproducible source lock and build recipe

| Item | Exact source of truth |
|---|---|
| Source repository | https://github.com/davidgiven/emutos |
| Source commit | **9c42ef0f2c2fa9d1e217fced9da68901b2326e8b** (historical branch dana) |
| Canonical target | **make dana** from repository root |
| Cross compiler (default) | **m68k-atari-mint-** toolchain, GCC/binutils; default CPUFLAGS **-m68000** |
| Optional toolchain mode | ELF=1 selects m68k-elf- and changes flags; **not** the default/validated reference |
| Key output | **emutos-dana.rom** (binary loader package) |
| Intermediate output | **emutos.img** (raw EmuTOS binary), linked using the preprocessed **obj/emutospp.ld** |
| Intermediate linker/map | **emutos.map**, containing __text, _main, stack/BSS symbols and physical placement information |
| Tool generated | **obj/danaboot.o**, linked with **util/danaboot.ld** to create emutos-dana.rom |
| C/assembly target selection | -DTARGET_DANA implies MACHINE_DANA and EMUTOS_LIVES_IN_RAM=1 |
| Runtime target features | 68000 base CPU, SDMMC enabled, DANA_DEBUG_PRINT enabled, Atari hardware disabled and advanced CPU disabled by default |
| Packaging on SD | Rename/copy **emutos-dana.rom** to **/kernel.img** on a Palm-readable card; DanaRun PRC is the launcher |
| Local Dana guest binary and SHA-256 | **NOT FOUND / NOT DETERMINED**. Drive filename search for emutos-dana, danarun, and kernel.img found no such binary. Do not fabricate a checksum |

**Source commands, for a FUTURE authorized isolated build only:** check out the immutable SHA; use a clean source tree and verified cross-toolchain; record any localconf.h and local.mk overrides; run **make dana** with **-j3** on machine T in the normal authorised Drive-job process. Capture tool versions, build exit code, emutos.map, emutos.img, emutos-dana.rom, file lengths and SHA-256. Do not run those commands as part of D0.3.

Build chain observed in Makefile:

1. Target **dana** adds -DTARGET_DANA and the small-size optimization flags, then recursively builds the Dana image.
2. Link **emutos.img** from core, optional and end objects using **emutos.ld** preprocessed as **obj/emutospp.ld**. Output is **OUTPUT_FORMAT(binary)**.
3. **util/danaboot.S** incorporates the exact EmuTOS binary by assembler **.incbin "emutos.img"**.
4. Link **obj/danaboot.o** using **util/danaboot.ld**, which declares **OUTPUT_FORMAT(binary)** and gives the booter link region origin **0x00100000**. The resulting **emutos-dana.rom** is also a raw binary, not an ELF/PRC/flash dump.

**Important address distinction:** the booter linker region origin 0x00100000 is a **link-time region for that stage**; it is not proof that Dana's physical ROM or the Palm heap at runtime is mapped at 0x00100000. The loader itself is labelled position-independent in source. The actual Palm heap address is not known from a release binary or trace.

## 3. Observed image layout and entry path

| Layer | File / component | Layout or behavior | Evidence |
|---|---|---|---|
| A — Palm application | **tools/danarun/danarun.prc** | Uses Palm VFS to open **/kernel.img** on a volume and allocate/copy 32-KiB chunks, plus a block for its own handoff stub | tools/danarun/danarun.c |
| B — Palm assembly handoff | **tools/danarun/palmboot.S** | Initializes UART1, disables interrupt delivery, places the first block address in **trap #0 vector at physical 0x80**, and executes **trap #0** | tools/danarun/palmboot.S |
| C — RAM booter | **emutos-dana.rom**, starts at symbol **entry** | Starts execution at the loaded first block, sets an internal stack, computes the relocation helper address, and passes the address of embedded image bytes as a stack argument | util/danaboot.S |
| D — image relocation | helper **relocate** | Copies **emutos.img** in 32-bit units to **0x00002140** and jumps to **0x00002140** | util/danaboot.S |
| E — EmuTOS execution | **emutos.img**, first instruction expected at destination | Startup .text begins with **_os_header: bra.s _main**. Then EmuTOS sets supervisor interrupt masking, constructs its own stack/vector environment, initializes RAM/peripherals, and enters BIOS | bios/startup.S, emutos.ld |

In **util/danaboot.S**, the payload markers are **data_start** and **data_end**. The byte sequence of **emutos.img** begins immediately after the header/relocation offset inside **emutos-dana.rom** and is copied without decompression.

**Correction of an earlier description:** the historical source calls its first stage a "decompressing RAM booter", but the visible implementation performs **literal longword copying**, not an algorithmic decompression. Do not design a compressed-image loader without additional evidence.

**0x00002140 is the booter's hard-coded copy destination and execution branch**, not the start address of a physical Dana flash ROM, nor the MAME device reset vector. Whether this value matches the linked **__text** address for a newly built image must be checked against **emutos.map** for that exact image; do not assume it for all builds.

## 4. Loader hazards and static invariants (must be tested before executing an image)

### H-01: historical Palm block-table capacity

In **danarun.c**:

- BLOCK_SIZE = **32 * 1024** bytes.
- KERNEL_SIZE = **300 * 1024** bytes.
- The array has **KERNEL_SIZE / BLOCK_SIZE = 9** pointers, but the allocator executes **for i = 0 through block_count inclusive**, needing **block_count + 1** pointers (last block reserved for stub).
- **block_count = ceil(kernel_size / 32768)**. Thus block_count **must be <= 8** for valid indices in this historical implementation, yielding an effective maximum payload size of **262,144 bytes (256 KiB)**, not 300 KiB.
- It reads each chunk with VFSFileRead of exactly BLOCK_SIZE and lacks an explicit, checked last-chunk tail/short-read policy. Do not assume safe padding.

**Implication:** a direct MAME loader should validate exact image length, not reproduce the unsafe array accesses. Reproducing actual DanaRun behavior is a separate task, not a prerequisite for RAM mode.

### H-02: first-stage relocation width and alignment

In **util/danaboot.S**, the code uses a 16-bit counter and DBF to execute **(data_end - data_start) / 4** copies of one longword each.

An image suitable for the unmodified booter therefore requires:

- **embedded length > 0**, and **embedded length divisible by 4** (otherwise the source expression truncates or fails to represent all bytes).
- **embedded length / 4 <= 65536**, or **embedded image <= 262,144 bytes (256 KiB)**, because the DBF loop uses a 16-bit iteration count.
- destination interval **[0x2140, 0x2140 + embedded_length)** must be valid writable RAM and avoid corrupting indispensable active loader or peripherals.
- actual **emutos.map** must confirm that the relocation destination corresponds to the expected linked text/address assumptions.

These are **constraints inferred directly from source**, not checks already exercised on a compiled binary.

### H-03: first-stage and second-stage stack are different

The assembly handoff and guest startup change the stack. The initial Palm heap block locations and inherited SR/SP/CPU state are **not constant in the source**, and no actual guest trace has been retrieved. A reduced virtual RAM loader should define and report its **own synthetic staging state** in D0.4 rather than pretending to restore an observed electrical reset state.

### H-04: no fake flash reset

The VZ's real reset vector state, chip-select map, SDRAM bank setup and Palm Flash mounting are unknown. Using MAME's CPU reset PC/SSP to jump directly to 0x2140 **is a labelled shortcut/loader profile**, not electrical boot. No such shortcut should be hidden in the MCU peripheral implementation.

## 5. Next MAME-mode specification derived from evidence

**Preferred minimal profile for initial debugging:** select the RAM guest **emutos.img**, whose contents will be obtained from the same pinned build, verify its SHA, place it at the location validated by **emutos.map** (booter expects **0x2140**), initialize 4 MiB of RAM and VZ MMIO in a separately documented **post-bootstrap** state, and hand off execution to the actual guest first instruction.

**Compatibility verification profile:** optionally load **emutos-dana.rom** with its actual booter included, to verify both stages and compare trace against a direct emutos.img load. Do not require a functioning Palm OS emulation for the first acceptance milestone.

**D0.4 is responsible for specifying actual virtual CPU reset/stack/vector state and the range/contents of initialized RAM** for each profile. D0.3 intentionally does not assign unobserved register values or addresses.

### Acceptance artifacts expected from the future first build

- **source_manifest.json:** Git commit, toolchain versions, resolved config/options, Make target, build host.
- **emutos.map**, **emutos.img**, **emutos-dana.rom** stored in isolated local/Drive test artifacts, not committed to Git.
- **guest_manifest.json:** exact byte sizes, SHA-256 of both images, beginning bytes and loader marker offsets, verified _main and __text addresses.
- **validation_report.json:** confirm both are headerless expected binaries, embedded image bytes match emutos.img, destination and size checks, and explicit flags for H-01 through H-04.
- **execution evidence only later:** PC/SR/SP traces and the first real guest MMIO; no functional PASS without MAME execution.

These are instructions for **later authorised execution** only. No binary or hash has been generated during this increment.

## 6. Historical source notes and correction policy

- [Makefile at pinned commit](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/Makefile), lines 189–218, 452–470, 627–652.
- [Dana RAM booter source](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/util/danaboot.S) (45 lines).
- [Dana booter linker](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/util/danaboot.ld).
- [EmuTOS linker](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/emutos.ld).
- [EmuTOS startup header and stack](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/startup.S).
- [Dana feature defaults](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/include/config.h), lines 515–575.
- [Palm loader C source](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/tools/danarun/danarun.c).
- [Palm handoff assembly](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/tools/danarun/palmboot.S).
- [Palm loader Makefile](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/tools/danarun/Makefile).
- [Port usage and limits](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/doc/readme-dana.txt).

**Scope closed:** pinned recipe and complete source-derived transfer chain documented; image bytes/SHA/real execution are pending. Advance strictly to **D0.4** (virtual RAM bootstrap CPU/bus initial state) after recording this document. Do not start D1 or run a build as part of D0.3.
