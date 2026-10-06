# Laboratorio Lara Consulting · esquema 7

Aplicación de solicitudes, recepción, ensayos e informes. React JavaScript, Vite y Tailwind CSS en `client`; Python 3.12 y Azure Functions HTTP en `api`; PostgreSQL como persistencia real. Interfaz en español, fechas presentadas en America/Lima.

## Cambios y compatibilidad

Producción conserva la base **lab_lc** y local **lab_lc_v3**. Los nombres JSON existentes se conservan mediante api/schema_names.py (por ejemplo weight → peso, easting/northing → coordenada_este/coordenada_norte). El número del esquema, ahora **7**, es independiente del nombre de la base. No se requiere crear otra base para actualizar. Hay once tablas; se retiraron `proyectos` y `miembros_proyecto`. El proyecto es un código de texto en `solicitudes.proyecto_id`, sin FK entre bases. `empresa_id` conserva la empresa de la solicitud aunque después se cambie la empresa del autor.

El acceso sigue usando contraseña Argon2id, sesiones opacas y CSRF. El administrador crea usuarios y restablece contraseñas; no se envían correos ni enlaces. Sin MFA, invitaciones ni FERNET_KEY. Fernet cifraba secretos de funciones retiradas y nunca intervino en el hash de contraseñas. No se puede recuperar una contraseña del hash.

## Actualizar una instalación existente

1. Respaldar PostgreSQL y PDF y poner la aplicación en mantenimiento; detener versiones anteriores durante la actualización.
2. Verificar `SELECT current_database(); SELECT max(version) FROM migraciones_esquema;` en la base deseada: Azure **lab_lc**, local **lab_lc_v3**.
3. **Si la versión es 6, ejecutar SOLO la nueva sección 6→7** de `sql/05_actualizacion_solicitudes.sql`, desde «NUEVA SECCIÓN — Actualización de esquema 6 a 7: estados de solicitud y resumen de ensayos» hasta su COMMIT. No repetir secciones anteriores. En versión 5 ejecutar 5→6 y 6→7; en versión 4, 4→5, 5→6 y 6→7; en versión 3, el archivo completo. En versión 7 no repetir. No ejecutar 01 ni demo sobre una base existente.
4. Comprobar versión7. `solicitudes.estado_general` añade CREATED/CANCELLED/CLOSED; los rechazos globales históricos se convierten en cancelaciones y sus ensayos abiertos no rechazados se cancelan con historial. Preserva decisiones, resultados completados, técnicos, fechas, informes y cierres históricos. No añade tablas.
5. Publicar `api` y `client` coordinadamente y reiniciar. **No hay nuevas variables ni servicios Azure respecto al esquema 6**; conservar la configuración que ya funciona. `python manage.py migrate` reconoce 3/4/5/6/7 y es una alternativa explícita al SQL, no un paso adicional automático al publicar.
6. Probar conteos y filtros en Solicitudes/Trabajo, revisión y ejecución parcial, cancelación con motivo, cierre con un completado y PDF antes de reabrir. Para revertir, restaurar juntos respaldo de base y paquetes anteriores; no borrar archivos PDF.

Las cantidades existentes se conservan numéricamente como **sacos**; no se convierten a peso. Si hay cantidades fraccionarias o no finitas, 05 aborta antes de modificar el esquema: revisar con el laboratorio y corregir explícitamente antes de reintentar. Los nuevos pesos, geografía y OT quedan NULL en registros históricos; no se inventan valores. Al editar una solicitud histórica se deberán completar distrito, provincia y departamento. Las coordenadas este y norte permanecen opcionales, incluso al editar.

Las solicitudes existentes conservan su código de proyecto, incluido un código antiguo de un cliente externo. Las nuevas externas usan `EXTERNO`. Los ensayos ya RUNNING conservan observar/completar aunque su solicitud antigua no tenga OT; para nuevas asignaciones, inicio o reanudación se necesita OT.

## Instalación local con dos ventanas de Anaconda

Requisitos: Anaconda/Miniconda, PostgreSQL en ejecución, Python 3.12, Node.js 24 LTS y Azure Functions Core Tools v4. No se utilizan Docker, Azurite ni buzones de correo.

### Base vacía

En pgAdmin conectado a `postgres`, ejecutar `sql/00_create_database_local.sql` fuera de transacción. Cambiar a `lab_lc_v3` y ejecutar en orden `01_schema.sql`, `02_catalog.sql` y, solo para demostración, `03_demo.sql`. 01 instala directamente esquema 7. **No ejecutar 05 después de 01**, pues 05 actualiza instalaciones anteriores 3/4/5/6. `04_runtime_permissions.sql` concede permisos a una cuenta PostgreSQL limitada opcional, distinta de los roles de usuarios del portal; quien utilice una cuenta existente debe revisar sus permisos. En Azure, el SQL 00 oficial crea `lab_lc`.

### Ventana 1: backend

```bat
cd /d C:\Trabajo\Laboratorio\App\app-lab-lc\api
conda create -n lab-lc python=3.12 -y
conda activate lab-lc
python -m pip install -r requirements-dev.txt
```

Solo en instalación nueva, copiar `local.settings.example.json` a `local.settings.json`. **No sobrescribir el archivo privado existente**. Configuración local:

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "",
    "APP_ENV": "development",
    "DATABASE_URL": "postgresql+psycopg://USUARIO:CLAVE@localhost:5432/lab_lc_v3",
    "PROJECTS_DATABASE_URL": "postgresql+psycopg://LECTOR:CLAVE@localhost:5432/AppControlHH",
    "APP_ORIGIN": "http://localhost:5173",
    "STORAGE_MODE": "local"
  }
}
```

Las contraseñas PostgreSQL con caracteres reservados deben codificarse como componentes URL. No son las contraseñas de cuentas del portal. Ajustar host/puerto reales. Las variables del proceso prevalecen sobre local.settings.json; cerrar una ventana que contenga ajustes de otro entorno.

```bat
python manage.py migrate
python manage.py bootstrap
func start
```

`migrate` instala una base vacía o actualiza esquema 3/4/5 mediante los bloques correspondientes de 05; no lo ejecutar mientras la versión anterior esté sirviendo peticiones. `bootstrap` inicializa el administrador sin contraseña incorporada. Para datos ficticios: `python manage.py demo`, después `python manage.py password --email admin@example.com` y repetir para las cuentas a usar. `demo` rechaza lab_lc para proteger producción; si se desea una prueba pública con SQL ficticio, cargarlo manualmente y establecer contraseñas desde una ventana privada. Nunca cargar demostración sobre datos reales.

### Ventana 2: frontend

```bat
cd /d C:\Trabajo\Laboratorio\App\app-lab-lc\client
npm ci
npm run dev
```

Abrir **http://localhost:5173**. Vite reenvía `/api` a 127.0.0.1:7071. El origen debe coincidir exactamente con APP_ORIGIN; CORS no sustituye la protección de origen. Reiniciar ambos servidores al cambiar configuración o esquema.

### Variables privadas del backend

| Variable | Uso / valor |
|---|---|
| DATABASE_URL | Base de laboratorio: lab_lc_v3 local; lab_lc Azure. |
| PROJECTS_DATABASE_URL | Conexión de solo lectura a AppControlHH. Necesaria para seleccionar/validar nuevos proyectos internos. |
| APP_ENV | development local; production Azure. |
| APP_ORIGIN | Origen exacto del portal, sin ruta ni barra final. |
| STORAGE_MODE | local para desarrollo; azure obligatorio en Azure. |
| UPLOAD_DIR | Solo local: api/.local/uploads por defecto, fuera del frontend. |
| STORAGE_ACCOUNT_URL | Solo Azure: https://CUENTA.blob.core.windows.net. |
| STORAGE_CONTAINER | Contenedor privado lab-informes. |
| SESSION_IDLE_MINUTES | 30 por defecto. |
| SESSION_HOURS | 8 por defecto. |
| FUNCTIONS_WORKER_RUNTIME | python, para Functions local; runtime Flex configurado en el recurso. |
| AzureWebJobsStorage | Host de Functions; vacío en desarrollo exclusivamente HTTP, configuración propia en Azure. |

## Proyectos desde AppControlHH

El backend consulta **public.proyecto(id_proyecto, nombre)** mediante una segunda conexión, sin modificar esa base ni copiar un catálogo persistente. Las solicitudes guardan solo el código seleccionado. El selector muestra `id_proyecto - nombre`, busca por ambos sin distinguir mayúsculas y pagina resultados; un proyecto seleccionado se valida otra vez en el servidor. Los filtros de listas usan códigos de solicitudes existentes, sin depender del catálogo externo. El nombre externo no se congela ni se guarda como campo adicional en la solicitud.

La cuenta de lectura necesita CONNECT en AppControlHH, USAGE en public y SELECT en esas dos columnas. Ejemplo para un rol LOGIN existente `lector_proyectos`, ejecutado por el propietario conectado a AppControlHH:

```sql
GRANT CONNECT ON DATABASE "AppControlHH" TO lector_proyectos;
GRANT USAGE ON SCHEMA public TO lector_proyectos;
GRANT SELECT (id_proyecto, nombre) ON TABLE public.proyecto TO lector_proyectos;
```

No ejecutar estos GRANT sin sustituir la cuenta real. También puede utilizarse una cuenta ya autorizada; no se crean roles automáticamente. La aplicación ejecuta transacciones READ ONLY, timeout de consulta de tres segundos y un pool acotado. Una caída del origen muestra un error recuperable en el selector interno; login, listados, recepción y documentos existentes siguen usando lab_lc. Los nuevos clientes externos no consultan el origen y reciben el código EXTERNO desde el servidor. Nunca poner PROJECTS_DATABASE_URL en client ni como VITE_.

## Solicitudes y trabajo del laboratorio

- **Datos generales:** proyecto solo para la empresa interna; nombre, distrito, provincia y departamento obligatorios. Fecha objetivo, indicaciones y coordenadas este/norte opcionales. No se asume zona UTM ni sistema geodésico a partir de estos números.
- **Matriz de muestras:** una fila por muestra, hasta 200. Calicata/sondaje y profundidades opcionales; Muestra y Tipo de muestra obligatorios. Sacos: entero positivo o desconocido; Peso: kg positivo o desconocido. Observaciones opcionales. Ensayos en columnas, casillas individuales o aplicadas a filas seleccionadas; duplicación y pegado tabulado de ocho columnas descriptivas desde Excel. No se importan automáticamente los Excel originales.
- **Envío:** se admiten muestras sin ensayos. La etapa interna es WAITING_ASSAYS si alguna muestra carece de ensayos o SUBMITTED cuando todas los tienen. Estas etapas controlan envío, privacidad y recepción; no son el Estado Solicitud visible. Los conteos muestran por separado revisiones pendientes y muestras sin ensayos.
- **Edición antes de aprobar:** el autor CLIENT puede editar antes de aprobación, también después de enviar. Desde el envío, el proyecto no cambia. Una muestra recibida conserva su identidad y datos declarados: no se elimina ni se modifica; se pueden incorporar ensayos después. Cambios concurrentes devuelven conflicto para recargar antes de reintentar.
- **Recepción:** jefatura recibe solicitudes enviadas, incluso pendientes de ensayos. TECH recibe solo muestras asignadas de solicitudes aprobadas. Sacos y peso recibidos son datos independientes de los declarados; fecha/hora y transporte se aplican al grupo seleccionado. Recepciones parciales y correcciones mantienen historial y motivo.
- **OT:** botón Generar OT en Recepción, exclusivo jefatura; código manual normalizado. Requiere al menos una muestra recibida, aunque esté observada/dañada/insuficiente y falten otras. No habilita por sí sola material no conforme. Cambiar una OT exige motivo. Un único texto por solicitud; no se crea tabla de órdenes.
- **Revisión individual:** «Revisar ensayos» permite aprobar o rechazar cada ensayo pendiente, guardar decisiones distintas juntas o revisar uno solo. Rechazar exige motivo; los no seleccionados continúan pendientes. La primera aprobación lleva la solicitud a APPROVED. Si todos se rechazan, sin ninguno aprobado ni pendiente, queda OBSERVED. Los nuevos y los rechazados no pueden asignarse ni ejecutarse; el trabajo aprobado continúa. Revisión y ejecución son campos distintos; asignación sigue derivándose de tecnico_id.
- **Estados:** pendiente ámbar, ejecución azul, observado rojo, completado verde, cancelado gris. Responsable/jefatura pueden observar/completar solamente después de iniciar. Solo jefatura cancela o retoma con motivo; retomar conserva la fecha inicial. La selección masiva muestra solo acciones válidas para todos y es atómica.
- **Informes:** PDF privado, máximo 20 MiB/500 páginas, sin cifrado ni contenido activo. Técnicos/jefatura cargan en solicitudes aprobadas; disponibilidad inmediata para usuarios autorizados. Cada carga conserva un archivo y versión. Las comprobaciones técnicas no son un escáner antimalware. Cierre separado de jefatura: al menos un ensayo aprobado completado, todas las muestras con ensayos definidos, ensayos aceptados resueltos, sin decisiones pendientes e informe disponible. Los rechazos resueltos no bloquean por sí solos el cierre.
- **Actas y etiquetas:** bajo demanda, sin almacenamiento histórico adicional. Etiquetas A4, 95×68 mm, 2×4, separación 4 mm; tamaño real/100 %, ocho por página. Código recepción compartible y código laboratorio único; ambos manuales obligatorios al recibir. Se conservan cliente, código proyecto, muestra, punto y profundidad; sin UR; la esquina inferior izquierda muestra OT: codigo_ot o OT: — si aún no existe.

### Solicitar y revisar ensayos

El autor usa «Solicitar ensayos» después de aprobar, mientras la solicitud no esté cancelada ni cerrada. `PUT /requests/{rid}/assays` recibe `version` y `samples: [{sample_id, assay_ids}]` para cambiar selecciones pendientes sobre las muestras existentes. No modifica la cabecera, las muestras ni ensayos ya revisados (aprobados o rechazados).

Solo MANAGER puede usar `POST /requests/{rid}/assays/review` con `version` y `decisions: [{task_id, decision, reason}]`. `decision` admite APPROVED o REJECTED; cada rechazo requiere motivo. Se validan pertenencia, duplicados, revisión pendiente, permisos y versión antes de guardar el conjunto en una única transacción. La antigua acción global `approve` devuelve 409 e indica que se debe seleccionar cada ensayo. ADMIN necesita el rol adicional MANAGER para revisar.

El autor CLIENT ve decisión y motivo, también en el historial, con responsable y fecha. «Volver a solicitar» usa `POST /requests/{rid}/assays/resubmit` con `version` y `task_ids`. Reutiliza los mismos registros rechazados, conserva auditoría y vuelve su revisión a PENDING. Una solicitud OBSERVED vuelve a WAITING_ASSAYS si tiene muestras sin ensayos o a SUBMITTED en caso contrario. Cada reenvío requiere otra decisión; una solicitud con trabajo aprobado conserva APPROVED.

JSON mantiene `approved` calculado desde `review_status=APPROVED`, e incorpora `review_status`, `review_reason`, `can_review` y `can_resubmit`. `unapproved_count` cuenta solo revisiones pendientes de ensayos operativamente PENDING; un rechazo resuelto no es «por aprobar». El motivo no añade columnas: procede de eventos públicos de `actividad`. La carga del dashboard solo cuenta ensayos aprobados abiertos.

### Filtros, coordenadas y carga

Solicitudes/Recepción/Trabajo/Informes muestran solicitante y empresa a ADMIN/MANAGER/TECH, usando la empresa conservada en la solicitud. Los parámetros `requester` y `organization` son UUID; las opciones paginadas de `/filter-options?kind=requester|organization&view=requests|reception|work|reports&q=...` respetan el mismo alcance. Los filtros **Estado Ensayo** de Solicitudes y Trabajo de laboratorio comparten `assay_status` CSV: `PENDING_REVIEW` (Por aprobar), `PENDING_EXECUTION` (Pendiente Ejecución), `RUNNING` (En Ejecución), `WAITING_ASSAYS` (Pendiente Ensayos), `REJECTED`, `COMPLETED`, `CANCELLED` y `OBSERVED`. OR dentro de cada selección y AND entre filtros. La tabla Solicitudes muestra cada cantidad distinta de cero; WAITING_ASSAYS cuenta **muestras** sin ensayos solo en solicitudes CREATED, no ensayos ficticios. Una fila real cuenta una sola vez: ejecución CANCELLED tiene prioridad, luego revisión REJECTED, revisión PENDING y ejecución aprobada. No mostrar Pendiente y Rechazado simultáneamente. En Work las muestras sin ensayos son filas informativas `row_kind=sample_without_assays`, `id=null`, sin selección ni acciones; la paginación cuenta todas las filas, pero el encabezado distingue ensayos reales. Incluye trabajo enviado pendiente de revisión, aprobado e histórico; excluye borradores. TECH sigue limitado a sus asignaciones y no accede a esas muestras sin ensayos.

**Estado Solicitud** usa `request_status=CREATED,CANCELLED,CLOSED` y corresponde a `solicitudes.estado_general`: Creado, Cancelado o Cerrado. El estado no cambia al revisar o ejecutar ensayos. JSON `status` conserva la etapa interna `estado_solicitud`; `assay_counts` se calcula en SQL sobre todas las filas autorizadas, sin guardar contadores. La ficha reutiliza el resumen del listado. La API conserva `status`, `state` y `pending_assays` para consultas antiguas; Recepción conserva sus filtros operativos, excluyendo solicitudes canceladas. Los enlaces internos de carga usan el nuevo `assay_status`.

`created_from` y `created_to` incluyen los días completos en America/Lima; filtran creación de solicitud. URL conserva filtros y paginación. «Borrar filtros», centrado en los cuatro paneles, limpia todos los parámetros, incluido pending_assays, vuelve a página 1 y reinicia las búsquedas de selectores, conservando la sección. Solicitudes muestra Fecha de creación en Lima y conserva Fecha objetivo. El cliente externo sin roles operativos no ve Proyecto.

**Recepción** muestra «Estado Recepción»: cantidades de muestras sin recibir, observadas, dañadas e insuficientes, más «Sin OT» cuando falta `codigo_ot`. Pueden coexistir varios indicadores; no representan aprobación ni ejecución de ensayos. `/requests?view=reception` devuelve `reception_counts` con `NOT_RECEIVED`, `OBSERVED`, `DAMAGED` e `INSUFFICIENT`, calculados en PostgreSQL y limitados a las muestras accesibles (TECH: asignadas). El único selector de estado en esta página es «Estado de recepción»: `condition=NOT_RECEIVED`, `issues` o `NO_OT`; los demás filtros se conservan. La interfaz retira `status` de enlaces antiguos de Recepción y reinicia su página, conservando las demás selecciones. Las reglas de recepción/OT y las exclusiones de solicitudes terminales no cambian.

**Informes** (`/reports`) sirve para consultar, visualizar y descargar versiones ya cargadas. La carga de PDF permanece en **Documentos**, dentro de la solicitud, con los permisos actuales. «Buscar solicitud» usa `q` para coincidencias parciales en código o título de solicitud sin distinguir mayúsculas; no busca proyecto ni nombre de archivo. Proyecto conserva su filtro independiente (`project`), combinado con los demás mediante AND. Estos ajustes no requieren SQL ni nuevas variables o servicios Azure; publicar API y frontend coordinadamente. El esquema continúa en versión 7.

Coordenadas opcionales e independientes: este `100000 ≤ valor < 1000000`, norte `1000000 ≤ valor < 10000000`, números finitos con decimales permitidos. Es validación de formato, no de posición, zona ni datum. No se reescriben coordenadas históricas; se valida una coordenada histórica al modificarla. Profundidad cero sigue siendo válida y es independiente de esta regla.

`Loading` distingue carga de vacío y error; `NetworkLoading` indica consultas y descargas en curso. Los listados conservan sus datos mientras se actualizan. Los controles de envío usan `busy` para impedir envíos duplicados. Los avisos de error usan `useErrorNotice` y `ErrorBox`: visibles 5 segundos, desvanecimiento de 500 ms; un nuevo error idéntico reinicia el plazo. Las marcas de campos inválidos permanecen hasta corregirse. El estado de fallo de una consulta se conserva separado del aviso: desaparecer no inicia otra carga. Los selectores y consultas recuperables permiten reintentar.

### Cabecera y controles numéricos

La cabecera muestra el nombre completo registrado y la empresa debajo, sin etiquetas de rol añadidas ni truncamiento; en móvil permite varias líneas. Inicio de sesión y sesión incluyen `organization_name`. Los nombres existentes no se editan automáticamente: un texto como «cliente interno» que forme parte del nombre registrado seguirá apareciendo hasta que el administrador lo cambie.

`NumericInput` se usa en sacos/peso de declaración y recepción. Sacos: mínimo 1, entero e incremento 1. Peso: positivo e incremento 0.1 kg. Las flechas son botones propios para no imponer un step de 0.1 a los decimales escritos: por ejemplo, 0.025 permanece 0.025 y la flecha suma 0.1 sin redondearlo a una décima. Profundidades conservan sus controles anteriores. No se redondean datos existentes.

### Cancelar y cerrar solicitudes

El autor CLIENT o MANAGER puede enviar `POST /requests/{rid}/actions` con `{version, action: "cancel", reason}`. El motivo es obligatorio. Se bloquea la solicitud y se cancela en una transacción todo ensayo abierto no rechazado; se conservan completados, rechazos, responsables, fechas, informes e historial. ADMIN sin MANAGER y TECH no pueden cancelar solicitudes. DRAFT permanece exclusivo de su autor, incluso cancelado. No hay reapertura.

Cancelar impide edición, recepción, revisión, reenvío, OT, carga de nuevos PDF, comentarios y ejecución; no impide consulta autorizada ni descargas o impresión. La solicitud sale de recepción y carga operativa. La antigua acción global reject devuelve409 para indicar Cancelar solicitud o revisión individual; el rechazo de un ensayo no cancela la solicitud.

Cerrar corresponde solo a MANAGER: al menos un ensayo aprobado COMPLETED, ninguna muestra sin ensayos, ninguna revisión/trabajo aceptado pendiente e informe disponible. Rechazos resueltos y ensayos cancelados no bloquean por sí solos el cierre, pero todos cancelados sin completados no permiten cerrar. Una solicitud cerrada no se puede cancelar. Los cierres históricos se conservan.

SQL 6→7 añade únicamente `estado_general` (text, NOT NULL, default CREATED, CHECK de tres valores). CLOSED interno se convierte en CLOSED general y REJECTED global anterior en CANCELLED; sus ensayos abiertos no rechazados se cancelan con auditoría de migración. No se modifican fechas, decisiones, archivos ni resultados completados. Los demás quedan CREATED. No se añaden tablas, servicios ni variables Azure.

## Permisos y privacidad

| Rol | Alcance |
|---|---|
| CLIENT | Redacta, consulta y descarga exclusivamente sus solicitudes; empresa interna selecciona catálogo y externa usa EXTERNO. |
| TECH | Solicitudes con ensayos asignados, solo sus muestras/ensayos, informes de esas solicitudes; dashboard personal. |
| MANAGER | Consulta global excepto borradores ajenos; recepción, aprobación, OT y operaciones de laboratorio. |
| ADMIN | Usuarios, contraseñas, empresas, catálogo y consulta/dashboard global excepto borradores ajenos; operar requiere rol adicional. |

Los roles son acumulables: CLIENT adicional permite redactar y leer sus solicitudes, sin ampliar operaciones de TECH sobre muestras ajenas. Los borradores pertenecen exclusivamente al autor. No existe asignación por proyecto; seleccionar un código de proyecto no concede acceso a solicitudes de otra persona. Consultas, descargas y operaciones validan permisos en el servidor en cada petición. Empresa de usuario y de solicitud son entidades distintas; cambiar la cuenta no cambia registros históricos.

Administración permite editar nombre, correo, teléfono opcional, empresa, roles y cuenta habilitada. Cambios de cuenta/permisos y contraseña revocan sesiones. Empresas se editan y como máximo una activa puede ser interna. El último administrador activo no puede deshabilitarse ni perder su rol.

La interfaz mantiene filtros y pestañas en URL. Navegación superior, filtros a la derecha y acciones de ensayos junto a la tabla; en pantallas pequeñas se reorganizan. Muestras sin recibir abre Recepción con NOT_RECEIVED; NO_OT identifica solicitudes que todavía necesitan OT. Las métricas se agregan en PostgreSQL sobre todo el conjunto autorizado, sin depender de la página ni estimar horas.

## Cómo funciona sesiones

Cada login correcto inserta una credencial temporal cuyo token original solo está en una cookie HttpOnly. PostgreSQL guarda su hash; usuario_id identifica la cuenta, creado_en el login, ultimo_acceso la actividad y vence_en el límite absoluto. Cerrar sesión elimina el registro; cambio de contraseña, edición de accesos/deshabilitación y limpieza de vencidas también lo eliminan. actividad conserva el historial permanente. Diagnóstico sin hashes:

```sql
SELECT u.correo,s.creado_en,s.ultimo_acceso,s.vence_en
FROM sesiones s JOIN usuarios u ON u.id=s.usuario_id
ORDER BY s.creado_en DESC;
SELECT current_database(), inet_server_port();
```

## Verificación y documentación

```bat
cd api
python -m pytest -q
python -m ruff check blueprints services tests config.py database.py errors.py function_app.py http_helpers.py manage.py security.py validation.py
cd ..\client
npm run lint
npm test
npm run build
```

Las pruebas PostgreSQL requieren TEST_DATABASE_URL apuntando exclusivamente a una base ficticia admitida con esquema 7, por ejemplo lab_lc_v7_unit_test. E2E usa LAB_E2E_URL y LAB_E2E_PASSWORD privados y cuentas ficticias. No usar bases reales. Resultados y limitaciones: [docs/verification.md](docs/verification.md). Contrato: [docs/openapi.json](docs/openapi.json). ERD: [Mermaid](docs/database.mmd) y [SVG](docs/database.svg). Publicación y actualización de Azure: [docs/deployment.md](docs/deployment.md).

Git, VS Code App Service y Functions tienen exclusiones independientes. No publicar .env, local.settings.json, .local, PDF locales, cachés, entornos ni node_modules Windows; sí lockfiles y certificados públicos. El frontend publicado requiere dist más server.mjs y sus dependencias; npm run build no crea un ZIP ni agrega el proxy. Se mantienen las configuraciones de despliegue existentes. Esta actualización 6→7 solo necesita el nuevo bloque SQL y ambos paquetes; no cambia conexiones, permisos de infraestructura ni variables Azure.

Los controles de aplicación no son una garantía absoluta de seguridad de Azure. Mantener HTTPS, verify-full, Blob privado, copias y restauración coordinada con los informes; probar la nueva entrega en los recursos reales antes de habilitar usuarios.

<!-- TYPOGRAPHY:START -->
## Dónde cambiar el tamaño de cada texto

Todos los tamaños de la web están en **client/src/styles.css**. Al principio, las variables `--text-*` definen la escala en **píxeles CSS**, independiente del zoom del navegador. Para cambiar un grupo completo, modifica su variable; para un texto concreto, modifica la regla del selector indicado abajo. Las reglas posteriores y los contextos responsive pueden prevalecer sobre las generales. Los textos sin tamaño explícito heredan el de su contenedor; la base es 15 px.

| Texto / componente | Control principal |
|---|---|
| Texto general, todas las páginas | `:root` → `--text-body` (15 px) |
| Títulos PageHead / ui.jsx | `h1`, `.page-head` y reglas responsive; 32 px general |
| Títulos de tarjetas / ui.jsx, detalles y formularios | `h2`, `.card-title h2`; variable según inventario |
| Campos y botones / Field, Button, SearchSelect | `.field`, `.btn`, `.search-select`, `.select-popover`; controles 14 px |
| Tablas / Dashboard, WorkPanel, ReportsPage, RequestDetail, Admin | `th`, `td`, `.table-scroll`, `.table-link`; encabezados 14 px |
| Matriz / RequestForm y AssaysEditor | `.sample-matrix`, `.assay-edit-matrix`; encabezados 14 px, datos según control |
| Estados / Badge, RequestBadges | `.badge`, `.status-stack` |
| Navegación y usuario / App.jsx | `.workspace-nav a`, `.user-block`, reglas móvil |
| LABORATORIO LURÍN / App.jsx | `.portal-header .brand span` → `--text-brand` (11 px) |
| Pie izquierdo y derecho / App.jsx | `.workspace-footer`, `.workspace footer` → `--text-tiny` (12 px) |
| Indicadores y gráficos / Dashboard.jsx | `.metric-value`, barras y leyendas: inventario de reglas debajo |
| Inicio de sesión / Login.jsx | selectores `.login-*` y sus excepciones responsive |
| Carga y errores / ui.jsx | `.loading-state`, `.error-box` → 14 px |

Escala central: --text-brand = 11px; --text-tiny = 12px; --text-small = 13px; --text-control = 14px; --text-body = 15px; --text-subheading = 16px; --text-heading = 20px; --text-title-small = 27px; --text-metric = 29px; --text-title-medium = 31px; --text-title = 32px; --text-hero-small = 36px; --text-hero = 56px.

### Inventario exacto de declaraciones (en orden del archivo)

| Selector | Contexto | Variable | Tamaño | Línea CSS |
|---|---|---|---|---|
| `:root` | General | `--text-body` | 15px | [29](client/src/styles.css#L29) |
| `h1` | General | `--text-title` | 32px | [68](client/src/styles.css#L68) |
| `h2` | General | `--text-heading` | 20px | [75](client/src/styles.css#L75) |
| `h3` | General | `--text-subheading` | 16px | [80](client/src/styles.css#L80) |
| `small` | General | `--text-small` | 13px | [87](client/src/styles.css#L87) |
| `.eyebrow` | General | `--text-tiny` | 12px | [134](client/src/styles.css#L134) |
| `.btn` | General | `--text-control` | 14px | [151](client/src/styles.css#L151) |
| `.brand span` | General | `--text-brand` | 11px | [227](client/src/styles.css#L227) |
| `.nav-caption` | General | `--text-tiny` | 12px | [233](client/src/styles.css#L233) |
| `.sidebar nav a` | General | `--text-control` | 14px | [249](client/src/styles.css#L249) |
| `.secure-note` | General | `--text-small` | 13px | [271](client/src/styles.css#L271) |
| `.secure-note small` | General | `--text-tiny` | 12px | [275](client/src/styles.css#L275) |
| `.user-block` | General | `--text-small` | 13px | [283](client/src/styles.css#L283) |
| `.user-block small` | General | `--text-tiny` | 12px | [297](client/src/styles.css#L297) |
| `.avatar` | General | `--text-small` | 13px | [309](client/src/styles.css#L309) |
| `.topbar` | General | `--text-small` | 13px | [324](client/src/styles.css#L324) |
| `.page-head p` | General | `--text-control` | 14px | [362](client/src/styles.css#L362) |
| `.welcome-banner h2` | General | `--text-title-medium` | 31px | [380](client/src/styles.css#L380) |
| `.welcome-banner p` | General | `--text-control` | 14px | [387](client/src/styles.css#L387) |
| `.welcome-banner a` | General | `--text-small` | 13px | [395](client/src/styles.css#L395) |
| `.art-tag` | General | `--text-tiny` | 12px | [440](client/src/styles.css#L440) |
| `.stat-card strong` | General | `--text-metric` | 29px | [483](client/src/styles.css#L483) |
| `.stat-card span` | General | `--text-tiny` | 12px | [492](client/src/styles.css#L492) |
| `.card-title h2` | General | `--text-subheading` | 16px | [517](client/src/styles.css#L517) |
| `.text-link` | General | `--text-tiny` | 12px | [526](client/src/styles.css#L526) |
| `table` | General | `--text-small` | 13px | [536](client/src/styles.css#L536) |
| `th` | General | `--text-tiny` | 12px | [540](client/src/styles.css#L540) |
| `.table-link > b` | General | `--text-tiny` | 12px | [564](client/src/styles.css#L564) |
| `.table-link > small` | General | `--text-tiny` | 12px | [575](client/src/styles.css#L575) |
| `.badge` | General | `--text-tiny` | 12px | [589](client/src/styles.css#L589) |
| `.progress-caption` | General | `--text-tiny` | 12px | [645](client/src/styles.css#L645) |
| `.activity-item b` | General | `--text-small` | 13px | [661](client/src/styles.css#L661) |
| `.activity-item small` | General | `--text-tiny` | 12px | [667](client/src/styles.css#L667) |
| `.help-card h3` | General | `--text-control` | 14px | [688](client/src/styles.css#L688) |
| `.help-card p` | General | `--text-tiny` | 12px | [692](client/src/styles.css#L692) |
| `.help-card a` | General | `--text-tiny` | 12px | [699](client/src/styles.css#L699) |
| `.empty` | General | `--text-control` | 14px | [706](client/src/styles.css#L706) |
| `.workspace-footer` | General | `--text-tiny` | 12px | [722](client/src/styles.css#L722) |
| `.error-box` | General | `--text-control` | 14px | [731](client/src/styles.css#L731) |
| `.notice` | General | `--text-control` | 14px | [740](client/src/styles.css#L740) |
| `.filter-bar > select` | General | `--text-control` | 14px | [763](client/src/styles.css#L763) |
| `.pagination` | General | `--text-small` | 13px | [771](client/src/styles.css#L771) |
| `.field > span,
 .field-label` | General | `--text-small` | 13px | [786](client/src/styles.css#L786) |
| `.back-link` | General | `--text-small` | 13px | [818](client/src/styles.css#L818) |
| `.steps button` | General | `--text-control` | 14px | [832](client/src/styles.css#L832) |
| `.sample-editor header` | General | `--text-control` | 14px | [863](client/src/styles.css#L863) |
| `.assay-chips label` | General | `--text-small` | 13px | [872](client/src/styles.css#L872) |
| `.request-overview small` | General | `--text-tiny` | 12px | [904](client/src/styles.css#L904) |
| `.request-overview b` | General | `--text-control` | 14px | [910](client/src/styles.css#L910) |
| `.tabs button` | General | `--text-control` | 14px | [930](client/src/styles.css#L930) |
| `.detail-columns p` | General | `--text-control` | 14px | [951](client/src/styles.css#L951) |
| `dl` | General | `--text-control` | 14px | [958](client/src/styles.css#L958) |
| `.next-step p` | General | `--text-small` | 13px | [977](client/src/styles.css#L977) |
| `.comment` | General | `--text-small` | 13px | [983](client/src/styles.css#L983) |
| `.check-label` | General | `--text-control` | 14px | [997](client/src/styles.css#L997) |
| `.document-hero p` | General | `--text-control` | 14px | [1008](client/src/styles.css#L1008) |
| `.document-row` | General | `--text-small` | 13px | [1024](client/src/styles.css#L1024) |
| `.list-row,
 .issue` | General | `--text-control` | 14px | [1047](client/src/styles.css#L1047) |
| `.list-row p` | General | `--text-small` | 13px | [1052](client/src/styles.css#L1052) |
| `.timeline-item` | General | `--text-control` | 14px | [1069](client/src/styles.css#L1069) |
| `.activation h1` | General | `--text-title-small` | 27px | [1142](client/src/styles.css#L1142) |
| `.login-story h1` | General | `--text-hero` | 56px | [1180](client/src/styles.css#L1180) |
| `.login-story p` | General | `--text-body` | 15px | [1188](client/src/styles.css#L1188) |
| `.story-track` | General | `--text-tiny` | 12px | [1195](client/src/styles.css#L1195) |
| `.login-story footer` | General | `--text-small` | 13px | [1202](client/src/styles.css#L1202) |
| `.login-form h2` | General | `--text-metric` | 29px | [1215](client/src/styles.css#L1215) |
| `.login-form p` | General | `--text-control` | 14px | [1220](client/src/styles.css#L1220) |
| `.login-security` | General | `--text-tiny` | 12px | [1239](client/src/styles.css#L1239) |
| `.stat-card span` | `@media (max-width: 1200px)` | `--text-tiny` | 12px | [1299](client/src/styles.css#L1299) |
| `h1` | `@media (max-width: 800px)` | `--text-title-small` | 27px | [1347](client/src/styles.css#L1347) |
| `.welcome-banner h2` | `@media (max-width: 800px)` | `--text-title-small` | 27px | [1363](client/src/styles.css#L1363) |
| `.steps button` | `@media (max-width: 800px)` | `--text-tiny` | 12px | [1374](client/src/styles.css#L1374) |
| `.login-story h1` | `@media (max-width: 800px)` | `--text-hero-small` | 36px | [1404](client/src/styles.css#L1404) |
| `.chart-legend` | General | `--text-control` | 14px | [1464](client/src/styles.css#L1464) |
| `.history-entry pre` | General | `--text-control` | 14px | [1528](client/src/styles.css#L1528) |
| `.portal-header .brand span` | General | `--text-brand` | 11px | [1693](client/src/styles.css#L1693) |
| `.workspace-nav a` | General | `--text-control` | 14px | [1710](client/src/styles.css#L1710) |
| `.sample-matrix th` | General | `--text-small` | 13px | [1891](client/src/styles.css#L1891) |
| `.sample-matrix textarea` | General | `--text-control` | 14px | [1942](client/src/styles.css#L1942) |
| `.portal-header .user-block b` | `@media (max-width: 600px)` | `--text-small` | 13px | [2157](client/src/styles.css#L2157) |
| `.portal-header .user-block small` | `@media (max-width: 600px)` | `--text-tiny` | 12px | [2160](client/src/styles.css#L2160) |
| `.steps button` | `@media (max-width: 600px)` | `--text-small` | 13px | [2174](client/src/styles.css#L2174) |
| `.portal-header .brand span` | General | `--text-brand` | 11px | [2214](client/src/styles.css#L2214) |
| `.workspace footer` | General | `--text-tiny` | 12px | [2217](client/src/styles.css#L2217) |
| `.table-scroll thead th` | General | `--text-control` | 14px | [2262](client/src/styles.css#L2262) |
| `.external-service` | General | `--text-small` | 13px | [2321](client/src/styles.css#L2321) |
| `.loading-state` | General | `--text-control` | 14px | [2386](client/src/styles.css#L2386) |
| `.select-clear` | General | `--text-heading` | 20px | [2419](client/src/styles.css#L2419) |
| `.select-popover [role="option"]` | General | `--text-control` | 14px | [2439](client/src/styles.css#L2439) |
| `.select-popover p` | General | `--text-small` | 13px | [2455](client/src/styles.css#L2455) |
| `.work-hint` | General | `--text-small` | 13px | [2564](client/src/styles.css#L2564) |
| `.numeric-buttons button` | General | `--text-control` | 14px | [2640](client/src/styles.css#L2640) |

Regenerar este inventario después de cambiar CSS: `node scripts/export_typography.mjs` (requiere las dependencias instaladas de client). Las fuentes del PDF son independientes: `api/services/documents.py`, función `render_labels`; no se cambian con el CSS web.
<!-- TYPOGRAPHY:END -->

<!-- BEGIN FIELD DICTIONARY -->
## Diccionario completo de la base de datos

Generado desde PostgreSQL con `python scripts/export_contracts.py`. NULL representa un dato desconocido; no es cero. Fechas y horas se presentan en Lima. `text` se limita en la API mediante Pydantic. FK indica relación; PK identifica la fila.

### empresas

Empresas de los solicitantes; como máximo una es interna.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `nombre` | `text` | Sí | `Sin valor; debe suministrarse` | — | Nombre visible. |
| `identificacion_tributaria` | `text` | No | `NULL` | — | Identificación tributaria; única si se informa. |
| `activo` | `boolean` | Sí | `true` | — | Registro habilitado. En usuarios, false impide el acceso. |
| `es_interna` | `boolean` | Sí | `false` | — | Designa la única empresa interna; sus clientes seleccionan proyectos de AppControlHH. |

### usuarios

Identidad, contacto, empresa y roles de acceso; no existen asignaciones a proyectos.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `empresa_id` | `uuid` | No | `NULL` | empresas.id | Empresa a la que pertenece el registro. |
| `nombre` | `text` | Sí | `Sin valor; debe suministrarse` | — | Nombre visible. |
| `num_telefono` | `text` | No | `NULL` | — | Teléfono opcional como texto, permite prefijo internacional. |
| `correo` | `text` | Sí | `Sin valor; debe suministrarse` | — | Correo de acceso, único y guardado en minúsculas; no se utiliza para enviar mensajes. |
| `hash_contrasena` | `text` | Sí | `Sin valor; debe suministrarse` | — | Hash Argon2id con salt y parámetros incluidos. No contiene contraseña recuperable y nunca se devuelve al navegador. |
| `roles` | `text_array` | Sí | `'{CLIENT}'::text[]` | — | Roles acumulables ADMIN, MANAGER, TECH y CLIENT. Debe existir al menos uno. |
| `activo` | `boolean` | Sí | `true` | — | Registro habilitado. En usuarios, false impide el acceso. |
| `creado_en` | `timestamptz` | Sí | `now()` | — | Instante de creación, almacenado con zona horaria. |

### catalogo_ensayos

Tipos de ensayo y referencias de método editables.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `codigo` | `text` | Sí | `Sin valor; debe suministrarse` | — | Código visible único. |
| `nombre` | `text` | Sí | `Sin valor; debe suministrarse` | — | Nombre visible. |
| `metodo` | `text` | Sí | `''::text` | — | Referencia del método, pendiente de validación por el laboratorio antes de usarla. |
| `categoria` | `text` | Sí | `'Geotecnia'::text` | — | Grupo del ensayo para organizar el catálogo. |
| `activo` | `boolean` | Sí | `true` | — | Registro habilitado. En usuarios, false impide el acceso. |

### solicitudes

Solicitud del autor; empresa conservada y código externo de proyecto sin FK entre bases.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `codigo` | `text` | Sí | `('SOL-'::text || lpad((nextval('numero_solicitud'::regclass))::text, 8, '0'::text))` | — | Correlativo visible SOL-00000001 generado por numero_solicitud. Los saltos de secuencia son normales. |
| `proyecto_id` | `text` | Sí | `Sin valor; debe suministrarse` | — | Código de AppControlHH para solicitudes internas; EXTERNO para nuevas solicitudes externas. No es UUID ni FK. |
| `empresa_id` | `uuid` | Sí | `Sin valor; debe suministrarse` | empresas.id | Empresa conservada al crear la solicitud, independiente de cambios posteriores en el usuario. FK empresas.id. |
| `creado_por` | `uuid` | Sí | `Sin valor; debe suministrarse` | usuarios.id | Usuario que creó la solicitud. |
| `distrito` | `text` | No | `NULL` | — | Distrito de procedencia. Obligatorio en API al crear/editar; NULL permitido en registros históricos migrados. |
| `provincia` | `text` | No | `NULL` | — | Provincia de procedencia. Obligatoria en API al crear/editar; NULL permitido en históricos. |
| `departamento` | `text` | No | `NULL` | — | Departamento de procedencia. Obligatorio en API al crear/editar; NULL permitido en históricos. |
| `coordenada_este` | `numeric` | No | `NULL` | — | Coordenada este opcional. NULL si se desconoce; no se convierte ni se presume sistema de referencia. |
| `coordenada_norte` | `numeric` | No | `NULL` | — | Coordenada norte opcional. NULL si se desconoce; no se convierte ni se presume sistema de referencia. |
| `codigo_ot` | `text` | No | `NULL` | — | OT manual normalizada en mayúsculas. Jefatura requiere al menos una muestra recibida para registrarla; correcciones con motivo. |
| `titulo` | `text` | Sí | `Sin valor; debe suministrarse` | — | Nombre o propósito del servicio solicitado. |
| `estado_solicitud` | `text` | Sí | `'DRAFT'::text` | — | Etapa interna de envío/revisión que conserva privacidad de borradores y permisos. No es el filtro visible Estado Solicitud. |
| `estado_general` | `text` | Sí | `'CREATED'::text` | — | Estado general: CREATED (Creado), CANCELLED (Cancelado) o CLOSED (Cerrado). Independiente de la etapa interna y los conteos derivados. |
| `observaciones` | `text` | Sí | `''::text` | — | Observaciones del registro. |
| `fecha_objetivo` | `date` | No | `NULL` | — | Fecha objetivo solicitada; no sustituye el fin previsto de cada ensayo. |
| `version` | `integer` | Sí | `1` | — | Contador de concurrencia del agregado: aumenta con cambios de muestras, ensayos, comentarios, informes o estado. |
| `creado_en` | `timestamptz` | Sí | `now()` | — | Instante de creación, almacenado con zona horaria. |
| `actualizado_en` | `timestamptz` | Sí | `now()` | — | Instante del último cambio de la solicitud o cualquiera de sus elementos. |

### muestras

Una identidad de muestra desde la declaración hasta la recepción. Conserva la última recepción; actividad conserva las correcciones.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `solicitud_id` | `uuid` | Sí | `Sin valor; debe suministrarse` | solicitudes.id | Solicitud propietaria; determina el proyecto autorizado. |
| `codigo_cliente` | `text` | Sí | `Sin valor; debe suministrarse` | — | Código de muestra declarado por el cliente, único dentro de la solicitud. |
| `calicata_sondaje` | `text` | Sí | `''::text` | — | Calicata, sondaje o punto de extracción. |
| `material` | `text` | Sí | `'Suelo'::text` | — | Descripción del material, por ejemplo suelo, relave o mezcla. |
| `profundidad_inicial` | `numeric` | No | `NULL` | — | Profundidad inicial en metros; puede desconocerse. |
| `profundidad_final` | `numeric` | No | `NULL` | — | Profundidad final en metros; no menor que la inicial. |
| `cantidad` | `numeric` | No | `NULL` | — | Cantidad declarada de sacos enteros positivos; NULL significa desconocida. |
| `peso` | `numeric` | No | `NULL` | — | Peso declarado en kg, positivo y opcional; separado de los sacos. |
| `observaciones` | `text` | Sí | `''::text` | — | Observaciones declaradas por el cliente; describe aquí los componentes de una mezcla. |
| `recibido_en` | `timestamptz` | No | `NULL` | — | Fecha y hora efectivas de la última recepción; NULL si no llegó. |
| `recibido_por` | `uuid` | No | `NULL` | usuarios.id | Persona del laboratorio que registró la recepción actual. |
| `transporte` | `text` | Sí | `''::text` | — | Transporte, vehículo o persona que entregó la muestra. |
| `cantidad_recibida` | `numeric` | No | `NULL` | — | Cantidad actual de sacos recibidos, enteros positivos y opcionales; no se acumula al corregir. |
| `peso_recibido` | `numeric` | No | `NULL` | — | Peso real recibido en kg, positivo y opcional; permite comparar con el declarado. |
| `condicion` | `text` | Sí | `'NOT_RECEIVED'::text` | — | NOT_RECEIVED, OK, OBSERVED, DAMAGED o INSUFFICIENT. Solo OK permite iniciar, retomar y completar ensayos. |
| `observaciones_recepcion` | `text` | Sí | `''::text` | — | Observación visible de recepción; obligatoria si la condición recibida no es OK. |
| `codigo_recepcion` | `text` | No | `NULL` | — | Código manual normalizado en mayúsculas, compartido por muestras recibidas juntas; obligatorio al recibir. |
| `codigo_laboratorio` | `text` | No | `NULL` | — | Código manual normalizado en mayúsculas y único en el laboratorio; obligatorio al recibir. |

### ensayos_muestra

Una fila por pareja muestra–tipo de ensayo. Es la unidad contada en el dashboard.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `muestra_id` | `uuid` | Sí | `Sin valor; debe suministrarse` | muestras.id | Muestra sobre la que se solicita y ejecuta el ensayo. |
| `ensayo_id` | `uuid` | Sí | `Sin valor; debe suministrarse` | catalogo_ensayos.id | Tipo de ensayo del catálogo; no se repite para la misma muestra. |
| `tecnico_id` | `uuid` | No | `NULL` | usuarios.id | Responsable asignado; usuario activo TECH o MANAGER al asignar. |
| `estado_revision` | `text` | Sí | `'PENDING'::text` | — | PENDING, APPROVED o REJECTED. Decisión de revisión separada de la ejecución; nuevos ensayos comienzan PENDING. Motivo, fecha y responsable se conservan en actividad. |
| `estado_ensayo` | `text` | Sí | `'PENDING'::text` | — | PENDING, RUNNING, OBSERVED, COMPLETED o CANCELLED. |
| `inicio_previsto` | `date` | No | `NULL` | — | Fecha prevista de inicio, opcional. |
| `fin_previsto` | `date` | No | `NULL` | — | Fecha prevista final, opcional; determina si el ensayo abierto está vencido. |
| `iniciado_en` | `timestamptz` | No | `NULL` | — | Primer inicio real; se conserva al retomar un ensayo observado. |
| `completado_en` | `timestamptz` | No | `NULL` | — | Instante de finalización real. |
| `observaciones` | `text` | Sí | `''::text` | — | Último motivo o nota técnica interna. El historial conserva los cambios anteriores. |

### informes

Versiones inmutables de los PDF. Cada fila conserva un archivo distinto, visible inmediatamente.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `solicitud_id` | `uuid` | Sí | `Sin valor; debe suministrarse` | solicitudes.id | Solicitud propietaria; determina el proyecto autorizado. |
| `version` | `integer` | Sí | `Sin valor; debe suministrarse` | — | Correlativo de carga dentro de la solicitud; se obtiene con la solicitud bloqueada y no sobrescribe versiones anteriores. |
| `nombre` | `text` | Sí | `Sin valor; debe suministrarse` | — | Nombre seguro generado por el servidor, Informe-N.pdf. |
| `clave_archivo` | `text` | Sí | `Sin valor; debe suministrarse` | — | Clave privada del archivo en Blob o en UPLOAD_DIR; nunca es una URL pública. |
| `sha256` | `text` | Sí | `Sin valor; debe suministrarse` | — | Resumen SHA-256 del contenido para comprobación de integridad. |
| `tamano_bytes` | `integer` | Sí | `Sin valor; debe suministrarse` | — | Tamaño del PDF en bytes, entre 1 y 20 MiB. |
| `subido_por` | `uuid` | Sí | `Sin valor; debe suministrarse` | usuarios.id | Usuario del laboratorio que subió el informe. |
| `creado_en` | `timestamptz` | Sí | `now()` | — | Instante de creación, almacenado con zona horaria. |

### actividad

Historial inmutable y comentarios. Los eventos de cuenta pueden no pertenecer a una solicitud.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `bigint` | Sí | `IDENTITY` | PK | Identidad bigint generada por PostgreSQL; orden estable del historial. |
| `solicitud_id` | `uuid` | No | `NULL` | solicitudes.id | Solicitud propietaria; determina el proyecto autorizado. |
| `autor_id` | `uuid` | No | `NULL` | usuarios.id | Usuario responsable del evento; puede ser NULL en un evento del sistema. |
| `tipo` | `text` | Sí | `'EVENT'::text` | — | EVENT para cambios y COMMENT para comentarios. |
| `mensaje` | `text` | Sí | `Sin valor; debe suministrarse` | — | Descripción del cambio, motivo o texto del comentario. |
| `detalle` | `jsonb` | Sí | `'{}'::jsonb` | — | Auditoría estructurada inmutable. No se devuelve el JSON al navegador; se proyectan descripciones legibles y autorizadas. |
| `interno` | `boolean` | Sí | `true` | — | true restringe el evento al personal autorizado; false permite verlo al autor de la solicitud. |
| `creado_en` | `timestamptz` | Sí | `now()` | — | Instante de creación, almacenado con zona horaria. |

### sesiones

Sesiones opacas revocables. El token original solo vive en la cookie del navegador.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `hash_token` | `text` | Sí | `Sin valor; debe suministrarse` | PK | SHA-256 del token opaco de sesión; clave primaria, no utilizable como cookie. |
| `usuario_id` | `uuid` | Sí | `Sin valor; debe suministrarse` | usuarios.id | Usuario al que pertenece el acceso o la sesión. |
| `creado_en` | `timestamptz` | Sí | `now()` | — | Instante de creación, almacenado con zona horaria. |
| `ultimo_acceso` | `timestamptz` | Sí | `now()` | — | Último acceso autenticado; determina la caducidad por inactividad. |
| `vence_en` | `timestamptz` | Sí | `Sin valor; debe suministrarse` | — | Caducidad absoluta de la sesión. |

### limites_intentos

Contador compartido entre instancias para los intentos de acceso.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `clave_limite` | `text` | Sí | `Sin valor; debe suministrarse` | PK | SHA-256 de la clave del límite (actualmente correo normalizado para login); no guarda la contraseña. |
| `numero_intentos` | `integer` | Sí | `1` | — | Intentos consumidos en la ventana vigente. |
| `inicio_ventana` | `timestamptz` | Sí | `now()` | — | Inicio de la ventana del límite; se renueva al vencer. |

### migraciones_esquema

Versiones instaladas, independientes del nombre de la base. El esquema actual es 7.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `version` | `integer` | Sí | `Sin valor; debe suministrarse` | PK | Versión instalada, PK. Instalación limpia: 7; las migraciones conservan también las versiones previas. |
| `aplicado_en` | `timestamptz` | Sí | `now()` | — | Instante de instalación de la versión del esquema. |

<!-- END FIELD DICTIONARY -->
