import azure.functions as func

from database import execute, one, rows
from errors import AppError
from http_helpers import body, endpoint, uid
from security import hasher, require_role, session
from services.common import audit
from validation import Catalog, Organization, Password, Project, UserCreate, UserEdit

bp = func.Blueprint()


def admin(db, req):
    u = session(db, req)
    require_role(u, "ADMIN")
    return u


def members(db, user_id, project_ids, organization_id):
    for pid in set(project_ids):
        p = one(db, "SELECT * FROM proyectos WHERE id=:p", p=pid)
        if not p or p["organization_id"] != organization_id:
            raise AppError(400, "Los proyectos deben pertenecer a la empresa del usuario.")
    execute(db, "DELETE FROM miembros_proyecto WHERE usuario_id=:u", u=user_id)
    for pid in set(project_ids):
        execute(db, "INSERT INTO miembros_proyecto(usuario_id,proyecto_id) VALUES(:u,:p)", u=user_id, p=pid)


@bp.route(route="management/data", methods=["GET"])
@endpoint
def admin_data(db, req):
    admin(db, req)
    return {
        "organizations": rows(db, "SELECT * FROM empresas ORDER BY nombre"),
        "projects": rows(db, "SELECT * FROM proyectos ORDER BY codigo"),
        "users": rows(
            db,
            "SELECT u.id,u.nombre,u.correo,u.roles,u.activo,u.empresa_id,ARRAY(SELECT proyecto_id FROM miembros_proyecto WHERE usuario_id=u.id) project_ids\n                FROM usuarios u ORDER BY u.nombre",
        ),
        "catalog": rows(db, "SELECT * FROM catalogo_ensayos ORDER BY codigo"),
    }


@bp.route(route="management/organizations", methods=["POST"])
@endpoint
def admin_organizations(db, req):
    u, p = admin(db, req), body(req, Organization)
    r = one(
        db,
        "INSERT INTO empresas(nombre,identificacion_tributaria) VALUES(:n,:t) RETURNING *",
        n=p.name,
        t=p.tax_id or None,
    )
    audit(db, u, "ORGANIZATION_CREATED", detail={"id": r["id"]})
    return r


@bp.route(route="management/projects", methods=["POST"])
@endpoint
def admin_projects(db, req):
    u, p = admin(db, req), body(req, Project)
    execute(db, "SELECT pg_advisory_xact_lock(481701)")
    r = one(
        db,
        "INSERT INTO proyectos(empresa_id,codigo,nombre,ubicacion)\n        VALUES(:organization_id,:code,:name,:location) RETURNING *",
        **p.model_dump(),
    )
    assigned = rows(
        db,
        "INSERT INTO miembros_proyecto(proyecto_id,usuario_id) SELECT :p,id FROM usuarios WHERE empresa_id=:o RETURNING usuario_id",
        p=r["id"],
        o=p.organization_id,
    )
    audit(
        db,
        u,
        "PROJECT_CREATED",
        detail={"id": r["id"], "assigned_user_ids": [a["user_id"] for a in assigned]},
    )
    return r


@bp.route(route="management/users", methods=["POST"])
@endpoint
def admin_users(db, req):
    u, p = admin(db, req), body(req, UserCreate)
    if "CLIENT" in p.roles and not p.organization_id:
        raise AppError(400, "Asigna una empresa al cliente.")
    execute(db, "SELECT pg_advisory_xact_lock(481701)")
    r = one(
        db,
        "INSERT INTO usuarios(nombre,correo,empresa_id,roles,hash_contrasena) VALUES(:n,:e,:o,:roles,:hash) RETURNING id",
        n=p.name,
        e=str(p.email).lower(),
        o=p.organization_id,
        roles=p.roles,
        hash=hasher.hash(p.password),
    )
    members(db, r["id"], p.project_ids, p.organization_id)
    audit(db, u, "USER_CREATED", detail={"id": r["id"], "roles": p.roles, "project_ids": p.project_ids})
    return r


@bp.route(route="management/users/{id}", methods=["PUT"])
@endpoint
def edit_user(db, req):
    u, p = admin(db, req), body(req, UserEdit)
    # Serialize administrative membership changes, including concurrent last-admin demotions.
    execute(db, "SELECT pg_advisory_xact_lock(481701)")
    target = one(db, "SELECT * FROM usuarios WHERE id=:u FOR UPDATE", u=uid(req.route_params["id"]))
    if not target:
        raise AppError(404, "Usuario no encontrado.")
    if "ADMIN" in target["roles"] and target["active"] and (not p.active or "ADMIN" not in p.roles):
        if one(db, "SELECT count(*) n FROM usuarios WHERE activo AND 'ADMIN'=ANY(roles)")["n"] <= 1:
            raise AppError(409, "Debe existir al menos un administrador activo.")
    organization = p.organization_id if "organization_id" in p.model_fields_set else target["organization_id"]
    if "CLIENT" in p.roles and not organization:
        raise AppError(400, "Asigna una empresa al cliente.")
    members(db, target["id"], p.project_ids, organization)
    execute(
        db,
        "UPDATE usuarios SET roles=:r,activo=:a,empresa_id=:o WHERE id=:u",
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
            "project_ids": p.project_ids,
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
