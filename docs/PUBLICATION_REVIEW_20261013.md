# Revisión previa a la publicación de DANA-emu — 2026-10-13

**Ámbito auditado:** repositorio `SamDelorean/DANA-emu`, revisión de partida `43a88dfdbe0dd6ca02fda1b02d830c77785082fb`, rama principal `main`. Esta revisión documenta hallazgos técnicos; **no constituye dictamen legal ni autoriza a copiar obras ajenas**.

## Inventario y resultado

- Se revisaron los **10 archivos de texto** del árbol principal (README, ocho documentos en `docs/` y `research/sources.lock.json`). No se encontraron fuentes C/C++ propias o ajenas, firmware, imágenes de ROM, ejecutables, claves privadas, tokens identificables ni datos de dispositivo volcados.
- Se inspeccionaron los cambios de **24 commits**, cuya lista de archivos queda dentro de ese conjunto documental; ninguna revisión introdujo binarios o firmware. Al momento de la auditoría se observó sólo `main`, sin pull requests ni versiones publicadas.
- La búsqueda estructurada de formatos comunes de credenciales en el contenido y los diffs históricos no encontró coincidencias. **Ninguna búsqueda automática garantiza ausencia absoluta de material confidencial.**
- El manifiesto `research/sources.lock.json` contiene rutas de referencia, enlaces GitHub, commits y notas de licencias; **no contiene archivos fuente descargados ni material de ROM**.
- Las referencias a `Dana-OS3K` apuntan a **otro repositorio privado**. Hacer público DANA-emu **no** hará público Dana-OS3K. Los enlaces hacia éste pueden mostrar un error a visitantes sin acceso.
- `docs/WORKFLOW_AS2K.md` nombra rutas locales de la máquina T, incluido un directorio de usuario. No se identifican secretos en esas rutas, pero permanecerán visibles en el historial si se cambia la visibilidad de este repositorio en el mismo lugar.
- GitHub hace visible también el historial, metadatos de commits, futuras ejecuciones de Actions y sus logs; los lectores podrán clonar y crear forks.

## Propiedad intelectual y distribución

1. **Diseño documental actual:** referencias técnicas, datos observables de hardware, nombres de registros y enlaces no equivalen a incorporar archivos protegidos de otra implementación. Esto no prueba por sí mismo la originalidad de cada frase ni elimina los derechos de sus autores.
2. **MAME:** el proyecto completo se distribuye como GPL-2.0-or-later y muchos archivos están bajo BSD-3-Clause. Antes de incorporar o distribuir componentes concretos se debe revisar **la cabecera SPDX/licencia de cada archivo**, sus avisos y las obligaciones de la distribución combinada. La marca MAME y su logotipo no son marcas propias. Documentación: https://docs.mamedev.org/license.html
3. **EmuTOS-Dana y POSE/Retro68:** se citan como referencias GPL. No copiar ni combinar su implementación directamente sin revisar licencia compatible, derechos y obligaciones. **Neo-re, cuya licencia está pendiente de verificar, se mantiene como referencia técnica, no como código reutilizable automáticamente.**
4. **ROM/firmware comercial AlphaSmart/Palm:** no publicar archivos originales, imágenes de Flash, dumps, bytes extraídos de actualizadores, firmware modificado derivado de software propietario o datos de usuarios/dispositivos. Que un binario pueda ejecutarse en un emulador no concede derechos para redistribuirlo.
5. **Marcas y afiliación:** AlphaSmart, Dana, Palm, MAME y otros nombres se usan únicamente con sentido descriptivo técnico. Este proyecto independiente no afirma respaldo de sus titulares.
6. **Ausencia de LICENSE:** al auditar no existía `LICENSE`. Publicar la documentación **no concede automáticamente una licencia de software libre**; sin licencia explícita, la reutilización por terceros queda sujeta a los derechos de autor aplicables. La eventual licencia del código propio debe elegirse separadamente, una vez determinado qué fuentes externas se incorporarán. Fuente: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

## Criterios obligatorios antes de añadir nuevos archivos

- No introducir credenciales, tokens, configuraciones privadas, rutas con secretos o información de terceros sin consentimiento.
- No almacenar en Git ROM/Flash/firmware comercial, snapshots o medios que contengan datos reales, ni archivos binarios compilados protegidos.
- Cada archivo de terceros que se incorpore debe declarar procedencia, copyright, licencia y obligaciones de distribución, y ser jurídicamente compatible con el destino; referenciar un enlace no equivale a autorización de copia.
- Aplicar el `.gitignore` conservador de la raíz como primera protección, **sin confiar en él para eliminar contenido ya comprometido al historial**.
- Auditar los workflows de Actions **antes** de publicarlos: no imprimir secretos en logs ni subir artefactos protegidos, y usar permisos mínimos de `GITHUB_TOKEN`.

## GitHub Actions — realidad de los costos

A fecha de esta revisión, los **GitHub-hosted runners estándar** de Actions son gratuitos para repositorios públicos. **Los runners grandes siguen facturándose**, y la capacidad de almacenamiento de artefactos/cache sigue su política de cuotas y cobros. El cambio de visibilidad no da uso gratuito ilimitado de Copilot, Codex ni de toda función premium de GitHub. Documentación oficial: https://docs.github.com/en/billing/concepts/product-billing/github-actions

En el árbol auditado **todavía no hay workflows `.github/workflows/`**: el repositorio no empezará a compilar o comprobar automáticamente por sólo volverlo público. Habrá que añadir primero tests o workflows apropiados para cada incremento, preservando la ejecución funcional en T cuando sea obligatoria.

## Revisión de visibilidad

Esta nota y el `.gitignore` preparan la publicación, pero **no modifican la visibilidad**. Confirmar después en GitHub que `visibility = public`, y revisar los logs e historial expuestos. Un cambio posterior de público a privado **no retira forks o copias ya obtenidas**.

## Punto técnico de continuidad

El plan autoritativo sigue siendo `docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md`: D0.1 documental `SPEC_READY`, próximo incremento **D0.2 (equivalencia MC68328/EZ/VZ)**. Esta auditoría no ejecutó Commander, no compiló el emulador ni cerró ninguna prueba de hardware.
