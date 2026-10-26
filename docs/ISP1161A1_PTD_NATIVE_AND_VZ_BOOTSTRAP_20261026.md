# DANA-emu — ISP1161A1 PTD/SIE software transaction unit and VZ bootstrap hardware boundary (26 October 2026)

## Product result — integrated code, not an aspirational plan

The single `SamDelorean/DANA-emu` repository on **`main`** now includes a **reusable Philips Transfer Descriptor packet executor** from the ISP1161A1 documentation and connects that executor to the existing physical Host Controller's **SOF engine, internal 4 KiB RAM, ATL and two ITL partitions**. Existing HC/DC command/data interfaces and all earlier tests are preserved. Real MAME firmware and bus tests passed on the one T DIAG. The installed functional operative is untouched.

**This is genuine packet-engine implementation work, but not a claim to full USB silicon parity**: there are currently no independently emulated USB devices attached to the physical HC downstream ports, no USB DC payload/endpoint ping-pong transactions exposed through the guest's bus, no physical DMA transfer arbitration, and the ISP1161 INT1/INT2-to-VZ pins have not yet been physically qualified on the Dana PCB. The PTD transport can interact with a real virtual-device packet backend through a typed callback, but the emulated Dana has no configured backend, and returns a truthful timeout for an inoperative/unconnected USB endpoint rather than inventing enumeration responses. Do not call these unsupported features implemented.

### Hardware isolation / future native bootstrap

The **MC68VZ328 itself**, not the ISP1161, has a **bootstrap program in silicon**, specified in Motorola MC68VZ328UM §17.1–17.1.3:

- **Assert EMUBRK LOW and then reset** to select bootstrap mode, which has precedence over normal/emulation modes.
- Built-in bootstrap initializes UART1/UART2 at **19,200 baud, 8-N-1**, selects the UART that receives data first, responds with acknowledgement `@`, and accepts Motorola hexadecimal **B-records** for memory initialization, program load, and execution.
- The internal 32-byte instruction buffer is at **`0xFFFFC0`**. Bootstrap/ROM entry and RESET are separate from ISP1161 HC/DC MMIO at `0x1F000000–0007`.
- On UART2, TXD2 may initially be disabled; Motorola §17.1.3 documents enabling it through Port J `FFFFF43B01CF` record. Do **not** claim that USB itself enters bootstrap or that the Dana PCB brings out EMUBRK/RESET/UART signals before tracing the board.
- Documented USB may subsequently carry a custom loader **after** code is running and has initialized the external ISP1161; it is not a substitute for ROM-internal UART bootstrap. The MAME reset/bootstrap input strap, actual pins and onboard wiring remain independently unvalidated and were not modified in this USB increment.

Official Motorola manual: https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf, §17.1.1, pp. 17-1–17-3; Drive copy https://drive.google.com/file/d/1UuxWG0rYc0n7RoLerqYTt9mlBpU45L6Y/view .

## Precise Host packet-engine integration

**Standalone reusable codec** `src/mame/skeleton/isp1161_ptd.h`, commit [`71ff4d7`](https://github.com/SamDelorean/DANA-emu/commit/71ff4d79a9c175b73a47aa9b4781874989ce30c1) — original BSD-3-Clause implementation, not a transplant from GPL drivers.

Per Philips Rev03 §§9.3.1, 9.4.2 and Tables 4/5:
- Decode the authentic **8-byte PTD** fields: ActualBytes[9:0], CompletionCode[3:0], Active, Toggle, MaxPacketSize[9:0], EndpointNumber[3:0], Last, Speed, TotalBytes[9:0], DirectionPID (SETUP/OUT/IN), Format (iso/noniso), FunctionAddress[6:0].
- Execute a packet transport using **explicit typed `transaction` and `reply`**; statuses ACK, NAK, STALL, no response, CRC error, bitstuffing, bad PID, toggle mismatch. Update PTD Active, ActualBytes, CompletionCode and data toggle; NAK retains Active and does not fake a completed transfer.
- For IN, store actual data in the PTD's reserved payload bytes; for OUT/SETUP, supply guest buffer bytes. Support multiple PTDs and **4-byte DWORD alignment**. Bound-check every descriptor, 10-bit lengths and SRAM allocation.
- Respect `Last` PTD, isochronous one-packet frame bound and manufacturer B5_5 one-packet flag. On a disconnected root port, use timeout/DeviceNotResponding `CompletionCode=5`, and never invent an attached device/descriptor.
- A generic OHCI ED/TD decoder was **not** substituted for Philips PTD format.

**Connection to original MAME device** `src/mame/skeleton/alphasdana.cpp`, commit [`b423149`](https://github.com/SamDelorean/DANA-emu/commit/b423149df641d639298607ccc3e162b68d42c79f):
- On HC operational SOF, execute actually uploaded descriptors in the **on-chip 4 KiB HC RAM**. Preserve physical 68000 command/data protocol, 16-bit little-byte packing in ISP1161 FIFO despite big-endian 68k CPU.
- Route HC ITL0/ITL1 separately, model CPU-access ping-pong selection, route ATL after two ITL partitions; retain uploaded payload length per bank; reject out-of-range layouts and malformed PTDs explicitly.
- Update HcBufferStatus Full/Done, HcµPInterrupt flags and write back result PTD for the guest to read through PIO. Register all new RAM lengths/ping-pong state in MAME save-states.
- Defaults to two disconnected root-hub ports. No invisible fake devices and no automatic host-to-DC loopback. Real UART/Palm OS, RAM and LCD untouched.

### Actual functional proof (sole T DIAG)

`/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`

Before synchronization, source, installed operative and original UK1.5 firmware SHA were explicitly matched. Local source was synchronized to exact pinned GitHub commits. MAME Clang21 build/link PASS **19.2 s**:

- C++ packet-engine test [`tests/isp1161_ptd_engine_test.cpp`](https://github.com/SamDelorean/DANA-emu/blob/main/tests/isp1161_ptd_engine_test.cpp), commit [`7ef53bb`](https://github.com/SamDelorean/DANA-emu/commit/7ef53bb2ca50b49d1b6bfe2e907e1d762fceaf0e): PASS. Real original-code implementation tested USB SETUP/IN transfer, payload, ACK, NAK Active retention, STALL CC4, no-response CC5, CRC CC1, multiple DWORD-aligned PTDs and invalid SRAM bounds.
- MAME *native real physical bus* script [`tests/isp1161_ptd_native_bus.lua`](https://github.com/SamDelorean/DANA-emu/blob/main/tests/isp1161_ptd_native_bus.lua), commit [`d2740b3`](https://github.com/SamDelorean/DANA-emu/commit/d2740b32813f975fcc90fe4cb4513085482b0f7b): PASS on genuine 68000 program memory bus. Upload ATL 8-byte PTD + 8-byte payload via HC command/data ports, enable HC, wait SOF, verify ATL Full→Done, guest-read-back completion code CC5 with unchanged Length/PID/MPS/address. `ISP1161_HC_PTD_NATIVE_BUS_PASS frame=5`. No mock handler substituted.
- Prior ISP1161 HC/DC physical MAME bus **33/33 PASS** through `tests/isp1161_uk15_dc_test.py` (2/2), plus PWM1/RTC/CSD/ROP/PCTLR **4/4 regressions PASS**.
- Authentic untouched UK1.5 private ROM boot observed for **1800 frames = 30 simulated seconds**, observer exit 0, no `DANA_PHYSICAL_BLOCKED`. Original **palm POWERED** 560×160 framebuffer 4,161 active pixels, CPU loop around `0x1007B090` (PLLFSR CLK32 delay); no Palm OS graphical desktop validated. This is not a successful complete OS boot.

**SHA256 tested and recorded:**
- `alphasdana.cpp`: `02592fc46c46fad7e63410458c033d05cdd9db9a4feeed079508bdcb30b9a929`
- `isp1161_ptd.h`: `47ddafaae843b9fa4dfc2fc63c9719f6ea887bca6e440e7780d8b656dcdad614`
- C++ test: `844f090d460dd9eafca2f5cc63306081e590f05392d13bfa3cd7d487f8b5269d`
- Staged `source/danadiagd`: `a51fdbf2b660f74bc1065bff6e1eb3402554fe09c4c5c6da81a182c698d07f1f`
- Installed `bin/dana-diag` (unchanged): `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`
- Original private UK1.5 ROM (unchanged): `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`

Original physical bus result:
```text
ATL_FULL_UPLOAD got=0004 expect=0004
ATL_DONE_AFTER_FRAME got=0020 expect=0020
ATL_NOT_FULL got=0000 expect=0000
PTD_DISCONNECTED_CC5 got=5000 expect=5000
PTD_MPS_LAST_UNCHANGED got=0808 expect=0808
PTD_LENGTH_PID_UNCHANGED got=0808 expect=0808
PTD_ADDR_UNCHANGED got=0000 expect=0000
ISP1161_HC_PTD_NATIVE_BUS_PASS frame=5
```

All local evidence `work/uk15_qualify_20261025/isp1161_ptd_engine_20261026`, including source-hash preflight, build logs, directed C++ output, regression results, authentic UK1.5 trace, and native 68000 PIO readback.

## Exact honest remaining boundary

- The current typed PTD transport supports successful/failed packets in directed production-code tests; a **plugged-in emulated USB device backend is not yet connected** to Dana's HC root ports. Default deliberately disconnected.
- There is not yet USB DC upstream endpoint ping-pong payload FIFO, USB SETUP/IN/OUT negotiation with an upstream host, or verified external DMA and IRQ pin coupling to the DragonBall VZ on the actual Dana PCB.
- USB motor timing models transfer completion at HC SOF; this is packet-level timing rather than precise D+/D− PHY analog waveforms.
- Bootstrap: only an *electrical investigation* of EMUBRK/RESET/UART pin access and future CPU ROM-loader emulation can qualify using the manufacturer's bootstrap on a real Dana. It was not magically enabled through ISP1161.

**Do not create extra tasks/gates, alternate MAME builds or imaginary physical results. Treat all of the above as one verified integrated product increment and the missing USB capabilities as one architectural limitation, not an endless fault-by-fault campaign.**
