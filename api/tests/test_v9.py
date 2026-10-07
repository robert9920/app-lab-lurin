import json
from uuid import uuid4

import pytest

from database import execute, one, rows
from services.common import audit
from test_workflow import RID, identity, invoke


def request_call(user, db, name="requests", method="GET", payload=None, **kwargs):
    response = invoke(name, method, payload, headers=identity(db, user), **kwargs)
    return response, json.loads(response.get_body())


def test_partial_draft_roundtrip_privacy_filter_and_cancel(db, users):
    response, draft = request_call(
        users["cliente"], db, method="POST", payload={"notes": "Primera línea\nSegunda"}
    )
    assert response.status_code == 200, draft
    rid = draft["id"]
    assert draft["status"] == "DRAFT" and draft["project_id"] is None
    assert draft["samples"] == [] and not draft["can_cancel"]
    _, listed = request_call(users["cliente"], db, params={"request_status": "DRAFT"})
    assert rid in [r["id"] for r in listed["items"]]
    _, created = request_call(users["cliente"], db, params={"request_status": "CREATED"})
    assert rid not in [r["id"] for r in created["items"]]
    _, mixed = request_call(users["cliente"], db, params={"request_status": "DRAFT,CREATED"})
    assert rid in [r["id"] for r in mixed["items"]]
    for name in ("admin", "jefe", "tecnico", "externo"):
        denied, _ = request_call(users[name], db, "request_detail", route={"rid": rid})
        assert denied.status_code == 404
        _, listed = request_call(users[name], db, params={"request_status": "DRAFT"})
        assert rid not in [r["id"] for r in listed["items"]]
    cancel, _ = request_call(
        users["cliente"],
        db,
        "actions",
        "POST",
        {"version": draft["version"], "action": "cancel", "reason": "Prueba"},
        route={"rid": rid},
    )
    assert cancel.status_code == 409
    assert one(db, "SELECT version FROM solicitudes WHERE id=:id", id=rid)["version"] == draft["version"]


def test_draft_partial_rows_complete_before_send_and_no_relaxation_after(db, users):
    response, draft = request_call(
        users["cliente"],
        db,
        method="POST",
        payload={"samples": [{"notes": "Primera muestra sin código"}, {"borehole": "DH-02"}, {}]},
    )
    assert response.status_code == 200, draft
    rid = draft["id"]
    assert len(draft["samples"]) == 2
    assert all(s["client_code"] is None and s["material"] is None for s in draft["samples"])
    denied, _ = request_call(
        users["cliente"],
        db,
        "actions",
        "POST",
        {"version": draft["version"], "action": "submit"},
        route={"rid": rid},
    )
    assert denied.status_code == 400
    data = {
        "version": draft["version"],
        "project_id": "DEMO-001",
        "district": "Lurín",
        "province": "Lima",
        "department": "Lima",
        "samples": [
            {"id": s["id"], "client_code": f"M-{i}", "material": "Suelo", "notes": s["notes"]}
            for i, s in enumerate(draft["samples"])
        ],
    }
    response, complete = request_call(users["cliente"], db, "request_detail", "PUT", data, route={"rid": rid})
    assert response.status_code == 200, complete
    stale, _ = request_call(users["cliente"], db, "request_detail", "PUT", data, route={"rid": rid})
    assert stale.status_code == 409
    response, sent = request_call(
        users["cliente"],
        db,
        "actions",
        "POST",
        {"version": complete["version"], "action": "submit"},
        route={"rid": rid},
    )
    assert response.status_code == 200 and sent["status"] == "WAITING_ASSAYS"
    assert sent["can_cancel"]
    partial, _ = request_call(
        users["cliente"],
        db,
        "request_detail",
        "PUT",
        {"version": sent["version"], "notes": "No permitir incompleto"},
        route={"rid": rid},
    )
    assert partial.status_code == 400


def test_draft_without_samples_and_internal_project_cannot_be_sent(db, users):
    _, draft = request_call(
        users["cliente"],
        db,
        method="POST",
        payload={"district": "Lurín", "province": "Lima", "department": "Lima"},
    )
    response, _ = request_call(
        users["cliente"],
        db,
        "actions",
        "POST",
        {"version": draft["version"], "action": "submit"},
        route={"rid": draft["id"]},
    )
    assert response.status_code == 400
    response, edited = request_call(
        users["cliente"],
        db,
        "request_detail",
        "PUT",
        {
            "version": draft["version"],
            "district": "Lurín",
            "province": "Lima",
            "department": "Lima",
            "samples": [{"client_code": "M", "material": "Suelo"}],
        },
        route={"rid": draft["id"]},
    )
    assert response.status_code == 200, edited
    response, body = request_call(
        users["cliente"],
        db,
        "actions",
        "POST",
        {"version": edited["version"], "action": "submit"},
        route={"rid": draft["id"]},
    )
    assert response.status_code == 400 and "Proyecto" in body["error"]
    _, external = request_call(users["externo"], db, method="POST", payload={})
    assert external["project_id"] == "EXTERNO" and external["samples"] == []


@pytest.mark.parametrize(
    "sample",
    [
        {"easting": "12345"},
        {"northing": "123456"},
        {"quantity": 1.5},
        {"weight": "1.11"},
        {"weight": "NaN"},
        {"depth_from": "5", "depth_to": "4"},
    ],
)
def test_partial_draft_does_not_relax_supplied_values(db, users, sample):
    response, _ = request_call(users["cliente"], db, method="POST", payload={"samples": [sample]})
    assert response.status_code == 400


def test_partial_draft_repeated_provided_codes_are_atomic(db, users):
    before = one(db, "SELECT count(*) n FROM solicitudes")["n"]
    response, _ = request_call(
        users["cliente"],
        db,
        method="POST",
        payload={"samples": [{"client_code": "M"}, {"client_code": " M "}]},
    )
    assert response.status_code == 400
    assert one(db, "SELECT count(*) n FROM solicitudes")["n"] == before


def test_operational_reasons_visible_now_and_in_legacy_history_scoped(db, users):
    tasks = rows(
        db,
        "SELECT a.id FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.solicitud_id=:r ORDER BY a.id LIMIT 2",
        r=RID,
    )
    other = one(
        db,
        "INSERT INTO usuarios(nombre,correo,roles,hash_contrasena) VALUES('Otro técnico',:email,ARRAY['TECH'],'!NOT_INITIALIZED') RETURNING *",
        email=str(uuid4()) + "@example.com",
    )
    for index, task in enumerate(tasks):
        owner = users["tecnico"] if index == 0 else other
        state, action = ("OBSERVED", "observe") if index == 0 else ("CANCELLED", "cancel")
        execute(
            db,
            "UPDATE ensayos_muestra SET tecnico_id=:u,estado_revision='APPROVED',estado_ensayo=:s,iniciado_en=now(),completado_en=NULL WHERE id=:id",
            u=owner["id"],
            s=state,
            id=task["id"],
        )
        audit(
            db,
            users["jefe"],
            "Ensayo actualizado",
            RID,
            {
                "task_id": task["id"],
                "action": action,
                "from": "RUNNING",
                "to": state,
                "reason": f"Motivo público {index}\nSegunda línea",
                "private": "No exponer",
            },
            internal=True,
        )
    audit(db, users["jefe"], "Nota interna reservada", RID, {"private": "No exponer"}, internal=True)
    _, client = request_call(users["cliente"], db, "request_detail", route={"rid": RID})
    for task in tasks:
        view = next(t for t in client["tasks"] if t["id"] == str(task["id"]))
        assert view["state_reason"].startswith("Motivo público")
        assert view["state_reason_author"] == users["jefe"]["name"] and view["state_reason_at"]
        assert not view["notes"]
    assert "Nota interna reservada" not in json.dumps(client, ensure_ascii=False)
    assert "No exponer" not in json.dumps(client, ensure_ascii=False)
    public = [a for a in client["activity"] if any("Motivo público" in s for s in a["description_lines"])]
    assert len(public) == 2 and all(not a["internal"] for a in public)
    assert all("detail" not in a for a in client["activity"])
    assert (
        one(
            db,
            "SELECT count(*) n FROM actividad WHERE solicitud_id=:r AND interno AND detalle->>'action' IN ('observe','cancel')",
            r=RID,
        )["n"]
        == 2
    )
    _, tech = request_call(users["tecnico"], db, "request_detail", route={"rid": RID})
    assert "Motivo público 1" not in json.dumps(tech, ensure_ascii=False)
    _, work = request_call(users["tecnico"], db, "work", params={"request": RID})
    assert any(t["state_reason"].startswith("Motivo público 0") for t in work["items"])
    assert "Motivo público 1" not in json.dumps(work, ensure_ascii=False)


@pytest.mark.parametrize("action,state", [("observe", "OBSERVED"), ("cancel", "CANCELLED")])
def test_new_operational_motive_is_public_and_reason_required(db, users, action, state):
    task = one(
        db,
        "SELECT a.id FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.solicitud_id=:r LIMIT 1",
        r=RID,
    )
    execute(
        db,
        "UPDATE ensayos_muestra SET tecnico_id=:u,estado_revision='APPROVED',estado_ensayo='RUNNING',iniciado_en=now(),completado_en=NULL WHERE id=:id",
        u=users["tecnico"]["id"],
        id=task["id"],
    )
    version = one(db, "SELECT version FROM solicitudes WHERE id=:r", r=RID)["version"]
    denied, _ = request_call(
        users["jefe"],
        db,
        "tasks",
        "POST",
        {"version": version, "task_ids": [str(task["id"])], "action": action},
        route={"rid": RID},
    )
    assert denied.status_code == 400
    response, data = request_call(
        users["jefe"],
        db,
        "tasks",
        "POST",
        {"version": version, "task_ids": [str(task["id"])], "action": action, "reason": "Comentario visible"},
        route={"rid": RID},
    )
    assert response.status_code == 200, data
    _, client = request_call(users["cliente"], db, "request_detail", route={"rid": RID})
    current = next(t for t in client["tasks"] if t["id"] == str(task["id"]))
    assert current["state"] == state and current["state_reason"] == "Comentario visible"
    assert any("Motivo: Comentario visible" in a["description_lines"] for a in client["activity"])
