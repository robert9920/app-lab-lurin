"""Exporta contratos, diccionario y ERD desde el esquema 9 instalado (solo lectura)."""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
local = ROOT / "api/local.settings.json"
if local.exists():
    for key, value in json.loads(local.read_text(encoding="utf-8-sig"))["Values"].items():
        os.environ.setdefault(key, value)
# La configuración y la ruta de la API deben cargarse antes de sus módulos.
import validation as v  # noqa: E402
from database import engine, rows  # noqa: E402
from function_app import app  # noqa: E402
from schema_names import FIELD_NAMES, TABLE_NAMES  # noqa: E402

PURPOSE = {
    "organizations": "Empresas propietarias de los proyectos.",
    "users": "Identidad y acceso. Los roles se acumulan; la empresa no sustituye la asignación a proyectos.",
    "projects": "Proyectos de ingeniería que agrupan las solicitudes.",
    "project_members": "Acceso explícito de cada cliente a proyectos de su empresa.",
    "assay_catalog": "Tipos de ensayo y referencias de método editables.",
    "requests": "Solicitud y estado general; unidad de bloqueo y control de concurrencia.",
    "samples": "Una identidad de muestra desde la declaración hasta la recepción. Conserva la última recepción; activity conserva las correcciones.",
    "sample_assays": "Una fila por pareja muestra–tipo de ensayo. Es la unidad contada en el dashboard.",
    "reports": "Versiones inmutables de los PDF. Cada fila conserva un archivo distinto, visible inmediatamente.",
    "activity": "Historial inmutable y comentarios. Los eventos de cuenta pueden no pertenecer a una solicitud.",
    "sessions": "Sesiones opacas revocables. El token original solo vive en la cookie del navegador.",
    "rate_limits": "Contador compartido entre instancias para los intentos de acceso.",
    "schema_migrations": "Versiones del esquema instaladas. Esta base nueva comienza en la versión 2.",
}
MEANINGS = {
    "id": "Identificador interno del registro; no acredita acceso.",
    "name": "Nombre visible.",
    "tax_id": "Identificación tributaria; única si se informa.",
    "active": "Registro habilitado. En usuarios, false impide el acceso.",
    "organization_id": "Empresa a la que pertenece el registro.",
    "email": "Correo de acceso, único y guardado en minúsculas; no se utiliza para enviar mensajes.",
    "password_hash": "Hash Argon2id con salt y parámetros incluidos. No contiene contraseña recuperable y nunca se devuelve al navegador.",
    "roles": "Roles acumulables ADMIN, MANAGER, TECH y CLIENT. Debe existir al menos uno.",
    "created_at": "Instante de creación, almacenado con zona horaria.",
    "code": "Código visible único.",
    "location": "Ubicación del proyecto.",
    "user_id": "Usuario al que pertenece el acceso o la sesión.",
    "project_id": "Proyecto propietario o asignado.",
    "method": "Referencia del método, pendiente de validación por el laboratorio antes de usarla.",
    "category": "Grupo del ensayo para organizar el catálogo.",
    "created_by": "Usuario que creó la solicitud.",
    "title": "Nombre o propósito del servicio solicitado.",
    "status": "Estado general: DRAFT, SUBMITTED, OBSERVED, APPROVED, REJECTED o CLOSED.",
    "notes": "Observaciones del registro.",
    "target_date": "Fecha objetivo solicitada; no sustituye el fin previsto de cada ensayo.",
    "version": "Número de versión.",
    "updated_at": "Instante del último cambio de la solicitud o cualquiera de sus elementos.",
    "request_id": "Solicitud propietaria; determina el proyecto autorizado.",
    "client_code": "Código de muestra declarado por el cliente, único dentro de la solicitud.",
    "borehole": "Calicata, sondaje o punto de extracción.",
    "material": "Descripción del material, por ejemplo suelo, relave o mezcla.",
    "depth_from": "Profundidad inicial en metros; puede desconocerse.",
    "depth_to": "Profundidad final en metros; no menor que la inicial.",
    "quantity": "Cantidad declarada, positiva; NULL significa desconocida.",
    "unit": "Unidad común para cantidad declarada y cantidad recibida.",
    "received_at": "Fecha y hora efectivas de la última recepción; NULL si no llegó.",
    "received_by": "Persona del laboratorio que registró la recepción actual.",
    "transport": "Transporte, vehículo o persona que entregó la muestra.",
    "received_quantity": "Cantidad recibida en la unidad de la muestra. Es un valor actual, no se suma automáticamente al corregir.",
    "condition": "NOT_RECEIVED, OK, OBSERVED, DAMAGED o INSUFFICIENT. Solo OK permite iniciar, retomar y completar ensayos.",
    "reception_notes": "Observación visible de recepción; obligatoria si la condición recibida no es OK.",
    "sample_id": "Muestra sobre la que se solicita y ejecuta el ensayo.",
    "review_status": "PENDING, APPROVED o REJECTED. Decisión de revisión separada de la ejecución; nuevos ensayos comienzan PENDING. Motivo, fecha y responsable se conservan en actividad.",
    "assay_id": "Tipo de ensayo del catálogo; no se repite para la misma muestra.",
    "technician_id": "Responsable asignado; usuario activo TECH o MANAGER al asignar.",
    "state": "PENDING, RUNNING, OBSERVED, COMPLETED o CANCELLED.",
    "planned_start": "Fecha prevista de inicio, opcional.",
    "planned_end": "Fecha prevista final, opcional; determina si el ensayo abierto está vencido.",
    "started_at": "Primer inicio real; se conserva al retomar un ensayo observado.",
    "completed_at": "Instante de finalización real.",
    "storage_key": "Clave privada del archivo en Blob o en UPLOAD_DIR; nunca es una URL pública.",
    "sha256": "Resumen SHA-256 del contenido para comprobación de integridad.",
    "bytes": "Tamaño del PDF en bytes, entre 1 y 20 MiB.",
    "uploaded_by": "Usuario del laboratorio que subió el informe.",
    "actor_id": "Usuario responsable del evento; puede ser NULL en un evento del sistema.",
    "kind": "EVENT para cambios y COMMENT para comentarios.",
    "message": "Descripción del cambio, motivo o texto del comentario.",
    "detail": "Datos estructurados del cambio, por ejemplo valores anteriores y posteriores; solo se muestran al personal interno.",
    "internal": "true restringe el evento al personal interno. false permite verlo a los clientes del proyecto.",
    "token_hash": "SHA-256 del token opaco de sesión; clave primaria, no utilizable como cookie.",
    "last_seen": "Último acceso autenticado; determina la caducidad por inactividad.",
    "expires_at": "Caducidad absoluta de la sesión.",
    "key": "SHA-256 de la clave del límite (actualmente correo normalizado para login); no guarda la contraseña.",
    "count": "Intentos consumidos en la ventana vigente.",
    "window_start": "Inicio de la ventana del límite; se renueva al vencer.",
    "applied_at": "Instante de instalación de la versión del esquema.",
}
OVERRIDES = {
    (
        "requests",
        "version",
    ): "Contador de concurrencia del agregado: aumenta con cambios de muestras, ensayos, comentarios, informes o estado.",
    (
        "reports",
        "version",
    ): "Correlativo de carga dentro de la solicitud; se obtiene con la solicitud bloqueada y no sobrescribe versiones anteriores.",
    (
        "schema_migrations",
        "version",
    ): "Versión instalada del esquema; clave primaria. La instalación actual inserta 2.",
    (
        "activity",
        "id",
    ): "Identidad bigint generada por PostgreSQL; orden estable del historial.",
    (
        "sample_assays",
        "notes",
    ): "Último motivo o nota técnica interna. El historial conserva los cambios anteriores.",
    (
        "samples",
        "notes",
    ): "Observaciones declaradas por el cliente; describe aquí los componentes de una mezcla.",
    (
        "requests",
        "code",
    ): "Correlativo visible SOL-00000001 generado por request_number. Los saltos de secuencia son normales.",
    ("reports", "name"): "Nombre seguro generado por el servidor, Informe-N.pdf.",
}


PURPOSE = {
    TABLE_NAMES.get(k, k): value.replace("activity", "actividad").replace("versión 2", "versión 3")
    for k, value in PURPOSE.items()
}
MEANINGS = {FIELD_NAMES.get(k, k): value for k, value in MEANINGS.items()}
MEANINGS.update(
    {
        "codigo_recepcion": "Código manual normalizado en mayúsculas, compartido por muestras recibidas juntas; obligatorio al recibir.",
        "codigo_laboratorio": "Código manual normalizado en mayúsculas y único en el laboratorio; obligatorio al recibir.",
        "detalle": "Auditoría estructurada inmutable. No se devuelve el JSON al navegador; se proyectan descripciones legibles y autorizadas.",
    }
)
OVERRIDES = {
    (TABLE_NAMES.get(t, t), FIELD_NAMES.get(c, c)): value.replace("inserta 2", "inserta 3").replace(
        "request_number", "numero_solicitud"
    )
    for (t, c), value in OVERRIDES.items()
}


# Esquema 6; diccionario físico en español, sin asignaciones a proyectos.
for obsolete in ("projects", "project_members", "proyectos", "miembros_proyecto"):
    PURPOSE.pop(obsolete, None)
PURPOSE.update(
    {
        "empresas": "Empresas de los solicitantes; como máximo una es interna.",
        "usuarios": "Identidad, contacto, empresa y roles de acceso; no existen asignaciones a proyectos.",
        "solicitudes": "Solicitud del autor; empresa conservada y código externo de proyecto sin FK entre bases.",
        "migraciones_esquema": "Versiones instaladas, independientes del nombre de la base. El esquema actual es 9.",
        "catalogo_ensayos": "Catálogo editable; precio vigente en USD para estimaciones económicas, sin registrar pagos.",
    }
)
MEANINGS.update(
    {
        "es_interna": "Designa la única empresa interna; sus clientes seleccionan proyectos de AppControlHH.",
        "num_telefono": "Teléfono opcional como texto, permite prefijo internacional.",
        "proyecto_id": "Código de AppControlHH para solicitudes internas; EXTERNO para nuevas solicitudes externas. No es UUID ni FK.",
        "distrito": "Distrito de procedencia. Obligatorio en API al crear/editar; NULL permitido en registros históricos migrados.",
        "provincia": "Provincia de procedencia. Obligatoria en API al crear/editar; NULL permitido en históricos.",
        "departamento": "Departamento de procedencia. Obligatorio en API al crear/editar; NULL permitido en históricos.",
        "coordenada_este": "Coordenada este opcional. NULL si se desconoce; no se convierte ni se presume sistema de referencia.",
        "coordenada_norte": "Coordenada norte opcional. NULL si se desconoce; no se convierte ni se presume sistema de referencia.",
        "codigo_ot": "OT manual normalizada en mayúsculas. Jefatura requiere al menos una muestra recibida para registrarla; correcciones con motivo.",
        "cantidad": "Cantidad declarada de recipientes enteros positivos; NULL significa desconocida.",
        "cantidad_recibida": "Cantidad actual de recipientes recibidos, enteros positivos y opcionales; no se acumula al corregir.",
        "peso": "Peso declarado en kg, positivo, finito, opcional y con máximo un decimal; se rechaza precisión incompatible sin redondear.",
        "peso_recibido": "Peso real recibido en kg, positivo, finito, opcional y con máximo un decimal; separado del declarado.",
        "precio": "Precio vigente del ensayo en USD, obligatorio, finito, positivo y con máximo dos decimales; no es un precio histórico ni un pago.",
        "fecha_estimada_arribo": "Fecha estimada de llegada de las muestras; opcional e independiente de la fecha objetivo de resultados.",
        "fecha_objetivo": "Fecha objetivo de entrega de resultados, opcional; no sustituye el fin previsto de cada ensayo.",
        "profundidad_inicial": "Profundidad inicial en metros, opcional, no negativa; precisión almacenada conservada, visualización con dos decimales.",
        "profundidad_final": "Profundidad final en metros, opcional y no menor que la inicial; precisión almacenada conservada, visualización con dos decimales.",
        "estado_solicitud": "DRAFT, WAITING_ASSAYS, SUBMITTED, OBSERVED, APPROVED, REJECTED o CLOSED.",
        "interno": "true restringe el evento al personal autorizado; false permite verlo al autor de la solicitud.",
    }
)
OVERRIDES[("solicitudes", "empresa_id")] = (
    "Empresa conservada al crear la solicitud, independiente de cambios posteriores en el usuario. FK empresas.id."
)
OVERRIDES[("migraciones_esquema", "version")] = (
    "Versión instalada, PK. Instalación limpia: 9; las migraciones conservan también las versiones previas."
)


MEANINGS["estado_general"] = (
    "Estado general físico CREATED/CANCELLED/CLOSED. Si estado_solicitud=DRAFT, la interfaz y el filtro muestran Borrador; no se almacena un estado duplicado."
)
OVERRIDES[("solicitudes", "estado_solicitud")] = (
    "Etapa interna de envío/revisión que conserva privacidad de borradores y permisos. No es el filtro visible Estado Solicitud."
)
OVERRIDES[("solicitudes", "proyecto_id")] = (
    "Código AppControlHH o EXTERNO; NULL solo para borrador interno aún sin proyecto. Obligatorio al enviar una solicitud interna. Sin FK."
)
OVERRIDES[("muestras", "codigo_cliente")] = (
    "Código declarado por el cliente, único por solicitud cuando está informado. NULL admite filas parciales de borrador; obligatorio antes del envío."
)
OVERRIDES[("muestras", "material")] = (
    "Tipo de muestra declarado. NULL solo en borradores incompletos; obligatorio antes del envío. El formulario no inventa un tipo."
)
OVERRIDES[("ensayos_muestra", "observaciones")] = (
    "Último motivo o nota operativa. La API proyecta solo motivos de observar/cancelar al cliente desde actividad; otras notas internas siguen restringidas."
)


def inspect_schema():
    with engine().connect() as db:
        if rows(db, "SELECT max(version) version FROM migraciones_esquema")[0]["version"] != 9:
            raise RuntimeError(
                "El exportador requiere esquema 9 instalado; usa una base ficticia o aplica SQL07 antes de exportar."
            )
        columns = rows(
            db,
            """SELECT table_name,column_name,data_type,is_nullable,column_default,is_identity
            FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position""",
        )
        foreign = rows(
            db,
            """SELECT tc.table_name,ccu.table_name parent,kcu.column_name,ccu.column_name parent_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON kcu.constraint_name=tc.constraint_name AND kcu.constraint_schema=tc.constraint_schema
            JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name AND ccu.constraint_schema=tc.constraint_schema
            WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema='public' ORDER BY tc.table_name,kcu.column_name""",
        )
        primary = rows(
            db,
            """SELECT k.table_name,k.column_name FROM information_schema.table_constraints c
            JOIN information_schema.key_column_usage k USING(constraint_catalog,constraint_schema,constraint_name)
            WHERE c.table_schema='public' AND c.constraint_type='PRIMARY KEY'""",
        )
    if {c["table_name"] for c in columns} != set(PURPOSE):
        raise RuntimeError("El exportador requiere exclusivamente las 11 tablas del esquema v9")
    return columns, foreign, primary


def export_erd(columns, foreign, primary):
    lines = [
        "---",
        "title: Laboratorio Lara Consulting · PostgreSQL v9",
        "config:",
        "  theme: neutral",
        "---",
        "erDiagram",
    ]
    pk = {(p["table_name"], p["column_name"]) for p in primary}
    fk = {(f["table_name"], f["column_name"]): f for f in foreign}
    dictionary = [
        "<!-- BEGIN FIELD DICTIONARY -->",
        "## Diccionario completo de la base de datos",
        "",
        "Generado desde PostgreSQL con `python scripts/export_contracts.py`. NULL representa un dato desconocido; no es cero. Fechas y horas se presentan en Lima. `text` se limita en la API mediante Pydantic. FK indica relación; PK identifica la fila.",
        "",
    ]
    for table in PURPOSE:
        lines.append(f"    {table} {{")
        dictionary += [
            f"### {table}",
            "",
            PURPOSE[table],
            "",
            "| Campo | Tipo | Obligatorio (NOT NULL) | Valor predeterminado SQL | Relación / clave | Función |",
            "|---|---|---|---|---|---|",
        ]
        for col in (c for c in columns if c["table_name"] == table):
            name = col["column_name"]
            key = (table, name)
            dtype = {
                "timestamp with time zone": "timestamptz",
                "ARRAY": "text_array",
            }.get(col["data_type"], col["data_type"].replace(" ", "_"))
            relation = fk.get(key)
            tags = (["PK"] if key in pk else []) + (["FK"] if relation else [])
            lines.append(f"        {dtype} {name}" + (" " + ",".join(tags) if tags else ""))
            default = col["column_default"] or (
                "IDENTITY"
                if col["is_identity"] == "YES"
                else ("NULL" if col["is_nullable"] == "YES" else "Sin valor; debe suministrarse")
            )
            description = OVERRIDES.get(key, MEANINGS.get(name))
            if not description:
                raise RuntimeError(f"Falta descripción de {key}")
            link = (relation["parent"] + "." + relation["parent_column"]) if relation else "—"
            if key in pk:
                link = "PK; " + link if relation else "PK"
            dictionary.append(
                f"| `{name}` | `{dtype}` | {'Sí' if col['is_nullable'] == 'NO' else 'No'} | `{default}` | {link} | {description} |"
            )
        lines.append("    }")
        dictionary.append("")
    for f in foreign:
        nullable = (
            next(
                c
                for c in columns
                if c["table_name"] == f["table_name"] and c["column_name"] == f["column_name"]
            )["is_nullable"]
            == "YES"
        )
        lines.append(
            f'    {f["parent"]} {"|o" if nullable else "||"}--o{{ {f["table_name"]} : "{f["column_name"]}"'
        )
    (ROOT / "docs/database.mmd").write_text("\n".join(lines) + "\n", encoding="utf-8")
    dictionary.append("<!-- END FIELD DICTIONARY -->")
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = re.sub(
        r"\n?<!-- BEGIN FIELD DICTIONARY -->[\s\S]*?<!-- END FIELD DICTIONARY -->\n?",
        "",
        text,
    )
    readme.write_text(text.rstrip() + "\n\n" + "\n".join(dictionary) + "\n", encoding="utf-8")
    (ROOT / "docs/schema-columns.json").write_text(
        json.dumps(columns, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def export_openapi():
    from services.statuses import ASSAY_STATUSES

    models = {
        "auth/login": v.Login,
        "requests": v.DraftCreate,
        "requests/{rid}": v.DraftEdit,
        "requests/{rid}/actions": v.Action,
        "requests/{rid}/assays": v.AssaysEdit,
        "requests/{rid}/assays/review": v.AssaysReview,
        "requests/{rid}/assays/resubmit": v.AssaysResubmit,
        "requests/{rid}/receptions": v.Reception,
        "requests/{rid}/tasks": v.TaskUpdate,
        "requests/{rid}/comments": v.Comment,
        "work": v.WorkUpdate,
        "management/organizations": v.Organization,
        "management/organizations/{id}": v.OrganizationEdit,
        "requests/{rid}/work-order": v.WorkOrder,
        "management/users": v.UserCreate,
        "management/users/{id}": v.UserEdit,
        "management/users/{id}/password": v.Password,
        "management/catalog": v.Catalog,
        "management/catalog/{id}": v.Catalog,
    }
    strict_edit = v.RequestEdit.model_json_schema(ref_template="#/components/schemas/{model}")
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Laboratorio Lara Consulting",
            "version": "9.0.0",
            "description": "Sesión opaca en cookie lab_session. Escrituras requieren Origin exacto y X-CSRF-Token de GET /session. "
            "ADMIN administra; MANAGER dirige; TECH solo consulta sus solicitudes, muestras y ensayos asignados; CLIENT accede solo a sus propias solicitudes. Borradores exclusivos de su autor. "
            "En Azure, la clave de Functions se agrega exclusivamente en el proxy. version identifica la revisión de la solicitud. "
            "Los lotes de /work son transaccionales. Cada informe se hace visible al confirmar la carga.",
        },
        "servers": [{"url": "/api"}],
        "paths": {},
        "components": {
            "securitySchemes": {"session": {"type": "apiKey", "in": "cookie", "name": "lab_session"}},
            "schemas": {},
        },
        "security": [{"session": []}],
    }
    queries = {
        "projects": ["scope", "q", "page", "limit"],
        "requests": [
            "q",
            "status",
            "request_status",
            "assay_status",
            "project",
            "view",
            "condition",
            "requester",
            "organization",
            "created_from",
            "created_to",
            "pending_assays",
            "page",
            "limit",
        ],
        "filter-options": ["kind", "view", "q", "selected", "page", "limit"],
        "work": [
            "project",
            "request_q",
            "requester",
            "organization",
            "request",
            "technician",
            "assay",
            "state",
            "request_status",
            "assay_status",
            "metric",
            "page",
            "limit",
        ],
        "reports": [
            "q",
            "project",
            "request",
            "requester",
            "organization",
            "page",
            "limit",
        ],
        "requests/{rid}/print/{kind}": ["sample_ids"],
    }
    spec["components"]["schemas"]["SessionView"] = {
        "type": "object",
        "properties": {
            "csrf": {"type": "string"},
            "user": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "name": {"type": "string"},
                    "organization_name": {"type": ["string", "null"]},
                    "organization_id": {"type": ["string", "null"]},
                    "roles": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    }
    spec["components"]["schemas"].update(
        {
            "WorkTask": {
                "type": "object",
                "properties": {
                    "id": {"type": ["string", "null"], "format": "uuid"},
                    "row_kind": {"enum": ["assay", "sample_without_assays"]},
                    "sample_id": {"type": "string", "format": "uuid"},
                    "assay_status": {"enum": list(ASSAY_STATUSES)},
                    "request_status": {"enum": ["CREATED", "CANCELLED", "CLOSED"]},
                    "workflow_status": {
                        "type": "string",
                        "description": "Etapa interna de envío/revisión.",
                    },
                    "state": {
                        "enum": [
                            "PENDING",
                            "RUNNING",
                            "OBSERVED",
                            "COMPLETED",
                            "CANCELLED",
                            None,
                        ]
                    },
                    "technician_id": {"type": ["string", "null"]},
                    "codigo_ot": {
                        "type": ["string", "null"],
                        "description": "OT manual por solicitud; requisito de assign/start/resume, junto con aprobación y material cuando corresponda.",
                    },
                    "approved": {
                        "type": ["boolean", "null"],
                        "description": "Calculado desde review_status=APPROVED; no es una columna física.",
                    },
                    "review_status": {
                        "type": ["string", "null"],
                        "enum": ["PENDING", "APPROVED", "REJECTED", None],
                    },
                    "review_reason": {
                        "type": "string",
                        "description": "Motivo público de la última decisión; historial de revisiones preservado.",
                    },
                    "state_reason": {
                        "type": "string",
                        "description": "Motivo público de observación/cancelación actual; proyectado de actividad, incluidos eventos anteriores internos.",
                    },
                    "state_reason_author": {"type": ["string", "null"]},
                    "state_reason_at": {
                        "type": ["string", "null"],
                        "format": "date-time",
                    },
                    "can_review": {"type": "boolean"},
                    "can_resubmit": {"type": "boolean"},
                    "requester_name": {"type": "string"},
                    "organization_name": {"type": "string"},
                    "assigned": {
                        "type": "boolean",
                        "description": "Derivado de tecnico_id; no es un estado ni columna duplicada.",
                    },
                    "allowed_actions": {
                        "type": "array",
                        "items": {
                            "enum": [
                                "assign",
                                "start",
                                "observe",
                                "complete",
                                "resume",
                                "cancel",
                            ]
                        },
                        "description": "Acciones autorizadas por rol, asignación, OT, material y estado. assign/start/resume necesitan APPROVED y OT; RUNNING histórico admite observe/complete sin OT. La API valida de nuevo al ejecutar.",
                    },
                },
            },
            "HistoryEntry": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "actor_name": {"type": ["string", "null"]},
                    "created_at": {"type": "string", "format": "date-time"},
                    "internal": {"type": "boolean"},
                    "description_lines": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Descripción legible; nunca JSON de auditoría crudo.",
                    },
                },
            },
            "ReceivedSampleView": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "codigo_recepcion": {"type": ["string", "null"], "maxLength": 60},
                    "codigo_laboratorio": {"type": ["string", "null"], "maxLength": 60},
                    "quantity": {
                        "type": ["string", "number", "null"],
                        "description": "Recipientes declarados, entero positivo o desconocido.",
                    },
                    "weight": {
                        "type": ["string", "number", "null"],
                        "description": "Peso declarado en kg, positivo, máximo un decimal, o desconocido; independiente de recipientes.",
                    },
                    "received_quantity": {"type": ["string", "number", "null"]},
                    "received_weight": {
                        "type": ["string", "number", "null"],
                        "description": "Peso recibido en kg, positivo y máximo un decimal, o desconocido.",
                    },
                    "can_receive": {
                        "type": "boolean",
                        "description": "Permiso operativo sobre la muestra; recibir requiere además solicitud enviada; TECH requiere aprobación y asignación.",
                    },
                    "can_print": {
                        "type": "boolean",
                        "description": "Permiso para imprimir muestras autorizadas, también en solicitudes canceladas o cerradas. No habilita escrituras.",
                    },
                },
            },
        }
    )
    spec["components"]["schemas"].update(strict_edit.pop("$defs", {}))
    spec["components"]["schemas"]["RequestEdit"] = strict_edit
    for fn in app.get_functions():
        trigger = next(
            b for b in json.loads(fn.get_function_json())["bindings"] if b["type"] == "httpTrigger"
        )
        route = trigger["route"]
        for method in trigger["methods"]:
            method = method.lower()
            op = {
                "operationId": fn.get_function_name() + "_" + method,
                "summary": fn.get_function_name().replace("_", " "),
                "responses": {
                    str(code): {"description": desc}
                    for code, desc in [
                        (200, "Operación completada"),
                        (400, "Validación"),
                        (401, "Sesión inválida"),
                        (403, "Permiso insuficiente, origen o CSRF"),
                        (404, "Recurso fuera del ámbito autorizado o inexistente"),
                        (409, "Conflicto de versión, duplicado o estado"),
                        (413, "Tamaño máximo excedido"),
                        (415, "Tipo de contenido incorrecto"),
                        (429, "Demasiados intentos"),
                        (500, "Error interno sin detalles sensibles"),
                        (503, "Catálogo de proyectos no disponible"),
                    ]
                },
                "parameters": [],
            }
            for name in re.findall(r"\{(\w+)\}", route):
                op["parameters"].append(
                    {
                        "name": name,
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string",
                            **({"enum": ["receipt", "labels"]} if name == "kind" else {"format": "uuid"}),
                        },
                    }
                )
            if method not in ("get", "head"):
                for name in ["Origin"] if route == "auth/login" else ["Origin", "X-CSRF-Token"]:
                    op["parameters"].append(
                        {
                            "name": name,
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    )
                model = models.get(route)
                if model:
                    schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
                    spec["components"]["schemas"].update(schema.pop("$defs", {}))
                    for key, minimum, maximum in (
                        ("easting", 100000, 1000000),
                        ("northing", 1000000, 10000000),
                    ):
                        if key in schema.get("properties", {}):
                            schema["properties"][key]["description"] = (
                                f"Opcional. Valor finito entre {minimum} inclusive y {maximum} exclusivo; decimales admitidos. En edición, históricos sin cambios se conservan."
                            )
                    spec["components"]["schemas"][model.__name__] = schema
                    op["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/" + model.__name__}}
                        },
                    }
                if route.endswith("/reports"):
                    op["parameters"].append(
                        {
                            "name": "X-Request-Version",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "integer", "minimum": 1},
                        }
                    )
                    op["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/pdf": {
                                "schema": {
                                    "type": "string",
                                    "format": "binary",
                                    "description": "PDF estructuralmente válido, sin cifrado ni contenido activo; máximo 20 MiB y 500 páginas.",
                                }
                            }
                        },
                    }
            if route == "requests/{rid}/assays/review":
                op["description"] = (
                    "MANAGER: decisiones individuales, motivo obligatorio al rechazar; versión y transacción atómica. Primera aprobación habilita solicitud; todos rechazados sin aprobaciones previas produce OBSERVED."
                )
            if route == "requests/{rid}/assays/resubmit":
                op["description"] = (
                    "Autor CLIENT: vuelve a solicitar ensayos rechazados conservando ID e historial. Revisión PENDING; requiere otra aprobación."
                )
            if route == "requests/{rid}/actions":
                op["description"] = (
                    "Las acciones legacy approve y reject devuelven 409. Usar /assays/review o cancel con motivo. submit exige declaración completa (incluidas muestras), admitiendo muestras sin ensayos. Un DRAFT no puede cancelarse. Cancelación por autor CLIENT o MANAGER: versión, transacción, conserva completados/rechazados e informes. close exige MANAGER, al menos un completado, muestras definidas, trabajo resuelto e informe. Canceladas/cerradas sin escrituras."
                )
            if route == "requests" and method == "post":
                op["description"] = (
                    "CLIENT crea un borrador privado parcial. Solo se omiten filas totalmente vacías; se validan valores informados y códigos repetidos. Para enviar usar actions submit con declaración completa."
                )
            if route == "requests/{rid}" and method == "put":
                op["description"] = (
                    "DRAFT usa DraftEdit parcial; las solicitudes enviadas exigen RequestEdit completo. La API decide desde el estado almacenado y comprueba versión/autor; no hay bandera de relajación elegible por cliente."
                )
                op["requestBody"]["content"]["application/json"]["schema"] = {
                    "anyOf": [
                        {"$ref": "#/components/schemas/DraftEdit"},
                        {"$ref": "#/components/schemas/RequestEdit"},
                    ]
                }
            if route == "auth/login":
                op["security"] = []
            if route in ("auth/login", "session"):
                op["responses"]["200"]["content"] = {
                    "application/json": {"schema": {"$ref": "#/components/schemas/SessionView"}}
                }
            if method == "get":
                for name in queries.get(route, []):
                    schema = (
                        {
                            "type": "integer",
                            "minimum": 1,
                            **({"maximum": 100, "default": 30} if name == "limit" else {"default": 1}),
                        }
                        if name in ("page", "limit")
                        else {"type": "string"}
                    )
                    op["parameters"].append({"name": name, "in": "query", "schema": schema})
                    if name in ("status", "state"):
                        op["parameters"][-1]["description"] = (
                            "Uno o varios códigos separados por comas; OR. En requests, SUBMITTED busca revisión pendiente en solicitudes enviadas/abiertas, incluidas APPROVED. WAITING_ASSAYS busca muestras sin ensayos en solicitudes enviadas/abiertas, incluidas APPROVED/OBSERVED. Otros códigos filtran el estado principal. En work, state filtra la ejecución."
                        )
                    if name == "assay_status":
                        op["parameters"][-1]["description"] = (
                            "CSV OR: "
                            + ", ".join(ASSAY_STATUSES)
                            + ". Clasificación exclusiva: CANCELLED > revisión REJECTED > revisión PENDING > ejecución aprobada. WAITING_ASSAYS cuenta muestras sin ensayos de solicitudes CREATED; work devuelve filas informativas sin id ni acciones. Otros filtros AND."
                        )
                    if name == "request_status":
                        op["parameters"][-1]["description"] = (
                            "CSV OR: DRAFT, CREATED, CANCELLED, CLOSED. DRAFT deriva de estado_solicitud y solo es accesible por su autor; CREATED excluye borradores. El JSON request_status conserva el valor físico CREATED/CANCELLED/CLOSED. Otros filtros AND."
                        )
                    if name in ("requester", "organization", "selected"):
                        op["parameters"][-1]["description"] = (
                            "UUID; filtra únicamente dentro del alcance autorizado. selected obtiene la etiqueta de una opción al recargar."
                        )
                    if name in ("created_from", "created_to"):
                        schema["format"] = "date"
                        op["parameters"][-1]["description"] = (
                            "Fecha de creación de solicitud; ambos extremos inclusivos en America/Lima."
                        )
                    if name == "pending_assays":
                        schema["enum"] = ["true", "false"]
                        op["parameters"][-1]["description"] = (
                            "Compatibilidad con enlaces anteriores: existencia de muestras autorizadas sin ningún ensayo. Independiente del estado; AND. La interfaz utiliza status=WAITING_ASSAYS."
                        )
                    if name == "scope":
                        schema["enum"] = ["requests", "catalog"]
                        op["parameters"][-1]["description"] = (
                            "requests: códigos de solicitudes autorizadas; catalog: AppControlHH, solo CLIENT de empresa interna, respuesta paginada."
                        )
                    if name == "condition":
                        schema["enum"] = ["", "NOT_RECEIVED", "issues", "NO_OT"]
                        op["parameters"][-1]["description"] = (
                            "En view=reception, NOT_RECEIVED exige al menos una muestra sin recibir; issues material observado/dañado/insuficiente; NO_OT carece de OT. Incluye solicitudes enviadas sin ensayos; TECH solo aprobadas asignadas."
                        )
                    if route == "reports" and name == "q":
                        op["parameters"][-1]["description"] = (
                            "Coincidencia parcial sin distinguir mayúsculas únicamente en código de solicitud. "
                            "No busca proyecto ni nombre de archivo; project es un filtro independiente combinado con AND."
                        )
                    if name == "sample_ids":
                        op["parameters"][-1]["description"] = (
                            "Obligatorio para labels: 1 a 200 UUID separados por comas, sin duplicados, recibidos y autorizados. PDF A4 2x4, etiquetas 95x68 mm."
                        )
                if route in ("requests", "work", "reports", "filter-options"):
                    properties = {
                        "id": {"type": "string", "format": "uuid"},
                        "requester_name": {
                            "type": "string",
                            "description": "Nombre del autor de la solicitud.",
                        },
                        "organization_name": {
                            "type": "string",
                            "description": "Empresa guardada en la solicitud; no depende de cambios posteriores del usuario.",
                        },
                    }
                    if route == "requests":
                        properties.update(
                            {
                                "request_status": {"enum": ["CREATED", "CANCELLED", "CLOSED"]},
                                "reception_counts": {
                                    "type": "object",
                                    "properties": {
                                        k: {"type": "integer", "minimum": 0}
                                        for k in (
                                            "NOT_RECEIVED",
                                            "OBSERVED",
                                            "DAMAGED",
                                            "INSUFFICIENT",
                                        )
                                    },
                                    "description": "Solo con view=reception: muestras por condición, calculadas en PostgreSQL sobre el alcance autorizado; cada muestra cuenta una vez. TECH solo asignadas. Sin OT se deriva de codigo_ot=null, independientemente de estos conteos.",
                                },
                                "codigo_ot": {"type": ["string", "null"]},
                                "assay_counts": {
                                    "type": "object",
                                    "properties": {
                                        k: {"type": "integer", "minimum": 0} for k in ASSAY_STATUSES
                                    },
                                    "description": "Una categoría por ensayo. WAITING_ASSAYS cuenta muestras, solo en CREATED. Alcance autorizado, cálculo SQL completo.",
                                },
                                "pending_assays": {
                                    "type": "boolean",
                                    "description": "Al menos una muestra accesible sin ensayos definidos.",
                                },
                                "unapproved_count": {
                                    "type": "integer",
                                    "description": "Ensayos accesibles que necesitan aprobación de jefatura.",
                                },
                            }
                        )
                    if route == "filter-options":
                        properties = {
                            "id": {"type": "string", "format": "uuid"},
                            "name": {"type": "string"},
                        }
                    op["responses"]["200"]["content"] = {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "items": (
                                            {"$ref": "#/components/schemas/WorkTask"}
                                            if route == "work"
                                            else {
                                                "type": "object",
                                                "properties": properties,
                                            }
                                        ),
                                    },
                                    "total": {"type": "integer"},
                                    "page": {"type": "integer"},
                                    "limit": {"type": "integer"},
                                },
                            }
                        }
                    }
                if route == "work":
                    op["responses"]["200"]["content"] = {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/WorkTask"},
                                    },
                                    "total": {"type": "integer"},
                                    "page": {"type": "integer"},
                                    "limit": {"type": "integer"},
                                },
                            }
                        }
                    }
                if route == "requests/{rid}":
                    op["responses"]["200"]["content"] = {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "project_id": {
                                        "type": ["string", "null"],
                                        "description": "Código de catálogo o EXTERNO; no UUID/FK. NULL solo en borrador interno incompleto.",
                                    },
                                    "status": {
                                        "enum": [
                                            "DRAFT",
                                            "WAITING_ASSAYS",
                                            "SUBMITTED",
                                            "OBSERVED",
                                            "APPROVED",
                                            "REJECTED",
                                            "CLOSED",
                                        ]
                                    },
                                    "can_edit_assays": {
                                        "type": "boolean",
                                        "description": "Autor CLIENT de solicitud aprobada abierta; PUT /requests/{rid}/assays solo modifica selecciones no aprobadas.",
                                    },
                                    "undefined_samples": {"type": "integer"},
                                    "unapproved_count": {"type": "integer"},
                                    "can_edit": {
                                        "type": "boolean",
                                        "description": "Autor CLIENT antes de aprobación; declaración recibida protegida.",
                                    },
                                    "is_internal": {"type": "boolean"},
                                    "district": {"type": ["string", "null"]},
                                    "province": {"type": ["string", "null"]},
                                    "department": {"type": ["string", "null"]},
                                    "target_date": {
                                        "type": ["string", "null"],
                                        "format": "date",
                                        "description": "Fecha objetivo entrega resultados.",
                                    },
                                    "estimated_arrival_date": {
                                        "type": ["string", "null"],
                                        "format": "date",
                                        "description": "Fecha estimada arribo muestra.",
                                    },
                                    "codigo_ot": {"type": ["string", "null"]},
                                    "request_status": {"enum": ["CREATED", "CANCELLED", "CLOSED"]},
                                    "can_cancel": {"type": "boolean"},
                                    "assay_counts": {
                                        "type": "object",
                                        "properties": {
                                            k: {"type": "integer", "minimum": 0} for k in ASSAY_STATUSES
                                        },
                                    },
                                    "tasks": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/WorkTask"},
                                    },
                                    "samples": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/ReceivedSampleView"},
                                    },
                                    "activity": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/HistoryEntry"},
                                    },
                                },
                            }
                        }
                    }
                if "/download" in route or "/print/" in route:
                    op["responses"]["200"]["content"] = {
                        "application/pdf": {"schema": {"type": "string", "format": "binary"}}
                    }
            spec["paths"].setdefault("/" + route, {})[method] = op
    schemas = spec["components"]["schemas"]
    for name in ("Sample", "SampleEdit", "ReceivedSampleView"):
        if name not in schemas:
            continue
        for key, lo, hi in (
            ("easting", 100000, 1000000),
            ("northing", 1000000, 10000000),
        ):
            schemas[name]["properties"][key] = {
                "type": ["string", "number", "null"],
                "description": f"Coordenada de esta muestra, opcional e independiente. Finita entre {lo} inclusive y {hi} exclusivo, decimales admitidos. Validación de formato, no de ubicación.",
            }
        for key in ("depth_from", "depth_to"):
            schemas[name]["properties"].setdefault(key, {"type": ["string", "number", "null"]})[
                "description"
            ] = "Metros; presentación con dos decimales sin modificar la precisión almacenada."
    for name in ("Sample", "SampleEdit", "ReceivedSample", "ReceivedSampleView"):
        if name in schemas:
            for key in ("weight", "received_weight"):
                if key in schemas[name]["properties"]:
                    schemas[name]["properties"][key]["description"] = (
                        "Kilogramos opcionales, positivos y finitos, máximo un decimal. Se rechaza precisión incompatible sin redondeo."
                    )
    schemas["Catalog"]["properties"]["price"]["description"] = (
        "Precio vigente en USD, obligatorio, positivo, finito y máximo dos decimales."
    )
    catalog_properties = {
        k: schemas["Catalog"]["properties"][k]
        for k in ("code", "name", "method", "category", "active", "price")
    }
    catalog_properties["id"] = {"type": "string", "format": "uuid"}
    spec["paths"]["/catalog"]["get"].update(
        {
            "description": "Metadatos de todos los ensayos autorizados. Selección solo de activos; los deshabilitados permiten mostrar selecciones históricas. price se devuelve únicamente a ADMIN/MANAGER.",
            "responses": {
                **spec["paths"]["/catalog"]["get"]["responses"],
                "200": {
                    "description": "Catálogo; precio solo para ADMIN/MANAGER",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": catalog_properties,
                                },
                            }
                        }
                    },
                },
            },
        }
    )
    spec["paths"]["/management/catalog/{id}"]["put"]["description"] = (
        "ADMIN edita por UUID código, nombre, método, categoría, precio USD y disponibilidad. Cambiar el código conserva ID y relaciones; un código duplicado devuelve409."
    )
    amount = {
        "type": ["string", "number"],
        "description": "Importe exacto en USD, serializado como decimal.",
    }
    schemas["EconomicSummary"] = {
        "type": "object",
        "properties": {
            "currency": {"const": "USD"},
            "price_basis": {"const": "current_catalog"},
            "totals": {
                "type": "object",
                "properties": {k: amount for k in ("completed_total", "completed_month", "projected_total")},
            },
            "monthly": {
                "type": "array",
                "minItems": 12,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "string", "format": "date"},
                        "amount": amount,
                    },
                },
            },
            **{
                k: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "name": {"type": "string"},
                            "amount": amount,
                        },
                    },
                }
                for k in ("by_type", "by_organization")
            },
        },
    }
    spec["paths"]["/dashboard"]["get"]["description"] = (
        "Agregaciones PostgreSQL completas por alcance. economics exclusivamente ADMIN/MANAGER: valor estimado de completados (incluso con solicitud cancelada) y proyección aprobada abierta. Precio vigente, una valoración por muestra–ensayo, fechas de Lima; no pagos ni utilidad neta. TECH conserva únicamente carga propia."
    )
    spec["paths"]["/dashboard"]["get"]["responses"]["200"]["content"] = {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "totals": {"type": "object"},
                    "economics": {"$ref": "#/components/schemas/EconomicSummary"},
                },
                "description": "economics se omite para TECH.",
            }
        }
    }
    for route, key, description in (
        (
            "requests",
            "q",
            "Código de solicitud o proyecto; coincidencia parcial sin distinguir mayúsculas. No existe título de solicitud.",
        ),
        (
            "work",
            "request_q",
            "Código de solicitud; coincidencia parcial sin distinguir mayúsculas.",
        ),
    ):
        next(p for p in spec["paths"]["/" + route]["get"]["parameters"] if p["name"] == key)[
            "description"
        ] = description
    for key in ("target_date", "estimated_arrival_date"):
        spec["paths"]["/requests"]["get"]["responses"]["200"]["content"]["application/json"]["schema"][
            "properties"
        ]["items"]["items"]["properties"][key] = {
            "type": ["string", "null"],
            "format": "date",
        }
    (ROOT / "docs/openapi.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    export_erd(*inspect_schema())
    export_openapi()
    print("README: diccionario; docs: Mermaid, columnas y OpenAPI actualizados.")
