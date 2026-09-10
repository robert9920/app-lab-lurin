# Puesta en producción · v3

## Recursos y separación

Crear recursos dedicados o un slot de preparación: App Service Linux para Node, Function App Linux Python 3.12 con runtime v4, PostgreSQL Flexible Server, una cuenta privada de Blob para informes y el almacenamiento requerido por el host de Functions. Usar la base **lab_lc_v3**, sin restaurar ni migrar automáticamente lab_lc.

El navegador se comunica únicamente con el origen HTTPS de App Service. server.mjs sirve dist y reenvía /api a una URL fija de Functions. La clave de Functions se agrega en el servidor Node. No se expone al navegador. Las cuentas del portal son propias; no configurar Easy Auth/Entra para el ingreso de los usuarios de este producto.

El arranque requerido es npm start. El servidor respeta PORT. Microsoft admite comandos personalizados y documenta npm start; actualmente recomienda PM2 para la supervisión de procesos en producción. Mantener npm start para este piloto, configurar reinicio/health check/Always On cuando el plan lo permita y evaluar supervisión antes de ampliar el servicio. [Configuración oficial de Node en App Service](https://learn.microsoft.com/en-us/azure/app-service/configure-language-nodejs).

## Preparar PostgreSQL

1. Crear lab_lc_v3 conectado a postgres, con un operador autorizado. Ejecutar 01_schema.sql y 02_catalog.sql conectado a la nueva base.
2. No ejecutar 03_demo.sql en producción.
3. Usar una cuenta de migraciones propietaria del esquema y una cuenta de ejecución limitada diferente, por ejemplo lab_runtime. Establecer la contraseña mediante herramienta segura, no incorporarla al SQL.
4. Ejecutar sql/04_runtime_permissions.sql después de crear lab_runtime. No otorgar al runtime privilegios de crear/borrar tablas ni de modificar los triggers de historial.
5. Configurar TLS con verificación del nombre y CA: sslmode=verify-full y sslrootcert apuntando al certificado CA vigente y confiable de Azure PostgreSQL. Instalar el certificado público en el paquete o sistema; nunca incluir claves privadas.
6. Restringir la red al backend. Usar integración VNet y endpoint privado cuando el plan elegido lo admita; limitar firewall a orígenes necesarios.
7. Inicializar el primer ADMIN mediante manage.py bootstrap desde un equipo de operación con acceso a la base y configuración privada APP_ENV=production. Después crear usuarios en el portal y otorgar los roles operativos necesarios.

## Configuración privada de Function App

| Variable | Valor / requisito |
|---|---|
| FUNCTIONS_WORKER_RUNTIME | python |
| FUNCTIONS_EXTENSION_VERSION | ~4 |
| APP_ENV | production |
| APP_ORIGIN | https://dominio-del-portal, sin ruta ni barra final |
| DATABASE_URL | postgresql+psycopg://lab_runtime:CONTRASENA_CODIFICADA@HOST:5432/lab_lc_v3?sslmode=verify-full&sslrootcert=/ruta/ca.pem |
| STORAGE_MODE | azure |
| STORAGE_ACCOUNT_URL | https://CUENTA.blob.core.windows.net |
| STORAGE_CONTAINER | lab-informes, creado previamente con acceso público deshabilitado |
| SESSION_IDLE_MINUTES | 30 o valor acordado |
| SESSION_HOURS | 8 o valor acordado |
| AzureWebJobsStorage | Configuración protegida de la cuenta del host, según el plan Functions |

Habilitar identidad administrada de Functions y asignarle Storage Blob Data Contributor **al contenedor de informes**, no a toda la suscripción. services/storage.py usa DefaultAzureCredential. Deshabilitar acceso anónimo de la cuenta, mantener contenedor privado y HTTPS. El acceso privado de red y su resolución DNS deben funcionar desde Functions. No se generan SAS ni enlaces públicos de descarga.

La cuenta del host de Functions es una dependencia de Azure aunque no haya timers. Si se configura mediante identidad administrada, seguir la configuración y roles del host del plan seleccionado; no confundir esos permisos con los del contenedor de informes. [Almacenamiento de Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/storage-considerations).

Las credenciales y referencias de Key Vault se administran en configuración del servicio. No publicar local.settings.json. Eliminar de los recursos anteriores las variables FERNET_KEY, MFA, MAIL, SMTP y almacenamiento emulado. No crear procesos de envío ni análisis de documentos.

## Publicar backend

Validar pruebas y dependencias antes de publicar. Desde api:

```text
func azure functionapp publish NOMBRE_FUNCTION_APP --python
```

O desplegar api con la extensión Azure Functions de VS Code y compilación remota habilitada. Seleccionar Python 3.12. requirements.txt incluye requirements.lock.txt con las 35 versiones auditadas de la entrega; requirements.in conserva los requisitos para futuras actualizaciones. No copiar un entorno Anaconda o .venv de Windows a Linux.

.funcignore excluye configuraciones locales, .local, pruebas y manage.py. Confirmar que el paquete contenga function_app.py, blueprints, services, security.py, validation.py, config.py, database.py, schema_names.py, http_helpers.py, errors.py, host.json y data/logo.png.

Todos los endpoints usan AuthLevel.FUNCTION además de autorización de la aplicación. Obtener una Function Key para el proxy y almacenarla solo en App Service. Restringir acceso de red de Functions al frontend o a la red del servicio. No habilitar CORS comodín: el navegador utiliza el proxy del mismo origen.

## Publicar frontend

Configurar App Service Linux con una versión Node soportada compatible con Node >=22. Preparar desde client:

```text
npm ci
npm run lint
npm test
npm run build
```

Publicar un paquete cuya raíz contenga **server.mjs, package.json, package-lock.json y dist/**. Restaurar dependencias de producción con npm ci --omit=dev en el proceso de despliegue Linux. Si se construye en App Service, incluir src, index.html y vite.config.js y permitir las devDependencies durante el build. No publicar solo dist ni node_modules de Windows.

Variables privadas del servidor:

| Variable | Valor |
|---|---|
| NODE_ENV | production |
| API_TARGET | https://NOMBRE_FUNCTION_APP.azurewebsites.net (sin /api) |
| FUNCTION_PROXY_KEY | Clave de Functions, privada |
| PORT | Definida por la plataforma |

Configurar comando de inicio **npm start**. HTTPS Only, TLS mínimo vigente, redirección HTTP a HTTPS, certificado del dominio y APP_ORIGIN coincidente. El proxy agrega cabeceras Helmet y limita intentos por IP; PostgreSQL comparte el límite por correo entre instancias. No se necesitan variables VITE_ de autenticación.

## Comprobar antes de abrir acceso

- Probar login con ADMIN, MANAGER, TECH y clientes de dos proyectos distintos.
- Verificar cookies HttpOnly, Secure y SameSite; escritura sin CSRF/origen inválido debe fallar.
- Comprobar revocación al cambiar contraseña o deshabilitar, y caducidad de sesión.
- Descargar un PDF autorizado y comprobar que modificar su UUID o proyecto no permita acceso a otro cliente.
- Cargar un PDF nuevo, verificar acceso inmediato y conservación de la versión anterior.
- Registrar recepción parcial y comprobar bloqueo de material observado.
- Recargar URLs de solicitudes, recepción, trabajo e informes; comprobar regreso con filtros.
- Conciliar dashboard con SQL. Revisar Application Insights sin registrar cuerpos, cookies, tokens ni URL de conexión.
- Comprobar límites de 20 MiB en API y plataforma. Rechazar archivos sobredimensionados antes del backend en el gateway si se añade uno.
- Guardar el paquete de aplicación y una copia de seguridad de base/documentos antes del cambio de slot.

## Respaldos y restauración

Definir retención y objetivos de pérdida/tiempo de recuperación con el propietario del servicio. Activar copias automáticas y recuperación a un instante en PostgreSQL Flexible Server. Activar versionado/soft delete de Blob según políticas de retención. [Respaldo y restauración de PostgreSQL Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-backup-restore).

Para copia lógica adicional con pg_dump de versión compatible, usar PGPASSFILE privado o solicitud interactiva de contraseña; no argumentos que la expongan:

```text
pg_dump -h HOST -p 5432 -U USUARIO_RESPALDO -d lab_lc_v3 -Fc -f lab_lc_v3_FECHA.dump
```

Respaldar también los objetos referenciados en informes.clave_archivo. El dump solo contiene metadatos; **no contiene los PDF**. En local incluir api/.local/uploads; en Azure conservar los blobs/versiones correspondientes y su cuenta/contendor. El cifrado, acceso y retención de las copias son tan importantes como los de producción.

Para restaurar, crear una base **nueva vacía**, restaurar el dump con pg_restore --no-owner --no-privileges --exit-on-error y aplicar de nuevo los permisos al runtime. No ejecutar 01_schema.sql antes de restaurar un dump con esquema completo. Restaurar documentos en un contenedor privado aparte y verificar tamaño/SHA-256 contra informes. El backend acepta un nombre alternativo de base en DATABASE_URL para recuperación; manage.py migrate/demo solo admite los nombres del piloto para prevenir errores operativos.

Revocar todas las sesiones de la base restaurada con DELETE FROM sesiones antes de ponerla en servicio; limpiar limites_intentos si corresponde. Configurar un slot con APP_ENV=production y las conexiones nuevas, comprobar permisos y recorrido completo, y solo después cambiar tráfico. Probar esta recuperación regularmente; la mera existencia de un archivo dump no confirma que la restauración funcione.

## Operación

Supervisar errores 5xx, latencia, saturación del pool, conexiones PostgreSQL y fallos de Blob. El máximo por proceso es pool_size=2 + max_overflow=3; considerar número de workers e instancias. Mantener dependencias y runtimes actualizados.

Las cargas escriben Blob antes del commit de metadatos. Un fallo de base después de cargar puede dejar un archivo huérfano; nunca queda visible sin una fila informes. Revisar huérfanos en una tarea de operación con respaldo y antigüedad de seguridad, no borrarlos automáticamente mientras haya cargas activas. No hay temporizadores de negocio.

La versión nueva no altera lab_lc ni lab_lc_v2. Para volver a la aplicación anterior, restaurar su paquete y su configuración original apuntando a la base que utilizaba (lab_lc_v2 para código v2), después de valorar qué operaciones nuevas existen solo en v3. No mezclar esquemas: desplegar frontend/API v3 juntos con lab_lc_v3. Conservar paquete y conexión v2 para revertir; no existe migración histórica automática.


Validar además borradores exclusivos del autor, aislamiento entre técnicos en una solicitud compartida, indicador de muestras sin recibir, asignación independiente del estado y etiquetas de 95×68 mm.
