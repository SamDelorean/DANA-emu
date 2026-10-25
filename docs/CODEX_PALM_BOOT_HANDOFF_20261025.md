# Codex takeover — DANA-emu authentic Palm OS boot (2026-10-25)

**This file is the complete executable work brief for Codex. Start implementation, not a proposal or additional handoff.** User-facing conversation: Spanish. Git commits, code and repository technical records: English.

## 0. Product outcome and exact starting point

**Deliver a working AlphaSmart Dana stock Palm OS startup in the one existing MAME-based `dana-diag`.** Use actual MC68VZ328 68k instruction execution, actual reset/Flash/DRAM/chip-select/MMIO and the already present user-owned Palm firmware. Reach a genuine, guest-generated Palm OS startup/UI if achievable from these files. If the files lack necessary boot sectors or other original hardware behavior, prove that exact missing dependency with CPU/disassembly/bus evidence; never invent code, suppress blocked accesses, or report a successful boot without genuine guest execution.

- Repository: https://github.com/SamDelorean/DANA-emu ; **work on the existing canonical `main`**, pinned initial checkpoint `3dde150819bf8c49fda6d0d71f00b9ce63173a34`. Refresh the head safely and reconcile real changes before editing.
- Sole authoritative emulator tree on authorized T computer: `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`. MAME source: `.../diag/source`. One installed executable: `.../diag/bin/dana-diag`. Build intermediate `source/danadiagd` is NOT another authorized installed emulator.
- **Current qualified installed binary SHA256:** `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. Verify exact SHA before any installation. Retain a rollback path and never replace the operating executable with a failing candidate.
- Published driver: `src/mame/skeleton/alphasdana.cpp` (MC68VZ328 M68000 subclass, 32-bit address space, R-direct loader, physical Flash/reset mode, chip select and SDRAM, GPIO, clocks, IRQ, LCD, pen, UART1, SPI2/ST, SPI1/dual SD). Inspect `src/mame/skeleton/alphasdana_sd.h` and `alphasdana_sd_image.h` where applicable.
- **Known qualified, do not rebuild or retest gratuitously:** actual guest CPU+SPI2 native keyboard **81/81 scan codes, 86 releases, 5/5 chords** and installed EmuTOS-Dana boot smoke. Dual-SD guest read/write and close/reopen persistence previously qualified, as well as existing LCD/GUI-025/026; preserve features. Interactive EmuTOS text rendering was not proven by the most recent keyboard smoke. Prior qualification is not proof of Palm boot.

## 1. Private original firmware already present on T — do not ask user to reacquire it

Directory: `/home/spc/Projects/Dana-OS3K/firmware/research-only/`.

| File | Exact original bytes / SHA256 / significance |
| --- | --- |
| `Dana_US15_Flas.raw` | 6,062,080 B (`0x5C8000`); `fbba62000334bdb2faf352bdb899591c999528b3d631a4645c2dfce581e11059`. Concatenated Palm updater resource content, **NOT proven full physical Flash**. |
| `Dana_US12_Flas.raw` | 3,833,856 B (`0x3A8000`); `6169f44e8ddaf003bd5b98ea3424b19dfecf82f2681263feae078ab566b3370d`. Same limitation. |
| `DanaUpdate_enUS150R1.prc` | 6,085,164 B, SHA256 `53086494a233522d1773107a21f465835dca20e2cfd2076f2b45d0349558a342`. Resource DB `appl/asmt`, 119 consecutive `Flas` resources. |
| `DanaUpdate_enUS120.prc` | 3,855,501 B, SHA256 `1d4e19a41a68962bd6bce91cd9ed891bdedbf5eb24a296d3acf7221438fda1d6`. 75 `Flas` resources. |
| `AlphaSmart_Dana1_5_Flash.zip` | 9,453,509 B, SHA256 `1a0256e35c11c7455a58738f05218e1e290b8d381a5742467f1a512ac25c14fc`. Official-source updater archives/instructions. |

The `Flas` records concatenate in ID order; each resource contains payload + four-byte *byte-sum* checksum, NOT CRC32. The raw concatenated content contains `FE ED BE EF` at offset `0x8`, `PalmCard` metadata, Palm OS and AlphaSmart strings. This demonstrates **firmware data**, not a complete readout of protected boot sectors or physical NOR chip geometry. Do not commit original ROM/PRC/ZIP or derived ROM bytes to public Git, paste private bytes into issue logs, or write to a physical Dana.

The big-endian first two longwords in each extracted raw image are **candidate vectors**, not independently verified physical reset mapping:
- US1.5: SSP=`0x000048fe`, reset PC=`0x1000c80a`.
- US1.2: SSP=`0x0000486a`, reset PC=`0x1000c776`.

## 2. Last actual native Palm run — NOT BOOTED

Result text: `docs/PALM_UPDATER_DERIVED_COLD_BOOT_20261025.json`; immutable corresponding handoff prefix at `docs/HANDOFF.md`, latest current content only. User-owned emulator-only trial padded US1.5 with `0xFF` to **8 MiB** and US1.2 to **4 MiB** in private `/tmp/DANA_PALMOS_NATIVE_BOOT.3YyuVIg0/` solely to explore existing physical loader (which enforces complete power-of-two geometry). **This padded tail is invented/unknown**, NOT a recovered physical dump. Do not promote this experiment into a stock-ROM reference.

One recorded US1.5 run loaded the 8MiB temporary array in physical `-rom` profile, not EmuTOS `-quickload`. Native log:
```
DANA_PHYSICAL_IMAGE bytes=8388608 ... topology=linear_array_unqualified
DANA_PHYSICAL_RESET vectors=firmware CSA=00b0 CSCTRL2=1000 CSCTRL3=9c00
DANA_PHYSICAL_BLOCKED reason=FLASH_COMMAND_SET_UNVERIFIED address=00000000 data=0000 pc=1000c812
```
This proves physical-mode loading/reset and CPU-origin bus activity at a guest PC. **It does not establish Palm OS boot**. At `PC=0x1000c812`, firmware attempted a word write to physical address 0, which the current driver classified as Flash (boot CSA still selected). Root cause is **UNKNOWN**: absent boot region? firmware image not mapped as original? correct CSA reset decode? guest stack/address remap expectation? actual NOR/DRAM timing? Diagnose from disassembly and documented VZ behavior; do NOT decide by intuition.

The observer itself had an independent error: Lua `cpu.state["A7"]` is NIL in this MAME CPU state binding. Therefore its guest.trace was not produced. Fix observer by listing valid CPU state names or using available `SP` binding; do not mistake observer failure for guest hardware failure. The published receipt has **no US1.2 guest execution/trace**. Never claim US1.2 passed.

No Palm UI, OS boot, external ROM write, or new production emulator installation occurred in this native Palm attempt.

## 3. Code regions needing precise examination

In `src/mame/skeleton/alphasdana.cpp` inspect and trace these concrete functions:
- `firmware_load`: `-rom` takes a power-of-two linear 128KiB–16MiB byte array; rejects updater-sized partial images and checks reset PC at bytes4–7. Treating a PRC or Flash-content fragment as a complete power-of-two NOR array is **not justified**.
- `physical_reset`, `machine_reset`, `program_map`, `cpu_space_map`: profile selection, vector fetch, SCR, CSA at reset, CPU state.
- `physical_r`, `physical_w`: current `boot = !(m_cs_select[0] & 1)`; this routes all ordinary low writes to Flash until guest reprograms CSA. `physical_w` stops on `FLASH_COMMAND_SET_UNVERIFIED`. Determine whether this correctly reproduces the MC68VZ328 reset remap and initial DRAM availability; preserve fail-closed unsupported behavior until real evidence supports change.
- `cs_r/cs_w`, `cs_select_*`, `cs_hit/cs_size/cs_base`, `dram_r/dram_w`, `physical_mmio_r/w`, `physical_block`: first guest-visible failure and precise decoding.
- `GENERIC_SOCKET` in machine config, `DANA_VZ_CPU` address-width variant and scheduler. Avoid a new CPU engine, fake Palm system calls or host-side display painting.

For *real* MC68VZ328 reset vector, CSA/CSB/CSD initial mapping, DRAM/SDRAM, PalmCard and original Dana-specific boot behavior, read source references first:
- `research/sources.lock.json` and `docs/D0_2_EZ_VZ_REGISTER_CONTRACT.md` (existing Motorola manual/addendum contract).
- `docs/D8_5_PHYSICAL_BOOT_IMPLEMENTATION.md`; `docs/GENERAL_WORK_PLAN.md`, `docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md` and `docs/DANA_DIAG_EXCLUSIVE_TEST_POLICY.md` (current rules).
- `https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/05-ROM-DANA-ACTUALIZADORES.md` (authentic updater structure and known limits).
- `https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/01-HARDWARE-DANA.md`.
- Pinned MAME donor `SamDelorean/mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`, `src/mame/palm/palm.cpp`, MC68EZ328 device as conceptual reference only.
- Original POSE `EmRegsVZ` and pinned Motorola `M68VZ328Hwr` via `research/sources.lock.json`; POSE reference defaults are NOT automatically Motorola official reset defaults. Review per-file license before reusing code.
- EmuTOS-Dana `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b` for board hardware accesses, NOT an authentic Palm boot substitute.

## 4. Do the work now — single boot objective, modular diagnosis only if helpful

1. **Inspect the actual checked-out T source/binary and the private firmware.** Verify hashes, no second emulator, no uncommitted user work overwritten. If T is not connected to this Codex environment, do as much source/firmware analysis and implementation as actually possible, then report the exact inaccessible requirement; do not invent execution or claim background progress.
2. **Resolve the earliest failing CPU bus transaction**, not a generic survey. Decode and disassemble first ~100 68k instructions from genuine image origin near raw offset `0xC80A` for 1.5, inspect jump/branch destinations and the first memory write, decode actual CPU state (PC/SR/SSP and effective address) using correct MAME APIs. Understand whether a valid stock Palm startup requires a separately protected boot sector or initial low RAM alias. Analyze updater's programming offsets and check whether the first longwords are genuine reset vectors or PalmCard metadata. Cross-check chip-select control values and runtime bus trace against pinned Motorola/Dana evidence.
3. **Implement the smallest real hardware correction** if and only if supported by authentic source/guest behavior. Integrate in the current `src/mame/skeleton/alphasdana.cpp`, without app-specific hooks or bypassing Flash write rejection. If original full dump is a hard requirement, state which sector/range and proof establishes it. A private test-only temporary image with missing bytes clearly marked hypothetical may be used to isolate the cause, but must never be presented as physical ROM fidelity.
4. **Build ONLY the existing reduced DANA DIAG** incrementally using the established Clang21/MAME build cache and inspect/record actual compiler output and hashes; no new branches/clones/worktrees/alternative emulators. Keep the old installed binary safe until a candidate has credible functional evidence. CPU guest trace must identify how far authentic Palm OS reaches; isolate a real Flash/remap/MMIO blockage and fix from evidence. Run US1.5 first, US1.2 for contrast when useful.
5. **Product acceptance:** success requires actual CPU-executed stock Palm OS reaching Palm UI with guest-driven framebuffer/input, no invented ROM vectors, fake MMIO, hidden exceptions or host-rendered screen. Prove first stages separately (valid image vector, first genuine instructions, DRAM chip selects, Palm initialization, LCD) but do not confuse partial steps with finished product. Preserve working EmuTOS R-direct / ST81 keyboard / SD regression with **targeted** tests only where changed behavior could affect them. Never rerun closed large suites just to produce activity.
6. **Report exact verifiable outputs:** commit(s) on canonical `main` (unless current authorization or repository safety requires leaving a reviewed diff), source changes, authentic image SHA (not bytes), binary SHA, MAME full CLI, native CPU PC/SSP/SR/bus sequence and first unresolved MMIO/register or guest UI evidence; PASS/FAIL/BLOCKED and the one remaining blocker. Update the existing handoff/status in-place without proliferating plans, trackers or artificial gates. Never claim an OS boot if only the loader or a synthetic guest succeeded.

## 5. Hard working constraints

- **Single working DANA DIAG product**; no new branch, clone, isolated version, parallel emulator, or alternate stable build. No Codex work in AS2K, Pro or EmuTOS/OS3K firmware repos; they are read-only references unless user explicitly expands scope.
- Protect the previously qualified 81-key ST keyboard, dual SD read/write, LCD, pen, GUI and EmuTOS boot. Do not replace known-good operating executable on a FAIL.
- Never write to a real physical Dana, host disk image outside disposable copies, user's original updater/ROM files or private firmware, and do not distribute copyrighted Palm ROM bytes.
- No blind address padding/mirroring, switching to synthetic RAM entry, patching Palm binaries, hardcoded success checks, CPU state shortcuts or ignoring exceptions to pretend Palm boots.
- Maximize **real product progress in one intervention**: focused module diagnosis is allowed where needed, but not artificial per-register gates or a stream of test-harness-only tasks.
- This handoff alone does not grant new **Remote Desktop Commander** privileges: the last ChatGPT intervention exhausted its five specifically authorized remote calls. Codex should use only the machine access and permissions the user explicitly supplies in its own environment, otherwise report BLOCKED access precisely. Do not claim that publishing these instructions executed Codex.

**Begin now with the private US1.5 source image and the first write at `PC=0x1000C812`. Work toward real Palm OS boot instead of offering another work plan.**
