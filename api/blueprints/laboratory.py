import azure.functions as func

from database import one, rows
from errors import AppError
from http_helpers import body, endpoint, uid
from security import (
    REQUEST_SCOPE,
    SAMPLE_SCOPE,
    request_access,
    require_role,
    scope_params,
    session,
    technical_only,
)
from services import workflow as w
from services.common import audit, touch
from validation import Action, Comment, Reception, RequestCreate, RequestEdit, TaskUpdate, WorkUpdate

bp = func.Blueprint()
SCOPE = REQUEST_SCOPE
TASK_FROM = "FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id JOIN solicitudes r ON r.id=s.solicitud_id\n    JOIN proyectos p ON p.id=r.proyecto_id JOIN catalogo_ensayos c ON c.id=a.ensayo_id LEFT JOIN usuarios t ON t.id=a.tecnico_id"
OPEN = "r.estado_solicitud='APPROVED' AND a.estado_ensayo NOT IN ('COMPLETED','CANCELLED')"


def paging(req):
    try:
        return max(1, int(req.params.get("page", "1"))), max(1, min(100, int(req.params.get("limit", "30"))))
    except ValueError:
        raise AppError(400, "Paginación inválida.") from None


def page_result(db, req, select, source, where, params, order):
    page, limit = paging(req)
    total = one(db, "SELECT count(*) n " + source + " WHERE " + where, **params)["n"]
    items = rows(
        db,
        select + " " + source + " WHERE " + where + " ORDER BY " + order + " LIMIT :limit OFFSET :offset",
        **params,
        limit=limit,
        offset=(page - 1) * limit,
    )
    return {"items": items, "total": total, "page": page, "limit": limit}


@bp.route(route="projects", methods=["GET"])
@endpoint
def projects(db, req):
    u = session(db, req)
    return rows(
        db,
        "SELECT p.*,o.nombre organization_name FROM proyectos p JOIN empresas o ON o.id=p.empresa_id\n        WHERE (:global OR (:client AND p.id IN(SELECT proyecto_id FROM miembros_proyecto WHERE usuario_id=:u))\n        OR (:tech AND EXISTS(SELECT 1 FROM solicitudes r JOIN muestras s ON s.solicitud_id=r.id\n        JOIN ensayos_muestra a ON a.muestra_id=s.id WHERE r.proyecto_id=p.id AND r.estado_solicitud<>'DRAFT' AND a.tecnico_id=:u))) ORDER BY p.codigo",
        **scope_params(u),
    )


@bp.route(route="catalog", methods=["GET"])
@endpoint
def catalog(db, req):
    session(db, req)
    return rows(db, "SELECT * FROM catalogo_ensayos ORDER BY categoria,codigo")


@bp.route(route="technicians", methods=["GET"])
@endpoint
def technicians(db, req):
    u = session(db, req)
    require_role(u, "ADMIN", "MANAGER", "TECH")
    return rows(
        db,
        "SELECT id,nombre FROM usuarios WHERE activo AND roles && ARRAY['MANAGER','TECH'] AND (:all_samples OR id=:u) ORDER BY nombre",
        **scope_params(u),
    )


@bp.route(route="requests", methods=["GET", "POST"])
@endpoint
def requests(db, req):
    u = session(db, req)
    if req.method == "POST":
        created = w.create_request(db, u, body(req, RequestCreate))
        return w.detail(db, u, created["id"])
    params = {
        **scope_params(u),
        "q": "%" + req.params.get("q", "")[:150] + "%",
        "status": req.params.get("status", ""),
        "project": req.params.get("project", ""),
    }
    where = (
        SCOPE
        + " AND (:status='' OR r.estado_solicitud=:status) AND (:project='' OR r.proyecto_id::text=:project) AND (r.codigo ILIKE :q OR r.titulo ILIKE :q OR p.codigo ILIKE :q)"
    )
    if req.params.get("view") == "reception":
        require_role(u, "ADMIN", "MANAGER", "TECH")
        where += (
            " AND r.estado_solicitud='APPROVED' AND EXISTS(SELECT 1 FROM muestras s WHERE s.solicitud_id=r.id AND s.condicion<>'OK' AND "
            + SAMPLE_SCOPE
            + ")"
        )
    if req.params.get("view") == "reception":
        condition = req.params.get("condition", "")
        if condition not in ("", "NOT_RECEIVED", "issues"):
            raise AppError(400, "Filtro de recepción inválido.")
        if condition:
            predicate = (
                "s.condicion='NOT_RECEIVED'"
                if condition == "NOT_RECEIVED"
                else "s.condicion IN ('OBSERVED','DAMAGED','INSUFFICIENT')"
            )
            where += (
                " AND EXISTS(SELECT 1 FROM muestras s WHERE s.solicitud_id=r.id AND "
                + predicate
                + " AND "
                + SAMPLE_SCOPE
                + ")"
            )
    return page_result(
        db,
        req,
        "SELECT r.*,p.codigo project_code,p.nombre project_name,\n        (SELECT count(*) FROM muestras s WHERE s.solicitud_id=r.id AND s.condicion<>'OK' AND (:all_samples OR EXISTS(SELECT 1 FROM ensayos_muestra ax WHERE ax.muestra_id=s.id AND ax.tecnico_id=:u))) pending_samples,\n        (SELECT count(*) FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.solicitud_id=r.id AND a.estado_ensayo<>'CANCELLED' AND (:all_samples OR a.tecnico_id=:u)) task_count,\n        (SELECT count(*) FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.solicitud_id=r.id AND a.estado_ensayo='COMPLETED' AND (:all_samples OR a.tecnico_id=:u)) completed_count",
        "FROM solicitudes r JOIN proyectos p ON p.id=r.proyecto_id",
        where,
        params,
        "r.creado_en DESC,r.id",
    )


@bp.route(route="requests/{rid}", methods=["GET", "PUT"])
@endpoint
def request_detail(db, req):
    u, rid = session(db, req), uid(req.route_params["rid"])
    if req.method == "PUT":
        w.edit_request(db, u, rid, body(req, RequestEdit))
    return w.detail(db, u, rid)


@bp.route(route="requests/{rid}/actions", methods=["POST"])
@endpoint
def actions(db, req):
    u, rid = session(db, req), uid(req.route_params["rid"])
    w.action(db, u, rid, body(req, Action))
    return w.detail(db, u, rid)


@bp.route(route="requests/{rid}/receptions", methods=["POST"])
@endpoint
def receptions(db, req):
    u, rid = session(db, req), uid(req.route_params["rid"])
    w.reception(db, u, rid, body(req, Reception))
    return w.detail(db, u, rid)


@bp.route(route="requests/{rid}/tasks", methods=["POST"])
@endpoint
def tasks(db, req):
    u, rid = session(db, req), uid(req.route_params["rid"])
    w.update_tasks(db, u, rid, body(req, TaskUpdate))
    return w.detail(db, u, rid)


@bp.route(route="requests/{rid}/comments", methods=["POST"])
@endpoint
def comments(db, req):
    u, rid, p = session(db, req), uid(req.route_params["rid"]), body(req, Comment)
    request_access(db, u, rid, p.version)
    if p.internal:
        require_role(u, "MANAGER", "TECH")
    audit(db, u, p.body, rid, internal=p.internal, kind="COMMENT")
    touch(db, rid)
    return w.detail(db, u, rid)


@bp.route(route="work", methods=["GET", "POST"])
@endpoint
def work(db, req):
    u = session(db, req)
    require_role(u, "ADMIN", "MANAGER", "TECH")
    if req.method == "POST":
        data = body(req, WorkUpdate)
        if len({r.request_id for r in data.requests}) != len(data.requests):
            raise AppError(400, "Solicitud duplicada.")
        if data.planned_start and data.planned_end and data.planned_end < data.planned_start:
            raise AppError(400, "Fechas inválidas.")
        # Stable lock order; the endpoint transaction rolls back the entire batch on any failure.
        for selection in sorted(data.requests, key=lambda r: str(r.request_id)):
            w.update_tasks(
                db,
                u,
                selection.request_id,
                TaskUpdate(
                    **selection.model_dump(exclude={"request_id"}), **data.model_dump(exclude={"requests"})
                ),
            )
        return {"ok": True}
    where = [SCOPE, "r.estado_solicitud IN ('APPROVED','CLOSED')", "(:all_samples OR a.tecnico_id=:u)"]
    params = scope_params(u)
    for key, column in (
        ("project", "r.proyecto_id"),
        ("request", "r.id"),
        ("technician", "a.tecnico_id"),
        ("assay", "a.ensayo_id"),
        ("state", "a.estado_ensayo"),
    ):
        value = req.params.get(key)
        if value:
            if key == "technician" and value == "unassigned":
                where.append("a.tecnico_id IS NULL")
            else:
                where.append(column + "::text=:" + key)
                params[key] = value
    metric = req.params.get("metric", "")
    if req.params.get("request_q"):
        where.append("(r.codigo ILIKE :request_q OR r.titulo ILIKE :request_q)")
        params["request_q"] = "%" + req.params["request_q"][:150] + "%"
    if metric in ("open", "overdue", "unassigned", "undated", "upcoming"):
        where.append(OPEN)
    if metric == "overdue":
        where.append("a.fin_previsto < (now() AT TIME ZONE 'America/Lima')::date")
    if metric == "unassigned":
        where.append("a.tecnico_id IS NULL")
    if metric == "undated":
        where.append("a.fin_previsto IS NULL")
    if metric == "upcoming":
        where.append("a.fin_previsto >= (now() AT TIME ZONE 'America/Lima')::date")
    result = page_result(
        db,
        req,
        "SELECT a.*,s.codigo_cliente sample_code,s.condicion,c.nombre assay_name,t.nombre technician_name,\n        r.id solicitud_id,r.codigo request_code,r.version request_version,r.estado_solicitud request_status,p.codigo project_code",
        TASK_FROM,
        " AND ".join(where),
        params,
        "a.fin_previsto NULLS LAST,r.codigo,s.codigo_cliente,c.nombre,a.id",
    )
    for task in result["items"]:
        task["assigned"] = task["technician_id"] is not None
        task["allowed_actions"] = w.allowed_actions(u, task, task["request_status"])
    return result


@bp.route(route="dashboard", methods=["GET"])
@endpoint
def dashboard(db, req):
    u = session(db, req)
    require_role(u, "ADMIN", "MANAGER", "TECH")
    params = scope_params(u)
    scope = " AND (:all_samples OR a.tecnico_id=:u)"
    totals = one(
        db,
        "SELECT count(*) open,\n        count(*) FILTER(WHERE a.fin_previsto < (now() AT TIME ZONE 'America/Lima')::date) overdue,\n        count(*) FILTER(WHERE a.tecnico_id IS NULL) unassigned,\n        count(*) FILTER(WHERE a.fin_previsto IS NULL) undated,\n        count(*) FILTER(WHERE a.estado_ensayo='RUNNING') running,\n        count(*) FILTER(WHERE a.estado_ensayo='OBSERVED') observed "
        + TASK_FROM
        + " WHERE "
        + OPEN
        + scope,
        **params,
    )
    for key, predicate in (
        ("pending_samples", "s.condicion='NOT_RECEIVED'"),
        ("observed_samples", "s.condicion IN ('OBSERVED','DAMAGED','INSUFFICIENT')"),
    ):
        totals[key] = one(
            db,
            "SELECT count(*) n FROM muestras s JOIN solicitudes r ON r.id=s.solicitud_id WHERE r.estado_solicitud='APPROVED' AND "
            + predicate
            + " AND "
            + SAMPLE_SCOPE,
            **params,
        )["n"]
    return {
        "personal": technical_only(u),
        "totals": totals,
        "by_type": rows(
            db,
            "SELECT c.id,c.nombre,a.estado_ensayo,count(*) numero_intentos "
            + TASK_FROM
            + " WHERE "
            + OPEN
            + scope
            + " GROUP BY c.id,c.nombre,a.estado_ensayo ORDER BY c.nombre,a.estado_ensayo",
            **params,
        ),
        "by_technician": rows(
            db,
            "SELECT t.id,coalesce(t.nombre,'Sin asignar') nombre,count(*) numero_intentos "
            + TASK_FROM
            + " WHERE "
            + OPEN
            + scope
            + " GROUP BY t.id,t.nombre ORDER BY count(*) DESC",
            **params,
        ),
        "weekly": rows(
            db,
            "WITH weeks AS (SELECT generate_series(\n            date_trunc('week',now() AT TIME ZONE 'America/Lima')-interval '7 weeks',\n            date_trunc('week',now() AT TIME ZONE 'America/Lima'),interval '1 week') week),\n            counts AS (SELECT date_trunc('week',a.completado_en AT TIME ZONE 'America/Lima') week,count(*) numero_intentos\n                FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id JOIN solicitudes r ON r.id=s.solicitud_id\n                WHERE a.estado_ensayo='COMPLETED' AND r.estado_solicitud IN ('APPROVED','CLOSED') AND (:all_samples OR a.tecnico_id=:u) GROUP BY 1)\n            SELECT w.week::date,coalesce(c.numero_intentos,0) numero_intentos FROM weeks w LEFT JOIN counts c USING(week) ORDER BY w.week",
            **params,
        ),
        "upcoming": rows(
            db,
            "SELECT a.id,a.fin_previsto,c.nombre,s.codigo_cliente,r.id solicitud_id,r.codigo request_code,t.nombre technician_name "
            + TASK_FROM
            + " WHERE "
            + OPEN
            + scope
            + " AND a.fin_previsto >= (now() AT TIME ZONE 'America/Lima')::date ORDER BY a.fin_previsto,a.id LIMIT 10",
            **params,
        ),
    }
