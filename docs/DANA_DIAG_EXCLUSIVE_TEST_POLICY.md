# DANA-emu — Política obligatoria de pruebas: Dana DIAG exclusivamente

**Autorizada por el usuario: 2026-10-17. ESTADO: VIGENTE / VINCULANTE.**

## Regla

**El único emulador autorizado para ejecutar pruebas de DANA-emu es Dana DIAG (`dana-diag`).** Está prohibido ejecutar pruebas con `dana-stable`, versiones `stable`/release, MAME genérico u otros emuladores, aun cuando sus binarios existan en la máquina T.

- El selector de **máquina interna** `asmdana` utilizado dentro del ejecutable `dana-diag` es permitido; **no** es otro emulador.
- `danadiagd` es el nombre del artefacto intermedio **de compilación del mismo subtarget DIAG** (`SUBTARGET=danadiag`); para las pruebas se copia a `.../diag/bin/dana-diag`. No habilita ninguna variante ajena.
- Puede inspeccionarse el **código fuente** de la revisión donante de MAME para construir el único DIAG, pero **no ejecutar el MAME donante**.
- Está permitida la compilación aislada de fragmentos C++ para comprobación de lógica (no son emuladores completos), sin atribuirles PASS de emulación real.
- Antes de lanzar un trabajo T, verificar que los runners de pruebas aceptan **exclusivamente la ruta absoluta del `dana-diag` compilado**. Impedir ejecución de `dana-stable` u otro ejecutable por cualquier vía. No aceptar resultados comparativos stable/diag.
- Conservar la fuente original de EmuTOS, sus ROMs y sus SHA; **no recompilar ROMs** dentro de campañas funcionales D2.x.
- El uso de T/Commander queda sujeto a una **autorización específica y presupuesto separado**. Mantener SH verificado, registro SHA256, cola Drive de un único trabajo, ejecución `/home/spc/.local/bin/dcjob launch`, evidencia por Drive y estados PASS/FAIL/BLOCKED basados en ejecución real.

## Aplicación actual — D2.1 PLLFSR

El SH `004_dana_d2_1_pllfsr_native_diag_20261017.job.sh`, registrado en Drive/HOLD, pin `621c83df2aa1a1b614f3f4b5351a59ef8365f537`, está limitado a preparar `diag`, compilar exclusivamente `SUBTARGET=danadiag` y enviar `.../diag/bin/dana-diag` a smoke, RAM, MMIO y EmuTOS auténtico. Los runners ejecutan `asmdana` **dentro del binario `dana-diag`**, no con otro emulador. Se autorizaron **hasta 3 llamadas Commander** para la campaña, no para variantes adicionales.

**Infracción o identidad no comprobable ⇒ detener la campaña como BLOCKED, no sustituir por otro emulador.**
