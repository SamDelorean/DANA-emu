# F2 — Product increment: Dana stylus and SPI2 digitizer

**Production driver:** `src/mame/skeleton/alphasdana.cpp`, commit `9e870229afe6eff4b18eba7bf849fb3bb740cc84`.  
**Regression test:** `tests/dana_hardware_test.py::Hardware::test_actual_stylus_gpio_and_12bit_spi2_adc_path`, corrected test commit `f0a1c1890e4297b2ba3649ad755f8b0e8a0bdc9a`.  
**Branch / PR:** `codex/dana-d1-2-ram-bus` / #7. No new emulator or guest source.

## Exact guest contract

Pinned EmuTOS `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b`, `bios/dana.c`, identifies an active-low pen IRQ on PF1, PG2 pen SPI chip select and separate PE3 ST keyboard chip select. `pen_send_recv` sends an 8-bit `0x90` or `0xd0` command (`SPICONT2=0x2347`) followed by a 16-bit data read (`SPICONT2=0x234f`); `dana_ts_rawread` extracts `SPIDATA2 >> 4`. EmuTOS polls eight measurements and applies its own calibration; do not synthesize Atari mouse events.

## Implemented in the real MAME driver

- `PEN` mouse-button contact and absolute `PENX/PENY` MAME host ports.
- GPIO PF1 active-low input reflecting contact, while output-mode latch remains unchanged.
- GPIO PG2 chip-select handling, command/sample invalidation at deselect.
- Bounded 12-bit ADC sample, latched for a single eight-clock command + sixteen-clock read transaction.
- Explicit selection between existing eight-bit SPI2/ST keyboard on PE3 and new SPI2 pen ADC on PG2. Neither an unselected nor overlapping device receives a fabricated conversion.
- Save-state and reset coverage for command/sample.
- No modification to CPU, RAM, timer/IRQ implementation, existing ST scan code table, guest image, SD empty slot, LCD renderer, donor MAME or AS2K.

**Known limitation:** Provisional emulator X mapping [290,3760] and Y mapping [200,3650] over 16-bit normalized host positions. These are plausible ADS7846-compatible defaults, *not documented Dana factory calibration*. The exact guest calibration and live analog accuracy remain unqualified. Device protocol format is supported by TI ADS7846 documentation; physical component identity has not been independently confirmed.

## Qualification, evidence, and nonclaims

Added a directed regression that extracts and compiles real production methods under C++20 ASAN/UBSAN for contact, PF1 input/output, X/Y endpoints, active-low chip select, 8/16-bit protocol, unsupported/out-of-order phases, pen release and existing ST path.

A separate stand-alone equivalent C++20 logic smoke on the working computer **PASS** (`-Wall -Wextra -Werror -fsanitize=address,undefined`). That smoke is NOT the complete MAME build and does NOT establish execution of the committed extraction test; the new test has not been run in a repository checkout in this session. No Commander, MAME, ROM, or EmuTOS execution. Old ten native PASS results remain tied exclusively to the previous immutable driver revision.

**Next product step** when separately authorized: build one new `dana-diag` binary from this changed source and verify host pen -> PF1 -> PG2/SPI2 -> EmuTOS mouse packet. Continue to prioritize genuine OS boot and usable display, not additional speculative instrumentation. The original 012-C `restored.ram` mismatch must not be modified or concealed.
