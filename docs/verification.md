# Verificación de la versión 3

Ejecutada el 9 de septiembre de 2026 (Lima), con datos ficticios y PostgreSQL real. No se desplegaron ni verificaron recursos Azure en esta entrega.

## Resultados

| Comprobación | Resultado |
|---|---|
| pytest, base independiente lab_lc_v3_test | 26 pruebas aprobadas |
| Vitest | 4 pruebas aprobadas |
| Playwright / Chrome | 4 recorridos aprobados (administración, navegación/recepción/informes, cliente y técnico) |
| ESLint | Sin errores ni advertencias |
| Ruff, código y pruebas del backend | Sin errores |
| Vite build v3 | Compilación de producción correcta |
| npm audit | 0 vulnerabilidades conocidas en la consulta de esta fecha |
| Creación de esquema desde cero | lab_lc_v3 y lab_lc_v3_test creadas y cargadas con SQL 01/02/03 |
| Contratos | 13 tablas, 92 campos documentados y 25 rutas OpenAPI |
| Diagrama Mermaid/SVG | Regenerado desde PostgreSQL y revisado visualmente |
| Etiquetas | PDF A4; medidas de 95×68 mm comprobadas en operadores PDF; 1, 8 y 9 etiquetas verificadas |
| Revisión visual | Cliente, ficha, dashboard técnico, estados, paginación, PDF de dos páginas y nombre de cliente extenso |

La ejecución inicial encontró restricciones del entorno del agente al crear temporales o iniciar procesos auxiliares. La ejecución ampliada autorizada permitió completar las verificaciones; no queda un bloqueo de aprobación pendiente. Poppler emitió un aviso sobre su fuente Symbol de sustitución, pero produjo las imágenes de revisión y los textos utilizados en las etiquetas se renderizaron correctamente.

## Cobertura comprobada

- Borrador visible solo al autor; denegación para administrador, jefatura, técnico y otro cliente incluso dentro del mismo proyecto.
- Creación de solicitudes exclusiva de CLIENT; trabajador con CLIENT adicional puede redactar sin adquirir permisos operativos sobre ensayos ajenos.
- Dos técnicos en una misma solicitud: proyección de ensayos y muestras, recepción, historial, dashboard, filtros manipulados y PDF autorizados. Retirar la asignación revoca el acceso a informes de esa solicitud.
- Recepción parcial, correcciones con motivo, preservación de identidad e historial, códigos normalizados y rechazo de código de laboratorio duplicado.
- Filtro NOT_RECEIVED excluye solicitudes cuyo material pendiente de atender ya se recibió observado; dashboard y lista coinciden en su definición.
- Asignar mantiene PENDING. No se observa/completa antes del inicio. Retomar solo por jefatura y conservando la fecha inicial. Sin acciones posteriores a completar/cancelar.
- Una segunda solicitud incompatible revierte la asignación y versión de la primera dentro de un lote; rechazo de versiones obsoletas.
- Informe inmediato, versiones distintas, comprobaciones de PDF y descarga denegada fuera del proyecto o asignación.
- Métricas conciliadas contra SQL con más de 100 solicitudes, exclusión de cancelados, vencidos y ocho semanas de completados.
- Alta/restablecimiento de usuarios, Argon2id, revocación, caducidad, CSRF, origen y límite persistente de intentos.
- Navegación directa, recarga y regreso con filtros; acciones del técnico y contraste de botones del cliente superior al mínimo comprobado de 4,5:1.

Las capturas y PDF de revisión son ficticios y están en `.local/review`, fuera del código desplegable. Las pruebas E2E requieren credenciales privadas explícitas; sin ellas se omiten, nunca deben reportarse como ejecutadas.

## Estado local y pasos del usuario

Se preparó `lab_lc_v3` en la instancia PostgreSQL local indicada por la configuración existente y se actualizó únicamente la base de destino en `api/local.settings.json`. No se migraron registros ni se eliminaron las bases anteriores. La instancia separada del agente usó el puerto 55432 para pruebas; ese puerto no es un requisito de la aplicación.

La base nueva contiene datos ficticios y cuentas sin contraseña inicializada. Desde la ventana Anaconda del backend:

```bat
conda activate lab-lc
cd /d C:\Trabajo\Laboratorio\App\app-lab-lc\api
python manage.py password --email admin@example.com
func start
```

Usa el nombre real de tu entorno si difiere de `lab-lc`. Detén primero el servidor anterior con Ctrl+C. Reinicia el frontend con `npm run dev` en su ventana. Las cuentas y contraseñas de bases anteriores no se trasladan automáticamente. El administrador nuevo puede crear cuentas o inicializar las otras cuentas ficticias desde la plataforma.

## Límites de esta verificación

No se probó una impresora física: seleccionar A4, tamaño real/100 % y confirmar los márgenes de la impresora. No se aplicaron permisos de un rol runtime de producción ni se validaron Blob, certificados, red, respaldos/restauración o despliegue real en Azure. La guía de producción describe esos pasos. No se modificaron las dependencias Python; su auditoría de vulnerabilidades no se repitió en esta revisión.


## Revisión de administración y producción · 11/09/2026

Esta revisión complementa la evidencia anterior. No se desplegaron recursos Azure ni se modificaron bases de trabajo del usuario.

| Comprobación ejecutada | Resultado |
|---|---|
| Base nueva aislada | lab_lc_release_test, PostgreSQL 17 en 127.0.0.1:55432; 01/02/03 instalados desde cero, 13 tablas |
| Backend pytest | 29 pruebas aprobadas: sesiones, alcance de proyectos/técnicos, borradores, transiciones, recepción, PDF y administración |
| Frontend Vitest | 6 pruebas aprobadas; incluye payload de proyecto sin campos extra y selección inicial editable por empresa |
| Navegador Chrome, frontend construido + Functions | 2 pruebas aprobadas: crear/restablecer cuenta y login; crear proyecto con cuatro campos, comprobar preselección y desmarcar |
| Lint | ESLint y Ruff sin errores |
| Build | Vite completado; frontend servido con server.mjs, sin usar servidor de desarrollo |
| Auditorías | npm audit y pip-audit sin vulnerabilidades conocidas reportadas |
| Rol runtime en base aislada | SELECT catálogo e INSERT usuarios/informes permitidos; UPDATE actividad y CREATE en public denegados |
| Paquetes | Patrones de exclusión comprobados con casos de secretos/cachés; archivos requeridos y CA pública presentes |
| Servidor construido | /healthz y recarga de URL interna respondieron correctamente; proxy ejercitado en las pruebas de navegador |
| Certificados públicos | Dos CA descargadas de emisores oficiales por HTTPS; CA=true, firma propia y fechas comprobadas; huellas en api/certs/README.md |
| Revisión visual | Modal de alta revisado en captura: empresa, proyectos preseleccionados y exclusión manual legibles |

Se corrigió el campo project_ids inesperado del formulario de proyectos, se introdujo una lista explícita de campos para altas y mensajes seguros que identifican el campo inválido. La creación de proyectos inserta membresías de su empresa en la misma transacción y audita los usuarios asignados. No se modifica la estructura de las 13 tablas ni se requiere migración de datos local; Mermaid conserva su validez.

Durante la ejecución, el aislamiento de Windows bloqueó inicialmente esbuild, directorios temporales de pip-audit y procesos de revisión. Las comprobaciones se repitieron mediante ejecución autorizada y finalizaron. Una prueba de navegador falló por codificación de sus textos; se corrigió UTF-8 y ambas pruebas finalizaron correctamente.

Pendiente en Azure: comprobar compilación remota Linux/Oryx, PM2 provisto por App Service, indexación de Functions en Flex, VPN/DNS privado, rutas de certificados montados, RBAC/Blob, conexión PostgreSQL TLS, alertas y restauración real. Las pruebas locales no validan esos recursos. B1/Flex se documentan sin slots; conservar paquetes para reversión.

La inspección anterior de lab_lc_v3 mostró cero sesiones en ese momento e inicios de la cuenta manual en actividad. La prueba nueva confirma inserción durante login y eliminación al logout; no atribuye retrospectivamente la ausencia observada a una causa específica.
