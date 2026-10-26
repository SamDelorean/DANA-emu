# Dana MC68VZ328 — bootstrap optativo integrado, probado con ROM y sin ROM
**Fecha:** 2026-10-26. **Rama:** `main`. **Único DIAG en T**. Producto: **DANA-emu**, no un banco aislado.

## Objetivo y continuidad desde AS2K

La topología de trabajo de AS2K se conserva: arranque normal predeterminado, modo bootstrap activado antes de reset, inyección de payload y ejecución bajo CPU real; ROM original inalterada y electrónica externa física no presupuesta. **No se trasplanta el protocolo HC11**: el DragonBall VZ dispone de su **propio bootstrap interno**.

- AS2K/HC11: ATtiny85 controla RESET+MODA/MODB y SCI a 7812.5 baud; carga micro-payload en RAM del 68HC11.
- Dana/MC68VZ328: silicon `EMUBRK LOW` durante RESET; UART1 o UART2 **19200 8N1**, carácter inicial de sincronización, `@` de reconocimiento y eco; formato **Motorola B-record ASCII hexadecimal MAYÚSCULA + CR** (dirección 4 bytes, conteo 1 byte, datos), ejecución con `count=0`. Vectores internos reset: SP `FFFCFFFC`, PC `FFFFFF00`. Búfer interno de instrucciones IBUFF de 32 bytes en **`00FFFFC0`**. Si se carga una instrucción en IBUFF seguida de NOPs, la ROM interna la ejecuta y normalmente **regresa al bootloader**.
- Este incremento **implementa un servicio de carga de registros B y lanzamiento de código**, usando la capacidad Quickload de MAME como **transporte de archivo de prueba**. No afirma simular físicamente la UART de 19200 bps con bit/handshake, TXD2 ni el reconocimiento `@`: esas características NO están implementadas en esta integración. Los B-records sí son consumidos, escriben en el espacio de direcciones real de la CPU y ejecutan 68k. Para continuidad, el mensaje de log `uart=19200` identifica el protocolo elegido, no mide bits transmitidos.
- El modo IBUFF en el estado actual **cede control al código descargado**. El retorno automático de una instrucción breve a la ROM interna de bootstrap tampoco está emulado aún; no se debe declarar una implementación completa del bootloader máscara.

**Referencias originales:** [Motorola MC68VZ328UM, capítulo 17](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), Figura 17-1 y §17.1.2, además de la [copia del proyecto en Drive](https://drive.google.com/file/d/1UuxWG0rYc0n7RoLerqYTt9mlBpU45L6Y/view). Los datos son específicos de **VZ**, no del MC68EZ328, que presenta diferencias de baudios, tamaño de IBUFF y direcciones.

## Código integrado sin romper ROM/PalmOS

- [`src/mame/skeleton/vz328_bootstrap.h`](https://github.com/SamDelorean/DANA-emu/blob/main/src/mame/skeleton/vz328_bootstrap.h), [commit `90cb992`](https://github.com/SamDelorean/DANA-emu/commit/90cb992b115a70c182f9f3d883058529918a533f): parser B-record de 4-byte address+1-byte length+máximo 31 data, checks exactos, requiere hex MAYÚSCULA y CR, nunca simula S-record Motorola distinto ni rellena memoria silenciosamente, byte-count fail-closed, ejecución sólo como último registro.
- [`src/mame/skeleton/alphasdana.cpp`](https://github.com/SamDelorean/DANA-emu/blob/main/src/mame/skeleton/alphasdana.cpp), commits [`b0878c8`](https://github.com/SamDelorean/DANA-emu/commit/b0878c897d8c4f1f072e04fa79448056fada3b43), [`5c9ba60`](https://github.com/SamDelorean/DANA-emu/commit/5c9ba606d355e6b7f8d5aee01c83bf58d10acf19), [`b19aec5`](https://github.com/SamDelorean/DANA-emu/commit/b19aec5208343dbf3244963b21b8c8acae1a2779):
  - `EMUBRK` input configurable, normal alto predeterminado, bootstrap bajo;
  - B-record mediante `-quickload .b` puede activar automáticamente EMUBRK y RESET y funcionar con firmware flash **instalado**, tal como inyector externo AS2K, sin reescribir la ROM;
  - en el modo bootstrap sobre mapa físico VZ se exponen los vectores internos de la figura 17-1, IBUFF de 32 B con acceso de CPU por el bus real `0x00FFFFC0–00FFFFDF` y guardado en save state, PC 68k apuntando a la dirección del registro de ejecución.
  - la descarga por registro B escribe mediante `m_maincpu->space(AS_PROGRAM).write_byte`, **no** un mapa RAM paralelo ni una imagen de ROM sustituta. Si la dirección no tiene dispositivo o acceso válido, se conserva el control de fallas físicas del emulador. No se fabrican chips, CS activos o control NOR.
  - la ROM normal continúa con sus vectores originales y funcionamiento previo. `DANARAM1` sigue siendo incompatible con `-rom`; solo los B-records son aceptados en la ruta de bootstrap.

## Prueba nativa real, no estática

**T único DIAG:** `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag` y evidencia `work/uk15_qualify_20261025/vz_bootstrap_20261026/`.

**Payload-0 de prueba:** [`tests/fixtures/vz328_ibuff_payload0.b`](https://github.com/SamDelorean/DANA-emu/blob/main/tests/fixtures/vz328_ibuff_payload0.b), bytes originales de archivo CR:
```text
00FFFFC0044E7160FE\r
00FFFFC000\r
```
B-record 1 escribe `4E71` (NOP), `60FE` (BRA.S -2) en IBUFF; B-record 2 ejecuta desde `00FFFFC0`.

**Prueba de parser real C++20:** [`tests/vz328_bootstrap_test.cpp`](https://github.com/SamDelorean/DANA-emu/blob/main/tests/vz328_bootstrap_test.cpp) **PASS**: ejemplo Motorola para reactivar TXD2 `FFFFF43B01CF`, parsing de instrucciones en IBUFF, ejecución `count=0`, rechazo de minúsculas, CR ausente, conteos incongruentes, modos ilegales, escritura tras ejecución y overflow 32 bits. Esta prueba no afirma que el hardware de UART2 esté cableado.

**Compilación Clang21 MAME** final, código `main@b19aec5208343dbf3244963b21b8c8acae1a2779`: **PASS**, retorno 0, 18.83 s.

**Prueba física MAME 68000 sin ROM**, `-quickload <payload.b>`, 12 fotogramas y script [`tests/vz328_bootstrap_native.lua`](https://github.com/SamDelorean/DANA-emu/blob/main/tests/vz328_bootstrap_native.lua): **PASS** (same code before final sync), CPU lee instrucciones originales descargadas y ejecuta en IBUFF.

**Prueba física MAME con ROM original UK1.5 presente**, `-rom <UK15_private.raw> -quickload <payload.b>`: **PASS** (final candidate), la ROM no se modifica y B-record tiene prioridad sobre la ejecución normal. La traza registra:
```text
DANA_VZ_BOOTSTRAP_EXEC address=00ffffc0 writes=4 uart=19200
FRAME 1 curpc=00ffffc2 pc=00ffffc4 ibuff=4e71,60fe vec=ffffff00
FRAME 3 curpc=00ffffc2 pc=00ffffc4 ibuff=4e71,60fe vec=ffffff00
FRAME 12 curpc=00ffffc2 pc=00ffffc4 ibuff=4e71,60fe vec=ffffff00
```
Obsérvese el **PC original `FFFFFF00`** leído del vector interno, distinto del vector físico PalmOS.

**Regresión de arranque real UK1.5 sin bootstrap**, `-rom` durante **1800 fotogramas/30 segundos simulados**, **PASS sin `DANA_PHYSICAL_BLOCKED`**, framebuffer palm POWERED con 4,161 pixeles encendidos y CPU ejecutando espera CLK32 conocida. No se afirma escritorio PalmOS.

**Otras regresiones:** ISP1161 HC/DC 33 registros MAME con prueba Python (2/2 PASS), PWM1, RTC, CSD/ROP y PCTLR (4 pruebas PASS). El nuevo modo CPU bootstrap **no modificó** el ISP1161 Host/Device ni el PTD executor ya probado.

**SHA256 verificado:**
- `alphasdana.cpp`: `42885f69ebbb70c4540e9e222a1754a7f3230b7ba747e87f5645225b75ef00d9`
- `vz328_bootstrap.h`: `33334a8e23932db3c82158b8e7dcff5d096b5159f5797afa456e823514bc9e85`
- **Candidato `source/danadiagd`: `6f2eb8a7789bfa6930c14363ca696a3272dad50c114000517c0d888873f53d49`**.
- **Ejecutable operativo `bin/dana-diag` permanece INTACTO:** `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
- ROM privada UK1.5 intacta: `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`; nunca se subió al repositorio.

## Uso reproducible en el ÚNICO DIAG

```bash
# A) Arranque normal PalmOS: EMUBRK alto, ninguna B-record
source/danadiagd asmdana -rom /ruta/privada/UK15_private.raw

# B) Bootstrap hardware-lógico: los registros B activan EMUBRK
# y RESET del chip (sin sustituir la ROM)
source/danadiagd asmdana -rom /ruta/privada/UK15_private.raw \
  -quickload tests/fixtures/vz328_ibuff_payload0.b
```

Existe además selector físico-lógico `EMUBRK` en la configuración del emulador: alto es normal; bajo antes de reset selecciona bootstrap (prioridad mayor que ROM). La prueba controlada puede iniciarse también sin ninguna ROM, usando `-quickload` del ejemplo.

## Límites exactos (evitar atribuir capacidad futura como demostrada)

**Cerrado y funcional:** formato B, prioridad de arranque EMUBRK, vectores internos, buffer 32B accesible a la CPU, ejecución desde el buffer, coexistencia con ROM, regresión arranque normal.

**No demostrado:** UART1/UART2 RX/TX **serial real bit a bit, reconocimiento `@`, eco, selección de UART, cambios de baudios**, retorno automático tras instrucciones aisladas de IBUFF, bootstrap de RAM externa con configuración completa de SDRAM, cables físicos EMUBRK/RESET/UART Dana, ni reemplazo de flash. Esos aspectos requieren un modelo UART VZ y/o calificación de placa y no deben recibir PASS por una prueba Quickload. `0xFFFFF43B` está documentado pero no se ha conectado aquí a Port J real.

**USB:** el ISP1161A1 es hardware externo separado del bootstrap silicon VZ. Su HC/DC/ATL/ITL/PTD físico está integrado y probado en los incrementos previos, sin alterar este modo. **No** existe a la fecha un USB host backend con dispositivo conectado ni USB DC endpoint completo; no fabricar respuestas USB por defecto. Para un futuro bootstrap basado en USB haría falta primero entrar por UART/EMUBRK o Flash ROM y cargar firmware propio que utilice ISP1161.

**No abrir una campaña de pruebas del bootstrap a costa del emulador:** el comportamiento funcional requerido para descargar y ejecutar payload-0 de prueba en el emulador quedó demostrado con original y sin original ROM. Las limitaciones de precisión UART/retorno son las fronteras honestas del modelo.
