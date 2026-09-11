import json
import secrets
from uuid import uuid4

from database import one, rows
from test_workflow import identity, invoke

ORG = "10000000-0000-0000-0000-000000000001"
PROJECT = "30000000-0000-0000-0000-000000000001"


def test_project_memberships_are_atomic_and_scoped(db, users):
    admin = identity(db, users["admin"])
    before = one(db, "SELECT count(*) n FROM miembros_proyecto")["n"]
    response = invoke(
        "admin_projects",
        "POST",
        {"name": "Nuevo estudio", "code": "NEW-" + str(uuid4()), "location": "Lurín", "organization_id": ORG},
        headers=admin,
    )
    assert response.status_code == 200, response.get_body()
    pid = json.loads(response.get_body())["id"]
    expected = {str(u["id"]) for u in rows(db, "SELECT id FROM usuarios WHERE empresa_id=:o", o=ORG)}
    actual = {
        str(u["user_id"])
        for u in rows(db, "SELECT usuario_id FROM miembros_proyecto WHERE proyecto_id=:p", p=pid)
    }
    assert actual == expected
    assert one(db, "SELECT count(*) n FROM miembros_proyecto WHERE proyecto_id<>:p", p=pid)["n"] == before
    # Same code must fail without partial assignments.
    payload = json.loads(response.get_body())
    duplicate = invoke(
        "admin_projects",
        "POST",
        {"name": "Duplicado", "code": payload["code"], "location": "Lima", "organization_id": ORG},
        headers=admin,
    )
    assert duplicate.status_code == 409
    assert one(db, "SELECT count(*) n FROM miembros_proyecto")["n"] == before + len(expected)


def test_manual_user_session_is_persisted_and_logout_removes_it(db, users):
    admin = identity(db, users["admin"])
    password = secrets.token_urlsafe(24)
    email = str(uuid4()) + "@example.com"
    response = invoke(
        "admin_users",
        "POST",
        {
            "email": email,
            "name": "Cuenta manual",
            "password": password,
            "roles": ["CLIENT"],
            "organization_id": ORG,
            "project_ids": [],
        },
        headers=admin,
    )
    assert response.status_code == 200
    uid = json.loads(response.get_body())["id"]
    assert one(db, "SELECT count(*) n FROM miembros_proyecto WHERE usuario_id=:u", u=uid)["n"] == 0
    response = invoke("login", "POST", {"email": email, "password": password})
    assert response.status_code == 200
    headers = {
        "cookie": response.headers["Set-Cookie"].split(";")[0],
        "x-csrf-token": json.loads(response.get_body())["csrf"],
    }
    assert one(db, "SELECT count(*) n FROM sesiones WHERE usuario_id=:u", u=uid)["n"] == 1
    assert invoke("current_session", headers=headers).status_code == 200
    assert invoke("logout", "POST", {}, headers=headers).status_code == 200
    assert one(db, "SELECT count(*) n FROM sesiones WHERE usuario_id=:u", u=uid)["n"] == 0
    assert invoke("current_session", headers=headers).status_code == 401


def test_assignment_foreign_company_and_field_errors(db, users):
    admin = identity(db, users["admin"])
    response = invoke(
        "admin_users",
        "POST",
        {
            "email": str(uuid4()) + "@example.com",
            "name": "Ajeno",
            "password": secrets.token_urlsafe(24),
            "roles": ["CLIENT"],
            "organization_id": "10000000-0000-0000-0000-000000000002",
            "project_ids": [PROJECT],
        },
        headers=admin,
    )
    assert response.status_code == 400
    bad = invoke(
        "admin_projects",
        "POST",
        {"name": "x", "organization_id": ORG, "code": "P1", "location": "Lima"},
        headers=admin,
    )
    assert bad.status_code == 400
    assert "Nombre" in json.loads(bad.get_body())["error"]
    extra = invoke(
        "admin_projects",
        "POST",
        {"name": "Prueba", "organization_id": ORG, "code": "P1", "location": "Lima", "project_ids": []},
        headers=admin,
    )
    assert extra.status_code == 400
    assert b"extra_forbidden" not in extra.get_body()
