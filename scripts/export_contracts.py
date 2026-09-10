"""Exporta contratos, diccionario y ERD desde la base v2 instalada (solo lectura)."""

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
import validation as v  # noqa: E402
from database import engine, rows  # noqa: E402
from function_app import app  # noqa: E402

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


from schema_names import TABLE_NAMES, FIELD_NAMES

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


def inspect_schema():
    with engine().connect() as db:
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
        raise RuntimeError("El exportador requiere exclusivamente las 13 tablas del esquema v3")
    return columns, foreign, primary


def export_erd(columns, foreign, primary):
    lines = [
        "---",
        "title: Laboratorio Lara Consulting · PostgreSQL v3",
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
    models = {
        "auth/login": v.Login,
        "requests": v.RequestCreate,
        "requests/{rid}": v.RequestEdit,
        "requests/{rid}/actions": v.Action,
        "requests/{rid}/receptions": v.Reception,
        "requests/{rid}/tasks": v.TaskUpdate,
        "requests/{rid}/comments": v.Comment,
        "work": v.WorkUpdate,
        "management/organizations": v.Organization,
        "management/projects": v.Project,
        "management/users": v.UserCreate,
        "management/users/{id}": v.UserEdit,
        "management/users/{id}/password": v.Password,
        "management/catalog": v.Catalog,
    }
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Laboratorio Lara Consulting",
            "version": "3.0.0",
            "description": "Sesión opaca en cookie lab_session. Escrituras requieren Origin exacto y X-CSRF-Token de GET /session. "
            "ADMIN administra; MANAGER dirige; TECH solo consulta sus solicitudes, muestras y ensayos asignados; CLIENT accede por proyecto. Borradores exclusivos de su autor. "
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
        "requests": ["q", "status", "project", "view", "condition", "page", "limit"],
        "work": [
            "project",
            "request_q",
            "request",
            "technician",
            "assay",
            "state",
            "metric",
            "page",
            "limit",
        ],
        "reports": ["q", "project", "request", "page", "limit"],
        "requests/{rid}/print/{kind}": ["sample_ids"],
    }
    spec["components"]["schemas"].update(
        {
            "WorkTask": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "state": {"enum": ["PENDING", "RUNNING", "OBSERVED", "COMPLETED", "CANCELLED"]},
                    "technician_id": {"type": ["string", "null"]},
                    "assigned": {
                        "type": "boolean",
                        "description": "Derivado de tecnico_id; no es un estado ni columna duplicada.",
                    },
                    "allowed_actions": {
                        "type": "array",
                        "items": {"enum": ["assign", "start", "observe", "complete", "resume", "cancel"]},
                        "description": "Acciones autorizadas por rol, asignación, material y estado. La API valida de nuevo al ejecutar.",
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
                    "can_receive": {
                        "type": "boolean",
                        "description": "Permiso operativo sobre la muestra; recibir requiere además solicitud aprobada.",
                    },
                },
            },
        }
    )
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
            if route == "auth/login":
                op["security"] = []
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
                    if name == "condition":
                        schema["enum"] = ["", "NOT_RECEIVED", "issues"]
                        op["parameters"][-1]["description"] = (
                            "En view=reception, NOT_RECEIVED exige al menos una muestra sin recibir; issues exige material observado, dañado o insuficiente."
                        )
                    if name == "sample_ids":
                        op["parameters"][-1]["description"] = (
                            "Obligatorio para labels: 1 a 200 UUID separados por comas, sin duplicados, recibidos y autorizados. PDF A4 2x4, etiquetas 95x68 mm."
                        )
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
    (ROOT / "docs/openapi.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    export_erd(*inspect_schema())
    export_openapi()
    print("README: diccionario; docs: Mermaid, columnas y OpenAPI actualizados.")
