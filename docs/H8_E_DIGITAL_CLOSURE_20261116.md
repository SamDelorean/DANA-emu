# H8-E — Cierre del hardware digital emulado Dana

Fecha: 2026-11-16. **Decisión de alcance:** el usuario todavía no cuenta con una placa Dana. Las mediciones e identificación física se aplazan; en esta etapa se acepta exclusivamente la funcionalidad digital que ya cuenta con evidencia nativa. **Estado H8-E: `CLOSED / PASS_DIGITAL_SCOPE_WITH_EXTERNAL_DEFERRED`.** No equivale a `FULL_HARDWARE_PHYSICAL_PASS`, ni al arranque stock de tres placas.

## Línea base única y prueba de aceptación de H8-E

- Canónico `SamDelorean/DANA-emu`, commit de fuente al comienzo de la auditoría `main@672ddb17b384df4026ce9c789457e2a544e8cca8`; se verificó `HEAD` local y remoto idéntico y árbol limpio.
- Único ejecutable instalado en T: `runtime/diag/bin/dana-diag`, SHA-256 `73550d0fc28c3189038e39fad2b5a4321dab59da8cfc416317fad18b875f4e41` (identidad preservada).
- Trabajo integral `001_dana_h8_e_digital_acceptance_20261116.job.sh`: **`H8_E_DIGITAL_ACCEPTANCE_PASS_PRIOR_NATIVE_EVIDENCE_REUSED`**, exit=0; **1/5** llamadas Commander consumidas en H8-E.
- El SH inspeccionó identidades y JSON nativos ya publicados, sin correr MAME, sin nuevos invitados, sin recompilar, sustituir ejecutable, cargar módulos del kernel ni escribir ROM, hardware, libros o entorno anfitrión. Las pruebas H1–H7 no se repitieron porque no hubo cambios funcionales posteriores.
- Acta del comprobador: [aceptación JSON](https://drive.google.com/file/d/1wTuKLmi1ESrLdE8D4BnE86-Cl7WhncKf/view); [estado y salida](https://drive.google.com/file/d/1FSm4Dwi3Mvo8poVIxCR55gpeUCk-hrX8/view).

## Matriz de aceptación: operaciones acreditadas, no silicio entero

| Subsistema | Evidencia conservada | Dictamen digital / límite |
| --- | --- | --- |
| MC68VZ328 68000, MMIO, reset, PLL/PCM/STOP, reloj, IRQ, Timer, RTC, watchdog y GPIO | [H2](H2_VZ_INTEGRATION_20261101.md), campañas H4/H6 posteriores | `PASS_EN_RUTAS_ACREDITADAS`, no todos los modos del VZ |
| SDRAM 8/16 MiB, CS y NOR 4/8 MiB, comandos, geometría y persistencia | [H3](H3_NOR_INTEGRATION_20261115.md), [H6](H6_INTEGRATION_20261116.md), [H8-B](H8_B_NATIVE_MEDIA_AUDIT_20261116.md) | `PASS_DIGITAL`; H8-B reutilizó 22 recibos de perfil (16 CPU positivos, 6 rechazos previstos); **no** es prueba de tres ROMs comerciales completas |
| LCD 560×160, profundidad 1/2/4 bpp y DMA | [H4](H4_LCD_INTEGRATION_20261115.md) | 51 escenarios instalados previamente PASS; óptica y polarización no certificadas |
| Teclado ST, digitalizador y SPI2 | [Plan incremental](DANA_EMU_INCREMENTAL_WORK_PLAN.md), campañas originales | `PASS` para rutas de teclado, lápiz e IRQ registradas |
| SD/MMC doble ranura, SPI1, lectura/escritura, aislamiento y persistencia | [Plan incremental](DANA_EMU_INCREMENTAL_WORK_PLAN.md), [H8-C/D](H8_C_D_BOARD_NET_GAPS_20261116.md) | `PASS_DIGITAL`; posición izquierda/derecha, switch de inserción y continuidad reales sin medir |
| UART1/UART2, IrDA y USB Host de impresión | [H2](H2_VZ_INTEGRATION_20261101.md), [H4](H4_LCD_INTEGRATION_20261115.md), [plan](DANA_EMU_INCREMENTAL_WORK_PLAN.md) | `PASS` para trayectos ya probados, no transferencia óptica/electrofísica |
| PWM1 audio mono, alimentación lógica PG1/PJ6 y ADC SPI2 A4/E4 | [H5](H5_PWM_POWER_INTEGRATION_20261115.md) | 22 escenarios instalados previamente PASS; analógica/voltajes/batería no medidos |
| Perfiles Dana 2002, revisado 2003 y Wireless 2003; monitor PK0 | [H6](H6_INTEGRATION_20261116.md) | 14 escenarios instalados PASS con 5 pares de pasividad; Wireless **sin radio** |
| ISP1161 Device, CPU→EP0/FIFO→DUSB→USB/IP local | [H7](H7_USB_NATIVE_INTEGRATION_20261116.md) | `M68000_USBIP_END_TO_END_PASS` previamente; enumeración en sistema operativo PC diferida expresamente |

**Distinción obligatoria:** el examen H8-E no añade PASS nativos nuevos. Los contadores 51, 22 y 14 pertenecen a H4/H5/H6, respectivamente; no se suman como una única campaña H8 ni se convierten en pruebas completas de placa.

## Estado por punto H8

| Punto | Estado de cierre autorizado | Commander usado / máximo |
| --- | --- | --- |
| H8-A | `SOURCE_RECONCILED / CLOSED` | 0 |
| H8-B | `DIGITAL_PROFILE_EVIDENCE_REUSED / COMMERCIAL_BOOT_BLOCKED_EXTERNAL_IMAGE` | **3/5** (dos inventarios más sincronización documental; ninguno ejecutó una ROM comercial nueva) |
| H8-C | `SOURCE_MAP_RECONCILED / PENDING_PHYSICAL_DEVICE` | **0/5** |
| H8-D | `NO_CHANGE_REQUIRED_WITHOUT_GUEST_PROVEN_BLOCKER`; no se declara paridad de modos no usados | **0/5** |
| H8-E | `CLOSED / PASS_DIGITAL_SCOPE_WITH_EXTERNAL_DEFERRED` | **1/5** (auditoría read-only) |

## Pendientes **fuera del criterio de cierre digital**

1. No se dispone todavía de un **Dana físico**. En el atlas de placa quedan U7 NOR/topmark, continuidad de pines, mapeo izquierda/derecha y detección de SD, circuitos LCD/altavoz/batería/cargador, J100, rieles de alimentación y corriente: `PENDING_PHYSICAL_DEVICE`, sin atribuirles `FAIL_EMULATOR`.
2. Ninguna de las imágenes privadas disponibles es un **dump completo, autenticado, por sectores de una Flash comercial Dana 4/8 MiB**. UK1.5 `0x5D0000`, imágenes US y paquetes Palm actualizadores siguen siendo fuentes comerciales **parciales**. Arranque comercial íntegro por variante: `BLOCKED_EXTERNAL_IMAGE` / `NOT_ACCREDITED`, no simulable completando bytes desconocidos.
3. **No pertenecen a H8**: SDIO, radio Wi-Fi, comunicación/HotSync/USB enumerado ante PC, autenticidad óptica/analógica ni adaptación OS3K-Dana. Mantener la decisión H7 de posponer la comunicación con PC.
4. Modos secundarios VZ (ICE, PCR combinado, PWM2 u otros): `NOT_REQUIRED_WITHOUT_GUEST_PROVEN_BLOCKER`. No completar registros hipotéticos para forzar un estado total.

## Política de continuación

- Conservamos el único `dana-diag`; no habrá otra versión o `gate`, compilación repetida o campaña H1–H7 si no aparece un defecto concreto reproducible.
- Para una futura placa real: verificar primero identidad/topmark y procedencia de Flash, luego únicamente nets relevantes no medidas; mantener procedimientos pasivos/seguros y evidencia fotográfica.
- Una ROM stock completa y autenticada, o una traza original reproducible que demuestre uso de una ruta VZ faltante, habilitará una prueba de aceptación específica bajo nueva tarea. Esto **no reabre automáticamente** H8 digital ni los hitos cerrados.
- En esta intervención: no tocar libros maestros `DANA_EMU_Control_Rector_Auditoria.xlsx` ni `DANA_Interconexiones_Hardware_Maestro_v04_20261026.xlsx`; preservar 14 hojas/1.020 fórmulas/8 tablas del primero y el historial de ambos. Este cierre se publica en las fuentes/documentos GitHub/Drive; no representa mediciones físicas.

**Cierre:** `H8 DIGITAL HARDWARE SCOPE CLOSED`, `FULL PHYSICAL HARDWARE / COMMERCIAL STOCK BOOT DEFERRED`. Criterio técnico: evidencia digital real y sus limitaciones, sin expansión de alcance ni afirmaciones no verificadas.
