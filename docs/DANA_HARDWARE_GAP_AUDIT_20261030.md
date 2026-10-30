# DANA-emu — auditoría de cobertura de hardware

## Current USB execution status — 2026-10-30

The single canonical Dana emulator now has explicit downstream USB printers and a packet-level upstream link, retaining the existing Philips PTD/SRAM implementation. Original UK1.5 AlphaWord printing produced a complete 10409-byte PostScript job containing the test document. Diagnostic 68000 HC/DC endpoint, FIFO, IRQ, DMA and robustness tests passed. The original-Palm USB Computer/HotSync path has not enabled SoftConnect in the tested Cable workflow; original enumeration and end-to-end synchronization remain pending. **The full ISP1161 contract is OPEN, not CLOSED/PASS integral.**

See [USB integration and native qualification](ISP1161_USB_INTEGRATION_20261030.md) for the command matrix, Ghidra paths, evidence, limitations and installed artifact. The sole installed executable is `runtime/diag/bin/dana-diag`, SHA-256 `34c0ddd062c15427b5485d7d99b1a9ab8b17da8873af51ed2d32cca000d7142b`. The previous operative is retained compressed for rollback. Older build/install locations and continuation cursors below are historical. The later LCD grayscale and physical audio queues remain deferred and unchanged.

**Corte:** 30 de octubre de 2026. **Modalidad:** auditoría estática del código integrado y conciliación de pruebas existentes; no se recompiló ni modificó el ejecutable.

**Única versión:** `main@cc05666`, `runtime/diag/bin/dana-diag`. Git inicial limpio. SHA-256 del ejecutable: `db7404acb1b0ea44431d05e442dac231c1add2508bd1bcd217c35c2d628f5f3e`.

**Criterio de estados:** **ACREDITADO** = operación concreta probada nativamente con CPU/ROM invitado; no implica reproducción eléctrica/ciclo-perfecta. **PARCIAL** = el código ejecuta alguna función pero faltan facetas verificables o conexiones. **AUSENTE** = no existe trayecto funcional de emulación. **PENDIENTE FÍSICO** = no debe inventarse una conexión/semiconductor del PCB sin medición o fuente.

## Matriz de componentes

| Hardware / función | Estado real al corte | Evidencia y límite concreto |
|---|---|---|
| **Motorola MC68VZ328 / CPU 68000 y bus de 32 bits** | **ACREDITADO para Palm OS/EmuTOS; PARCIAL en fidelidad VZ** | ROM original UK1.5 arranca y ejecuta AlphaWord, MMIO y 68k; reset/CSA/CS y SDRAM operativos. Se reutiliza MAME M68000 y configuración VZ. No se afirma paridad de todas las funciones internas, timings y pad eléctrico. `alphasdana.cpp` clases CPU/CS/reset/MMIO. |
| **SDRAM y control DRAM** | **ACREDITADO funcional / PENDIENTE FÍSICO** | RAM 8/16 MiB configurable, CSD/CAS y secuencia SDRAM modeladas. U5 Samsung K4S641632F-TL1L 8 MiB identificado por topmark; continuidad U5↔VZ y cantidad total por variante no medida. `alphasdana.cpp` `physical_reset`, `dram_w`; `DANA_HARDWARE_INTERCONNECTION_ATLAS_20261026.md`. |
| **NOR Flash interna y arranque real** | **ACREDITADO lectura/boot; PARCIAL escritura** | Reset/lectura original UK1.5 y CS, ID/status seleccionados. Programación, borrado, lock, CFI y geometría de chip real no implementados (`NOR_COMMAND_NOT_IMPLEMENTED`); U7 TSOP48 no identificado por código/topmark bajo etiqueta. Actualización de firmware Palm/OS3K desde el guest NO probada. |
| **LCD 560×160 / DMA framebuffer** | **ACREDITADO visual; PARCIAL eléctrico** | Imagen producida por RAM real, boot, menús, AlphaWord y F12. Contraste, retroiluminación, polarización, LCD IRQ y tasa de refresco real no emulados; 60 Hz provisional. Fuente `screen_update`, comentario y `alphasdana(machine_config&)`. |
| **Teclado físico ST y SPI2 / IRQ1** | **ACREDITADO 81/81** | `cc05666`: lectura ROM original, IRQ1 real, Get Ver!, 5/5 acordes, teclado físico SDL, escritura/edición AlphaWord, restablecimiento de Shift después de savestate; F12 y atajos resueltos. `DANA_UK15_KEYBOARD_NATIVE_PASS_20261030.md`. No rehacer. |
| **Digitalizador / ADC por SPI2 / IRQ5** | **ACREDITADO calibración y clics; PARCIAL analógico** | 3 cruces, acceso a escritorio, mouse en PALM; 7+1+16 bits, polaridad X/Y, PG1, IRQ5. Extremos/linealidad son mapeo provisional, no coeficientes físicos medidos. `PALM_UK15_CALIBRATION_20261029.md`. |
| **PWM1 / audio mono** | **ACREDITADO salida lógica/WAV; PARCIAL fidelidad** | FIFO, registro y pulsos PWM1 reproducidos en SPEAKER_SOUND; WAV con muestras no nulas, menú Volume/Mute. Falta exactitud analógica, modo REPEAT y ciclo preciso, escucha por bocinas físicas aún no acreditada. `PALM_UK15_PWM1_AUDIO_20261029.md`. |
| **RTC y calendario Palm** | **ACREDITADO uso principal; PARCIAL periférico RTC** | Host HH:MM:SS y fecha Palm preconfigurada mediante formato inicial `SysNVParams`, persistencia y pruebas de bisiesto. RTC rate/otras interrupciones: `RTC_INTERRUPT_RATE_UNIMPLEMENTED`; no extrapolar a RTC completo. `DANA_HOST_CALENDAR_PRESET_20261029.md`. |
| **Timer1 y controlador de IRQ** | **ACREDITADO para rutas probadas; PARCIAL global** | Timer1, IACK, fuentes SPI1/SD/IRQ1 teclado/IRQ5 lápiz/IRQ6 power, UART/RTC según rutas; no calificar todas las fuentes VZ. `timer1_schedule`, `update_irq_lines`. |
| **Timer2 and watchdog** | **Timer2 SYSCLK USB use ACCREDITED; watchdog active clock ABSENT** | Original HC ATL upload at 10301D42 required TPRER2/TCMP2/TCN2 and enabled TCTL2; independent Timer2 timing/IRQ/save-state added as demonstrated USB dependency. Original printing now passes. Capture/TIN fidelity is not qualified; enabled watchdog still blocks as before. |
| **PLL, relojes, suspend/STOP y energía VZ** | **PARCIAL** | Palm ejecutó suspensión/despertar y teclado power; hay fórmula SYSCLK y timer de PLL wake. `PLL_CLOCK_MODE_UNIMPLEMENTED`, `PLL_SLEEP_MODE_UNIMPLEMENTED_R_DIRECT`, `PLL_WAKE_DELAY_UNIMPLEMENTED`, `PCTLR_CPU_BURST_UNIMPLEMENTED`. CPU parte de 1 MHz provisional y ajusta reloj de boot; LCD 60 Hz provisional. |
| **GPIO y control de pines** | **ACREDITADO rutas usadas; PARCIAL mapa físico** | B/D/E/F/G/J/K/M, selección pen, ST, SD, power. `PCDATA_PIN_LEVEL_UNQUALIFIED` para combinaciones no probadas; otras entradas son latches/modelos de arranque. No equiparar hoja de pinout con continuidad PCB. |
| **SPI1 y doble SD/MMC** | **ACREDITADO rutas de lectura/escritura; PARCIAL placa física/UI** | Dos imágenes aisladas, transferencias CPU SPI1, CMD24/25, CRC, protección, persistencia y lectura/escritura a tarjetas desechables; regresión reciente 4/4 PASS. Falta demostrar eléctricamente línea de detección de cada ranura, orientación izquierda/derecha, inserción real/interruptores y fidelidad de todos los tipos/tamaños de SD; confirmar selectores/política persistida en interfaz final. `D7_5_SD_WRITE_PERSISTENCE.md` y `DANA_UK15_KEYBOARD_NATIVE_PASS_20261030.md`. |
| **ISP1161A1 USB Host Controller** | **ACCREDITED for original AlphaWord USB printing; integral fidelity PARTIAL** | Explicit printers/diagnostic functions, two ports, real MMIO/PTD SETUP/IN/OUT, ATL/ITL, errors, overcurrent, unplug and save/restore qualified. Original UK1.5 emitted a complete PostScript job. Bandwidth/LS peripheral and power details remain bounded by `ISP1161_USB_INTEGRATION_20261030.md`. |
| **ISP1161A1 USB Device Controller** | **PARTIAL; diagnostic endpoint/packet path ACCREDITED** | 2462-byte SRAM, all endpoint entries, EP0, double FIFO, data/toggle/status, packet host link, IRQ2/IACK and 8/16-bit abstract DMA qualified by native 68000. Original-Palm SoftConnect/enumeration and genuine HotSync remain pending; physical attach/DMA continuity and suspend write protection are not qualified. See USB integration report. |
| **UART1 / puerto serie físico** | **PARCIAL** | Registros USTCNT/UBAUD/UTX/URX; TX solo emite `logerror` (`DANA_VZ_UART1_TX`), sin PTY/RS-232 ni RX real de host, FIFO/IRQ completo, control de flujo o enlaces. |
| **UART2 / segundo puerto serie** | **PARCIAL** | Banco de registros y bits de control; `UART2_TX_FIFO_UNIMPLEMENTED`, `UART2_SEND_BREAK_UNIMPLEMENTED`, sin RX/TX externo operativo. |
| **IrDA/infrarrojo** | **AUSENTE** | Ninguna implementación de ruta IRDA/infrared en controlador principal, sin transceptor/transferencia emulada ni pruebas Palm Beam. Primero verificar señal/UART/pin mux original antes de modelarlo. |
| **Batería/carga/estado de alimentación** | **AUSENTE como fuente de telemetría física** | Sin modelo dedicado de batería, carga/descarga, adaptador ni estado/ADC de tensión. El pulsador Power y STOP no constituyen medición de batería. No inferir circuitos de la PCB. |
| **Bootstrap de silicio EMUBRK/UART** | **PARCIAL** | Entrada EMUBRK, vector y parser B-record existente; el parser deja explícitamente modos word/long/read sin implementar. No existe una conexión física host-UART para un bootstrap fiel ni cableado medido en pads J100; no confundir quickload auxiliar con arranque electrónico real por UART. `vz328_bootstrap.h`. |
| **ICE/depuración interna, DMA y funciones VZ menores** | **PARCIAL / AUSENTE según función** | ICE/control no ordinario marca `ICE_CONTROL_MODE_UNIMPLEMENTED`, `ICE_EMULATION_MODE_UNIMPLEMENTED`. DMA USB externo DREQ/DACK no enlazado. MMIO general no reconocido bloquea deliberadamente; no suplantar dispositivos con valores falsos. |

## Priorización basada en valor para el emulador

**P1 — USB ISP1161A1 completo, HC y DC como un solo dispositivo.** Conservar la arquitectura existente PTD/HC/DC; integrar un backend de dispositivos y endpoints real, datos, IRQ/transferencias y host↔Dana. Sin inventar conexión de un USB externo. Permite evaluar Palm HotSync y transferencia USB. La construcción de esta unidad debe ser integral; no una larga serie de falsos PASS por registro.

**P2 — UART1/UART2 + IrDA.** Una campaña de comunicaciones coherente (puertos virtuales, RX/TX reales y colas/IRQ, control de flujo, y ruta IrDA separada si el hardware original así lo exige). Una ROM Palm funcional no acredita todavía HotSync, Beam ni serial.

**P3 — funciones auxiliares DragonBall VZ.** Timer2, watchdog, RTC rate, fuentes/mascaras de IRQ menos utilizadas, clock/PLL y gobernanza de energía. Implementar por contratos del manual + trazas de invitados; no cambiar partes ya validadas de wake.

**P4 — fidelidad física de Flash/SDRAM/GPIO/SD.** NOR identificación del chip U7, borrado/programación/sector/estados; medición de señales reales en tarjetas, U1 ISP1161 y U5 SDRAM, 8/16MiB por variante. El Excel de interconexiones v04 es la fuente de incertidumbres de placa, NO evidencia de continuidad.

**P5 — presentación/uso del hardware.** LCD contraste/backlight, audio PWM analógico/REPEAT, calibración ADC física, medición de batería y selección/perfil/persistencia. Son importantes para experiencia/fidelidad, pero no bloquear innecesariamente las interfaces centrales ya acreditadas.

**Dependencias de firmware/producto — no confundir con hardware faltante:** OS3K-Dana nativo, firmware update, DanaRun y elección amigable de ROM/SD son objetivos del producto que requieren pruebas independientes; los periféricos existentes pueden bastar para algunos y otros exigir hardware adicional. No exigir USB/IrDA para completar un arranque que no los usa.

## Reglas de esta auditoría
- Fuente: `main@cc05666` y archivos citados. Se han leído pruebas ya archivadas; no se ha repetido ninguna campaña, ni cambiado código/binary privado.
- **No asignar porcentajes globales**, porque los criterios no son equivalentes (registro implementado ≠ dispositivo conectado).
- Se conserva el indicador MAME `MACHINE_NOT_WORKING` en el driver: procede mientras falta fidelidad general, pese a que el Palm OS/AlphaWord concreto sí funciona.
- La foto del PCB confirma U4 MC68VZ328PV y U5 Samsung, pero U7 no tiene chip identificado y las nets no han sido medidas; consultar `DANA_HARDWARE_INTERCONNECTION_ATLAS_20261026.md` antes de asumir conectividad.
- Los estados ACREDITADO se circunscriben al alcance de las pruebas nativas archivadas; por ejemplo, WAV con muestras no nulas no es una escucha externa, y SPI SD de dos tarjetas no es detección eléctrica de ambas ranuras.

## Incorporación posterior a la cola — 30/oct/2026 (sin modificar la auditoría del corte)

**LCD D3.6 — P5 / EN COLA, posterior al ISP1161:** cuatro niveles de gris mediante framebuffer de 2 bpp; confirmar LPICF, LGPMR, stride, conversión de píxeles y prueba de 4 valores desde RAM real del invitado.

**LCD D3.7 — P5 / EN COLA, posterior al ISP1161:** dieciséis niveles de gris mediante framebuffer de 4 bpp; confirmar LPICF, memoria, orden de bits, 16 valores efectivos y características por versión de Dana/Dana Wireless.

Ambas capacidades deben coexistir con el renderizador 1 bpp ya acreditado, sin cambiar ni parchear Palm OS, y sin presentar un efecto de posprocesado del host como soporte de hardware. **Estado: pendientes, no implementadas; ninguna prueba ejecutada en esta incorporación.** Los 21 estados de la auditoría de hardware permanecen intactos. Control rector: pestaña HITOS (D3.6-LCD-4G, D3.7-LCD-16G), AUD_HW_20261030 (HW30-04) y BITACORA.

## Registro complementario — audio de la placa Dana (P5; 30/oct/2026)

**AUDIO-HW-01 — P5 / EN COLA, posterior al ISP1161:** revisar qué capacidades de generación de sonido del MC68VZ328 están **efectivamente conectadas** en la placa y usadas por la ROM: PWM1, PWM2, posibles mezclas, amplificación, altavoz, rutas GPIO y respuesta de interrupciones. Cruce obligatorio de datasheet + Ghidra + atlas/fotos de placa; las señales no medidas no son PASS físico.

**AUDIO-HW-02 — P5 / EN COLA, condicionado a AUDIO-HW-01:** implementar con fidelidad las capacidades acreditadas, reutilizando PWM1 ya operativo; verificar FIFOs, REPEAT, temporización, IRQ y salida mono. PWM2 y mezcla únicamente si se constata conexión funcional en el Dana, nunca por su existencia en el chip. Evidencia nativa ROM/MAME, capturas WAV y regresión.

**Estado:** solo tareas futuras, sin ejecutar ni alterar binario o ROM. El registro HW30-07 (PWM1 mono) permanece **ACREDITADO en el alcance antes probado**; el bloque de audio integral no se declara cerrado. Orden: ISP1161 → AUDITORÍA AUDIO → implementación sustentada; no requiere esperar LCD D3.6/D3.7. Excel rector: HITOS AUDIO-HW-01/02, AUD_HW_20261030 HW30-07 y BITACORA.
