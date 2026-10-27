# Dana / Flash NOR — implementación comprobada 2026-10-26

**Árbol único:** `SamDelorean/DANA-emu`, `main`, `src/mame/skeleton/alphasdana.cpp`. Trabajo y compilación nativa realizados en el DIAG único de T:
`/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag/source`.
No se creó otra compilación, otro árbol ni una rama. Ejecutable operativo **no sustituido**.

## Evidencia de ingeniería inversa original

La ROM privada UK1.5 (`SHA256 2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`) contiene, en `0x1046B328`, tres escrituras `FF`, una `90`, lectura de identificador de 32 bits desde `0x10000000` y `FF` para volver a lectura de arreglo. La comparación en `0x1046B33A` acepta `0x00208849` y registra capacidad de 8 MiB. El identificador `0x20 / 0x8849` corresponde a la memoria de 16 bits **M28W640HCB** de 64 Mbit, bottom boot. Referencia primaria: [Numonyx M28W640HCB, tablas 3–5 y comandos](https://www.part-elec.com/datasheet/micron/M28W640HCB70N6E.pdf), especialmente `FF` Read Memory Array, `90` Read Electronic Signature, `70` Read Status Register, `50` Clear Status Register.

**No hay fotografía/continuidad suficiente para identificar físicamente el chip concreto de la placa.** El perfil M28W640HCB es una hipótesis explícita respaldada por ROM y datasheet, **no** una atribución automática de hardware a todas las Dana.

## Código implementado

`alphasdana_state` agrega modo NOR `array/id/status`, estado de solo lectura y persistencia de estado MAME (`save_item`). Un nuevo `:NOR_PROFILE` configurable ofrece:
- `0` (predeterminado): componente desconocido; la identificación no responde sin calificación, y el emulador bloquea de forma controlada cualquier comando no soportado.
- `1`: M28W640HCB 8 MiB (diagnóstico explícito). Acepta escrituras de comando mediante accesos byte de las líneas correctas del bus de 16 bits, `FF`/ `90`/ `70`/ `50`; devuelve `0x0020` y `0x8849` desde las dos primeras posiciones de identificador, `0x0080` en estado Ready, y vuelve a leer exactamente el volcado original tras `FF`.

No se implementan indebidamente borrado, programación, bloqueos, AMD unlock/otros chips, CFI incompleto, bit de protección ni persistencia flash programable. Esas operaciones siguen produciendo **physical_block**, no un falso éxito. El volcado ROM **no se modifica**; el perfil no crea bytes de firmware inexistentes.

## Pruebas nativas reales

**Compilación Clang21:** `Compiling src/mame/skeleton/alphasdana.cpp` + archivo `libmame_danadiag.a` + `Linking danadiagd` **PASS**. SHA256 final del **mismo** candidato `c8fe219c9ad8f14a1c3f6ae5c6d06b20c1a5c9a7c32a94b25edfdf178993df3e`; fuente final Git blob `343a6f0078e061be541797dd4af25383a7ec2dd4`, idéntica a `main`.

**Prueba de bus nativo con Lua:** `tests/dana_nor_id_readonly_native.lua` equivalente al observador nativo en T, configuración transient `cfg_nor_id/asmdana.cfg`, original UK1.5, 720 frames. **PASS:**
```text
PROFILE=1 PC=1007B09A
NOR_ID manu=0020 dev=8849 array_before=0000
NOR_ARRAY_RECOVER=0000 initial=0000
NOR_STATUS=0080
NOR_MODEL_NATIVE_READONLY_PASS
END_FRAMES=720
```
Confirmadas **tres FF → 90 → ID → FF → array → 70 → estado → 50 → FF** con transferencias por el mapa original MAME. Sin error de Lua ni `DANA_PHYSICAL_BLOCKED`. Para reproducir, incluir bajo `<input>` del `asmdana.cfg` de prueba:
```xml
<port tag=":NOR_PROFILE" type="CONFIG" mask="1" defvalue="0" value="1" />
```
No sobreescribir la configuración global ni seleccionar ese perfil como valor predeterminado.

**Prueba de la CPU original UK1.5:** para revelar el acceso NOR, se inhibió **sólo durante el experimento** la entrega CPU de INT2/INT3, manteniendo registros `IPR/ISR` y ROM originales. Se recompiló *en el mismo árbol* y luego se restauró exactamente el código con IRQ normal, compilado y re-verificado. Evidencia `pose_historical_reference/nor_integrated_20261026/cpu_real_rom_trial/{error.log,uk15_original_cpu.log}`. El CPU original ejecutó con éxito varias rondas `FF–90–identificador–FF` y **superó el anterior `FLASH_COMMAND_SET_UNVERIFIED`**. Después intentó leer:

```text
DANA_PHYSICAL_MISSING_BYTES address=107f0000 array_offset=007f0000 supplied_bytes=6094848
DANA_PHYSICAL_BLOCKED reason=FLASH_BYTES_NOT_SUPPLIED
DANA_PHYSICAL_CPU curpc=00083d2c ir=0c70
```

**Nuevo límite exacto:** la ROM privada suministra **6 094 848 bytes**, pero el firmware, tras detectar el dispositivo de 8 MiB, intenta leer `0x007F0000` dentro de ese arreglo. La región no está en el volcado. Por seguridad y fidelidad, la lectura queda bloqueada: **no se completa con `FF`, ceros ni repetición de segmentos** sin evidencia de que ese bloque está borrado. Deberá obtenerse el dato real o demostrarse su semántica exacta mediante ingeniería inversa antes de emular su estado.

**Control de integridad final:** candidato compilado con IRQ normal y NOR `c8fe219c9ad8f14a1c3f6ae5c6d06b20c1a5c9a7c32a94b25edfdf178993df3e`; binario operativo intacto `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`; ROM intacta `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. No hay más ejecutables aislados.

**Resultado global:** CMD de identificación/status Flash NOR **INTEGRADO + CLANG/ENLACE PASS + BUS NATIVO PASS + SECUENCIA CPU UK1.5 CONFIRMADA**. **No** significa Palm desktop PASS: (1) interrupciones físicas SD no resueltas; (2) dump NOR incompleto, segundo bloqueo medido. No aplicar supresión de IRQs en producción.
