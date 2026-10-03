"""Shared, parameterized filters. Authorization is always supplied separately."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from errors import AppError
from http_helpers import uid
from security import SAMPLE_SCOPE

REQUEST_STATES = {"DRAFT", "WAITING_ASSAYS", "SUBMITTED", "OBSERVED", "APPROVED", "REJECTED", "CLOSED"}
TASK_STATES = {"PENDING", "RUNNING", "OBSERVED", "COMPLETED", "CANCELLED"}
UNDEFINED = (
    "EXISTS(SELECT 1 FROM muestras s WHERE s.solicitud_id=r.id AND "
    + SAMPLE_SCOPE
    + " AND NOT EXISTS(SELECT 1 FROM ensayos_muestra ax WHERE ax.muestra_id=s.id))"
)
AWAITING_REVIEW = (
    "EXISTS(SELECT 1 FROM ensayos_muestra ax JOIN muestras s ON s.id=ax.muestra_id WHERE s.solicitud_id=r.id AND ax.estado_revision='PENDING' AND ax.estado_ensayo='PENDING' AND "
    + SAMPLE_SCOPE
    + ")"
)


def state_filter(req, key, column, allowed, where, params):
    raw = req.params.get(key, "")
    if not raw:
        return
    values = list(dict.fromkeys(raw.split(",")))
    if not set(values).issubset(allowed):
        raise AppError(400, "Selecciona estados válidos.")
    params[key + "_values"] = values
    where.append(column + "=ANY(:" + key + "_values)")


def request_state_filter(req, where, params):
    raw = req.params.get("status", "")
    if not raw:
        return
    values = list(dict.fromkeys(raw.split(",")))
    if not set(values).issubset(REQUEST_STATES):
        raise AppError(400, "Selecciona estados válidos.")
    predicates = []
    principal = [v for v in values if v not in ("SUBMITTED", "WAITING_ASSAYS")]
    if principal:
        params["status_values"] = principal
        predicates.append("r.estado_solicitud=ANY(:status_values)")
    if "SUBMITTED" in values:
        predicates.append(
            "(r.estado_solicitud IN ('WAITING_ASSAYS','SUBMITTED','APPROVED') AND " + AWAITING_REVIEW + ")"
        )
    if "WAITING_ASSAYS" in values:
        predicates.append(
            "(r.estado_solicitud IN ('WAITING_ASSAYS','SUBMITTED','OBSERVED','APPROVED') AND "
            + UNDEFINED
            + ")"
        )
    where.append("(" + " OR ".join(predicates) + ")")


def request_filters(req, where, params, *, dates=False, definition=False):
    for key, column in (("requester", "r.creado_por"), ("organization", "r.empresa_id")):
        if req.params.get(key):
            params[key] = uid(req.params[key])
            where.append(column + "=:" + key)
    if definition and req.params.get("pending_assays", ""):
        value = req.params["pending_assays"]
        if value not in ("true", "false"):
            raise AppError(400, "Filtro de ensayos por definir inválido.")
        where.append(("" if value == "true" else "NOT ") + UNDEFINED)
    if dates:
        parsed = {}
        for key in ("created_from", "created_to"):
            if req.params.get(key):
                try:
                    parsed[key] = date.fromisoformat(req.params[key])
                except ValueError:
                    raise AppError(400, "Fecha de creación inválida.") from None
        if len(parsed) == 2 and parsed["created_from"] > parsed["created_to"]:
            raise AppError(400, "La fecha Desde no puede superar Hasta.")
        for key, value in parsed.items():
            try:
                boundary = value + timedelta(days=1) if key == "created_to" else value
                params[key] = datetime.combine(boundary, time(), ZoneInfo("America/Lima"))
            except OverflowError:
                raise AppError(400, "Fecha fuera del rango admitido.") from None
            where.append("r.creado_en" + ("<" if key == "created_to" else ">=") + ":" + key)
