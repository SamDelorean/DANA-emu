# F2 Dana peripheral: mandatory documentary cross-check before another build

**Date:** 2026-10-22. **Status:** SOURCE_REVIEWED / DOCUMENTATION_DIFFS_IDENTIFIED / NO NEW COMPILE / NO NATIVE PASS.
**Single active product/worktree:** `dana-diag`; no copies, clones, additional builds, stable execution, guest recompilation or blind retries.

## 1. Primary-source authority and exact revisions reviewed

1. **Manufacturer:** [MC68VZ328UM/D](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), sections 13.5 and 13.6.3, printed pp. 13-12..13-16 (PDF indices 247, 249–251), plus [MC68VZ328UMAD/D](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf), rev. 7. Official PDF text was retrieved and checked for SPI2 field descriptions; the web screenshot request failed (cache miss), so **do not claim image-level PDF verification** in this audit.
2. **Actual guest workload:** `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b`, `bios/dana.c` and `bios/dana.h`, especially `st_send_recv`, `pen_send_recv`, `dana_kbd_init`, `dana_ts_rawread`, `dana_poll_touchscreen`.
3. **Independent VZ model:** `cloudpilot-emu/pose-original@97b10711fe4ca50c1bd47072378eaab26ba8e81d`, `SrcShared/Hardware/EmRegsVZ.cpp` and `SrcShared/Palm/Platform/Core/Hardware/IncsPrv/M68VZ328Hwr.h`.
4. **Dana board/ADC:** `csnover/Retro68@d917b67b16bef7bcf5c75a74f617710c32addcbc`, `PalmUtils/poser/SrcShared/Hardware/EmRegsVZAlphaSmart.cpp` and `EmSPISlaveADS784x.cpp`; GPL-licensed **behavioral reference only**, no GPL-to-MAME copy.
5. **Pinned MAME:** `SamDelorean/mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`, `src/emu/devfind.h`, MAME-generated source-object build plan in authentic `F2_dryrun.log`.
6. **Actual code/evidence:** `DANA-emu@581601b49acb6603af2a100817d0f06fed17ed96` (012-C compiled driver); `80cbfecab4df3c4412e370974295ac8a2f336fc1` (not established compiled); `78be96c5615c4b929a96c9dc835b9fff3a2161aa` (F2 candidate); directed `tests/dana_hardware_test.py`, `F2_ONE_ACTIVE_DIAG_RESULT.json` and `F2_compile_and_link.log`.
7. **Project governance:** `docs/GENERAL_WORK_PLAN.md` and `docs/DANA_DIAG_EXCLUSIVE_TEST_POLICY.md` from **main** (not present on this feature branch), `docs/CANONICAL_CONTINUITY_AND_RULES.md`, `docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md`, `docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md`, `docs/D0_2_EZ_VZ_REGISTER_CONTRACT.md`, `docs/DANA_INTEGRATED_HARDWARE_CANDIDATE.md`, `docs/HANDOFF.md`, `research/sources.lock.json`, and `docs/F2_CLANG21_BACKEND_CRASH_OPTIONS_20261022.md`.

This is a targeted audit of the relevant available documents, **not a claim that every page of every unrelated project artifact or all historic private Drive material was independently reverified now**. Missing source or evidence must be marked UNKNOWN rather than guessed.

## 2. Cross-check: manufacturer ↔ guest ↔ model ↔ candidate ↔ tests

| Subject | Source-backed contract | Current observation / discrepancy | Required treatment |
| --- | --- | --- | --- |
| SPI2 address/width | SPIDATA2 `0xFFFFF800` 16-bit; SPICONT2 `0xFFFFF802` 16-bit; Motorola UM §13.6 | Existing 012-C and F2 maps agree | Preserve lane/access tests |
| SPI2 control bits | Motorola UM table 13-8: ENABLE bit 9 `0x0200`, XCH bit 8 `0x0100`, IRQ bit 7 `0x0080`, IRQEN bit 6 `0x0040`, speed bits 15–13 `0xE000` | Qualified 012-C gate `(ctrl & 0x2100)==0x2100` includes `0x2000` speed bit, unlike hardware; later uncompiled base uses `0x0300`, which agrees with manufacturer / POSE | **Do not treat preserving 012-C gating as correct general SPI2 emulation.** Decide explicitly whether first F2 integration is strictly a guest-specific regression or the hardware-correct SPI2 gate is a named prerequisite/correction; separately report IRQ semantics |
| Real ST exchange | EmuTOS `st_send_recv`: `0x2200`, write byte, `0x2307`, poll completion, PE3 active-low CS; ST greeting `0xAA` | Both `0x2100` and `0x0300` accept this particular `0x2307`, so guest's current SPI rate **masks** the 012-C defect | Regression must also include a different legal SPI2 rate to catch erroneous dependency on `0x2000` |
| Real pen exchange | EmuTOS `pen_send_recv`: write `0x2247`, command byte `0x90/0xD0`, PG2 low, `0x2347`, read completion, load 0, `0x224F`, `0x234F`, PG2 high, receive value >> 4 | F2 source implements 8-bit command / 16-bit sample and stateful PG2 CS; its directed test issues `0x2347` and `0x234F` without fully reproducing all intermediate guest control writes | Test exact **guest write sequence** and CS/enable timing, not merely a convenient modeled subset |
| Touch GPIO | EmuTOS PF1 active-low input, PG2 pen CS, PE3 ST CS; R-direct 012-C GPIO initial profile F input, PG2/PE3 deselected | F2 modifies PF1 input and PG2 DATA handling, reuses existing GPIO slots and SPI2; integration is feasible on 012-C without importing UART/SPI1/LCD additions | Preserve reset/select/direction, save-state and ST regression; test pressed/released and 12-bit X/Y responses |
| ADC data | EmuTOS consumes 12-bit read shifted by 4; Retro68 ADS784x maintains SPI command/conversion bitstream | F2 uses provisional host coordinate scaling; numeric endpoints not manufacturer-calibrated | Bound output and use real conversion commands; do **not** label scaling physically calibrated |
| F2 directed tests | `test_actual_stylus_gpio_and_12bit_spi2_adc_path` compiles extracted production methods with ASAN/UBSAN; includes `assert(s.irq_calls>0)` | This IRQ assertion assumes the later 80cb SPI2 `update_irq_lines` behavior **absent in compiled 012-C**. Naive F2-only transplant would mix an IRQ4 feature into an ADC test or fail for the wrong reason | Split pen-only contract from separately qualified SPI2 IRQ4 contract; do not alter hardware merely to satisfy a mismatched test |
| Compiler | Authentic `-O3` Clang21.1.8 crash in LLVM X86 DAG instruction selection for device_finder instantiation; make exit 2 | C++ parser did not emit a syntax error; no evidence that `pen_exchange` itself triggers crash | Fix source scope first; if still reproducible, one-object optimizer/compiler workaround only with new authorization |
| Build rollback | Existing MAME archive generation creates `libmame_danadiag.a` as well as `alphasdana.o` and linker output | Retired 017 job restores object/source/internal output but omitted the updated archive after a hypothetically successful link | Restore/check archive in the **same tree**; verify hashes on exit, do not create another emulator |
| Runtime proof | The exclusive test policy requires actual `dana-diag` with pinned binary, real MMIO, GPIO and host input, bound to source/hash | Current F2 test is code-level only; no native pen stimulus/ADC receipt; current 012-C PASS do not qualify F2 | F2 status remains NATIVE_PENDING regardless of compilation result |

## 3. Mandatory PRE-COMPILE source audit for F2

Before launching any further build, establish these in one compact checked report:
- Confirm immutable source pins and SHA-256 for manufacturer-derived contract, guest, baseline, new candidate and existing `dana-diag`; audit generated Make command and path. No new directory or compiler installation.
- Generate/inspect a **production-only** source delta against the **actually compiled** 012-C SHA. Classify every changed method/member as F2 / pre-existing prerequisite / unrelated. Reject silent ST/UART/LCD/Timer1/SPI1 additions.
- For every F2-accessed peripheral, compare actual guest writes, chip-select order, register lane/bit semantics, reset and IRQ behavior against Motorola and POSE/Retro68. Where an old compiled bug exists, **state it** instead of silently preserving it as a correct contract.
- Align each directed test's assertions to the same source-delta scope. Add exact EmuTOS SPI2 sequences, no-pen and selected-overlap cases, and separate IRQ tests; never promote source-only tests to native PASS.
- Preflight the canonical in-place job: exactly one `alphasdana.o` compilation, bounded log, `-j3`, no other compilation, one existing Git checkout/DIAG tree, reversible `.o` and `.a` archive + output, no EmuTOS rebuild, no extra executable. Runtime verification limited to `dana-diag`.
- After explicit authorization, confirm **actual compiler launch** with the short one-time startup check; no continuing polling, broad retries or environment changes.

## 4. Blocked/unverified inputs

- Full original native 012-C evidence archive remains historic accreditation only; it has **not** been rerun in this audit.
- All historical private Drive attachments/workbook rows have **not** been freshly read and cross-matched in this audit. Do not claim exhaustive project-document completion.
- Clang's autogenerated crash reproducer files under `/tmp` have not been verified to persist; no T inspection or compile now.
- A specific native F2 pen/SPI2 observation case is **not yet implemented**, so neither a build nor six code-level tests alone can close F2.

## 5. Decision

**Do not issue a compile job yet.** First produce a true 012-C-plus-F2 candidate and aligned tests on the existing codebase using the audited manufacturer/guest register contract. In particular resolve the `0x2100` versus `0x0300` SPI2 enable-mask discrepancy explicitly, rather than presenting either behavior as universally qualified. Only then is one minimal incremental Clang run defensible. If the exact constrained source still crashes, isolate codegen before changing the entire compiler environment.
