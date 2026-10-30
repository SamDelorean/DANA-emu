# Palm UK1.5 three-point digitizer calibration — 2026-10-29

## Canonical scope
- One repo: SamDelorean/DANA-emu, main.
- One executable: runtime/diag/bin/dana-diag.
- Original ROM UK1.5 unchanged, no OS patches, no synthetic guest UI navigation.
- Ghidra 12.1.3 and native CPU traces were used to diagnose the hardware rather than bypass calibration.

## Exact root cause
Original UK1.5 68000 code at 0x1007B166–0x1007B176 and 0x1007F574–0x1007F582 shifts 16-bit SPI2 ADC samples RIGHT by 3, then masks the lower 12 bits. The former emulator packed its replies LEFT by 4, causing a doubled sample and a wraparound. Example original CPU-owned RAM measurements before the fix: horizontal left/center/right 742, 4050, 3234, which is not monotonic. The two ADC axes of the original Palm digitizer are inverted relative to the screen. The ROM rejects calibration when their direction is wrong or when the third off-diagonal point exposes a nonlinear response.

Hardware solution in src/mame/skeleton/alphasdana.cpp:
- Palm 7+1+16-clock SPI2 uses sample LEFT shift of 3; both X and Y ADC axes are reversed relative to input host screen coordinates. Do not swap axes.
- EmuTOS 8+16-clock path retains previous noninverted X/Y and sample LEFT shift of 4. That previous ABI is not deliberately changed; an independent EmuTOS native regression was not performed during this task.
- Track/reset/save the Palm 7-bit command phase in device state. Preserve host stylus PG1, external IRQ5, SPI2 guest clocking and the original ROM control flow.
- Early original-ROM A4/E4 ADC probing commands are supported; actual Palm setup contact uses 90/D8. The diagnostic flags explored during root-cause analysis were removed from production code.

## Native original-ROM PASS and limits

Test: tests/palm_uk15_calibration_complete.lua drives only genuine MAME PEN, PENX, PENY inputs, with no guest program counter manipulation. User-level targets: upper left, lower right, and top center at approximately (280,65).

Frame 2340: crosshair upper-left, framebuffer FNV B0F9EEA1.
Frame 2690: crosshair lower-right, framebuffer FNV F561FF90.
Frame 3030: crosshair top-center, framebuffer FNV CE7658B3.
Frame 3370 and frame 3510: original Palm Setup 3 of 4 screen, showing country/time/date settings. The visible title pixels were compared to the independent PASS image; full-frame hash varies naturally with the host-derived time of day.

Real code and installed sole dana-diag both independently PASS. Installed executable SHA-256: 787c4ccb55d8e8b0c00c6fb6a46f01234728a16319886d465beefc6f6242f5e5.
Ignored local evidence: local-evidence/runtime-compare/calibration-clean-native.log, calibration-clean-native-3370.png, calibration-installed-native.log, calibration-installed-native-3370.png, and Ghidra ghidra-calibration-control.txt.
Source scripts: tests/ghidra/DanaPalmUK15CalibrationBranch.java and tests/palm_uk15_calibration_probe.lua.

Manual test command from T graphical desktop:
/home/spc/Projects/alphasmart/DANA-emu/tools/run-palm-uk15.sh

At Setup 1 tap anywhere, at Setup 2 tap to begin calibration, then tap the three displayed target centers. Expected Setup 3 of 4. Real desktop mouse event path remains pending user confirmation; Setup 4 and final Palm launcher remain out of scope of this pass.

## 2026-10-29 subsequent independent blocker

Setup 3 mouse inactivity came from a physical PWM1 halt, not a regression in the PG1/IRQ5/SPI2 digitizer. Original ROM now progresses through Setup 4 and Enter Data using PWM1 MMIO; see PALM_UK15_SETUP3_PWM1_20261029.md.
