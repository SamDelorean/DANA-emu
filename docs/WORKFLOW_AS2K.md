# Directivas operativas heredadas del emulador AS2K

**MANDATORY FOR NEW CONVERSATIONS:** [CANONICAL_CONTINUITY_AND_RULES.md](CANONICAL_CONTINUITY_AND_RULES.md). It consolidates the verified Drive operating records, canonical T deviceId, dcjob launcher, three-call maximum subject to new explicit authorization, English Git rule and exact D0.6 checkpoint. No Commander for static documentary work.

**Objetivo:** producir un emulador estable y uno diagnóstico, reducidos, usando MAME como plataforma propia de pruebas.

## Plan autoritativo

El plan completo, con incrementos atómicos y sus pruebas, se guarda en [DANA_EMU_INCREMENTAL_WORK_PLAN.md](DANA_EMU_INCREMENTAL_WORK_PLAN.md). **No document-only increment may be marked as functional PASS.** D0.1–D0.5 are SPEC_READY documentation; **D0.6 is next** and requires no Commander calls.

## Metodología establecida

**Reutilización estática → diseño de incremento → candidata congelada → autorización explícita de ejecución → job autocontenido → T → evidencia por Drive → PASS/FAIL/BLOCKED → integración exclusiva de PASS.**

GitHub aloja fuentes y documentación; no sustituye compilación/ejecución real sobre la máquina T. La aceptación upstream MAME no es requisito y las pruebas de GitHub Actions no sustituyen el banco local.

## Máquina T y ejecución

- Entorno T: spc-HP-t640-Thin-Client, usuario spc.
- Repositorios de trabajo AS2K conocidos en /home/spc/Projects/alphasmart; Ghidra 12.1.3 en /home/spc/.local/opt/ghidra_12.1.3_PUBLIC; directorio Ghidra /home/spc/GhidraProjects.
- **No inventar la ruta local de checkout DANA-emu ni de un binario MAME Dana**: esa ruta aún no se ha establecido ni verificado.
- Para compilaciones T, política del usuario: **exactamente tres núcleos (-j3)**.
- Commander no debe usarse sin **autorización explícita**; el presupuesto aprobado en otro frente o conversación no se transfiere automáticamente.
- Drive transporta el único script SH/job autocontenido, resultados, fallas y evidencia. Usar lanzador real documentado **/home/spc/.local/bin/dcjob launch** sólo tras preparar el job y comprobar que no hay más de un job pendiente.
- **No gastar Commander** en exploración de rutas, polling, lectura reiterada de logs, pruebas de conexión, instalaciones exploratorias o recopilación estática resoluble por GitHub/Drive.
- Un job ejecuta autónomamente el alcance autorizado y deposita log, hashes, manifest, resultados y dictamen en Drive. Los temporales son aislados; no borrar ni alterar objetos de otros proyectos.
- Ningún job puede escribir firmware físico del Dana ni modificar repositorios AS2K salvo orden expresa distinta.

## Separación estable/diagnóstico

- Un único motor compartido de CPU/hardware en MAME; variantes por configuración de compilación, launcher e instrumentación.
- Ejecutables, perfiles, imágenes RAM/ROM externas, SD, snapshots, registros y temporales separados.
- **stable:** experiencia diaria y control de estado de sesión.
- **diag:** trazas MMIO/CPU/IRQ/SPI, guards/snapshots, logs machine-readable y scripts de pruebas; siempre opt-in cuando una sonda pueda producir gran volumen.
- La evidencia de diag sirve para calificar stable; un PASS de DIAG no reemplaza un smoke test de stable.

## Proveniencia y derechos

Registrar revisión exacta del código MAME y los hashes del binario de prueba. Un hash de ejecutable es evidencia de proveniencia, no un motivo para bloquear un test si se compiló legítimamente otro hash. No incorporar firmware comercial ni binarios Palm/Dana extraídos a GitHub. No copiar código GPL EmuTOS/POSE directamente en MAME sin revisar licencias.

## Referencias existentes del usuario

- [DANA-OS3K: entorno T y Ghidra](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/07-ENTORNO-T-Y-GHIDRA.md)
- [DANA-OS3K: directiva de emulador reducido](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/11-ALCANCE-EMULADOR-REDUCIDO.md)
- [DANA-OS3K: arquitectura EmuTOS](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/08-EMULADOR-ARQUITECTURA-EMUTOS.md)

Estas reglas rigen desde la preparación y durante todos los incrementos; no sustituirlas por un flujo improvisado.
