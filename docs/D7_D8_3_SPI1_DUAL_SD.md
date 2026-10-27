# D7/D8.3 — Integrated VZ SPI1 and two independent SD slots

2026-10-24. **IMPLEMENTED / STATIC_PASS / NATIVE_PENDING.** One integrated change in the existing checkout, directly on the canonical `main` ancestry. No new branch, clone, tree, emulator, executable, Commander call, T operation, firmware change or native campaign.

## Baseline and preservation

Base: `4275fb76156a6b8e41d60935142ed7d28eb9c8b0`. Its DIAG driver SHA-256 is `5b8d3ae5f7a01034241aa448b77eb4803f6c2dc8ac79d7dc50ad851f6436ddee`, matching the user-reported installed D8.5 source. Installed binary reported by the user: `7cfb5a7306b27d8a19d5110d0b71e16d12336fb33dcab143ce2154b2205a983c`. Neither T nor that executable was accessed or modified. D8.5's native build, RAM smoke and diagnostic Flash/RESET results remain accredited within their recorded scope; they are not SD evidence or authentic Palm boot evidence.

Existing physical reset, Flash loader/decode, original vector acquisition, RAM loader, LCD, Timer1 callbacks, UART, SPI2/ST and pen exchange functions are byte-identical. PB/PK handlers retain their original ST behavior and add only an SD-line notification. PF1 pen handling and PG2 ADC selection remain unchanged. Existing mappings/save fields are retained; new SPI1/PD/ILCR entries extend them. Neither SDL source nor GUI-025/026 patches are changed. No closed native campaign was repeated.

Production files:

- `src/mame/skeleton/alphasdana.cpp`: controller MMIO, per-bit MAME scheduler, GPIO coupling, interrupt routing, device configuration.
- `src/mame/skeleton/alphasdana_sd.h`: driver-local SD SPI protocol and FIFO state, independent of CPU and host filesystem.
- `src/mame/skeleton/alphasdana_sd_image.h`: two MAME read-only raw image devices and immutable-media snapshot validation.

## Implemented CPU-to-media path

CPU MMIO → VZ SPI1 FIFO/XCH → scheduled serial bits → selected/powered slot → SD SPI command/data tokens → exact sector reads from that slot's MAME image interface → MISO → RX FIFO → guest CPU. No host-side FAT, VFS, GEMDOS or guest system-call replacement exists.

| Register | Implemented behavior |
| --- | --- |
| `FFFFF700` SPIRXD, 16-bit | Pop RX FIFO; debugger inspection does not pop. Empty reads retain last received register value. |
| `FFFFF702` SPITXD, 16-bit | Lane-aware TX latch/enqueue when enabled; bounded eight-word FIFO. |
| `FFFFF704` SPICONT1 | Enable bit9, master bit10, XCH bit8, 1–16 bits, MSB first, rate bits15:13. XCH drains queued words and clears when empty. Disabling cancels the transfer and clears FIFOs. |
| `FFFFF706` SPIINTCS | High-byte enables; derived RX/TX thresholds and empty-to-nonempty RX latch; status read clears that latch, debugger reads do not. Pending bit21 routes through ILCR to levels1–6. |
| `FFFFF708` SPITEST | TX/RX FIFO occupancy; nonzero diagnostic/test-mode requests stop explicitly. |
| `FFFFF70A` SPISPC | Lane-aware register; nonzero sample-mode requests stop explicitly. |

Register/control latches reset to zero; FIFO status is derived from occupancy (TX empty when empty). Each serial bit consumes `4 << rate` SYSCLK ticks, using the existing clock formula and MAME scheduler, with the control word latched for that transfer. SD modes0/3 are supported; other phases, disconnected PJ SPI mux, overflow, simultaneously selected powered cards and unqualified sample/test modes stop with `DANA_SPI1_BLOCKED`, without successful card data. Clock/power electrical timing is not native-qualified. SPI slave operation has no external clock source and is inactive rather than pretending to execute master transfers.

| Slot / CLI | GPIO output power | Active-low CS | External input |
| --- | --- | --- | --- |
| 0 / `-sd1` (`-sdcard1`) | PB5 | PJ3 | PD2 / INT2 |
| 1 / `-sd2` (`-sdcard2`) | PK5 | PF2 | PD3 / INT3 |

Power and CS require the appropriate GPIO direction and selection. Turning off one card resets only its protocol state; CS release aborts its partial frame and streaming transfer but preserves initialized card state. Every bit resamples the GPIO connection. Existing ST reset/wakeup on PB6/PK2 remains intact.

**IRQ evidence boundary:** the original port identifies PD2/PD3 as SD IRQ, but neither it nor pinned Retro68 proves the external circuitry, insertion-switch semantics or assertion polarity. Ordinary SD SPI reads do not themselves generate SDIO-style asynchronous interrupts. Consequently image insertion never fabricates a PD interrupt. Two explicitly labeled external pin-level settings expose PD2/PD3 independently, initially high/released; these are test inputs, not a measured Dana board state or claimed card-detect implementation. PDDATA reflects them on input pins; PDPOL/PDIRQEN/PDIQEG implement level/selected-edge INT2/3 pending, PDDATA writes acknowledge latched edges, and IMR gates IRQ4 alongside the unchanged UART source. The undocumented board-level association of insertion with these pins remains **UNVERIFIED**. Image-device insertion/ejection status is independently real. PDKBEN is retained as a latch; a keyboard-interrupt model is not claimed.

## SD protocol, media and safety

- Two separate device instances each own command parser, wire shift state, initialization, capacity, transfer buffer, current sector, write-protect status and selected image. Neither can read the other slot's object or buffer.
- Require a raw image with exact 512-byte-sector length and capacity representable by the implemented SDSC CSDv1 or SDHC CSDv2, at most32GiB. SDSC uses exact C_SIZE/C_SIZE_MULT with READ_BL_LEN9; otherwise accept exact 1024-sector units as SDHC. Reject zero, incomplete-sector, unrepresentable or oversized media, CHD and known DANARAM1 wrappers. No guessed CHS, rounding, padding, repartitioning or filesystem changes. Extension is not proof of image type or provenance; keep Flash/RAM packages separate and select a genuine sector image.
- Power-up requires at least74 clocks with CS released and MOSI high. Implement CMD0, CMD8/R7, CMD55+ACMD41, CMD58/OCR, CMD59/CRC, CMD9/CSD, CMD10/CID, CMD13/status, CMD16(512), CMD17, CMD18 and CMD12. SDSC byte addressing and SDHC block addressing are distinct. CID identifies a virtual MAME/Dana card rather than impersonating a real manufacturer.
- CRC7 is checked for CMD0/CMD8 and all commands after CMD59 enable; CSD/CID include CRC7 and data blocks include CRC16. Ready-state reads require successful initialization. Invalid commands/addresses and failed or short backend reads return protocol error responses/tokens, never stale or zero-filled success data.
- **Read-only is the only implemented media policy in this delivery.** MAME opens both originals read-only; there is no write or create path, copy-on-write file or hidden replacement. CSD advertises temporary write protection. CMD24/CMD25 consume the supplied data/CRC then reject it with write-error token; CMD13 reports WP violation. Writable images, erase/program and SDIO are not implemented or claimed. This satisfies initialization/identification/sector reading and safe write protection, not write qualification.
- MAME Image Devices provides independent selection/path and inserted/ejected state. Options `-sd1`/`-sd2` map to slots0/1; physical left/right labeling is not inferred from numeric pins. Use MAME `-writeconfig` with the normal existing INI path to retain both assignments; ordinary XML config saves browsing directories only. Deliberate UI eject clears that slot's option on normal config write, discards partial wire state and does not reset the CPU or other card. Original images require no flush because no writes occur.
- All controller/card/partial-bit/IRQ state is saved using MAME, including scheduled timer state. Full-file SHA1 (MAME hashing API) and exact length bind each slot to its original read-only media; fingerprinting uses64KiB of temporary memory. Save and restore reject changed presence, mismatched bytes or short reads. A wrong image of the same size/filename is rejected; content is never embedded in public Git. A large image requires a full scan on mount/save/restore. External changes during execution can produce I/O errors and are not a supported editing workflow.

## Source-to-decision evidence

| Immutable reference | Used facts / limits |
| --- | --- |
| `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b`, `bios/dana.c` (SHA256 `5c70f2ea282e3cf7d86db04048d8dd00505ec19f2498bccb2da53d447a97b47a`) | Exact register group, byte GPIO lanes, PB5/PJ3/PD2 and PK5/PF2/PD3 labels, active-high power, active-low CS, PJ mux, 0607 control, XCH/polling. Guest initializes/selects only slot0; no EmuTOS changes. It does not prove IRQ wiring or the SPI1 clock-divider comment. |
| Same pin, `bios/sd.c` (SHA256 `9e0d11b88a5eb74fe46ba94cebd57199c0ceed84ae57f24a5d23537ee1fb6f48`) | Actual guest command flow, R1/R3/R7, CSD/CID, byte/block addressing, multiblock stop, CRC/token consumption and write-error handling. No GPL guest code copied. |
| Existing `D0_2_EZ_VZ_REGISTER_CONTRACT.md`, Motorola UM + addendum | VZ SPI1 six16-bit registers at700–70A, not EZ/SPI2, 16-bit RX/TX erratum, PD registers and ILCR reset6533. Existing completed research consumed; no new manufacturer-document retrieval claimed. |
| `cloudpilot-emu/cloudpilot-emu@064d5d578bcd1f9072de384d05aa217f83db2f7f`, `src/cloudpilot/emulator/hardware/EmRegsVZ.cpp` | Secondary implementation confirms FIFO depth8, masks/thresholds, read-cleared RX latch, interrupt bit21/ILCR field, divider `4<<rate`, FIFO counts, PD level/edge interrupt model. The EmuTOS comment says divide8 at rate0; source code/reference model uses4. Timing remains native-unqualified. GPL code was inspected for facts, not pasted. |
| `csnover/Retro68@d917b67b16bef7bcf5c75a74f617710c32addcbc`, `PalmUtils/poser/SrcShared/Hardware/EmRegsVZAlphaSmart.cpp` | Its PortD inputs are placeholders, so they cannot establish Dana socket insertion polarity. No borrowed NEO wiring or invented switches. |
| `SamDelorean/mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`, `src/devices/machine/spi_sdcard.{cpp,h}`, `imagedev/harddriv.*`, `src/lib/util/harddisk.cpp` | BSD SPI bit/command/data-token/CRC and removable-media infrastructure reference. Existing donor was inspected read-only. Direct donor attachment would guess raw CHS capacity, ignore some failed reads, fail to reset power state through its public API and omit media identity/state fields. Keep MAME image/config/save/scheduler infrastructure, implement the bounded read-only raw adapter locally without altering donor devices or generic MAME behavior. No second emulator. |
| Same MAME pin, `src/emu/{diimage.*,image.cpp,emumem*}` | Native image selection/names, read-only file access, INI assignment persistence, lane-aware MMIO and save-state integration. Driver syntax checked against these actual APIs. |

Linux `v6.12` MC68VZ328 header was an auxiliary address/source-bit cross-check, not an implementation dependency or a replacement manufacturer pin. The existing canonical source lock is unchanged.

## Checks actually executed

`DANA_MAME_REFERENCE=/path/to/pinned/mame python3 tests/d7_sd_test.py`: **12/12 PASS**, no skips/errors/failures. Exact command output is in `tests/d7_sd_static.log`; `tests/d7_sd_status.json` identifies source/log hashes and native limitations. The reference path can be supplied explicitly; no hardcoded cloud path is required by the implementation or build.

- Whole driver C++20 `-fsyntax-only -Werror` against pinned MAME: PASS.
- Six production-protocol/FIFO `static_assert` groups and an extracted production GPIO/IRQ `static_assert`: PASS. Negative controls include missing initial clocks, invalid CRC/commands, invalid geometry/address, failed I/O, removal, write rejection, FIFO overflow, half-frame CS/power and save/restore of an in-progress read. They manipulate component data at compile time, not firmware or CPU instructions.
- Exact unchanged existing function bodies, original maps/save fields, PortC/PLL and GUI patch preservation: PASS. Existing ST handlers differ only by the required SD-line notification. Historical D8.5 source-specific test files/results remain unchanged; this suite verifies D8.5 preservation on the current integration rather than reopening its original campaign.
- Python syntax and final Git whitespace/integrity checks: recorded with the delivered status. No object, guest image, disk image, executable or MAME binary was generated.

**Native result: PENDING.** Neither CPU-origin SD commands nor actual EmuTOS filesystem access has been run on the modified driver. Static protocol checks cannot establish runtime MAME construction, media UI behavior, IRQ delivery or end-to-end guest disk access. Unchanged EmuTOS only exercises card0; card1 needs independently sourced CPU code/firmware that actually selects PF2 and powers PK5. Do not claim both cards were guest-qualified because their component tests passed.

## Same-DIAG integration and one next action

After **fresh explicit T/build/native authorization**, verify the installed baseline source/binary hashes above, place all three production files together in the existing canonical `src/mame/skeleton` directory and incrementally compile/link the **same** DIAG with its current qualified Clang21 command/cache. The SD adapter is header-only in that existing driver translation unit; no new library target, device source object, MAME tree or executable is required. Preserve the installed SDL GUI-025/026 sources, existing firmware selection and unchanged024C guest. Do not apply the old D8.5 patch again or broadly regenerate/rebuild MAME.

Use the existing DIAG image UI or explicitly authorized invocation with `-sd1 /private/card0.img -sd2 /private/card1.img` and the existing boot-profile arguments. Record actual new executable and private image hashes. One scoped campaign must prove CPU-origin SPI1 control/TX/RX, actual data matching each independent sector image, CS/power isolation, absence/WP behavior, native save-media rejection, and IRQ4/Timer1 coexistence; retain the original guest and closed GUI results. Treat an untouched old executable as **BLOCKED_BINARY_NOT_UPDATED**, not an SD failure. No job was launched or uploaded by this implementation.

**Exact next action:** authorize one incremental update and scoped dual-SD native qualification on the single existing DIAG. Do not split the two peripherals into separate increments. Prepared rector rows target only the existing workbook `1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l`; no workbook was created, replaced or edited here.

## 2026-10-26 — CMD1 legacy integration, bounded (source and static test only)

**Source integrated in canonical `main`** without new MAME targets/trees, ROM changes, native binaries, or T/Commander calls.

- In the **existing** production card parser (`src/mame/skeleton/alphasdana_sd.h`), command `CMD1 / SEND_OP_COND` now returns SPI R1=`0x00` when a powered, selected, properly clocked, standard-capacity raw card is idle. The state changes from idle to ready using **byte-addressed** legacy operation, with no OCR response bytes. CRC checking, power/CS gating, initial clock threshold and normal `CMD0` reset still use the pre-existing common parser. This is a bounded historical MMC/SD-v1 *compatibility fallback*, **not** a complete MMC device identity / CID-CSD profile or timing model, and **not** a claim that the UK1.5 ROM requested CMD1.
- Do not let high-capacity cards silently switch to byte addressing: the fallback returns R1=`0x05` (idle + illegal) when SDSC geometry cannot be represented. Existing SD `CMD55/ACMD41` and SDHC negotiation remain unchanged. Once SD is initialized through that path, `CMD1` is still treated as an illegal command.
- Existing **`tests/d7_sd_static.cpp`**, not a second detached fixture, gained a `constexpr` regression `legacy_cmd1_init_and_sd_isolation`: original six `static_assert` groups retained, checking CMD1 response, standard-capacity CMD16/CMD17 read, independent SD ACMD41, rejection of CMD1 on ready SD and on high-capacity media. **No compiler/native execution has occurred for this exact source change; tests are INTEGRATED / NOT EXECUTED.**
- SD images remain separate from electrical `:SDIRQ` signals; `alphasdana.cpp` unchanged. Board-level contact-detect, write-protect switch and intervening chip are **NOT identified or integrated**. No signal polarity, GPIO selection, chip identity or pin number has been invented. The manufacturer's non-electronic dummy cards make blind `image.exists()→PD2/PD3` coupling demonstrably unjustified.
- Relevant protocol sources: Linux MMC SPI `mmc_send_op_cond` (CMD1 polls R1 idle bit), ST AN5595 §6.1, `elm-chan.org/docs/mmc/mmc_e.html`, and SD Physical Layer spec v2 warning that CMD1 is not an adequate SD/MMC identity discriminator.
- **Native acceptance pending explicit authorization:** compile the single existing T DIAG in place with cache; test the compiled production `d7_sd_static.cpp`, qualify CPU-origin SPI1 CMD1/R1 and readback with an actual raw media image, and perform a bounded UK1.5 regression. Never call Palm desktop PASS based solely on CMD1 support. Prior 026R2/027 remain accepted only in their original scope (both boot tests had NO mounted SD media).
