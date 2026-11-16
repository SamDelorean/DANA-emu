# H8-B — Arranque físico: inventario nativo y bloqueo de imagen comercial

Fecha: 2026-11-16. **Resultado** `DIGITAL_H3_H6_PRIOR_PASS_REUSED / COMMERCIAL_FULL_BOOT_BLOCKED_EXTERNAL_IMAGE`. Esta etapa no ejecutó un invitado nuevo ni reabrió H3/H6. No declarar nuevo `PASS` de firmware comercial.

## Evidencia ejecutada en T, 2/5 llamadas autorizadas para H8-B

- Trabajo 001 `H8_B_MEDIA_INVENTORY_AND_SOURCE_SYNC_PASS`, salida 0; inventario de rutas de Dana en `runtime/diag/work`, sus hashes y vectores. No ejecutó MAME. El árbol Git de T se sincronizó por *fast-forward* con `main@1785a26a5f38ae4180f922c8dc81e379eaf437e1`, árbol limpio.
- Trabajo 002 `H8_B_KNOWN_PRIVATE_SOURCE_INVENTORY_PASS`, salida 0; inspección adicional de las **dos ubicaciones privadas ya documentadas** `/home/spc/Projects/alphasmart/private/roms/dana` y `/home/spc/Projects/Dana-OS3K/firmware/research-only`. Sin lecturas ni publicaciones de contenido comercial más allá de hashes, cabeceras de 8 bytes, tamaños y nombres de miembros ZIP; no descomprimir/ejecutar los actualizadores ni escribir en ninguna ROM.
- Ejecución sin cambio del único `dana-diag`, SHA-256 `73550d0fc28c3189038e39fad2b5a4321dab59da8cfc416317fad18b875f4e41`. **Ningún nuevo binario, compilación ni perfil aislado**.

## Inventario y procedencia

| Fuente | Tamaño / naturaleza | Evidencia y dictamen |
| --- | --- | --- |
| `UK15_private.raw` | 6,094,848 bytes, SHA-256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` | Flujo UK1.5 `Flas` derivado de actualizador. SSP `00000316`, PC `100002a2` estructuralmente válidos; **no** dump completo de NOR 4/8 MiB. |
| `pose_historical_reference/Dana1.2.1.rom` | 3,866,624 bytes | Imagen histórica de referencia, vectores estructuralmente válidos; longitud física no completa ni procedencia de placa acreditada. |
| `AlphaSmart_Dana1_5_Flash.zip` | 9,453,509 bytes, SHA-256 `1a0256e35c11c7455a58738f05218e1e290b8d381a5742467f1a512ac25c14fc` | Contiene actualizadores Palm, no dump de Flash; hash del archivo fuente coincidió. |
| `DanaUpdate_enUS120.prc` y `...150R1.prc` | PRC 1.2/1.5, hashes verificados | Bases de recursos de actualización, no imágenes físicas. |
| `Dana_US12_Flas.raw` / `Dana_US15_Flas.raw` | 3,833,856 y 6,062,080 bytes | Contenidos `Flas` US derivados de actualización. SHA-256 coincide con documento original; no NOR íntegra. |
| `emutos-dana.rom`, `emutos.img`, `emutos.dana` | 223,792 / 223,748 / 223,812 bytes | Herramientas/paquetes de invitado EmuTOS; no reemplazo de firmware físico de Dana. |
| Dos imágenes `synthetic_sd*.img` | 2 MiB cada una | Tarjetas SD diagnósticas; no firmware. |

**No hay ningún archivo encontrado que certifique un dump comercial completo, byte a byte, de la Flash de Dana 2002 o 2003.** Una coincidencia de tamaño y vector nunca es evidencia suficiente por sí sola. El inventario es acotado a ubicaciones conocidas, no una afirmación sobre todos los archivos que puedan existir fuera de esas rutas.

## Pruebas nativas anteriores recuperadas sin repetirlas

22 recibos H6 de perfiles NOR/SDRAM: 16 pruebas CPU positivas en perfiles 0–3 y 6 rechazos previstos por geometría incompatible. **De esos recibos, 8 son del SHA H6/H7 aún instalado**: 5 CPU positivos y 3 rechazos correctos; otros 14 pertenecen a una compilación anterior. Los perfiles digitales siguen acreditados en su alcance, **no equivalen** a tres arranques comerciales.

## Estado por variante

| Perfil | Pruebas digitales reutilizadas | Arranque comercial completo |
| --- | --- | --- |
| Dana original 2002, RAM 8 MiB / NOR 4 MiB | `PASS` previo | `BLOCKED_EXTERNAL_IMAGE` (sin dump íntegro autenticado) |
| Dana revisada 2003, 16/8 MiB | `PASS` previo | `BLOCKED_EXTERNAL_IMAGE` (UK/US Flas no son dump 8 MiB) |
| Dana Wireless 2003, 16/8 MiB | `PASS` previo de RAM/NOR | `BLOCKED_EXTERNAL_IMAGE`; radio excluida por decisión de alcance |

**No corresponde modificar `alphasdana.cpp`, recompilar, rellenar/truncar un actualizador ni crear una ROM falsa** para forzar un PASS. Si aparece un dump real con trazabilidad de placa/sector, ejecutar una única prueba de arranque por perfil apropiado con fuente, tamaño y SHA fijos, registrando vectores leídos por CPU, CSA/CSD, reset, restore y primer bloqueo.

## Recibos Drive sin bytes de firmware

- [Inventario inicial](https://drive.google.com/file/d/1LItQYejiHSCXGutFfnyPNMB3xgns7yBE/view)
- [H6 previos aprovechados](https://drive.google.com/file/d/1YcnvjtT_Fp8MA5IRfPbcQ0tu-qXK4ALI/view)
- [Segundo inventario privado acotado](https://drive.google.com/file/d/1ia-2YmokYjWnkQC7kGcHvGCiMW18YO0N/view)
- [Estado segundo trabajo](https://drive.google.com/file/d/1HK1fdWli2P_xkHwNTVbt-5laSb28DOhm/view)

Fuentes de procedencia: [`SamDelorean/Dana-OS3K/docs/05-ROM-DANA-ACTUALIZADORES.md`](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/05-ROM-DANA-ACTUALIZADORES.md), y documento de cierre H8-A. Toda evidencia de firmware comercial permanece privada en T.
