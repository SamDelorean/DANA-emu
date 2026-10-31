# USB Computer del Dana: prueba de transporte para OS3K y NEO Manager

**Decision 2026-10-31: sustituye el plan de desarrollar HotSync de Palm y un menu PRC/PDB en MAME. DOCUMENTAL.**

## Objetivo
Validar que el ISP1161A1 Device Controller del Dana transmite y recibe datos con una PC mediante su USB Computer real, y preservar ese canal para OS3K-Dana, cuya futura meta es comunicarse con la suite original AlphaSmart Manager / NEO Manager. No es necesario implementar Palm Desktop, conductos Palm DLP ni interfaz propia de instalacion/exportacion.

## Pruebas existentes y limites
- ISP1161 HC: impresion original AlphaWord USB desde ROM Palm UK1.5 PASS, por la ruta Host (NO demuestra Device).
- ISP1161 DC: programa invitado 68000 diagnostico controla por MMIO EP0, descriptores, SETUP, IN/OUT, FIFO, IRQ2 y paquetes de ida y vuelta con host virtual DUSB; pruebas nativas PASS.
- El link -usbcomputer implementado actualmente es un socket local de paquetes DUSB, **no** una interfaz que enumere como dispositivo USB fisico ante Windows/Linux/macOS. El reconocimiento como periferico del SO anfitrion NO esta acreditado; se necesita puente gadget/USB adecuado y demostrado o ensayar un Dana fisico.
- Palm UK1.5 HotSync original: la prueba Cable no activo SoftConnect; sigue PENDING, pero no es requisito para validar el uso futuro con OS3K.
- INT2/VBUS/PG3 cableado PCB por medir; no confundir evidencias del driver original con continuidad de la placa.

## Dos modos NEO distintos
Manuales: https://www.daneel.franken.de/alphasmart.neo/ALSMUserManual.pdf y https://www.daneel.franken.de/alphasmart.neo/NEO1and2UserManual.pdf

1) USB Send como teclado: NEO emula el teclado de la PC, sin AlphaSmart Manager activo.
2) NEO Manager/AlphaSmart Manager: transferencia bidireccional de documentos, configuracion y SmartApplets sobre USB directo, protocolo de administracion propio. El protocolo especifico, los identificadores USB, interfaces y descriptores deben investigarse en ROM NEO y/o captura original antes de cualquier afirmacion de compatibilidad con la suite.

## Alcance MINIMO y responsables
- **DC-A / DANA-emu:** rutinas autenticas de DC ISP1161, EP0 y endpoints de datos, interrupciones, FIFO y paquetes bidireccionales de un invitado 68000: **PASS dentro del enlace de diagnostico DUSB**. No repetir pruebas cerradas.
- **DC-B / DANA-emu/hardware:** cuando sea imprescindible demostrar PC fisica, enumeracion mediante descriptores del firmware invitado y lectura/escritura de paquetes por el SO de la PC con un puente USB verificado o un Dana fisico: **NO VERIFICADO**. No inventar cableado ni prometer enumeracion nativa del socket DUSB.
- **NEO-C / Dana-OS3K:** tras adaptar OS3K, reutilizar el protocolo del NEO y probar que la suite AlphaSmart/NEO Manager identifica al Dana y ejecuta una transaccion real de lectura y escritura, con descriptores y controladores apropiados: **FUTURO / NO IMPLEMENTADO**. Este ultimo paso pertenece a OS3K-Dana, no es un defecto del hardware del emulador.
- PALM HotSync y DLP no constituyen gate del producto OS3K; conservar sus hallazgos solo como evidencia historica.

**Sin cambios de codigo, RAM, ROM, ejecutable, SDL, registro USB ni resultados PASS anteriores.** Una sola rama main y un unico dana-diag.
