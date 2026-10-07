"""Derived assay categories shared by lists, filters and request summaries."""

from database import one
from errors import AppError
from security import SAMPLE_SCOPE

ASSAY_STATUSES = (
    "PENDING_REVIEW",
    "PENDING_EXECUTION",
    "RUNNING",
    "WAITING_ASSAYS",
    "REJECTED",
    "COMPLETED",
    "CANCELLED",
    "OBSERVED",
)
REQUEST_STATUSES = {"DRAFT", "CREATED", "CANCELLED", "CLOSED"}


def assay_case(alias="a"):
    return (
        f"CASE WHEN {alias}.estado_ensayo='CANCELLED' THEN 'CANCELLED' "
        f"WHEN {alias}.estado_revision='REJECTED' THEN 'REJECTED' "
        f"WHEN {alias}.estado_revision='PENDING' THEN 'PENDING_REVIEW' "
        f"WHEN {alias}.estado_ensayo='PENDING' THEN 'PENDING_EXECUTION' "
        f"ELSE {alias}.estado_ensayo END"
    )


def counts_sql():
    return (
        "coalesce((SELECT jsonb_object_agg(category,n) FROM (SELECT "
        + assay_case()
        + " category,count(*) n FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id "
        "WHERE s.solicitud_id=r.id AND (:all_samples OR (:client AND r.creado_por=:u) OR a.tecnico_id=:u) GROUP BY 1) grouped),'{}'::jsonb) "
        "|| jsonb_build_object('WAITING_ASSAYS',CASE WHEN r.estado_general='CREATED' THEN "
        "(SELECT count(*) FROM muestras s WHERE s.solicitud_id=r.id AND "
        + "("
        + SAMPLE_SCOPE
        + " OR (:client AND r.creado_por=:u))"
        + " AND NOT EXISTS(SELECT 1 FROM ensayos_muestra ax WHERE ax.muestra_id=s.id)) ELSE 0 END)"
    )


def request_counts(db, rid, params):
    return normalize_counts(
        one(
            db,
            "SELECT " + counts_sql() + " assay_counts FROM solicitudes r WHERE r.id=:rid",
            rid=rid,
            **params,
        )["assay_counts"]
    )


def normalize_counts(counts):
    return {key: int(counts.get(key, 0)) for key in ASSAY_STATUSES}


def csv_values(req, key, allowed):
    raw = req.params.get(key, "")
    if not raw:
        return []
    values = list(dict.fromkeys(raw.split(",")))
    if not set(values).issubset(allowed):
        raise AppError(400, "Selecciona estados válidos.")
    return values


def lifecycle_filter(req, where, params):
    values = csv_values(req, "request_status", REQUEST_STATUSES)
    if values:
        params["request_status_values"] = values
        where.append(
            "(CASE WHEN r.estado_solicitud='DRAFT' THEN 'DRAFT' ELSE r.estado_general END)=ANY(:request_status_values)"
        )


def assay_filter(req, where, params, *, work=False):
    values = csv_values(req, "assay_status", ASSAY_STATUSES)
    if not values:
        return
    params["assay_status_values"] = values
    if work:
        where.append(
            "(CASE WHEN a.row_kind='sample_without_assays' THEN 'WAITING_ASSAYS' ELSE "
            + assay_case()
            + " END)=ANY(:assay_status_values)"
        )
    else:
        where.append(
            "EXISTS(SELECT 1 FROM jsonb_each_text("
            + counts_sql()
            + ") categories WHERE categories.key=ANY(:assay_status_values) AND categories.value::bigint>0)"
        )
