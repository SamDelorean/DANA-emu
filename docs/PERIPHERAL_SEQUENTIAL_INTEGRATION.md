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
