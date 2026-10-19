# Dana integrated Timer1 / UART1 / IRQ service group

**Status:** source candidate committed; isolated source regression test added; no new full MAME/DIAG compile or guest execution authorized/performed in this increment.

## One genuine progression, not a chain of microgates

The previous 011 DIAG build **passed** on HP t640 with one native MAME build, 66 offline tests, two PFSEL A/B native PASS and two authentic EmuTOS guest processes. The original EmuTOS wrote a nonblank 560 x 160 framebuffer bearing `EmuTOS Version 20261017`. First new CPU-origin unsupported MMIO was at guest PC 0x8320, 16-bit TPRER write 0x0002 at 0xFFFFF602; later TCTL1/TCMP1 writes are only raw post-block tail, not independent milestones. Immutable private evidence [566,943-byte archive](https://drive.google.com/file/d/1n1PUdg9_FTN5BwGGWM7QtvmiHI1umqUl/view), SHA256 `bd144043cba255ebb3392bb9ccc836bb862798c2dca2ae0693dfdbc8df109341`. Do not rerun or modify 011.

New production implementation is IN THE EXISTING `src/mame/skeleton/alphasdana.cpp` MAME driver, reusing its true original CPU, 4 MiB RAM, ROM Quickload, GPIO, LCD, SPI2 and ST code, with NO copy of GPL EmuTOS/POSE program code.

## Primary pinned technical evidence

- [DANA D0.2 VZ register contract](https://github.com/SamDelorean/DANA-emu/blob/main/docs/D0_2_EZ_VZ_REGISTER_CONTRACT.md): Timer1 has six 16-bit registers **F600/F602/F604/F606/F608/F60A**, reset TCTL/TPRER/TCR/TCN/TSTAT=0 and TCMP=0xFFFF; UART1 has USTCNT, UBAUD, URX, UTX, UMISC at **F900/F902/F904/F906/F908**, 16-bit; UART1 prescaler F90A; corrected VZ UART baud register reset **0x0002**, not EZ/POSE 0x003F.
- [Pinned MAME donor](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.cpp) contains the actual DragonBall timer read/write/compare/prescaler/interrupt semantics (§ functions around lines 2641–2828), UART TX-ready (3033–3042), IRQ CPU-space acknowledge mapping (310–318), masking and IRQ line mapping (1145–1275). Its MC68328 Timer1 interrupt bit 22 **must not be copied** to the VZ, whose bit is **1** as evidenced directly in the original EmuTOS code below.
- [Pinned unmodified original EmuTOS-Dana](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c) reads PLLFSR and calculates `clock_frequency=(pc*14+qc+15)*0x8000`. Timer1 init writes TPRER, TCMP1, TCTL1=0x33 then clears IMR bit1 (IRQ6, `VEC_USER(6)`). UART1 init sets USTCNT RX-ready enable and clears IMR bit2 (IRQ4, `VEC_USER(4)`); guest tests UTX1 bit13 (transmit ready) then writes UTX1D low byte.
- [Pinned MAME CPU-space IRQ reference](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.cpp#L315-L317): VZ-capable 32-bit IACK `0xFFFFFFF0…FFFFFFFF`, low 8-bit lane returns `IVR | level`; MAME's `AS_CPU_SPACE` must be wired in addition to `AS_PROGRAM`.

## Integrated behavior implemented

- Timed Timer1 **compare only**: one MAME `emu_timer` scheduled per compare in virtual time, with frequency selected by VZ clock-source bits and prescaler `TPRER+1`. EmuTOS `TCTL=0x33` selects guest PLL-derived SYSCLK and IRQ enable, with a compare interval near 5ms for observed 0x0347/0x0002/0xD7E4 inputs. No host-wallclock polling or expensive per-oscillator-cycle callbacks.
- MAME donor-style Timer1 read-then-write TSTAT clear, maintained pending IPR source bit1, IMR mask/unmask, CPU **IRQ6**, VZ `IVR | 6` IACK in CPU space. IRQ4 similarly represents actual UART bit2 only; no RX events fabricated. TCR/capture/physical signal inputs and cycle-perfect free-running counter are **not** native-qualified.
- UART1 full register bank (USTCNT, VZ-specific UBAUD reset, URX no-data state, UTX ready/empty, UMISC, prescaler), including low byte UTX1D output logged as `DANA_VZ_UART1_TX`. No synthetic incoming serial character or UART interrupt.
- Save-state for new register fields and one deterministic scheduler timer reset. Historical PLLFSR/Port C/PFSEL, 32 GPIO bootstrap bytes, the guest-RAM LCD display and SPI2/ST remain present and unmodified.
- The E5 Lua and independent Python CPU bus observers now treat Timer1 and UART1 as implemented **only for a new SHA/source-qualified DIAG binary**. The old 011 immutable evidence is still evaluated against its original hardware shape. A subsequent CPU-origin unsupported address is discovered, never preselected.

## Guest CPU/TIMER virtual-clock alignment

The previous integrated driver had a **functional virtual-timing mismatch**: Timer1 used the original VZ PLLFSR-derived system frequency, but MAME's guest 68000 ran at a provisional 1,000,000 Hz. This would distort actual instructions executed per timer compare/IRQ. The source now calculates the clock once through `guest_system_clock_hz()` using the *pinned original EmuTOS* formula `(PC*14 + QC + 15)*32768`, feeds SYSCLK-sourced Timer1 and explicitly invokes the MAME 0.289 `device_t::set_unscaled_clock()` API when an **authentic EmuTOS guest** is loaded. Writes to PLLFSR refresh both guest CPU clock and Timer1 if applicable. For the existing independent **no-guest DIAG fixtures**, `DANA_VZ_CPU(...,1'000'000)` remains unchanged and no guest-specific clock override happens. Initial R-direct PLLFSR 0x0347 yields 33,161,216 Hz. The source-level C++ isolated Timer1/UART1/IRQ smoke has been recompiled with `clang++ -std=c++20 -O2 -Wall -Wextra -Werror` and completed `TIMER_UART_IRQ_ISOLATED_CPP_PASS` including the extracted PLL clock calculation. **This does not qualify a newly compiled full MAME driver, guest progression, IRQ delivery or LCD presentation.**

**Launch block:** Historic 011 passed with the older driver; the pre-existing Git HOLD job `012_dana_integrated_timer_uart_irq_diag.job.sh` is frozen to the **previous** Timer/UART source `b0e0c501796b0cff4d6b827e0c6b7c402aaf0e4a` and must NOT be used to qualify the new CPU-frequency source. The additional fail-closed Timer1 verdict and UART-transmit narrowing change to job 012 was refused by a safety check. It was **not** repeated or bypassed. Do not dispatch 012, and never update that refusal by a different transport method. Preserve the existing 011 immutable evidence and the remaining canonical workflow.

## One future grouped qualification, no isolated register campaign

The next single authorized build should test all grouped subsystems using **one** newly compiled `SUBTARGET=danadiag` with the previous pin-verified MAME donor, no EmuTOS rebuild. It should retain the 011 PFSEL/guest provenance gates, source test C++ smoke, and two genuine original EmuTOS-Dana processes. Separate verifiers must report:
1. actual CPU Timer1 programming (TPRER/TCMP1/TCTL1), IRQ6 acknowledge/vector and timer status/counter as seen;
2. actual CPU UART1 accesses and debug bytes, without claiming virtual serial RX;
3. nonblank guest-owned LCD framebuffer and whether original on-screen text continues;
4. SPI2/ST and keyboard only if real CPU transactions occur;
5. first **new** unsupported peripheral after Timer/UART, no guessing and no claiming post-block tail.

**Do not label full EmuTOS boot, MAME GUI display, interactive keyboard, UART RX, or IRQ6 delivery PASS from mere static tests or register writes.** Full emulator build/native execution require a new explicit Commander/build authorization. The previous 3-call budget was exhausted in campaign 011.
