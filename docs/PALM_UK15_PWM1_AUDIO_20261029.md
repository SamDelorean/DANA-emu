# Dana PWM1 audio and sound menu — 2026-10-29

## Scope
One repo SamDelorean/DANA-emu main; single installed executable runtime/diag/bin/dana-diag. No standalone MAME versions. Unmodified original UK1.5 firmware.

## Physical sound output
The Motorola MC68VZ328 PWM1 PWMC1/PWMS1/PWMP1/PWMCNT1 guest-controlled model now drives the existing MAME filtered 1-bit SPEAKER_SOUND device as mono audio (0.30 base gain). A PWM period timer latches the sample from the hardware FIFO and raises the output. A second timer lowers the output according to its programmed duty cycle; disable drives output to zero. This is guest-generated sound, not an artificial beep or an injected Palm OS event.

Not certified: analog Dana board frequency response, full sample REPEAT semantics, counter cycle-level accuracy or other Dana audio hardware. They remain distinct future investigations.

## Integrated menu
The existing MAME Tab -> General Settings -> Sound Options menu now offers Volume (0 to 100% in 5% steps) and Mute (on/off), both operating immediately on MAME sound_manager. Existing Sound on/off, Sample Rate and External Samples remain. The Slider Controls -> Master Volume is still supported.

IMPORTANT: the authenticated Palm launcher intentionally creates an expendable temporary MAME machine CFG, preventing unwanted NOR/SDIRQ state overwrite. Volume and mute selections are session-only with this launcher (persistence is not yet engineered). Do not reintroduce stale CFG files.

## Tested
Installed sole dana-diag SHA256 c073e42e7368dcd6d9bdf87767316dddab3636edad87f08901d5d26f81b874e0, built on T with Clang 21.1.8 MAME 0.289. REGENIE=1 was used to regenerate the single-driver sound-device selection, including src/devices/sound/spkrdev.cpp.

Authentic UK1.5 on installed emulator via tools/run-palm-uk15.sh and tests/palm_uk15_setup3_click_probe.lua: captured true WAV at 48000 Hz, mono 16-bit, 79.98 seconds, peak 5980 and 3289 nonzero samples. Frame 3900 displays Setup 4; frame 4400 displays Enter Data; frame 4800 PC=10079776, and no physical blocks. Untracked local evidence under local-evidence/runtime-compare/pwm-audio-installed.wav/log/out. No private ROM copied to GitHub. No reimplementation of guest sounds as sampled host notifications.

Actual listening on the physical T output and human menu volume/mute interaction remain pending manual confirmation.

## Canonical source
- src/mame/skeleton/alphasdana.cpp is synchronized with runtime/diag/source/src/mame/skeleton/alphasdana.cpp.
- src/frontend/mame/ui/sndmenu.cpp and sndmenu.h mirror MAME frontend source files in runtime/diag/source/src/frontend/mame/ui/. They are a source overlay, NOT an alternate emulator.
- Minimal compilation: TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang OVERRIDE_CXX=clang++ OVERRIDE_LD=clang++ REGENIE=1.
- The compile-generated source/danadiagd is moved to the sole bin/dana-diag and not retained.
