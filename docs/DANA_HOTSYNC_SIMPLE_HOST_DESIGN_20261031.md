> **SUSTITUIDO / HISTORICO (2026-10-31):** el usuario descarto el menu HotSync/PRC/PDB y el protocolo Palm DLP como objetivo del proyecto. La directriz vigente es acreditar USB Computer para la futura suite NEO Manager con OS3K-Dana. Consultar [alcance USB Computer](USB_COMPUTER_OS3K_PC_VALIDATION_20261031.md). Esta propuesta se conserva solo por valor historico, no es trabajo activo.\n\n# Dana HotSync: gestor sencillo de instalación y respaldo en MAME

**Corte 2026-10-31. Investigación y contrato de integración. NO IMPLEMENTADO; NO HOTSYNC PASS.**
Repositorio único DANA-emu/main; único ejecutable runtime/diag/bin/dana-diag. No cambiar la ROM original, no ramas, no segundo emulador.

## Necesidad del usuario y experiencia

Menú MAME **HotSync** similar en sencillez al selector de archivo/salida de la impresora AS2K:

| Opción | Función real |
| --- | --- |
| Instalar aplicaciones/bases... | Elegir uno o varios archivos PRC/PDB, validar y poner en cola para la próxima sesión HotSync auténtica de Palm OS. |
| Carpeta de exportación... | Seleccionar el directorio del host donde se respaldarán bases de datos y documentos. |
| Respaldar bases disponibles | Recuperar bases por protocolo DLP sin modificación de la RAM invitada ni archivos host. |
| Estado / registro | Ver conexión, enumeración, transferencia, errores, bytes y resultados por archivo. |

Los archivos .rom/.img de Flash o imágenes SD no son paquetes HotSync PRC/PDB; conservar los selectores de firmware y -sd1/-sd2 existentes. AlphaWord puede requerir un conduit específico para RTF: primero respaldar PDB original, luego convertir RTF sólo con un convertidor comprobado; no confundir PDB con RTF.

## Programas y algoritmos originales

**Dana:** aplicación HotSync de Palm OS, activable por Fn+Sync, USB Computer; driver USB residente con endpoint 0 y bulk.
**PC/Mac original:** Palm Desktop + HotSync Manager, con conduits Install (PRC/PDB), System (respaldo) y AlphaWord (documentos/formato). No es necesario copiar Palm Desktop.
**Protocolos:** capa USB y protocolo Palm de conexión y bases: CMP, SLP/PADP según el transporte realmente observado, DLP para listar/crear/leer/escribir bases y registros. El uso de SLP serial no debe presumirse idéntico en el enlace USB; validar descriptores y bytes de los endpoints.

Fuentes verificadas:
- Manual Dana HotSync https://www.manualslib.com/manual/4096958/Alphasmart-Dana.html?page=172
- Manual conduits https://www.manualslib.com/manual/4096958/Alphasmart-Dana.html?page=175
- Arquitectura Palm https://palm.wiki/development/docs/601/PalmOSCompanion2/SerialCommunication.html
- pilot-link https://github.com/desrod/pilot-link/blob/main/README.md
- pilot-link DLP https://github.com/desrod/pilot-link/blob/main/libpisock/dlp.c
- pilot-link USB https://github.com/desrod/pilot-link/blob/main/libpisock/usb.c
- pilot-link CMP https://github.com/desrod/pilot-link/blob/main/libpisock/cmp.c
- pilot-link PADP https://github.com/desrod/pilot-link/blob/main/libpisock/padp.c
- pilot-link SLP https://github.com/desrod/pilot-link/blob/main/libpisock/slp.c
- pilot-link instalación/backup https://github.com/desrod/pilot-link/blob/main/src/pilot-xfer.c

Biblioteca libpisock LGPL y herramientas pilot-xfer GPL: evaluar enlace legalmente correcto o reimplementar un subconjunto de protocolo desde especificación, sin copiar GPL en MAME BSD. USB de pilot-link supone dispositivo USB físico/libusb; NO conecta directamente al transporte DUSB de MAME.

AS2K reutilización exclusivamente de patrón de menú/selección, sin hardware AS2K: SamDelorean/AS2K-Emulator, stable/frontend/as2k_ui.py::_choose_file y stable/frontend/as2k_session.py.

## Estado del hardware existente y bloqueo exacto

Commit ISP1161 ya integrado 95d44db: src/mame/skeleton/isp1161_dana.h, isp1161_usb.h, isp1161_ptd.h, isp1161_link.h y alphasdana.cpp. Existe Device Controller con SRAM, EP0, bulk, IRQ2, DMA de diagnóstico y un enlace local USB packet-level DUSB v1, ya utilizable con -usbcomputer y socket.127.0.0.1:PORT; tests/isp1161_virtual_host.py. NO REHACER CONTROLADOR.

La ROM original de Palm UK1.5 abre la aplicación HotSync, pero el caso instalado local-evidence/runtime-compare/usb-20261030/installed-hotsync/probe.json declara original_device_softconnect=false, hotsync_e2e=PENDING, sin bloqueos físicos. El log sólo observó inicialización Host ISP1161, no inicialización Device antes del error Cable. La emulación diagnóstica de DC sí PASS; NO sustituye prueba del Palm auténtico.

Rutas original ROM estudiadas antes con Ghidra: 102DD74E -> 102DFAB8 (USB virtual driver open/connect), 10081A7A y 102DE138 (DC ConnectSetup), 100824FA y 102DEFFA (SETUP), 1007CEF6 -> 10081732 (IRQ2), 102DFD86 (ISR). Comprobar ruta real de Fn+Sync y selección local/USB, evento VBUS/PG3, configuraciones de placa, códigos de error y notificaciones de conexión ANTES de añadir DLP. No forzar SoftConnect, inyectar bytes al sistema invitado ni parchear la ROM.

Intento nuevo Ghidra read-only 2026-10-31 falló ANTES del script al abrir proyecto original por error interno Disk quota exceeded, pese a espacio libre en filesystem. No hay nuevos hallazgos Ghidra; evidencia previa conservada. No borrar proyectos originales.

## Diseño de integración: una sola función HotSync del emulador

Menú MAME -> cola de instalación, carpeta de salida y estado.
Servicio anfitrión de protocolo Palm (reutilizar libpisock LGPL si es compatible; alternativa DLP mínima independiente verificada).
Conectar servicio mediante el enlace DUSB ya implementado -> controlador ISP1161 Device existente -> ROM Palm original.
Ningún acceso directo del host a bases invitadas, RAM, traps ni framebuffer para inventar éxito. Si se implementa un helper de protocolo por licencias, debe lanzarse/gestionarse desde el MISMO producto DANA-emu, nunca como segundo emulador ni usuario forzado a instalar Palm Desktop.

**Orden funcional para cierre, sin declarar PASS por etapas aisladas:**
1. La ROM original activa USB DC SoftConnect con su propio comando y descriptores, enumera por SETUP, SET_ADDRESS, SET_CONFIGURATION y bulk con host auténtico. Confirmar correctamente VBUS, modo USB Computer, transporte y endpoint.
2. Negociar sesión Palm y DLP mediante el mismo enlace y la aplicación HotSync invitada; leer información del Dana y listado de bases. Sólo entonces protocolo PASS.
3. Instalar un PRC/PDB elegido desde el menú vía DLP y comprobar existencia y persistencia tras reinicio; rollback/errores.
4. Exportar un PDB válido al directorio elegido desde el menú, luego respaldo completo, manifest de nombres, tipo/creator, tamaño, hash y estado, archivo temporal/rename atómico.
5. AlphaWord PDB a RTF sólo si el algoritmo y casos de formato se acreditan. Menú simple sin instalación de Palm Desktop, selector de archivos/dir, progreso, cancelación y log.
6. Regresiones completas USB Host/impresora/Device, teclado, RTC, audio, SD y pantalla; actualizar Excel rector único e informe USB, compilar/instalar sólo dana-diag y sincronizar main.

**Seguridad:** no sobrescribir archivos host ni bases originales sin confirmación; sanear nombres/rutas procedentes de Palm, validar cabeceras PRC/PDB, límites de longitud, no auto-conectar USB externos. Un save-state obliga a reconectar sesión host. No sincronizar datos con servicios externos.

**Estado final en esta revisión:** INVESTIGADO / CONTRATO DOCUMENTADO / IMPLEMENTACIÓN DE MENÚ Y DLP PENDIENTES / ORIGINAL PALM USB COMPUTER PENDIENTE. Sin nueva compilación, pruebas nativas ni cambios de código. ISP1161 integral permanece OPEN/PARTIAL.
