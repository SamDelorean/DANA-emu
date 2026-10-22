> **CURRENT F2 SOURCE STATE — 2026-10-22: PREPARED / STATIC_SCOPE_REVIEWED / NO COMPILE / NATIVE_PENDING.** Exact candidate source pin `09f171b426c7180eea2c244861005176a9c5ac82`, SHA256 `105f882f77251ac3be4ee988f982ed88e64e6baadc775ca02fcd497a8f0df557`, Git blob `791926d45577a8adc407b0ada7e80e10d4c63c3f`. **Actual compiled-binary baseline** `581601b49acb6603af2a100817d0f06fed17ed96` (826 lines). New F2 candidate 897 lines, exact LCS diff **+84/-13 in 15 hunks**. Reuses F2 pen IO, PF1/PG2, ADC command/sample from previously written F2 but retains 012-C CPU, ST, LCD, UART, Timer1 and omits SPI1/uncompiled keyboard expansions. SPI2 enable mask changed from inaccurate `0x2100` to manufacturer-backed `0x0300`, with **no IRQ4 change**. Two bounded tests in `tests/dana_f2_012c_contract_test.py` mirror pinned EmuTOS `0x2247→0x2347→0x224f→0x234f`, ST chip select, pen states and legal zero speed-bit rates, no extra IRQ assertion; **tests prepared, not run**. Same existing 017 HOLD job now pins this source/tests, requires one driver compilation and restores source/object/**libmame_danadiag.a**/internal linker output in place; no T execution authorized by this doc. A genuine native F2 MMIO observer remains to be bound so compilation and native test can be performed in one campaign rather than repeating compilation. Earlier 80cb/78be F2 status below is retained as history and superseded. See `docs/F2_MANDATORY_SOURCE_CONTRAST_AND_NO_BLIND_TESTING_20261022.md`.

# DANA-emu — integración de periféricos uno por uno

**Rama exclusiva:** `codex/dana-peripherals-sequential-80cbfeca`.
**Base exacta:** `80cbfecab4df3c4412e370974295ac8a2f336fc1`, última versión que produjo pruebas nativas acotadas reales.

## F2 — lápiz táctil / ADC SPI2

F2 es el único periférico añadido a la fuente base. Se recuperaron las implementaciones reales previamente escritas, **sin recomponerlas**:
- Señal PF1 activa baja según entrada de contacto y configuración del GPIO;
- Señal PG2 para selección del ADC, separada de PE3/ST teclado;
- Secuencia SPI2 de orden 8 bits y respuesta de 16 bits para lecturas 12 bits de X/Y;
- Puertos MAME `PEN`, `PENX`, `PENY`, estado del ADC y guardado/restauración de sus latches;
- Se conservó íntegro el resto de periféricos base y el procesador Dana.

La nueva fuente es **idéntica por SHA de blob** a `alphasdana.cpp` del commit F2 original `9e870229afe6eff4b18eba7bf849fb3bb740cc84`:
`5bac95c484d5cb83e7089bc3225a9d3348765665`. Contra la base: **81 líneas añadidas, 8 eliminadas**, sin modificación de otros archivos de producción. No se han incorporado F3 ni F4.

Se reutilizó asimismo el único nuevo test F2 previamente escrito desde `f0a1c1890e4297b2ba3649ad755f8b0e8a0bdc9a`. Los cinco casos anteriores permanecen. **Los seis tests existen pero todavía no se han vuelto a ejecutar sobre este nuevo candidato.**

Preparado job acotado: `tests/hold/016_f2_stylus_only_diag.job.sh`. Fija el commit exacto de código/tests `78be96c5615c4b929a96c9dc835b9fff3a2161aa`, utiliza copia aislada del antiguo árbol de objetos y verifica antes de ejecutar que sólo se compilará `alphasdana.cpp`. No toca ROM, firmware, donante, ni originales. `HOLD`: requiere autorización vigente de Commander/T para compilar y ejecutar tests; el job no ha sido lanzado. **Sin afirmar PASS nativo ni DIAG nuevo.**

## Siguientes periféricos

Después de acreditar compilación y prueba F2, integrar **F3 (UART1 CTS)** sobre el mismo candidato y después **F4 (estado CTS_DELTA / BUSY / IRQ4)**, cada uno en su propia revisión fuente y su evidencia separada. Sólo `dana-diag` puede realizar pruebas nativas. No lanzar múltiples variantes ni recompilar un MAME completo como reacción a un único error.

## Objetivo de producto

No confundir aprobar un periférico con arrancar por completo EmuTOS. Mantener separados los indicadores de compilación, prueba periférica y arranque completo; la investigación Timer1/IRQ6 y GUI debe retomarse una vez disponible el ejecutable integrado.

## CURRENT OVERRIDE — SINGLE DIAG WORKTREE (2026-10-22)

The F2 execution job previously prepared in `tests/hold/016_f2_stylus_only_diag.job.sh` is **RETIRED** because it duplicates a complete build tree on every attempt. Do not run it again. User specifically stopped this practice; ONLY one active Dana emulator/build version is authorized, `dana-diag`. Future F2/F3/F4 increments go into the same canonical DIAG workspace without `cp -a` source/object trees, temporary full MAME copies, or parallel binary variants. Maintain only essential bounded evidence and Git history. The abandoned 2026-10-22 F2 copy `dana_integrated_hardware_j7xxm3xq` and its `f2_stylus_single_WLcT8C` launcher directory were both deleted after process termination (1.5GB plus ~2.1MB), without touching the older 012C qualified cache. The source F2 integration in Git remains valid **as uncompiled/unqualified code**; no F2 runtime PASS has been established. A replacement one-worktree job must be designed before any new T execution and requires new authorization.


## F2 — single active DIAG continuation (2026-10-22)

A replacement HOLD job is now at tests/hold/017_f2_one_active_diag_inplace.job.sh. It targets **only** the retained canonical DIAG tree /home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag and source commit 78be96c5615c4b929a96c9dc835b9fff3a2161aa. No MAME copying, detached secondary worktree, additional DIAG installation, stable build, replacement compiler, or ROM rebuild is permitted. The MAME driver source/object and existing internal linker output are preserved in process memory and restored in place after the attempt. It uses a read-only \`make -n\` check for exactly one new driver object, then one incremental Clang build and the **six pre-existing source-method tests** applied to the actual staged driver.

**Evidence scope:** compiled driver + six directed code-level tests only. These do NOT establish an authentic guest pen-contact/SPI2 native PASS; the installed prior qualified \`dana-diag\` remains unchanged until a new candidate has a separately evidenced native peripheral qualification. After that, F3 CTS and F4 IRQ may be integrated sequentially in the same installation. The existing 016 job is permanently retired.

**Execution:** NOT RUN. It explicitly requires a fresh T/Commander authorization and is never polled. Git edits and HOLD preparation do not count as a MAME compile or native proof.
