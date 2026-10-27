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
