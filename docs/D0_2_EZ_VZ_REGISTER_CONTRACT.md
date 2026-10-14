# D0.2 — Comparativo de registros MC68EZ328 (MAME) ↔ MC68VZ328 (Dana)

**Fecha 2026-10-13. Estado: SPEC_READY documental, no PASS funcional.** Incremento exclusivamente estático. No se modificaron MAME, T, Ghidra ni firmware.

## 1. Dictamen

**El DragonBall EZ de MAME es la base de reutilización, no un sustituto directo del VZ.** Comparten núcleo 68000 y familias de registros, pero hay diferencias de chip-select y DRAM, valores de reset, prioridades IRQ, GPIO, temporizador 2, SPI1, UART2 y DMA LCD.

**Orden de autoridad:** manual Motorola MC68VZ328UM **más addendum MC68VZ328UMAD** → implementaciones abiertas POSE/Retro68 → accesos observados en EmuTOS-Dana → extrapolaciones del MAME EZ. Los valores iniciales de POSE **no** se asumen como reset físico cuando no coinciden con el fabricante.

### Fuentes inmutables

- **ME:** [MAME, mc68328.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.cpp) y [mc68328.h](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.h), especialmente líneas 113–330 y 370–559.
- **PV:** [POSE, EmRegsVZ.cpp](https://github.com/cloudpilot-emu/pose-original/blob/97b10711fe4ca50c1bd47072378eaab26ba8e81d/SrcShared/Hardware/EmRegsVZ.cpp), tabla kInitial68VZ328RegisterValues líneas 73–335; [M68VZ328Hwr.h](https://github.com/cloudpilot-emu/pose-original/blob/97b10711fe4ca50c1bd47072378eaab26ba8e81d/SrcShared/Palm/Platform/Core/Hardware/IncsPrv/M68VZ328Hwr.h).
- **ET:** [EmuTOS-Dana bios/dana.c](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c), líneas 42–98, 201–305, 308–370.
- **DZ:** [dbztool danainit.sh](https://github.com/davidgiven/dbztool/blob/d32702383c2ea3523ea58599c52345435c74e900/danainit.sh), referencias de chip-select y DRAM *después* del bootstrap.
- **UM:** [Motorola MC68VZ328UM/D](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), tabla 3-1/3-2 y capítulos 6–14.
- **AD:** [Addendum oficial MC68VZ328UMAD/D](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf), correcciones de CSCTRL, LRRA, SPI1 y UART.

### Convención de direcciones

Los offsets de las tablas se suman a **0xFFFFF000**. Ejemplo, offset 0x700 = dirección **0xFFFFF700**. Se indican anchos de acceso en bits. Si un valor dice **POSE**, es reset implementado en POSE, no valor oficial confirmado; si dice **AD** o **UM**, procede del fabricante. Los datos de RAM (4 MiB) y registros configurados por dbztool/EmuTOS **no** son estado de reset eléctrico.

## 2. Contrato de MMIO, registro por registro

| Función | VZ offset(s) | Ancho | Equivalente EZ en MAME | Reset VZ observado/corregido | Divergencia o efecto a modelar |
|---|---|---|---|---|---|
| SCR | 000 | 8 | Sí; MAME EZ arranca 0x0C | **0x1C UM/PV** | RESET distinto; no heredar EZ |
| ID de chip | 004–007 | 32 conjunto | Lecturas de revision EZ, no ID VZ | Chip ID 0x56 en PV | Identidad de CPU, consultar datasheet |
| Base de CS A/B/C/D | 100,102,104,106 | 16 cada | Sí | 0x0000 cada PV/UM | Bases parecidas pero efectos físicos por modelo |
| CSUGBA upper group | 108 | 16 | **NO EZ**; el MC68328 clásico coloca mask A aquí | 0x0000 PV | Registro diferente en igual offset |
| CSCTRL1 | 10A | 16 | **NO EZ**; MC68328 clásico tiene mask B | **0x0000 AD** | Control de grupos y bancos VZ |
| CSCTRL2 | 10C | 16 | No | **0x1000 AD**, POSE usa incorrectamente 0x0000 | Corrección crítica de reset |
| CSA / CSB / CSC / CSD | 110/112/114/116 | 16 cada | Sí, máscaras específicas EZ | 0x00B0 / 0 / 0 / 0x0200 UM/PV | Ventanas/bus/DRAM y líneas externas |
| EMUCS | 118 | 16 | Sí | 0x0060 UM/PV | Emulation chip select |
| CSCTRL3 | 150 | 16 | NO EZ | **0x9C00 AD**, POSE usa incorrectamente 0x0000 | Corrección crítica de reset |
| PLLCR | 200 | 16 | Sí; MAME EZ 0x2400 | 0x24B3 **POSE** | Recalcular clock y modelo del VZ |
| PLLFSR | 202 | 16 | Sí; MAME EZ 0x0123 | 0x0123 **POSE** | Bit15 **varía**: ET espera alternancia |
| PCTLR | 207 | 8 | Sí | 0x1F **POSE** | Estados de power/STOP por contrastar |
| IVR | 300 | 8 | Sí | 0x00 UM/PV | ET escribe 0x40 antes de IRQ |
| ICR | 302 | 16 | Sí | 0x0000 UM/PV | ET escribe 0x8000 |
| IMR | 304–307 | 32 (dos palabras 16) | Sí | 0x00FFFFFF UM/PV | ET primero enmascara; luego habilita Timer1/UART1 |
| ISR | 30C–30F | 32 | Sí | 0x00000000 UM/PV | Status no debe confundirse con pending |
| IPR | 310–313 | 32 | Sí | 0x00000000 UM/PV | Pending, prioridad y ack reales |
| ILCR | 314 | 16 | **NO EZ** | 0x6533 UM/PV | Niveles de interrupción programables del VZ |
| GPIO A–G | 400–433, discontinuos | 8 por registro | Parcialmente común | Tabla POSE por registro | Multiplexación, pull-up/down y entradas externas diferentes |
| GPIO J/K/M | 438–44B, discontinuos | 8 por registro | **NO en clase EZ**; algunos en MC68328 clásico | Tabla POSE por registro | ST, SD y LCD en pines J/K del Dana |
| Timer1 TCTL/TPRER/TCMP/TCR/TCN/TSTAT | 600/602/604/606/608/60A | 16 cada | Sí | 0000/0000/FFFF/0000/0000/0000 PV/UM | ET configura compare, prescaler y ack |
| Timer2, misma secuencia | **610/612/614/616/618/61A** | 16 cada | **NO EZ**; MC68328 clásico usa segundo timer en **60C** | 0000/0000/FFFF/0000/0000/0000 PV/UM | No copiar ubicación de Timer2 MC68328 |
| SPI1 RX/TX/CTRL/INT/TEST/SPC | **700/702/704/706/708/70A** | **16 cada** | **NO en clase EZ**; MC68328 clásico mapea SPIS en 700 | 0x0000 cada PV/UM | **Diferencia crítica: SPI1 VZ es maestro/esclavo y sirve a SD** |
| SPI2 DATA/CTRL | 800/802 | 16 cada | SPIM EZ sí existe en estos offsets | 0x0000 cada PV/UM | ST/ADC del Dana. Validar bitfields/XCH |
| UART1 USTCNT/UBAUD/URX/UTX/UMISC | 900/902/904/906/908 | 16 cada | Sí (única UART EZ) | 0000/**0002**/0000/0000/0000 | **AD corrige BAUD1**; MAME EZ y POSE usan 003F |
| UART1 noninteger prescaler | 90A | 16 | No en EZ revisado | 0x0000 POSE | Elemento nuevo de ajuste de baudios |
| UART2 CONTROL/BAUD/RX/TX/MISC/PRESC/HMARK | 910/912/914/916/918/91A/91C | 16 cada | **NO EZ** | 0000/**0002**/0000/0000/0000/0000/**0102** | **AD corrige BAUD2; UM da HMARK 0102 (POSE 0000)** |
| LCD LSSA | A00 | 32 | Sí | 0x00000000 POSE/UM | Dirección física del framebuffer, no puntero host |
| LCD LVPW, LXMAX, LYMAX | A05/A08/A0A | 8/16/16 | Sí | FF/03F0/01FF POSE | ET carga 35/560/159 para Dana |
| LCD LPICF, LPOLCF, LACDRC, LPXCD, LCKCON | A20/A21/A23/A25/A27 | 8 cada | Sí | 0/0/0/0/0 POSE | ET escribe 8/0/0/3/0x80 |
| **LCD LRRA** | **A28** | **16** | MAME EZ tiene registro de 8 bits en **A29** | **0x00FF AD** | **Ancho y posición corregidos por AD** |
| LCD LGPMR / PWMR | A33 / A36 | 8 / 16 | Sólo subconjuntos EZ, semántica diferente | 84 / 0000 POSE | Modos de escala de grises y contraste |
| LCD RMCR / DMACR | A38 / A39 | 8 cada | NO en EZ revisado | 00 / 62 POSE/UM | DMA LCD específico VZ |
| RTC/watchdog, control | B00–B1C | 8/16/32 según registro | Parcial | consultar UM+AD | **AD corrige RTCCTL y STPWCH a 16 bits** |
| **DRAMMC/DRAMC/SDCTRL/SDPWDN** | **C00/C02/C04/C06** | **16 cada** | **NO en EZ MAME** | **0000/0000/003C/0000 según UM** | **POSE asigna 003C a DRAMC y 0000 a SDCTRL; incompatibilidad de reset** |
| ICEM/depuración hardware | D00–D0E | 16/32 | No equivalente | ceros en POSE | Bootstrap y depuración separados del debugger host |

**No se declara equivalencia bit a bit para todos los registros.** D0.2 fija el mapa, el ancho, los resets esenciales y los efectos/riesgos de integración. Máscaras específicas del VZ, comportamiento de lectura, temporización y restricciones de buses se verifican en los contratos de implementación D1–D4 contra UM+AD, no se inventan.

## 3. GPIO del Dana — configuración y riesgos

| Puerto VZ | Offsets 8b (DIR/DATA/PUEN/SEL) | Reset POSE en ese orden | Función Dana observada |
|---|---|---|---|
| B | 408/409/40A/40B | 00/00/FF/FF | PB6 reset ST; PB5 alimentación SD0 |
| C | 410/411/412/413 | 00/00/FF/FF | PDEN/SEL LCD y pines; C412 es pulldown |
| D | 418/419/41A/41B (más 41C–41F) | 00/00/FF/FF, otros 00 | Interruptores ST/SD experimentales; port usa polling ST |
| E | 420/421/422/423 | 00/00/FF/FF | PE3 chip select ST |
| F | 428/429/42A/42B | 00/00/FF/8F | PF1 pen IRQ, PF2 CS SD1, PF6 contraste |
| G | 430/431/432/433 | 00/00/3D/08 | PG2 chip select táctil |
| J | 438/439/43A/43B | 00/00/FF/EF | PJ3 chip select SD0 |
| K | 440/441/442/443 | 00/00/FF/FF | PK2 ready ST, PK6/PK3 contraste, PK7/PK4 LCD |

Estos son **resets modelados por POSE**, no una prueba de niveles eléctricos del tablero Dana. La conexión en placa requiere contrastar EmuTOS y Retro68; no reutilizar la matriz de Neo como si equivaliera al ST.

## 4. Erratas y discrepancias relevantes: bloqueantes para copiar registros

| ID | Situación errónea en fuente secundaria | Valor oficial VZ a usar |
|---|---|---|
| ERR01 | POSE CSCTRL2=0x0000 | **0x1000**, 0xFFFFF10C, 16 bits (AD) |
| ERR02 | POSE CSCTRL3=0x0000 | **0x9C00**, 0xFFFFF150, 16 bits (AD) |
| ERR03 | POSE UBAUD1/2=0x003F | **0x0002**, 0xFFFFF902 y 0xFFFFF912 (AD) |
| ERR04 | Manual inicial LRRA de 8 bits en A29 | **16 bits en 0xFFFFFA28**, reset 0x00FF (AD) |
| ERR05 | Manual inicial SPI1 RX y TX como 8 bits | **16 bits** en 0xFFFFF700 y 0xFFFFF702 (AD) |
| ERR06 | POSE DRAMC=0x003C; SDCTRL=0x0000 | **DRAMC=0x0000; SDCTRL=0x003C** (UM) |
| ERR07 | POSE UART2 FIFO HMARK=0x0000 | **0x0102 en 0xFFFFF91C** (UM) |
| ERR08 | Timer2 MC68328 clásico usa offset 60C | **VZ Timer2 comienza en 610** |
| ERR09 | Interpretar 700 como SPI slave genérico del EZ | **VZ SPI1 RX/TX/CTRL/INT/TEST/SPC ocupa 700–70A** |
| ERR10 | Usar 4 MiB RAM y PC de EmuTOS como reset eléctrico | Es el **estado post-bootstrap**, no el reset de hardware |

Las discrepancias anteriores son **hallazgos documentales**, no defectos medidos del equipo real ni fallos comprobados de POSE en ejecución.

## 5. Contrato observable para incrementos posteriores

- **D1: chip-select/DRAM.** El perfil RAM-only permite 4 MiB ya inicializados con CPU/PC/SP documentados. El cold boot debe modelar reset real y CS/DRAM programables, sin imaginar regiones físicas Flash. Revisar escrituras de [danainit.sh](https://github.com/davidgiven/dbztool/blob/d32702383c2ea3523ea58599c52345435c74e900/danainit.sh) antes de decidir layout.
- **D2.1 PLL:** ET espera alternancia de PLLFSR bit15 en delay_us. Se modela el reloj virtual, no una constante manipulada por instrucción.
- **D2.2 IRQ:** IVR=0x40, ICR=0x8000, IMR inicialmente 0x00FFFFFF; interrupciones de UART1 y Timer1 deben alcanzar realmente al guest.
- **D2.3 Timer1:** ET programa prescaler, compare, TCTL1=0x33 y reconoce TSTAT1. El reloj virtual determina el tick.
- **D2.4 UART1:** ET espera bit13 UTX1 y escribe byte al offset 907; salida de consola comprobable.
- **D3 LCD:** LSSA apunta a RAM invitada; 560x160x1bpp = 11200 bytes sin padding; LPICF=8, LVPW=35, LXMAX=560, LYMAX=159, LCKCON=0x80.
- **D4 SPI2/ST:** ET escribe SPICONT2=0x2200, SPIDATA2 y SPICONT2=0x2307; handshake 0xAA; GPIO PB6/PE3/PK2 y state machine comparada con Retro68.
- **D7 SPI1/SD:** bus de 16 bits, ready/busy y CS PJ3, power PB5; no suplantar SPI por llamadas de disco de alto nivel.

## 6. Lo que NO cerramos artificialmente

- La instalación exacta y SHA del **checkout MAME físico de T**: pendiente de primer preflight remoto autorizado, no gastar Commander en exploración.
- El conjunto completo de bitfields de cada periférico VZ: se recuperará en el contrato y las pruebas del incremento específico.
- La ROM guest de EmuTOS-Dana compilada y su SHA: **D0.3**, siguiente tarea.
- Dirección de todos los bancos Flash/ROM físicos del Dana: desconocidas; no inventar cold boot.
- El soporte estable/diag y el arranque de EmuTOS: **cero pruebas funcionales**.

## 7. Dictamen

**D0.2: SPEC_READY (documentación de mapa/ancho/resets críticos y diferencias entregada).** Su estado no implica aprobación de código ni valida funcionalidad del hardware.

**Siguiente incremento estricto: D0.3 — especificar binario EmuTOS-Dana, formato/relocación y receta reproducible, sin lanzar compilación en T.** No iniciar D1 ni utilizar Commander por este documento.
