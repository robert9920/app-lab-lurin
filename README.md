# Laboratorio Lara Consulting · esquema 4

Aplicación de solicitudes, recepción, ensayos e informes. React JavaScript, Vite y Tailwind CSS en `client`; Python 3.12 y Azure Functions HTTP en `api`; PostgreSQL como persistencia real. Interfaz en español, fechas presentadas en America/Lima.

## Cambios y compatibilidad

Producción conserva la base **lab_lc** y local **lab_lc_v3**. Los nombres JSON existentes se conservan mediante api/schema_names.py (por ejemplo weight → peso, easting/northing → coordenada_este/coordenada_norte). El número del esquema, ahora **4**, es independiente del nombre de la base. No se requiere crear otra base para actualizar. Hay once tablas; se retiraron `proyectos` y `miembros_proyecto`. El proyecto es un código de texto en `solicitudes.proyecto_id`, sin FK entre bases. `empresa_id` conserva la empresa de la solicitud aunque después se cambie la empresa del autor.

El acceso sigue usando contraseña Argon2id, sesiones opacas y CSRF. El administrador crea usuarios y restablece contraseñas; no se envían correos ni enlaces. Sin MFA, invitaciones ni FERNET_KEY. Fernet cifraba secretos de funciones retiradas y nunca intervino en el hash de contraseñas. No se puede recuperar una contraseña del hash.

## Actualizar una instalación existente

1. Respaldar PostgreSQL y los PDF; suspender temporalmente el acceso y detener ambos servidores locales o poner el portal desplegado en mantenimiento.
2. Verificar `SELECT current_database(); SELECT max(version) FROM migraciones_esquema;`. Debe ser la base deseada y versión 3.
3. Ejecutar **sql/05_actualizacion_solicitudes.sql**, completo, con el propietario del esquema. No volver a ejecutar 01 ni 03. La migración es transaccional, conserva IDs, muestras, ensayos, informes, historial y sesiones; convierte los UUID de proyecto en sus códigos existentes y elimina las dos tablas de proyectos.
4. Añadir `PROJECTS_DATABASE_URL` al backend, actualizar ambos paquetes y reiniciar los servidores.
5. En Administración → Empresas → Editar, marcar la empresa interna. Solo puede existir una; las otras son externas. Revisar las cuentas y probar una solicitud interna y una externa.

Las cantidades existentes se conservan numéricamente como **sacos**; no se convierten a peso. Si hay cantidades fraccionarias o no finitas, 05 aborta antes de modificar el esquema: revisar con el laboratorio y corregir explícitamente antes de reintentar. Los nuevos pesos, geografía y OT quedan NULL en registros históricos; no se inventan valores. Al editar una solicitud histórica se deberán completar distrito, provincia y departamento. Las coordenadas este y norte permanecen opcionales, incluso al editar.

Las solicitudes existentes conservan su código de proyecto, incluido un código antiguo de un cliente externo. Las nuevas externas usan `EXTERNO`. Los ensayos ya RUNNING conservan observar/completar aunque su solicitud antigua no tenga OT; para nuevas asignaciones, inicio o reanudación se necesita OT.

## Instalación local con dos ventanas de Anaconda

Requisitos: Anaconda/Miniconda, PostgreSQL en ejecución, Python 3.12, Node.js 24 LTS y Azure Functions Core Tools v4. No se utilizan Docker, Azurite ni buzones de correo.

### Base vacía

En pgAdmin conectado a `postgres`, ejecutar `sql/00_create_database_local.sql` fuera de transacción. Cambiar a `lab_lc_v3` y ejecutar en orden `01_schema.sql`, `02_catalog.sql` y, solo para demostración, `03_demo.sql`. 01 instala directamente esquema 4. **No ejecutar 05 después de 01**, pues 05 solo actualiza esquema 3. `04_runtime_permissions.sql` concede permisos a una cuenta PostgreSQL limitada opcional, distinta de los roles de usuarios del portal; quien utilice una cuenta existente debe revisar sus permisos. En Azure, el SQL 00 oficial crea `lab_lc`.

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

`migrate` instala una base vacía o actualiza esquema 3 con 05; no lo ejecutar mientras la versión anterior esté sirviendo peticiones. `bootstrap` inicializa el administrador sin contraseña incorporada. Para datos ficticios: `python manage.py demo`, después `python manage.py password --email admin@example.com` y repetir para las cuentas a usar. `demo` rechaza lab_lc para proteger producción; si se desea una prueba pública con SQL ficticio, cargarlo manualmente y establecer contraseñas desde una ventana privada. Nunca cargar demostración sobre datos reales.

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
- **Envío:** se admiten muestras sin ensayos. Si alguna carece de ellos, el estado es WAITING_ASSAYS / Pendiente de ensayos. Cuando todas tengan ensayos, pasa a SUBMITTED / En revisión. Ambos estados ya son visibles para jefatura y permiten recepción.
- **Edición:** el autor CLIENT puede editar antes de aprobación, también después de enviar. Desde el envío, el proyecto no cambia. Una muestra recibida conserva su identidad y datos declarados: no se elimina ni se modifica; se pueden incorporar ensayos después. Cambios concurrentes devuelven conflicto para recargar antes de reintentar.
- **Recepción:** jefatura recibe solicitudes enviadas, incluso pendientes de ensayos. TECH recibe solo muestras asignadas de solicitudes aprobadas. Sacos y peso recibidos son datos independientes de los declarados; fecha/hora y transporte se aplican al grupo seleccionado. Recepciones parciales y correcciones mantienen historial y motivo.
- **OT:** botón Generar OT en Recepción, exclusivo jefatura; código manual normalizado. Requiere al menos una muestra recibida, aunque esté observada/dañada/insuficiente y falten otras. No habilita por sí sola material no conforme. Cambiar una OT exige motivo. Un único texto por solicitud; no se crea tabla de órdenes.
- **Aprobación:** todas las muestras deben tener al menos un ensayo; aprobación independiente de la recepción. Asignar/programar ensayos requiere solicitud aprobada y OT. Iniciar/retomar exige además responsable y muestra conforme. Asignación no cambia el estado.
- **Estados:** pendiente ámbar, ejecución azul, observado rojo, completado verde, cancelado gris. Responsable/jefatura pueden observar/completar solamente después de iniciar. Solo jefatura cancela o retoma con motivo; retomar conserva la fecha inicial. La selección masiva muestra solo acciones válidas para todos y es atómica.
- **Informes:** PDF privado, máximo 20 MiB/500 páginas, sin cifrado ni contenido activo. Técnicos/jefatura cargan en solicitudes aprobadas; disponibilidad inmediata para usuarios autorizados. Cada carga conserva un archivo y versión. Las comprobaciones técnicas no son un escáner antimalware. Cierre separado de jefatura: ensayos resueltos e informe disponible.
- **Actas y etiquetas:** bajo demanda, sin almacenamiento histórico adicional. Etiquetas A4, 95×68 mm, 2×4, separación 4 mm; tamaño real/100 %, ocho por página. Código recepción compartible y código laboratorio único; ambos manuales obligatorios al recibir. Se conservan cliente, código proyecto, muestra, punto y profundidad; sin UR ni OT en la etiqueta.

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

Las pruebas PostgreSQL requieren TEST_DATABASE_URL apuntando exclusivamente a una base ficticia admitida, por ejemplo lab_lc_v4_test. E2E usa LAB_E2E_URL y LAB_E2E_PASSWORD privados y cuentas ficticias. No usar bases reales. Resultados y limitaciones: [docs/verification.md](docs/verification.md). Contrato: [docs/openapi.json](docs/openapi.json). ERD: [Mermaid](docs/database.mmd) y [SVG](docs/database.svg). Publicación y actualización de Azure: [docs/deployment.md](docs/deployment.md).

Git, VS Code App Service y Functions tienen exclusiones independientes. No publicar .env, local.settings.json, .local, PDF locales, cachés, entornos ni node_modules Windows; sí lockfiles y certificados públicos. El frontend publicado requiere dist más server.mjs y sus dependencias; npm run build no crea un ZIP ni agrega el proxy. Se mantienen las configuraciones de despliegue existentes. La actualización necesita únicamente la conexión privada al catálogo y permisos de lectura además del SQL y ambos paquetes.

Los controles de aplicación no son una garantía absoluta de seguridad de Azure. Mantener HTTPS, verify-full, Blob privado, copias y restauración coordinada con los informes; probar la nueva entrega en los recursos reales antes de habilitar usuarios.

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
| `estado_solicitud` | `text` | Sí | `'DRAFT'::text` | — | DRAFT, WAITING_ASSAYS, SUBMITTED, OBSERVED, APPROVED, REJECTED o CLOSED. |
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

Versiones instaladas, independientes del nombre de la base. El esquema actual es 4.

| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |
|---|---|---|---|---|---|
| `version` | `integer` | Sí | `Sin valor; debe suministrarse` | PK | Versión instalada, PK. Instalación limpia: 4; una migración conserva además el registro 3. |
| `aplicado_en` | `timestamptz` | Sí | `now()` | — | Instante de instalación de la versión del esquema. |

<!-- END FIELD DICTIONARY -->
