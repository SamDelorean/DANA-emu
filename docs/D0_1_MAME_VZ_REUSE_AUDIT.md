# D0.1 — Auditoría de reutilización MAME / DragonBall / Neo / Dana

**Documento de cierre de investigación estática — 2026-10-13.**

**Estado: SPEC_READY (evidencia documental completada; SIN PASS funcional).** Esta auditoría responde a la única pregunta de D0.1: *qué código de emulación existe, qué podemos reutilizar y qué falta modelar para Dana*. No se implementó, compiló ni ejecutó nada en T; **la ruta/revisión del checkout real de T aún no fue corroborada**, por lo que el primer preflight de implementación deberá compararlo con el SHA aquí fijado. No usar la existencia de fuentes GitHub como prueba de que compilan o arrancan.

## 1. Baseline de fuentes

| Rol | Repositorio | Revisión inmutable examinada | Estado de disponibilidad |
|---|---|---|---|
| **Base prevista de código MAME** | [SamDelorean/mame-as3k](https://github.com/SamDelorean/mame-as3k) | **c4e48388ca620472643110db2941ce70aa5f3c07**, rama master al fijarlo | Accesible en GitHub; árbol/checkout/versión de compilación en T: **NO VERIFICADOS** |
| MAME oficial para contraste | [mamedev/mame](https://github.com/mamedev/mame) | **98e60b54d0718171636f50e39794d861564aac08** | Fuentes accesibles; no es automáticamente el baseline T |
| Referencia de placa Dana | [davidgiven/emutos](https://github.com/davidgiven/emutos) | **9c42ef0f2c2fa9d1e217fced9da68901b2326e8b** (rama dana) | Código del port, **no** firmware guest compilado/verificado localmente |
| Modelado POSE de SoC VZ | [cloudpilot-emu/pose-original](https://github.com/cloudpilot-emu/pose-original) | **97b10711fe4ca50c1bd47072378eaab26ba8e81d** | Código GPL, referencia de comportamiento |
| Emulación POSE **específica Dana** | [csnover/Retro68](https://github.com/csnover/Retro68) | **d917b67b16bef7bcf5c75a74f617710c32addcbc** | Código GPL, referencia de comportamiento de placa y ST |
| Neo firmware-first (no MAME) | [ioma8/neo-re](https://github.com/ioma8/neo-re) | **732814871fe493e80ed1ab1f959d8dad174ee540** | Código Rust disponible para leer; licencia de reutilización no identificada |

Manifest de procedencia: [research/sources.lock.json](../research/sources.lock.json); auditoría de Neo previa: [docs/NEO_NEO2_REUSE_AUDIT.md](NEO_NEO2_REUSE_AUDIT.md).

**No se fijó una versión numérica de MAME por intuición:** el **commit** es nuestra referencia reproducible; la versión/build/árbol de trabajo de la máquina T se comprueban en el primer preflight autorizado y no requieren una exploración Commander separada.

## 2. MAME base: componentes y hechos observados

### A — CPU 68000: REUTILIZABLE

**Archivo:** [src/devices/machine/mc68328.h](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.h), líneas 90–139. La clase **mc68328_base_device** deriva de **m68000_device**, el núcleo CPU MAME; es la infraestructura de instrucciones/estados/interrupt acknowledgement a estudiar.

**Conclusión:** NO escribir otra CPU 68k ni adoptar el intérprete Rust de Neo como motor alterno. Mantener contratos de CPU, excepciones y depurador MAME. La compatibilidad del conjunto de instrucciones 68000 no implica igualdad de reset/IRQ/MMIO.

### B — Driver SoC DragonBall MC68328/MC68EZ328: BASE DE ADAPTACIÓN, NO DROP-IN VZ

**Archivos:**
- [mc68328.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.cpp), líneas 45–46, 97–200, 202–330.
- [mc68328.h](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.h), definición base, callbacks y clases específicas.

**Tipos definidos explícitamente:** **MC68328** y **MC68EZ328**. En el árbol auditado **no** se encontró registro de dispositivo **MC68VZ328**.

Los subsistemas existentes de MAME aportan arquitectura y operaciones comunes:
- Ventana interna MMIO de reloj/PLL/IRQ y GPIO; handlers que diferencian accesos 8 y 16 bits y mapas CPU.
- Timer1, UART, control LCD, RTC y callbacks GPIO/SPI.
- Scheduler, timers y save-state del framework MAME. La implementación de uno u otro registro exige comparación VZ **bit a bit**, no extrapolación.

**Riesgo concreto de reutilización directa:**
- En \`mc68328_base_device::base_internal_map()\` (líneas ~170), los registros **0x800/0x802** se conectan al **SPIM**, mientras que la variante MC68328 mapea un **SPIS** en **0x700** (línea ~309 de mc68328.cpp).
- En [EmuTOS-Dana bios/dana.c](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c), líneas 84–91, **SPI1** usa **0xFFFFF700–0xFFFFF70A**, y **SPI2** usa **0xFFFFF800/0xFFFFF802**. Estas asignaciones no admiten herencia automática del mapa del MC68328/EZ.
- El VZ incorpora recursos adicionales/diferentes de chip-select, control DRAM, GPIO, dos UART, dos SPI y temporizadores. No basta renombrar el tipo de dispositivo.

**Decisión D0.1:** priorizar evaluar factoring/reutilización de handlers MAME **sin cambiar comportamiento MC68328/EZ existente**. D0.2 determinará registros concretos compatibles, divergentes y nuevos; D1 será quien decida el diseño C++ y lo someta a pruebas.

### C — LCD existente: infraestructura reutilizable, NO renderer Dana listo

**Archivos:**
- [mc68328lcd.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/video/mc68328lcd.cpp) (BSD-3-Clause; device MC68328_LCD).
- [mc68328lcd.h](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/video/mc68328lcd.h).

Ofrece **flm_w, llp_w, lsclk_w, ld_w, lcd_info_changed y video_update**; gestiona bitmap, paleta, dimensiones y scanlines a partir de señales emitidas por el SoC. Este patrón de conexión puede adaptarse al VZ **si su DMA/registro LCD produce señales con semántica compatible**. En Dana la pantalla real es **560 × 160, 1 bpp** y el guest configura framebuffer por **LSSA**.

**Lo que D3 debe demostrar:** la salida visible se obtiene leyendo la RAM del guest según las direcciones/registros VZ; no basta pintar una imagen de 560×160 desde el host.

### D — Driver Palm MAME: patrón de integración entre CPU, LCD y entrada

**Archivo:** [src/mame/palm/palm.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/mame/palm/palm.cpp), líneas ~575–690.

Ejemplos útiles: CPU integrada en \`machine_config\`, \`address_map\`, callbacks de GPIO, SPI y pantalla LCD, registros de entrada, \`screen_update\`, estado serializable y periféricos separados. **No** reutilizar GPIO de una placa Palm como cableado Dana; \`palm.cpp\` es ejemplo arquitectónico y no driver Dana.

### E — Driver AlphaSmart 3000: NO ES NEO/NEO2

**Archivo:** [src/mame/skeleton/alphasma3k.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/mame/skeleton/alphasma3k.cpp), líneas 1–9, 97–121.

Es un *skeleton* **AlphaSmart 3000** con **MC68EZ328**, configuración provisional a 16 MHz y **dos controladores KS0066/HD44780**, no el dispositivo MC68VZ328 ni el LCD Dana. Documenta explícitamente que aún falla el proceso IPL. No tomar ese boot como criterio de calificación Dana.

El archivo [hash/alphasmart_kapps.xml](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/hash/alphasmart_kapps.xml) cataloga **SmartApplets System 3/NEO** y no implementa emulación de su hardware.

## 3. Referencias ajenas a MAME: qué proporcionan

### F — POSE original: diseño interno VZ

[EmRegsVZ.cpp](https://github.com/cloudpilot-emu/pose-original/blob/97b10711fe4ca50c1bd47072378eaab26ba8e81d/SrcShared/Hardware/EmRegsVZ.cpp): dispone de **kInitial68VZ328RegisterValues** con reset values explícitos para SCR/chip-select/PLL/IRQ/GPIO, y rutinas de LCD, SPI, UART y temporizador. [M68VZ328Hwr.h](https://github.com/cloudpilot-emu/pose-original/blob/97b10711fe4ca50c1bd47072378eaab26ba8e81d/SrcShared/Palm/Platform/Core/Hardware/IncsPrv/M68VZ328Hwr.h) aporta offsets/bitfields.

**Uso correcto:** contrastar datasheet y pruebas existentes, extraer contratos de lectura/escritura/side effects para D0.2. **No** declarar la temporización de POSE ciclo exacta ni copiar código GPL dentro de MAME BSD por omisión.

### G — Retro68/POSE Dana: lógica de placa y microcontrolador ST

- [EmRegsVZAlphaSmart.cpp](https://github.com/csnover/Retro68/blob/d917b67b16bef7bcf5c75a74f617710c32addcbc/PalmUtils/poser/SrcShared/Hardware/EmRegsVZAlphaSmart.cpp), 346 líneas: deriva de EmRegsVZ; conecta **GetSPISlave**, GPIO E/K, ADC ADS784x y esclavo ST, señal de pantalla/retroiluminación, condiciones IRQ y control SPI.
- [EmSPISlaveSTMicro.cpp](https://github.com/csnover/Retro68/blob/d917b67b16bef7bcf5c75a74f617710c32addcbc/PalmUtils/poser/SrcShared/Hardware/EmSPISlaveSTMicro.cpp), 448 líneas: **DoExchange, NeedsExchange, PortKOutputEnable, ButtonEvent, KeyEvent y ProcessVersionCommand**. Ofrece una máquina de estados para las transacciones, eventos y códigos de teclado.

**Valor:** no reconstruir sin base la interfaz ST. Comparar el protocolo con el guest real [bios/dana.c](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c). **Licencia GPL-2.0-or-later** según cabecera de los archivos: fuente de ingeniería, no copiar literalmente antes de determinar licencia y estrategia de distribución.

### H — EmuTOS-Dana: evidencia de los accesos del *guest*

[bios/dana.c](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c), ~677 líneas; fuente GPL-2.0-or-later. Define direcciones de MMIO VZ 0xFFFFFxxx y 0xFFFFFAxx y secuencias reales LCD, SPI1-SD, SPI2-ST, PLL, timer1, UART1 y GPIO. En el port el guest espera inicialización ST y sondea el teclado.

**Uso correcto:** fixtures derivados de transacciones observables. Evitar reutilizar rutinas TOS en el emulador MAME, ya que ello ocultaría fallas de MMIO.

### I — Neo firmware-first, fuera de MAME

[neo-re / alpha-emu](https://github.com/ioma8/neo-re/tree/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu) modela hardware Neo y ejecuta firmware System 3 con un intérprete Rust \`m68000\`. Aporta referencias de **CPU VZ, estados de ROM, MMIO, reloj, capturas LCD, entrada y pruebas headless**; ver [auditoría Neo/Neo 2](NEO_NEO2_REUSE_AUDIT.md).

**Diferencias fundamentales:** teclado Neo por matriz y LCD Neo con controladores externos; **Dana** usa ST/SPI2 y LCD integrado VZ 560×160. Los offsets Neo de controladores externos no se aplican a Dana. Tampoco se encontró licencia de reutilización declarada en Cargo.toml o en el listado raíz inspeccionados: **sólo lectura** hasta verificarla.

## 4. Matriz de decisiones de reutilización

| Bloque | Infraestructura MAME reutilizable | Extensión propia Dana/VZ necesaria | Prioridad |
|---|---|---|---|
| CPU 68000 | Motor, excepciones y debugger | Mapeos de CPU y estado VZ | D1 |
| Program/address map | \`address_map\`, callbacks, bus lanes | 4 MiB guest RAM y mapa VZ; control CS/DRAM | D1 |
| SoC 68328/EZ | Helpers de MMIO, base de timers/IRQ/LCD/UART/SPI | Nueva semántica de registros y estados VZ; no romper EZ | D0.2 / D1–D4 |
| LCD | \`MC68328_LCD\`, \`screen_device\` y callbacks | LSSA, formato 560×160, DMA y encendido Dana | D3 |
| IRQ/timer | Scheduler y lógica 68328 | Reset, fuentes, prioridad/ack y contador VZ | D2 |
| UART | Interface serial y handlers de base | UART1 VZ observada, flags RX/TX y vectores | D2 |
| SPI | Interfaz SPIM y callbacks de buses | Dos controladores VZ, SPI1 SD y SPI2 ST; CS GPIO Dana | D4 / D7 |
| Teclado | Entrada host MAME / port event plumbing | ST firmware protocol, scancodes físicos, cola y estado | D4 |
| Tarjeta SD | Dispositivos media/block-image MAME a evaluar | Conexión SPI1, GPIO de placa y estado de inserción | D7 |
| UI y DIAG | Depurador MAME, headless y save-state | Perfiles separados y sondas para experimentos Dana | D1 y D6 |
| Palm stock/OS3K | Loader/ROM region y debugger genéricos | Boot físico/flash desconocidos y ROM parcheada | D8.5 / O0 |

**No copiar los archivos del port EmuTOS o Retro68 al árbol MAME**, aunque sus nombres sugieran funcionalidad perfecta. Decidir diseño y compatibilidad/licencias por archivo antes de cualquier integración.

## 5. Exclusiones y obstáculos localizados

- **No existe confirmación de un driver Neo/Neo 2 ni MC68VZ328 dentro del MAME consultado**. Ésta es una constatación sobre las revisiones auditadas, no una afirmación universal sobre cualquier rama WIP u otra máquina.
- **Ruta, revisión y versión de binario MAME de T: NO VERIFICADAS.** Este D0.1 se realizó por GitHub. Se contrastarán con el commit fijado en el **preflight del primer job autorizado de T** (o previamente mediante evidencia de Drive), sin gastar Commander sólo para \`ls\`/\`git status\`.
- **Formato binario de EmuTOS-Dana y su hash/ubicación de fixture: NO VERIFICADOS.** Es objetivo **D0.3**, no inferir su existencia por encontrar el código fuente.
- **Mapeo detallado VZ:** objetivo D0.2; la auditoría D0.1 **no** firma equivalencia de reset values ni timer/IRQ/SPI.
- **Calificación funcional:** ningún test en T; stable/diag siguen sin implementarse.

## 6. Cierre, alcance de estados y continuidad

- **D0.1: SPEC_READY**, auditoría estática entregada y trazable, **sin PASS de emulación**.
- **D0.2: PENDING**, siguiente incremento: **tabla de equivalencia MC68EZ328/MC68VZ328 por registro** con direcciones, ancho, reset, side effects, fuentes y diferencias.
- **El preflight físico de T no se cierra** con este documento. Antes de abrir D1.1, se deberá probar que el árbol candidato coincide con una revisión registrada. La falta de dicho preflight **no obliga a consumir Commander durante D0.1 o D0.2**.
- Ningún archivo de fuente MAME, AS2K, ROM ni DANA-emu de producto fue modificado aquí. El único cambio autorizado por este incremento es documental.

**Conclusión:** construir en MAME reducido sobre CPU 68000 y dispositivos de la familia DragonBall existentes; producir una adaptación VZ de hardware con fuentes de contraste POSE/Retro68/EmuTOS y preservar el modelo AS3000/EZ existente.
