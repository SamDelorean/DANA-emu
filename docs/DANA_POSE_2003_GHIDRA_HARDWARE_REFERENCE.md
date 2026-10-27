# AlphaSmart Dana POSE (2003) — original binary/Ghidra hardware reference

**2026-10-26. Evidence:** downloaded *actual* vendor-specific archive [Alphasmart_Dana.zip](https://palmdb.net/content/files/tools-emu/palm-emulator/Alphasmart_Dana.zip) from the [PalmDB POSE listing](https://palmdb.net/app/palm-emulator). This is a **closed historical distribution**; not the generic POSE3.5 code. A contemporary developer reference explicitly states [Dana needs special POSE](https://www.nsbasic.com/palm/info/technotes/TN20.htm). Performed **static analysis only**, never executed the historic Windows or Mac binaries; no binary/ROM redistribution, no DANA-emu source edits or new MAME build.

## Archive provenance / scope

Remote T working path under the *existing* UK1.5 evidence tree:
`work/uk15_qualify_20261025/pose_historical_reference/`.

| Artifact | Historical description | SHA-256 |
|---|---|---|
| `Alphasmart_Dana.zip` | verified ZIP, no CRC errors, nominal 4.4 MiB | `82ec0a80990c11389e1260b66ba4a43f44202f09ace8ab68a666451dd3939f8a` |
| `poser/Emulator.exe` | PE32 i386, original 2003-06-04, 2,609,152 bytes | `75fc8773df92e632d13901989d88408d7b19f341220f2632a7dfa345f06c0150` |
| `roms/Dana1.2.1.rom` | original 2003-07-21, 3,866,624 bytes; **not** current UK1.5 | `a40a8053b9ffffd0857723338c45d043a6d3b427a783247cbe7d769a17aac9d5` |
| `poser/Mac Palm OS Emulator.sit` | historical Mac application, not source | ZIP entry only |
| `poser/AlphaSmart/Dana.skin` | calls device `DanaDevice`, 560x160 LCD, name "Dana without SD cards" **skin title only** | ZIP entry only |
| `poser/AlphaSmart/DanaSkin_1x.jpg`, `DanaSkin_2x.jpg` | two skins | ZIP entries only |
| `poser/ReadMe POSER.txt` | vendor 'Dana Poser', specifies Dana 1.2 ROM and Dana keyboard/clickable modifier semantics | ZIP entry only |

No `.cpp`, `.h`, vendor-specific source archive or PDB shipped in ZIP. It therefore **does not furnish Dana source code**. No evidence yet that the Windows binary boots UK1.5 (readme explicitly says use 1.2).

## Vendor-specific hardware model: positive direct reverse engineering

MSVC RTTI in the actual 2003 PE contains `.?AVEmRegsVZAlphaSmart@@` at VA `0x005DB8D0` (TypeDescriptor `0x005DB8C8`), plus `EmRegsVZ` and `EmRegsVZHandEra330` in the same image, and strings `DanaDevice` and `AlphaSmart Dana`. **This is a compiled Dana-specific hardware model**, not only an image skin. Historical class vtable arrays were located through MSVC CompleteObjectLocator `0x005BF2F0` and `0x005BF348`; corresponding function arrays `0x005B8BF8` and `0x005B8C74`. These were checked against the base `EmRegsVZ` vtables in the *same* original PE.

**Ghidra 12.1.3 x86:LE:32:default** saved a separate static **reference-analysis project** `pose_historical_reference/DanaPOSEReference`. Full-file autoanalysis exceeded its 140-second bounded analyzer budget; a second `-noanalysis` targeted procedure **successfully disassembled and decompiled** exactly known virtual method addresses. Proof: `pose_methods_disassembly.txt` (398 lines), `pose_methods_ghidra.log`, `pose_class_audit.txt`, `DanaPOSESelectedMethods.java` in the research folder; no code imported into MAME.

| PE function address | Verified 2003 POSE implementation (Ghidra C + x86) | DANA-emu significance |
|---|---|---|
| `0x0044A3E0` | Overrides VZ **external port input** by port ASCII: **D (0x44), E (0x45), G (0x47): returns `0`**; K (0x4B) returns base input `|` bit `0x04` from internal state; all other ports delegate to base VZ `0x00448C20`. | Historical Dana board profile does **not** expose D2/D3 high by default; needs comparison to current I/O model and genuine ROM state. |
| `0x0044A450` | Overrides VZ **internal port value**: D `0x80`; G base value `|0x04`; remaining ports base `0x00448C40`. | Historic Port-D read can yield `0x80`; current UK1.5 both-low pin trial already observed **PDDATA=0x80** and *did not boot desktop*. This is not a standalone fix. |
| `0x0044A5B0` | Calls base sub-bank installer then adds MMIO handler **SPI2 `0xFFFFF802` (2 bytes)** and **Port K `0xFFFFF440` (1 byte)**. | Positive hardware evidence that special Dana model wires the ST keyboard/SPI2 and K port; there is **no Dana-specific SPI1 `0xFFFFF700` registration in this override**. This does **not** exclude inherited support elsewhere. |
| `0x0044A5F0` | Custom SPI2 exchange handler checks control `&0x0300 == 0x0300`, exchanges with peripheral virtual interface, clears XCH and updates interrupt status. | Specific reference for Dana SPI2/ST interface, not a substitute for our qualified current SPI2 implementation. |
| `0x0044A6D0` | Custom Port-K write handler tests bit `0x04` and notifies keyboard-side state. | Compare existing emulator's PK2 ready/handshake behavior before changing any physical GPIO. |
| `0x0044A260 / 0x0044A280` | reads register-derived bits 7 / 4 from class state; modeled LCD/display control flags | Device LCD-specific adaptation; inspect vtable type mapping before naming exactly. |
| `0x0044A570` | outputs 8 rows / 16 columns for keyboard information | Confirms keyboard matrix dimensions / built-in keyboard model. |

**Important qualified correction:** Ghidra's full switch reconstruction shows **D, E *and G* input=0**, and the special OR `0x04` is **Port K**, not J. A separate OR `0x04` applies to Port G internal-state reading. Earlier quick x86 manual decoding must be superseded by this full switch analysis.

## Comparison / causal limits

- Current MAME `alphasdana.cpp::pd_r()` overlays D2/D3 from manual `:SDIRQ` switches and PD7 from `:PD7`, not this historical Dana input policy. Its **controlled both-low configuration** in actual native 027/028 original UK1.5 tests resulted in `PDDATA=80` **matching the historical POSE derived port-D value**, yet UK1.5 remained at the second AlphaSmart splash. Hence simply making PD2/PD3 low is **insufficient** in our model.
- Original current UK1.5 guest `0x1032703E TST.W D0; 0x10327044 BNE 0x10327020` loops while `0x103268DC` returns nonzero; that helper calls both `PrvSpiSetPol0/1` and evaluates card event state. There is no current proof it expects SPI CMD1 or that an unidentified PCB IC is the culprit.
- Historical `Dana.skin` reads “Dana without SD cards”, but this **is only a skin label**, not proof that the emulator never implements an SD controller or boots without cards. The specialized sub-bank installation itself registers SPI2 and Port K only. Combined evidence makes **boot independent of mounted SD** a hypothesis to test, not a completed causal conclusion.
- Public POSE original ([cloudpilot-emu/pose-original](https://github.com/cloudpilot-emu/pose-original)), [POSE64](https://github.com/clintonthegeek/pose64), and [CloudpilotEmu](https://github.com/cloudpilot-emu/cloudpilot-emu) do not contain source file/class `EmRegsVZAlphaSmart` in their currently queried repository trees; their generic VZ code is still useful for timing, IRQ, and SPI comparisons. Historical vendor-specific source remains **not found**.
- **No source imports/CPU patching:** do not copy proprietary ROM, do not force GPIO defaults in MAME without original guest+hardware validation, do not create another DIAG. Focus next on real UK1.5 `0x103268DC` return path and `0x10325634` callback, plus exact vendor-specific Port E/G/K/SPI2 method semantics; one bounded native trace if needed.

## Reproducibility

Historic ZIP and PE: held locally on T only, original PalmDB URL above. PE class matching and Vtable: binary RTTI TypeDescriptor and COL memory references, both vtables compared against base VZ. Ghidra artifacts named above. This reference is **not an emulator build or a replacement architecture** and should remain a static library of hardware evidence.

## Vtable semantic mapping — checked against POSE's EmHALHandler declaration

The full `EmHALHandler` virtual method order is preserved in the historical GPL base header [`SrcShared/Hardware/EmHAL.h`](https://github.com/cloudpilot-emu/pose-original/blob/master/SrcShared/Hardware/EmHAL.h). The first `EmRegsVZAlphaSmart` vtable in the 2003 binary is its **EmHALHandler** virtual table: slot 7 `GetInterruptLevel` points to the *same inherited address* `0x00448830` as base `EmRegsVZ`, so there is **no Dana-only override to suppress or change IRQ level in this virtual method**; general VZ logic applies. Directly verified address mapping:

| First vtable slot | Interface virtual method | Vendor specific function |
|---|---|---|
| 9 | `GetLCDScreenOn` | `0x0044A260` |
| 10 | `GetLCDBacklightOn` | `0x0044A280` |
| 21 | `GetPortInputValue` | `0x0044A3E0` |
| 22 | `GetPortInternalValue` | `0x0044A450` |
| 24 | `GetKeyInfo` | `0x0044A570` |

The separate `EmRegs` vtable slot6 `SetSubBankHandlers` maps to `0x0044A5B0` and registers SPI2/Port K only. This mapping follows the actual 2003 binary vtable offsets; inherited method addresses and names are cross-checked against the original header, **not guessed from x86 instructions alone**.

The vendor-specific input implementation decompiled to C under Ghidra:

```c
switch(port) {
case 'D': case 'E': case 'G': return 0;
case 'K': return EmRegsVZ::GetPortInputValue(port) | (internal_register & 4);
default: return EmRegsVZ::GetPortInputValue(port);
}
```

For `GetPortInternalValue`, `D→0x80`, `G→base|0x04`, otherwise delegate. The complete original C++ implementation was **not recovered**; this is a faithful short paraphrase of directly observed Ghidra output.

The early PE Ghidra import logged `Analysis timed out at 140 seconds` during generic whole-file analysis, but **targeted `-noanalysis` Ghidra disassembly and decompilation PASS** for key exact known methods. Class-vtable RTTI and the manually verified binary refs do not depend on complete global analysis.

## 2026-10-26 — ROM 1.2.1 versus UK1.5, and POSE IRQ timing difference

**Static and native evidence, not an implemented hardware fix.** Using the original vendor `Dana1.2.1.rom` from `Alphasmart_Dana.zip` (SHA256 `a40a8053b9ffffd0857723338c45d043a6d3b427a783247cbe7d769a17aac9d5`) and the authentic UK1.5 raw ROM (SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`), direct 68k binary examination confirmed *matching opcode sequences* for both `PrvSpiSetPol0` and `PrvSpiSetPol1`: identical Port-D masks `0x06/0x09`, `PDPOL` XOR, 250-unit trap and three consecutive low samples. Labels occur at file offsets `0x2463C9/0x246453` in vendor 1.2.1, `0x325759/0x3257E3` in UK1.5. Both firmware images contain `SpiSdio`, `HwrSpiCardInSlot`, `PrvShouldWeInstall` and MMC-related symbols. **Therefore the SD-debounce algorithm was not newly introduced in UK1.5.**

Ghidra 12.1.3 verified the 1.2.1 ROM instructions in a **second program inside the pre-existing** `DanaUK15RelocatedTemp` project: `pose_historical_reference/vendor_rom12_sd_init_ghidra.txt` (318 lines), script `ghidra_scripts/DanaPOSE12ROMHardwareCompare.java`. No second emulator build or isolated MAME tree.

**Precisely verified behavior difference between emulators:** public [POSE `EmRegsVZ.cpp`](https://github.com/cloudpilot-emu/pose-original/blob/master/SrcShared/Hardware/EmRegsVZ.cpp) registers `portDPolarity` and `portDIntEdge` using ordinary `StdWrite` (around source lines 624/627), but `portDIntReqEn` using `portDIntReqEnWrite` that invokes `UpdatePortDInterrupts` (around 1994–2002). `PortDataChanged` also invokes it. Its `UpdatePortDInterrupts` computes INT[3:0] from `EmHAL::GetPortInputValue('D')`, `PDPOL`, IRQEN, DIR and edge-state (around 2541–2602). Historical proprietary Dana override `EmRegsVZAlphaSmart::GetPortInputValue(D)=0` was confirmed from its PE/Ghidra; the Dana override adds SPI2/Port-K MMIO and does not install a Dana-only Port-D polarity handler. **In our MAME `alphasdana.cpp`, `pd_extra_w` recomputes INT2/INT3 immediately on *every* `PDPOL` write**. That is a reproducible emulator-implementation difference, but the POSE behavior might itself be a shortcut; **do not integrate its stale-IRQ behavior without a controlled guest CPU comparison**.

**Controlled same-DIAG old/new-ROM comparison, qualified limitation:** both files share the initial 68000 vector/header bytes `00000316100002A2FEEDBEEF...`, yet their ROM lengths differ (1.2.1: 3,866,624; UK1.5: 6,094,848 bytes). Both run with exact same unmodified candidate SHA256 `f72403cab7e781608f1c3f7050ae245fc62443c29d66c9ceef168461bbe5d2cd`, `cfg_sd_both_low`, same corrected Lua observer, 2400 frames. **Vendor 1.2.1** remains at `CURPC=0x100052BC`, `LSSA=0` at all sampled frames—fails **before** SD initialization in this current MAME build. **UK1.5** progresses from `LSSA=0x3B00` to second splash `LSSA=0x72A10`, remains stuck there. Therefore **a native old-ROM comparison of SD handling is NOT established**; cannot claim vendor POSE itself fails or that 1.2.1 proves different IRQ semantics at the SD code. First attempted Lua probe used unavailable `cpu.state['A7']` and logged errors; only subsequent fixed `A6`-based run is qualified. Recorded under `pose_historical_reference/rom_12_original_emulator_comparison/{vendor12,uk15}.fixed.log`. Existing operative DIAG and original UK1.5 unmodified.

**Next valid discriminator:** derive the vendor binary's exact Port-D IRQ handler and emulate its deferred-versus-immediate polarity bookkeeping *only in a reversible, same-tree diagnostic experiment*, comparing original UK1.5 guest PC/stack/interrupt state before and after. If the difference truly changes the stall, reconcile with Motorola VZ manual; do not silently ship a POSE compatibility bug as faithful hardware.

## 2026-10-26 — Native controlled POSE IRQ-update comparison (single DIAG; reversible)

**Native original UK1.5 causal test completed on authorized T**. This section supersedes any assumption that copying historical POSE's `PDPOL` write timing automatically solves the splash. All tests used the *existing* `mame-stage/diag/source` tree, its original cached `build/dana-diag`, and original UK1.5 ROM. **No second emulator compilation tree, no new branch and no operative replacement**. Trial sources were temporarily installed **only in the candidate source**, compiled, observed, and then restored **byte for byte and recompiled**. Exact final SHA256 candidate `f72403cab7e781608f1c3f7050ae245fc62443c29d66c9ceef168461bbe5d2cd`, source Git blob `b25c759e2c62ddbdbe0a3e16544458d7e96eef38`; untouched operative `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` and private original ROM `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. Logs remain in pre-existing UK1.5 work folder, not published with proprietary ROM.

**Trial 1: precise POSE update-event timing.** Historic POSE VZ source writes `portDPolarity`, `portDIntEdge`, `portDDir` with `StdWrite` (no direct `UpdatePortDInterrupts`), writes `portDIntReqEn` with `portDIntReqEnWrite` (updates IRQ), and calls update on changed `portDData`. Diagnostic changed ONLY the corresponding MAME methods: in `pd_extra_w` recompute IRQ if and only if `reg==1` (`PDIRQEN`), in `pd_w` recompute if and only if `reg==1` (`PDDATA`). The trial compiled using Clang21, archived and linked actual driver in the single existing DIAG, temporary candidate SHA256 `b45e81458d34f68dfdd34ed76f100b1c425e0fe936dd5df6f40104ba01ce7ab5`; ran bounded **2400 frames original UK1.5 ROM** with *two actual physical input configurations* and the existing qualified 027 + postboot observer.

| Original ROM, frame900 | Baseline original MAME IRQ write timing | Exact tested POSE-style timing | Implication |
|---|---|---|---|
| `SDIRQ=00`, `PDDATA=80`, `PDPOL=00` | `ISR_L=0C00`, PC near `1007B090` | `ISR_L=0C00`, PC near `1007B098` | **Unchanged level INT2+INT3 / second splash** |
| `SDIRQ=0C`, `PDDATA=8C`, `PDPOL=04` | `ISR_L=0412` | `ISR_L=0012`, PC near `1007B09A` | **Real difference:** historical deferred `PDPOL` recalc leaves INT2 unasserted; **second splash persists** |

The original UK1.5 does not reach Palm desktop under either scenario. It is **false to claim** the temporal mismatch alone fixes SD startup. Existing source has been restored and binary fully recompiled. Full local data: `pose_historical_reference/irq_parity_20261026/{pose_style_low.log,pose_style_high.log,build_trial.log,build_restored.log}`.

**Trial 2: explicit *nonphysical* causal counterfactual IRQ CPU delivery.** Trial source *only for test* changed MAME `update_irq_lines()` level-4 assertion from `active&0x00000c14` to `active&0x00000014`, i.e. disabled **CPU delivery only** of low INT2/INT3 but **left IRQ pending register computation and original ROM fully intact**. This is **NOT a proposal for real Dana circuit or production**. One-tree Clang21 recompiled and linked candidate SHA256 `90212cb3c0a7b7c52765dd1ec654073ec1d14f301a315ea35ef788f0cbe87c22`. Same real UK1.5 original, SDIRQ both low, 2400 frames:

- Baseline frame900 `PC=1007B098`, `ISR_L=0C00`, `IPR_L=0C00`, `IMR_L=F0ED`, callback flag=0 and LCD `LSSA=72A10`.
- With only INT2/INT3 **CPU delivery suppressed**: frame900 `PC=00084654`, `ISR_L=0000`, `IPR_L=0C02`, `IMR_L=FFFF`, `global+1C=0FE0`, `LSSA=72A10`; repeated through frame2400, **NO PALM DESKTOP**.
- Thus **removing the persistent IRQ level is causally relevant** (original guest reaches an entirely different PC/state) **but not sufficient** to boot the OS. The new RAM address `00084654` is presently **uninterpreted**; cannot claim it is a valid next boot routine, an exception, or a successful advance without actual opcode/stack trace. Do not silently implement IRQ suppression.
- Files: `pose_historical_reference/irq_delivery_counterfactual/{guest_irq_delivery_suppressed.log,guest.stdout,guest.stderr,build_trial.log,build_restored.log}`. Trap ensured source restoration and candidate recompile on exit. Restoration PASS: canonical Git blob `b25c759e2c62ddbdbe0a3e16544458d7e96eef38`, candidate SHA256 `f72403cab7e781608f1c3f7050ae245fc62443c29d66c9ceef168461bbe5d2cd`.

**Updated research state:** two independently proven ingredients contribute: static SDIRQ input levels + edge/level/polarity IRQ model **and** additional uncharacterized original-ROM progress/CPU state after delivering or suppressing IRQ4. We cannot yet identify missing board chip, and original vendor POSE binary's successful UK1.5 execution remains untested. **Not integrated into product:** no speculative board pulse, no hard-coded IRQ mask, no assumed electric feedback. Best next technical discriminator: inspect original UK1.5 live machine-code at `0x00084654` and exception/stack/IACK events in short, *bounded* diagnostic trial; independently compare exact PE's inherited IRQ pending update/Port-D handler with static register write sequence to avoid copying a POSE shortcut into MAME. Reuse same DIAG; maintain original-ROM integrity.
