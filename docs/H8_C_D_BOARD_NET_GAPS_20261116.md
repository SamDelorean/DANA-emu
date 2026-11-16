# H8-C / H8-D — Clasificación de interconexiones y modos VZ no usados

Fecha 2026-11-16. **H8-C = `SOURCE_MAP_RECONCILED / PHYSICAL_MEASUREMENT_PENDING`; H8-D = `CONDITIONAL_NO_GUEST_PROVEN_BLOCKER`.** Sin nueva ejecución en T, sin tocar emulador, ROM, atlas ni libros maestros.

## H8-C. Evidencia física versus digital

| Elemento y posible red | Evidencia actualmente disponible | Nivel autorizado | Acción mínima de la siguiente medición si se dispone de placa |
| --- | --- | --- | --- |
| U4 VZ MC68VZ328PV TQFP144 | Marcado legible en `IMG_3277`; manual Motorola | `OBSERVADO_COMPONENTE` | Ninguna; no repetir identificación |
| U5 RAM Samsung K4S641632F-TL1L TSOP-II 54, 8 MiB | Topmark de una SDRAM visible; ficha y pinout de 54 posiciones | `OBSERVADO_COMPONENTE`, **continuidad no medida** | Solo si la configuración de la placa no cuadra con RAM emulada, contar chips y comprobar líneas CS/RAS/CAS |
| U7 NOR TSOP-48, etiqueta V33 | 48 terminales visibles; fabricante, modelo y capacidad ilegibles | `OBSERVADO_ENCAPSULADO`, `NO_VERIFICADO_MODELO/CONTINUIDAD` | Fotografía nítida de topmark y orientación pin1; identificación JEDEC/CFI únicamente con un procedimiento seguro de lectura, sin programar/borrar |
| U1 candidato Philips ISP1161A1 LQFP64, Y1 6 MHz | Pin count y cristal; ISP1161 software/registro acreditado, **no** continuidad U1↔VZ | `INFERIDO_COMPONENTE`, `NO_MEDIDO_PCB` | No medir en H8: transferencia USB con PC expresamente diferida |
| SD0 `PB5 power` / `PJ3 CS` / `PD2 INT2` | Referencia EmuTOS y CPU/SPI1 de MAME con dos medios | `OBSERVADO_SOFTWARE`, `NO_MEDIDO_PLACA` | Comprobar qué ranura física es SD0 y si PD2 se conecta a un interruptor real de inserción; pin/circuito/polaridad, sin inferir que INT2 sea card-detect |
| SD1 `PK5 power` / `PF2 CS` / `PD3 INT3` | Segunda ruta virtual y documentación del port | `OBSERVADO_SOFTWARE`, `NO_MEDIDO_PLACA` | Igual con SD1; confirmar orientación izquierda/derecha antes de rotular GUI |
| PWM1 `PB7/PWMO1` y altavoz | H5 y la ROM UK1.5 usan PWM1; audio mono PASS digital | `OBSERVADO_FIRMWARE`, `NO_MEDIDO_ETAPA_ANALOGICA` | No hay bloqueo de hardware digital. Medir amplificación solo si se solicita fidelidad acústica |
| PWM2 `PM5/PWMO2` | Existe en silicio; no se observó una ruta usada por Palm original | `NO_REQUERIDO_ACTUAL`, `SIN_CONTINUIDAD` | No implementar un segundo canal sin evidencia de uso |
| Batería `PG1`, ADC A4/E4, carga `PJ6` | H5 acreditó lecturas en SPI2 y estado GPIO mediante ROM UK1.5 | `OBSERVADO_SOFTWARE`, `NO_MEDIDO_VOLTAJE/CARGADOR` | Si se necesita modelar voltaje/carga, medir la transferencia real; nunca deducir una curva de porcentaje del ADC en bruto |
| LCD 560x160 y contraste | H4 controlador digital completo; cristal/óptica/bias no medida | `PASS_DIGITAL`, `NO_MEDIDO_PANEL` | No introducir respuesta de vidrio imaginaria |
| UART2/SIR infrarrojo | Palm original transmite y recibe XID/bytes por UART2 | `OBSERVADO_SOFTWARE`, `NO_MEDIDO_TRANSCEPTOR` | No bloquear las funciones del emulador por alcance óptico no requerido |
| J100 RESET/EMUBRK/UART | Pads 2x4 visibles, sin continuidad/cabecera identificada | `NO_VERIFICADO_PCB` | No asignar pinout sin multímetro y equipo sin energía; la conexión física no es parte de la emulación digital acreditada |
| Dana Wireless PKDATA.0 | Solicitud digital `ON/OFF` H6 y rutinas NetIF original | `PASS_MONITOR`, `NO_MEDIDO_ALIMENTACION_MODULO` | Radio/SDIO fuera de alcance; no añadir chip ni interrupciones hipotéticas |

**Ninguna de estas líneas se convierte automáticamente en hardware faltante**: una conexión hipotética no autoriza cambiar un GPIO, IRQ, chip-select, puerto, ADC o PWM del driver. Una futura medición debe registrar placa/modelo, pin de origen, pin de destino, condición de energía, instrumento, continuidad observada y foto; `INFERIDO` no es `MEDIDO`.

## H8-D. Funciones VZ condicionadas a bloqueos reales

- `physical_r`/`physical_w` y `physical_mmio_r/w` preservan errores terminales ante accesos no soportados. Constituyen **protección correcta**, no fallos en sí; no se retiran para fingir funcionamiento.
- `PCR_PWM_TIMER_COMBINATION_UNIMPLEMENTED` protege modos periféricos no usados en las campañas aprobadas. No hay traza de ROM original que exija activarlos.
- `ICE` completo, funciones de fábrica/EMUBRK y transferencia B-record fuera del trayecto de arranque probado pertenecen a un futuro requisito diagnóstico **solo si se demuestra uso**. No inventar protocolo ni reutilizar instrucciones HC11 del AS2K.
- Los registros LCD IRQ/LFRCM no deben recrearse: H4 documenta su ausencia en el controlador VZ y la utilización digital ya verificada.
- La ruta PALM original hacia PC por USB, HotSync/NEO Manager, radio y SDIO están excluidos de este alcance por decisiones explícitas.

**Resultado H8-D:** No existe en los dos trabajos H8-B una nueva traza CPU de firmware comercial que permita justificar una corrección VZ. Sin imagen completa, la etapa queda `NOT_TRIGGERED / NO_CHANGE_JUSTIFIED`, no `PASS` de funciones desconocidas. Se conservarán los errores genuinos si en una prueba posterior aparecen.

## H8-E. Límite de aceptación

Los controladores digitales esenciales ya cuentan con evidencia H1–H7, y H8-B reutilizó sus pruebas de perfil. No hay un motivo técnico para crear más controladores ni alterar H6/H7. **No declarar todavía fidelidad física integral ni arranque comercial de tres variantes**, porque U7 y las líneas de placa no están medidos y no existe una imagen stock completa certificada. H8-E espera esas dependencias o una decisión explícita sobre un alcance final más limitado.

Fuentes: [`DANA_HARDWARE_INTERCONNECTION_ATLAS_20261026.md`](DANA_HARDWARE_INTERCONNECTION_ATLAS_20261026.md), [`D7_D8_3_SPI1_DUAL_SD.md`](D7_D8_3_SPI1_DUAL_SD.md), [`H5_PWM_POWER_INTEGRATION_20261115.md`](H5_PWM_POWER_INTEGRATION_20261115.md), [`H6_INTEGRATION_20261116.md`](H6_INTEGRATION_20261116.md), [`H8_B_NATIVE_MEDIA_AUDIT_20261116.md`](H8_B_NATIVE_MEDIA_AUDIT_20261116.md) y código `src/mame/skeleton/alphasdana.cpp` en `main`.
