import azure.functions as func

from database import execute, one
from errors import AppError
from http_helpers import body, endpoint, json_response
from security import (
    DUMMY,
    cookie_header,
    csrf_for,
    digest,
    maintenance,
    new_session,
    origin_check,
    public_user,
    rate_limit,
    session,
    token_from,
    verify_password,
)
from services.common import audit
from validation import Login

bp = func.Blueprint()


@bp.route(route="auth/login", methods=["POST"])
@endpoint
def login(db, req):
    origin_check(req)
    data = body(req, Login)
    rate_limit("login:" + str(data.email).lower())
    user = one(db, "SELECT * FROM usuarios WHERE correo=:email FOR UPDATE", email=str(data.email).lower())
    valid = verify_password(user["password_hash"] if user else DUMMY, data.password)
    if not user or not valid or not user["active"]:
        raise AppError(401, "Correo o contraseña incorrectos.")
    payload, cookie = new_session(db, user)
    maintenance(db)
    audit(db, user, "Inicio de sesión")
    return json_response(payload, headers={"Set-Cookie": cookie})


@bp.route(route="session", methods=["GET"])
@endpoint
def current_session(db, req):
    user = session(db, req)
    return {"user": public_user(user), "csrf": csrf_for(token_from(req))}


@bp.route(route="auth/logout", methods=["POST"])
@endpoint
def logout(db, req):
    user = session(db, req)
    execute(db, "DELETE FROM sesiones WHERE hash_token=:hash", hash=digest(token_from(req)))
    audit(db, user, "Cierre de sesión")
    return json_response({"ok": True}, headers={"Set-Cookie": cookie_header("", clear=True)})
