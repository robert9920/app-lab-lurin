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
from services.filters import TASK_STATES, UNDEFINED, request_filters, request_state_filter, state_filter
from services.statuses import assay_case, assay_filter, counts_sql, lifecycle_filter, normalize_counts
from validation import (
    Action,
    AssaysEdit,
    AssaysResubmit,
    AssaysReview,
    Comment,
    DraftCreate,
    DraftEdit,
    Reception,
    RequestEdit,
    TaskUpdate,
    WorkOrder,
    WorkUpdate,
)

bp = func.Blueprint()
SCOPE = REQUEST_SCOPE
TASK_FROM = "FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id JOIN solicitudes r ON r.id=s.solicitud_id\n    JOIN catalogo_ensayos c ON c.id=a.ensayo_id LEFT JOIN usuarios t ON t.id=a.tecnico_id"
OPEN = "a.estado_revision='APPROVED' AND r.estado_solicitud='APPROVED' AND r.estado_general='CREATED' AND a.estado_ensayo NOT IN ('COMPLETED','CANCELLED')"


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
    if req.params.get("scope", "requests") == "catalog":
        require_role(u, "CLIENT")
        org = w.organization_for(db, u)
        if not org["is_internal"]:
            raise AppError(403, "El catálogo de proyectos está disponible para clientes internos.")
        from services.projects import catalog

        page, limit = paging(req)
        return catalog(req.params.get("q", ""), page, limit)
    if req.params.get("scope", "requests") != "requests":
        raise AppError(400, "Filtro de proyectos inválido.")
    return rows(
        db,
        "SELECT DISTINCT r.proyecto_id id,r.proyecto_id code,r.proyecto_id name FROM solicitudes r WHERE r.proyecto_id IS NOT NULL AND "
        + SCOPE
        + " ORDER BY r.proyecto_id",
        **scope_params(u),
    )


@bp.route(route="catalog", methods=["GET"])
@endpoint
def catalog(db, req):
    u = session(db, req)
    fields = "*" if set(u["roles"]) & {"ADMIN", "MANAGER"} else "id,codigo,nombre,metodo,categoria,activo"
    return rows(db, "SELECT " + fields + " FROM catalogo_ensayos ORDER BY categoria,codigo")


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
        created = w.create_request(db, u, body(req, DraftCreate))
        return w.detail(db, u, created["id"])
    params = {
        **scope_params(u),
        "q": "%" + req.params.get("q", "")[:150] + "%",
        "project": req.params.get("project", ""),
    }
    where = (
        SCOPE
        + " AND (:project='' OR r.proyecto_id::text=:project) AND (r.codigo ILIKE :q OR r.proyecto_id ILIKE :q)"
    )
    extra = []
    request_state_filter(req, extra, params)
    lifecycle_filter(req, extra, params)
    assay_filter(req, extra, params)
    request_filters(req, extra, params, dates=True, definition=True)
    if extra:
        where += " AND " + " AND ".join(extra)
    if req.params.get("view") == "reception":
        require_role(u, "ADMIN", "MANAGER", "TECH")
        where += (
            " AND r.estado_general='CREATED' AND r.estado_solicitud IN ('WAITING_ASSAYS','SUBMITTED','OBSERVED','APPROVED') AND (r.codigo_ot IS NULL OR EXISTS(SELECT 1 FROM muestras s WHERE s.solicitud_id=r.id AND s.condicion<>'OK' AND "
            + SAMPLE_SCOPE
            + "))"
        )
        if technical_only(u):
            where += " AND r.estado_solicitud='APPROVED'"
    if req.params.get("view") == "reception":
        condition = req.params.get("condition", "")
        if condition not in ("", "NOT_RECEIVED", "issues", "NO_OT"):
            raise AppError(400, "Filtro de recepción inválido.")
        if condition == "NO_OT":
            where += " AND r.codigo_ot IS NULL"
        elif condition:
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
    reception_select = ""
    if req.params.get("view") == "reception":
        reception_select = (
            "(SELECT jsonb_build_object("
            "'NOT_RECEIVED',count(*) FILTER (WHERE s.condicion='NOT_RECEIVED'),"
            "'OBSERVED',count(*) FILTER (WHERE s.condicion='OBSERVED'),"
            "'DAMAGED',count(*) FILTER (WHERE s.condicion='DAMAGED'),"
            "'INSUFFICIENT',count(*) FILTER (WHERE s.condicion='INSUFFICIENT')) "
            "FROM muestras s WHERE s.solicitud_id=r.id AND " + SAMPLE_SCOPE + ") reception_counts, "
        )
    result = page_result(
        db,
        req,
        "SELECT "
        + reception_select
        + counts_sql()
        + " assay_counts, ("
        + UNDEFINED
        + ") pending_assays, (SELECT count(*) FROM ensayos_muestra ax JOIN muestras s ON s.id=ax.muestra_id WHERE s.solicitud_id=r.id AND ax.estado_revision='PENDING' AND ax.estado_ensayo='PENDING' AND (:all_samples OR ax.tecnico_id=:u)) unapproved_count, r.*,r.proyecto_id project_code,r.proyecto_id project_name,author.nombre requester_name,org.nombre organization_name,\n        (SELECT count(*) FROM muestras s WHERE s.solicitud_id=r.id AND s.condicion<>'OK' AND (:all_samples OR EXISTS(SELECT 1 FROM ensayos_muestra ax WHERE ax.muestra_id=s.id AND ax.tecnico_id=:u))) pending_samples,\n        (SELECT count(*) FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.solicitud_id=r.id AND a.estado_revision<>'REJECTED' AND a.estado_ensayo<>'CANCELLED' AND (:all_samples OR a.tecnico_id=:u)) task_count,\n        (SELECT count(*) FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.solicitud_id=r.id AND a.estado_ensayo='COMPLETED' AND (:all_samples OR a.tecnico_id=:u)) completed_count",
        "FROM solicitudes r JOIN usuarios author ON author.id=r.creado_por JOIN empresas org ON org.id=r.empresa_id",
        where,
        params,
        "r.creado_en DESC,r.id",
    )
    for item in result["items"]:
        item["assay_counts"] = normalize_counts(item["assay_counts"])
    return result


@bp.route(route="requests/{rid}", methods=["GET", "PUT"])
@endpoint
def request_detail(db, req):
    u, rid = session(db, req), uid(req.route_params["rid"])
    if req.method == "PUT":
        current = request_access(db, u, rid)
        w.edit_request(db, u, rid, body(req, DraftEdit if current["status"] == "DRAFT" else RequestEdit))
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
    where = [
        SCOPE,
        "r.estado_solicitud<>'DRAFT'",
        "(:all_samples OR a.tecnico_id=:u)",
        "(a.row_kind='assay' OR r.estado_general='CREATED')",
    ]
    params = scope_params(u)
    for key, column in (
        ("project", "r.proyecto_id"),
        ("request", "r.id"),
        ("technician", "a.tecnico_id"),
        ("assay", "a.ensayo_id"),
    ):
        value = req.params.get(key)
        if value:
            if key == "technician" and value == "unassigned":
                where.append("a.tecnico_id IS NULL")
            else:
                where.append(column + "::text=:" + key)
                params[key] = value
    request_filters(req, where, params)
    state_filter(req, "state", "a.estado_ensayo", TASK_STATES, where, params)
    lifecycle_filter(req, where, params)
    assay_filter(req, where, params, work=True)
    metric = req.params.get("metric", "")
    if req.params.get("request_q"):
        where.append("r.codigo ILIKE :request_q")
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
    work_source = (
        "FROM (SELECT ax.id,ax.muestra_id,ax.ensayo_id,ax.tecnico_id,ax.estado_revision,ax.estado_ensayo,"
        "ax.inicio_previsto,ax.fin_previsto,ax.iniciado_en,ax.completado_en,ax.observaciones,"
        "'assay'::text row_kind FROM ensayos_muestra ax UNION ALL "
        "SELECT NULL::uuid id,sx.id muestra_id,NULL::uuid ensayo_id,NULL::uuid tecnico_id,"
        "NULL::text estado_revision,NULL::text estado_ensayo,NULL::date inicio_previsto,NULL::date fin_previsto,"
        "NULL::timestamptz iniciado_en,NULL::timestamptz completado_en,''::text observaciones,"
        "'sample_without_assays'::text row_kind FROM muestras sx WHERE NOT EXISTS"
        "(SELECT 1 FROM ensayos_muestra ax WHERE ax.muestra_id=sx.id)) a "
        "JOIN muestras s ON s.id=a.muestra_id JOIN solicitudes r ON r.id=s.solicitud_id "
        "LEFT JOIN catalogo_ensayos c ON c.id=a.ensayo_id LEFT JOIN usuarios t ON t.id=a.tecnico_id"
    )
    result = page_result(
        db,
        req,
        "SELECT a.*,s.id sample_id,CASE WHEN a.row_kind='sample_without_assays' THEN 'WAITING_ASSAYS' ELSE "
        + assay_case()
        + " END assay_status,s.codigo_cliente sample_code,s.condicion,c.nombre assay_name,t.nombre technician_name,\n        r.id solicitud_id,r.codigo request_code,author.nombre requester_name,org.nombre organization_name,r.version request_version,r.estado_solicitud workflow_status,r.estado_general request_status,r.codigo_ot,r.proyecto_id project_code",
        work_source
        + " JOIN usuarios author ON author.id=r.creado_por JOIN empresas org ON org.id=r.empresa_id",
        " AND ".join(where),
        params,
        "a.fin_previsto NULLS LAST,r.codigo,s.codigo_cliente,c.nombre,a.id",
    )
    w.review_projection(db, [t for t in result["items"] if t["row_kind"] == "assay"])
    w.state_reason_projection(db, [t for t in result["items"] if t["row_kind"] == "assay"])
    for task in result["items"]:
        task["assigned"] = task["technician_id"] is not None
        task["allowed_actions"] = (
            w.allowed_actions(u, task, task["workflow_status"], task["codigo_ot"])
            if task["row_kind"] == "assay" and task["request_status"] == "CREATED"
            else []
        )
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
            "SELECT count(*) n FROM muestras s JOIN solicitudes r ON r.id=s.solicitud_id WHERE r.estado_general='CREATED' AND r.estado_solicitud IN ('WAITING_ASSAYS','SUBMITTED','OBSERVED','APPROVED') AND "
            + predicate
            + " AND "
            + SAMPLE_SCOPE
            + (" AND r.estado_solicitud='APPROVED'" if technical_only(u) else ""),
            **params,
        )["n"]
    result = {
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
            "WITH weeks AS (SELECT generate_series(\n            date_trunc('week',now() AT TIME ZONE 'America/Lima')-interval '7 weeks',\n            date_trunc('week',now() AT TIME ZONE 'America/Lima'),interval '1 week') week),\n            counts AS (SELECT date_trunc('week',a.completado_en AT TIME ZONE 'America/Lima') week,count(*) numero_intentos\n                FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id JOIN solicitudes r ON r.id=s.solicitud_id\n                WHERE a.estado_revision='APPROVED' AND a.estado_ensayo='COMPLETED' AND r.estado_solicitud IN ('APPROVED','CLOSED') AND (:all_samples OR a.tecnico_id=:u) GROUP BY 1)\n            SELECT w.week::date,coalesce(c.numero_intentos,0) numero_intentos FROM weeks w LEFT JOIN counts c USING(week) ORDER BY w.week",
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
    if set(u["roles"]) & {"ADMIN", "MANAGER"}:
        from services.economics import summary

        result["economics"] = summary(db)
    return result


@bp.route(route="requests/{rid}/work-order", methods=["POST"])
@endpoint
def work_order(db, req):
    u, rid = session(db, req), uid(req.route_params["rid"])
    w.work_order(db, u, rid, body(req, WorkOrder))
    return w.detail(db, u, rid)


@bp.route(route="requests/{rid}/assays", methods=["PUT"])
@endpoint
def edit_assays(db, req):
    u, rid = session(db, req), uid(req.route_params["rid"])
    w.edit_assays(db, u, rid, body(req, AssaysEdit))
    return w.detail(db, u, rid)


@bp.route(route="requests/{rid}/assays/review", methods=["POST"])
@endpoint
def review_assays(db, req):
    u, rid = session(db, req), uid(req.route_params["rid"])
    w.review_assays(db, u, rid, body(req, AssaysReview))
    return w.detail(db, u, rid)


@bp.route(route="requests/{rid}/assays/resubmit", methods=["POST"])
@endpoint
def resubmit_assays(db, req):
    u, rid = session(db, req), uid(req.route_params["rid"])
    w.resubmit_assays(db, u, rid, body(req, AssaysResubmit))
    return w.detail(db, u, rid)


@bp.route(route="filter-options", methods=["GET"])
@endpoint
def filter_options(db, req):
    u = session(db, req)
    require_role(u, "ADMIN", "MANAGER", "TECH")
    kind, view = req.params.get("kind"), req.params.get("view", "requests")
    if kind not in ("requester", "organization") or view not in ("requests", "reception", "work", "reports"):
        raise AppError(400, "Filtro no válido.")
    where = SCOPE
    if view == "reception":
        where += " AND r.estado_general='CREATED' AND r.estado_solicitud IN ('WAITING_ASSAYS','SUBMITTED','OBSERVED','APPROVED')"
        if technical_only(u):
            where += " AND r.estado_solicitud='APPROVED'"
    elif view == "work":
        where += (
            " AND r.estado_solicitud<>'DRAFT' AND EXISTS(SELECT 1 FROM muestras s WHERE s.solicitud_id=r.id AND "
            + SAMPLE_SCOPE
            + ")"
        )
    elif view == "reports":
        where += " AND EXISTS(SELECT 1 FROM informes d WHERE d.solicitud_id=r.id)"
    table, fk = ("usuarios", "creado_por") if kind == "requester" else ("empresas", "empresa_id")
    source = (
        "FROM (SELECT DISTINCT f.id,f.nombre FROM solicitudes r JOIN "
        + table
        + " f ON f.id=r."
        + fk
        + " WHERE "
        + where
        + ") options"
    )
    # Escape wildcards: typing % or _ searches literal characters.
    query = req.params.get("q", "")[:150].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return page_result(
        db,
        req,
        "SELECT *",
        source,
        "nombre ILIKE :q AND (:selected='' OR id::text=:selected)",
        {**scope_params(u), "q": "%" + query + "%", "selected": req.params.get("selected", "")},
        "nombre,id",
    )
