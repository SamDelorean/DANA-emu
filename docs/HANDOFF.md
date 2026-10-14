# Continuidad para el nuevo chat / frente DANA-emu

**Fecha de traslado: 2026-10-13.**

## Qué se decidió

El emulador del AlphaSmart Dana es el **primer frente ejecutable** que debe abrirse para el proyecto DANA-OS3K. Este repositorio **SamDelorean/DANA-emu** es su único espacio de desarrollo. El repositorio **SamDelorean/Dana-OS3K** conserva la investigación del hardware y los parches futuros de OS3K.

Meta: **dana-stable** y **dana-diag**, emuladores **reducidos** basados en un mismo motor MAME, siguiendo el método probado para AS2K. Las contribuciones a MAME oficial son opcionales y no condicionan el producto.

## Información disponible y reproducible

- El Neo físico usa **DragonBall VZ**, también presente en Dana; confirmar por hardware la variante exacta de Neo 2. El MAME AS3K inventariado contiene MC68328/MC68EZ328 y el skeleton **AlphaSmart 3000 (EZ)**, **no** un driver completo Neo/Neo2 ni dispositivo MC68VZ328 en esa revisión. La lista `alphasmart_kapps.xml` cataloga SmartApplets Neo/OS3K, pero **no** es un emulador de Neo.
- **ioma8/neo-re/alpha-emu** contiene trabajo abierto (pero licencia de reutilización aún no confirmada) de emulación **firmware-first de NEO**, fuera de MAME: RAM/MMIO VZ, teclado, LCD y timer, con pruebas headless. Consultar [docs/NEO_NEO2_REUSE_AUDIT.md](NEO_NEO2_REUSE_AUDIT.md) antes de escribir el dispositivo de Dana.
- El port EmuTOS-Dana de David Given documenta ejecución con 4 MiB de RAM, LCD 560×160 1bpp, IRQ, timer1, UART1, microcontrolador ST del teclado por SPI2, SD por SPI1 y táctil.
- Hay código GPL específico del **Dana** en **Retro68 rama palmos**: EmRegsVZAlphaSmart.cpp/h y EmSPISlaveSTMicro.cpp/h. Es fuente importante para GPIO, IRQ y protocolo ST, pero debe evitarse su copia directa a MAME sin auditar licencias.
- POSE original tiene EmRegsVZ.cpp y el layout M68VZ328Hwr.h del DragonBall VZ, con diferencias de fidelidad respecto a hardware real.
- El archivo de manifiesto maestro [research/sources.lock.json](https://github.com/SamDelorean/Dana-OS3K/blob/main/research/sources.lock.json) conserva SHA concretos para MAME, EmuTOS, Retro68, POSE, Cloudpilot, POSE64, dbztool y BetaWise.
- [Documentación hardware/MMIO](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/09-EMULADOR-MAPA-MMIO-Y-GPIO.md), [periféricos y pruebas](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/10-EMULADOR-PERIFERICOS-Y-HITOS.md) y [comparación EZ/VZ](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/06-DATASHEET-EZ-VZ-COMPARACION.md).

## Estado exacto

Documentación y estructura inicial listas. **No existe en este repositorio una compilación del emulador Dana, ni un núcleo VZ implementado y validado, ni dos ejecutables stable/diag terminados.** Ninguna prueba del firmware fue ejecutada en T por este frente. No se autorizó consumir Commander para crear esta estructura documental.

## Punto exacto de continuación: D0.1

**PLAN AUTORITATIVO:** [DANA_EMU_INCREMENTAL_WORK_PLAN.md](DANA_EMU_INCREMENTAL_WORK_PLAN.md). La sección D0 subdivide lo que antes era una única preparación general.

**D0.1 = fijar la versión y revisión del MAME reutilizable, confirmar qué existe realmente de Neo/Neo2/VZ en código ya accesible, registrar archivos, licencias y diferencias respecto a Dana.** Esto es revisión estática, no compilación ni prueba T. No declarar PASS hasta completar tabla con procedencia, SHA y rutas verificadas.

### Alcance histórico de D0, ahora dividido en D0.1–D0.6

1. Fijar con evidencia la versión y la revisión del MAME que se reutilizará, y la ruta real del árbol de trabajo en T cuando haga falta; no inventar checkout/rutas.
2. Elaborar diferencia precisa del MAME MC68EZ328, la arquitectura compartida Neo/Dana DragonBall VZ, y la implementación VZ de POSE/Retro68. Examinar también el emulador firmware-first `ioma8/neo-re/alpha-emu` (fuera de MAME) y cualquier controlador Neo/VZ WIP presente en el árbol MAME real de T; distinguir periféricos externos para no duplicarlos ni confundirlos.
3. Definir la primera candidata de driver VZ y loader RAM EmuTOS: archivos exactos a tocar, imagen de prueba identificada, mapa de memoria, punto de entrada, evidencia de PC/SP, interruptores de instrumentación, checks deterministas.
4. Cerrar el alcance de D1 y sólo entonces pedir autorización para preparar/ejecutar en T un job Drive-first. **No desarrollar teclado/UI/SD antes de tener núcleo y timer ejecutando correctamente un guest.**

No iniciar un árbol completo nuevo de MAME, la implementación de OS3K ni el cold boot Palm por inercia. Detenerse ante un bloqueo verificable.

## Frase de continuidad

«Retoma DANA-emu en D0.1. Lee el PLAN MAESTRO docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md, las reglas WORKFLOW_AS2K.md y la auditoría NEO_NEO2_REUSE_AUDIT.md, además de research/sources.lock.json. Completa sólo la auditoría estática D0.1; sin Commander ni compilación salvo autorización explícita».
