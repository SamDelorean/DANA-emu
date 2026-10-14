# Arquitectura prevista — DANA-stable y DANA-diag

**Estado: especificación inicial. Ninguna variante está implementada.**

## Un motor común, dos productos

El proyecto se basa en un **MAME reducido**, que reutiliza el núcleo Motorola 68000, planificador de dispositivos, mapa de direcciones, depurador y controladores ya disponibles cuando resulte apropiado. El dispositivo **MC68VZ328** debe tener una implementación propia que respete registros, temporización, reset y prioridades de interrupción. El MC68EZ328 existente no constituye por sí solo ese dispositivo.

La lógica compartida modelará RAM y chip-select, MMIO VZ, LCD, SPI1/2, UART1, GPIO, Timer1, IRQ y el microcontrolador auxiliar ST del Dana. **Un solo modelo de hardware para ambas variantes**: no introducir parches distintos de hardware para que pasen sus respectivas pruebas.

### Producto stable

Emulador ligero de uso diario: escalado LCD 560 × 160, teclado funcional, carga de imagen seleccionable y mensajes de fallo inteligibles; controles de reinicio, pausa, guardado/restauración de estado y medios externos sólo cuando cada servicio tenga una implementación real. Experiencia de instalación y ejecución sencilla, siguiendo la filosofía del AS2K-stable.

### Producto diag

Mismo motor y comportamiento del guest, con instrumentación **opt-in**: PC/SR/SP, excepciones, vectores IRQ, lecturas/escrituras de MMIO, GPIO, SPI1/2, UART, framebuffer y regiones de memoria. Registros legibles por máquina, trazas activadas por evento o intervalo, snapshots con hash y fallas reproducibles. Idealmente compatibilidad con herramientas nativas del depurador MAME y corridas sin interfaz para automatizar pruebas.

No permitir que el perfil diagnóstico altere el orden de memoria, el estado de un periférico o las entradas del firmware bajo prueba. Estable y diagnóstico deben tener configuración, NVRAM, imágenes SD y snapshots aislados.

## Perfiles de firmware diferenciados

**R — RAM/EmuTOS (primer objetivo):** recrear explícitamente el estado posterior a DanaRun o dbztool de 4 MiB de RAM en 0x00000000–0x003FFFFF y cargar una imagen EmuTOS-Dana. Este **no** equivale al reset eléctrico original. Confirmar formato exacto y punto de entrada de la imagen antes de programar el loader.

**P — Palm/Flash stock (posterior):** reconstruir reset, chip-select, boot ROM y memoria Flash. El firmware extraído de actualizadores US/UK 1.2/1.5 **no ha sido identificado como volcado físico completo**. Su imagen no puede colocarse en una dirección de bus arbitraria y declararse ROM de arranque.

**O — OS3K parcheado (posterior):** ejecutar firmware de NEO adaptado al hardware virtual validado. No crear este binario dentro del repositorio del emulador; pertenece a DANA-OS3K.

## Compatibilidad y reutilización

- Motor y periféricos MAME: [SamDelorean/mame-as3k](https://github.com/SamDelorean/mame-as3k), como referencia; no modificar ni destruir el emulador AS2K existente.
- Modelo VZ genérico: [POSE original, EmRegsVZ](https://github.com/cloudpilot-emu/pose-original) y [CloudpilotEmu](https://github.com/cloudpilot-emu/cloudpilot-emu).
- Modelo específico Dana: [Retro68 / EmRegsVZAlphaSmart](https://github.com/csnover/Retro68/tree/palmos/PalmUtils/poser/SrcShared/Hardware) y EmSPISlaveSTMicro.
- Hardware observado: [EmuTOS-Dana](https://github.com/davidgiven/emutos/tree/dana), inicialización, GPIO, ST, SD y LCD.
- Bootstrap RAM: [dbztool](https://github.com/davidgiven/dbztool).
- Fuentes cerradas por commit: [SOURCES](SOURCES.md).

**Restricción de licencias:** POSE/Retro68 y EmuTOS incorporan GPLv2+; CloudpilotEmu/POSE64 usan GPLv3. No copiar sus archivos directamente a un dispositivo MAME de licencia distinta sin evaluación de compatibilidad. La documentación y los contratos observables son referencias para la futura implementación.

## Orden de subsistemas

Motor CPU/memoria/loader → PLL/timer/IRQ/UART → framebuffer LCD → ST/SPI2/teclado → arranque interactivo EmuTOS → SD SPI1 → táctil → RAM extra/Flash real/energía/USB/IR según necesidades OS3K.

## Criterio de producto

El valor está en reproducir pruebas con el firmware invitado real, no en cubrir todas las funciones del Palm original ni obtener aprobación de MAME upstream. Cada funcionalidad se admite por necesidad verificada; no implementar prestaciones de presentación que oculten una falta de fidelidad interna.
