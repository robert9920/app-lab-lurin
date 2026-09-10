import json
import secrets
from uuid import uuid4

import pytest

from database import execute, one
from errors import AppError
from security import hasher, rate_limit
from test_workflow import RID, identity, invoke


def test_admin_creation_login_reset_disable_and_csrf(db, users):
    admin = identity(db, users["admin"])
    password = secrets.token_urlsafe(24)
    response = invoke(
        "admin_users",
        "POST",
        {
            "email": str(uuid4()) + "@example.com",
            "name": "Cliente de prueba",
            "password": password,
            "roles": ["CLIENT"],
            "organization_id": "10000000-0000-0000-0000-000000000001",
            "project_ids": ["30000000-0000-0000-0000-000000000001"],
        },
        headers=admin,
    )
    assert response.status_code == 200, response.get_body()
    uid = json.loads(response.get_body())["id"]
    user = one(db, "SELECT * FROM usuarios WHERE id=:id", id=uid)
    assert user["password_hash"].startswith("$argon2id$")
    response = invoke("login", "POST", {"email": user["email"], "password": password})
    assert response.status_code == 200, response.get_body()
    session_data = json.loads(response.get_body())
    assert "mfa_required" not in session_data
    cookie = response.headers["Set-Cookie"].split(";")[0]
    headers = {"cookie": cookie, "x-csrf-token": session_data["csrf"]}
    assert invoke("current_session", headers=headers).status_code == 200
    assert invoke("logout", "POST", {}, headers={"cookie": cookie}).status_code == 403
    reset = invoke(
        "reset_password", "POST", {"password": secrets.token_urlsafe(24)}, route={"id": uid}, headers=admin
    )
    assert reset.status_code == 200
    assert invoke("current_session", headers=headers).status_code == 401
    headers = identity(db, user)
    assert (
        invoke(
            "edit_user",
            "PUT",
            {"roles": ["CLIENT"], "active": False, "project_ids": []},
            route={"id": uid},
            headers=admin,
        ).status_code
        == 200
    )
    assert invoke("current_session", headers=headers).status_code == 401
    listed = invoke("admin_data", headers=admin).get_body()
    assert b"password_hash" not in listed and password.encode() not in listed


def test_session_expiration_origin_and_project_scope(db, users):
    headers = identity(db, users["cliente"])
    assert invoke("request_detail", route={"rid": RID}, headers=headers).status_code == 200
    assert (
        invoke(
            "request_detail", route={"rid": "40000000-0000-0000-0000-000000000003"}, headers=headers
        ).status_code
        == 404
    )
    assert (
        invoke("logout", "POST", {}, headers={**headers, "origin": "https://malicious.invalid"}).status_code
        == 403
    )
    execute(
        db,
        "UPDATE sesiones SET ultimo_acceso=now()-interval '31 minutes' WHERE usuario_id=:id",
        id=users["cliente"]["id"],
    )
    assert invoke("current_session", headers=headers).status_code == 401
    headers = identity(db, users["cliente"])
    execute(
        db,
        "UPDATE sesiones SET vence_en=now()-interval '1 second' WHERE usuario_id=:id",
        id=users["cliente"]["id"],
    )
    assert invoke("current_session", headers=headers).status_code == 401


def test_rate_limits_survive_failures():
    key = "test:" + str(uuid4())
    for _ in range(3):
        rate_limit(key, maximum=3)
    with pytest.raises(AppError) as err:
        rate_limit(key, maximum=3)
    assert err.value.status == 429


def test_internal_activity_hidden(db, users):
    from services.common import audit

    audit(db, users["jefe"], "Nota interna confidencial", RID, {"private": True})
    data = json.loads(
        invoke("request_detail", route={"rid": RID}, headers=identity(db, users["cliente"])).get_body()
    )
    assert all(not a["internal"] for a in data["activity"])


def test_password_whitespace_is_preserved():
    from validation import UserCreate

    raw = "  " + secrets.token_urlsafe(20) + "  "
    data = UserCreate(email="test@example.com", name="Test", roles=["ADMIN"], password=raw)
    assert data.password == raw
    assert hasher.verify(hasher.hash(raw), data.password)
