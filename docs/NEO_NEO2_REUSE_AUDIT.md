# Auditoría de reutilización AlphaSmart NEO / NEO 2 para DANA-emu

**Revisión inicial: 2026-10-13.** Esta nota distingue emulación ya disponible, firmware real y hardware específico de cada placa. **No modifica código ni ejecuta pruebas.** Fuente canónica de hardware Dana: [DANA-OS3K](https://github.com/SamDelorean/Dana-OS3K).

## Resultado de comprobación

1. **NEO comparte la familia MC68VZ328 DragonBall VZ con Dana.** El desmontaje público de NEO registra `MC68VZ328PV` (o revisión AG) y ~33 MHz: https://hackaday.io/project/25732-hacking-the-alphasmart-neo/log/62397-whats-inside ; https://hackaday.com/2020/11/05/alphasmart-neo-teardown-this-is-the-way-to-write-without-distractions/ . La equivalencia exacta de revisión de silicio entre NEO, NEO 2 y Dana **requiere comprobación por placa/datasheet**, y compartir CPU **no significa compartir periféricos externos ni mapa de placa**.
2. **En MAME oficial y en el fork AS3K revisados no encontramos un driver NEO/NEO 2 completo ni el tipo de dispositivo `MC68VZ328`.** El archivo `src/mame/skeleton/alphasma3k.cpp` es el driver **AlphaSmart 3000 / MC68EZ328** y está marcado no funcional. `src/devices/machine/mc68328.cpp` registra `MC68328` y `MC68EZ328`, no VZ. `hash/alphasmart_kapps.xml` contiene archivos de aplicaciones/SmartApplets para System 3/NEO, **no** un emulador de máquina NEO. Esto describe los árboles **inspeccionados**, no descarta una rama local no sincronizada en la T u otro trabajo WIP externo.
3. **Sí existe un emulador NEO abierto, independiente de MAME:** [ioma8/neo-re, alpha-emu](https://github.com/ioma8/neo-re/tree/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu). README del módulo declara modo **firmware-first**, carga System 3 real, ejecución de instrucciones 68k acotadas, trazas de MMIO, GUI/headless, pulsaciones programadas y capturas LCD. El repositorio raíz conserva un resumen anterior que lo describe como emulador de SmartApplets; **priorizar el README y código actual de `alpha-emu`** y no declarar verificadas localmente las pruebas que el autor describe.
4. **Retro68/POSE contiene emulación específica de la placa Dana**, además del modelo VZ común: `EmRegsVZAlphaSmart`, `EmSPISlaveSTMicro`, ADC y referencias GPIO/USB. El código POSE/Retro68 es GPL; verificar licencia antes de copiar. Más información en [sources.lock.json](../research/sources.lock.json).

## Código NEO que debemos estudiar antes de diseñar VZ en MAME

Repositorio NEO fijado: **`ioma8/neo-re` @ `732814871fe493e80ed1ab1f959d8dad174ee540`** (rama master al inspeccionar).

| Archivo | Extraer | Limitación |
|---|---|---|
| [alpha-emu/README.md](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/README.md) | Arranque firmware-first, pruebas headless, comandos, evidencia de LCD y teclado | Documentación de experimentos del autor, no nuestros PASS |
| [src/firmware.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/firmware.rs) | Análisis de formato System 3, vectores, segmentos y loader | Son formatos de ROM **NEO**; no colocar ROM Palm/Dana en esas direcciones |
| [src/memory.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/memory.rs) | Decodificador MMIO, inicialización, timers, espejos de registros, modelo RAM | Mapa de periféricos externos propio de NEO |
| [src/keyboard.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/keyboard.rs) | Matriz física y eventos NEO | **Dana utiliza un auxiliar ST por SPI2**, no reutilizar cableado de matriz |
| [src/lcd.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/lcd.rs) | Modelo de controlador LCD NEO, puertos y captura | **Dana usa framebuffer LCD VZ 560×160**, no dos controladores NEO externos |
| [src/firmware_session.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/firmware_session.rs) | Encapsulación de estado firmware / motor de pruebas | Adaptación conceptual, no copiar indiscriminadamente |
| [src/gui.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/gui.rs) | Herramientas de visualización y control headless/GUI | Nuestro objetivo es MAME reducido, no portar la GUI Rust |
| [docs/2026-04-20-alpha-emu-memory-map.md](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/docs/2026-04-20-alpha-emu-memory-map.md) | Memoria y efectos MMIO documentados por el autor | No es mapa Dana |
| [docs/2026-04-22-alpha-emu-headless-usage.md](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/docs/2026-04-22-alpha-emu-headless-usage.md) | Contratos de pruebas reproducibles | Reproducir y validar en nuestro entorno posteriormente |

Datos del README NEO: CPU objetivo 33 MHz; puertos LCD izquierdo `0x01008000..02` y derecho `0x01000000..02`; matriz teclado `0xFFFFF419` y selección `0xFFFFF411`; ventana interna `0xFFFFF000..0xFFFFFFFF` con alias bajo; Small ROM en `0x00400000` y datos de ROM System 3. **Las direcciones de controladores LCD NEO NO corresponden al LCD integrado de Dana**, aunque parte de los registros internos DragonBall VZ sean comunes.

**Licencia de ioma8/neo-re:** no se observó fichero `LICENSE` en la raíz al inspeccionar el listado. Tratar el código como **referencia de lectura únicamente** hasta verificar permisos específicos; no asumir que estar publicado en GitHub permite copiar/relicenciar.

## Matriz de reutilización para Dana

| Función | NEO / NEO 2 | Dana | Qué reutilizar |
|---|---|---|---|
| CPU | DragonBall VZ para NEO; confirmar NEO2 exacto | DragonBall VZ | Núcleo 68000 de **MAME** + comportamiento de registro VZ validado en fuentes externas |
| MMIO interno | Chip VZ, reloj, timers, IRQ, GPIO, UART | Chip VZ, periféricos configurados distintamente | Estructura/registros, estados reset y test por dirección/ancho; no copiar valores de placa |
| RAM y Flash | Mapa de NEO con OS3K | RAM de Dana y PalmCard/Flash propia | Algoritmos de mapeo, diagnóstico y loader por separado |
| LCD | Controladores externos por puertos duales en NEO | VZ LCD DMA 560×160 monocromo | Patrón de visualización, registros de CPU comunes; no circuito/driver LCD de NEO |
| Teclado | Matriz conectada a GPIO | ST auxiliar en SPI2 | Interfaz de eventos host y harness; controlador Dana de Retro68/EmuTOS |
| SD | NEO stock sin ranuras integradas de Dana | Dos ranuras; una controlada en EmuTOS | Sólo subsistema SPI1/SD y cableado específico Dana |
| Diagnósticos | Trazas MMIO, LCD snapshots y scripts del `alpha-emu` | DIAG instrumentado MAME | Diseño de pruebas, no cambiar base del emulador |
| ABI/OS | NEO System 3 / OS3K | Palm stock hoy; OS3K-Dana parcheado después | Útil en fase **firmware**, no para forzar comportamiento al hardware virtual |

## Instrucción para D0 antes de escribir código

1. Examinar por separado **los drivers realmente existentes en MAME**: `mc68328.cpp/h`, `mc68328lcd.cpp/h`, `alphasma3k.cpp` y `alphasmart_kapps.xml`. No declarar que este último es un driver NEO.
2. Extraer por lectura estática de `neo-re/alpha-emu` los accesos al **núcleo VZ** y distinguirlos de periféricos externos NEO. Elaborar tabla comparación VZ común/NEO/Dana.
3. Cruzar con **POSE EmRegsVZ** y **Retro68 EmRegsVZAlphaSmart/EmSPISlaveSTMicro**, usando **EmuTOS-Dana** como referencia de secuencias reales.
4. Diseñar el primer dispositivo VZ **dentro de MAME**, y después el perfil de placa Dana. Antes de implementar, verificar cualquier driver WIP de Neo/VZ en la rama MAME que efectivamente se use en T.
5. Documentar fuentes, licencias, mapa y pruebas. No modificar AS2K, DANA-OS3K ni ROM física.

## Estado

**Reutilización documentada; código no importado ni compilado.** No se encontró driver NEO/NEO2 completo dentro de los árboles de MAME auditados. La emulación NEO de `neo-re` constituye referencia adicional externa, no componente MAME ya presente. Los componentes compartidos son arquitectura CPU/registros; las diferencias de periféricos se mantienen explícitas.
