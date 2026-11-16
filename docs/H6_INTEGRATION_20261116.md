# H6 — Dana profiles and passive digital power monitoring

## Consolidated result

**Digital profiles and passive host-side observation PASS within the tested scope.** This release preserves GPT's published storage work at `378a1fdaaa42ce017a30a25f500acb2ee70795ff` and adds a bounded, optional observer to the same `alphasdana_state`. It does not emulate a radio or establish a network interface. SDIO functions, physical rail removal, radio-specific sleep/wake and current consumption are not accredited.

The single executable is `runtime/diag/bin/dana-diag`. Its final SHA-256 is `73550d0fc28c3189038e39fad2b5a4321dab59da8cfc416317fad18b875f4e41`. The existing Clang 21.1.8 incremental build/cache was reused; no branches, clones, worktrees, additional emulator installations or tool installations were created. Original firmware and PRC files remain unchanged and private. Development stops after H6.

[Native results and installation identity](H6_NATIVE_RESULTS_20261116.json), [evidence matrix](H6_EVIDENCE_MATRIX_20261116.csv), [NetIF interface research](H6_WIFI_NETIF_API_20261116.csv), [request transitions](H6_POWER_TRANSITIONS_20261116.csv) and [actual monitor sample](H6_MONITOR_SAMPLE_20261116.csv) provide reproducible evidence and limits.

## Continuity and reuse

At resumption, T and GitHub both had `378a1fd`; T's installed binary was `8538592882358372293e583a6570ddc307398548a81aa8ceb0f0c1aa5515c46a`. GPT had already integrated `DANA_STORAGE`, its first-reset latch, NOR-capacity validation and save-state guards, and published native storage results. Those changes are preserved. The only pre-existing untracked file was this intervention's read-only Ghidra audit script.

H1 UART/IrDA, H2 VZ clocks/power/interrupts/GPIO, H3 NOR, H4 LCD, H5 PWM/raw power ADC, both SD/MMC slots and ISP1161 remain the shared implementation. The observer uses existing GPIO, bus and interrupt state; it has no timer, clock generator, module input, device-presence bit, endpoint, packet reply or interrupt producer.

## Three configurations in one controller

| Selector | Documented board configuration | Tested digital scope |
| --- | --- | --- |
| `DANA_STORAGE=0` | Manual diagnostics; independent `PHYSRAM`, `-nor`, `LCD_PANEL` | Existing diagnostic flexibility retained. |
| `DANA_STORAGE=1` | Dana original 2002: 8 MiB RAM, 4 MiB NOR, marketed four grays | RAM aliasing and selected 4 MiB NOR; incompatible NOR rejected. No original complete 4 MiB firmware is available. |
| `DANA_STORAGE=2` | Dana revised 2003: 16/8 MiB, marketed sixteen grays, advertised SDIO | RAM/NOR selection and shared digital VZ; no radio interpretation. |
| `DANA_STORAGE=3` | Dana Wireless 2003: 16/8 MiB, marketed sixteen grays, advertised SDIO/802.11b | Same shared MCU/storage plus optional passive interpretation of the evidenced PK0 software request. No radio is attached. |

The storage selector does not manufacture a radio, infer a physical chip from file length, or silently rewrite LCD registers. `LCD_PANEL` remains documentary panel metadata; native VZ 1/2/4-bpp capability is distinct from the optical response of installed glass. This is not proof that original firmware boots on every physical board configuration. Board/NOR and postload guards from GPT's storage commit are retained.

## Original NetIF provenance and directed reverse engineering

The supplied package has nine members, including an eight-file hash manifest. Its ZIP SHA-256 is `b582d0ee8a233f259e024bedbbe881027db7a2bb62fd9b7b7eccb6bda6017dbd` (36,042 bytes). The standalone instruction equals the ZIP member byte for byte. The 22,258-byte NetIF PRC equals installer resource `wifi/0`, without reconstruction.

Private source identities:

* `WiFiDriverInstaller.prc`: `670cf9b9edf1e867d7cd9f6c9088fcaa03988f72d5071bff9612643d46977937`.
* `WiFi_NetIF_AlphaSmart_Dana.prc`: `6948b018b7926062ab25bfa6d2e142ff62a03f57167d52af403677714cf61726`.

The latter contains `neti/0`, file offset `0xBE`, length 20,946. The existing 68000 Ghidra project `DanaPalmUK15Touch` was reused with `-readOnly -noanalysis`. A transient resource block at analysis address `0x20000000` was discarded after queries; no original program or project content was rewritten. All private listings and generated fixtures remain on T. The bounded audit found 70 candidate function entries; candidates and decompiler output are not automatically treated as verified API definitions. Unresolved switch targets/Palm traps and decompiler warnings are explicitly outside the claimed complete ABI.

The complete external NetIF resource was not found byte for byte in UK1.5. Matching prefixes of several routines occur in ROM, including cleanup candidate `0x103086D8` and initialization candidate `0x10308782`. The full cleanup body is not byte-identical to that ROM candidate. Native validation here applies to the supplied original PRC; the receipts record that distinction. No identity of the entire ROM/PRC or physical Wireless revision is inferred from those matches.

Verified instruction-level findings:

* Resource `+0x3394` performs cleanup, unregisters callbacks when present, clears internal flags/state and clears **PKDATA bit 0, `0xFFFFF441`**, when `(CSA & 0x000E) >= 0x000C`. CSA is at `0xFFFFF110`; it is not CSD.
* Resource `+0x343E` polls the USB library, sets PK0 once when attempting discovery, and clears PK0 on its timeout/failure path. The listing shows a 16-tick preliminary interval, ten-tick retry delays and a 300-tick timeout comparison. These are firmware tick counts, not measured rail timings or newly invented millisecond constants.
* The startup path uses library trap selectors including `A80A`, `A80C`, `A80F`, `A810` and `A811`, and checks several descriptor-ID pairs. The resource also references `UsbBusDriver` and accesses the existing ISP1161 window during a conditional recovery path. This establishes a USB software dependency, not continuity from a particular internal root port to a particular radio chip.
* Resource `+0x05F4` delegates to cleanup; `+0x0516` has enable/disable control branches; `+0x4570` calls the initialization path. Radio-specific system-sleep/wake entrypoints and a physical reset/IRQ net are not established.

The first monitor prototype incorrectly attributed `0xFFFFF441` to PMDATA. Its native trace assertions failed, although the CPU's GPIO reads completed. The actual VZ map identifies **PKDATA**; the final implementation observes the existing PK handler. That failed prototype is retained privately as failed evidence and is not included in the final PASS count.

[Dmitry Grinberg's rePalm study](https://www.dmitry.gr/?proj=27.+rePalm&r=05.Projects) independently discusses reversing Dana's undocumented NetIF. It is a research reference, not a source of Dana pin assignments or a transplanted implementation. The manufacturer's [MC68VZ328 manual](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), existing VZ map, atlas and original instruction evidence ground the register attribution.

## Passive monitor implementation and use

Set the existing configuration field `H6_MONITOR=1` to enable bounded `DANA_H6` log records with `-log`; default is off. The observer records up to 512 events per saved diagnostic session. There is no continuous sampling timer or background radio activity.

Records contain virtual time, selected board, guest instruction PC, event, MMIO address/mask/value, software request, derived digital-pad level and the existing controller-pending snapshot. `verified_board_rail` and `measured_current` always remain `NO_VERIFICADO`. Width follows the mask: GPIO byte versus 16-bit bus operation. The CSV export uses the supplied monitor schema and leaves unverified physical quantities explicit.

Observation points are the existing PK control handler after its normal latch/ST/SD effects, ISP1161 controller writes and SPI1 storage writes. Normal GPIO effects are preserved; no data read is inserted into the guest bus. USB records describe the **controller**, not a fabricated Wi-Fi module. SPI1 records explicitly describe **storage**, not an assumed internal SDIO connection. Pending IRQ snapshots are real controller state and are not attributed to an unidentified radio IRQ wire.

Only Wireless profile 3 interprets PKDATA.0 writes as `ACTIVE_REQUESTED` or `OFF_REQUESTED`. Other profiles retain `UNKNOWN`; their ordinary PK GPIO is not removed. `digital_pad` is HIGH/LOW only when the existing DIR/SEL state drives that pin, otherwise UNDRIVEN. A latch request does not prove VCC switching, acknowledgment, initialization success or zero current.

The five diagnostic state names are `UNKNOWN`, `OFF_REQUESTED`, `ACTIVE_REQUESTED`, `SLEEP_REQUESTED`, `WAKE_REQUESTED`. **The last two are not emitted from a guessed Wi-Fi route.** H2 system STOP/PLL sleep is not equated with module sleep or power-off. Native tests preserve PK0 across actual MCU suspend/wake, then explicitly request cleanup; a radio-specific sleep/wake contract remains unverified.

The request phase and bounded event counter are saved. Restoring a session emits no synthetic GPIO transition; the next genuine bus operation observes the restored request. Reset returns diagnostic interpretation to UNKNOWN without inventing an external reset pulse or a measured rail state.

## SDIO separation

The 2003 advertised slot capability and original SDIO-related ROM routines are documented. Existing SPI1/SD/MMC storage remains functional and has its own power/CS/IRQ routes. A second slot does not establish an internal Wi-Fi bus. No SDIO card/function, CCCR/CIS responder, CMD52/CMD53 endpoint or invented interrupt source is added. Generic SDIO compatibility therefore remains **NO VERIFICADO / not accredited**. This scope closes the documented digital observer, not a working SDIO radio.

## Native tests and regressions

Final candidate and installed campaigns each pass **14 scenarios**: four profiles with monitoring off/on; original NetIF cleanup with monitoring off/on; active-phase save/load; actual PLL STOP/wake; trace-cap saturation; and an OS-level network-syscall audit. Five off/on pairs produce identical guest CPU journals, including GPIO, pending interrupts and PLL readback.

The private cleanup test executes the **unchanged original PRC routine** in guest RAM, with a valid detached-state context created by real 68000 instructions. No Palm trap hook, fabricated module response or host-written guest register is used. It proves cleanup's digital PK0 action in that detached path, not full NetIF initialization, an association, or analog shutdown. The private generated seed is disposable and never published.

The first installed SDL rerun failed to observe End/Prior after closing the MAME menu. The host harness released keys after 45 ms without a UI/CPU acknowledgment. Its final version waits for the existing passive UI observer to report menu closure and holds these two real XTest keys until the original SPI read tap observes their actual guest codes. The first synchronization attempt reversed the two acknowledgment IDs; the canonical profile maps End to 110 and Prior to 98. The final harness uses that mapping and holds Escape until UI closure. No required code or assertion was removed, and Lua never sets an input or writes guest state. Candidate and installed SDL sessions were repeated with this synchronization; the initial failure remains in private evidence and the final receipts.

Guest code performs real GPIO/USB reads and writes, reads the existing ISP1161 silicon ID, and verifies its journals. The ID is the controller's identity, not a radio acknowledgment. The save test verifies restored ACTIVE_REQUESTED on the next real controller operation before another guest cleanup write. The cap case executes more than 512 actual control writes and confirms bounded observation. `strace` around the dedicated H6 native case observes no AF_INET/AF_INET6 socket operations. Existing UART/USB regression transports remain their previously accredited, separate facilities; H6 adds none.

The final candidate also passes all 22 H5 scenarios, 38 existing regression-harness invocations and eight targeted storage-profile tests (including expected capacity rejections). Installed repetition passes 22 H5 scenarios, 35 affected-path regression invocations and SDL/XTest/F12 using a state from this same build. Composite campaigns are not counted as single independent CPU scenarios.

Coverage retained: original UK1.5/AlphaWord, 81 keys/five chords, stylus, RTC/calendar/audio, EmuTOS, dual SD persistence/CRC/protection, LCD 1/2/4 bpp and recovery, H2 clocks/watchdog/IRQ/GPIO, 4/8-MiB NOR, UART/IrDA, USB HC/DC and original printing, Power suspension/wake, and display/cursor behavior. Existing limits on Palm Beam and original USB Computer enumeration are not converted to PASS.

Candidate PASS preceded atomic installation into the sole runtime path. The prior storage-qualified executable is retained only as a private non-executable compressed rollback archive. Canonical source and existing compilation-cache source are compared byte for byte. The original UK1.5 SHA-256 remains `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.

## Neutral future OS3K contract — documentation only

Future independent firmware may request OFF whenever the interface is unnecessary, but must first establish the real enable/regulator net. The proven sequence facts are: conditional PK0 request, original tick-based polling/retry, USB-library dependency, timeout cleanup and request/pad separation. The [API table](H6_WIFI_NETIF_API_20261116.csv) records function/resource/file offsets, dependencies, errors and evidence limits without copying proprietary code.

Conceptual policy, not an ABI or implementation: check evidence/profile; request the documented control level; observe the real bus/status; fail closed and request cleanup on failure; preserve UNKNOWN for unproved rail/current/sleep state. Never treat absent hardware as ready. No Palm driver was ported, no binary copied into OS3K and no networking product work was started.

## Documentation, publication and physical limits

The original Drive master retains its ID, 14 sheets, 1,020 exact formulas and prior history. The existing atlas and OS3K plan are updated only in their applicable documentary cells and appended source/history rows, without new master files. [Drive readback](H6_DRIVE_READBACK_20261116.json) and [workbook preservation checks](H6_WORKBOOK_VERIFICATION_20261116.json) record same-ID raw-byte verification.

The result distinguishes:

* **OBSERVADO / digital PASS:** installed observer, actual CPU-controlled PK0/latch/mux behavior, original detached cleanup, save/load, off/on passivity, storage selection and affected regressions.
* **INFERIDO:** a PK0 level is interpreted as an activity/off request from the observed NetIF instructions; software USB dependency suggests a transport without establishing its internal board connection.
* **NO VERIFICADO:** module identity, PCB/rail/enable continuity, external reset and IRQ, current or energy savings, complete radio sleep/wake, generic SDIO operation and full NetIF ABI/initialization without hardware.
* **NO APLICA:** a radio endpoint for non-Wireless profiles and any host-network/802.11 emulation in this power-only scope.

H6 closes only the demonstrated digital scope. No full Wi-Fi or SDIO PASS, power-rail-off claim or measured battery saving is asserted. Stop after H6.
