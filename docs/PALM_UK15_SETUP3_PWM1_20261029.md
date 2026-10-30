2026-10-29 sound follow-up: original PWM1 now emits mono sound through MAME speaker_sound_device, with volume/mute options; see PALM_UK15_PWM1_AUDIO_20261029.md for verification and limitations.

# Original Palm UK1.5: Setup 3 mouse/CPU freeze fixed at PWM1

## Root cause (2026-10-29)
The mouse was not disconnected: the installed emulator halted the real 68000 CPU upon a legitimate Motorola PWMC1 write. Pre-fix native -log output after tapping Setup 3 Next:
DANA_PHYSICAL_BLOCKED reason=PWM1_AUDIO_OR_IRQ_UNIMPLEMENTED address=fffff500 data=5012 pc=1007f1c2
DANA_PHYSICAL_CPU curpc=1007f1be
Afterward CPU stayed at 1007F1BE despite additional PEN contacts.

Ghidra 12.1.3 of authentic UK1.5 (ROM base 10000000) identifies instruction 1007F1BE MOVE.W D0,($FFFFF500).W to PWMC1, with following accesses to PWM1 period/counter registers. The Motorola MC68VZ328 User Manual §§15.4.1–15.4.4 identifies PWMC1 at FFFFF500, PWMS1 at FFFFF502, PWMP1 at FFFFF504 and PWMCNT1 at FFFFF505. It specifies a 5-byte sample FIFO and hardware FIFOAV, IRQ and EN behavior.

## Hardware correction, one canonical driver
Within the sole existing source, src/mame/skeleton/alphasdana.cpp:
- PWM1 control register supports ENABLE, clock selection/prescaling, FIFOAV, IRQ status and IRQ enable.
- Five-byte sample FIFO and word/low-byte sample writes, PWM period and counter MMIO.
- Hardware-timed FIFO consumption and PWM1 bit7 interrupt source at VZ level 6 when enabled; disable flushes FIFO.
- Original guest ROM, guest PC, date/time setup and stylus events remain unmodified.
- Not yet qualified: audible PWM waveform output, full REPEAT timing, exact counter cycle simulation or new EmuTOS regression. These are not claimed PASS.

## Real guest observation and scope
Reproduced with original UK1.5 through tests/palm_uk15_setup3_click_probe.lua (PEN/PENX/PENY MAME input, not guest UI injection).
Frame 3510: Setup 3 of 4 (country/date/time).
First Next contact frames 3780–3840: frame 3900 displays Setup 4 of 4.
Second Next contact frames 4210–4270: frame 4400 displays Enter Data.
After 4800 frames original CPU still executes at 10079776, with no DANA_PHYSICAL_BLOCKED events.

Proof: ignored local-evidence/runtime-compare/setup3-pwm1-installed.log, setup3-pwm1-installed.out, setup3-pwm1-installed-{3510,3900,4400}.png.
Installed sole runtime/diag/bin/dana-diag SHA256 6615dbb0cde30d43c99de7eaba429213f62a70f9323c5e1b9b6ee8196a9c4f21.
Native guest progression PASS. Real SDL physical mouse must still be confirmed manually on T.

Run on T from graphical desktop:
/home/spc/Projects/alphasmart/DANA-emu/tools/run-palm-uk15.sh
