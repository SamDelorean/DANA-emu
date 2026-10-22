# F4 — UART1 CTS status, FIFO BUSY and IRQ4 (product code)

**Branch/PR:** codex/dana-d1-2-ram-bus / #7
**Production commit:** 1cebf6743099c68622e1707541489bde866001db
**Regression commit:** 2256eaefbb3396d312aaa1d76e06fa6349efaf46
**Previous product F3:** UART1 configurable virtual receiver CTS and queued NOCTS release.
**Old native-qualified source (unchanged):** 80cbfecab4df3c4412e370974295ac8a2f336fc1.

## Demonstrated defect in the driver

The F3 UTX register read reported BUSY only while a shift register was actively transmitting, returning **not busy with up to eight bytes stalled by CTS**. The source also masked out the writeable CTS_DELTA bit8, and UART IRQ4 never recognized the USTCNT.CTSD interrupt enable bit6. The F3 CTS-resume read did not recompute IRQ thresholds after dequeuing a byte.

This is a software-defined hardware-model defect, not proof that EmuTOS encountered the issue within the previous two bounded runs.

## Implemented on the actual emulator

- Preserve read-only live UTX1 CTS_STAT (bit9) and report BUSY (bit10) whenever **either** transmitter busy or FIFO nonempty, even when CTS blocks progress.
- Maintain a save-state backed previous physical CTS level; detect edge on guest register sampling and latch CTS_DELTA bit8. Debugger peeks do not latch status, start TX, or change IRQs.
- UTX high-byte status writes control CTS_DELTA correctly (write 0 clears, write 1 sets). Unrelated status bits remain read-only.
- USTCNT CTSD enable bit6 and CTS_DELTA bit8 now contribute to the existing UART IRQ4 producer, alongside RX and TX thresholds. Disabling CTSD removes only its contribution.
- Recompute IRQ thresholds if a guest UTX status read starts a queued frame after CTS becomes asserted. No fabricated UART RX data.
- Preserve F2 stylus, keyboard ST, LCD, Timer1/IRQ6, SPI1/2 and the original EmuTOS guest.

**External CTS sampling limitation:** changes are detected when the guest accesses UTX; there is not yet an independent host-edge callback delivering an asynchronous interrupt before any guest register access. Native IRQ4 edge timing is not qualified.

## Evidence boundary

The regression in `tests/dana_hardware_test.py` now covers FIFO BUSY with eight blocked bytes, CTS readback, sticky CTS_DELTA, software acknowledge/set, CTSD IRQ4 masked/unmasked, pending transitions, debugger peeks, CTS-driven TX resume and NOCTS release. It extracts the existing UART production method region.

On the local working container a focused subset of the production C++ methods (with a simplified, RX-empty test double) compiled with `c++ -std=c++20 -Wall -Wextra -Werror -fsanitize=address,undefined`, and executed **PASS** covering CTS Delta IRQ4, BUSY, blocked FIFO, NOCTS and debugger peek. This does **not** establish the entire production test suite passed or a full MAME binary compiled.

**Commander/T calls:** 0. **New MAME/EmuTOS runs:** 0. **Fourth native attempt:** not authorized. **Full boot:** not accredited.

**Primary source:** Motorola MC68VZ328UM section 14.4 and MC68VZ328UMAD section 1.8.3 correcting UTX bit9/10 access types, available at https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf ; Linux MC68VZ328.h UTX bit definitions at https://codebrowser.dev/linux/linux/arch/m68k/include/asm/MC68VZ328.h.html .

**Next work:** Continue genuine EmuTOS startup and interface development using existing sources. When separately authorized, compile this accumulated F2–F4 product driver incrementally and qualify real UART completion/IRQ6/host input on the exclusive dana-diag binary, with a single bounded native campaign rather than per-feature jobs.
