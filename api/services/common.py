import json

from database import execute


def audit(db, user, action, request_id=None, detail=None, internal=True, kind="EVENT"):
    execute(
        db,
        "INSERT INTO actividad(autor_id,solicitud_id,mensaje,detalle,interno,tipo)\n        VALUES(:actor,:rid,:message,CAST(:detail AS jsonb),:internal,:kind)",
        actor=user["id"] if user else None,
        rid=request_id,
        message=action,
        detail=json.dumps(detail or {}, default=str),
        internal=internal,
        kind=kind,
    )


def touch(db, rid):
    execute(db, "UPDATE solicitudes SET version=version+1,actualizado_en=now() WHERE id=:id", id=rid)
