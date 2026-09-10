import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from http.cookies import SimpleCookie

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from config import settings
from database import engine, execute, one
from errors import AppError

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
DUMMY = hasher.hash(secrets.token_urlsafe(24))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_for(token):
    return hmac.new(token.encode(), b"lab-lc-csrf-v3", hashlib.sha256).hexdigest()


def token_from(req):
    cookie = SimpleCookie()
    try:
        cookie.load(req.headers.get("cookie", ""))
        return cookie[settings()["cookie"]].value
    except (KeyError, ValueError):
        raise AppError(401, "Inicia sesión para continuar.") from None


def origin_check(req):
    if req.headers.get("origin") != settings()["origin"]:
        raise AppError(403, "Origen no permitido.")


def public_user(user):
    return {key: user[key] for key in ("id", "name", "email", "roles", "organization_id")}


def require_role(user, *roles):
    if not set(user["roles"]).intersection(roles):
        raise AppError(403, "No tienes permiso para esta operación.")


def is_staff(user):
    return bool(set(user["roles"]).intersection({"ADMIN", "MANAGER", "TECH"}))


def global_reader(user):
    return bool(set(user["roles"]).intersection({"ADMIN", "MANAGER"}))


def technical_only(user):
    return "TECH" in user["roles"] and not global_reader(user)


# Request alias r; scope parameters are always supplied by the authenticated server.
REQUEST_SCOPE = "(r.estado_solicitud<>'DRAFT' OR r.creado_por=:u) AND\n(:global OR (:client AND r.proyecto_id IN(SELECT proyecto_id FROM miembros_proyecto WHERE usuario_id=:u))\n OR (:tech AND EXISTS(SELECT 1 FROM muestras sx JOIN ensayos_muestra ax ON ax.muestra_id=sx.id\n WHERE sx.solicitud_id=r.id AND ax.tecnico_id=:u)))"
SAMPLE_SCOPE = (
    "(:all_samples OR EXISTS(SELECT 1 FROM ensayos_muestra ax WHERE ax.muestra_id=s.id AND ax.tecnico_id=:u))"
)


def scope_params(user):
    return {
        "u": user["id"],
        "global": global_reader(user),
        "client": "CLIENT" in user["roles"],
        "tech": "TECH" in user["roles"],
        "all_samples": not technical_only(user),
    }


def client_project(db, user, project_id):
    return "CLIENT" in user["roles"] and bool(
        one(
            db,
            "SELECT 1 FROM miembros_proyecto WHERE usuario_id=:u AND proyecto_id=:p",
            u=user["id"],
            p=project_id,
        )
    )


def laboratory_access(db, user, rid, version=None):
    require_role(user, "MANAGER", "TECH")
    request = request_access(db, user, rid, version)
    if "MANAGER" not in user["roles"] and not one(
        db,
        "SELECT 1 FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.solicitud_id=:r AND a.tecnico_id=:u",
        r=rid,
        u=user["id"],
    ):
        raise AppError(404, "Solicitud no encontrada.")
    return request


def session(db, req):
    token = token_from(req)
    user = one(
        db,
        "SELECT u.*,s.vence_en,s.ultimo_acceso FROM sesiones s JOIN usuarios u ON u.id=s.usuario_id\n        WHERE s.hash_token=:hash AND u.activo FOR SHARE OF u",
        hash=digest(token),
    )
    now = datetime.now(timezone.utc)
    if (
        not user
        or user["expires_at"] <= now
        or (now - user["last_seen"]).total_seconds() > settings()["idle_minutes"] * 60
    ):
        raise AppError(401, "La sesión ha caducado.")
    if req.method not in ("GET", "HEAD"):
        origin_check(req)
        if not hmac.compare_digest(req.headers.get("x-csrf-token", ""), csrf_for(token)):
            raise AppError(403, "Protección CSRF: recarga la página.")
    execute(db, "UPDATE sesiones SET ultimo_acceso=now() WHERE hash_token=:hash", hash=digest(token))
    return user


def project_access(db, user, pid):
    project = one(db, "SELECT * FROM proyectos WHERE id=:id", id=pid)
    if not project or (
        not is_staff(user)
        and not one(
            db, "SELECT 1 FROM miembros_proyecto WHERE usuario_id=:u AND proyecto_id=:p", u=user["id"], p=pid
        )
    ):
        raise AppError(404, "Proyecto no encontrado.")
    return project


def request_access(db, user, rid, version=None, allow_closed=False):
    request = one(
        db, "SELECT * FROM solicitudes WHERE id=:id" + (" FOR UPDATE" if version is not None else ""), id=rid
    )
    if not request:
        raise AppError(404, "Solicitud no encontrada.")
    if version is not None:
        require_role(user, "CLIENT", "MANAGER", "TECH")
    access_user = (
        {**user, "roles": [r for r in user["roles"] if r != "ADMIN"]} if version is not None else user
    )
    if not one(
        db,
        "SELECT 1 FROM solicitudes r WHERE r.id=:id AND " + REQUEST_SCOPE,
        id=rid,
        **scope_params(access_user),
    ):
        raise AppError(404, "Solicitud no encontrada.")
    if version is not None:
        if request["version"] != version:
            raise AppError(409, "La solicitud cambió. Recarga antes de guardar.")
        if request["status"] == "CLOSED" and not allow_closed:
            raise AppError(409, "La solicitud está cerrada.")
    return request


def rate_limit(key, maximum=10, minutes=15):
    # Transacción separada: un intento fallido también consume el límite.
    with engine().begin() as conn:
        hit = one(
            conn,
            "INSERT INTO limites_intentos(clave_limite) VALUES(:key)\n            ON CONFLICT(clave_limite) DO UPDATE SET\n            numero_intentos=CASE WHEN limites_intentos.inicio_ventana<now()-make_interval(mins=>:mins) THEN 1 ELSE limites_intentos.numero_intentos+1 END,\n            inicio_ventana=CASE WHEN limites_intentos.inicio_ventana<now()-make_interval(mins=>:mins) THEN now() ELSE limites_intentos.inicio_ventana END\n            RETURNING numero_intentos",
            key=digest(key),
            mins=minutes,
        )
    if hit["count"] > maximum:
        raise AppError(429, "Demasiados intentos. Espera unos minutos.")


def verify_password(encoded, password):
    try:
        return hasher.verify(encoded if encoded.startswith("$argon2") else DUMMY, password)
    except (VerificationError, InvalidHashError):
        return False


def cookie_header(token, clear=False):
    value = f"{settings()['cookie']}={token}; Path=/; HttpOnly; SameSite=Lax"
    value += "; Max-Age=0" if clear else f"; Max-Age={settings()['session_hours'] * 3600}"
    return value + ("; Secure" if settings()["production"] else "")


def new_session(db, user):
    token = secrets.token_urlsafe(32)
    execute(
        db,
        "INSERT INTO sesiones(hash_token,usuario_id,vence_en)\n        VALUES(:hash,:uid,now()+make_interval(hours=>:hours))",
        hash=digest(token),
        uid=user["id"],
        hours=settings()["session_hours"],
    )
    return {"user": public_user(user), "csrf": csrf_for(token)}, cookie_header(token)


def maintenance(db):
    execute(
        db,
        "DELETE FROM sesiones WHERE hash_token IN\n        (SELECT hash_token FROM sesiones WHERE vence_en<now() OR ultimo_acceso<now()-make_interval(mins=>:mins) LIMIT 100)",
        mins=settings()["idle_minutes"],
    )
    execute(
        db,
        "DELETE FROM limites_intentos WHERE clave_limite IN\n        (SELECT clave_limite FROM limites_intentos WHERE inicio_ventana<now()-interval '1 day' LIMIT 100)",
    )
