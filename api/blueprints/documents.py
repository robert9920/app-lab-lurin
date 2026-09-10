import hashlib
from uuid import uuid4

import azure.functions as func

from blueprints.laboratory import SCOPE, page_result
from database import one
from errors import AppError
from http_helpers import endpoint, uid
from security import laboratory_access, request_access, require_role, scope_params, session
from services import documents as d
from services import storage
from services.common import audit, touch
from services.workflow import detail, require_approved

bp = func.Blueprint()


def pdf_response(content, name, inline=False):
    return func.HttpResponse(
        content,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{name}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
        },
    )


@bp.route(route="requests/{rid}/reports", methods=["POST"])
@endpoint
def upload(db, req):
    u, rid = session(db, req), uid(req.route_params["rid"])
    require_role(u, "MANAGER", "TECH")
    try:
        version = int(req.headers.get("x-request-version", ""))
        if version < 1:
            raise ValueError()
    except ValueError:
        raise AppError(400, "Falta la versión de la solicitud.") from None
    require_approved(laboratory_access(db, u, rid, version))
    if req.headers.get("content-type", "").split(";")[0] != "application/pdf":
        raise AppError(415, "Se requiere application/pdf.")
    content = req.get_body()
    d.validate_pdf(content)
    report_version = one(
        db, "SELECT coalesce(max(version),0)+1 v FROM informes WHERE solicitud_id=:id", id=rid
    )["v"]
    did = uuid4()
    key = f"{rid}/{did}.pdf"
    name = f"Informe-{report_version}.pdf"
    storage.put(key, content)
    report = one(
        db,
        "INSERT INTO informes(id,solicitud_id,version,nombre,clave_archivo,sha256,tamano_bytes,subido_por)\n        VALUES(:id,:rid,:version,:name,:key,:sha,:bytes,:uid) RETURNING id,version,nombre",
        id=did,
        rid=rid,
        version=report_version,
        name=name,
        key=key,
        sha=hashlib.sha256(content).hexdigest(),
        bytes=len(content),
        uid=u["id"],
    )
    audit(db, u, "Informe disponible", rid, {"report_id": did, "version": report_version}, internal=False)
    touch(db, rid)
    return report


@bp.route(route="reports", methods=["GET"])
@endpoint
def reports(db, req):
    u = session(db, req)
    where = (
        SCOPE
        + " AND (:project='' OR r.proyecto_id::text=:project) AND (:request='' OR r.id::text=:request) AND (r.codigo ILIKE :q OR p.codigo ILIKE :q OR r.titulo ILIKE :q)"
    )
    return page_result(
        db,
        req,
        "SELECT d.id,d.solicitud_id,d.version,d.nombre,d.tamano_bytes,d.creado_en,r.codigo request_code,p.codigo project_code,u.nombre uploaded_by_name",
        "FROM informes d JOIN solicitudes r ON r.id=d.solicitud_id JOIN proyectos p ON p.id=r.proyecto_id JOIN usuarios u ON u.id=d.subido_por",
        where,
        {
            **scope_params(u),
            "project": req.params.get("project", ""),
            "request": req.params.get("request", ""),
            "q": "%" + req.params.get("q", "")[:150] + "%",
        },
        "d.creado_en DESC,d.id",
    )


@bp.route(route="reports/{did}/download", methods=["GET"])
@endpoint
def download(db, req):
    u = session(db, req)
    doc = one(db, "SELECT * FROM informes WHERE id=:id", id=uid(req.route_params["did"]))
    if not doc:
        raise AppError(404, "Informe no encontrado.")
    request_access(db, u, doc["request_id"])
    content = storage.get(doc["storage_key"])
    audit(db, u, "Informe consultado", doc["request_id"], {"report_id": doc["id"]})
    return pdf_response(content, doc["name"], req.params.get("inline") == "true")


@bp.route(route="requests/{rid}/print/{kind}", methods=["GET"])
@endpoint
def print_document(db, req):
    u = session(db, req)
    require_role(u, "MANAGER", "TECH")
    kind = req.route_params["kind"]
    if kind not in ("receipt", "labels"):
        raise AppError(404, "Documento no disponible.")
    data = detail(db, u, uid(req.route_params["rid"]))
    laboratory_access(db, u, data["id"])
    data["samples"] = [s for s in data["samples"] if s["can_receive"]]
    if kind == "labels":
        ids = req.params.get("sample_ids", "").split(",")
        if not ids or not all(ids) or len(ids) > 200:
            raise AppError(400, "Selecciona entre 1 y 200 muestras recibidas.")
        selected = {uid(i) for i in ids}
        if len(selected) != len(ids):
            raise AppError(400, "Muestra duplicada.")
        samples = {s["id"]: s for s in data["samples"]}
        if not selected.issubset(samples):
            raise AppError(404, "Muestra no encontrada.")
        data["samples"] = [samples[uid(i)] for i in ids]
        if any(
            not s["received_at"] or not s["codigo_recepcion"] or not s["codigo_laboratorio"]
            for s in data["samples"]
        ):
            raise AppError(409, "Confirma la recepción y los códigos antes de imprimir.")
    return pdf_response(d.render(data, kind), kind + ".pdf")
