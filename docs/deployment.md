# Publicación en Azure desde VS Code

Esta guía prepara recursos **nuevos**. Base oficial: `lab_lc` en Azure PostgreSQL Flexible Server. Local: `lab_lc_v3`. Ambos usan esquema 3; el número del esquema no forma parte del nombre de producción. No modificar bases históricas locales. La aplicación no está certificada como desplegada por ejecutar pruebas locales.

## 1. Recursos y red antes de publicar

Crear en una misma región con disponibilidad de Flex: App Service Linux **Basic B1 / Node 24 LTS**, Functions **Flex Consumption / Python 3.12 / 2048 MB**, PostgreSQL Flexible Server PostgreSQL 17, almacenamiento del host de Functions, almacenamiento de informes StorageV2 Standard y Application Insights. B1 es punto inicial, no una capacidad garantizada; observar carga y ajustar. B1 y Flex no ofrecen el flujo de slots descrito para otros planes: conservar paquetes/configuraciones para reversión. No habilitar Easy Auth: los usuarios acceden con correo y contraseña propios.

Red propuesta `10.40.0.0/16` (cambiar si se superpone con redes corporativas):

| Subred | CIDR | Uso/delegación |
|---|---|---|
| portal | 10.40.1.0/26 | Integración saliente App Service; Microsoft.Web/serverFarms |
| functions | 10.40.2.0/24 | Integración Flex; Microsoft.App/environments |
| endpoints | 10.40.3.0/24 | Endpoints privados, sin delegación |
| GatewaySubnet | 10.40.4.0/27 | VPN Gateway; nombre obligatorio |
| dns-inbound | 10.40.5.0/28 | Azure DNS Private Resolver, Microsoft.Network/dnsResolvers |

Crear VPN Gateway basado en rutas, SKU VpnGw1, conexión punto a sitio OpenVPN, autenticación por certificado y pool de clientes `172.20.100.0/24` sin solapamientos. Instalar certificado cliente y perfil VPN solo en equipos de operación; nunca en el repositorio. Crear Private Resolver inbound en su subred y configurar su IP como DNS del perfil VPN; volver a descargar el perfil al modificar DNS. Integrar App Service y Functions en sus subredes respectivas.

Crear PostgreSQL con modo de red que admita **Private Endpoint** (no mezclar con el modo de subred delegada de PostgreSQL); crear endpoint y deshabilitar acceso público después de verificar conectividad. Crear endpoints privados para Functions y Blob de informes. Vincular a la VNet las zonas `privatelink.azurewebsites.net`, `privatelink.postgres.database.azure.com` y `privatelink.blob.core.windows.net`; aceptar los grupos DNS automáticos del endpoint. La zona de App Service debe incluir los registros de Functions y su SCM cuando corresponda. App Service del portal conserva entrada pública HTTPS para clientes externos; Functions, PostgreSQL e informes quedan privados.

El almacenamiento del host y el contenedor de despliegue de Flex son distintos de los informes. Conservar la configuración generada al crear Flex y aplicar los endpoints Blob/Queue/Table que use el host, sus zonas privadas y acceso desde la subred Functions antes de deshabilitar su red pública. No eliminar contenedores de despliegue ni de claves. No aplicar permisos del contenedor de informes como sustituto de los permisos del host.

Antes de publicar: desde el equipo conectado a VPN, resolver con `Resolve-DnsName` los nombres normales de Functions, PostgreSQL y Storage; deben resolver a IP privadas. Probar 443 y 5432 con `Test-NetConnection`. Usar siempre el hostname normal, no una IP ni el nombre privatelink en las conexiones TLS. Si falla DNS/VPN, corregirlo antes del despliegue; no abrir temporalmente todos los servicios a Internet.

Referencias: [integración App Service](https://learn.microsoft.com/en-us/azure/app-service/overview-vnet-integration), [red de Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options), [VPN punto a sitio](https://learn.microsoft.com/en-us/azure/vpn-gateway/point-to-site-about).

## 2. PostgreSQL desde cero

Desde el equipo de operación conectado por VPN, usando VS Code con cliente PostgreSQL o psql:

1. Conectado a `postgres`, ejecutar `sql/00_create_database.sql` fuera de transacción. Crea **lab_lc**. No usar el script local.
2. Cambiar conexión a `lab_lc` y ejecutar `sql/01_schema.sql` y después `sql/02_catalog.sql`.
3. **No ejecutar `03_demo.sql`** en producción.
4. Crear rol LOGIN `lab_runtime` sin superusuario, CREATEDB ni CREATEROLE. Asignar contraseña con un diálogo seguro o `\password lab_runtime` en psql. Conservar al propietario del esquema como cuenta de instalación separada.
5. Como propietario ejecutar `sql/04_runtime_permissions.sql` en `lab_lc`. El script usa la base de la conexión; verificarla antes con `SELECT current_database();`.
6. Inicializar el primer administrador con `python manage.py bootstrap` desde `api` en el equipo autorizado, con variables privadas de producción. El comando pregunta correo, nombre y contraseña sin eco. Usar la cuenta runtime para esta operación. Las variables de entorno prevalecen sobre local.settings.json; abrir una ventana exclusiva y cerrarla al finalizar.

En local el script de creación es `00_create_database_local.sql`, seguido de 01, 02 y opcionalmente 03. No se cambia tu `local.settings.json`. `manage.py migrate` acepta los nombres previstos y exige base vacía o esquema compatible; `demo` rechaza siempre `lab_lc`, incluso si APP_ENV se configura mal.

TLS: `sslmode=verify-full`. Se incluye api/certs/azure-postgresql-roots.pem, descargado de los emisores oficiales y verificado el 11/09/2026. Para renovarlo, descargar desde la documentación oficial los certificados raíz públicos **DigiCert Global Root G2** y **Microsoft RSA Root CA 2017**, verificando emisor y vigencia; concatenar PEM en `api/certs/azure-postgresql-roots.pem`. No incorporar certificados intermedios, certificados de servidor ni claves privadas. El paquete admite ese directorio. Usar en Linux `sslrootcert=/home/site/wwwroot/certs/azure-postgresql-roots.pem`; comprobar que exista tras el despliegue. Si el montaje del plan usa otra ruta, configurar la ruta real antes del primer acceso. [TLS y rotación de certificados](https://learn.microsoft.com/en-us/azure/postgresql/security/security-tls).

## 3. PDF: cuenta y contenedor

Crear cuenta StorageV2 Standard, redundancia ZRS donde esté disponible, acceso seguro obligatorio, TLS mínimo 1.2, acceso anónimo de blobs deshabilitado y espacio de nombres jerárquico desactivado. Crear contenedor **lab-informes**, nivel de acceso **Private**. Deshabilitar acceso público de red tras comprobar endpoint privado/DNS. No habilitar sitio web estático ni CORS: el navegador descarga mediante la API.

Habilitar identidad administrada de sistema en Functions. En IAM del contenedor lab-informes, asignarle **Storage Blob Data Contributor**, con alcance del contenedor. Esperar propagación RBAC. `DefaultAzureCredential` usa esa identidad en Azure; no necesita una clave de cuenta para los PDF. Deshabilitar acceso mediante claves compartidas en esta cuenta dedicada si ningún otro consumidor lo requiere.

No crear carpetas: la aplicación genera claves de archivo por solicitud e informe. `informes.clave_archivo` guarda esa referencia; PostgreSQL no contiene el PDF. Cada carga conserva una versión propia. Activar versionado de blobs, eliminación temporal de blobs y contenedores con 30 días iniciales de retención. Ajustar la retención a la política empresarial y evitar reglas lifecycle que eliminen archivos todavía referenciados.

## 4. Variables de Functions y publicación del backend

Plantillas sin secretos en `docs/settings/functions.example.json` y `docs/settings/app-service.example.json`, formato de edición avanzada del portal. Reemplazar marcadores en una copia privada; combinar con los ajustes existentes, no reemplazar la configuración del host. No guardar la copia con secretos en el proyecto.

| Variable propia | Valor |
|---|---|
| APP_ENV | production |
| APP_ORIGIN | https://HOST-PORTAL; origen exacto sin ruta/barra final |
| DATABASE_URL | postgresql+psycopg://lab_runtime:CLAVE_URL_ENCODED@HOST.postgres.database.azure.com:5432/lab_lc?sslmode=verify-full&sslrootcert=/home/site/wwwroot/certs/azure-postgresql-roots.pem |
| STORAGE_MODE | azure |
| STORAGE_ACCOUNT_URL | https://CUENTA-INFORMES.blob.core.windows.net |
| STORAGE_CONTAINER | lab-informes |
| SESSION_IDLE_MINUTES | 30 |
| SESSION_HOURS | 8 |

Codificar caracteres especiales de usuario/contraseña en la URL; nunca poner la URL en comandos compartidos, logs o capturas. Configurar secretos en variables privadas del servicio o referencias Key Vault. No subir local.settings.json. No definir UPLOAD_DIR en Azure. Mantener los ajustes generados para almacenamiento del host y Application Insights. Para esta instalación inicial usar la conexión protegida de almacenamiento del host generada por Azure; su acceso de red privado debe funcionar. Migrar ese host a identidad requiere sus roles específicos, no solo el permiso de informes.

**Flex:** Python y versión 3.12 son propiedades del runtime del recurso. No copiar como ajustes `FUNCTIONS_WORKER_RUNTIME`, `FUNCTIONS_EXTENSION_VERSION`, `WEBSITE_RUN_FROM_PACKAGE`, `SCM_DO_BUILD_DURING_DEPLOYMENT` ni `ENABLE_ORYX_BUILD` de guías para otros planes. Tampoco Always On; Flex utiliza opciones propias de escalado/always ready. Empezar sin instancias always ready y con concurrencia HTTP 4; revisar latencia de arranque y conexiones antes de abrir acceso amplio. El pool permite hasta cinco conexiones por proceso; dimensionar máximo de instancias y presupuesto de PostgreSQL conjuntamente.

Instalar extensión Azure Functions de VS Code, iniciar sesión en la suscripción correcta y **abrir api como carpeta del workspace**. Seleccionar `Azure Functions: Deploy to Function App...`, destino Flex correcto, con compilación remota. La raíz publicada debe contener host.json, function_app.py y requirements.txt. Incluir requirements.lock.txt, schema_names.py, blueprints, services, módulos comunes, logo y certificados públicos. `.funcignore` excluye secretos, PDFs locales, entornos, cachés, pruebas y manage.py. No copiar dependencias de Windows a Linux.

Comprobar en logs que se instalaron requisitos y se descubrieron funciones. Crear/obtener una **host function key** para que el proxy pueda invocar todas las rutas; no usar la master key. Guardarla solo en App Service. Mantener AuthLevel.FUNCTION además de la sesión del usuario. Sin CORS comodín ni Easy Auth. [Despliegue remoto](https://learn.microsoft.com/en-us/azure/azure-functions/functions-deployment-technologies), [ajustes de Flex](https://learn.microsoft.com/en-us/azure/azure-functions/functions-app-settings#flex-consumption-plan).

## 5. Frontend: VS Code, build y arranque

`npm run build` genera únicamente `dist`; **no comprime la aplicación ni incluye el servidor proxy**. La ruta principal es publicar **client completo con exclusiones**, y construir en Azure. No seleccionar dist.

1. Abrir `client` como carpeta en VS Code para aplicar su `.vscode/settings.json`.
2. Verificar localmente `npm ci`, `npm run lint`, `npm test`, `npm run build`.
3. App Service: publicación de código, Linux, Node **24 LTS**, B1; HTTPS Only, TLS mínimo 1.2, Always On habilitado; integración VNet configurada. No contenedor personalizado.
4. Definir las variables de la tabla siguiente antes de publicar.
5. Extensión Azure App Service → **Deploy to Web App...** → seleccionar client y el recurso correcto. Confirmar despliegue con build remoto. Se incluyen src, public, index.html, vite.config.js, package.json, package-lock.json, server.mjs y ecosystem.config.cjs. Se excluyen dist local, node_modules, pruebas, secretos y archivos privados.
6. Confirmar en logs restauración de dependencias y ejecución de Vite. Verificar que dist/index.html exista en la aplicación publicada.
7. Comando de inicio: **`pm2 start ecosystem.config.cjs --no-daemon`**. El PM2 provisto por la imagen Node supervisa server.mjs en primer plano. `npm start` sigue disponible para ejecutar localmente el paquete construido. No usar vite preview en producción.

| Variable App Service | Valor |
|---|---|
| NODE_ENV | production |
| SCM_DO_BUILD_DURING_DEPLOYMENT | true (solo App Service, no Flex) |
| NPM_CONFIG_PRODUCTION | false (Vite/Tailwind necesitan devDependencies al construir) |
| API_TARGET | https://HOST-FUNCTIONS.azurewebsites.net, sin /api |
| FUNCTION_PROXY_KEY | host function key privada |

No fijar PORT: el servidor utiliza el puerto de la plataforma. No definir secretos VITE_. Health Check `/healthz` verifica el proceso del portal, no la disponibilidad de PostgreSQL/Blob; monitorizar adicionalmente operaciones reales. No publicar mapas de código con secretos ni habilitar logs de cuerpos/cookies.

VS Code comprime los archivos al publicar. `.gitignore` controla Git, **no sustituye** appService.zipIgnorePattern ni `.funcignore`. Si se abre la raíz del monorepo, los ajustes anidados no se aplican: abrir cada carpeta por separado como se indica.

[Node, build y PM2 en App Service](https://learn.microsoft.com/en-us/azure/app-service/configure-language-nodejs).

## 6. Aceptación antes de admitir clientes

- Revisar el paquete: sin configuraciones privadas, PDFs locales, claves o entornos Windows; con lockfiles, logo y CA públicos.
- Probar /healthz, login, persistencia de sesión, cierre y revocación con ADMIN y cuenta creada desde la plataforma.
- Probar nuevo proyecto y sus asignaciones; empresa ajena denegada; selección de proyectos editable.
- Probar CSRF/origen incorrectos, borradores exclusivos y técnicos compartiendo solicitud sin ampliar alcance.
- Cargar PDF válido hasta 20 MiB, descargarlo con usuario autorizado y denegar otra empresa. Confirmar acceso anónimo al blob denegado y disponibilidad inmediata de la versión nueva.
- Recargar una URL interna y comprobar proxy, cookies Secure/HttpOnly/SameSite y filtros.
- Verificar DNS privado desde App Service/Functions y acceso administrativo por VPN. La URL pública de Functions no debe permitir acceso desde fuera de la red.
- Application Insights: alertas 5xx, latencia, fallos Blob y saturación/conexiones de PostgreSQL; no registrar credenciales ni documentación.

## 7. Respaldos y reversión

Configurar PostgreSQL PITR con retención inicial de 30 días y probar una restauración. Ajustar RPO/RTO con el responsable. Copia lógica opcional: `pg_dump -h HOST -U OPERADOR -d lab_lc -Fc -f lab_lc_FECHA.dump`, contraseña interactiva o PGPASSFILE privado, TLS verificado. Respaldar también los blobs/versiones referenciados: el dump no contiene los PDF.

Restaurar a base nueva con `pg_restore --no-owner --no-privileges --exit-on-error`, sin ejecutar antes 01_schema.sql. Reaplicar permisos runtime. Restaurar archivos a contenedor privado de recuperación y conciliar tamaño/SHA256. Revocar sesiones restauradas antes de habilitar tráfico. Mantener el servicio en mantenimiento durante la restauración coordinada.

Conservar paquetes frontend/API y configuración de la misma entrega. B1/Flex: revertir ambos mediante redespliegue del paquete anterior; no dar instrucciones de swap de slots inexistentes. No apuntar una entrega a un esquema incompatible. Cualquier cambio futuro de esquema necesita estrategia de reversión propia.

Una carga escribe Blob antes del commit SQL: un fallo puede dejar un archivo huérfano invisible a usuarios. Su limpieza requiere conciliación con informes y antigüedad de seguridad, nunca borrar objetos recientes automáticamente. Probar recuperación periódicamente. Recursos privados, VPN, DNS Resolver y respaldos generan costes adicionales a App Service/Functions.
