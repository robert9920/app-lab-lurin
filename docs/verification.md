# Verificación · esquema 7

Ejecutada el **5 de octubre de 2026**. Solo se crearon y utilizaron las bases ficticias `lab_lc_v7_unit_test` y `lab_lc_v7_migration_test`; no se modificaron `lab_lc_v3`, `lab_lc`, AppControlHH, configuraciones privadas ni recursos Azure.

## Ajustes de Recepción e Informes — sin migración

Comprobados el **5 de octubre de 2026**, conservando el esquema 7 y las reglas operativas existentes.

| Comprobación | Resultado real |
|---|---|
| Backend / pytest | **68 pruebas aprobadas** en `lab_lc_v7_unit_test`, con rollback por prueba; cuatro nuevas cubren los conteos de recepción y la búsqueda de informes. La suite existente de carga, descarga, privacidad y permisos también pasa. |
| Recepción / PostgreSQL | Condiciones combinadas, conteos de una muestra una sola vez aunque tenga dos ensayos, dos técnicos con alcances distintos, filtros NOT_RECEIVED/issues/NO_OT, recepción conforme sin OT y exclusión de solicitudes canceladas/cerradas. `reception_counts` se devuelve solo con view=reception. |
| Informes / PostgreSQL | Búsqueda parcial por código o título sin distinguir mayúsculas; coincidencia solo en proyecto excluida. Proyecto independiente AND, versiones conservadas y acceso denegado a cliente ajeno o técnico sin asignación. |
| Frontend | **10 pruebas Vitest aprobadas**, ESLint sin errores ni advertencias y build Vite correcto (**1834 módulos**). |
| Python / contratos | Ruff y formato correctos en los archivos modificados. OpenAPI regenerado y comprobado: conteos de recepción y búsqueda de informes documentados; README y AGENTS actualizados. |
| Chrome / Playwright | Respuestas HTTP exclusivamente ficticias: indicadores combinados y Sin OT independiente, eliminación de status de enlaces antiguos sin restringir la primera consulta, reinicio de página, conservación de otros filtros, recarga/regreso y limpieza. Informes sin carga para ADMIN/MANAGER/TECH/CLIENT, búsqueda y proyecto separados, cero registros y carga conservada desde Documentos para MANAGER. Sin errores de React. |
| Revisión visual | Capturas de Recepción e Informes a **1560 y 390 px**, con registros y vacío, en `.local/review-reception-reports/`; inspección de indicadores compactos, paneles y tablas. |

Las primeras ejecuciones restringidas no pudieron iniciar esbuild ni gestionar temporales de pytest; se repitieron con permisos técnicos y finalizaron correctamente. La comprobación de navegador necesitó ajustar una espera de navegación, sin cambios adicionales de aplicación. No hay bloqueo local pendiente.

**Publicación pendiente:** volver a publicar `api` y `client` coordinadamente y comprobar recepción, búsqueda y descarga con los servicios Azure desplegados. Esta actualización **no requiere SQL, variables ni servicios nuevos**; no repetir SQL05 sobre una base ya en esquema 7. Las pruebas locales no verifican los recursos Azure. No se cambiaron dependencias ni las exclusiones de publicación.

## Resultados de estados y cancelación — esquema 7

| Comprobación | Resultado real |
|---|---|
| Backend / pytest | **64 pruebas aprobadas** sobre PostgreSQL ficticio, con rollback por prueba. Incluyen las pruebas anteriores adaptadas al cierre con un completado y siete casos nuevos v7. |
| Frontend / Vitest | **10 pruebas aprobadas**, cuatro archivos. Clasificación exclusiva, prioridad de cancelación/rechazo, singular/plural y distinción de muestras/ensayos. |
| Ruff / formato / ESLint | Sin errores; formato Python correcto. |
| Vite producción | Build correcto, **1834 módulos**; dist generado con el proxy conservado fuera de dist. |
| Conteos y filtros SQL | Las ocho categorías se concilian con listados/ficha/Work, decisiones mixtas y transición operativa. **125 solicitudes** ficticias verificadas: 100 filas en primera página, 25 en segunda y total completo, sin ampliación del técnico por filtros manipulados. |
| Permisos | Borradores exclusivos incluso cancelados; autor/jefatura pueden cancelar, ADMIN sin MANAGER y TECH no. Roles CLIENT+TECH mantienen resumen propio sin ampliar operaciones. Solicitud cancelada no admite comentarios ni acciones; desaparece de recepción/carga y del selector de destino de nuevos informes. |
| Cancelación y cierre | Motivo, versión y control de acceso; preservación de responsables, fechas, completados, rechazados e informes. Impresión de etiquetas sigue disponible después de cancelar. Cierre sin completados se rechaza incluso con informe y ensayos cancelados; cierre válido fija CLOSED y no permite cancelar. |
| SQL 05 | Cadena **3→4→5→6→7** en una base inicialmente vacía. También ejecución independiente de 6→7, bloqueo de repetición, conservación de cierre histórico sin completados y cancelación auditada de abiertos de rechazos globales antiguos. |
| Coherencia de esquema | Instalación limpia y migración coinciden en nombres, tipos, nulabilidad y defaults; **11 tablas, 96 campos**. Única nueva columna física: solicitudes.estado_general. No contadores persistidos ni ensayos ficticios. |
| Contratos/documentación | OpenAPI, diccionario README, AGENTS, Mermaid y SVG v7. Nuevos filtros assay_status/request_status, row_kind informativo y conteos documentados; parámetros antiguos conservados. |
| Chrome / Playwright | Respuestas HTTP **sintéticas**, sin datos reales: conteos en listado/ficha, ocho opciones iguales en ambas vistas, selección múltiple, recarga/regreso/URL y limpieza. Botones centrados en cuatro vistas a **1560 y 390 px**. Filas sin ensayos no seleccionables; rechazo sin doble estado. Sin errores de React. Capturas locales revisadas, incluido SVG. |
| Exclusiones | .gitignore y .funcignore conservan exclusiones de secretos, cachés, entornos, PDF y pruebas. El módulo services/statuses.py sí se incluye al publicar API. No fue necesario cambiar las exclusiones. |

La primera ejecución restringida encontró errores de permisos al iniciar esbuild y gestionar temporales pytest. Las comprobaciones finales se ejecutaron con autorización técnica y terminaron correctamente; no queda un bloqueo de validación local.

**Pendiente en Azure:** respaldar, aplicar solo 6→7 cuando la base esté en versión6, publicar API/client coordinadamente y repetir pruebas de aceptación con identidad Blob, proxy y PostgreSQL desplegados. El navegador sintético no sustituye una prueba integrada contra los servicios Azure ni se ha realizado un despliegue en esta entrega. La compilación no prueba esa infraestructura. Véase deployment.md.

## Historial de comprobaciones — esquema 6

Ejecutada el **2 de octubre de 2026**, con PostgreSQL y servidores locales aislados. Se conservaron `lab_lc_v3`, `lab_lc`, AppControlHH y la configuración privada original. No se publicaron cambios ni se modificaron recursos Azure.

## Resultados de esta actualización

| Comprobación | Resultado |
|---|---|
| Backend / pytest | **57 pruebas aprobadas**, con rollback por prueba sobre `lab_lc_v6_unit_test`. |
| Frontend / Vitest | **8 pruebas aprobadas**. |
| Chrome / Playwright | **8 recorridos aprobados**: cuatro nuevos v6 y cuatro de regresión v5, contra Functions 7072 y Vite 5174 aislados. |
| Ruff / ESLint | Sin errores. |
| Vite producción | Compilación correcta, **1833 módulos**; paquete dist generado. |
| SQL 05 | Cadena 3→4→5→6 en `lab_lc_v6_migration_test`. Conversión de aprobado=true/false a APPROVED/PENDING, sin modificar estados operativos, técnicos, fechas ni identidades. |
| Integridad de migración | Tipos, nulabilidad y defaults coinciden con instalación limpia. Once tablas, 95 campos. Repetir 5→6 se rechaza. Se conserva la prueba de rollback de cantidades históricas incompatibles con 3→4. |
| Contratos y documentación | README/diccionario, Mermaid, SVG y **30 rutas** OpenAPI actualizados a esquema6. Inventario de **92 reglas tipográficas** con variables, selectores y líneas. |
| Publicación | **27 archivos** del backend admitidos por .funcignore; sin settings privados, entornos, cachés ni pruebas. Fuentes, adaptador de proyectos y certificados públicos incluidos. Las exclusiones de VS Code del frontend conservan fuentes/proxy/lockfile y excluyen dependencias locales, pruebas y secretos. |
| Revisión visual | Capturas inspeccionadas de cabecera a 768 y 390 px, revisión individual y rechazo visible al cliente a 1440 px, más render del SVG. Sin truncamiento de nombre/empresa ni desbordamiento horizontal global en móvil. |

Cobertura funcional nueva: nombre y empresa de sesión/login; avisos repetidos reinician el plazo de 5s + 500ms; mensajes de celdas desaparecen y marcas inválidas permanecen. Fallo de consulta conserva su estado tras ocultar el aviso y ofrece reintento, sin rueda infinita. Flechas de sacos suman 1 y peso suma 0.1; escritura manual 0.025 se conserva y al incrementar resulta 0.125, sin stepMismatch.

Las cuatro listas limpian filtros, página y búsquedas de selectores manteniendo la sección. Solicitudes muestra creación en Lima. El filtro separado de definición ya no aparece; En revisión incluye solicitudes APPROVED con ensayos pendientes y Pendiente de ensayos incluye muestras sin ensayos de solicitudes abiertas. Selección múltiple, URL, solicitante/empresa y privacidad conservan los controles de regresión.

Revisión comprobada: decisiones distintas en una transacción, motivo obligatorio al rechazar, no seleccionados pendientes, aprobado continúa disponible y rechazado no admite operaciones. Motivo e historial públicos legibles para el autor, con actor/fecha; no se expone JSON de auditoría. Reenvío conserva ID, limpia la revisión actual y conserva el motivo anterior en historial. Todos rechazados lleva a OBSERVED; reenvío vuelve al estado de envío. Cierre con rechazo resuelto funciona si el trabajo aceptado está resuelto, no faltan ensayos por definir y hay informe.

Seguridad y concurrencia: revisión solo MANAGER, administrador sin ese rol denegado; reenvío solo CLIENT autor, cliente ajeno y técnico denegados. Identificadores externos, lotes incompatibles y duplicados se rechazan sin escritura parcial. Revisiones ya decididas no se modifican; versiones obsoletas generan conflicto. La suite conserva aislamiento de borradores/técnicos, sesiones, PDF y agregados superiores a cien solicitudes.

Bases ficticias de esta entrega: `lab_lc_v6_unit_test`, `lab_lc_v6_test`, `lab_lc_v6_migration_test`. Se pueden eliminar después de revisar; no son bases operativas. Capturas en `.local/review-v6/`, excluidas de publicación. No se cambiaron dependencias: las auditorías históricas más abajo no se presentan como consultas nuevas.

## Pendiente después de publicar

- En una base en versión5, aplicar **solo la nueva sección 5→6** del SQL05; confirmar versión6 y publicar api/client coordinadamente. No ejecutar 01 ni todo el SQL05 sobre esa base. No se requieren nuevas variables ni servicios Azure.
- Comprobar en Azure login/proxy, cookies, filtros, revisión mixta/reenvío y descargas privadas con cuentas autorizadas. No se han ejecutado comprobaciones sobre recursos desplegados.
- Los datos reales de nombres no se editaron. Si el nombre registrado contiene «cliente interno» o similar, el administrador debe editarlo para mostrar únicamente el nombre deseado.
- La impresión física y el zoom nativo 80% continúan con las limitaciones de la revisión histórica; esta actualización no modifica el diseño de etiquetas.

---

# Registro histórico · esquema 5

Ejecutada el **2 de octubre de 2026**, con PostgreSQL local, Azure Functions local y cuentas ficticias. Se conservaron `lab_lc_v3`, las configuraciones privadas originales y los datos de Azure. No se publicaron cambios.

## Resultados de esta actualización

| Comprobación | Resultado |
|---|---|
| Backend / pytest | **49 pruebas aprobadas** en `lab_lc_v5_unit_test`, con rollback por prueba. |
| Frontend / Vitest | **8 pruebas aprobadas**. |
| Chrome / Playwright | **4 recorridos aprobados** contra Functions 7072 y Vite 5174 aislados. |
| Ruff / ESLint | Sin errores. |
| Vite producción | Compilación correcta, 1829 módulos. |
| SQL 05 | Actualización aislada 3→4→5; aprobado se incorpora sin alterar estados, técnicos ni fechas existentes. |
| Integridad de migración | Columnas, tipos, nulabilidad y valores predeterminados coinciden con instalación limpia. Repetir la actualización es rechazado. Se conserva la prueba de rollback de cantidades históricas incompatibles con 3→4. |
| Documentación | Once tablas y **95 campos**; README, Mermaid, SVG y **28 rutas** OpenAPI regenerados desde el esquema instalado. Inventario CSS con **91 reglas de tamaño**, sus variables, selectores y líneas. |
| Interfaz | Inspección de tablas y filtros, formulario externo compacto, resultados vacíos, acciones al seleccionar, revisión de ensayos y logo/pie. Vistas 1440, 1024 y 768 px; vista cliente a 100 % y simulación CSS de escala 80 %. |
| Etiquetas | OT inferior izquierda con separador; ausencia de OT indicada con raya. Lotes de 1, 8 y 9, tamaño A4 y dos páginas para nueve etiquetas comprobados. PDF renderizado para inspección visual. |

Cobertura nueva: aprobación parcial con otra muestra sin ensayos; edición específica de selecciones no aprobadas; rechazo de eliminación de ensayos aprobados, operaciones sobre ensayos sin aprobar y versiones obsoletas; segunda aprobación que conserva el inicio del trabajo previo; cierre bloqueado por muestras pendientes. Se mantienen las comprobaciones de permisos, privacidad de borradores, aislamiento de técnicos y agregados sobre más de cien solicitudes.

Filtros verificados: opciones autorizadas por solicitante/empresa, búsqueda sin distinguir mayúsculas, selección con teclado, etiqueta conservada al recargar, estados múltiples y fechas inclusivas de Lima en servidor. Cliente externo sin filtro de proyecto; carga visible y vacío diferenciado. Coordenadas opcionales independientes, decimales válidos y límites de dígitos incorrectos cubiertos por pruebas.

Bases ficticias creadas: `lab_lc_v5_unit_test`, `lab_lc_v5_test` y `lab_lc_v5_migration_test`. Pueden eliminarse después de revisar los resultados; no son las bases operativas. Las capturas y PDF de comprobación están en `.local/review-v5/`, excluido de publicación. No se cambiaron dependencias ni la configuración de Azure; las auditorías históricas de dependencias que siguen abajo no se presentan como consultas nuevas.

## Pendiente después de publicar

- Aplicar **solo la nueva sección 4→5** de SQL 05 si la base ya está en versión 4; publicar API y frontend coordinadamente y comprobar la versión 5. No ejecutar el esquema de instalación sobre una base existente.
- Comprobar en Azure login/proxy, filtros, aprobación parcial, PDF privado y permisos con cuentas reales autorizadas. Las pruebas locales no validan recursos desplegados.
- Confirmar en una impresora física A4, escala 100 %, sin ajuste automático, las medidas de etiquetas. La revisión al 80 % usó escala CSS en Chrome; queda pendiente contrastarla con el zoom nativo del navegador del equipo de destino.

---

# Registro histórico · esquema 4

Ejecutada el **1 de octubre de 2026**, hora de Lima, con PostgreSQL local y datos ficticios. No se publicaron paquetes ni se modificaron recursos o datos en Azure. La base local existente lab_lc_v3 y su local.settings.json privado se conservaron.

## Resultados ejecutados

| Comprobación | Resultado |
|---|---|
| Backend / pytest | **36 pruebas aprobadas** en lab_lc_v4_unit_test; transacciones rollback. |
| Frontend / Vitest | **8 pruebas aprobadas**, incluidos pegado con calicata vacía, campos opcionales y payloads explícitos. |
| Chrome / Playwright | **7 recorridos aprobados**, contra API Functions real 7072 y Vite 5174 en entorno separado. |
| Ruff / ESLint | Sin errores ni advertencias de lint. |
| Vite producción | Build correcto; 1826 módulos, CSS y JS generados. |
| Servidor construido | Arranque en NODE_ENV=production, healthz, recarga de ruta SPA y cabeceras comprobados sin llamar Azure. |
| Publicación y limpieza | 26 archivos admitidos por el filtro .funcignore, incluido services/projects.py y certificados públicos; sin settings privados, entornos ni pruebas. Retiradas 26 carpetas de caché/copia temporal; fuentes, dependencias, dist y PDF reales conservados. |
| Esquema nuevo | SQL 01/02/03 sobre bases ficticias vacías; once tablas. |
| Migración SQL 05 | Versión 3→4; conservación de IDs, empresa y código antiguo; cantidades no convertidas; pesos nuevos NULL. |
| Fallo de migración | Sacos fraccionarios abortan; rollback deja versión3 sin columnas nuevas. Repetir 05 después de éxito es rechazado. |
| Coherencia | Columnas/tipos/nulabilidad/defaults de migración idénticos a instalación limpia; README con **94 campos**, Mermaid/SVG y **26 rutas** OpenAPI. |
| Catálogo AppControlHH | Consulta real de solo lectura en local: nueve proyectos; búsqueda por código sin distinguir mayúsculas y validación al crear en el recorrido. Búsqueda por nombre y fallo de origen cubiertos en backend. |
| PDF / visual | Acta con sacos y peso recibidos separados, etiqueta y diagrama renderizados e inspeccionados. Dimensiones/paginación 1/8/9 etiquetas e IDs autorizados cubiertos por backend. |
| Dependencias Python | pip-audit de versiones fijadas: sin vulnerabilidades conocidas en esta consulta. |
| Dependencias Node | npm audit: **dos paquetes con avisos**; uno en desarrollo y uno en producción, descritos abajo. |

Bases creadas solo para esta entrega: lab_lc_v4_test (recorridos), lab_lc_v4_unit_test (unitarias) y lab_lc_v4_migration_test (actualización aislada). Se pueden eliminar posteriormente sin afectar lab_lc_v3 ni AppControlHH. AppControlHH solo se leyó; no se añadieron proyectos ni permisos en esa base.

## Cobertura

- Cuentas manuales, edición de nombre/correo/teléfono/empresa/roles/activo, contraseña y revocación; último administrador protegido; empresa interna única y editable.
- Solicitudes propias del cliente, borradores privados y dos técnicos compartiendo solicitud: muestras/ensayos, recepción, documentos, actas, etiquetas, historial y métricas según asignación.
- Solicitud interna con **33 muestras**, envío sin ensayos y coordenadas vacías. Recepción parcial insuficiente con sacos/peso; OT manual antes de recepción completa; agregar ensayos conserva IDs, cantidad declarada y peso recibido. Aprobación y asignación posteriores, PDF inmediatamente disponible.
- Solicitud externa sin selector; código EXTERNO impuesto en servidor. Códigos forjados, muestras de otra solicitud, transiciones inválidas y conflicto de versión rechazados.
- OT bloquea asignar/iniciar/retomar nuevos; material no conforme bloquea ejecución. Observar/completar trabajos históricos ya iniciados no requiere inventar una OT. Lotes incompatibles revierten de forma atómica.
- Dashboard y filtro NOT_RECEIVED concuerdan sobre recepciones pendientes, incluidos envíos WAITING_ASSAYS; agregado sobre más de cien solicitudes y límites del técnico.
- Navegación directa, recarga y regreso con filtros; contraste del inicio cliente; tabla horizontal, paneles derechos, paginadores y vista de tablet. Datos de PDF renderizados legibles; no se probó una impresora física.
- manage.py migrate acepta esquema4 sin reinstalar ni cambiar solicitudes existentes. scripts/verify_migration.py permite repetir la comprobación SQL únicamente sobre una base ficticia vacía prevista, nunca elimina datos existentes.

Las primeras ejecuciones necesitaron permisos ampliados del entorno para temporales/procesos auxiliares. Hubo ajustes a las esperas y selectores de pruebas E2E durante el desarrollo; el resultado final es siete aprobadas. Poppler avisó de su fuente Symbol de sustitución; acta y etiqueta se renderizaron y sus textos se inspeccionaron correctamente. No hay un bloqueo actual de aprobación pendiente.

## Avisos de dependencias, sin cambios de versión

- **brace-expansion 1.1.18**, transitiva de ESLint/minimatch: aviso de severidad alta en herramientas de desarrollo.
- **ip-address 10.7.0**, transitiva de express-rate-limit 8.7.0: aviso moderado presente también con `npm audit --omit=dev`.

No se aplicó actualización automática ni se cambió el servidor proxy/dependencias de producción, conforme al alcance solicitado. Estos avisos siguen pendientes de una actualización separada y validada; la auditoría no equivale a certificar seguridad ni demuestra que la aplicación sea explotable. La entrega no afirma cero vulnerabilidades Node. Reconsultar audit antes de publicar, pues los avisos cambian.

## Pendiente en los recursos reales

Aplicar SQL05 con respaldo/mantenimiento en lab_lc y lab_lc_v3, configurar PROJECTS_DATABASE_URL privado y permisos SELECT reales, marcar empresa interna y desplegar ambos paquetes. Comprobar allí TLS/CA, conectividad a AppControlHH, login/cookies/CSRF, carga y descarga Blob con identidad administrada, red privada cuando corresponda y restauración coordinada PostgreSQL/PDF. Las pruebas locales no verifican esos recursos Azure.

## Reproducción

Pruebas unitarias: preparar una base ficticia vacía con 01/02/03, configurar TEST_DATABASE_URL privado (nombre permitido: lab_lc_v4_unit_test) y ejecutar pytest desde api. No utilizar lab_lc ni lab_lc_v3. Frontend: npm run lint, npm test, npm run build. E2E: LAB_E2E_URL y contraseñas ficticias en LAB_E2E_PASSWORD / LAB_E2E_CLIENT_PASSWORD / LAB_E2E_TECH_PASSWORD; npm run test:e2e desde client, con catálogo origen accesible.

Para SQL05: crear lab_lc_v4_migration_test vacía, configurar TEST_MIGRATION_DATABASE_URL y ejecutar python scripts/verify_migration.py desde la raíz. El comprobador deja los registros ficticios verificados y rehúsa una base ya usada; preparar otra instalación vacía bajo ese nombre para repetir. No hay contraseñas universales en SQL ni en pruebas.
