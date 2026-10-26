# DANA-emu — contrato único para emulación funcional del ISP1161A1

**Fecha:** 26/oct/2026. **Proyecto:** `SamDelorean/DANA-emu`, rama **`main`**, único DIAG en T. **Prioridad:** producto **emulador Dana con Palm OS original**, no simuladores, instrumentación ni tareas paralelas.

## Decisión de hardware: UN circuito integrado, no dos

El **Philips ISP1161A1** integra físicamente **Host Controller (HC)**, **Device Controller (DC)**, el **root hub de 2 puertos** dentro del HC, motores SIE (Serial Interface Engine) independientes, transceptores USB, reloj/PLL, procesador hardware de **Philips Transfer Descriptors (PTD)**, temporizador de tramas, 4 KiB de RAM HC (ATL + dos ITL ping-pong), 2462 B RAM DC con endpoints ping-pong, controladores DMA e INT1/INT2. Motorola **MC68VZ328 DragonBall VZ** *no implementa el motor USB*: es la CPU y el árbitro de memoria externa que envía comandos/datos y recibe las señales de IRQ/DREQ. Circuitería externa como interruptores de alimentación, resistencias y detección de sobrecorriente **no sustituye** el protocolo USB ni requiere otro chip USB.

Referencias autoritativas: Philips ISP1161A1 Rev03, §5 Figs. 4–6, §7.4 SIE, §9.2–9.5 Host transfers PTD/FIFO, §10 HC, §11–§13 DC, y Motorola MC68VZ328UM. PDF de Philips **ya en Drive** [Rev03](https://drive.google.com/file/d/1mYRvC1TUSisXnkZm97exyj78fmn3VKw_/view), Motorola [MC68VZ328UM](https://drive.google.com/file/d/1UuxWG0rYc0n7RoLerqYTt9mlBpU45L6Y/view), carpeta `ALPHASMART/Dana/DATASHEETS`.

La placa Dana expone una sola ventana física de 8 bytes `0x1F000000..0007`; cuatro pares de registros: HC DATA `+0`, HC COMMAND `+2`, DC DATA `+4`, DC COMMAND `+6`. La ROM UK1.5 ejecuta el *driver de host*, pero **el tráfico USB real ocurre dentro del ISP1161**, no en el 68k. Las conexiones exactas de INT1/INT2/DREQ/DACK a puertos VZ deben determinarse a partir del PCB o de las rutinas de ROM; nunca inferirse del protocolo HC.

## Reutilización investigada (fuentes, límites, derechos)

- Linux [`isp116x-hcd.c`](https://github.com/torvalds/linux/blob/master/drivers/usb/host/isp116x-hcd.c) y [`isp116x.h`](https://github.com/torvalds/linux/blob/master/drivers/usb/host/isp116x.h): **driver real del chip**, aporta definición PTD, empaquetado, colas ATL, control de root hub, IRQ y FIFO. **No es emulación de hardware.** Su nota de cabecera reconoce que el soporte isócrono no está implementado: no copiarlo como motor completo ni trasplantar código GPL a BSD.
- QEMU [modelo OHCI/USB](https://www.qemu.org/docs/master/system/devices/usb.html): implementa transacciones USB con dispositivos emulados; **no implementa el ISP1161**. La representación OHCI estándar de TD/ED en memoria **difiere** de los PTD de 8 bytes del ISP1161; no conectar QEMU-OHCI directamente a las escrituras `1F000000`. Puede servir de *referencia conceptual*, no de incorporación textual GPL.
- MAME existente en T: `src/devices/machine/pci-usb.cpp` tiene `usb_ohci_device` con `map(){}` y sin motor de paquetes. `src/devices/bus/ti99/peb/tn_usbsm.cpp` utiliza nominalmente ISP1161 pero comenta explícitamente `TODO: Implement USB controller and assorted USB devices`. **No hay chip completo aprovechable dentro del MAME actual.**
- [Bug99](https://nouspikel.com/bug99.htm): un emulador/depurador TI-99 con **DC parcial**; su autor aclara que el **HC no está emulado**. Tampoco es una solución completa del chip.
- **EmuTOS** es firmware/sistema operativo invitado: no contiene un dispositivo ISP1161 físico ni se debe presentar como controlador hardware.

**Decisión:** implementar **un solo dispositivo** `isp1161a1_device` dentro del MAME de DANA-emu, con interfaces de bus HC/DC y servicio de paquetes encapsulados. Mantener compatibilidad de memoria, runtime/CPU y ROM. No crear un segundo emulador, ramas paralelas, ni una sucesión de registros simulados. No se copiará código con licencias incompatibles.

## Una única unidad de ingeniería (definición estricta de terminado)

La entrega es **el controlador USB completo y conectado**, no un conjunto ilimitado de hitos. Cinco componentes internos forman parte del *mismo* dispositivo; se integrarán y probarán juntos:

| Bloque interno del ISP1161A1 | Contrato funcional | Criterio de prueba |
|---|---|---|
| **1. Bus, temporización y registros** | HC/DC command/data, fases LOW/HIGH, comandos y efectos documentados, reset independiente, clock 1-ms, save state, chipID y banco completo de registros. No hay lecturas/desconexiones falsas. | Compatibilidad 33 casos ya probados + 32-bit endian + resets + lectura/escritura de estado |
| **2. Host PTD/SIE** | Parsear los *PTD Philips de 8 bytes*, dirección SETUP/IN/OUT, número y dirección de endpoint, toggle, packet/total/actual bytes y completion codes. Consumir ATL/ITL0/ITL1 con alineación DWORD, manejar ping-pong ITL, programar FIFO, estado buffer Done/Full, microprocessor EOT/ATL/ITL/OPR IRQ y NAK/reintentos/STALL/CRC/timeout. | PTD→paquete→resultado→PTD reescrito con estado, longitud y IRQ correctas. Probar transferencia satisfactoria y negativa |
| **3. Root Hub y transporte USB** | Dos puertos downstream, connection/status/change, power/overcurrent/suspend/reset, SOF, dispositivo virtual explícito, sin conexiones fantasma. Backend de paquetes con USB SETUP/IN/OUT y respuestas ACK/NAK/STALL. | Enumeración de un dispositivo de prueba USB conectado explícitamente; estado desconectado y reconectado, sin corrupción |
| **4. Device SIE y endpoints** | USB upstream independiente con SoftConnect/VBUS, endpoint0 control bidireccional y otros 14 endpoints; configuración, asignación y validación de los 2462 B; buffering simple/doble ping-pong, SETUP/F4, IN/OUT/status, halt, interrupciones y coherencia de dirección. | Secuencia SETUP→DATA→STATUS real por interfaz de paquetes; recepción OUT, transmisión IN, NAK cuando FIFO no válido, stall/un-stall, reset DC sin tocar HC |
| **5. Integración con DragonBall VZ** | INT1/INT2 IRQ, DREQ/DACK, DMA PIO, GPIO/control de alimentación y configuración eléctrica **según señales reales**, no rutas inventadas; acceso 68000 endianness, ancho de palabra y estados de ahorro de energía. | Pruebas de propagación real a VZ y de ROM UK1.5, sin reemplazar CPU, RAM, display ni código del OS |

**Nivel de fidelidad delimitado:** la interfaz requerida es **USB transaccional a nivel de paquetes y resultados hardware observables**. No se exige reproducir las ondas analógicas D+/D- ni cada bit stuffing en tiempo real para ejecutar Palm OS: el SIE físico queda modelado semánticamente a nivel de paquetes, PID/handshake/CRC-error outcome. Se deben evitar respuestas sintéticas de dispositivos conectados si no fueron configurados.

**Una prueba de aceptación integrada**, con seis escenarios dentro de la misma ejecución MAME sobre la única versión de DIAG:
1. Sin dispositivos conectados: no enumera inexistentes, coherencia de puerto/IRQ/SOF.
2. HC↔dispositivo virtual control: RESET/GET_DESCRIPTOR/SET_ADDRESS/SET_CONFIGURATION vía PTD SETUP/IN/OUT y FIFO.
3. HC: bulk e interrupción; NAK, STALL, timeouts, toggle, buffers y EOT/IRQ.
4. ITL isócrono/ping-pong en cada intervalo frame; sin trampas de descriptores.
5. DC upstream: control EP0 SETUP/DATA/STATUS, bulk IN/OUT, FIFO doble, suspend/resume, DC F6 sin afectar HC; DMA y señales comprobadas.
6. ROM original UK1.5: comparación de pantalla, progreso CPU, IRQ y USB *sin* fallas silenciosas; no afirmar escritorio hasta presenciarlo.

**No se vuelve a llamar PASS «chip completo» con solo 33/33 registros.** Esos 33 casos son regresión de la *interfaz de control* ya cerrada.

## Línea de base real disponible (no volver a hacerla)

- `main` fuente `src/mame/skeleton/alphasdana.cpp`, commit `fc01a0c585736033553b8c0112d13f0f569b16f1`, SHA256 `c50baf64a7a33e4cc0eb50240c7788d7480a7db6bd0a2a64704dd7216d7083a9`.
- Candidato ya compilado `source/danadiagd` SHA256 `1c141495c39fa0365a0fa299500912ea22140c811f237e4e376f5deb2f66efa5`, Clang21 PASS.
- `tests/isp1161_hc_dc_bus.lua`: 33/33 pruebas físicas de bus PASS; regresiones PWM1, RTC, CSD/ROP y PCTLR PASS. No son pruebas de USB externo ni isócrono.
- UK1.5 privada SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`, arranque nativo 30 segundos sin bloqueo MMIO, pero splash Palm Powered sin escritorio. Ghidra indica la ROM frecuentemente ejecuta demora por `PLLFSR CLK32` y esta señal **sí oscila**; esto no prueba dependencia USB para el escritorio.
- Binario operativo instalado `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` **intacto**. Única instalación T `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`.

## Restricciones contra campañas

- **Un artefacto final:** dispositivo ISP1161A1 completo, compatible con ROM y compilado/integrado en el único emulador MAME.
- **Una sola definición de terminado**, los escenarios de arriba, no gates incrementales abiertos ni seguimiento por «el próximo MMIO».
- Las datasheets, el driver Linux y Ghidra sirven para completar ese dispositivo **de manera cerrada**, sin introducir cambios a subsistemas ajenos ni emular conexiones ausentes.
- Si evidencia de la PCB no permite ubicar INT/DMA, declarar la línea no validada y verificar por ROM/medición; nunca asignar pines ficticios.
- **No confundir** «motor USB implementado» con «Palm OS inició»: se necesitan pruebas independientes para ambos resultados.

### Estado en la fecha

**Revisión de hardware cerrada: el motor está en el ISP1161A1.** El contrato sigue siendo una sola unidad, sin campañas por registros. **Actualización de integración comprobada:** `src/mame/skeleton/isp1161_ptd.h` y el SOF/ATL/ITL de `alphasdana.cpp` ya ejecutan PTD Philips reales y superan una prueba de bus MAME 68000 (ATL Full→Done, CompletionCode=5 al no haber dispositivo externo); C++ SETUP/IN/NAK/STALL/CRC también PASS. Véase [informe y SHA de ejecución nativa](ISP1161A1_PTD_NATIVE_AND_VZ_BOOTSTRAP_20261026.md). **Continúan sin implementar** la vinculación con un backend USB real/virtual conectado, las transferencias de datos DC ping-pong completas y los canales eléctricos DMA/IRQ externos; el escritorio Palm OS aún no ha arrancado. **Bootstrap nativo VZ: EMUBRK bajo al reset y UART1/UART2, no el ISP1161.** No confundir esta integración parcial del motor con la aceptación total de las cinco capacidades de este contrato.
