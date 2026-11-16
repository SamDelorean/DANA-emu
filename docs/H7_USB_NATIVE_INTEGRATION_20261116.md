# H7 USB Computer — integración digital nativa (2026-11-16)

**Estado:** `DIGITAL_CPU_ISP1161_DUSB_USBIP_PASS / ORIGINAL_UK15_PENDING / OS_ENUMERATION_NOT_ACCREDITED`. Este registro **no** cierra íntegramente H7 ni reabre H1–H6.

## Línea base y restricciones

- Repositorio canónico: `SamDelorean/DANA-emu`, único ejecutable `runtime/diag/bin/dana-diag` en T640. H6 aprobado en `322e021924bc3c5d22e3911d51a153957e12d861`; fuentes de H7 USB/IP publicadas en `d66cbcf3892d797b73238fcbfd7381ba9d349445`.
- SHA-256 del ejecutable **inalterado** durante los ensayos: `73550d0fc28c3189038e39fad2b5a4321dab59da8cfc416317fad18b875f4e41`.
- Sin otro emulador, ramales, recompilación, instalación de binario, modificación de ROM, ni SDIO, radio Wi-Fi, Palm HotSync/DLP, NEO Manager o cambios de cableado supuestos.
- Código anfitrión reutiliza `tests/isp1161_virtual_host.py` y el ISP1161 original (`src/mame/skeleton/isp1161_dana.h`, `isp1161_usb.h`, `isp1161_link.h`); USB/IP transporta peticiones del anfitrión sin fabricar respuestas del controlador. DATA1 es `flags` bit 0 de DUSB; bit 2 significa ISO. Identidades USB deben proceder del firmware invitado.

## Resultados separados por fuente de evidencia

| Canal | Prueba y evidencia | Veredicto |
|---|---|---|
| Pruebas locales de protocolo | 14 casos unitarios; USB/IP DEVLIST/IMPORT/URBs, solicitudes concurrentes, UNLINK, encapsulado DUSB, DATA0/DATA1 y respuestas de un invitado *simulado* | `14/14 PASS` **solo protocolo local** |
| ROM Palm original UK1.5 | El mismo `dana-diag` ejecutó 7000 cuadros con salida 0, 174 transacciones MMIO USB, 9 comandos DC y 4 selecciones B8 observadas; la ruta de interfaz ensayada no activó `DcMode.SoftConnect` y no produjo descriptor EP0 | `BLOCKED_ORIGINAL_DEVICE_NO_DESCRIPTOR` (no fallo del ISP1161 atribuido) |
| CPU invitada M68000 de diagnóstico | Código M68000 real configuró MMIO ISP1161, activó SoftConnect, cargó descriptores y respondió por FIFO EP0; DUSB entregó al adaptador y USB/IP respondió a `DEVLIST`, `IMPORT`, URB `GET_DESCRIPTOR` | **`M68000_USBIP_END_TO_END_PASS`**; MAME RC=0, bridge RC=0, marker `0xA55A` |
| Identidad USB del invitado de prueba | VID/PID `1234:5678`, primeros 8 bytes del descriptor `12010002ff000008` | Identidad **diagnóstica**, no identidad original del Dana |
| Enumeración Linux/Windows/macOS | USB/IP usuario local probado, pero sin importar por un controlador USB virtual del sistema operativo | `NOT_ACCREDITED` |
| VBUS/INT2/PG3/diferencial físico de placa | Sin nuevas mediciones físicas | `NO_VERIFICADO` |

**Nota importante:** el PASS nativo M68000 acredita el recorrido digital **CPU → ISP1161 → DUSB → USB/IP en modo usuario**. No acredita que Palm UK1.5 original configure USB Computer ni que el equipo anfitrión vea un periférico en `lsusb`.

## Ingeniería inversa UK1.5 / Ghidra

- La investigación existente documenta el acceso DC `0x1F000006` (comandos) / `0x1F000004` (datos), `C0` en dos palabras e IRQ2 lógico, más puntos de entrada de conexión/SETUP.
- Un primer intento de auditoría contra el proyecto `DanaUK15Reverse` no encontró programas. Un proyecto posterior `DanaUK15RelocatedTemp` sí contenía base de datos, pero Ghidra 11.1.2 no podía abrirla por haber sido creado en versión nueva.
- Se identificó y ejecutó **Ghidra 12.1.3** en modo solo lectura contra el programa existente `Dana1.2.1.rom`. El auditor consultó 19 direcciones históricas, pero `INSTRUCTION_AT_SITE=NOT_DISASSEMBLED` para todas en el espacio del proyecto. **No se afirma desensamblado, decompilación, apertura del driver Palm ni reconstrucción de red física** con esta ejecución.
- Para continuar la ingeniería inversa solo se justifica un análisis de direcciones/segmentos y referencias demostrados o un trace real de la ruta Palm que abra USB Computer; no fabricar llamadas MMIO para que el invitado parezca funcionar.

## Anfitrión / kernel

- En T existe `usbip` CLI y el archivo `/lib/modules/7.0.0-43-generic/kernel/drivers/usb/usbip/vhci-hcd.ko.zst`.
- En los ensayos no había un dispositivo VHCI activo ni ruta gadget operativa. **No se cargaron módulos**, no se cambió la red ni se afirmó una enumeración USB del sistema operativo. Que exista el `.ko.zst` no acredita soporte operativo ni permisos para cargarlo.

## Fuentes canónicas y evidencia de Drive

- Código fuente publicado anterior: [`d66cbcf`](https://github.com/SamDelorean/DANA-emu/commit/d66cbcf3892d797b73238fcbfd7381ba9d349445), ocho archivos H7 de puente, pruebas y Ghidra. Nuevo complemento en este commit: `tests/h7_m68000_descriptor_fixture.py` y `tests/h7_m68000_usbip_native_runner.py`, empleados en la prueba real. La ROM UK1.5 y los volcados privados **no** se publican.
- <https://drive.google.com/file/d/1ZdVMrQCQUDYN1gQP9coo4dmKrx3Q1ybJ/view> — original UK1.5, prueba nativa R2 con bloqueo.
- <https://drive.google.com/file/d/1xJ09xWnfpGPAmkYbjvtRQWOX1Faq4jvo/view> — resumen MMIO nativo UK1.5.
- <https://drive.google.com/file/d/1SWKgDKyoD3CY1oZlVDHln--H3XPiuq7d/view> — **PASS** nativo M68000/USB-IP R3.
- <https://drive.google.com/file/d/1ANoeixHXJaaDwhhssP_jZwMczjJhul-V/view> — resultado detallado R3.
- <https://drive.google.com/file/d/1eunkchTS3o5pb7DDLrKxI0VY2XxQOEPx/view> — Ghidra12 auditoría READONLY.
- <https://drive.google.com/file/d/1Nxp7-rxZh5kxY38PBJX1AXqwCzr0k-e1/view> — 19 direcciones no desensambladas.

## Cierre de la intervención y continuidad

- Cinco llamadas Commander de diez autorizadas hasta concluir la auditoría Ghidra 12.1.3; queda presupuesto, pero ningún uso justifica reabrir H6 ni repetir campañas cerradas.
- Los tres archivos maestros existentes se preservan; actualizar el rector original solo con campos H7 y conservando **14 hojas, 1.020 fórmulas y 8 tablas**; atlas y plan OS3K no cambian porque H7 no acreditó continuidad física ni se ejecutó OS3K.
- **Siguiente requisito técnico no acreditado:** una presentación USB/IP por VHCI/OS con acceso comprobado, y por separado la activación auténtica de USB Computer desde Palm UK1.5. Ambos deben etiquetarse pendientes mientras no existan observaciones positivas.
