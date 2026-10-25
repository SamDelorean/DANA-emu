# Dana stock Palm OS — Small ROM physically present in archived UK updaters

**Research date:** 2026-10-25. **Investigated here, not delegated to Codex.** Status: **AUTHENTIC VENDOR-ARCHIVE BOOT-CODE CANDIDATE FOUND / HARDWARE PHYSICAL RESET NOT YET EXECUTED**. Only PUBLIC METADATA recorded; original commercial binary bytes remain private and unchanged.

## Private source and reproducible method

Source: owner-controlled Google Drive `AlphaSmart_Dana1_5_Flash.zip` (Drive file id `1LY_Ykm3RysWe4vutxWeFRnwSTCxlIcFg`), 9,453,509 B, SHA256 `1a0256e35c11c7455a58738f05218e1e290b8d381a5742467f1a512ac25c14fc`.

Read the ZIP in memory and recursively inspect its four vendor PRC updater entries (two UK, two US); parse Palm PRC resource directory (starting byte 78, 10 bytes per resource); select `Flas` resources, sort by numeric ID; for every resource verify its trailing four-byte big-endian checksum equals the **unsigned byte-sum of the preceding content**; concatenate content without four-byte checksums. **All 391 Flas chunks verified across the four PRCs**: UK1.5 120 + UK1.2 77 + US1.5 119 + US1.2 75 = 391, zero checksum failures. Other PRC resource kinds are `code, data, tFRM, Talt, tSTR, tAIB, tver, wTap`; the original source archive also includes an unrelated WiFiDriverInstaller and documentation. No need to obtain/download missing code to establish existence of Small ROM in UK.

| Vendor PRC | Flas chunks | Concatenated content | SHA256 of content | PalmCard signature at offsets |
|---|---:|---:|---|---|
| `ROMUpdater_enUK150R1.prc` | 120 | `0x5D0000` = 6,094,848 B | `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` | `0x0000` and **`0x8000`** |
| `ROMUpdater_enUK120R2.prc` | 77 | `0x3C0000` = 3,932,160 B | `d450743f454e84ee6d781211fddef216867492a15a0b1cd3bb13b1916b811672` | `0x0000` and **`0x8000`** |
| `DanaUpdate_enUS150R1.prc` | 119 | `0x5C8000` = 6,062,080 B | `fbba62000334bdb2faf352bdb899591c999528b3d631a4645c2dfce581e11059` | `0x0000` only (not at 0x8000) |
| `DanaUpdate_enUS120.prc` | 75 | `0x3A8000` = 3,833,856 B | `6169f44e8ddaf003bd5b98ea3424b19dfecf82f2681263feae078ab566b3370d` | `0x0000` only (not at 0x8000) |

## Exact Small ROM vs Big ROM evidence

In **both UK PRCs**, the concatenated Flas payload at byte 0 has `CardHeaderType` header fields: `initStack=0x00000316`, `resetVector=0x100002A2`, `signature=0xFEEDBEEF`, `hdrVersion=5`, `flags=0x0040` (VZ flag, as parsed by pinned POSE EmROMReader). At **file offset 0x8000**, a SECOND complete `CardHeaderType` begins, with `resetVector=0x1000C80A` in UK1.5 and `0x1000C776` in UK1.2. Its first 16 bytes match the respective US updater's Big ROM header exactly (regional payload content itself differs).

The offset `0x68` in both first and second UK headers contains `0x10008000`; the physical relationship strongly supports a separate 32 KiB initial Small ROM, then Big ROM at flash-address candidate `0x10008000`, **but firmware-update data alone does not prove chip identity, physical A0..An wiring, NOR geometry, protected sector status, or how reset CSA0 decodes the actual chip**.

The putative original boot code is NOT zero/FF padding: both UK images have `0x4EFA 0x0072` at file offset `0x02A2`, valid M68000 `JMP (0x0072,PC)` from effective PC `0x100002A4` to **`0x10000316`** inside the authentic image. There are further executable-looking Motorola 68k instructions at `0x0316`, alongside a `boot` marker in the surrounding header. This **supports existence of original vendor-supplied Small ROM startup code**, though its exact electrical boot applicability is not proven until a CPU reset trace on Dana-faithful MAME or a verified physical dump.

The first 32768 bytes of UK1.5 hash `e7d878d3fb110761ae85e0a9085bcb4cece93d6b6d243fc716873b7d3f8b5c6c`; UK1.2 hashes `1839b05e96157872953f5fed421a1dcaf7f4eba3b66904ac0bb74a38ad4702b2`. These version-specific prefixes are **not interchangeable by assumption**. There is no justification for mixing UK Small ROM with US Big ROM and presenting it as an original vendor image. Prefer **one complete UK1.5 firmware stream from a single original updater** for next native reset test.

**Important geometry caveat:** UK1.5 `0x5D0000` and UK1.2 `0x3C0000` are not powers of two; these are genuine archive payload lengths, not verified physical Flash chip capacities. Current DANA `firmware_load` rejects them because its generic ROM array requires a power-of-two length. Do NOT interpret the missing trailing bytes as `0xFF` authentic Flash or silently modulo across a fabricated size. Use an explicitly coverage-aware diagnostic loader or a clearly labeled temporary experiment that rejects/records any guest access to unprovided bytes. Production cold-boot PASS demands genuine bytes for all accessed ranges and correct chip-select geometry. **No changes to current installed DIAG were made by this research.**

## Correct ownership and next coding interface

**Research OWNER: this ChatGPT conversation.** Here we inspect source/vendor images and determine chip mapping, coverage, disassembly, physical reset semantics and hardware evidence (Ghidra installed on T may be run here when explicitly authorized). **Codex OWNER: coding only**, based on explicitly closed research findings; it must not be told to take over open-ended firmware archaeology.

When implementation is requested, Codex's narrow task is: in the **sole canonical DANA DIAG**, enable an evidence-labeled, read-only **UK1.5 vendor-image cold-reset test** from the genuine Small ROM at array offset zero; preserve reset-generated CPU SSP/PC, existing physical CSA decode, all existing peripherals, and strict unknown-byte detection. No synthetic PC, fake Small ROM, host-rendered OS, branch/clone, or alternative emulator. Use the real UK1.5 native code path; expose true first terminal MMIO/DRAM issue to *this chat* for interpretation and next closed code order. No executable replacement unless qualified. Only classify hardware fidelity PASS when physical mapping provenance is independently proven and Palm guest UI is real.

## Source checks

- Source-archive own ZIP and nested UK/US PRCs above (all hashes/checksums and header values directly calculated in this chat, not inferred from an assistant plan).
- POSE original `cloudpilot-emu/pose-original@97b10711fe4ca50c1bd47072378eaab26ba8e81d`, `SrcShared/Hardware/EmBankROM.cpp` (`LoadROM`, Small/Big ROM) and `SrcShared/EmROMReader.cpp` (VZ flag and `bigrom` field).
- NXP Motorola MC68VZ328UM (chip selects, reset vectors and external memory).
- Current DANA physical driver `src/mame/skeleton/alphasdana.cpp`; prior user-approved 81-key installed DIAG SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.

**Status: firmware boot code FOUND in UK updater ZIP. Palm OS physical startup NOT YET TESTED/PROVED with UK firmware.**
