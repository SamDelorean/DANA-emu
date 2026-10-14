# Fuentes técnicas para la construcción del emulador

**Manifiesto local congelado:** [research/sources.lock.json](../research/sources.lock.json). Copiado del manifiesto de DANA-OS3K el 2026-10-13; contiene la revisión SHA exacta y los enlaces inmutables a todos los archivos prioritarios. No es una copia del código de terceros.

| Prioridad | Repositorio y revisión fuente | Qué extraer para DANA-emu |
|---|---|---|
| **Base** | [SamDelorean/mame-as3k, c4e48388](https://github.com/SamDelorean/mame-as3k/tree/c4e48388ca620472643110db2941ce70aa5f3c07) | CPU 68000, DragonBall 68328/EZ, LCD, infraestructuras y debugger MAME. No contiene dispositivo VZ identificado |
| **Placa real** | [davidgiven/emutos, rama dana, 9c42ef0f](https://github.com/davidgiven/emutos/tree/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b) | Registros MMIO, LCD, GPIO, teclado ST, SPI1/2, RAM, UART, IRQ y modelo de loader desde RAM |
| **Emulación específica Dana** | [csnover/Retro68, palmos, d917b67b](https://github.com/csnover/Retro68/tree/d917b67b16bef7bcf5c75a74f617710c32addcbc/PalmUtils/poser) | **EmRegsVZAlphaSmart** y **EmSPISlaveSTMicro**: dispositivo placa AlphaSmart y microcontrolador del teclado; también ADC y USB |
| **Modelo VZ general** | [cloudpilot-emu/pose-original, 97b10711](https://github.com/cloudpilot-emu/pose-original/tree/97b10711fe4ca50c1bd47072378eaab26ba8e81d) | **EmRegsVZ.cpp**, tablas de reset, chip-select, timer, UART, IRQ, SPI, LCD y layout **M68VZ328Hwr.h** |
| **VZ revisado** | [cloudpilot-emu/cloudpilot-emu, 064d5d57](https://github.com/cloudpilot-emu/cloudpilot-emu/tree/064d5d578bcd1f9072de384d05aa217f83db2f7f) | Comparación de tratamiento de MMIO y correcciones a POSE; dispositivos alternativos |
| **Bootstrap** | [davidgiven/dbztool, d3270238](https://github.com/davidgiven/dbztool/tree/d32702383c2ea3523ea58599c52345435c74e900) | Secuencias **danainit.sh** para chip-select, DRAM y carga RAM. Estudiar; **no ejecutar en Dana físico** |
| **UI y automatización** | [clintonthegeek/pose64, 9354edd5](https://github.com/clintonthegeek/pose64/tree/9354edd5b0a2cdadfa0f736e65d080b59500c78f) | Diseño de captura, sesiones, watches y automatización; no usarlo como núcleo alternativo MAME |
| **ABI OS3K** | [SamDelorean/betawise, ad557fcf](https://github.com/SamDelorean/betawise/tree/ad557fcf4efbf07fcf0ff3f398a71a7987b7a41c) | Referencia de firmware invitado, sólo en fase OS3K |

## Evidencias ya documentadas

- [MMIO, GPIO y vectores VZ](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/09-EMULADOR-MAPA-MMIO-Y-GPIO.md).
- [Protocolos y hitos de periféricos](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/10-EMULADOR-PERIFERICOS-Y-HITOS.md).
- [Investigación POSE/Retro68 y licencia](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/12-POSE-DANA-CODIGO-LIBRE-VZ.md).
- [Datasheets EZ vs VZ](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/06-DATASHEET-EZ-VZ-COMPARACION.md).
- [ROM Dana 1.2/1.5 extraída de actualización oficial](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/05-ROM-DANA-ACTUALIZADORES.md).

## Uso de estas fuentes

**Sólo MAME constituye la base del emulador a desarrollar.** Las demás implementaciones sirven para levantar comportamiento y diseñar adaptaciones específicas; no se deben integrar mecánicamente en un código distribuible con licencias incompatibles.

MAME moderno tiene licencias a nivel de archivo, incluido BSD-3-Clause; EmuTOS y POSE/Retro68 tienen GPL-2.0-or-later; Cloudpilot/POSE64 usan GPL-3.0. La publicación posterior requerirá revisar cada archivo realmente usado y las condiciones de redistribución.

**Atención:** la existencia del dispositivo VZ en POSE no equivale a dispositivo MC68VZ328 ya existente en la rama MAME que usaremos. La implementación concreta Dana y sus pruebas continúan pendientes.

El snapshot local sirve para trabajar aun si las ramas upstream cambian; revisar y actualizar la fuente canónica antes de decidir mover un SHA.
