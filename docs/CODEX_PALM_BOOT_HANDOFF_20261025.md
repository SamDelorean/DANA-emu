# Codex takeover — DANA-emu authentic Palm OS boot (2026-10-25)

## ÚLTIMO RESULTADO REAL, AUTORITATIVO PARA CODEX — UK1.5 NATIVO EN T, SCR.DMAP (2026-10-25)

**Este párrafo sustituye cualquier instrucción histórica que ordene a Codex investigar firmware o implementar arranque Big ROM asistido.** La investigación de hardware se hace en este chat; **Codex solo codifica un cambio concreto**.

**EVIDENCIA:** `docs/PALM_UK15_NATIVE_20261025.json` (ejecución nativa real) y `docs/PALM_UK15_NATIVE_SCR_DMAP_20261025.md` (**causa documental y contrato de codificación completo; léelo primero**). Se compiló en T el parche de cobertura `main@07443b2` con Clang21, sin errores; candidato SHA256 `a335583ebb7cc1f29fd7b8d6f5f22f1ddfb72a2e964b668db40ebbd4e09b5984`, binario operativo intacto `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. Se extrajo privadamente UK1.5 120/120 Flas, `0x5D0000` bytes, SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`, sin relleno ni publicación ROM. CPU hizo vectores reales SSP=`00000316`, reset PC=`100002A2`, Small ROM ejecutó a `CURPC=1000514C` y se bloqueó erróneamente cuando escribió `SCR=F0` en `FFFFF000` (motivo `SCR_DMAP_MODE`). **Manual Motorola cap.5:** DMAP=0 elimina alias duplicados `XXFFF000`, pero mantiene los registros en `FFFFF000`. El código actual `scr_w` bloquea esta operación válida.

**SIGUIENTE INCREMENTO CODEX CERRADO:** Cambiar SOLO `alphasdana_state::scr_w(u8)`: preservar W1C y reset SCR, retirar bloqueo por `DMAP=0` y comentario falso; conservar decodificación interna superior. Compilar incrementalmente con Clang21 en único DIAG y repetir UK1.5 `-rom` en binario candidato sin instalar, devolviendo el primer próximo bloqueo real con CURPC/máscara. No hacer Ghidra, investigación abierta, refactor ni nuevas ramas; no preimplementar Watchdog/PLLCR basándose en predicción estática. El último código intacto de Small ROM predice escritura al WATCHDOG `FFFFFB0A`, luego PLLCR `FFFFF200`, pero **AÚN NO EXISTE PRUEBA NATIVA** para esos registros. El firmware no ha arrancado Palm OS hasta su UI. La autorización previa para Commander ya agotó 5/5 llamadas y no se renueva mediante estos documentos.

---


**This file is the complete executable work brief for Codex. Start implementation, not a proposal or additional handoff.** User-facing conversation: Spanish. Git commits, code and repository technical records: English.


## Handoff para GPT — ejecutar UK1.5 y analizar el primer bloqueo real

**Solicitud actual: realizar la ejecución y su análisis en GPT. No reabrir la investigación de firmware ya entregada ni delegar otro plan a Codex.**

### Estado concreto que se entrega

El código de cobertura está implementado en `main`. Procedencia local:
`23830f56bd14cfa49ddc5a9436fb72a570b7e93b`; al publicarlo por la conexión GitHub
el SHA del commit cambia. Verificar el contenido del controlador mediante SHA256
`9b0e03909c21717758f9f75a31540b28f5943b377b2a0f000f7788b18885783e`.
Base canónica anterior: `0a159bd2d208c32eab6c987e2880cd78fe00a3a5`.
No ramas, clones ni worktrees nuevos.

Cambios funcionales exclusivamente en `src/mame/skeleton/alphasdana.cpp`:
acepta tamaños pares originales, conserva la asignación exacta, registra cobertura
para streams no potencia de dos, bloquea lecturas no suministradas con
`FLASH_BYTES_NOT_SUPPLIED`, y registra palabras/máscaras de los vectores reales.
Para el stream parcial usa una ventana experimental de reset de 16 MiB, con
bits bajos de dirección; **esto no acredita capacidad, cableado o espejos del chip**.
No convierte el tamaño del stream en un módulo, no agrega bytes y no altera
el reset ni los registros CPU. CSA/CSD/DRAM y protecciones siguen como estaban.

`tests/d8_5_physical_boot_test.py` actualiza únicamente la evaluación de tamaños
y prueba último word disponible, primer word ausente, ausencia de wrap y CSA
programada. Las pruebas enfocadas y compilación de cabeceras pasan; no hubo
compilación/enlace Clang21 ni ejecución UK. La suite histórica completa no se
ha declarado PASS: sus fallos de preservación anteriores siguen documentados.

### Fuente privada ya resuelta: usar UK1.5 coherente

Leer `docs/PALM_UK_SMALLROM_RESEARCH_20261025.md` y el registro JSON existente.
Archivo Drive `1LY_Ykm3RysWe4vutxWeFRnwSTCxlIcFg`,
`AlphaSmart_Dana1_5_Flash.zip`, SHA256
`1a0256e35c11c7455a58738f05218e1e290b8d381a5742467f1a512ac25c14fc`.
Ruta esperada en T: `/home/spc/Projects/Dana-OS3K/firmware/research-only/`.
Contenedor anidado: `Dana UK 1.5 update/ROMUpdater_enUK150R1.ZIP`;
PRC `ROMUpdater_enUK150R1.prc`. Reutilizar `resources` y `payload` de
`tools/palm_updater_audit.py`: 120 recursos Flas, quitar solamente el checksum
final validado por suma de bytes de cada recurso y concatenar por ID.
Resultado exacto: **6,094,848 bytes / 0x5D0000**, SHA256
`2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.
Cobertura suministrada: `[0x00000000,0x005CFFFF]`.

Small ROM auténtico UK en offset 0, Big ROM UK en 0x8000. Valores de entrada
**esperados del archivo, todavía no medidos en una ejecución UK**:
SSP/campo initStack=0x00000316, PC=0x100002A2; JMP PC-relativo a
0x10000316. La entrada declarada del Big ROM es 0x1000C80A.
No mezclar UK/US, no agregar cola FF, no inyectar registros y no usar quickload.
El prefijo Small ROM ya fue encontrado: no seguir afirmando que falta de todas
las fuentes. La geometría física completa continúa sin acreditar.

### Único entorno y protección del operativo

T: `spc-HP-t640-Thin-Client`, ID conocido
`dee0b4b6-578a-41a5-88de-73dbeb808983`; su disponibilidad actual debe comprobarse.
DIAG: `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`.
Fuente en `source/`, instalado `bin/dana-diag`; único artefacto intermedio de
la misma compilación `source/danadiagd`. No ejecutar otro emulador.
Último instalado verificado y restaurado:
`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
Última fuente T conocida antes del incremento rechazado:
`beb460df6e04013d1bc24c542b89276a088cf06fc0e96e52fedd566c57cc7eda`.
Si algo difiere, reconciliar sin sobreescribir trabajo del usuario.

**Autorización remota pendiente.** Las cinco llamadas anteriores se consumieron
en el ensayo US; no autorizaron esta nueva campaña. La revisión automática
rechazó expresamente el intento UK por falta de autorización renovada para
compilar, sustituir temporalmente el ejecutable instalado y ejecutar firmware.
La llamada rechazada no hizo nada en T. Este handoff no renueva el cupo y no
permite eludir el rechazo con otros canales. Obtener consentimiento explícito
para el número de llamadas y el procedimiento de calificación temporal antes
de actuar remotamente. Conservar el original y restaurarlo si el candidato
no queda calificado; no promover un candidato por el simple exit code 0.

### Ejecución concreta pendiente, una vez autorizada

1. Verificar hashes y ausencia de otra compilación; preservar el operativo.
   Integrar el diff del controlador contra la fuente verificada del mismo árbol.
   Preparar únicamente el stream privado UK exacto y el observador ya publicado.
2. Inspeccionar `make -n` y compilar con la caché existente. La orden calificada
   anterior es:
   `make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang-21 OVERRIDE_CXX=clang++-21 OVERRIDE_LD=clang++-21`.
   Exigir un alcance incremental: controlador, archivo y enlace necesarios;
   no REGENIE ni reconstrucción general sin una causa concreta.
3. Medir SHA del candidato. Ejecutar únicamente el DIAG con perfil
   `asmdana -rom PRIVATE_UK15.raw`, sin `-quickload`, sin parches de firmware.
   Utilizar un límite de tiempo externo que termine realmente el proceso.
   El observador existente requiere `DANA_PALM_TRACE=PRIVATE_LOG`; para autoboot
   usar `-autoboot_script PRIVATE_OBSERVER.lua -autoboot_delay 0`.
   Ya usa SP y `emu.add_machine_stop_notifier`, con suscripción retenida;
   **su corrección completa todavía requiere validación nativa**.
4. Reutilizar debugger/trace nativo y logs del controlador para registrar los
   cuatro accesos de reset, SSP/PC/SR, salto Small ROM, cambios MMIO y primera
   dependencia no resuelta. CURPC es la dirección relevante; IR puede contener
   la siguiente instrucción prefetched. No tomar lecturas del debugger como
   accesos CPU ni ocultar el primer bloqueo. Guardar CLI, errores y códigos
   reales. Si llega a LCD, guardar evidencia del framebuffer del invitado.
5. GPT analiza la evidencia contra el contrato Motorola y la investigación
   entregada. Un fallo local inequívoco puede corregirse dentro del alcance y
   autorización restantes; una discrepancia de hardware no investigada se
   devuelve con dirección, máscara/anchura, registros y última instrucción.
   No inventar respuestas MMIO, sectores o una interfaz Palm anfitriona.

### Entrega y aceptación

Devolver commit/rama y archivos, salida de compilación, SHA candidato, CLI,
SSP/PC/SR **medidos**, primer salto, última instrucción correcta, primer bloqueo
concreto y estado/hash del operativo. Actualizar estos mismos documentos y
`docs/PALM_UPDATER_DERIVED_COLD_BOOT_20261025.json`.
Solo declarar arranque completo si Palm OS genera su UI mediante CPU y
framebuffer emulados. Si no puede ejecutarse, clasificar como bloqueo de acceso;
si se ejecuta y encuentra dependencia no soportada, reportar bloqueo técnico
real. Nunca convertir un ensayo parcial en PASS de Palm OS.

## UK1.5 coverage implementation — current coding result

**IMPLEMENTED / STATIC_PASS / REMOTE_AUTO_REVIEW_BLOCKED / NOT_NATIVE_TESTED.**
Based strictly on the delivered UK research, the existing physical loader now
accepts even raw stream lengths in its original 128 KiB–16 MiB bounds. It
allocates exactly the supplied byte count; the existing generic cartridge API
retains this exact size. Non-power-of-two inputs log supplied coverage and
`UPDATER_DERIVED_RESET_EXPERIMENT`; they do not declare a chip capacity.
Partial-stream reads use the existing maximum 16 MiB reset decode window as
an explicitly unqualified experimental address window, then enforce the exact
supplied boundary. They never modulo by the stream length or read allocation
padding. A missing word logs address, array offset, lane mask and supplied size,
then suspends with `FLASH_BYTES_NOT_SUPPLIED`. The established power-of-two
array aliases and configured chip-select/DRAM/protection rules remain intact.
No physical mapping fidelity is claimed by admitting this experiment.

Reset still fetches the original words through the CPU bus; those four reads
now log values and masks. No SSP/PC injection, guest-byte modifications, RAM
seed or synthetic prefix was added. Existing native snapshots and the fixed
Lua observer provide the remaining compact CPU/MMIO trace on an authorized
run. No peripheral implementation or reset/lifecycle method was changed.

The exact original UK1.5 nested PRC was processed using the existing parser:
120 Flas chunks, every byte-sum valid, 6,094,848 bytes, SHA256
`2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.
Private original stream is `/workspace/work/palm-uk/UK15.raw`, outside Git.
Its supplied array coverage is 0x00000000–0x005CFFFF. This is preparation of
already researched bytes, not new firmware or hardware research.

Checks executed: full driver g++14 C++20 `-fsyntax-only -Werror` with pinned
MAME headers PASS; focused existing constant-evaluation test PASS, extended for
partial final word, first missing word, no modulo wrap and programmed CSA;
existing Lua mock PASS; comparison of all existing out-of-class peripheral and
lifecycle methods PASS; whitespace check PASS. The old historical preservation
suite was not rerun or relabelled as passing. No object or binary was built.

**Remote action rejected, not executed.** Automatic approval review rejected
exact-match staging, incremental Clang21 build and the same canonical DIAG's
native candidate qualification because the prior Commander quota is exhausted
and renewed remote authorization is absent. It also identified temporary
replacement of the installed emulator for qualification as requiring explicit
approval. No T source/image/binary was modified by the rejected call. No native
SSP/PC/SR, instruction trace, LCD output, candidate binary SHA or new guest
blocker exists for UK1.5 yet. The final delivery is therefore BLOCKED at remote
execution, not a claim of a firmware or hardware failure.

The same existing JSON receipt records this increment under
`uk15_coverage_increment`. `main` was synchronized to exact checkpoint
0a159bd2d208c32eab6c987e2880cd78fe00a3a5 through GitHub readback before editing;
no branch, clone or worktree was created. The single operating executable
remains unmodified; its SHA must be freshly checked on an authorized preflight.

## INSTRUCCIÓN RECTORAL ACTUAL — INVESTIGACIÓN AQUÍ; CODEX EXCLUSIVAMENTE DESARROLLO (2026-10-25)

**Decisión expresa del usuario:** la investigación del firmware, ingeniería inversa y conclusiones de hardware se realizan en ESTA conversación de ChatGPT. **Ghidra está instalado en T y es una herramienta de NUESTRA investigación**, no un paquete de tareas de descubrimiento indefinido que Codex deba asumir. **Codex solo desarrolla, compila, prueba e integra cambios de código cerrados y especificados a partir de hallazgos entregados aquí.** Esta sección tiene autoridad sobre cualquier instrucción anterior del archivo que pida a Codex investigar con Ghidra o diseñar una vía de arranque asistido.

### HALLAZGO MATERIAL Y NUEVA FUENTE AUTÉNTICA

**YA ENCONTRAMOS el Small ROM en el ZIP original del usuario, dentro de los ACTUALIZADORES UK 1.5 y UK 1.2.** Investigación directamente reproducida aquí sobre los bytes privados del archivo Drive. Ver informe con tamaños y SHA, checksums 391/391, doble PalmCard, comienzo del código de arranque, distinción UK/US y limitaciones de geometría: **[docs/PALM_UK_SMALLROM_RESEARCH_20261025.md](PALM_UK_SMALLROM_RESEARCH_20261025.md)**. No pedir a Codex repetirla ni especular que el primer bloque 0x8000 falta de todas las fuentes.

Resultado esencial: `ROMUpdater_enUK150R1.prc` contiene 6,094,848 bytes `Flas` concatenados, **Small ROM en offset 0**, Big ROM en **offset 0x8000**. El encabezado Small ROM posee `initStack=0x00000316, resetVector=0x100002A2, signature=FEEDBEEF, hdrVersion=5, flags=0x0040`; en `0x100002A2` hay `JMP (0x72,PC)` que salta al código real de la imagen en `0x10000316`. Big ROM en 0x8000 con entrada `0x1000C80A`. `ROMUpdater_enUK120R2.prc` también incluye Small ROM desde offset 0 y Big ROM en 0x8000, con el mismo vector Small `0x100002A2` y Big `0x1000C776`. Las versiones estadounidenses contienen solo el encabezado Big ROM desde offset cero; **NO mezclar UK Small con US Big** para simular una ROM genuina. Los archivos privados originales se conservan íntegros. Es contenido de paquetes oficiales, pero no está acreditado que incluya todos los sectores/bytes de la Flash física completa.

### ÚNICO OBJETIVO DE PRODUCTO: RESET FÍSICO FIEL MC68VZ328

El único `bin/dana-diag` debe ejecutar vectores reales suministrados por un firmware original desde la selección CSA0 del DragonBall VZ, seguir el Small ROM auténtico, configurar CS/DRAM/MMIO genuinos y arrancar Palm OS con LCD/teclado procesados por el invitado. No inyectar SSP/PC, falsear bootloader, construir cabecera Small ROM, cambiar 0x0 a RAM para ignorar error, generar pantalla Palm en anfitrión, ni presentar un arranque asistido como fiel. Manual Motorola MC68VZ328UM caps. 6, 9.3; comprobar topología de Flash mediante registros y evidencia antes de acreditar fidelidad eléctrica.

### PRÓXIMO CONTRATO DE CODIFICACIÓN PARA CODEX

**Entrada autorizada para implementar:** en la rama `main` del único `SamDelorean/DANA-emu` trabajar solamente sobre el controlador físico existente y utilidades de diagnóstico estrictamente necesarias para una **prueba de cold reset nativo a partir de la IMAGEN UK1.5 coherente de un único actualizador original**. No inventar prefijo: el original UK *sí lo contiene*. El `firmware_load` actual rechaza longitudes no potencia de dos: la imagen UK1.5 `0x5D0000` y UK1.2 `0x3C0000` son contenidos originales de los paquetes, pero **no dimensiones certificadas del chip**. Implementar una prueba de memoria **con cobertura explícita de bytes conocidos** que detecte y detenga cualquier lectura de regiones no proporcionadas, manteniendo los flujos de selección de Flash y vectores por reset real; no aceptar relleno como bytes originales, no ocultar accesos desconocidos, no modificar firmware ni comandos NOR sin fuente. Calificar como `UPDATER_DERIVED_RESET_EXPERIMENT` hasta demostrar el mapa físico completo. No reemplazar el DIAG instalado antes de PASS real. Mantener funcionalidades cerradas de 81 teclas, LCD, doble SD, UART, táctil y EmuTOS.

**Criterio de devolución a ESTA conversación:** Codex entrega exclusivamente diff/commit, compilación incremental y TRAZA REAL de CPU SSP/PC/SR y primer acceso MMIO/Flash/RAM o avance hasta UI, con la dirección de instrucción correcta. Nos encargamos AQUÍ de interpretar la evidencia, decidir requisitos físicos y diseñar el siguiente incremento cerrado. No solicitar a Codex plan general, búsqueda de fuentes, nueva investigación de firmware, tareas en Ghidra ni otra arquitectura. Sus llamadas a T dependen de autorizaciones explícitas en su entorno; esta transferencia no otorga permisos nuevos.

**Código existente protegido:** `bin/dana-diag` instalado y calificado SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. No ramas paralelas, clones, nuevos DIAG ni publicación de bytes comerciales.

---

## HISTORICAL RESEARCH — 2026-10-25 — POSE Big ROM file structure (NOT AUTHORIZED AS BOOT STRATEGY)

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

**C2 — HISTORICAL NOTE; DO NOT IMPLEMENT AN ASSISTED BIG ROM BOOT.** The previously contemplated POSE-compatible Big ROM synthetic startup is explicitly **withdrawn by the user's latest hardware-fidelity mandate**. Keep the POSE source above as a structural clue only: use it to distinguish PalmCard metadata, Big ROM, and missing Small ROM; do not add an alternate boot profile, inject SSP/PC, fabricate first-sector vectors or change the physical loader to accept an updater as a complete ROM. Instead, use Ghidra on T to identify the original boot block's address, NOR sector layout and updater write coverage, and recover genuine bytes if present. If absent, document the precise region and evaluate a *read-only* authenticated hardware dump only with explicit owner consent.

**C3 — prioritize authenticated physical cold boot as the ONE product target.** Once genuine complete SmallROM contents become available, map full Flash, execute actual CPU reset fetch at original physical vectors and prove transitions from SmallROM to BigROM and then Palm UI. Never quietly use BigROM-assisted injected PC as physical reset, or treat a padded Flash array as a recovered dump. Protect canonical installed DIAG SHA `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`; stage/atomically install only a verified successor.

**C4 — acceptance:** (a) read-only exact header/layout report; (b) visible native MAME 68k PC/SP/SR and guest-produced Palm framebuffer via hardware accesses in the one DIAG; (c) interactive Palm keyboard events using the qualified ST/SPI2, then Palm startup/launcher; (d) no regression to current keyboard/SD/LCD/EmuTOS. For physical fidelity additionally demand byte-authenticated SmallROM and actual reset fetch. On any blocked step, deliver *one* decisive actual guest CPU+bus blocker and the minimum further evidence—not a new program of gates.

**Key distinction (CURRENT)**: The sole accepted product is authentic MC68VZ328 cold reset through real boot ROM. BigROM-only POSE workarounds are useful for understanding file format but expressly NOT allowed as an implementation or interim boot deliverable. No additional T calls are authorized from this handoff; actual Codex machine access and permissions must come from the user.

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
