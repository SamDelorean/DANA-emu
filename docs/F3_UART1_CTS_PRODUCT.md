# F3 — Dana UART1 serial CTS and guest forward progress

**Product driver commits:** `b6dca55f61beec2315a6e309607cca7ade68c149`, `ec3c36bf158b657172494c700ce40cf57ace7f31`.  
**Production regression:** `tests/dana_hardware_test.py::Hardware::test_actual_uart_fifo_lanes_framing_interrupts_and_disabled_tx`, commit `d1ca6559dd40f606b7eb2d4709d093e62550f346`.  
**Previous native-qualified hardware:** immutable driver source `80cbfecab4df3c4412e370974295ac8a2f336fc1` (10 scoped PASS, unrelated to new F2/F3 source builds).  
**Current scope:** actual `src/mame/skeleton/alphasdana.cpp` product change on PR #7; no new device tree or guest modification.

## Reproduced source-level bug

The previous UART1 transmitter required either guest software UTX1.NOCTS or internal UMISC1 loopback to transmit. Its eight-byte TX FIFO could never drain in the no-CTS profile: `uart1_start_tx()` returned without even considering a physical/host CTS input. The fixed EmuTOS Dana guest `bios/dana.c` uses `dana_rs232_can_write()` (polls UTX bit13 TX_AVAIL) and `dana_rs232_writeb()` (writes a data byte). A full undrained FIFO can therefore block guest progress. No trace from the older two native runs proves that EmuTOS actually became blocked in this precise way.

The manufacturer **NXP MC68VZ328UM** specifies UART CTS1 on PE7 active low, UTX.CTS_STAT at bit9, and UTX.NOCTS at bit11. See `https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf` and the pinned guest source `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b`.

## Changes in real hardware model

- Add `UART1CTS` host input setting to select an explicitly **connected/ready virtual serial receiver** (active-low CTS, default for the emulator's serial-console profile) or **no cable** (CTS deasserted, genuine hardware backpressure). This describes a virtual accessory, not historical proof of Dana physical wiring.
- Read UTX1.CTS_STAT from the actual virtual CTS input; preserve NOCTS, FIFO and busy flags.
- Permit `uart1_start_tx` when *any* documented condition applies: asserted external CTS, software NOCTS, or hardware serial loopback. With the no-cable profile, guest-visible backpressure remains real rather than fabricating a received byte.
- Release a previously queued FIFO on a guest UTX status read if CTS has become asserted; debugger peeks never alter the shift engine.
- Also call `uart1_start_tx` following a **control-only UTX1.NOCTS write**, not only a new data byte, so firmware can release a previously blocked TX FIFO. Preserve asynchronous MAME bit/framing engine, TXD output, serial completion and IRQ rules.

## Qualification and boundary

- Production-source inspection checked input binding, CTS status, queue release and test fixture references.
- Expanded the *actual production-method extraction test* with deasserted CTS, full eight-byte FIFO, CTS transition, debugger peek, completion sequencing, control-only NOCTS release and loopback.
- An independently executed, **equivalent focused C++20 model** compiled with GCC `-Wall -Wextra -Werror -fsanitize=address,undefined` and passed. This is *not* the production extraction test nor a complete MAME build. The committed production extraction test has not been executed in a checkout in this intervention.
- Commander/T calls **zero**. No new MAME, EmuTOS, ROM or guest execution; no fourth native attempt.
- The new source is **F3_PRODUCT_SOURCE_IMPLEMENTED / NATIVE_PENDING**. EmuTOS full boot and native UART frame-completion PASS are **not claimed**. No current change to Timer1/IRQ6 behavior or existing LCD/ST controller.

**Next product goal:** integrate and build this source only under a separately scoped authorization, then measure actual EmuTOS forward progress, UART TX completion and IRQ6. The existing guest and earlier native evidence are to be reused, not rebuilt without a genuine dependency.
