import json
from datetime import datetime, timezone

import pytest

from database import execute
from errors import AppError
from services import workflow as w
from test_workflow import FUNCTIONS, RID, identity, invoke
from validation import Action, Reception


def test_admin_without_operational_roles_cannot_modify_requests(db, users):
    execute(db, "UPDATE usuarios SET roles=ARRAY['ADMIN'] WHERE id=:id", id=users["admin"]["id"])
    headers = identity(db, users["admin"])
    response = invoke(
        "comments", "POST", {"version": 1, "body": "No autorizado"}, route={"rid": RID}, headers=headers
    )
    assert response.status_code == 403
    assert invoke("dashboard", headers=headers).status_code == 200


def test_removed_authentication_and_document_routes():
    assert not set(FUNCTIONS).intersection(
        {"invite_again", "activate", "forgot", "mfa_verify", "publish", "arrivals", "release"}
    )


def test_cancelled_excluded_and_completed_weekly(db, users):
    execute(
        db,
        "UPDATE ensayos_muestra SET estado_ensayo='CANCELLED',observaciones='Cancelación de prueba'\n        WHERE muestra_id='50000000-0000-0000-0000-000000000002'",
    )
    response = invoke("dashboard", headers=identity(db, users["jefe"]))
    assert response.status_code == 200
    data = json.loads(response.get_body())
    assert data["totals"]["open"] == 3
    assert data["totals"]["unassigned"] == 0
    assert sum(row["count"] for row in data["weekly"]) == 8
    filtered = invoke(
        "work",
        headers=identity(db, users["jefe"]),
        params={"request_q": "SOL-DEMO-001", "state": "CANCELLED"},
    )
    assert json.loads(filtered.get_body())["total"] == 2


def test_mismatched_sample_and_stale_request_rejected(db, users):
    with pytest.raises(AppError):
        w.reception(
            db,
            users["tecnico"],
            RID,
            Reception(
                version=1,
                received_at=datetime.now(timezone.utc),
                samples=[
                    {
                        "sample_id": "50000000-0000-0000-0000-000000000004",
                        "codigo_recepcion": "REC-TEST",
                        "codigo_laboratorio": "LAB-TEST-004",
                    }
                ],
            ),
        )
    with pytest.raises(AppError) as error:
        w.action(db, users["jefe"], RID, Action(version=999, action="close"))
    assert error.value.status == 409
