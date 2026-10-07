import json
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_v4 import declaration

from database import execute, one
from services import economics
from services import workflow as w
from test_workflow import identity, invoke
from validation import Catalog, ReceivedSample, RequestCreate, Sample


def test_catalog_official_price_edit_by_identity_and_visibility(db, users):
    assert one(db, "SELECT count(*) n FROM catalogo_ensayos")["n"] == 58
    old = one(db, "SELECT * FROM catalogo_ensayos WHERE codigo='LC-001'")
    assert old["price"] == 11 and old["active"]
    payload = {
        "code": "CAMBIADO",
        "name": old["name"],
        "method": "Método validado",
        "category": "Nueva categoría",
        "price": "12.34",
        "active": False,
    }
    for who in ("cliente", "tecnico"):
        data = json.loads(invoke("catalog", headers=identity(db, users[who])).get_body())
        assert all("price" not in a for a in data)
        assert (
            invoke(
                "edit_catalog", "PUT", payload, route={"id": str(old["id"])}, headers=identity(db, users[who])
            ).status_code
            == 403
        )
    response = invoke(
        "edit_catalog", "PUT", payload, route={"id": str(old["id"])}, headers=identity(db, users["admin"])
    )
    assert response.status_code == 200, response.get_body()
    assert one(db, "SELECT count(*) n FROM catalogo_ensayos")["n"] == 58
    updated = one(db, "SELECT * FROM catalogo_ensayos WHERE id=:id", id=old["id"])
    assert updated["code"] == "CAMBIADO" and updated["price"] == Decimal("12.34") and not updated["active"]
    assert any(
        "price" in a for a in json.loads(invoke("catalog", headers=identity(db, users["jefe"])).get_body())
    )
    payload["code"] = "LC-002"
    assert (
        invoke(
            "edit_catalog", "PUT", payload, route={"id": str(old["id"])}, headers=identity(db, users["admin"])
        ).status_code
        == 409
    )


def test_request_dates_coordinates_per_sample_and_removed_title(db, users):
    data = declaration(estimated_arrival_date="2026-11-01", target_date="2026-11-10")
    data["samples"][0].update(easting="123456.12", depth_from="5.12345")
    data["samples"][1].update(northing="8765432.1")
    rid = w.create_request(db, users["cliente"], RequestCreate(**data))["id"]
    r = w.detail(db, users["cliente"], rid)
    assert "title" not in r and "easting" not in r and "northing" not in r
    assert r["estimated_arrival_date"].isoformat() == "2026-11-01"
    assert r["samples"][0]["easting"] == Decimal("123456.12")
    assert r["samples"][0]["depth_from"] == Decimal("5.12345")
    assert r["samples"][1]["northing"] == Decimal("8765432.1")
    with pytest.raises(ValidationError):
        RequestCreate(**declaration(), title="Campo retirado")


@pytest.mark.parametrize("weight", ["0", "-1", "1.01", "NaN", "Infinity"])
def test_weight_precision_and_finite_validation(weight):
    with pytest.raises(ValidationError):
        Sample(client_code="M", material="Suelo", weight=weight)
    with pytest.raises(ValidationError):
        ReceivedSample(
            sample_id=uuid4(), codigo_recepcion="R", codigo_laboratorio="L", received_weight=weight
        )


@pytest.mark.parametrize("price", ["0", "-1", "1.001", "NaN", "Infinity"])
def test_price_validation(price):
    with pytest.raises(ValidationError):
        Catalog(code="X", name="Ensayo", price=price)


def test_income_all_records_current_prices_cancelled_history_and_role_scope(db, users):
    before = economics.summary(db)
    aid = one(db, "SELECT id FROM catalogo_ensayos WHERE codigo='LC-001'")["id"]
    rid = one(db, "SELECT id FROM solicitudes WHERE codigo='SOL-DEMO-001'")["id"]
    execute(
        db,
        """WITH s AS (INSERT INTO muestras(solicitud_id,codigo_cliente) SELECT :r,'ECON-'||n FROM generate_series(1,125) n RETURNING id)
      INSERT INTO ensayos_muestra(muestra_id,ensayo_id,tecnico_id,estado_revision,estado_ensayo,iniciado_en,completado_en)
      SELECT id,:a,:u,'APPROVED','COMPLETED',now()-interval '1 hour',now() FROM s""",
        r=rid,
        a=aid,
        u=users["tecnico"]["id"],
    )
    after = economics.summary(db)
    assert after["totals"]["completed_total"] - before["totals"]["completed_total"] == Decimal(125 * 11)
    assert after["totals"]["completed_month"] - before["totals"]["completed_month"] == Decimal(125 * 11)
    execute(db, "UPDATE solicitudes SET estado_general='CANCELLED' WHERE id=:id", id=rid)
    cancelled = economics.summary(db)
    assert cancelled["totals"]["completed_total"] == after["totals"]["completed_total"]
    assert cancelled["totals"]["projected_total"] == 0
    execute(db, "UPDATE catalogo_ensayos SET precio=22 WHERE id=:id", id=aid)
    assert economics.summary(db)["totals"]["completed_total"] == after["totals"]["completed_total"] + 125 * 11
    assert len(after["monthly"]) == 12
    assert sum(x["amount"] for x in after["by_type"]) == after["totals"]["completed_total"]
    assert sum(x["amount"] for x in after["by_organization"]) == after["totals"]["completed_total"]
    assert "economics" in json.loads(invoke("dashboard", headers=identity(db, users["jefe"])).get_body())
    assert "economics" not in json.loads(
        invoke("dashboard", headers=identity(db, users["tecnico"])).get_body()
    )
    assert invoke("dashboard", headers=identity(db, users["cliente"])).status_code == 403
