import json
import secrets
from uuid import uuid4

from database import one
from test_workflow import identity, invoke

ORG = "10000000-0000-0000-0000-000000000001"


def test_manual_user_session_is_persisted_and_logout_removes_it(db, users):
    admin = identity(db, users["admin"])
    password = secrets.token_urlsafe(24)
    email = str(uuid4()) + "@example.com"
    r = invoke(
        "admin_users",
        "POST",
        {
            "email": email,
            "name": "Cuenta manual",
            "phone": "+51 999 123 456",
            "password": password,
            "roles": ["CLIENT"],
            "organization_id": ORG,
        },
        headers=admin,
    )
    assert r.status_code == 200, r.get_body()
    uid = json.loads(r.get_body())["id"]
    r = invoke("login", "POST", {"email": email, "password": password})
    assert r.status_code == 200
    headers = {
        "cookie": r.headers["Set-Cookie"].split(";")[0],
        "x-csrf-token": json.loads(r.get_body())["csrf"],
    }
    assert one(db, "SELECT count(*) n FROM sesiones WHERE usuario_id=:u", u=uid)["n"] == 1
    assert invoke("current_session", headers=headers).status_code == 200
    assert invoke("logout", "POST", {}, headers=headers).status_code == 200
    assert one(db, "SELECT count(*) n FROM sesiones WHERE usuario_id=:u", u=uid)["n"] == 0
    assert invoke("current_session", headers=headers).status_code == 401


def test_user_edit_and_company_classification(db, users):
    admin = identity(db, users["admin"])
    u = users["cliente"]
    headers = identity(db, u)
    r = invoke(
        "edit_user",
        "PUT",
        {
            "name": "Nombre actualizado",
            "email": "nuevo-" + str(uuid4()) + "@example.com",
            "phone": "987654321",
            "organization_id": ORG,
            "roles": ["CLIENT"],
            "active": True,
        },
        route={"id": str(u["id"])},
        headers=admin,
    )
    assert r.status_code == 200, r.get_body()
    assert (
        one(db, "SELECT nombre,num_telefono FROM usuarios WHERE id=:id", id=u["id"])["phone"] == "987654321"
    )
    assert invoke("current_session", headers=headers).status_code == 401
    other = "10000000-0000-0000-0000-000000000002"
    r = invoke(
        "edit_organization",
        "PUT",
        {"name": "Externa ahora interna", "tax_id": "DEMO-X", "active": True, "is_internal": True},
        route={"id": other},
        headers=admin,
    )
    assert r.status_code == 200, r.get_body()
    assert one(db, "SELECT count(*) n FROM empresas WHERE es_interna")["n"] == 1
    assert not one(db, "SELECT es_interna FROM empresas WHERE id=:id", id=ORG)["is_internal"]


def test_removed_memberships_and_strict_admin_fields(db, users):
    admin = identity(db, users["admin"])
    r = invoke(
        "admin_users",
        "POST",
        {
            "email": str(uuid4()) + "@example.com",
            "name": "Nuevo",
            "password": secrets.token_urlsafe(24),
            "roles": ["CLIENT"],
            "organization_id": ORG,
            "project_ids": [],
        },
        headers=admin,
    )
    assert r.status_code == 400 and b"extra_forbidden" not in r.get_body()
    r = invoke(
        "admin_users",
        "POST",
        {
            "email": "invalid",
            "name": "Nuevo",
            "password": secrets.token_urlsafe(24),
            "roles": ["CLIENT"],
            "organization_id": ORG,
        },
        headers=admin,
    )
    assert r.status_code == 400 and "Correo" in json.loads(r.get_body())["error"]
    assert "projects" not in json.loads(invoke("admin_data", headers=admin).get_body())
