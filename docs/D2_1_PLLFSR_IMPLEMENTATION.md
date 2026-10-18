# D2.1 — VZ PLLFSR first-hardware-dependency increment (2026-10-17)

**Status:** SOURCE IMPLEMENTED / ISOLATED C++ HANDLER TEST PREPARED / ACTUAL T MAME QUALIFICATION PENDING. No Commander calls are authorized or used in this increment.

## Trigger and preserved baselines

F1/E3 R3 compiled a real Dana MAME DIAG binary with Clang 21.1.8 and executed authentic EmuTOS-Dana twice with normalized-repeat PASS. Both halted at the same CPU-origin **16-bit read of 0xFFFFF202** from instruction PC **0x0000829A**. This is PLLFSR (not a generic unimplemented 4-KiB MMIO page). Its physical/register behavior is not inferred from the return value of an unmapped bus.

The original unmodified EmuTOS files and validated private mirrors are immutable inputs; **do not rebuild EmuTOS, CrossMiNT, BetaWise, Writer, or DictROM**. The previously real-qualified D1.2 RAM 9/9 and F1/E3 R3 smoke/RAM-01/RAM-08/MMIO-01 remain baselines. Do not rebuild stable MAME; DIAG exclusively.

## Primary authorities

- Motorola **MC68VZ328UM/D**, Rev 0, 02/2000, section 4.4.2/Table 4-4, [official NXP PDF](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf). PLLFSR is **0xFFFFF202–0xFFFFF203**, 16-bit, reset **0x0347**: bit15 CLK32 (read-only oscillator status), bit14 PROT (can be set, only hardware reset clears), bits13:12 reserved (0), bits11:8 QC, bits7:0 PC. Writes should be 16-bit, but byte access is possible.
- Section 4.3.1: VZ supports an external **32.768-kHz or 38.4-kHz** crystal; the latter is not inferred for Dana from this evidence. Current DIAG fixture deliberately chooses **32768 Hz**, explicitly not a measurement of the physical Dana board.
- Linux [MC68VZ328.h](https://codebrowser.dev/linux/linux/arch/m68k/include/asm/MC68VZ328.h.html) corroborates masks and exact address.
- Pinned MAME [mc68328.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.cpp) provides the actual `timer_alloc`/`refclk_tick` pattern. Its EZ **reset 0x0123 must not be copied** to VZ.

## Minimal source changes

- `src/mame/skeleton/alphasdana.cpp`: map **only** `0xFFFFF202..03` as a 16-bit handler. On machine reset set storage `0x0347` and CLK32 phase low. Allocate a scheduler timer and toggle CLK32 **once per virtual 32.768-kHz tick**; never toggle on reads or wall-clock time. Register the state for MAME save-state. Word or lane-selected writes can update the QC/PC mask `0x0FFF` only while PROT was clear; writing bit14 sets a sticky lock even if counters change in that same bus operation. Subsequent writes cannot clear PROT or change QC/PC; CLK32 remains read-only, reserved bits stay zero. PLLCR/Timer/GPIO/UART are *not* implemented or stubbed.
- `tests/f1_emutos_boot.lua`: recognize *only* the newly decoded PLLFSR address pair in the CPU-origin MMIO observer; unimplemented nearby addresses still trigger a real next-hardware-dependency stop.
- `docs/D0_2_EZ_VZ_REGISTER_CONTRACT.md`: correct the POSE-only 0x0123 historical value to Motorola's 0x0347 VZ reset.

## Binding test-emulator restriction (user directive 2026-10-17)

**Only Dana DIAG (`dana-diag`) is authorized to execute emulator tests. All other emulators are prohibited.** See the canonical [exclusive DIAG policy](https://github.com/SamDelorean/DANA-emu/blob/main/docs/DANA_DIAG_EXCLUSIVE_TEST_POLICY.md). The donor MAME is *source only*; `danadiagd` is merely the output name of the **same DIAG subtarget**, copied to the staged executable `.../diag/bin/dana-diag`; `asmdana` is its internal machine selector. Smoke, RAM, MMIO and authentic EmuTOS runners receive the **same staged Dana DIAG executable**; no stable, reference or other emulator may run. If executable identity is ambiguous, stop as BLOCKED.

**T dispatch preflight (same date):** Shared Drive `inbox` was occupied by unrelated `energy_r13a_r10_wake_trace_20261017.job.sh`. D2.1 remains in HOLD. No Commander calls consumed. Never execute, move or overwrite that unrelated job. User authorized at most **3** D2.1 Commander calls when the queue is exclusive.

## Verification and gates

1. `python3 -m unittest tests/d2_1_pllfsr_contract_test.py` from repo root: checks exact source map/observer masks and compiles the **actual production register read/write and timer handler methods** into a tiny bounded C++ harness. Tests actual arithmetic for reset, CLK32 phase, full-word writes, byte lanes, reserved bits, sticky PROT and reset-unlock. This is **isolated C++ handler semantics only, not a real MAME peripheral PASS**.
2. New future T campaign: pinned original MAME donor, updated DIAG driver only, `make -j3` Clang 21; no other MAME flavor. Run DIAG CLI smoke, impacted RAM-01/RAM-08 and MMIO-01.
3. Run two fresh EmuTOS-Dana guests with **the same authentic original package SHA**, preserve CPU register state/ordered bus, map-bound instruction trace, exact first PLLFSR access, subsequent progress and next genuinely unimplemented peripheral with address/width/PC.
4. Negative controls: corrupt image rejected before CPU fetch; no 24-bit alias of 0xFFFFF202; no blanket F2xx RAM; no fabricated guest completion. Compare normalized two-run results; PASS/FAIL/BLOCKED determined from actual native evidence.
5. **Do not mark D2.1 real PASS until independent Drive evidence reports compiled DIAG hash, successful tests, and CPU-origin PLLFSR access under the new native handler**. Later GUI, LCD, keyboard, SD and full PLL clock tree remain unimplemented.

**Rollback:** revert the small PLLFSR driver and the single Lua observer change on the DANA-emu branch. No private ROM, reference MAME source, or hardware configuration requires restoration.
