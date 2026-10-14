# DANA-emu

**Start of any future session:** read [CANONICAL_CONTINUITY_AND_RULES.md](docs/CANONICAL_CONTINUITY_AND_RULES.md) first. It preserves the authoritative D0.6 cursor, all AS2K/Commander/Drive constraints, the English-only Git policy and the pre-action checklist; do not ask the user to reconstruct these rules. No remote authorization is inherited.

**Emulador propio y reducido del AlphaSmart Dana, basado en MAME.**

Proyecto de ingeniería para reproducir el hardware **AlphaSmart Dana / MC68VZ328 (DragonBall VZ)** y disponer de un banco de pruebas para **DANA-OS3K**. Se adopta la filosofía del emulador AS2K: dos variantes reducidas, un núcleo compartido y evidencia funcional antes de cerrar incrementos.

## Productos definidos

| Variante | Contrato previsto | Estado |
|---|---|---|
| **dana-stable** | Emulador de uso cotidiano: carga de imágenes y ROM según soporte confirmado, pantalla, teclado, interfaz de control, persistencia de estado, lanzamiento e instalación sencillos | **Diseño inicial; no implementado** |
| **dana-diag** | Banco de pruebas instrumentado: trazas CPU/MMIO, IRQ, RAM, GPIO, SPI, UART, LCD, snapshots y ejecuciones reproducibles | **Diseño inicial; no implementado** |

**Una implementación de hardware común, dos perfiles separados.** Nunca mezclar estados, medios de almacenamiento o configuraciones de las variantes. La instrumentación no debe falsear el resultado observado por el firmware invitado (guest).

## Prioridad de ejecución

1. Emular **DragonBall VZ y los periféricos Dana** utilizando la infraestructura MAME.
2. Validar primero con **EmuTOS-Dana** cargado en RAM, por ser una referencia de rutinas LCD, teclado ST/SPI2, reloj y otros periféricos.
3. Construir las funciones de banco que realmente requieren nuestras pruebas, diferenciando stable y diag.
4. Probar en el mismo hardware virtual el **firmware OS3K/NEO parcheado**. La emulación del arranque Palm/Dana desde Flash es un perfil distinto y requiere mapa físico aún no cerrado.

**No** se busca emular Palm OS por sí mismo, implementar Atari TOS ni lograr aceptación del proyecto oficial MAME. La publicación independiente y las contribuciones upstream son opcionales. No sustituir MMIO con hooks que simulen resultados exitosos.

## Publicación y uso del repositorio

Este repositorio documenta una implementación **todavía no construida** y no incluye ROM, firmware comercial ni código de terceros copiado. El proyecto no está afiliado a AlphaSmart, Palm ni MAMEDev. Las implementaciones externas enlazadas conservan sus respectivas licencias y titulares; **un enlace no autoriza copiar su código**.

**[Revisión de procedencia, riesgos y costos de GitHub Actions](docs/PUBLICATION_REVIEW_20261013.md).** Un repositorio público no equivale automáticamente a un proyecto con licencia abierta: la licencia del futuro código propio y las obligaciones al incorporar MAME/EmuTOS/POSE deberán revisarse antes de su redistribución.
## Documentación

- [Arquitectura stable/diag](docs/ARCHITECTURE.md).
- [**Plan maestro incremental (autoritativo)**](docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md): microincrementos, pruebas por periférico, regresiones y criterios PASS/FAIL/BLOCKED.
- [Índice del plan anterior D0–D8](docs/INCREMENTAL_PLAN.md): equivalencias históricas, supersedidas en detalle por el plan maestro.
- [Reglas de trabajo AS2K](docs/WORKFLOW_AS2K.md).
- [Fuentes técnicas y revisiones fijadas](docs/SOURCES.md).
- [**D0.1 — Auditoría de reutilización MAME/VZ**](docs/D0_1_MAME_VZ_REUSE_AUDIT.md): SPEC_READY documental.
- [**D0.2 — EZ/VZ register contract**](docs/D0_2_EZ_VZ_REGISTER_CONTRACT.md): SPEC_READY; VZ MMIO mapping and manufacturer errata.
- [**D0.3 — EmuTOS-Dana guest image/loader**](docs/D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md): SPEC_READY source/build recipe, image binary/hash unavailable. **D0.4 documented.**
- [**D0.4 — RAM/CPU/bus entry contract**](docs/D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md): SPEC_READY documentation.
- [**D0.5 — Deterministic test harness and evidence**](docs/D0_5_DETERMINISTIC_TEST_HARNESS_CONTRACT.md): SPEC_READY documentary; next D0.6.
- [Punto de continuación en otro chat](docs/HANDOFF.md).

## Relación con otros repositorios

- **[DANA-OS3K](https://github.com/SamDelorean/Dana-OS3K)**: documentación de hardware, firmware y adaptación OS3K, y el manifiesto maestro de fuentes.
- **[DANA-emu](https://github.com/SamDelorean/DANA-emu)**: desarrollo exclusivo del emulador.
- **[EmuTOS-Dana](https://github.com/davidgiven/emutos/tree/dana)** y **[POSE-Dana (Retro68)](https://github.com/csnover/Retro68/tree/palmos/PalmUtils/poser)**: referencia de hardware, con licencias que deben respetarse.
- **[MAME-AS3K](https://github.com/SamDelorean/mame-as3k)**: infraestructura MAME/DragonBall EZ existente, **no un emulador Dana funcional**.

## Estado de traslado — 2026-10-13

**Preparación documental.** Todavía no existe un controlador MC68VZ328 de este proyecto dentro de MAME, ni ejecutable Dana, ni prueba EmuTOS dentro del emulador. No se utilizó Commander durante esta preparación. **D0.1 quedó SPEC_READY documental**, con revisión GitHub fijada y mapa de reutilización; el checkout de T todavía no está comprobado. **Current next increment: D0.6 — freeze the first minimal MAME D1.1 candidate.** D0.1–D0.5 are SPEC_READY documentation only; guest binary/hash and actual build remain unverified. No se ha probado ningún emulador Dana. Consultar [plan maestro](docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md) y [HANDOFF](docs/HANDOFF.md).
