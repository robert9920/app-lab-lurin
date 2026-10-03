# Guía de desarrollo · Laboratorio Lara Consulting · esquema 6

## Alcance y trabajo

client: React JavaScript/Vite/Tailwind. api: Python 3.12/Azure Functions HTTP blueprints, SQLAlchemy y PostgreSQL. No sustituir persistencia por SQLite/memoria. No se requieren agentes adicionales. Conservar Referencia, configuraciones privadas, archivos PDF y cambios ajenos. No desplegar ni modificar bases reales sin autorización explícita; SQL de actualización se entrega para ejecución controlada.

La instrucción del usuario reemplaza Entra de la skill azure-fullstack-entra-postgres: contraseña Argon2id, sesión opaca y CSRF. No reintroducir MFA, Fernet, correo, invitaciones, activación ni JWT. Blob usa identidad administrada; autorización de usuarios sigue siendo propia.

## Datos y migraciones

Exactamente once tablas: empresas, usuarios, catalogo_ensayos, solicitudes, muestras, ensayos_muestra, informes, actividad, sesiones, limites_intentos y migraciones_esquema. Nombres físicos en español sin tildes, JSON compatible mediante schema_names.py. No traducción de SQL en runtime.

Local conserva lab_lc_v3; producción lab_lc. Esquema 6 independiente del nombre. 01 instala una base vacía; 05 contiene tres bloques: 3→4, 4→5 y NUEVA SECCIÓN 5→6. En versión5 ejecutar solo 5→6; en versión4, 4→5 y 5→6; en versión3, todo; en versión6 no repetir. No ejecutar 01 en una base existente. Respaldar y detener versiones anteriores antes de 05. manage.py migrate es una operación explícita; no migrar al importar Functions. El nuevo bloque sustituye aprobado por estado_revision y preserva el resto de los datos.

solicitudes.proyecto_id es texto: código del catálogo AppControlHH.public.proyecto(id_proyecto,nombre) o EXTERNO para nuevas externas. No FK ni copia del catálogo. empresa_id es snapshot necesario; no cambiarlo al editar usuario. Retirar proyectos/miembros_proyecto y toda asignación de proyectos.

Una única empresa interna activa como máximo; ADMIN la elige. PROJECTS_DATABASE_URL exclusivamente privado del backend, permisos SELECT de dos columnas, pool y timeout acotados, transacción READ ONLY. Caída del catálogo no bloquea login ni recursos existentes. Validar código al crear/cambiar un borrador interno; no revalidar códigos históricos solo al consultar.

Distrito/provincia/departamento obligatorios en formularios y API nueva; NULL histórico permitido sin inventar ubicación. Coordenadas este y norte siempre opcionales, números finitos opcionales; este seis y norte siete dígitos enteros, decimales admitidos. Validar coordenadas nuevas/modificadas; conservar históricos intactos. No añadir datum/zona no solicitados. Sacos entero positivo o NULL, peso kg positivo o NULL; datos recibidos separados. No reutilizar peso como cantidad ni convertir históricos automáticamente.

Una muestra mantiene identidad: no duplicarla al recibir. Declaración recibida protegida de edición/eliminación; ensayos añadibles antes de aprobación y, mediante edición específica, después de aprobar sin alterar ensayos ya aprobados ni muestras/cabecera. Mezclas en observaciones. Pareja muestra/ensayo única. historial/informes inmutables; documentos generados bajo demanda no añaden tablas.

## Reglas y permisos

- CLIENT solo redacta y accede a sus solicitudes, no a todos los clientes de su empresa ni a un proyecto entero. DRAFT exclusivo autor sin excepciones. TECH ve solicitudes con asignación, solo muestras/ensayos propios, informes de esas solicitudes. Roles acumulables conservan permisos expresos; CLIENT no amplía operaciones TECH.
- MANAGER global salvo borradores ajenos, aprueba/recibe/OT/asigna/cancela/retoma/cierra. ADMIN administra y consulta; para operar necesita rol adicional.
- Autor puede editar DRAFT/WAITING_ASSAYS/SUBMITTED/OBSERVED. Tras envío no cambia proyecto. Muestras recibidas conservan declaración e IDs. Edición con versión/bloqueo; lotes atómicos y bloqueos ordenados por UUID.
- Enviar sin todos los ensayos produce WAITING_ASSAYS. Completar selección pasa SUBMITTED. MANAGER revisa ensayos pendientes individualmente desde WAITING_ASSAYS/SUBMITTED/APPROVED, sin exigir ensayos en todas las muestras. Mezclar decisiones es atómico; rechazo exige motivo por ensayo. La primera aprobación lleva a APPROVED. Todos rechazados, sin aprobados ni pendientes, lleva a OBSERVED. Legacy approve devuelve409; no reintroducir aprobación global. Recepción MANAGER desde envío, TECH solo APPROVED y muestras propias. Corrección exige motivo; no invalidar material RUNNING/COMPLETED.
- codigo_ot manual por solicitud después de ≥1 muestra recibida, sin exigir recepción completa/conforme. Corrección con motivo. Cada ensayo nuevo empieza estado_revision=PENDING (APPROVED/REJECTED son decisiones). approved JSON se calcula. Solo MANAGER revisa y audita cada ensayo. CLIENT autor reenvía explícitamente rechazados con versión, conservando IDs e historial; OBSERVED vuelve a envío. No eliminar ni editar selecciones revisadas sin reenvío. Motivo/fecha/actor se conservan en actividad pública sin nuevas tablas. Ninguna acción operativa en ensayos no aprobados. Asignar/start/resume requieren APPROVED+OT; start/resume además técnico y material OK. Observar/completar RUNNING histórico se conserva sin OT.
- Asignación independiente de estado, sin ASSIGNED/booleano persistido. allowed_actions servidor autoritativo, intersección en selección masiva. Retomar MANAGER conserva inicio. Cancelar/reanudar motivo. COMPLETED/CANCELLED terminal.
- Informes PDF privados inmediato tras carga, tamaño/estructura/contenido activo verificados; mantener límites 20 MiB/500 páginas. No revisión ni espera. Nuevas versiones inmutables, carga en APPROVED. Cierre requiere muestras con ensayos definidos, sin revisiones pendientes, ensayos aceptados resueltos e informe. Rechazos resueltos no bloquean por sí solos.
- Etiquetas 95×68 mm, A4 2×4, separación 4 mm; datos declarados/recepción, código laboratorio único y recepción compartible. Solo recibidas/accesibles. Mostrar codigo_ot en esquina inferior izquierda, OT: — si falta. No añadir UR ni revisión.
- Dashboard agregación SQL completa por alcance, no resultados paginados. Recepción NOT_RECEIVED incluye enviadas pendientes de ensayos; TECH solo aprobadas propias. NO_OT independiente de material observado.

## Seguridad

Permisos de IDs en cada consulta, modificación y descarga. Perfil/roles/activo desde PostgreSQL por petición. Edición de usuario, contraseña o desactivación revoca sesiones; mantener ADMIN activo. Sesiones temporales distintas del historial.

No exponer hash_contrasena/hash_token/clave_archivo ni URL de conexiones. No logs de cookies/tokens/PDF/contraseñas. Notas internas filtradas; auditoría estructurada interna, descripción legible en UI. Validación central Pydantic extra=forbid y payloads por lista permitida.

APP_ENV=production exige HTTPS, PostgreSQL verify-full y Blob privado. Source URL verify-full en producción. Cookie Secure/HttpOnly/SameSite, Origin exacto/CSRF, límites de intentos persistidos. Sin credenciales del servidor en client, VITE_ ni almacenamiento de navegador.

## Arquitectura y comprobaciones

blueprints HTTP; services/workflow.py reglas; security.py alcance/sesión; services/projects.py origen de catálogo; storage.py archivos; documents.py PDF. Axios central, perfil/CSRF en memoria. URL conserva vista/filtros/pestaña/regreso seguro. Navegación superior, tabla y filtros/acciones a derecha; matriz horizontal editable.

Desde client: npm ci, npm run dev, npm run lint, npm test, npm run build. Desde api con entorno Anaconda Python3.12: pip install -r requirements-dev.txt, func start, pytest -q, ruff check/format acotados a código. No alterar local.settings.json privado para pruebas. TEST_DATABASE_URL solo base ficticia permitida; fixtures rollback. E2E cuenta privada ficticia. No contraseñas universales en SQL/código. Migración fixture schema_v3.sql solo pruebas.

scripts/export_contracts.py exporta desde esquema6 instalado (solo lectura) diccionario completo README, Mermaid, schema-columns y OpenAPI. Regenerar SVG y verificar visualmente. README explica cada campo, instalación y reglas; docs/deployment.md actualización/publicación/respaldos; docs/verification.md resultados reales y pendientes.

Revisar .gitignore, .funcignore y client/.vscode/settings.json de forma independiente. No publicar entornos Windows, cachés, .local, secretos ni PDF. Incluir lockfiles y certificados públicos api/certs. No alterar proxy/infra ya desplegada sin necesidad. Functions AuthLevel.FUNCTION; proxy privado App Service. No afirmar Azure verificado por pruebas locales.

## Presentación y contratos v6

Tipografía centralizada en variables --text-* de client/src/styles.css; inventario exacto de selectores en README. Usar Loading/NetworkLoading y distinguir vacío/error/carga. SearchSelect común, con teclado y opciones remotas paginadas; no extender el alcance autorizado en filtros. Cabeceras rojo claro, panel de filtros 320px en escritorio, sin columnas de acciones vacías ni alturas mínimas que desperdicien espacio.

Miembros de personal ven autor y empresa snapshot en las cuatro listas. Estados CSV usan OR; otros filtros AND. SUBMITTED filtra revisión pendiente en enviadas abiertas, incluidas APPROVED; WAITING_ASSAYS filtra alguna muestra sin ensayos en enviadas abiertas, incluidas APPROVED/OBSERVED. Excluir DRAFT/CLOSED/REJECTED de esos dos agregados. Quitar selector pending_assays pero conservar parámetro legacy. Fechas inclusivas Lima. Borrar filtros retira toda consulta y reinicia selectores/página sin cambiar vista. Cliente externo puro no ve proyecto. PUT /requests/{rid}/assays solo autor CLIENT sobre APPROVED y solo selecciones PENDING; POST /assays/review MANAGER; POST /assays/resubmit CLIENT autor. Versión, alcance y atomicidad en todos. No almacenar listas de estados ni flags derivados. Mantener once tablas.

Cabecera nombre completo/empresa, organization_name en login/sesión; no editar nombres existentes. useErrorNotice/ErrorBox: 5s + fade500ms, reinicio en cada error repetido. Estado de consulta separado del aviso; marcas inválidas hasta corregir. Coordenadas Este/Norte en mensajes y etiquetas. NumericInput sacos increment1, peso0.1, escritura manual sin redondeo. Solicitar ensayos reemplaza Completar ensayos.

Pruebas v6 en bases ficticias lab_lc_v6_unit_test, lab_lc_v6_test, lab_lc_v6_migration_test; no alterar bases operativas.
