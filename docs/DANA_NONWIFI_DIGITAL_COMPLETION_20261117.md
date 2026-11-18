# Dana — non-Wi-Fi digital VZ completion, single integrated intervention

Scope: one existing `dana-diag`, no Wi-Fi/radio, SDIO or USB-PC communication.
Manufacturer authority: MC68VZ328UM §§5.2.2, 9.6.6, 15.1, 15.5.

## Added source-backed digital behavior

- Real VZ 16-bit **PWM2** registers `0xFFFFF510–0xFFFFF517`, without PWM1 FIFO duplication; period/width/counter, SYSCLK prescaler divided by 4–512, self-clearing LOAD, status IRQ read-to-clear, ISR/IPR source bit13 and ILCR PWM2_LEVEL bits6:4.
- Manufacturer-defined **PCR** bits0:4: UCLK selection, four logical combinations of PWM1 and PWM2 on PWMO1/PB7, and the documented TIN/TOUT routing selection bits. The timer routing register is stored; **physical PB6 TIN/TOUT net and cascaded timers remain unqualified** until source/PCB evidence permits faithful behavior. No fictitious cascaded tick input is generated.
- PWM2 dedicated **PWMO2 / PK0** digital output only when K0 is peripheral-selected and output-driven. It does not connect a guessed speaker or Wi-Fi module.
- Preserve the already qualified default PCR=0 PWM1/AlphaWord audible signal, keyboard ST, ADC, SD, USB, UART and all native H1–H8 evidence.

## Explicit remaining limits, NOT claimed PASS

- Physical Dana not available: NOR U7 topmark, SD pin-detect and orientation, LCD/audio/charging analog nets, RESET/EMUBRK/J100 continuity unmeasured.
- This intervention does **not** implement an actual radio, SDIO responder, PC enumeration, unknown silicon ICE breakpoint fabric, unverified CS upper decoding, B-record serial bitstream/read-back, SPI1 TEST/sample silicon modes, timer TIN/TOUT external capture/chain, or arbitrary non-Dana MMIO. They must not be faked by accepting writes or inventing a PCB level.
- PWM2 / PCR are silicon-complete **within the bounded digital behavior tested**, not physical loudspeaker/channel fidelity or a total silicon datasheet certification.

Acceptance requires one Clang21 MAME build, new real 68000 PWM2/PCR guest test (CPU writes all MMIO, Lua observes only), affected original PWM1/H2/UART/USB regressions, installed-binary re-test, SHA verification, single Git main commit and Drive receipt. If any fails, do not claim delivered or replace the operative without recovery.

## R4 native acceptance (2026-11-18)

The first PWM2 test used a 16-tick period and mistakenly expected the IRQ
source to stay clear while PWM2 continued to roll over. The corrected
68000 guest test disables PWM2 before reading/acknowledging PWMIRQ. No
physical GPIO or board-specific signal was assumed. Candidate PWM2 and
affected PWM1/VZ/UART/USB/LCD regressions passed before binary replacement;
installed PWM2 and PWM1 were retested. Missing stock commercial Flash,
untested ICE/bootstrap modes, USB Computer PC enumeration, analog rails
and real PCB nets are **not claimed complete**. Wi-Fi/SDIO remain excluded.
