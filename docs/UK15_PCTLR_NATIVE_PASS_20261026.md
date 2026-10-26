# Original Palm OS UK1.5 PCTLR — manufacturer-backed native PASS (2026-10-26)

## Outcome

**PCTLR (DragonBall VZ Power Control Register) at physical 0xFFFFF207: implemented and original UK1.5 native CPU PASS.** The original ROM wrote 0x9F, which is **PCEN=1 with WIDTH=31/31**, so CPUCLK is continuously on. There is NO legitimate clock-suspension transition at this exact access. Palm desktop GUI is not yet demonstrated; the next independent USB device-controller command is explicitly blocked, not accepted with invented data.

### Sources and reverse engineering

- Manufacturer primary document: Motorola **MC68VZ328UM**, §4.5.4, Table 4-5, printed page 4-14, PDF page index 81, https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf. PCTLR is an **8-bit R/W register at 0xFFFFF207**, reset **0x1F**. Bits: PCEN bit7; reserved bits6:5; WIDTH bits4:0. With WIDTH=31 CPU clock is always enabled, whether PCEN is 0 or 1. When PCEN=1 with smaller WIDTH, actual CPUCLK burst/stop behavior would require a separate clock-gating implementation, and is not emulated or falsely marked PASS.
- Independent Linux kernel `arch/m68k/include/asm/MC68VZ328.h`: `PCTRL_ADDR 0xfffff207`, `PCTRL_PCEN 0x80`, `PCTRL_WIDTH_MASK 0x1f`.
- The previously completed **original Ghidra 12.1.3** instruction listing (same existing private UK1.5 Ghidra project, language `68000:BE:32:default`, base 0x10000000) proves:
```asm
1007D11C MOVEA.L #$FFFFF000,A0
1007D122 MOVE.B ($00000252).W,D0
1007D126 ORI.B #$80,D0
1007D12A MOVE.B D0,($0207,A0) ; PCTLR, physical 0xFFFFF207
1007D12E RTS
```
- Real native physical write from ROM at `CURPC=0x1007D12A`, data `0x9F`, bus word base `0xFFFFF206` low/odd lane `00FF`. Do not map the even neighboring byte 0xFFFFF206 as the PCTLR.

## Production implementation and validation

- Existing single `src/mame/skeleton/alphasdana.cpp`, commit **`51eef322326a45dc7f417db08ea23354b41abbae`**. Adds real stored `u8 m_pctlr=0x1f`, reset and MAME save registration, exactly one physical-mode 8-bit `.umask16(0x00ff)` map for `0xFFFFF207`, real readback, reserved-bit filtering, full-clock-width behavior.
- Original UK1.5 write of `0x9f` is accepted without CPU clock changes because full duty is physically documented; PCEN=0 allows all WIDTH settings without CPU throttling. Unimplemented PCEN=1 and WIDTH<31 modes are **fail-closed** with `PCTLR_CPU_BURST_UNIMPLEMENTED` instead of pretending the CPU keeps running.
- Directed production-handler C++20 test `tests/pctlr_uk15_test.py`, commit **`efe73b0fbddb46de7a96873bc6e705c74df72446`**, checks reset, 0x9F exact original write, 0xFF reserved mask ->0x9F, low/odd lane, state registration, rejection of partial clock and fully gated CPU, PCEN=0 continuous clock, reversion to 0x1F. **1/1 PASS** on the sole T DIAG.
- Preexisting regression `tests/csd_rop_read_protection_test.py` **1/1 PASS** (protected SDRAM window still works).
- Clang21 MAME incremental build/link **PASS**, return code 0, 18.88s.
- Exact tested source SHA256 **`7a6fcd54efb42ad60e8b64ad8b78eeaddd7e19115cc6a431f872cbf8b16cef6a`**, synchronized from pinned `main@51eef322`.
- Staged candidate `source/danadiagd` SHA256 **`e1d67fcd46fa4b5035728a1dd5ade49257e30691cf2003029d757460ac4a8d40`**.
- Installed operative `bin/dana-diag` SHA256 **`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`** unchanged.
- Original private `UK15_private.raw` SHA256 **`2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`** unchanged; updater-derived, NOR full geometry still unqualified.
- Sole canonical remote environment `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`; logs at `work/uk15_qualify_20261025/pctlr_gpt_20261025/` (`build.log`, `pctlr_uk15_test.py.log`, `csd_rop_read_protection_test.py.log`, `native.err`, `native_metrics.txt`, `ghidra_next_usb_exact.txt`).
- Exact native log from authentic original `-rom` execution:
```text
DANA_PCTLR value=9f pcen=1 width=31 cpuclk_full_duty=1
```
The CPU executed instructions beyond the previously fatal PC `1007D12A`; power-control access now **PASS native**. Original `palm POWERED` framebuffer still displayed at 4,161 active pixels in 60–240-frame snapshots, but this is not Palm OS desktop.

## Newly observed first real independent blocker

```text
DANA_PHYSICAL_BLOCKED reason=ISP1161_DC_COMMAND_UNIMPLEMENTED address=1f000006 data=00c0 pc=1008173e
DANA_PHYSICAL_CPU curpc=10081736 ir=33fc sp=0007ec76 sr=2000
```
**A new actual USB DEVICE-CONTROLLER command `0xC0`, not another power register.** Ghidra was run again in the same original T Ghidra project; after correcting an embedded-ROM-data false instruction boundary, original code at the true native `CURPC` is:
```asm
10081732 LINK.W A6,#0
10081736 MOVE.W #$00C0,$1F000006 ; USB DC command channel (A1=1,A0=1)
1008173E MOVEQ #0,D0
10081740 MOVE.W $1F000004,D0 ; DC data word 1, not executed
10081746 MOVEQ #0,D1
10081748 MOVE.W $1F000004,D1 ; DC data word 2, not executed
1008174E SWAP D1
10081750 CLR.W D1
10081752 OR.L D0,D1
10081754 MOVE.L D1,D0
10081756 UNLK A6
10081758 RTS
```
Source of this exact native-following disassembly `ghidra_scripts/DanaUK15AfterPCTLRExact.java`, `pctlr_gpt_20261025/ghidra_next_usb_exact.txt`. Do not falsely infer *which* ISP1161 DC read-only register command C0 selects without corroborating the official datasheet or implementing its actual 16-bit read protocol. No DC code was changed in PCTLR increment; the first observed next block is precisely scoped.

### Closed vs open

**Closed:** original PCTLR low-lane full-duty write and readback, correct mask/reset/save, source-extracted test, actual MAME build, native genuine firmware CPU advance.  
**Open:** first next USB DC command `C0` and its successive data-port reads; actual Palm OS desktop/GUI and visual validation of installed emulator. No Codex, branches, duplicated DIAG or ROM edits.
