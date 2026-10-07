"""Estimated income at current catalog prices; one charge per sample-assay."""

from database import one, rows

SOURCE = (
    " FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id "
    "JOIN solicitudes r ON r.id=s.solicitud_id "
    "JOIN catalogo_ensayos c ON c.id=a.ensayo_id "
    "JOIN empresas o ON o.id=r.empresa_id "
)
COMPLETED = "a.estado_revision='APPROVED' AND a.estado_ensayo='COMPLETED' AND r.estado_solicitud<>'DRAFT'"
PROJECTED = (
    "a.estado_revision='APPROVED' AND a.estado_ensayo IN ('PENDING','RUNNING','OBSERVED') "
    "AND r.estado_general='CREATED' AND r.estado_solicitud='APPROVED'"
)


def summary(db):
    totals = one(
        db,
        "SELECT coalesce(sum(c.precio) FILTER(WHERE " + COMPLETED + "),0) completed_total,"
        "coalesce(sum(c.precio) FILTER(WHERE "
        + COMPLETED
        + " AND date_trunc('month',a.completado_en AT TIME ZONE 'America/Lima')="
        "date_trunc('month',now() AT TIME ZONE 'America/Lima')),0) completed_month,"
        "coalesce(sum(c.precio) FILTER(WHERE " + PROJECTED + "),0) projected_total" + SOURCE,
    )
    monthly = rows(
        db,
        "WITH months AS (SELECT generate_series(date_trunc('month',now() AT TIME ZONE 'America/Lima')"
        "-interval '11 months',date_trunc('month',now() AT TIME ZONE 'America/Lima'),interval '1 month') AS periodo),"
        "amounts AS (SELECT date_trunc('month',a.completado_en AT TIME ZONE 'America/Lima') AS periodo,"
        "sum(c.precio) amount" + SOURCE + " WHERE " + COMPLETED + " GROUP BY 1) "
        "SELECT m.periodo::date AS month,coalesce(a.amount,0) amount FROM months m LEFT JOIN amounts a USING(periodo) ORDER BY m.periodo",
    )
    return {
        "currency": "USD",
        "price_basis": "current_catalog",
        "totals": totals,
        "monthly": monthly,
        "by_type": rows(
            db,
            "SELECT c.id,c.nombre,sum(c.precio) amount"
            + SOURCE
            + " WHERE "
            + COMPLETED
            + " GROUP BY c.id,c.nombre ORDER BY amount DESC,c.nombre",
        ),
        "by_organization": rows(
            db,
            "SELECT o.id,o.nombre,sum(c.precio) amount"
            + SOURCE
            + " WHERE "
            + COMPLETED
            + " GROUP BY o.id,o.nombre ORDER BY amount DESC,o.nombre",
        ),
    }
