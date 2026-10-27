# UK1.5 — IRQ Port D, PD7/IRQ6 y suspensión del PLL (27-oct-2026)

## Alcance comprobado

Se investigó y sincronizó **el único DIAG de T**, sin modificar el ejecutable operativo, sin copiar otra compilación y sin parchear la ROM UK1.5. El nuevo código proviene de la misma fuente que efectivamente compiló T; el Git blob publicado y el local coinciden.

- Fuente: `src/mame/skeleton/alphasdana.cpp`, Git blob **`3ae04027ef0a5a0de89a5f51a22902368ad6ca33`**.
- Commit de integración: [`4789f0c`](https://github.com/SamDelorean/DANA-emu/commit/4789f0c33bfc9c322d548321eea6a4812890bc57).
- Candidato único `source/danadiagd`: SHA256 **`4614a42f476b8675e8444a2a340376a13ebbcaeaa8b08e5c4c7638b03cbf2de6`**.
- Operativo `bin/dana-diag` **intacto**: SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
- ROM privada original UK1.5 **intacta**: SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.
- Trabajo T dentro de `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag/work/uk15_qualify_20261025/pose_historical_reference/`. No archivos propietarios publicados.

## Correcciones implementadas (fuente y hardware, no parches del guest)

1. **Polaridad Port D INT2/INT3.** El [manual MC68VZ328, §10.4.5.6](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf) establece que PDPOL=0 significa señal activa ALTA / flanco ascendente, y PDPOL=1 activa BAJA / descendente. El cálculo anterior invertía ese comportamiento y mantenía `ISR_L=0C00` para pines PD2/PD3 en cero; ahora con ambos en cero y PDPOL=0, `ISR_L&0C00=0000` en la ejecución real de UK1.5.
2. **Entrada física PD7 e interrupción IRQ6.** El pulsador On/off entrega tanto su código original al controlador de teclado ST como un contacto eléctrico independiente en PD7, con polaridad y flanco/registros ICR y puerta de GPIO. La señal no es una escritura a RAM del firmware. El IRQ6 participa en el cálculo `m_pending`, máscaras y nivel de CPU; se guarda el estado de contact/edge.
3. **PCTLR y PLLCR.** El controlador reconoce WIDTH=0 de PCTLR para el caso de **STOP nativo** que emite la ROM, sin convertir indiscriminadamente todos los anchos parciales en modo ejecutable. Se modela DISPLL y la reactivación solicitada por una interrupción real con el temporizador de recuperación del reloj; no se crea una IRQ falsa ni se desactivan permanentemente INT2/INT3.

**Cautela:** la fidelidad temporal completa de modo burst/PLL de la placa y la electrónica de las ranuras sigue sin acreditarse físicamente. Validar el despertar de la CPU no equivale a completar la aplicación gráfica.

## Evidencia de Ghidra sobre UK1.5 original

Proyecto reutilizado: `DanaUK15RelocatedTemp`, Ghidra 12.1.3, sin modificación de ROM. Scripts `DanaUK15PostWakePath.java` y `DanaUK15PowerCallerChain.java`, resultados en `pose_historical_reference/pll_sleep_wake_20261026/post_wake_original_rom.txt` y `power_callchain_20261027.txt`.

La primera ruta contiene `1007976C MOVE.B #C0,$FFFFF207` y `10079772 STOP #2000`; reanuda después en `10079776`. La segunda ruta `1007A190 ORI.W #0008,$FFFFF200` establece DISPLL y `1007A196 STOP #2000`. **`1007A19A RTS` es la instrucción *después* del STOP, no una instrucción en bucle**. Una PC constante allí no significa que el guest esté ejecutando código; puede seguir suspendido. La variable `$00000111` se observa cero en las capturas, pero su semántica global no se ha establecido; no modificarla.

Las pilas originales registradas en `post_wake_stacks/native.log` enlazan la primera transición con retornos `10010042` y `10091888`; tras despertar, aparecen retornos `1007D048`, la ruta de gestión de la línea PD7. Se validaron por desensamblado; **no se inyectaron direcciones/retornos**.

## Pruebas originales, no sintéticas

**Regression reproducible en `tests/dana_uk15_power_irq6_original_cpu_native.lua`.** Ejecutada sobre el candidato sin modificación, ROM UK1.5 genuina, `:NOR_PROFILE=1` y `:NOR_FACTORY=1` explícitos (**región borrada sólo en diagnóstico**, no una afirmación sobre una placa utilizada), `SDIRQ=00` (ambos PD2/PD3 bajos), sin tarjetas y a velocidad libre, 3500 cuadros:

```text
F=900 PC=1007B09A ISR_LO=0000 PD=80 LSSA=00072A10
F=1380 PC=10079776 PCTLR=80 PLLCR=2483
ORIGINAL_GUEST_POWER_PRESS frame=1600
F=1601 PC=1007A19A PLLCR=238B ICR=1000 PD=00
ORIGINAL_GUEST_POWER_RELEASE frame=1624
F=1625 PC=1007A19A ICR=0000 PD=80
ORIGINAL_CPU_STOP_TO_WAKE_IRQ6_PASS; PALM_DESKTOP_NOT_ATTESTED
END_FRAMES=3500
```

Registro T: `pose_historical_reference/pll_sleep_wake_20261026/qualified_regression/native_regression.log`. Salida nativa y `LUA ERROR` comprobada, exit code 0. Este test acredita IRQ2/3 desactivadas físicamente cuando corresponde, STOP ejecutado por ROM y progreso posterior causado por tecla física. No acredita escritorio.

**Tres regresiones adicionales, ejecutadas sobre el *mismo* candidato actualizado con la ROM UK1.5 privada, PASS las tres (sin alterar ROM ni binario):**

| Test en `tests/` | Evidencia |
| --- | --- |
| `dana_spi1_mux_internal_native.lua` | `SPI1_INTERNAL_XCH_AND_ISOLATION_PASS` |
| `dana_nor_id_readonly_native.lua` | `NOR_MODEL_NATIVE_READONLY_PASS`; manufacturer `0020`, device `8849` |
| `dana_nor_rtc_day_native.lua` | `RTC_ALARM_AND_FACTORY_NOR_BUS_PASS`; RTCALRM, DAYR/DAYALARM y sector `7F0000=FFFF` bajo perfil virtual borrado |

Ruta T `pose_historical_reference/pll_sleep_wake_20261026/regression_matrix_20261027/` con logs individuales y stdout/stderr. SHA256 del candidato y ROM revalidado después de las cuatro pruebas.

### Matriz de teclas antes del reposo (diagnóstica, no batería física)

Pruebas `pre_stop_power_matrix/hold_from_boot.log`, `pulse_650.log`, `pulse_1150.log`, todas con UK1.5 genuina sin falsificar PC/IRQ:
- Pulsar desde frame1 a 1800: la CPU llega a `PC=100058EE` y se suspende **antes** de pintar el LCD; al soltar, termina las pantallas de inicio y más tarde vuelve a STOP.
- Pulsar entre frames650–800: la CPU entra en la segunda ruta de STOP en `1007A196` y permanece allí en las capturas.
- Pulsar 1150–1700: mismo segundo STOP.
- Cuatro perfiles de SDIRQ ya estudiados anteriormente; esta matriz **no reconstruye** la placa ni justifica un pulso artificial para saltarse código.

## Pendiente de resolución completa (no confundir con PASS)

La ROM original no ha mostrado la pantalla de calibración o el lanzador Palm. **La primera transición STOP→IRQ6 está implementada y comprobada, pero UK1.5 luego ejecuta un segundo STOP legítimo en `0x1007A196`**, con la pantalla AlphaSmart `LSSA=00072A10`. El comportamiento observable es compatible con un estado de energía del sistema operativo, pero **no hay evidencia suficiente para atribuirlo a batería, señal de un chip o programa faltante**. Investigar con Ghidra y evidencia nativa el origen de la solicitud de reposo (gestor de energía / planificador, callbacks y fuente de wake de segundo STOP); no inyectar una PC, ROM ni constante en RAM para proclamar escritorio PASS. No modificar la fuente ni duplicar el DIAG sin nueva evidencia causal.
