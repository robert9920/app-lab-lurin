# Guía de desarrollo · Laboratorio Lara Consulting v3

## Stack y alcance

Dos raíces desplegables: client (React JavaScript, Vite, Tailwind CSS) y api (Python 3.12, Azure Functions HTTP con blueprints). PostgreSQL mediante SQLAlchemy con consultas parametrizadas y pool acotado. No sustituir PostgreSQL por memoria o SQLite.

La instrucción del usuario reemplaza el flujo Entra de la skill azure-fullstack-entra-postgres. La aplicación usa cuentas propias y contraseña Argon2id, sesiones opacas y CSRF. No reintroducir MFA, Fernet, correo, invitaciones, enlaces de activación, recuperación por correo ni JWT propios. La identidad administrada de Azure para Blob es apropiada.

No se requieren agentes adicionales. Trabajar dentro de la tarea y conservar los cambios del usuario. No modificar Referencia ni la base anterior lab_lc.

## Modelo y reglas

- El esquema v3 tiene exactamente 13 tablas: empresas, usuarios, proyectos, miembros_proyecto, catalogo_ensayos, solicitudes, muestras, ensayos_muestra, informes, actividad, sesiones, limites_intentos y migraciones_esquema.
- Se instala en una base independiente lab_lc_v3. No migrar ni eliminar registros de lab_lc. El SQL inicial es versión 3; los próximos cambios necesitan nuevas migraciones.
- Una muestra mantiene su identidad desde solicitud hasta recepción. No introducir arribos, bultos, muestras duplicadas, órdenes ni custodia. Mezclas: una muestra y componentes en observaciones.
- Una pareja muestra_id/ensayo_id representa un ensayo y es única. Cantidades desconocidas son NULL; nunca confundirlas con cero.
- Una recepción conforme habilita iniciar/retomar/completar. Las condiciones restantes bloquean esas acciones. Las correcciones de recepción requieren motivo e historial, y no pueden invalidar material con ensayos RUNNING/COMPLETED.
- Un informe válido se hace visible al confirmar la carga. No hay publicación manual ni estado de análisis. Mantener PDF máximo 20 MiB/500 páginas, comprobación de estructura y contenido activo, almacenamiento privado y versión nueva en cada carga.
- Cerrar es una acción independiente de MANAGER: ensayos COMPLETED/CANCELLED e informe disponible. CLOSED permite lectura, sin modificaciones.
- Actas y etiquetas se generan bajo demanda desde los datos actuales; no se persisten.
- actividad y informes son inmutables mediante triggers. No borrar versiones ni historial. Correcciones y cancelaciones conservan motivo.
- Cambios multiobjeto transaccionales: bloquear solicitudes, comprobar version y aumentar el contador. Para lotes de varias solicitudes ordenar bloqueos por UUID. Un error revierte el lote completo.
- Dashboard consulta toda la base autorizada, nunca los primeros 100 registros de una lista. Definiciones y cada campo están en README.

## Seguridad y permisos

- CLIENT: acceso por miembros_proyecto; pertenecer a una empresa no basta. Sus asignaciones deben pertenecer a esa empresa.
- CLIENT adicional permite solicitudes y consulta pública del proyecto. No amplía operaciones de TECH: laboratory_access y can_receive siguen exigiendo asignación. Borradores exclusivos del autor en todos los casos.
- TECH: solicitudes con ensayos propios; solo sus ensayos y muestras. Recepción, actas y etiquetas limitadas a esas muestras; informes de solicitudes autorizadas. Dashboard personal.
- MANAGER: lectura global y operaciones de laboratorio, incluido cierre.
- ADMIN: usuarios, contraseñas y maestros; lectura global y dashboard. Operar requiere rol adicional MANAGER o TECH.
- UI es solo presentación. Resolver proyecto y propiedad de todos los IDs en el backend, incluidas muestras, ensayos y descargas.
- Leer roles/activo desde PostgreSQL en cada petición. Restablecer contraseña, deshabilitar o cambiar permisos revoca sesiones. Mantener un ADMIN activo.
- Nunca devolver hash_contrasena, hash_token, clave_archivo ni credenciales. No registrar contraseñas, cookies, CSRF, URL de conexión o contenido PDF. Los endpoints retornan errores genéricos.
- Notas técnicas se restringen al personal autorizado por ensayo. El JSON del historial no se devuelve al navegador; proyectar campos legibles y filtrar eventos de otras muestras/ensayos para TECH. Los eventos interno=true no se muestran al cliente. Observaciones de recepción y comentarios públicos sí son visibles en su proyecto.
- Configuración privada en api/local.settings.json o variables del servidor; no VITE_ secrets ni almacenamiento de credenciales en navegador.
- Cookies HttpOnly/SameSite y Secure en producción; Origin exacto y CSRF en escrituras. Límite de intentos persistente entre instancias.
- APP_ENV=production en Azure, HTTPS, PostgreSQL verify-full y Blob privado obligatorios. Prohibir UPLOAD_DIR dentro de client. api/.local se excluye de Git y del paquete Functions.

## Arquitectura y documentación

- blueprints: HTTP; services/workflow.py: reglas operativas; security.py: sesión/permisos; validation.py: modelos Pydantic que rechazan campos extra; services/storage.py: adaptadores local/Blob; services/documents.py: PDF.
- client/src/services/api.js centraliza Axios y descarga; AuthContext mantiene perfil y CSRF en memoria.
- Solicitudes, Recepción, Trabajo e Informes son vistas independientes. Filtros/pestaña/origen de regreso se conservan en URL. safeReturn limita destinos internos.
- Sin temporizadores ni procesos de correo/análisis. Limpieza acotada al login.
- README: arranque de dos ventanas Anaconda, reglas y diccionario de cada campo. docs/deployment.md: Azure y restauración. docs/verification.md: evidencia real.
- scripts/export_contracts.py exporta Mermaid, campos y OpenAPI y actualiza el diccionario del README. Ejecutar contra v3, nunca contra la base histórica. Regenerar también SVG con Mermaid CLI.
- No afirmar producción desplegada o seguridad absoluta sin comprobar el recurso real.

## Comandos

Desde client:

```text
npm ci
npm run dev
npm run lint
npm test
npm run build
npm audit
npm run test:e2e
```

Desde api, con conda activate lab-lc:

```text
python -m pip install -r requirements-dev.txt
python manage.py migrate
func start
python -m pytest -q
python -m ruff check blueprints services tests config.py database.py errors.py function_app.py http_helpers.py manage.py security.py validation.py
python -m ruff format blueprints services tests config.py database.py errors.py function_app.py http_helpers.py manage.py security.py validation.py
```

No pasar --exclude con valores que anulen la exclusión de entornos virtuales. Acotar los directorios de lint/formato al código. Tests solo contra lab_lc_v3_test, con TEST_DATABASE_URL; los fixtures usan rollback. E2E solo cuentas/proyectos ficticios, con Chrome y LAB_E2E_PASSWORD en entorno privado. No incorporar contraseñas de pruebas en SQL, comandos o código.

Mantener package-lock.json y el lock de dependencias Python de producción cuando cambien paquetes. Verificar permisos, sesiones, transiciones, PDF y métricas con datos de borde; no añadir pruebas triviales para cambios cosméticos.


## Reglas v3 adicionales

- Solo CLIENT redacta; borradores exclusivos del autor, sin excepción ADMIN/MANAGER. Retirar DRAFT del filtro de personal. Proteger también consulta directa y recursos derivados.
- `tecnico_id` es asignación independiente; nunca restaurar ASSIGNED como estado ni guardar un booleano duplicado. `allowed_actions` es autoritativo. OBSERVED solo proviene de RUNNING; resume exclusivo MANAGER vuelve a RUNNING manteniendo iniciado_en.
- Recepción exige codigo_recepcion/codigo_laboratorio manuales y normalizados. Laboratorio único; recepción compartible. No imprimir muestras no recibidas ni ajenas al técnico.
- Etiquetas de 95x68 mm, 2x4 en A4, separación 4 mm. Selección de hasta 200 muestras con paginación PDF automática. Renderizar y revisar antes de entregar cambios de formato.
- Actualizar schema_names.py al modificar nombres físicos; preservar JSON HTTP mediante mapeo explícito, no traducción SQL en runtime. Mantener exactamente 13 tablas y diccionario generado completo.
- No modificar ni eliminar lab_lc, lab_lc_v2. SQL v3 solo en base nueva. Reiniciar ambos servidores al cambiar DATABASE_URL a v3. No publicar configuraciones privadas.
- Pruebas de alcance: filtros, fichas, recepción, work, dashboard, historial, actas/etiquetas y PDF, incluidas asignaciones compartidas y borradores.
