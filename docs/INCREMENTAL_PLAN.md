# Plan incremental de construcción y pruebas

**Referencia para el próximo frente.** No se han ejecutado los hitos de esta tabla. Estados iniciales: TODOS **PENDIENTE** salvo la documentación de fuentes ya existente en DANA-OS3K. Prohibido convertir documentación en PASS funcional.

| Hito | Incremento limitado | Evidencia mínima para cerrar |
|---|---|---|
| **D0** | Fijar baseline MAME existente, identificar ruta/revisión real sin duplicar árboles y concretar arquitectura común stable/diag | Fuente, commit, configuración y alcance verificables; análisis estático |
| **D1** | CPU M68000, esqueleto MC68VZ328, RAM 4 MiB, carga RAM EmuTOS | Compilación aislada, vector/PC/SP/estado inicial registrados, trazas de primeros accesos; sin completar LCD |
| **D2** | Registros PLL, timer1, IRQ y UART de VZ | Tick/IRQ/ack y bytes UART del guest observables, sin bucles congelados |
| **D3** | LCD 560×160 1bpp y LSSA real | Captura determinista de framebuffer producido por el guest |
| **D4** | SPI2, GPIO y esclavo ST teclado | Handshake 0xAA, F1–F8, flechas, pulsación/liberación desde guest |
| **D5** | Arranque EmuTOS interactivo | LCD real + teclado en EmuTOS, con prueba de reset y ausencia de atajos |
| **D6** | SD0 por SPI1 y medios externos | Lectura de sectores, inicialización SD, listado/lectura FAT del guest, fallas reproducibles |
| **D7** | Estabilización stable/diag: snapshot, estado aislado, controles y corridas automáticas | Comparación de ambos sobre mismas pruebas; bitácoras DIAG sin alterar guest, build reducido e instalación |
| **D8+** | Táctil, Flash/cold boot stock, energía, USB/IR y segunda SD según prioridad | Contratos propios, sin afirmar soporte por mera presencia de hardware |
| **O0** | Integración de pruebas OS3K (sin desarrollar firmware en este repo) | Imagen OS3K verificada y trazas del mismo hardware emulado |

### Reglas de secuencia

1. Cada incremento se prepara con contrato, hipótesis, fuentes, archivos permitidos, prueba y condiciones de PASS/FAIL/BLOCKED antes de ejecutar.
2. Sólo una pregunta técnica cerrada por incremento; no expandir alcance a periféricos adyacentes ni repetir incrementos PASS.
3. Diseñar primero y reutilizar código/instrumentación preexistente. MAME/POSE/EmuTOS son referencias, no licencias para copiar mecánicamente.
4. Probar cambios en un árbol/candidato aislado, conservando código y artefactos anteriores; no usar el árbol de AS2K como área desechable.
5. El **primer éxito real** es un guest EmuTOS corriendo en MAME con LCD/teclado. No se declara emulador Dana funcional tras mostrar una UI generada por el host o al compilar.
6. En DIAG, instrumentación opt-in, persistente en log y separada del producto estable; no hacer rebuild innecesario en cada prueba.
7. No abrir un perfil de cold boot Palm/Flash sin conocer mapa, sectores y reset; no asumir que las imágenes Flas extraídas son ROM físicas completas.
8. Retroceder únicamente hasta el incremento de la evidencia contradictoria, no reiniciar todas las auditorías.

### Estado y etiquetas

- **PENDIENTE:** no se ha implementado.
- **READY:** especificación cerrada y autorizada para la ejecución.
- **PASS:** prueba real verificada y artefactos conservados.
- **FAIL:** resultado técnicamente fallido con causa reproducible.
- **BLOCKED:** faltan recurso/evidencia o el entorno impide ejecutar. No declarar PASS ni gastar llamadas a ciegas.

La construcción y cierre de cada hito se asignará al frente de DANA-emu; la documentación de hardware y firmware continúa en DANA-OS3K.
