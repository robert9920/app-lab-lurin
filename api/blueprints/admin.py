import azure.functions as func

from database import execute, one, rows
from errors import AppError
from http_helpers import body, endpoint, uid
from security import hasher, require_role, session
from services.common import audit
from validation import Catalog, Organization, OrganizationEdit, Password, UserCreate, UserEdit

bp = func.Blueprint()


def admin(db, req):
    u = session(db, req)
    require_role(u, "ADMIN")
    return u


def administrative_lock(db):
    execute(db, "SELECT pg_advisory_xact_lock(481701)")


def valid_company(db, organization, roles):
    if "CLIENT" in roles and not organization:
        raise AppError(400, "Asigna una empresa al cliente.")
    if organization and not one(db, "SELECT 1 FROM empresas WHERE id=:id AND activo", id=organization):
        raise AppError(400, "Empresa: selecciona una empresa habilitada.")


@bp.route(route="management/data", methods=["GET"])
@endpoint
def admin_data(db, req):
    admin(db, req)
    return {
        "organizations": rows(db, "SELECT * FROM empresas ORDER BY nombre"),
        "users": rows(
            db,
            "SELECT u.id,u.nombre,u.correo,u.num_telefono,u.roles,u.activo,u.empresa_id\n                FROM usuarios u ORDER BY u.nombre",
        ),
        "catalog": rows(db, "SELECT * FROM catalogo_ensayos ORDER BY codigo"),
    }


def set_internal(db, oid, p):
    if p.is_internal and not p.active:
        raise AppError(400, "La empresa interna debe estar habilitada.")
    if p.is_internal:
        execute(db, "UPDATE empresas SET es_interna=false WHERE es_interna AND id<>:id", id=oid)
    execute(db, "UPDATE empresas SET es_interna=:internal WHERE id=:id", internal=p.is_internal, id=oid)


@bp.route(route="management/organizations", methods=["POST"])
@endpoint
def admin_organizations(db, req):
    u, p = admin(db, req), body(req, Organization)
    administrative_lock(db)
    r = one(
        db,
        "INSERT INTO empresas(nombre,identificacion_tributaria,activo) VALUES(:n,:t,:a) RETURNING *",
        n=p.name,
        t=p.tax_id or None,
        a=p.active,
    )
    set_internal(db, r["id"], p)
    audit(db, u, "Empresa creada", detail={"id": r["id"], "is_internal": p.is_internal})
    return one(db, "SELECT * FROM empresas WHERE id=:id", id=r["id"])


@bp.route(route="management/organizations/{id}", methods=["PUT"])
@endpoint
def edit_organization(db, req):
    u, p = admin(db, req), body(req, OrganizationEdit)
    administrative_lock(db)
    oid = uid(req.route_params["id"])
    old = one(db, "SELECT * FROM empresas WHERE id=:id FOR UPDATE", id=oid)
    if not old:
        raise AppError(404, "Empresa no encontrada.")
    set_internal(db, oid, p)
    execute(
        db,
        "UPDATE empresas SET nombre=:n,identificacion_tributaria=:t,activo=:a WHERE id=:id",
        n=p.name,
        t=p.tax_id or None,
        a=p.active,
        id=oid,
    )
    audit(db, u, "Empresa actualizada", detail={"id": oid, "before": old, "after": p.model_dump()})
    return one(db, "SELECT * FROM empresas WHERE id=:id", id=oid)


@bp.route(route="management/users", methods=["POST"])
@endpoint
def admin_users(db, req):
    u, p = admin(db, req), body(req, UserCreate)
    administrative_lock(db)
    valid_company(db, p.organization_id, p.roles)
    r = one(
        db,
        "INSERT INTO usuarios(nombre,correo,num_telefono,empresa_id,roles,hash_contrasena) VALUES(:n,:e,:phone,:o,:roles,:hash) RETURNING id",
        n=p.name,
        e=str(p.email).lower(),
        phone=p.phone or None,
        o=p.organization_id,
        roles=p.roles,
        hash=hasher.hash(p.password),
    )
    audit(db, u, "USER_CREATED", detail={"id": r["id"], "roles": p.roles})
    return r


@bp.route(route="management/users/{id}", methods=["PUT"])
@endpoint
def edit_user(db, req):
    u, p = admin(db, req), body(req, UserEdit)
    # Serialize administrative account changes, including concurrent last-admin demotions.
    execute(db, "SELECT pg_advisory_xact_lock(481701)")
    target = one(db, "SELECT * FROM usuarios WHERE id=:u FOR UPDATE", u=uid(req.route_params["id"]))
    if not target:
        raise AppError(404, "Usuario no encontrado.")
    if "ADMIN" in target["roles"] and target["active"] and (not p.active or "ADMIN" not in p.roles):
        if one(db, "SELECT count(*) n FROM usuarios WHERE activo AND 'ADMIN'=ANY(roles)")["n"] <= 1:
            raise AppError(409, "Debe existir al menos un administrador activo.")
    organization = p.organization_id if "organization_id" in p.model_fields_set else target["organization_id"]
    valid_company(db, organization, p.roles)
    execute(
        db,
        "UPDATE usuarios SET nombre=:name,correo=:email,num_telefono=:phone,roles=:r,activo=:a,empresa_id=:o WHERE id=:u",
        name=p.name,
        email=str(p.email).lower(),
        phone=p.phone or None,
        r=p.roles,
        a=p.active,
        o=organization,
        u=target["id"],
    )
    execute(db, "DELETE FROM sesiones WHERE usuario_id=:u", u=target["id"])
    audit(
        db,
        u,
        "USER_ACCESS_CHANGED",
        detail={
            "id": target["id"],
            "roles": p.roles,
            "active": p.active,
            "organization_id": organization,
        },
    )
    return {"ok": True}


@bp.route(route="management/users/{id}/password", methods=["POST"])
@endpoint
def reset_password(db, req):
    u, p = admin(db, req), body(req, Password)
    target = one(db, "SELECT id FROM usuarios WHERE id=:id FOR UPDATE", id=uid(req.route_params["id"]))
    if not target:
        raise AppError(404, "Usuario no encontrado.")
    execute(
        db,
        "UPDATE usuarios SET hash_contrasena=:hash WHERE id=:id",
        hash=hasher.hash(p.password),
        id=target["id"],
    )
    execute(db, "DELETE FROM sesiones WHERE usuario_id=:id", id=target["id"])
    audit(db, u, "Contraseña restablecida", detail={"user_id": target["id"]})
    return {"ok": True}


@bp.route(route="management/catalog", methods=["POST"])
@endpoint
def admin_catalog(db, req):
    u, p = admin(db, req), body(req, Catalog)
    result = one(
        db,
        "INSERT INTO catalogo_ensayos(codigo,nombre,metodo,categoria,activo) VALUES(:code,:name,:method,:category,:active)\n        ON CONFLICT(codigo) DO UPDATE SET nombre=excluded.nombre,metodo=excluded.metodo,categoria=excluded.categoria,activo=excluded.activo RETURNING id",
        **p.model_dump(),
    )
    audit(db, u, "CATALOG_SAVED", detail={"id": result["id"]})
    return result
