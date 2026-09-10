# Laboratorio Lara Consulting · versión 3

Aplicación de solicitudes, recepción, ensayos e informes. React JavaScript + Vite + Tailwind CSS en `client`; Python 3.12 + Azure Functions HTTP en `api`; PostgreSQL como persistencia real. Interfaz y fechas en español, zona horaria America/Lima.

## Cambios de esta versión

La base nueva es **lab_lc_v3**, independiente de lab_lc y lab_lc_v2. El código v3 requiere el esquema v3 en español; no apuntarlo a la base anterior. El instalador no migra, borra ni modifica registros de la base anterior. Hay 13 tablas y un solo registro por muestra desde la solicitud hasta la recepción. Los originales de Referencia siguen siendo material de consulta; no se importan automáticamente.

El acceso utiliza correo y contraseña. El administrador crea cuentas y restablece contraseñas en Administración. No se envían correos, invitaciones ni enlaces. No hay MFA ni recuperación automática por correo.

**FERNET_KEY fue eliminada.** Antes cifraba secretos MFA y datos de enlaces de cuenta. Ya no existen esos flujos. Fernet nunca se utilizó para el hash de contraseñas: estas se guardan con Argon2id, salt individual y parámetros incorporados al hash, sin posibilidad de consultar su valor original. Se exigen entre 15 y 128 caracteres. La implementación usa 64 MiB, 3 iteraciones y paralelismo 1; revisar el costo con el hardware de producción. [Referencia OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

## Instalación local con dos ventanas de Anaconda

Requisitos instalados en Windows: Anaconda o Miniconda, PostgreSQL 17 (servicio en ejecución), Node.js 22.12+ o 24 LTS y Azure Functions Core Tools v4. No se requieren contenedores ni servicios de correo o almacenamiento emulado.

### Preparar PostgreSQL una sola vez

En pgAdmin o psql, conectado a la base `postgres`, ejecuta `sql/00_create_database.sql` fuera de una transacción. Crea **lab_lc_v3**, no lab_lc. Usa un usuario con permiso de crear el esquema en esa base. No elimines la base anterior.

Con psql, sustituyendo usuario, host y puerto por los tuyos:

```bat
psql -h localhost -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -f sql/00_create_database.sql
```

Si lab_lc_v3 ya existe, no repitas CREATE DATABASE. La instalación siguiente verifica que el esquema sea v3 o que la base esté vacía.

### Ventana 1: backend

```bat
cd /d C:\Trabajo\Laboratorio\App\app-lab-lc\api
conda create -n lab-lc python=3.12 -y
conda activate lab-lc
python -m pip install -r requirements-dev.txt
copy local.settings.example.json local.settings.json
```

El comando copy es solo para una instalación nueva: **no sobrescribas tu configuración privada existente**. Edita `api/local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "",
    "APP_ENV": "development",
    "DATABASE_URL": "postgresql+psycopg://USUARIO:CONTRASENA@localhost:5432/lab_lc_v3",
    "APP_ORIGIN": "http://localhost:5173",
    "STORAGE_MODE": "local"
  }
}
```

La contraseña de PostgreSQL se codifica como componente de URL si contiene @, #, /, %, : u otros caracteres reservados. La URL nunca debe copiarse al frontend ni a mensajes de error. Configura el puerto de tu instancia, que puede ser distinto de 5432. No confundas el usuario PostgreSQL con los usuarios de la aplicación.

```bat
python manage.py migrate
python manage.py demo
python manage.py password --email admin@example.com
func start
```

`migrate` instala esquema y catálogo. `demo` es opcional y solo admite desarrollo; carga empresas, proyectos, solicitudes, muestras y ensayos ficticios. La contraseña del administrador se solicita sin eco. Desde la plataforma crea las cuentas reales o restablece las contraseñas de jefe@example.com, tecnico@example.com, cliente@example.com y externo@example.com.

Para una base sin datos demo, ejecuta `python manage.py bootstrap --email administrador@tu-dominio.com` en lugar de demo/password. Crea únicamente el primer ADMIN; asigna MANAGER como rol adicional desde la plataforma si también dirigirá ensayos.

En arranques posteriores basta:

```bat
cd /d C:\Trabajo\Laboratorio\App\app-lab-lc\api
conda activate lab-lc
func start
```

Core Tools debe informar Python 3.12 y servir la API en http://localhost:7071. `where python` permite verificar que el ejecutable corresponda al entorno activado. El proyecto usa exclusivamente HTTP; en local, AzureWebJobsStorage puede quedar vacío. En Azure, la cuenta de almacenamiento del host sigue siendo necesaria.

### Ventana 2: frontend

```bat
cd /d C:\Trabajo\Laboratorio\App\app-lab-lc\client
npm ci
npm run dev
```

Abre **http://localhost:5173**. Vite reenvía /api a 127.0.0.1:7071. No ingreses como 127.0.0.1:5173 si APP_ORIGIN es localhost:5173: la comprobación de origen exige coincidencia exacta. No necesitas crear un archivo .env del frontend para desarrollo.

Si un puerto está ocupado, cierra tu proceso anterior o elige puertos distintos de forma coordinada. Para una revisión en 5174/7072: cambia APP_ORIGIN a http://localhost:5174, ejecuta `func start --port 7072` y, en Anaconda Prompt del frontend, `set API_DEV_TARGET=http://127.0.0.1:7072` seguido de `npm run dev -- --port 5174`. En PowerShell se asigna con `$env:API_DEV_TARGET = 'http://127.0.0.1:7072'`. Reinicia ambos servidores tras cambiar configuración o después de sustituir el esquema.

### Configuración y documentos locales

| Variable del backend | Uso | Valor local / predeterminado |
|---|---|---|
| DATABASE_URL | Conexión privada SQLAlchemy/psycopg a PostgreSQL | Obligatoria, base lab_lc_v3 |
| APP_ENV | Activa las restricciones de producción | development |
| APP_ORIGIN | Origen exacto permitido para escrituras | http://localhost:5173 |
| STORAGE_MODE | Adaptador de documentos | local |
| UPLOAD_DIR | Carpeta privada de informes | api/.local/uploads, absoluta respecto al código |
| SESSION_IDLE_MINUTES | Caducidad por inactividad | 30 |
| SESSION_HOURS | Duración máxima de una sesión | 8 |
| FUNCTIONS_WORKER_RUNTIME | Runtime de Functions | python |
| AzureWebJobsStorage | Almacenamiento del host de Functions | Vacío en HTTP local; obligatorio en Azure |
| STORAGE_ACCOUNT_URL | URL HTTPS de la cuenta Blob | Solo modo azure |
| STORAGE_CONTAINER | Contenedor previamente creado y privado | lab-informes |

La carpeta de informes está fuera del frontend y excluida del repositorio y despliegue. No se sirve como contenido estático: toda descarga comprueba la sesión y el proyecto. UPLOAD_DIR no puede apuntar a client. El despliegue en Azure prohíbe almacenamiento local y APP_ENV de desarrollo.

## Uso y reglas del servicio

- **Solicitudes:** borrador → enviada → aprobada, observada o rechazada. El cliente puede corregir una solicitud observada y reenviarla. La lista de muestras y ensayos es la declaración del envío; ya no hay pestaña ni archivos de custodia.
- **Recepción:** muestra únicamente solicitudes aprobadas con material pendiente o no conforme. Selecciona las muestras que llegaron, cantidad recibida, condición y observación. La fecha/hora (Lima) y el transporte son comunes a la selección. Para fechas diferentes guarda grupos por separado. No hay anuncio previo, bultos ni liberación posterior.
- **Correcciones:** una muestra recibida requiere motivo para cambiar su recepción. Se conserva la identidad, el valor actual y el antes/después en actividad. No se permite invalidar material con ensayos en ejecución o completados. Una mezcla se declara como una muestra, describiendo componentes en sus observaciones.
- **Trabajo:** una fila corresponde a un ensayo de una muestra. Jefatura asigna técnico y fechas; el técnico inicia, observa o completa sus ensayos. Se puede actuar sobre varias filas, incluso de solicitudes distintas, en una transacción. Una muestra no conforme bloquea iniciar, retomar y completar. Es posible programar antes de recibir. Cancelar y retomar observados requieren motivo.
- **Informes:** técnicos y jefatura suben PDF de hasta 20 MiB y 500 páginas en solicitudes aprobadas. No hay revisión, aprobación ni espera de análisis. Se comprueba estructura PDF, contenido activo, cifrado y tamaño; estas comprobaciones no son un análisis antimalware. Cada carga es una versión nueva y queda visible inmediatamente para el proyecto. El nombre de descarga es Informe-N.pdf.
- **Cierre:** jefatura cierra una solicitud aprobada si todos sus ensayos están completados o cancelados y existe al menos un informe. Una solicitud cerrada conserva consulta y descarga, sin modificaciones posteriores.
- **Actas y etiquetas:** se generan al pedirlas desde Recepción y reflejan el estado actual. No se guardan como filas ni archivos históricos adicionales.
- **Historial:** los comentarios pueden ser visibles al cliente o internos. El historial muestra descripciones legibles; el JSON de auditoría permanece en PostgreSQL y no se devuelve al navegador. Las observaciones de recepción sí se comparten con el cliente.

Trabajo excluye solicitudes que aún no fueron aprobadas. Los filtros y la pestaña de detalle viven en la URL; recargar o volver conserva el contexto. Las listas paginan hasta 100 filas por página. Los indicadores no dependen de esa paginación.

## Cambios operativos v3

Solo CLIENT crea solicitudes. Los borradores pertenecen exclusivamente a su autor: ni ADMIN, MANAGER ni otro miembro del proyecto pueden consultarlos. Para que un trabajador solicite ensayos, asignarle CLIENT además de sus roles, una empresa y proyectos desde Administración → Permisos.

El técnico ve únicamente solicitudes con ensayos asignados, sus ensayos y las muestras correspondientes. Recibir una muestra, imprimir actas/etiquetas y consultar historial aplica ese mismo alcance; los informes se comparten a nivel de solicitud. ADMIN y MANAGER tienen alcance global salvo borradores ajenos.

Si un técnico recibe además CLIENT y membresía de proyecto, puede consultar la información pública de ese proyecto y redactar sus solicitudes como cliente. Ese rol adicional no permite recibir muestras, operar ensayos ni subir informes sin la asignación operativa correspondiente. ADMIN/MANAGER conservan su alcance global de lectura; los borradores siguen siendo exclusivos del autor.

La asignación no es un estado. `ensayos_muestra.tecnico_id` identifica al responsable; la API calcula `assigned` y `allowed_actions` y no guarda un booleano redundante. Estados: PENDING, RUNNING, OBSERVED, COMPLETED y CANCELLED.

| Situación | Acciones |
|---|---|
| Pendiente sin técnico | Jefatura asigna/programa o cancela con motivo. |
| Pendiente con técnico y muestra conforme | Iniciar; jefatura también reasigna/programa o cancela. |
| En ejecución | Responsable o jefatura observan/completan; jefatura cancela. |
| Observado | Solo jefatura retoma con motivo y material conforme, o cancela. Retomar vuelve a RUNNING sin cambiar el primer inicio. |
| Completado/cancelado | Sin acciones operativas. |

Una selección múltiple ofrece únicamente acciones comunes a todos sus registros. La API vuelve a comprobar permisos, estado, técnico, material y versión; si una fila falla se revierte todo el lote.

En Inicio, Muestras sin recibir enlaza a `/reception?condition=NOT_RECEIVED`: solo solicitudes aprobadas con al menos una muestra no recibida, dentro del alcance del usuario. El filtro de incidencias de recepción es independiente. El técnico tiene métricas personales de abiertos, vencidos, en ejecución y observados, gráficos por tipo/estado, completados semanales y próximas fechas. Son cantidades, no horas estimadas.

### Códigos y etiquetas

Al recibir cada muestra son obligatorios `codigo_recepcion` y `codigo_laboratorio`, capturados manualmente. Se normalizan con trim/mayúsculas, máximo 60 caracteres. El primero puede compartirse en un grupo recibido junto; el segundo es único en todo el laboratorio. El código común del formulario se aplica a las filas seleccionadas, y cada fila permite modificarlo. Las correcciones conservan motivo e historial.

En Recepción selecciona las muestras recibidas y pulsa Imprimir etiquetas. El PDF usa A4 vertical, dos columnas y cuatro filas, etiquetas **95 × 68 mm**, separación de 4 mm y márgenes centrados (8 mm laterales, 6,5 mm superior/inferior). Hay ocho etiquetas por página y páginas adicionales automáticas. En el diálogo de impresión selecciona A4 y tamaño real/100 %, sin ajustar a página; comprobar que la impresora admita esos márgenes.

Incluye LARA CONSULTING, recepción, MUESTRA DE LABORATORIO, código de laboratorio, cliente (empresa del proyecto), código de proyecto, ID cliente, punto y profundidad inicial–final con dos decimales en metros. Los valores desconocidos usan —. No incluye UR origen ni OT. Los PDF y actas se generan bajo demanda y no agregan tablas ni archivos históricos.

### Compatibilidad de API

Tablas y campos físicos están en español. `api/schema_names.py` mantiene un mapeo explícito de campos PostgreSQL a nombres JSON existentes; las consultas SQL ya usan español y no se reescriben en ejecución. Rutas como `/requests`, `/work` y `/reports` permanecen estables. Los dos códigos nuevos se exponen con su nombre español. El historial expone `description_lines`, sin `detail` crudo. La descarga de etiquetas requiere `sample_ids` separados por comas y verifica cada muestra.

## Permisos

| Rol | Alcance |
|---|---|
| CLIENT | Solicitudes e informes de sus proyectos asignados. Puede declarar muestras y responder comentarios visibles. |
| TECH | Consulta solicitudes con ensayos asignados y únicamente sus muestras/ensayos; recibe esas muestras y carga PDF en sus solicitudes. Dashboard personal. |
| MANAGER | Consulta global, aprobación, recepción, asignación, ejecución, cancelación, carga y cierre. |
| ADMIN | Usuarios, contraseñas, empresas, proyectos, asignaciones y catálogo; dashboard y consulta global. Requiere MANAGER o TECH adicional para operaciones de laboratorio. |

Una empresa asignada al usuario **no concede por sí sola acceso**: el cliente necesita filas en miembros_proyecto. Los proyectos que se asignan deben pertenecer a su empresa. Roles, estado activo y proyecto se consultan en el servidor en cada operación; modificar un UUID o el HTML no concede permisos.

Las sesiones usan tokens aleatorios; PostgreSQL guarda solo su SHA-256. La cookie tiene HttpOnly, SameSite=Lax y Secure en producción. El token CSRF se deriva de la sesión y se conserva solo en memoria. Cambiar roles, deshabilitar o restablecer contraseña revoca todas las sesiones del usuario. Se conserva al menos un administrador activo. Se permiten 10 intentos por correo cada 15 minutos; el proxy añade un límite por IP. Al iniciar sesión se limpian hasta 100 sesiones vencidas y 100 límites antiguos.

## Dashboard: definiciones verificables

- **Carga abierta:** filas de ensayos_muestra cuya solicitud está APPROVED y estado distinto de COMPLETED/CANCELLED.
- **Vencido:** ensayo abierto con fin_previsto anterior al día actual en Lima. El día de vencimiento sigue siendo válido.
- **Sin asignar:** ensayo abierto con tecnico_id NULL.
- **Sin fecha:** ensayo abierto con fin_previsto NULL; se consulta en el filtro Sin fecha de Trabajo; nunca se cuenta como vencido.
- **Muestras sin recibir:** muestras con solicitud APPROVED y condicion NOT_RECEIVED.
- **Muestras observadas:** solicitud APPROVED y condición OBSERVED/DAMAGED/INSUFFICIENT.
- **Por tipo / técnico:** agrupaciones de toda la carga abierta. Un trabajo sin técnico pertenece a Sin asignar.
- **Completados por semana:** estado COMPLETED, solicitud APPROVED o CLOSED y completado_en en cada semana (lunes, Lima), últimas ocho semanas incluyendo la actual.
- **Próximos vencimientos:** abiertos con fecha final hoy o posterior. El dashboard muestra los primeros 10 y enlaza la lista completa.

Los gráficos expresan cantidades, no horas, productividad ajustada por complejidad ni capacidad estimada.

## SQL, contratos y mantenimiento

Orden de instalación manual: 00_create_database.sql conectado a postgres; después 01_schema.sql, 02_catalog.sql y opcionalmente 03_demo.sql conectado a lab_lc_v3. El comando migrate equivale al esquema y catálogo. requirements.in declara las dependencias; requirements.lock.txt fija las 35 versiones de producción auditadas y requirements.txt lo incluye. El SQL de esquema es la migración inicial v3, con registro en migraciones_esquema; no se ejecuta repetidamente sobre una base instalada. Los cambios futuros requieren migraciones nuevas revisadas.

`docs/database.mmd` y `docs/database.svg` muestran las 13 tablas. `docs/openapi.json` enumera las rutas actuales y validaciones. `docs/schema-columns.json` captura los campos exportados, sin registros. Para regenerarlos:

```bat
python scripts/export_contracts.py
npx --package @mermaid-js/mermaid-cli mmdc -i docs/database.mmd -o docs/database.svg -b white
```

El exportador usa DATABASE_URL del entorno o la configuración local, verifica las 13 tablas y actualiza el diccionario al final de este README. No exporta usuarios, contraseñas ni documentos. En equipos con Chrome ya instalado, Mermaid CLI permite `-p ruta-a-puppeteer.json` con executablePath de Chrome.

## Pruebas

Backend: crea una base **lab_lc_v3_test** vacía y carga 01_schema, 02_catalog y 03_demo. Define TEST_DATABASE_URL apuntando exclusivamente a esa base. Los fixtures revierten las operaciones; el contador de limites_intentos de pruebas usa claves aleatorias y puede quedar hasta su limpieza.

```bat
cd api
set TEST_DATABASE_URL=postgresql+psycopg://USUARIO:CONTRASENA@localhost:5432/lab_lc_v3_test
python -m pytest -q
python -m ruff check blueprints services tests config.py database.py errors.py function_app.py http_helpers.py manage.py security.py validation.py
```

Frontend:

```bat
cd client
npm run lint
npm test
npm run build
npm audit
```

E2E con Chrome y ambos servidores activos: configura LAB_E2E_URL (predeterminado http://localhost:5173), LAB_E2E_EMAIL y LAB_E2E_PASSWORD de una cuenta **ficticia** con ADMIN, MANAGER y CLIENT, con empresa y proyecto ficticio asignados. Ejecuta `npm run test:e2e`. No utilices cuentas ni proyectos reales: la prueba crea un servicio de demostración, recibe una muestra y carga un PDF marcado como ficticio. Las contraseñas no deben escribirse en archivos versionados ni en argumentos compartidos. Ver evidencias y limitaciones en `docs/verification.md`. Los resultados de esta versión se registran en docs/verification.md.

## Producción en Azure

La configuración de producción se detalla en [docs/deployment.md](docs/deployment.md), con instalación, permisos, publicación, respaldo y restauración. El frontend requiere **client completo**, incluido server.mjs, package.json, package-lock.json y dist. No publiques solo dist en App Service para este diseño: el servidor Node realiza el proxy a Functions.

El arranque acordado es `npm start`; escucha process.env.PORT. Microsoft documenta la configuración de Node y comandos de arranque; revisar supervisión/reinicio y la alternativa PM2 para una operación sostenida. [Documentación de App Service](https://learn.microsoft.com/en-us/azure/app-service/configure-language-nodejs).

## Resolución de problemas

| Síntoma | Acción |
|---|---|
| 500 tras cambiar de versión | Verifica que DATABASE_URL apunte a lab_lc_v3 con esquema instalado. Reinicia func start. No ejecutes SQL v3 en lab_lc. |
| 409 al ingresar con servidor antiguo | Reinicia el backend: los módulos cargados deben corresponder al esquema v3; borra la cookie solo si persiste el error. |
| 403 al guardar | Abre exactamente APP_ORIGIN; verifica cookie y CSRF, inicia sesión de nuevo y comprueba el rol. |
| 401 | Sesión vencida, cuenta deshabilitada, contraseña o permisos modificados; inicia sesión otra vez. |
| 429 | Espera 15 minutos desde el comienzo de la ventana de intentos. |
| 409 al operar una solicitud | Otro cambio incrementó version; recarga y revisa antes de repetir. También puede indicar estado incompatible o duplicados. |
| 502 del frontend | Revisa func start, puerto 7071 y destino del proxy. |
| Material bloqueado | Registra recepción conforme; revisar condición, cantidad y observación. |
| No aparece un proyecto al cliente | Asigna empresa y proyecto en Administración; empresa sola no concede acceso. |
| PDF rechazado | Comprueba que no esté cifrado, dañado, con acciones/scripts/adjuntos, que no exceda 20 MiB ni 500 páginas. |
| Core Tools usa otro Python | Activa el entorno Anaconda correcto y verifica where python antes de func start. |
| Importaciones antiguas o errores tras quitar MFA | Instala requirements y reinicia Functions; elimina FERNET_KEY y variables de correo de tus configuraciones externas. |
| Error de permisos al ejecutar pruebas desde un agente | Ejecuta los comandos en tus terminales o mediante ejecución ampliada autorizada. No equivale a un defecto funcional del código. |

## Reunión con laboratorio y límites

Usar únicamente la base ficticia: crear servicio con dos muestras; aprobar; recibir una conforme y otra observada en fechas distintas; asignar varios ensayos; verificar bloqueo; corregir recepción con motivo; subir PDF antes de finalizar los ensayos; comprobar visibilidad con un cliente autorizado y exclusión del cliente externo; revisar carga por tipo y cerrar después de atender los ensayos.

Validar con jefatura los nombres/métodos, criterios de recepción, necesidad de repetir un mismo tipo de ensayo sobre una muestra y tratamiento de correcciones después del cierre. Esta versión mantiene una única pareja muestra–tipo, sin cálculos científicos, facturación, inventario, calibración ni integraciones con Microsoft 365/Autodesk. La seguridad operativa depende además de recursos, credenciales, redes, respaldos y mantenimiento; no constituye una garantía absoluta.

<!-- BEGIN FIELD DICTIONARY -->
## Diccionario completo de la base de datos

Generado desde PostgreSQL con `python scripts/export_contracts.py`. NULL representa un dato desconocido; no es cero. Fechas y horas se presentan en Lima. `text` se limita en la API mediante Pydantic. FK indica relación; PK identifica la fila.

### empresas

Empresas propietarias de los proyectos.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `nombre` | `text` | Sí | `Sin valor; debe suministrarse` | — | Nombre visible. |
| `identificacion_tributaria` | `text` | No | `NULL` | — | Identificación tributaria; única si se informa. |
| `activo` | `boolean` | Sí | `true` | — | Registro habilitado. En usuarios, false impide el acceso. |

### usuarios

Identidad y acceso. Los roles se acumulan; la empresa no sustituye la asignación a proyectos.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `empresa_id` | `uuid` | No | `NULL` | empresas.id | Empresa a la que pertenece el registro. |
| `nombre` | `text` | Sí | `Sin valor; debe suministrarse` | — | Nombre visible. |
| `correo` | `text` | Sí | `Sin valor; debe suministrarse` | — | Correo de acceso, único y guardado en minúsculas; no se utiliza para enviar mensajes. |
| `hash_contrasena` | `text` | Sí | `Sin valor; debe suministrarse` | — | Hash Argon2id con salt y parámetros incluidos. No contiene contraseña recuperable y nunca se devuelve al navegador. |
| `roles` | `text_array` | Sí | `'{CLIENT}'::text[]` | — | Roles acumulables ADMIN, MANAGER, TECH y CLIENT. Debe existir al menos uno. |
| `activo` | `boolean` | Sí | `true` | — | Registro habilitado. En usuarios, false impide el acceso. |
| `creado_en` | `timestamptz` | Sí | `now()` | — | Instante de creación, almacenado con zona horaria. |

### proyectos

Proyectos de ingeniería que agrupan las solicitudes.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `empresa_id` | `uuid` | Sí | `Sin valor; debe suministrarse` | empresas.id | Empresa a la que pertenece el registro. |
| `codigo` | `text` | Sí | `Sin valor; debe suministrarse` | — | Código visible único. |
| `nombre` | `text` | Sí | `Sin valor; debe suministrarse` | — | Nombre visible. |
| `ubicacion` | `text` | Sí | `''::text` | — | Ubicación del proyecto. |
| `activo` | `boolean` | Sí | `true` | — | Registro habilitado. En usuarios, false impide el acceso. |

### miembros_proyecto

Acceso explícito de cada cliente a proyectos de su empresa.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `proyecto_id` | `uuid` | Sí | `Sin valor; debe suministrarse` | PK; proyectos.id | Proyecto propietario o asignado. |
| `usuario_id` | `uuid` | Sí | `Sin valor; debe suministrarse` | PK; usuarios.id | Usuario al que pertenece el acceso o la sesión. |

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

Solicitud y estado general; unidad de bloqueo y control de concurrencia.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `id` | `uuid` | Sí | `gen_random_uuid()` | PK | Identificador interno del registro; no acredita acceso. |
| `codigo` | `text` | Sí | `('SOL-'::text || lpad((nextval('numero_solicitud'::regclass))::text, 8, '0'::text))` | — | Correlativo visible SOL-00000001 generado por numero_solicitud. Los saltos de secuencia son normales. |
| `proyecto_id` | `uuid` | Sí | `Sin valor; debe suministrarse` | proyectos.id | Proyecto propietario o asignado. |
| `creado_por` | `uuid` | Sí | `Sin valor; debe suministrarse` | usuarios.id | Usuario que creó la solicitud. |
| `titulo` | `text` | Sí | `Sin valor; debe suministrarse` | — | Nombre o propósito del servicio solicitado. |
| `estado_solicitud` | `text` | Sí | `'DRAFT'::text` | — | Estado general: DRAFT, SUBMITTED, OBSERVED, APPROVED, REJECTED o CLOSED. |
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
| `cantidad` | `numeric` | No | `NULL` | — | Cantidad declarada, positiva; NULL significa desconocida. |
| `unidad` | `text` | Sí | `'kg'::text` | — | Unidad común para cantidad declarada y cantidad recibida. |
| `observaciones` | `text` | Sí | `''::text` | — | Observaciones declaradas por el cliente; describe aquí los componentes de una mezcla. |
| `recibido_en` | `timestamptz` | No | `NULL` | — | Fecha y hora efectivas de la última recepción; NULL si no llegó. |
| `recibido_por` | `uuid` | No | `NULL` | usuarios.id | Persona del laboratorio que registró la recepción actual. |
| `transporte` | `text` | Sí | `''::text` | — | Transporte, vehículo o persona que entregó la muestra. |
| `cantidad_recibida` | `numeric` | No | `NULL` | — | Cantidad recibida en la unidad de la muestra. Es un valor actual, no se suma automáticamente al corregir. |
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
| `interno` | `boolean` | Sí | `true` | — | true restringe el evento al personal interno. false permite verlo a los clientes del proyecto. |
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

Versiones del esquema instaladas. Esta base nueva comienza en la versión 3.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `version` | `integer` | Sí | `Sin valor; debe suministrarse` | PK | Versión instalada del esquema; clave primaria. La instalación actual inserta 3. |
| `aplicado_en` | `timestamptz` | Sí | `now()` | — | Instante de instalación de la versión del esquema. |

<!-- END FIELD DICTIONARY -->
