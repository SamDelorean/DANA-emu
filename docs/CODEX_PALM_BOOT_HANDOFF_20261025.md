# Codex takeover — DANA-emu authentic Palm OS boot (2026-10-25)

**This file is the complete executable work brief for Codex. Start implementation, not a proposal or additional handoff.** User-facing conversation: Spanish. Git commits, code and repository technical records: English.


## DIRECTRIZ RECTORA VIGENTE — ARRANQUE FÍSICO FIEL, GHIDRA YA INSTALADO EN T (2026-10-25)

**LA PREFERENCIA DEL USUARIO ES EXPLÍCITA: ARRANQUE FIEL AL HARDWARE.** Se revoca la ruta de arranque asistido Big ROM sugerida históricamente más abajo. Las secciones sobre POSE siguen siendo REFERENCIAS DE FORMATO, no una autorización para crear un bootstrap artificial. Producto aceptado: el único DANA DIAG reproduce el reset del MC68VZ328, lee SSP y PC del dispositivo ROM real seleccionado por CSA0, ejecuta el bootloader original, configura chip-select/SDRAM/periféricos como lo haría una Dana y llega a Palm OS con pantalla generada por el invitado. **Prohibido** fabricar bytes de Small ROM, inyectar PC/SSP, situar artificialmente una copia de la cabecera PalmCard en la dirección física cero, sustituir los vectores, poner RAM escribible en cero para saltar el fallo, parchear las aplicaciones o presentar un arranque asistido como fiel. No arranques todavía otro perfil artificial.

**T YA TIENE GHIDRA.** Prioriza análisis real del firmware disponible con Ghidra sobre especulación o repetición de pruebas sintéticas. Los archivos privados están en /home/spc/Projects/Dana-OS3K/firmware/research-only/: Dana_US15_Flas.raw SHA256 fbba62000334bdb2faf352bdb899591c999528b3d631a4645c2dfce581e11059; Dana_US12_Flas.raw SHA256 6169f44e8ddaf003bd5b98ea3424b19dfecf82f2681263feae078ab566b3370d; DanaUpdate_enUS150R1.prc, DanaUpdate_enUS120.prc y AlphaSmart_Dana1_5_Flash.zip. Comprueba hashes; copias y bases Ghidra exclusivamente privadas; no publicar ROM/PRC/ZIP ni alterar los originales. No hace falta volver a pedir imágenes ya presentes.

### Hallazgo documental verificable, no inferencia

MANUAL MOTOROLA: MC68VZ328UM (https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), cap. 6 Chip-Select Logic y 9.3 Reset. Al reset, CSA0 selecciona globalmente el dispositivo de arranque (excepto registros internos/espacios reservados); los demás CS no están habilitados hasta su configuración; ancho de bus inicial determinado por BUSW. El CPU toma los dos longwords REALES de inicio de la ROM seleccionada: SSP y PC, y el bootstrap ROM auténtico configura los CS/DRAM. CSA reset = 0x00B0, registro 0xFFFFF110. Los ejemplos de distribución memoria de la placa M68VZ328ADS no representan necesariamente la Dana.

Investigación vigente del proyecto: el código Flas concatenado empieza con cabecera PalmCard (initStack/resetVector/signature/version/flags), NO con bytes de reset físico acreditados. US1.5 PalmCard PC=0x1000C80A, US1.2 PC=0x1000C776; offset de datos sustentado por actualizador=0x10008000, de manera que entradas del bloque estudiado están en +0x480A / +0x4776 respectivamente. No implica que 0x10008000 sea dirección del chip ROM físico ni que los 0x8000 bytes anteriores representen exactamente un sector original. Primer fallo anterior en PC real de instrucción 0x1000C80E fue CLR.B (A4) en PrvConvertIToA por colocación equivocada; NO constituye evidencia a favor de escrituras Flash, ni RAM en cero.

### Trabajo de ingeniería inversa INMEDIATO para Codex (Ghidra en T)

**A. Rastrear la secuencia de actualización FLASH**, comenzando por recurso Palm PRC code/1 de US1.5, con US1.2 como comparativa. Reutilizar tools/palm_updater_audit.py para Flas recursos/consecutividad/byte-sums; emplear Ghidra para desensamblar el actualizador, identificar referencias cruzadas al literal 0x10008000 y calcular realmente destinos de escritura por recurso, regiones protegidas, ancho de bus, identificador NOR y transiciones a código de inicialización/bootloader. Verificar que el literal corresponde a un destino real de escritura y no asumirlo por el nombre.

**B. Analizar la imagen US1.5/US1.2 en Ghidra sin modificarla.** Raw Binary, Motorola 68k big-endian, 32-bit addressing. Ghidra oficial identifica lenguaje 68000:BE:32:default (la variante default puede admitir un 68040; cotejar las instrucciones con el 68000 integrado). Para estudio XREF de la hipótesis Big ROM configurar base DE ANÁLISIS 0x10008000, usando analyzeHeadless con -loader BinaryLoader -loader-baseAddr 0x10008000 -processor 68000:BE:32:default -cspec default, previa comprobación de la versión instalada. **Esta base en la base de datos de Ghidra NO es autorización para cambiar el reset del emulador**. Crear funciones de arranque declaradas y rastrear accesos a 0xFFFFF000 (SCR), 0xFFFFF100 (grupo A base), 0xFFFFF110 (CSA), 0xFFFFF116 (CSD), y demás MMIO/documentación Motorola; contrastar llamadas y offsets de código real. No fiarse de pseudocódigo sin validar instrucciones y bytes.

**C. Determinar de dónde salen LOS VECTORES FÍSICOS Y EL CÓDIGO ORIGINAL PREVIO al Big ROM.** Construir una tabla verificable de cobertura de regiones del chip: offset/nombre/dirección física SUPUESTA, recursos Flash que las escriben, destino real de la instrucción de actualización, referencias cruzadas desde el sistema y cuáles bytes no se encuentran. Buscar original Small ROM/boot region en todas las entradas del ZIP, recursos no-Flas, sector de recuperación, código de update que preserva bootblock y fuentes autorizadas del hardware Dana. Verificar cabecera PalmCard versus bloque físico por separado. Si el primer sector está ausente, entregar exactamente el rango no obtenido, la prueba en código y la alternativa de lectura NO destructiva desde la ROM física de una Dana propiedad del usuario. Ghidra demuestra rutinas/cobertura, no genera bytes ausentes.


**Fuente para posible obtención NO destructiva de boot ROM original, si el usuario tiene una Dana física disponible:** proyecto `davidgiven/dbztool@d32702383c2ea3523ea58599c52345435c74e900`, `README.md` y `danainit.sh` (licencia BSD-2-Clause). Su README afirma que la interfaz bootstrap DragonBall VZ fue probada precisamente con AlphaSmart Dana y admite `dump` de direcciones físicas; ejemplo de sintaxis genérica: `dbztool -p /dev/ttyUSB0 dump 0xfffffe00 512` (es un ejemplo de bootstrap microcode, **NO** dirección Flash a copiar ciegamente). Por ello Codex debe investigar si hay una vía de **LECTURA** del primer bloque ROM desde la propia Dana por bootstrap/UART1, determinar el mapa correcto de Flash a partir de chip select, y documentar conexión/estado de boot/efectos colaterales **antes** de proponer cualquier acceso físico. `danainit.sh` modifica numerosos registros (incluyendo CS/DRAM) y **no** debe ejecutarse sin autorización explícita y análisis de efectos; no escribir/erase NOR, no realizar hard reset con posible pérdida de datos, no intentar forzar bootstrap eléctrico. No afirmes que hay un dump ni que el canal está conectado: es una capacidad externa documentada que podría aportar el contenido original ausente si el usuario dispone del equipo y aprueba su lectura. Proyecto: https://github.com/davidgiven/dbztool .

**D. Corregir y ejecutar SOLO el hardware real que falte, una vez acreditado el inicio auténtico.** Contrastar source/src/mame/skeleton/alphasdana.cpp: vector fetch real CSA0, ancho BUSW, alias ROM inicial, cambio a mapa post-CSA, DRAM/SDRAM y accesos MMIO del bootstrap. Registrar PC de instrucción (no PC de prefetch), SSP/SR, lane/size, CS regs y destino de la primera escritura. Implementar mínimo ajuste hardware fundamentado, compilar con Clang21 incremental en único DIAG y probar reset real con la imagen auténtica. Conservar ejecutable instalado sha256 0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a hasta PASS nativo. Preservar ST 81/81, doble SD y EmuTOS. Nunca construir un segundo DIAG, clonar, abrir rama paralela ni producir arranque host-pintado.

**Entregable obligatorio:** hallazgos de Ghidra reproducibles (funciones, offsets, XREF, bytes/procedencia solo en carpeta privada), tabla exacta de cobertura ROM/sector boot y primer bloqueo real, cambios mínimos del controlador y prueba nativa del RESET FÍSICO: ROM -> bootstrap original -> CS/DRAM -> Palm OS dibuja LCD. PASS solo con arranque real; si faltan bytes de boot, BLOCKED justificando exactamente esos bytes sin inventarlos. No gates administrativos ni planes sustitutos de ejecución.

**Presupuesto remoto:** la última autorización anterior a este mandato agotó 5/5 llamadas Commander. Este mandato no otorga nuevas llamadas en el chat. Codex debe usar el acceso local que el usuario le conceda dentro de su propio entorno y no atribuirse ejecuciones inexistentes.

**Esta sección MANDA sobre cualquier instrucción anterior del mismo archivo que promueva Big ROM assisted. Comienza investigando con GHIDRA y el actualizador code/1.**

---


## RESEARCH UPDATE — 2026-10-25 — actionable route to Big ROM startup (source-backed; no fresh native run)

**This section adds NEW research and supersedes any inference that the contents at byte 0 of `Dana_US15_Flas.raw` are original physical address zero. Preserve the 5/5 exhausted T Commander budget and the currently qualified installed executable. This source-based analysis is NOT a Palm boot or a native test.**

### A. The PalmCard at payload offset zero is a ROM CARD HEADER — not evidence of physical reset location

Two independent source implementations identify the initial fields of a PalmCard (`CardHeaderType`) as `initStack`, `resetVector`, `signature`, `hdrVersion`, `flags`, and a **separate `bigROMOffset`**. The Debian `romeo` ROM inspector prints those exact fields and its Big ROM and HAL offsets (read-only code):
- https://sources.debian.org/src/romeo/0.5.0-9/output.c/#L45 (see `Output_CardHeader`; the website's rendered source line is around `818-873`).
- `cloudpilot-emu/pose-original@97b10711fe4ca50c1bd47072378eaab26ba8e81d`, `SrcShared/EmROMReader.cpp`, `AcquireCardHeader`, and `SrcShared/Hardware/EmBankROM.cpp`, `Card::CheckCardHeader` / `LoadROM`.

Our **existing verified private header bytes** (NOT included in Git): US1.5 offset 0 = `000048fe 1000c80a feedbeef 00050040`, US1.2 = `0000486a 1000c776 feedbeef 00050040`. Thus `hdrVersion=5`, `flags=0x0040`. POSE `EmROMReader::AcquireCardHeader` explicitly identifies `flags & 0x0040` as **68VZ328**, consistent with Dana's MCU. `0x48FE`/`0x486A` are the card-header init-stack fields, not proof that this header was located at physical Flash offset zero.

**Prior Codex analysis (already recorded elsewhere in this same handoff)** independently confirmed candidate base **`0x10008000`** from literal use in each updater `code/1` and each header at byte `0x68`. It checked coherent entry instruction paths when using that base: US1.5 `0x1000C80A - 0x10008000 = 0x480A`, US1.2 `0x1000C776 - 0x10008000 = 0x4776`. Under WRONG zero-origin placement the offsets became `0xC80A` / `0xC776`, and US1.5 entered `PrvConvertIToA`, where a real `CLR.B (A4)` targeted zero. This **explains the old observed 0-address write** without allowing any Flash writes or changing address zero to RAM. The absolute physical boot region `0x10000000..0x10007fff` is still **unverified/missing**; check actual ROM header structure for the precise meaning of `0x68` and do not infer physical geometry exclusively from this literal.

### B. A ready-made REFERENCE IMPLEMENTATION of the missing-SmallROM case exists: POSE

Pinned official-origin emulator code: **`cloudpilot-emu/pose-original@97b10711fe4ca50c1bd47072378eaab26ba8e81d`, `SrcShared/Hardware/EmBankROM.cpp`, function `EmBankROM::LoadROM`**:
https://github.com/cloudpilot-emu/pose-original/blob/97b10711fe4ca50c1bd47072378eaab26ba8e81d/SrcShared/Hardware/EmBankROM.cpp

It explicitly handles ROM files containing BOTH **Small ROM + Big ROM** and files containing **only Big ROM**. Its algorithm: validate PalmCard header; derive `bigROMOffset` from header for modern versions (or `0x3000` for v1), determine whether a second valid card header exists at the advertised offset; if only Big ROM, reserve the missing prefix in an emulator buffer, relocate the supplied Big ROM accordingly, fill unknown prefix with `0xff` and COPY ONLY the Big ROM header into Small ROM's header position for emulation. It then detects VZ compatibility and derives a *temporary* ROM base from `cardHeader.resetVector & 0xFFF00000` until chip selects are configured. **This is a POSE emulation convenience, NOT proof of authentic Small ROM bytes or physical power-on reset code.** Do not copy GPL implementation into BSD-licensed MAME: reimplement the behavioral contract independently if necessary.

Corroboration: older xcopilot-derived emulators also document that many POSE `.rom` files omit Small ROM; old Palm debugger documentation distinguishes its SmallROM bootstrap from BigROM. These corroborate architecture **across Palm devices**, not Dana's exact protected sector size. Source references:
- https://www.cypherpunks.ca/zaurus/ (section `QCopilot`; generic Palm, not VZ-specific);
- https://www.cs.trinity.edu/~jhowland/class.files.cs3194.html/palm-docs/Development%20Tools%20Guide.pdf (SmallROM vs BigROM; consult only necessary excerpt).
- Historical Dana-source verification in `SamDelorean/Dana-OS3K`, `docs/05-ROM-DANA-ACTUALIZADORES.md`; the original update `Flas` resource data and checksums are already validated.

### C. Exact next engineering task for Codex (DO THE WORK, not another plan)

**C1 — one read-only source/firmware inspection** (no hardware/emulator run needed): reuse `tools/palm_updater_audit.py` (already exists, supports `--candidate-base 0x10008000`) and the actual private US1.5/US1.2 PRCs. Independently parse `CardHeaderType` field offsets using POSE `EmROMReader.cpp` / Palm header definitions, including `bigROMOffset`, `checksumBytes`, and `halCodeOffset`. Determine whether the source stream is solely Big ROM and the actual missing-prefix extent. Check for a second valid PalmCard at advertised offset; compare US1.2 vs US1.5; validate entry branch and disassembly from offsets `0x480A` / `0x4776`. Produce **only hashes/field values/disassembly observations**, not private ROM bytes. Investigate original update programming destination offsets if the header alone does not settle exact physical position.

**C2 — deliver a working emulator mode using the available Big ROM, not a false physical dump.** If the image is Big-ROM-only, implement a **distinct, explicitly labeled `Palm BigROM-assisted` diagnostic boot profile in the SAME DANA DIAG**, without modifying or replacing original physical `-rom` reset semantics. POSE's source is the behavioral research donor, not source code to paste. Map the supplied authentic image at the evidenced base `0x10008000` in the 68k address space, with correct unmapped/unknown prefixes (do not reinterpret `ff` as recovered code). Initialize a **clearly marked synthetic boot context** only as required to enter the authentic card-header reset vector `0x1000c80a` with its defined stack `0x48fe` and compare with 1.2; all following OS instructions, MMIO, LCD, keyboard and SD must execute genuinely in M68000. This mode does NOT count as original hardware cold-boot PASS. Preserve R-direct EmuTOS and stock physical-mode boot. Any unknown required BigROM external bytes must cause a specific reproducible BLOCKED result, never a fake OS interface. If the user prefers strict original cold boot, the next requirement is **independently authenticated original Small ROM boot bytes** from an owned physical ROM dump or separately demonstrable vendor recovery data; inspect existing archive before assuming it cannot contain them.

**C3 — preserve authentic physical boot as a separate pending fidelity target.** Once genuine complete SmallROM contents become available, map full Flash, execute actual CPU reset fetch at original physical vectors and prove transitions from SmallROM to BigROM and then Palm UI. Never quietly use BigROM-assisted injected PC as physical reset, or treat a padded Flash array as a recovered dump. Protect canonical installed DIAG SHA `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`; stage/atomically install only a verified successor.

**C4 — acceptance:** (a) read-only exact header/layout report; (b) visible native MAME 68k PC/SP/SR and guest-produced Palm framebuffer via hardware accesses in the one DIAG; (c) interactive Palm keyboard events using the qualified ST/SPI2, then Palm startup/launcher; (d) no regression to current keyboard/SD/LCD/EmuTOS. For physical fidelity additionally demand byte-authenticated SmallROM and actual reset fetch. On any blocked step, deliver *one* decisive actual guest CPU+bus blocker and the minimum further evidence—not a new program of gates.

**Key distinction**: The *main emulator is required to make authentic Palm OS software run*. POSE-compatible assisted BigROM startup is a valuable intermediate usable result when original reset bootloader was omitted from updater data. It must be labeled as software-assisted, never simulated stock cold boot or host-painted Palm UI. No additional T calls are authorized from this handoff; actual Codex machine access and permissions must come from the user.

---

## Current native result — 2026-10-25, authorized five-call T intervention

**INCREMENTAL_BUILD_PASS / US15_NATIVE_ROOT_CAUSE_CONFIRMED /
ORIGINAL_BINARY_RESTORED / PALM_UI_NOT_BOOTED.**

The user explicitly renewed authorization for **up to five Desktop Commander
calls** after the source-only stage below. Exactly **5/5** were used:
preflight, exact-match staging plus make dry-run, incremental build/qualification,
process output, and error readback plus native retry. No sixth call or remote
operation remains running from this intervention.

Preflight independently verified installed SHA
`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`,
original driver SHA
`bcd61b82ae7259613a853b329b3b0586e13b68387e3192c24fde3c1e72afbe4b`,
and original US15/US12/US15 PRC sizes and hashes. Only the two exact-matching
physical diagnostic methods were replaced in the existing T source. Modified
driver SHA is
`beb460df6e04013d1bc24c542b89276a088cf06fc0e96e52fedd566c57cc7eda`.
The old private US15 attempt was still running after **09:41:20**; only its
verified wrapper/timeout/emulator PIDs 25124/25198/25199 were terminated, avoiding
its wrapper automatically launching the next obsolete trial.

The make dry-run selected one driver compilation. Actual **Clang 21.1.8 build
exit 0** compiled `alphasdana.cpp`, archived `libmame_danadiag.a` and linked the
same `danadiagd` intermediate, using the existing cache and command recorded in
[the existing receipt](PALM_UPDATER_DERIVED_COLD_BOOT_20261025.json).
Candidate executable SHA:
`7d5f9bbe05311e093ea1e4f512927977daba1b459a3a00d41ad9417b147c763e`.
No donor tree, emulator variant or new branch was created.

Candidate tests used only the canonical `bin/dana-diag` path, with an exact
non-executable backup and unconditional restoration. The first US15 and US12
attempts exited **3** because this MAME exposes **no `emu.register_stop`**.
They did enumerate the actual CPU states, including SP and excluding A7, but
failed before guest tracing. This was an observer defect, not a new guest
hardware failure. A second defect was fixed locally: autoboot scripts run after
machine start, so registration of a later start callback cannot attach to the
current session. The final source observer starts immediately and uses
`emu.add_machine_stop_notifier`, retaining its subscription. Its updated mocked
API test rejects unsupported API names. **That final observer fix has not been
redeployed or retested natively; the five calls are exhausted.**

The fifth call repeated **US15 without Lua or debugger**, using the same
preexisting padded zero-origin experimental array; no new or repaired image was
created. One virtual second, **process exit 0**, produced:
```
DANA_PHYSICAL_WRITE address=00000000 data=0000 mask=ff00
DANA_PHYSICAL_BLOCKED reason=FLASH_COMMAND_SET_UNVERIFIED address=00000000 data=0000 pc=1000c812
DANA_PHYSICAL_CPU curpc=1000c80e ir=244c sp=000048fe usp=00000000 sr=2704 a4=00000000
DANA_PHYSICAL_DECODE csa=00b0 csd=0200 csgba=0000 csgbd=0000 csugba=0000 csctrl=0000/1000/9c00 dram=0000/0000/003c/0000
```
This **natively confirms CLR.B (A4) at 0x1000C80E**, writing the upper byte lane
at address zero with A4=0. It is the static PrvConvertIToA instruction found
below. `IR=244C` is the *next prefetched instruction*, not CLR.B's opcode:
pinned MAME `m68000-sdf.cpp::clr_b_ais_df` advances m_ir/m_pc before issuing
the data write. CURPC, lane mask, register and disassembly must be considered
together. No RAM/Flash bypass is justified by this failure. US12 has matching
static placement evidence but **no successful native trace** in this campaign.

**Remaining authenticated-input dependency:** the updater payload's evidenced
placement at 0x10008000 leaves the original initial Flash prefix and separate
reset/header contents unidentified, preceding offset 0x8000. No part geometry,
protected-sector values, physical reset vectors or bytes were invented. Correct
payload placement alone does not establish a complete physical Flash image.
The root cause of the old first write is now observed, but authentic Palm UI
boot remains **false**, not a PASS inferred from exit code 0.

Final readback independently measured restored canonical binary SHA
`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
The candidate was **not promoted**. Its intermediate and private build/receipt
files remain inside the same DIAG root at `work/palm-boot-5080ce9`.
No unrelated ST81, SD or GUI campaign was rerun. Existing peripheral code is
unchanged; diagnostic success does not requalify all peripherals.

## Historical source-only result — 2026-10-25 (before renewed T authorization)

**STATIC_ROOT_CAUSE_EVIDENCE / DIAGNOSTICS_IMPLEMENTED / PALM_NOT_BOOTED.**

The previous write is explained by a concrete image-layout discrepancy, rather
than evidence that address zero should accept RAM writes during CSA boot:

| Check | US 1.5 | US 1.2 |
| --- | --- | --- |
| Verified Flas resources, consecutive IDs, valid byte sums | 119, 2000–2118 | 75, 2000–2074 |
| Concatenated payload size | 0x5C8000 | 0x3A8000 |
| Header PC field | 0x1000C80A | 0x1000C776 |
| Entry offset under previous zero-origin array | 0xC80A | 0xC776 |
| Nearby byte clear through A4 | 0xC80E | 0xC77A |
| Entry offset with payload base 0x10008000 | 0x480A | 0x4776 |
| PC-relative entry jump target (payload offset) | 0x48FE | 0x486A |
| Updater code/1 literal 0x10008000 offset | 0x978 | 0x900 |

Downloaded the exact source archive through connected Drive file
`1LY_Ykm3RysWe4vutxWeFRnwSTCxlIcFg`; archive, both PRCs and both extracted
payload hashes match section 1. No originals modified, padded image created,
ROM uploaded, or firmware bytes committed. Private reports and temporary bytes
are outside the repository in `/workspace/work/palm-boot/`.

At the old US15 entry, linear disassembly gives a move from D0 to D3, conditional
backward branch, then **CLR.B through A4 at guest 0x1000C80E**, inside
PrvConvertIToA. This matches a zero write through a reset-valued A4 and the old
prefetch PC 0x1000C812. The previous receipt does not contain CURPC, IR, A4 or
lane mask, so this is static identification of the consistent offending
instruction, not a newly observed native bus trace. A CLR.B bus transaction
must not be described as a guest word-write solely from the 16-bit handler.

Both payload headers contain 0x10008000 at offset 0x68; the updater explicitly
loads that address before reading version metadata. With this base, both PC
fields land on a coherent entry jump rather than the conversion routine. In
US15 the entry proceeds to the payload's 0x48FE startup dispatch, computes its
base using the PC-relative offset at 0x48FA, then uses header offset 0x7A
(0x7063A) to dispatch to board startup. That entry jumps to payload 0x71A2E:
real VZ MMIO initialization, followed by CSA group base 0x10000000,
CSA=0x018D, and checks for a separate Palm header at guest 0x10000000
(and 0x10400000 for the other bank). Later instructions initialize CSD and
DRAM/SDRAM. These are disassembled instructions, not executed events.

**Missing authenticated input:** with the evidenced 0x10008000 payload
placement, no original bytes have been recovered for the preceding Flash
0x00000000–0x00007FFF region (guest 0x10000000–0x10007FFF once mapped),
including its reset vectors and separate initial card header. The exact
physical part, sector protection and contents remain unverified. The archive
alone does not establish these missing bytes. Do not fill that prefix, move
PC/SP from the host, or reinterpret the updater header as physical reset
vectors. Placement evidence does not establish a complete chip image.

Implementation in the same driver: terminal physical failures now record native
CURPC/IR/SP/USP/SR/A4 and CSA/CSD/group/control/DRAM state; rejected writes also
record the lane mask. No extra guest memory reads, memory decoding changes,
Flash write bypass, CPU state injection or changes to existing peripheral
functions. `tools/palm_boot_observer.lua` uses the actual `SP` binding, lists
available bindings, retains read/write taps, limits output to 512 events and
marks UI boot unproven. `tools/palm_updater_audit.py` verifies resource structure,
consecutive IDs, byte-sum checksums and hashes; optional binutils disassembly
is written only to the explicitly chosen private report.

Executed validation:
- Full driver: g++ 14, C++20 `-fsyntax-only -Werror` against the existing MAME
  donor headers, PASS. **No Clang21 object/link or native executable built.**
- Six parser error/ordering/checksum tests, PASS.
- Lua mocked API test via `texlua`, PASS (SP, unavailable optional bindings,
  unchanged CPU values, byte-lane logging, event cap and trace close).
- Existing D8.5 constant-evaluation test, PASS. Its old preservation suite has
  eight failure records across three test methods, identically reproduced
  against untouched `f73aba8` and the new driver; zero errors. It predates later
  ST81/SD/reset changes. Do not report the whole historical suite as PASS.
- Whole-driver text comparison against f73aba8 after removing just
  physical_block/physical_w: identical, PASS; git diff whitespace check PASS.

Repository continuity: checkpoint 3dde150 is the parent of starting f73aba8;
the cached origin/main ba40acd is an ancestor 160 commits behind. Renamed the
provided local `work` branch to `main`; no branch, clone or worktree created.
`git fetch origin main` failed because the configured proxy refused connection;
remote HEAD freshness and push are not verified.

Access correction: Cloud has neither T filesystem nor its Clang21 build cache.
Desktop Commander discovery subsequently found `spc-HP-t640-Thin-Client` online,
ID `dee0b4b6-578a-41a5-88de-73dbeb808983`. Discovery only; no process launched,
T file read/written, build, replacement or guest run. Section 5's explicit
exhausted remote-call authorization remains in force. The installed binary
hash is still historical, not independently remeasured in this intervention.

Reproduce static auditing (set LD_LIBRARY_PATH for the existing cached binutils):
```
python3 tools/palm_updater_audit.py PRIVATE_US15.prc --candidate-base 0x10008000 --objdump M68K_OBJDUMP --output PRIVATE_REPORT.json
python3 tests/palm_updater_audit_test.py
texlua tests/palm_boot_observer_test.lua
```
Native CLI **not run** (requires authentic complete Flash and authorized T access):
```
DANA_PALM_TRACE=PRIVATE_TRACE /home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag/bin/dana-diag asmdana -rom PRIVATE_AUTHENTIC_FULL_FLASH -autoboot_script tools/palm_boot_observer.lua -seconds_to_run 2 -log
```
Do not use either extracted updater payload as PRIVATE_AUTHENTIC_FULL_FLASH.

## 0. Product outcome and exact starting point

**Deliver a working AlphaSmart Dana stock Palm OS startup in the one existing MAME-based `dana-diag`.** Use actual MC68VZ328 68k instruction execution, actual reset/Flash/DRAM/chip-select/MMIO and the already present user-owned Palm firmware. Reach a genuine, guest-generated Palm OS startup/UI if achievable from these files. If the files lack necessary boot sectors or other original hardware behavior, prove that exact missing dependency with CPU/disassembly/bus evidence; never invent code, suppress blocked accesses, or report a successful boot without genuine guest execution.

- Repository: https://github.com/SamDelorean/DANA-emu ; **work on the existing canonical `main`**, pinned initial checkpoint `3dde150819bf8c49fda6d0d71f00b9ce63173a34`. Refresh the head safely and reconcile real changes before editing.
- Sole authoritative emulator tree on authorized T computer: `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`. MAME source: `.../diag/source`. One installed executable: `.../diag/bin/dana-diag`. Build intermediate `source/danadiagd` is NOT another authorized installed emulator.
- **Current qualified installed binary SHA256:** `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. Verify exact SHA before any installation. Retain a rollback path and never replace the operating executable with a failing candidate.
- Published driver: `src/mame/skeleton/alphasdana.cpp` (MC68VZ328 M68000 subclass, 32-bit address space, R-direct loader, physical Flash/reset mode, chip select and SDRAM, GPIO, clocks, IRQ, LCD, pen, UART1, SPI2/ST, SPI1/dual SD). Inspect `src/mame/skeleton/alphasdana_sd.h` and `alphasdana_sd_image.h` where applicable.
- **Known qualified, do not rebuild or retest gratuitously:** actual guest CPU+SPI2 native keyboard **81/81 scan codes, 86 releases, 5/5 chords** and installed EmuTOS-Dana boot smoke. Dual-SD guest read/write and close/reopen persistence previously qualified, as well as existing LCD/GUI-025/026; preserve features. Interactive EmuTOS text rendering was not proven by the most recent keyboard smoke. Prior qualification is not proof of Palm boot.

## 1. Private original firmware already present on T — do not ask user to reacquire it

Directory: `/home/spc/Projects/Dana-OS3K/firmware/research-only/`.

| File | Exact original bytes / SHA256 / significance |
| --- | --- |
| `Dana_US15_Flas.raw` | 6,062,080 B (`0x5C8000`); `fbba62000334bdb2faf352bdb899591c999528b3d631a4645c2dfce581e11059`. Concatenated Palm updater resource content, **NOT proven full physical Flash**. |
| `Dana_US12_Flas.raw` | 3,833,856 B (`0x3A8000`); `6169f44e8ddaf003bd5b98ea3424b19dfecf82f2681263feae078ab566b3370d`. Same limitation. |
| `DanaUpdate_enUS150R1.prc` | 6,085,164 B, SHA256 `53086494a233522d1773107a21f465835dca20e2cfd2076f2b45d0349558a342`. Resource DB `appl/asmt`, 119 consecutive `Flas` resources. |
| `DanaUpdate_enUS120.prc` | 3,855,501 B, SHA256 `1d4e19a41a68962bd6bce91cd9ed891bdedbf5eb24a296d3acf7221438fda1d6`. 75 `Flas` resources. |
| `AlphaSmart_Dana1_5_Flash.zip` | 9,453,509 B, SHA256 `1a0256e35c11c7455a58738f05218e1e290b8d381a5742467f1a512ac25c14fc`. Official-source updater archives/instructions. |

The `Flas` records concatenate in ID order; each resource contains payload + four-byte *byte-sum* checksum, NOT CRC32. The raw concatenated content contains `FE ED BE EF` at offset `0x8`, `PalmCard` metadata, Palm OS and AlphaSmart strings. This demonstrates **firmware data**, not a complete readout of protected boot sectors or physical NOR chip geometry. Do not commit original ROM/PRC/ZIP or derived ROM bytes to public Git, paste private bytes into issue logs, or write to a physical Dana.

The big-endian first two longwords in each extracted raw image are **candidate vectors**, not independently verified physical reset mapping:
- US1.5: SSP=`0x000048fe`, reset PC=`0x1000c80a`.
- US1.2: SSP=`0x0000486a`, reset PC=`0x1000c776`.

## 2. Last actual native Palm run — NOT BOOTED

Result text: `docs/PALM_UPDATER_DERIVED_COLD_BOOT_20261025.json`; immutable corresponding handoff prefix at `docs/HANDOFF.md`, latest current content only. User-owned emulator-only trial padded US1.5 with `0xFF` to **8 MiB** and US1.2 to **4 MiB** in private `/tmp/DANA_PALMOS_NATIVE_BOOT.3YyuVIg0/` solely to explore existing physical loader (which enforces complete power-of-two geometry). **This padded tail is invented/unknown**, NOT a recovered physical dump. Do not promote this experiment into a stock-ROM reference.

One recorded US1.5 run loaded the 8MiB temporary array in physical `-rom` profile, not EmuTOS `-quickload`. Native log:
```
DANA_PHYSICAL_IMAGE bytes=8388608 ... topology=linear_array_unqualified
DANA_PHYSICAL_RESET vectors=firmware CSA=00b0 CSCTRL2=1000 CSCTRL3=9c00
DANA_PHYSICAL_BLOCKED reason=FLASH_COMMAND_SET_UNVERIFIED address=00000000 data=0000 pc=1000c812
```
This proves physical-mode loading/reset and CPU-origin bus activity at a guest PC. **It does not establish Palm OS boot**. At `PC=0x1000c812`, firmware attempted a word write to physical address 0, which the current driver classified as Flash (boot CSA still selected). Root cause is **UNKNOWN**: absent boot region? firmware image not mapped as original? correct CSA reset decode? guest stack/address remap expectation? actual NOR/DRAM timing? Diagnose from disassembly and documented VZ behavior; do NOT decide by intuition.

The observer itself had an independent error: Lua `cpu.state["A7"]` is NIL in this MAME CPU state binding. Therefore its guest.trace was not produced. Fix observer by listing valid CPU state names or using available `SP` binding; do not mistake observer failure for guest hardware failure. The published receipt has **no US1.2 guest execution/trace**. Never claim US1.2 passed.

No Palm UI, OS boot, external ROM write, or new production emulator installation occurred in this native Palm attempt.

## 3. Code regions needing precise examination

In `src/mame/skeleton/alphasdana.cpp` inspect and trace these concrete functions:
- `firmware_load`: `-rom` takes a power-of-two linear 128KiB–16MiB byte array; rejects updater-sized partial images and checks reset PC at bytes4–7. Treating a PRC or Flash-content fragment as a complete power-of-two NOR array is **not justified**.
- `physical_reset`, `machine_reset`, `program_map`, `cpu_space_map`: profile selection, vector fetch, SCR, CSA at reset, CPU state.
- `physical_r`, `physical_w`: current `boot = !(m_cs_select[0] & 1)`; this routes all ordinary low writes to Flash until guest reprograms CSA. `physical_w` stops on `FLASH_COMMAND_SET_UNVERIFIED`. Determine whether this correctly reproduces the MC68VZ328 reset remap and initial DRAM availability; preserve fail-closed unsupported behavior until real evidence supports change.
- `cs_r/cs_w`, `cs_select_*`, `cs_hit/cs_size/cs_base`, `dram_r/dram_w`, `physical_mmio_r/w`, `physical_block`: first guest-visible failure and precise decoding.
- `GENERIC_SOCKET` in machine config, `DANA_VZ_CPU` address-width variant and scheduler. Avoid a new CPU engine, fake Palm system calls or host-side display painting.

For *real* MC68VZ328 reset vector, CSA/CSB/CSD initial mapping, DRAM/SDRAM, PalmCard and original Dana-specific boot behavior, read source references first:
- `research/sources.lock.json` and `docs/D0_2_EZ_VZ_REGISTER_CONTRACT.md` (existing Motorola manual/addendum contract).
- `docs/D8_5_PHYSICAL_BOOT_IMPLEMENTATION.md`; `docs/GENERAL_WORK_PLAN.md`, `docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md` and `docs/DANA_DIAG_EXCLUSIVE_TEST_POLICY.md` (current rules).
- `https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/05-ROM-DANA-ACTUALIZADORES.md` (authentic updater structure and known limits).
- `https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/01-HARDWARE-DANA.md`.
- Pinned MAME donor `SamDelorean/mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`, `src/mame/palm/palm.cpp`, MC68EZ328 device as conceptual reference only.
- Original POSE `EmRegsVZ` and pinned Motorola `M68VZ328Hwr` via `research/sources.lock.json`; POSE reference defaults are NOT automatically Motorola official reset defaults. Review per-file license before reusing code.
- EmuTOS-Dana `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b` for board hardware accesses, NOT an authentic Palm boot substitute.

## 4. Do the work now — single boot objective, modular diagnosis only if helpful

1. **Inspect the actual checked-out T source/binary and the private firmware.** Verify hashes, no second emulator, no uncommitted user work overwritten. If T is not connected to this Codex environment, do as much source/firmware analysis and implementation as actually possible, then report the exact inaccessible requirement; do not invent execution or claim background progress.
2. **Resolve the earliest failing CPU bus transaction**, not a generic survey. Decode and disassemble first ~100 68k instructions from genuine image origin near raw offset `0xC80A` for 1.5, inspect jump/branch destinations and the first memory write, decode actual CPU state (PC/SR/SSP and effective address) using correct MAME APIs. Understand whether a valid stock Palm startup requires a separately protected boot sector or initial low RAM alias. Analyze updater's programming offsets and check whether the first longwords are genuine reset vectors or PalmCard metadata. Cross-check chip-select control values and runtime bus trace against pinned Motorola/Dana evidence.
3. **Implement the smallest real hardware correction** if and only if supported by authentic source/guest behavior. Integrate in the current `src/mame/skeleton/alphasdana.cpp`, without app-specific hooks or bypassing Flash write rejection. If original full dump is a hard requirement, state which sector/range and proof establishes it. A private test-only temporary image with missing bytes clearly marked hypothetical may be used to isolate the cause, but must never be presented as physical ROM fidelity.
4. **Build ONLY the existing reduced DANA DIAG** incrementally using the established Clang21/MAME build cache and inspect/record actual compiler output and hashes; no new branches/clones/worktrees/alternative emulators. Keep the old installed binary safe until a candidate has credible functional evidence. CPU guest trace must identify how far authentic Palm OS reaches; isolate a real Flash/remap/MMIO blockage and fix from evidence. Run US1.5 first, US1.2 for contrast when useful.
5. **Product acceptance:** success requires actual CPU-executed stock Palm OS reaching Palm UI with guest-driven framebuffer/input, no invented ROM vectors, fake MMIO, hidden exceptions or host-rendered screen. Prove first stages separately (valid image vector, first genuine instructions, DRAM chip selects, Palm initialization, LCD) but do not confuse partial steps with finished product. Preserve working EmuTOS R-direct / ST81 keyboard / SD regression with **targeted** tests only where changed behavior could affect them. Never rerun closed large suites just to produce activity.
6. **Report exact verifiable outputs:** commit(s) on canonical `main` (unless current authorization or repository safety requires leaving a reviewed diff), source changes, authentic image SHA (not bytes), binary SHA, MAME full CLI, native CPU PC/SSP/SR/bus sequence and first unresolved MMIO/register or guest UI evidence; PASS/FAIL/BLOCKED and the one remaining blocker. Update the existing handoff/status in-place without proliferating plans, trackers or artificial gates. Never claim an OS boot if only the loader or a synthetic guest succeeded.

## 5. Hard working constraints

- **Single working DANA DIAG product**; no new branch, clone, isolated version, parallel emulator, or alternate stable build. No Codex work in AS2K, Pro or EmuTOS/OS3K firmware repos; they are read-only references unless user explicitly expands scope.
- Protect the previously qualified 81-key ST keyboard, dual SD read/write, LCD, pen, GUI and EmuTOS boot. Do not replace known-good operating executable on a FAIL.
- Never write to a real physical Dana, host disk image outside disposable copies, user's original updater/ROM files or private firmware, and do not distribute copyrighted Palm ROM bytes.
- No blind address padding/mirroring, switching to synthetic RAM entry, patching Palm binaries, hardcoded success checks, CPU state shortcuts or ignoring exceptions to pretend Palm boots.
- Maximize **real product progress in one intervention**: focused module diagnosis is allowed where needed, but not artificial per-register gates or a stream of test-harness-only tasks.
- This handoff alone does not grant new **Remote Desktop Commander** privileges: the last ChatGPT intervention exhausted its five specifically authorized remote calls. Codex should use only the machine access and permissions the user explicitly supplies in its own environment, otherwise report BLOCKED access precisely. Do not claim that publishing these instructions executed Codex.

**Begin now with the private US1.5 source image and the first write at `PC=0x1000C812`. Work toward real Palm OS boot instead of offering another work plan.**
