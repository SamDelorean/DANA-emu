# H8 — Cierre de fidelidad del hardware Dana (16-nov-2026)

**Estado: H8-A `SOURCE_RECONCILED` / H8-B–E `PENDING_EVIDENCE`.** Este plan desarrolla la instrucción de cerrar el hardware esencial ya identificado, sin volver a abrir H1–H7. No se afirma un nuevo PASS nativo, se evita iniciar OS3K y no se autoriza automáticamente Commander. El único emulador sigue siendo `runtime/diag/bin/dana-diag`.

## Identidades y línea base

- Repositorio canónico: `SamDelorean/DANA-emu`, `main@dcbb7df94c1c849b88e6c6d32d17eb596fccbfc8` (H7 cerrado al hardware digital).
- Driver inspeccionado: `src/mame/skeleton/alphasdana.cpp`, blob Git `6ac01b936a9e2dff9c473fbe213c0c50a8d23ffe`, 3530 líneas. La revisión aquí es documental y no sustituye una compilación.
- Ejecutable instalado de referencia (sin cambio): SHA-256 `73550d0fc28c3189038e39fad2b5a4321dab59da8cfc416317fad18b875f4e41`.
- H2: reloj/PLL/PCM/watchdog/RTC/IRQ/GPIO; H3: NOR 4/8 MiB; H4: LCD 560×160 1/2/4bpp; H5: PWM1/PG1/ADC A4/E4; H6: perfiles y monitor pasivo PK0; H7: CPU M68000→ISP1161→DUSB→USB/IP en modo usuario. Doble SD, teclado, táctil y UART/IrDA tienen campañas nativas previas.
- Rector de Drive original: `DANA_EMU_Control_Rector_Auditoria.xlsx`, ID `1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l`; el atlas original `1xiNMO0Oz4Ng6qk2--O6WoNtQ77z9ox0Y`. Conservar sus fórmulas, historial, tablas y nombres.

## Conciliación H8-A: lo que **NO** es trabajo nuevo

Los estados de `docs/DANA_HARDWARE_GAP_AUDIT_20261030.md` son el **corte histórico del 30-octubre**, no el estado de noviembre: allí NOR programación, grises 2/4 bpp, UART/IrDA, watchdog, RTC periódico, PLL y PWM REPEAT aparecen parciales o ausentes. Sus campañas H2–H7 posteriores ya los acreditaron digitalmente. Conservar el corte como evidencia histórica; no ejecutar de nuevo sus antiguas prioridades P1–P5 ni cambiar código por ellas.

En `alphasdana.cpp`, las rutas `machine_reset`, `physical_reset`, `firmware_load`, `physical_r`, `physical_w`, `boot_postload` y el selector `DANA_STORAGE` ya existen. `DANA_STORAGE=1` exige RAM 8 MiB/NOR 4 MiB; `=2` y `=3`, RAM 16 MiB/NOR 8 MiB; perfil 3 no emula radio. El driver impide cambios de perfil tras el arranque y valida la identidad de la Flash al restaurar. No reconstruir estos mecanismos.

La ROM privada UK1.5 disponible es un flujo de actualizador de `0x5D0000` bytes (6.094.848 B), SHA-256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. Ha ejecutado Palm/AlphaWord en CPU real del emulador, pero **no constituye una imagen completa autenticada** de NOR de 4 MiB ni de 8 MiB. No rellenar, truncar o etiquetar ese flujo como dump físico íntegro. Las pruebas digitales del perfil de 4 MiB con ROM diagnóstica tampoco acreditan el arranque comercial de Dana 2002.

## Trabajo restante, sin proliferación de hitos

| Paquete | Ejecución y límites | Aceptación exacta |
| --- | --- | --- |
| **H8-A. Auditoría de código/evidencia** | Reconciliar H1–H7, controladores vigentes, fuentes de arranque y PCB; registrar ausencias reales. **SOURCE_RECONCILED** con este plan y matriz JSON; no ejecución nativa. | Ningún pendiente reabierto, sin radio/SDIO/PC, lista de pruebas apoyada en rutas actuales del driver. |
| **H8-B. Arranque y memoria por perfil** | Usar el MISMO `dana-diag`, el `-rom`/`-nor` existentes, las imágenes completas legítimamente disponibles, sus hashes y casos de reinicio/restore. **No** compilar otras variantes ni reconstruir ROMs. | Por perfil: geometría SDRAM/NOR correcta, vector SSP/PC leído por CPU, CSA/CSD real, secuencia guest, reset/restore, registro del primer bloqueo. Si falta dump íntegro: `BLOCKED_EXTERNAL_IMAGE`, no FAIL de hardware. Reutilizar evidencia H3/H6/UK1.5 en lugar de repetir campañas. |
| **H8-C. Interconexiones de placa** | Cruce atlas/fotos/manual con trazas originales; medir físicamente **solo** nets aún necesarias: U7 topmark/selección, detección/orientación SD0/SD1, alimentación/sensores, señales periféricas usadas. Sin presuponer continuidad. | Cada pin o señal marcado `OBSERVADO` (documento/foto), `MEDIDO` (continuidad), `INFERIDO` o `NO_VERIFICADO`. Adaptar driver **únicamente** ante una discrepancia demostrada que afecte el objetivo. |
| **H8-D. Funciones VZ secundarias** | Auditar bloqueos CPU reales. ICE, EMUBRK, captura de temporizadores, PWM2 y GPIO alternos se trabajan **solo si** aparece uso demostrado por firmware pertinente. | Caso mínimo CPU-origin que falla → corrección dirigida → prueba nativa PASS sin regresión. Si no se utiliza: `NO_REQUERIDO`, sin proyecto de emulación especulativa. |
| **H8-E. Cierre integral** | Repetir solo regresiones impactadas; un binario/árbol, source + T + GitHub + Drive conciliados, pruebas de arranque y de los periféricos que se hayan tocado. | Matriz final por variante, evidencia hashes/trazas y estado explícito para cualquier falta externa/física; no porcentajes fabricados ni PASS de circuitos no medidos. |

## Primer trabajo técnico iniciado: diagnóstico H8-B preparado, **sin ejecutar T**

1. Revisado el código actual: `machine_reset()` valida perfil, NOR y RAM; `physical_reset()` restaura CSA, CSCTRL2=`0x1000`, CSCTRL3=`0x9c00` y DRAM/Flash sin inyectar SSP/PC; `physical_r()` extrae vectores de la imagen invitada, en lugar de fabricar el arranque. `boot_postload()` protege identidad de imagen y perfil. Estas funciones se consideran **IMPLEMENTADAS / NO REABRIR**.
2. Carencia decisiva para autenticidad Dana 2002: no hay dump completo identificado de 4 MiB. El trabajo de código no puede suplirlo. Queda `BLOCKED_EXTERNAL_IMAGE`, no `HARDWARE_FAIL`.
3. Las configuraciones Dana revisada y Wireless comparten la capacidad digital de RAM/NOR ya probada, pero la ROM UK1.5 de origen no establece por sí sola cuál placa completa representa. No confundir `DANA_STORAGE` con certificación de boot comercial.
4. La ejecución H8-B debe comenzar **solo** con imágenes cuya procedencia, longitud, SHA, reset-vector y correspondencia con el perfil estén acreditados. Registrar también el caso de falta de imagen en lugar de forzar el arranque. Dar prioridad a un único recorrido autenticado antes de introducir cambios en C++.
5. No se requiere modificación del controlador con los datos disponibles. Próximo resultado verificable: una campaña nativa acotada de arranque/restore por perfiles disponibles y un listado de los bloqueos CPU reales, con cupo de T explícito. No crear un nuevo emulador, ROM ficticia, Ghidra duplicado ni pruebas de hardware ya cerradas.

## Fuera de alcance y dependencia distinta

- **Excluidos expresamente:** SDIO, radio Wi-Fi/802.11, transferencia/enumeración USB en el sistema operativo de la PC, HotSync/NEO Manager, funciones analógicas no sustentadas.
- **No confundir con nuevo hardware:** DanaRun, transición Palm→EmuTOS y OS3K-Dana son pruebas de integración de firmware/producto. Pueden utilizarse para exponer fallos de hardware, pero su ausencia no constituye un controlador periférico inexistente.
- **No certificados:** mediciones reales de rieles, consumo, LCD polarización/contraste, amplificador PWM2, circuitos del cargador, continuidad entre pines del PCB, identificación física NOR U7 y módulo inalámbrico.
- **Uso de recursos:** esta intervención es de fuentes/documentación. No modifica ROM ni ejecutable; no llama a Commander sin nuevo cupo expreso. Cuando se apruebe T, usar el SH integrado prevalidado por Drive y la política de `-j3` únicamente si hay cambios justificados que requieran compilar. Detenerse ante un bloqueo medible, no inventar un dispositivo ni dividirlo en falsas tareas.

## Fuentes canónicas inspeccionadas (mismo repositorio)

- `docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md`, matriz de variantes y D8.5/D8.6.
- `docs/DANA_HARDWARE_GAP_AUDIT_20261030.md`, corte histórico, y `docs/DANA_HARDWARE_INTERCONNECTION_ATLAS_20261026.md`.
- `docs/H2_VZ_INTEGRATION_20261101.md`, `docs/H3_NOR_INTEGRATION_20261115.md`, `docs/H4_LCD_INTEGRATION_20261115.md`, `docs/H5_PWM_POWER_INTEGRATION_20261115.md`.
- `docs/H6_INTEGRATION_20261116.md`, `docs/H7_USB_NATIVE_INTEGRATION_20261116.md`.
- `docs/D8_5_PHYSICAL_BOOT_IMPLEMENTATION.md` (histórica; su estado de 2026-10-24 no incorpora todo el trabajo posterior), `src/mame/skeleton/alphasdana.cpp` y `docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md` (contiene cursores históricos, no reanudar automáticamente).

**Ningún cierre H1–H7 se cambia. H8-A es auditoría concluida sobre fuentes; H8-B, C, D y E no tienen nuevo PASS.**
