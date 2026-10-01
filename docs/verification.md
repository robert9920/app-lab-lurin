# Verificación · esquema 4

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
