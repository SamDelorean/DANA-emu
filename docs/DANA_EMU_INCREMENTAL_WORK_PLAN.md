# DANA-emu — plan maestro incremental y de calificación

**Mandatory session guard:** read [CANONICAL_CONTINUITY_AND_RULES.md](CANONICAL_CONTINUITY_AND_RULES.md) before any action. It preserves the universal AS2K rules, execution authorization limits, source checkpoints, and exact next cursor. This plan alone does not authorize remote execution.

**Plan autoritativo del emulador reducido.** Elaborado el 2026-10-13. Sustituye la granularidad del esquema D0–D8 previo sin invalidar la arquitectura, fuentes ni reglas AS2K. **Development status: no functional increments have passed. Current next task: D0.5 (deterministic test harness and trace contract); D0.1–D0.4 are SPEC_READY documentation only.** No remote execution is authorized by this plan.

## 1. Objetivo y productos

Construir **DANA-stable** (uso cotidiano) y **DANA-diag** (instrumentación, ejecución automatizada, reproducciones y evidencias), **a partir de un motor MAME reducido común**, con hardware MC68VZ328/Dana realista. En primer lugar se ejecutará el port EmuTOS-Dana como invitado de referencia y **después** se probará el firmware OS3K parcheado desde DANA-OS3K. El interés principal es un banco de ingeniería propio; una contribución a MAME oficial es completamente opcional.

- **Stable:** interfaz y ejecución simples, LCD 560×160, teclado, selector de imagen, pausa/reset, conservar/restaurar estado, instalación y manejo de errores. Sólo anunciar servicios ya probados.
- **Diag:** mismo modelo de hardware, con trazas de CPU, MMIO, IRQ, timer, SPI, UART y framebuffer; probes activables, ejecuciones headless, checkpoints y artefactos reproducibles.
- **Separación:** binarios/configuraciones, logs, estados, medios y pruebas de cada variante aislados; ninguna corrección de emulación exclusiva de DIAG. La instrumentación no debe alterar el comportamiento del invitado.
- **Base:** reutilizar CPU, dispositivos, depurador y scheduler MAME existentes; no comenzar un nuevo motor 68k. Revisar antes el driver MC68328/EZ, los trabajos Neo/Neo2 y el modelo Dana POSE/Retro68. No copiar código GPL hacia componentes MAME sin revisión de licencia y condiciones de distribución.

## 2. Reglas de operación y cierre (obligatorias)

1. **Trabajo estrictamente lineal.** Una pregunta técnica y un cambio pequeño por incremento. Para **D0.x exclusivamente documentales**, el cierre **SPEC_READY** requiere inventario completo y fuentes verificadas; permite pasar al siguiente D0.x **sin fingir PASS funcional**. A partir de D1, no comenzar N+1 hasta cerrar N como **PASS** con prueba real en T, o **BLOCKED** con impedimento localizado y desvío mínimo documentado. Nunca llamar PASS a una hipótesis.
2. **STATIC_FIRST:** revisar versiones y commits ya fijados en research/sources.lock.json y en DANA-OS3K; preferir código reutilizable. No recomenzar análisis que ya terminó satisfactoriamente.
3. **Contrato de cambio previo:** antes de implementar cada incremento, registrar objetivo, prerequisitos, archivos permitidos, efectos esperados, fixture/imagen exacta, comando de prueba, señales observables, criterios PASS/FAIL/BLOCKED y reversión. No ampliar el contrato dentro de la ejecución.
4. **Diagnóstico antes de depurar:** incorporar observabilidad mínima en el motor desde D1. Registrar PC, vector, operación MMIO y causa del fallo. Evitar hacks de host que sustituyan acciones reales del invitado.
5. **Prueba determinista y regresión:** guardar fuente/commit, hashes de imagen y ejecutable, argumentos, entradas, salida, transiciones de estado y un reporte machine-readable. Ejecutar al menos el smoke test de los incrementos ya cerrados que pueda verse afectado. Compilar con **-j3 en T** cuando proceda.
6. **PASS exige evidencia real en T:** compilar no demuestra funcionalidad. Una imagen dibujada por el host no demuestra LCD funcional. Un mensaje de log no demuestra ejecución de una interrupción si el guest no la observó. El verificador debe distinguir fallos de infraestructura, harness y producto.
7. **Commander/Drive:** preparar un único job SH autocontenido, prevalidado, en inbox de Drive; comprobar que no existan dos jobs. Ejecutar mediante el lanzador canónico de T sólo con autorización explícita y presupuesto de llamadas para el incremento. Resultados por Drive; no consumir Commander en sondeos, lecturas de logs, búsquedas de rutas o reparaciones exploratorias. El presupuesto de conversaciones anteriores no se hereda.
8. **Trabajo aislado:** no modificar emuladores/ROM AS2K, ni repositorios ajenos, ni firmware físico Dana. No borrar, limpiar ni resetear árboles de otras tareas. En GitHub registrar fuente, documentación y PR/commit sólo de incrementos calificados.
9. **Estados únicos por incremento:** PENDING, SPEC_READY (especificación revisada, no ejecutada), READY (ejecución expresamente autorizada), PASS, FAIL, BLOCKED. FAIL/BLOCKED deben identificar la causa y la pregunta técnica que debe resolverse; no inflar otros hitos.
10. **Sin plazos ni porcentajes especulativos:** el progreso se mide por cierres reproducibles, no por líneas de código o tiempo de CPU.

### Paquete mínimo de evidencia por incremento ejecutado

- **manifest.json:** ID del incremento, versiones/commit, hashes y parámetros del banco.
- **result.json:** status PASS/FAIL/BLOCKED, verificaciones, resultados esperados/observados y causa.
- **console.log + guest-trace.log** (el segundo acotado y opcional cuando no aplica).
- **Artefacto objetivo:** prueba unitaria o fixture reproducible, captura real del framebuffer, traza de SPI, evidencia de vector IRQ, etc., según el incremento.
- **Resumen de regresión:** anteriores que se probaron, los que no aplican y justificación.
- **Checkpoint y reversión:** identificar el commit base y confirmar que stable/diag preexistentes siguen operativos.

Un test harness que falle por una ruta o archivo inexistente no es falla funcional del hardware. Registrar **BLOCKED_INFRA** en la causa, manteniendo el estado general BLOCKED.

## 3. Primera línea base técnica (no asumir que ya existe software Dana)

MAME inventariado contiene CPU 68000 y dispositivos MC68328/MC68EZ328; **no** se confirmó dispositivo MC68VZ328 ni driver Neo/Neo2 integrado en las revisiones consultadas. El proyecto [ioma8/neo-re/alpha-emu](https://github.com/ioma8/neo-re/tree/master/alpha-emu) sí estudia firmware Neo y VZ fuera de MAME. El port [EmuTOS-Dana](https://github.com/davidgiven/emutos/tree/dana) usa 4 MiB de RAM operativa, LCD 560×160, timer1, UART1, SPI1/SD y SPI2/ST teclado. [Retro68 POSE Dana](https://github.com/csnover/Retro68/tree/palmos/PalmUtils/poser) ya dispone de dispositivos VZ y ST específicos; es fuente GPL de comportamiento, **no** una importación permitida sin examen de licencias.

**Pendientes de D0:** confirmar la rama y checkout concreto de MAME para Dana en T; localizar/producir la imagen de invitado EmuTOS-Dana, su SHA y formato (no inventar que existe en Drive); contrato exacto del bootstrap RAM y estado de CPU; mapa MMIO/bus de la revisión VZ elegida. No crear otra copia indiscriminada de MAME.

## 4. Incrementos atómicos

**Status note:** D0.1–D0.3 have SPEC_READY documentary records. All D0.4 onward remain PENDING unless explicitly marked otherwise. No document-only closure is a functional PASS.

### D0 — Referencias, modelo inicial y banco reproducible (sólo estático)

| ID | Único objetivo | Cierre documental |
|---|---|---|
| **D0.1** | Fijar versión/revisión del MAME de referencia y confirmar qué recursos Neo/VZ y EZ son reutilizables | **SPEC_READY**: [auditoría fechada](D0_1_MAME_VZ_REUSE_AUDIT.md). SHA de GitHub fijado; instalación T no verificada hasta preflight posterior |
| **D0.2** | Completar tabla EZ frente a VZ por bloque | **SPEC_READY documental**: [contrato de registros y correcciones Motorola](D0_2_EZ_VZ_REGISTER_CONTRACT.md); bitfields finos aún se validarán por subsistema |
| **D0.3** | Fix the EmuTOS-Dana reference guest artifact | **SPEC_READY:** [source/build and RAM bootstrap contract](D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md). Source commit, make target, raw binary stages and 0x2140 relocation recorded. **No built image/hash exists yet**; actual binary validation belongs to a future authorized build |
| **D0.4** | Specify virtual RAM bootstrap CPU/bus state | **SPEC_READY documentary:** [contract](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md); includes 4 MiB RAM, vectors, SSP/PC/SR policy, memory-init ordering and first MMIO; no runtime validation |
| **D0.5** | Definir harness reproducible y trazas mínimas | Formatos, fixtures, marcadores independientes, límite de traza, reporte máquina y verificador host/guest |
| **D0.6** | Congelar candidata D1.1 | Archivos y dispositivos MAME concretos, límites, reversión y primer test; ninguna compilación implícita |

**Entrega D0:** contrato ejecutable para el primer incremento MAME, no un emulador funcional. D0.1–D0.6 no consumen Commander mientras sólo se puedan resolver mediante fuentes/Drive.

### D1 — CPU, memoria, MMIO básico y arranque mínimo

| ID | Único cambio de producto | Prueba de cierre en T |
|---|---|---|
| **D1.1** | Introducir driver Dana mínimo y configuración reducida de build, sin periféricos simulados | Compila candidato aislado; el driver es seleccionable; smoke de otros drivers preservado |
| **D1.2** | Mapear 4 MiB RAM/lecturas y escrituras 68k; sin MMIO nuevo | Fixture guest lee/escribe 8/16/32 bits, BE correcto, alineación y límites sin corrupción |
| **D1.3** | Implementar decodificación de ventana de registros VZ (MMIO) con valores reset básicos | Traza direccionada demuestra offsets y anchos 8/16/32, efectos de byte lanes, acceso inválido identificable |
| **D1.4** | Añadir cargador del payload EmuTOS-Dana **RAM-only** | Verifica tamaño/hash, colocación, SSP/PC y entrega del control, sin reivindicar cold boot físico |
| **D1.5** | Ejecutar guest hasta el primer bloque VZ todavía no implementado | Captura de PC/SR/SP, instrucciones, causa exacta del bloqueo y acceso MMIO siguiente; sin declarar boot completo |

No iniciar LCD, teclado o tarjeta SD dentro de D1.

### D2 — Reloj, interrupciones, temporizador y consola serie

| ID | Único cambio de producto | Prueba de cierre en T |
|---|---|---|
| **D2.1** | Implementar reloj/PLL y fase dinámica del bit consultado por EmuTOS | El bucle de espera del guest avanza por eventos de reloj virtual, sin valores forzados por el host |
| **D2.2** | Implementar máscara/pendientes/vectorización de IRQ VZ | Fixture activa/enmascara fuente, recibe vector correcto, comprueba prioridad y reconocimiento |
| **D2.3** | Implementar Timer1 (prescaler/compare/status/ack) | Guest obtiene ticks medidos contra tiempo virtual y los detiene/reanuda mediante máscaras |
| **D2.4** | Implementar UART1 TX y condiciones de ready | Bytes enviados por el guest aparecen en consola con orden y ready coherentes |
| **D2.5** | Completar UART1 RX e IRQ si el guest lo necesita | Inyección RX controlada, lectura guest e interrupción/ack; no bloquearse en FIFO |
| **D2.6** | Repetir recorrido EmuTOS hasta siguiente periférico no implementado | Traza prueba que ya superó los estados antes bloqueados sin parches al invitado |

Los registros y efectos se cotejarán con las implementaciones VZ de POSE y manual; **no** copiar temporizadores sintéticos basados sólo en la cantidad de lecturas si distorsionan el comportamiento del invitado.

### D3 — LCD real del Dana

| ID | Único cambio de producto | Prueba de cierre en T |
|---|---|---|
| **D3.1** | Registros LCD integrados VZ y sus cambios de estado | Escrituras guest a LSSA, dimensiones, stride y enable registradas fielmente |
| **D3.2** | Leer framebuffer desde RAM física apuntada por LSSA | Patrón determinista 560×160, 1 bpp, **11,200 B** mínimos, sin imagen host ficticia |
| **D3.3** | Resolver bit order, líneas, polaridad y refresco | Captura checksum/imagen coincide con patrón conocido y muestra cambios después de escritura guest |
| **D3.4** | Encendido/apagado LCD y contraste básico | A partir del estado GPIO/registro, una captura cambia correctamente sin alterar memoria guest |
| **D3.5** | Primera pantalla producida por EmuTOS | Captura de framebuffer real en la secuencia guest con PC y comandos precedentes demostrables |

No añadir UI final ni teclado dentro de D3.

### D4 — Controlador auxiliar ST, SPI2 y teclado Dana

| ID | Único cambio de producto | Prueba de cierre en T |
|---|---|---|
| **D4.1** | GPIO ST: reset, ready, CS y estado en reposo | Verifica transiciones de PB6, PK2, PE3 y selección sin intercambios falsos |
| **D4.2** | Motor de transacción SPI2 y flags de fin | Fixture guest escribe/lee SPIDATA2/SPICONT2 con chip-select y orden de bytes correctos |
| **D4.3** | Inicialización del ST y respuesta de handshake | El guest recibe **0xAA** mediante protocolo real y no por salto de código |
| **D4.4** | Paquetes de códigos físicos de tecla/pulsación/liberación | F1–F8 y letras; eventos ordenados y estado de tecla coherente |
| **D4.5** | Conectar eventos teclado del host con ST virtual | Pulsar y soltar genera efectos en el guest y no sólo en la ventana host |
| **D4.6** | Casos límite ST: sin teclas, varias teclas, reset | Sin inventar funciones ST desconocidas; cola acotada, estabilidad y fallos trazables |

La matriz de NEO no se reutiliza como si fuera ST. La referencia prioritaria es Retro68/EmSPISlaveSTMicro contrastada con EmuTOS-Dana.

### D5 — Calificación del primer emulador funcional

| ID | Pregunta de prueba | Evidencia de cierre en T |
|---|---|---|
| **D5.1** | ¿Arranca EmuTOS sin emulación de llamadas TOS por el host? | Repetición determinista de guest hasta interfaz real en LCD |
| **D5.2** | ¿Funciona interacción de teclado de punta a punta? | Secuencia de entrada y reacción visible desde el sistema invitado |
| **D5.3** | ¿Reset/relanzamiento reproducen estado limpio? | Dos corridas desde snapshot/configuración base con resultados comparables |
| **D5.4** | ¿Son correctas RAM/IRQ bajo carga básica? | Sesión prolongada de pulsaciones, redibujado y ticks sin corrupciones ni loops |
| **D5.5** | ¿El diagnóstico opt-in preserva la ejecución del guest? | Capturas/estado comparables con instrumentación encendida/apagada; la separación final de productos ocurre en D6.1 |

**D5 es el primer hito donde puede afirmarse «emulador Dana funcional»**, con alcance claro: **modo RAM/EmuTOS + LCD + teclado**. No es garantía de boot Palm, USB, SD, suspensión ni OS3K.

### D6 — Productos stable y diag de calidad diaria

D5 valida primero la paridad al encender/desactivar sondas dentro de una base común; **D6.1 formaliza por primera vez los dos productos separados**. No confundir ambos criterios.

| ID | Único incremento | Prueba de cierre en T |
|---|---|---|
| **D6.1** | Separar lanzadores, configuración y datos stable/diag | Build reducido de ambas variantes; rutas/cachés/estados independientes |
| **D6.2** | Activar trazas DIAG selectivas y bounded logs | Trace CPU/MMIO/IRQ/SPI reproducible sin inundar disco; paridad con stable |
| **D6.3** | Automatizar smoke y regresiones headless | Script reproduce casos D1–D5 y emite resultado estructurado de cada caso |
| **D6.4** | Guardar/restaurar estado completo | Checkpoint de CPU, RAM y periféricos; continuación determinista tras restore |
| **D6.5** | Robustecer loader y reporte de errores | Imágenes faltantes/corruptas, RAM inválida, truncamientos y reinicios: fallan de forma controlada |
| **D6.6** | Interfaz ligera estable e instalación | Selector, reset, borrado/guardado, escala y arranque desde entorno del usuario; smoke de instalación limpia |

**La variante DIAG no puede exigir un segundo motor 68k ni parches a EmuTOS.** El modo headless puede funcionar antes del GUI; no retrasar pruebas por presentación.

### D7 — Almacenamiento SD0 (posterior al emulador base)

| ID | Único cambio | Prueba de cierre |
|---|---|---|
| **D7.1** | GPIO de alimentación, inserción y CS de SD0 | Transiciones guest reconocidas, ausencia de tarjeta detectable |
| **D7.2** | SPI1 y negociación SD a velocidad inicial | Secuencia de comandos/respuestas desde guest, sin interceptar GEMDOS |
| **D7.3** | Lectura de sectores de imagen SD | Lectura de sector y checksum reproducible, imagen de prueba aislada |
| **D7.4** | Integración guest con filesystem | EmuTOS monta y lee un fichero conocido desde SD virtual |
| **D7.5** | Escritura opcional protegida y recuperación | Prueba sobre imagen desechable/copias, sin daño a medios reales, manejo de fallos |

### D8 — Extensiones separables según necesidad real

| ID | Alcance | Condición para activarlo |
|---|---|---|
| **D8.1** | ADC/táctil por SPI2 | Requisito de interfaz guest y contrato de controlador |
| **D8.2** | RTC, gestión de energía y suspensión virtual | Mapas validados y criterios de consistencia RAM/reloj |
| **D8.3** | Segunda SD, USB, IR y otros periféricos | Evidencia de hardware y necesidad del firmware |
| **D8.4** | RAM ampliada y configuración completa de chip selects | Modelo físico documentado; no asumir 8/16 MiB por rumor |
| **D8.5** | Arranque real Palm/Flash y diagnóstico de actualización | Regiones físicas, reset, bootloader y coberturas de ROM probados |

Los D8.x son **opcionales e independientes**, no condición para dar por usable DANA-stable.

### O0 — Soporte para el firmware DANA-OS3K

Sólo cuando haya un binario OS3K adaptado con procedencia y mapa definidos: crear una **suite de compatibilidad de hardware** sobre el emulador ya calificado. El código y la arquitectura del firmware OS3K se desarrollan en DANA-OS3K, **no aquí**. Si falla una prueba, aislar qué contrato del hardware es incorrecto antes de modificar el motor.

## 5. Política de regresión y paridad

- **Cada D1–D4:** fixture sintético pequeño **más guest EmuTOS si corresponde**. Ejecutar lo ya cerrado y afectado, con manifiesto de cobertura.
- **Cada D5–D6:** inicio EmuTOS, teclado, LCD y timer; prueba mínima en **stable y DIAG**, con hashes de captura y state serialization cuando aplique.
- **D7/D8:** suite básica D5 sigue obligatoria; media y periféricos extra aislados.
- **Cualquier cambio de CPU/IRQ/memoria:** ejecutar *toda* la suite cerrada dependiente de esos servicios, no sólo la última prueba.
- **No falsos positivos:** compilar, iniciar GUI, crear archivo de salida o terminar sin excepción sólo califican su propio control; no demuestran comportamiento del periférico guest.

## 6. Registro de avance y control de desvíos

| Bloque | Estado al elaborar plan | Primera actividad autorizable |
|---|---|---|
| **D0.1** | **SPEC_READY (cierre documental)** | [Auditoría de reutilización MAME/VZ](D0_1_MAME_VZ_REUSE_AUDIT.md); commit de baseline GitHub fijado, checkout de T pendiente del primer preflight |
| **D0.2** | **SPEC_READY (cierre documental)** | [Tabla EZ/VZ y correcciones de addendum](D0_2_EZ_VZ_REGISTER_CONTRACT.md), sin PASS de emulación |
| **D0.3** | **SPEC_READY (documentation only)** | [EmuTOS-Dana source/build and RAM handoff audit](D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md); no binary SHA or test |
| **D0.4** | **SPEC_READY (documentation only)** | [Post-bootstrap RAM/CPU/bus entry contract](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md), no MAME functional PASS |
| **D0.5–D0.6** | **PENDING** | Deterministic harness/trace specification, then frozen D1 candidate |
| D1.1–D1.5 | **PENDING** | Sólo después de D0 |
| D2.1–D2.6 | **PENDING** | Sólo después de D1 |
| D3.1–D3.5 | **PENDING** | Sólo después de D2 |
| D4.1–D4.6 | **PENDING** | Sólo después de D3 |
| D5.1–D5.5 | **PENDING** | Sólo después de D4 |
| D6.1–D6.6 | **PENDING** | Sólo después de D5 |
| D7.1–D7.5 | **PENDING** | Sólo después de D6 |
| D8.1–D8.5 y O0 | **PENDING / condicional** | Según necesidad explícita |

**No saltar un bloqueo usando un stub que devuelva éxito artificialmente.** Ante evidencia insuficiente registrar exactamente el registro, evento, archivo o señal que falta, estudiar fuentes/repositorios y retomar ese mismo incremento. Cambios de orden requieren modificar este plan de forma explícita, motivada y trazable.

**Exact continuation cursor: D0.5 — design the deterministic test harness, bounded trace and independent PASS/FAIL/BLOCKED evidence contract.** D0.1–D0.4 are **SPEC_READY documentation only**, not functional PASS. Do not build, use Commander, or execute a guest without a new explicit authorization.

## 7. Referencias de control

- [Fuentes congeladas](../research/sources.lock.json).
- [Auditoría NEO/NEO2](NEO_NEO2_REUSE_AUDIT.md).
- [Arquitectura stable/diag](ARCHITECTURE.md).
- [Reglas AS2K](WORKFLOW_AS2K.md).
- [DANA-OS3K/MMIO](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/09-EMULADOR-MAPA-MMIO-Y-GPIO.md).
- [DANA-OS3K/protocolo de periféricos](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/10-EMULADOR-PERIFERICOS-Y-HITOS.md).
