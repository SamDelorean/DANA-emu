# UK1.5 PWM1 original-ROM native PASS (2026-10-26)

## Status

**Closed:** original Palm OS UK1.5 physical-mode PWM1 control `0xFFFFF500` read-modify-write. The previously unreachable operation `ANDI.W #$FFEF,($FFFFF500).W` executed and completed in the authentic ROM under the sole existing T DIAG. The CPU advanced to a **different Philips ISP1161 Host Controller** command. This does **not** establish Palm OS desktop boot.

## Trace-grounded hardware

- Original ROM Ghidra 12.1.3 in existing project `DanaUK15RelocatedTemp`, language `68000:BE:32:default`, from original SHA-verified private UK1.5. Transcript `work/uk15_qualify_20261025/rtc_20261026/ghidra_after_rtc.txt`:

```asm
1007F1EC [0278FFEFF500] ANDI.W #$FFEF,($FFFFF500).W
1007F1F2 [42B80260] CLR.L ($00000260).W
1007F1F6 [4E5E] UNLK A6
1007F1F8 [4E75] RTS
```

- Motorola [MC68VZ328UM](https://drive.google.com/file/d/1UuxWG0rYc0n7RoLerqYTt9mlBpU45L6Y/view), PWM1 control `PWMC1` at `FFFFF500`, RESET `0020` (FIFO available, PWM disabled); EN bit4. Crucially this is **not** the existing LCD contrast PWM register at `FFFFFA36`.
- Independent CloudpilotEmu/POSE source [EmRegsVZ.cpp](https://github.com/cloudpilot-emu/cloudpilot-emu/blob/master/src/cloudpilot/emulator/hardware/EmRegsVZ.cpp) initializes `pwmControl` to `0020`; `pwmc1Write` handles the same EN bit4 being cleared.

## Integrated in the existing DANA-emu

- Source in GitHub `main`: [commit `8c276b9e18d933996902b7b4abaa4d02fb07099a`](https://github.com/SamDelorean/DANA-emu/commit/8c276b9e18d933996902b7b4abaa4d02fb07099a), `src/mame/skeleton/alphasdana.cpp`.
- Registers precisely PWM1 `FFFFF500–FFFFF501` in physical-mode memory map; stored PWMC1 reset `0020`, save-state, FIFOAV hardware status and readback of write-only repeat bits. Original `ANDI.W` performs read of `0020` followed by write of `0020`; incomplete PWM audio and IRQ functionality is explicitly blocked, not faked.
- Persistent directed regression: `tests/pwm1_uk15_test.py`, [commit `8ba6af28b06389ff260bfb652ce55c67e4473d46`](https://github.com/SamDelorean/DANA-emu/commit/8ba6af28b06389ff260bfb652ce55c67e4473d46), downloads and compiles **the production handler bodies**, tests authentic RMW, word/byte masks, FIFO available and fail-closed unsupported audio/IRQ.

## Exact T verification after connection recovered

- **Preflight** original T source SHA256 `ebe6fd73f4f6df903a9d3946ef5c129c1cd8d9229def69d2276e6822eb927408`, operative `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`, private UK1.5 firmware `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`; all unchanged at preflight.
- Synchronized exact PWM1 GitHub commit into **only existing DIAG**, candidate code SHA256 `4f49394f900ce7717a2e4f0a24b05ad4b5ca49c5a500ebd6021cc6290c16625c` and persisted directed test SHA256 `cff45b76a4f4a9a622f5a0495bd4f30dd58036cc9412e410e8661416dfafb837`.
- Production-extracted Clang++21 C++ directed test **PASS**; uploaded/persisted independent test **1/1 PASS**, and existing regressions RTC, ISP1161 DC, CSD/ROP, PCTLR **4/4 PASS**.
- Original MAME build and link with Clang21 **PASS** return 0 in **19.68 s**, command `make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang-21 OVERRIDE_CXX=clang++-21 OVERRIDE_LD=clang++-21`.
- New staged candidate `source/danadiagd` SHA256 **`b090e572905a284ee840fa705aa35fbe3e47b52a60cc75b35da4a7dba4b8e04c`**.
- Installed **operative unchanged** `bin/dana-diag` SHA256 **`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`**.
- Native genuine unchanged private UK1.5 `-rom` test with bounded passive 1800-frame original observer; emitted:

```text
DANA_PWM1_CONTROL value=0020 enabled=0 fifo_available=1
```

- Palm Powered framebuffer persisted **4,161 dark pixels** throughout frames 60–240; CPU progressed past PWM1 at `1007F1EC`.
- Next first fail-closed hardware interaction:

```text
DANA_PHYSICAL_BLOCKED reason=ISP1161_COMMAND_UNIMPLEMENTED address=1f000002 data=0027 pc=10301a7e
DANA_PHYSICAL_CPU curpc=10301a76 ir=33fc sp=0007eb28 usp=00000000 sr=2700
```

This is an **ISP1161 HC command port** `0x1F000002` (host, not device). Command `0x27` is **not implemented and its register meaning has not yet been Ghidra/datasheet qualified in this increment**. Avoid inventing it. The CPU remains at this block through extended passive frames 360–1800; exit code 0 only means observer exit, not Palm OS graphical boot. PCM/PWM audio playback, PWM sample FIFO and associated interrupts not yet emulated.

- All T logs/evidence under sole DIAG `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag/work/uk15_qualify_20261025/pwm1_20261026/` including `pwm1_production_handler.cpp`, `directed_*.log`, `regression_*.log`, `build.log`, `native.err`, `native_metrics.txt`. No ROM redistributed, no Codex, no alternate branches or new DIAG.

**Next:** follow the original Ghidra instruction at `CURPC=10301A76` (ROM offset `0x301A76`), qualify Host Controller command `0x27` against Philips ISP1161 Rev03 in Drive and genuine HC driver code (Linux `isp116x-hcd.c`), implement only verified semantics and rerun native ROM. Palm OS desktop is still NOT BOOTED.
