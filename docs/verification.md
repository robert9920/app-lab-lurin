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
