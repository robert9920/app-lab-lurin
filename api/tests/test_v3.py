import json
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

import pytest
from pypdf import PdfReader
from reportlab.lib.units import mm
from sqlalchemy.exc import IntegrityError

from database import execute, one
from errors import AppError
from services import workflow as w
from services.common import audit
from services.documents import render_labels
from test_workflow import RID, identity, invoke
from validation import Reception, RequestCreate, TaskUpdate


def result(name, db, user, **kwargs):
    response = invoke(name, headers=identity(db, user), **kwargs)
    assert response.status_code == 200, response.get_body()
    return json.loads(response.get_body())


def test_draft_author_only_lists_detail_and_creation(db, users):
    draft = "40000000-0000-0000-0000-000000000003"
    # Another client in exactly the same project still cannot read the draft.
    execute(
        db,
        "INSERT INTO miembros_proyecto(usuario_id,proyecto_id) VALUES(:u,:p)",
        u=users["cliente"]["id"],
        p="30000000-0000-0000-0000-000000000003",
    )
    for name in ("admin", "jefe", "tecnico", "cliente"):
        h = identity(db, users[name])
        assert invoke("request_detail", route={"rid": draft}, headers=h).status_code == 404
        listed = result("requests", db, users[name], params={"status": "DRAFT"})
        assert not listed["items"]
        assert invoke(
            "print_document",
            route={"rid": draft, "kind": "labels"},
            params={"sample_ids": "50000000-0000-0000-0000-000000000004"},
            headers=h,
        ).status_code in (403, 404)
    assert result("request_detail", db, users["externo"], route={"rid": draft})["status"] == "DRAFT"
    data = RequestCreate(
        project_id="30000000-0000-0000-0000-000000000001",
        title="Privacidad",
        samples=[
            {"client_code": "S", "assay_ids": [one(db, "SELECT id FROM catalogo_ensayos LIMIT 1")["id"]]}
        ],
    )
    for name in ("admin", "jefe", "tecnico"):
        with pytest.raises(AppError) as error:
            w.create_request(db, users[name], data)
        assert error.value.status == 403


def second_technician(db):
    return one(
        db,
        "INSERT INTO usuarios(nombre,correo,roles,hash_contrasena) VALUES('Otro técnico',:email,ARRAY['TECH'],'!NOT_INITIALIZED') RETURNING *",
        email=str(uuid4()) + "@example.com",
    )


def test_technical_scope_every_surface_and_dashboard(db, users):
    other = second_technician(db)
    task = one(
        db,
        "SELECT a.id,a.muestra_id FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.codigo_cliente='M-02' LIMIT 1",
    )
    execute(db, "UPDATE ensayos_muestra SET tecnico_id=:u WHERE id=:id", u=other["id"], id=task["id"])
    audit(
        db,
        users["jefe"],
        "Ensayo actualizado",
        RID,
        {"task_id": task["id"], "from": "PENDING", "to": "PENDING", "reason": "Solo del segundo técnico"},
    )
    audit(
        db,
        users["jefe"],
        "Recepción registrada",
        RID,
        {
            "samples": [
                {
                    "sample_id": task["sample_id"],
                    "after": {"condition": "OK", "reception_notes": "Nota de otra muestra"},
                }
            ]
        },
        internal=False,
    )
    h = identity(db, other)
    detail = result("request_detail", db, other, route={"rid": RID})
    assert [t["id"] for t in detail["tasks"]] == [str(task["id"])]
    assert [s["id"] for s in detail["samples"]] == [str(task["sample_id"])]
    mine = result("request_detail", db, users["tecnico"], route={"rid": RID})
    assert "Solo del segundo técnico" not in json.dumps(mine)
    assert "Nota de otra muestra" not in json.dumps(mine)
    assert all("detail" not in a for a in mine["activity"])
    for name, params in [
        ("work", {}),
        ("work", {"technician": str(users["tecnico"]["id"])}),
        ("requests", {"view": "reception", "condition": "NOT_RECEIVED"}),
    ]:
        data = result(name, db, other, params=params)
        if name == "work":
            assert all(t["technician_id"] == str(other["id"]) for t in data["items"])
        else:
            assert [r["id"] for r in data["items"]] == [RID]
    dash = result("dashboard", db, other)
    assert dash["personal"] and dash["totals"]["open"] == 1 and dash["totals"]["pending_samples"] == 1
    assert sum(t["count"] for t in dash["by_type"]) == 1
    assert sum(t["count"] for t in dash["weekly"]) == 0
    assert (
        invoke("request_detail", route={"rid": "40000000-0000-0000-0000-000000000002"}, headers=h).status_code
        == 404
    )
    bad = {
        "version": 1,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "samples": [
            {
                "sample_id": "50000000-0000-0000-0000-000000000001",
                "codigo_recepcion": "REC-X",
                "codigo_laboratorio": "LAB-X",
            }
        ],
    }
    assert invoke("receptions", "POST", bad, route={"rid": RID}, headers=h).status_code == 404
    assert (
        invoke(
            "print_document",
            route={"rid": RID, "kind": "labels"},
            params={"sample_ids": "50000000-0000-0000-0000-000000000001"},
            headers=h,
        ).status_code
        == 404
    )
    execute(
        db,
        "INSERT INTO informes(solicitud_id,version,nombre,clave_archivo,sha256,tamano_bytes,subido_por) VALUES(:r,1,'Test.pdf',:key,'test',1,:u)",
        r=RID,
        key=str(uuid4()),
        u=users["jefe"]["id"],
    )
    assert result("reports", db, other)["total"] == 1
    execute(db, "UPDATE ensayos_muestra SET tecnico_id=NULL WHERE id=:id", id=task["id"])
    assert result("reports", db, other)["total"] == 0
    assert (
        invoke(
            "download",
            route={"did": str(one(db, "SELECT id FROM informes WHERE solicitud_id=:r", r=RID)["id"])},
            headers=h,
        ).status_code
        == 404
    )


def test_pending_receipt_filter_excludes_only_nonconforming(db, users):
    execute(
        db,
        "UPDATE muestras SET condicion='OBSERVED',recibido_en=now(),recibido_por=:u,observaciones_recepcion='Recepción observada',codigo_recepcion='REC-X',codigo_laboratorio='LAB-X' WHERE codigo_cliente='M-02'",
        u=users["jefe"]["id"],
    )
    assert result("requests", db, users["jefe"], params={"view": "reception"})["total"] == 1
    assert (
        result("requests", db, users["jefe"], params={"view": "reception", "condition": "NOT_RECEIVED"})[
            "total"
        ]
        == 0
    )
    assert result("dashboard", db, users["jefe"])["totals"]["pending_samples"] == 0


def test_assignment_state_machine_and_resume(db, users):
    rid = RID
    task = one(
        db,
        "SELECT a.*,s.condicion FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.codigo_cliente='M-01' AND a.estado_ensayo='PENDING'",
    )
    execute(db, "UPDATE ensayos_muestra SET tecnico_id=NULL WHERE id=:id", id=task["id"])
    task["technician_id"] = None
    assert w.allowed_actions(users["jefe"], task, "APPROVED") == ["assign", "cancel"]

    def act(user, action, version, **kwargs):
        w.update_tasks(
            db, user, rid, TaskUpdate(version=version, task_ids=[task["id"]], action=action, **kwargs)
        )

    act(users["jefe"], "assign", 1, technician_id=users["tecnico"]["id"])
    current = one(db, "SELECT * FROM ensayos_muestra WHERE id=:id", id=task["id"])
    assert current["state"] == "PENDING" and current["technician_id"] == users["tecnico"]["id"]
    with pytest.raises(AppError):
        act(users["tecnico"], "complete", 2)
    with pytest.raises(AppError):
        act(users["tecnico"], "observe", 2, reason="Aún no inició")
    act(users["tecnico"], "start", 2)
    act(users["tecnico"], "observe", 3, reason="Revisar montaje")
    started = one(db, "SELECT iniciado_en FROM ensayos_muestra WHERE id=:id", id=task["id"])["started_at"]
    with pytest.raises(AppError) as error:
        act(users["tecnico"], "resume", 4, reason="Revisión lista")
    assert error.value.status == 403
    act(users["jefe"], "resume", 4, reason="Revisión lista")
    assert (
        one(db, "SELECT iniciado_en FROM ensayos_muestra WHERE id=:id", id=task["id"])["started_at"]
        == started
    )
    act(users["tecnico"], "complete", 5)
    assert (
        one(db, "SELECT estado_ensayo FROM ensayos_muestra WHERE id=:id", id=task["id"])["state"]
        == "COMPLETED"
    )
    with pytest.raises(AppError):
        act(users["jefe"], "assign", 6, technician_id=users["jefe"]["id"])


def test_receipt_code_normalization_uniqueness_and_atomicity(db, users):
    r = w.detail(db, users["jefe"], RID)
    sid = next(s["id"] for s in r["samples"] if s["client_code"] == "M-02")

    def receive(code):
        return Reception(
            version=1,
            received_at=datetime.now(timezone.utc),
            samples=[{"sample_id": sid, "codigo_recepcion": " rec-demo-001 ", "codigo_laboratorio": code}],
        )

    with pytest.raises(IntegrityError), db.begin_nested():
        w.reception(db, users["jefe"], RID, receive(" lab-demo-001 "))
    w.reception(db, users["jefe"], RID, receive(" lab-new-002 "))
    s = one(db, "SELECT * FROM muestras WHERE id=:id", id=sid)
    assert s["codigo_recepcion"] == "REC-DEMO-001" and s["codigo_laboratorio"] == "LAB-NEW-002"
    assert w.detail(db, users["cliente"], RID)["version"] == 2


def test_bulk_second_request_failure_reverts_first_assignment(db, users):
    first = one(
        db,
        "SELECT a.* FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.codigo_cliente='M-02' LIMIT 1",
    )
    second = one(
        db,
        "SELECT a.id,s.solicitud_id FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.codigo_cliente='RF-01' LIMIT 1",
    )
    response = invoke(
        "work",
        "POST",
        {
            "action": "assign",
            "technician_id": str(users["tecnico"]["id"]),
            "requests": [
                {"request_id": RID, "version": 1, "task_ids": [str(first["id"])]},
                {"request_id": str(second["request_id"]), "version": 1, "task_ids": [str(second["id"])]},
            ],
        },
        headers=identity(db, users["jefe"]),
    )
    assert response.status_code == 409
    assert (
        one(db, "SELECT tecnico_id FROM ensayos_muestra WHERE id=:id", id=first["id"])["technician_id"]
        is None
    )
    assert one(db, "SELECT version FROM solicitudes WHERE id=:id", id=RID)["version"] == 1


def test_technician_with_client_role_can_draft_without_operational_access(db, users):
    user = users["tecnico"]
    user["roles"] = ["TECH", "CLIENT"]
    execute(
        db,
        "UPDATE usuarios SET roles=ARRAY['TECH','CLIENT'],empresa_id=:o WHERE id=:u",
        o=users["cliente"]["organization_id"],
        u=user["id"],
    )
    project = "30000000-0000-0000-0000-000000000001"
    execute(
        db, "INSERT INTO miembros_proyecto(usuario_id,proyecto_id) VALUES(:u,:p)", u=user["id"], p=project
    )
    rid = w.create_request(
        db,
        user,
        RequestCreate(
            project_id=project,
            title="Pedido propio del técnico",
            samples=[
                {
                    "client_code": "M-PROPIA",
                    "assay_ids": [one(db, "SELECT id FROM catalogo_ensayos LIMIT 1")["id"]],
                }
            ],
        ),
    )["id"]
    data = w.detail(db, user, rid)
    assert len(data["samples"]) == 1 and len(data["tasks"]) == 1
    assert not data["samples"][0]["can_receive"] and data["tasks"][0]["allowed_actions"] == []
    with pytest.raises(AppError):
        w.detail(db, users["admin"], rid)


@pytest.mark.parametrize("count,pages", [(1, 1), (8, 1), (9, 2)])
def test_label_geometry_pages_content(db, users, count, pages):
    data = w.detail(db, users["jefe"], RID)
    sample = next(s for s in data["samples"] if s["client_code"] == "M-01")
    data["samples"] = [
        {**sample, "codigo_laboratorio": f"LAB-{i:03}", "depth_from": 12.45, "depth_to": 13.0}
        for i in range(count)
    ]
    doc = PdfReader(BytesIO(render_labels(data)))
    assert len(doc.pages) == pages
    text = "".join(p.extract_text() for p in doc.pages)
    assert text.count("LARA CONSULTING") == count and text.count("MUESTRA DE LABORATORIO") == count
    assert "12.45" in text and "13.00 m" in text and "UR origen" not in text and "OT:" not in text
    assert abs(float(doc.pages[0].mediabox.width) - 210 * mm) < 0.1
    # PDF rectangle operators retain exact physical label size.
    from pypdf.generic import ContentStream

    rects = [
        operands for operands, op in ContentStream(doc.pages[0].get_contents(), doc).operations if op == b"re"
    ]
    assert len(rects) == min(count, 8)
    assert all(abs(float(v[2]) - 95 * mm) < 0.1 and abs(float(v[3]) - 68 * mm) < 0.1 for v in rects)
