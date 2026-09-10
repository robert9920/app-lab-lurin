from database import execute, one, rows
from errors import AppError
from security import (
    client_project,
    is_staff,
    laboratory_access,
    project_access,
    request_access,
    require_role,
    technical_only,
)
from services.common import audit, touch


def allowed_actions(user, task, request_status):
    if request_status != "APPROVED" or task["state"] in ("COMPLETED", "CANCELLED"):
        return []
    manager = "MANAGER" in user["roles"]
    owner = "TECH" in user["roles"] and task["technician_id"] == user["id"]
    if not (manager or owner):
        return []
    state, assigned = task["state"], task["technician_id"] is not None
    actions = []
    if manager:
        if state == "PENDING":
            actions.append("assign")
        actions.append("cancel")
        if state == "OBSERVED" and assigned and task["started_at"] and task["condition"] == "OK":
            actions.append("resume")
    if state == "PENDING" and assigned and task["condition"] == "OK":
        actions.append("start")
    if state == "RUNNING" and assigned and task["started_at"]:
        actions.append("observe")
        if task["condition"] == "OK":
            actions.append("complete")
    return actions


def readable_history(data, user):
    """Whitelist human-readable audit fields; never return raw JSON or unrelated task changes."""
    states = {
        "PENDING": "Pendiente",
        "RUNNING": "En ejecución",
        "OBSERVED": "Observado",
        "COMPLETED": "Completado",
        "CANCELLED": "Cancelado",
        "OK": "Conforme",
        "NOT_RECEIVED": "No recibida",
        "DAMAGED": "Dañada",
        "INSUFFICIENT": "Insuficiente",
    }
    tasks = {str(t["id"]): t for t in data["tasks"]}
    samples = {str(s["id"]): s for s in data["samples"]}
    result = []
    for event in data["activity"]:
        raw = event.pop("detail", {})
        lines = []
        if "task_id" in raw:
            task = tasks.get(str(raw["task_id"]))
            if technical_only(user) and (task is None or task["technician_id"] != user["id"]):
                continue
            if task:
                lines.append(f"{task['sample_code']} · {task.get('name', task.get('assay_name', 'Ensayo'))}")
                if raw.get("action") == "assign":
                    lines.append("Responsable: " + raw.get("technician_name", "Asignación actualizada"))
                    lines.append(
                        "Programación: "
                        + str(raw.get("planned_start") or "Sin fecha")
                        + " – "
                        + str(raw.get("planned_end") or "Sin fecha")
                    )
                else:
                    lines.append(
                        f"{states.get(raw.get('from'), 'Estado anterior')} → {states.get(raw.get('to'), 'Estado actualizado')}"
                    )
            if raw.get("reason"):
                lines.append("Motivo: " + raw["reason"])
        if "samples" in raw:
            changes = [
                c
                for c in raw["samples"]
                if str(c["sample_id"]) in samples
                and (not technical_only(user) or samples[str(c["sample_id"])].get("can_receive"))
            ]
            if technical_only(user) and not changes:
                continue
            for change in changes:
                s = samples[str(change["sample_id"])]
                after = change.get("after", {})
                lines.append(
                    f"{s['client_code']}: {states.get(after.get('condition'), 'Recepción actualizada')}"
                )
                for key, label in (
                    ("received_quantity", "Cantidad recibida"),
                    ("codigo_recepcion", "Recepción"),
                    ("codigo_laboratorio", "Código laboratorio"),
                    ("reception_notes", "Observación"),
                ):
                    if after.get(key) not in (None, ""):
                        lines.append(f"{label}: {after[key]}")
        if "report_id" in raw and raw.get("version"):
            lines.append(f"Informe PDF · versión {raw['version']}")
        event["description_lines"] = lines
        result.append(event)
    return result


def require_approved(r):
    if r["status"] != "APPROVED":
        raise AppError(409, "La solicitud debe estar aprobada.")


def detail(db, user, rid):
    r = request_access(db, user, rid)
    r["project"] = one(
        db,
        "SELECT p.*,o.nombre organization_name FROM proyectos p\n        JOIN empresas o ON o.id=p.empresa_id WHERE p.id=:id",
        id=r["project_id"],
    )
    r["samples"] = rows(
        db,
        "SELECT s.*,ARRAY(SELECT ensayo_id FROM ensayos_muestra WHERE muestra_id=s.id) assay_ids\n        FROM muestras s WHERE solicitud_id=:id ORDER BY codigo_cliente",
        id=rid,
    )
    r["tasks"] = rows(
        db,
        "SELECT a.*,s.codigo_cliente sample_code,s.condicion,c.nombre,c.codigo assay_code,u.nombre technician_name\n        FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id JOIN catalogo_ensayos c ON c.id=a.ensayo_id\n        LEFT JOIN usuarios u ON u.id=a.tecnico_id WHERE s.solicitud_id=:id ORDER BY s.codigo_cliente,c.nombre",
        id=rid,
    )
    client_view = client_project(db, user, r["project_id"])
    owned = {t["sample_id"] for t in r["tasks"] if t["technician_id"] == user["id"]}
    for s in r["samples"]:
        s["can_receive"] = "MANAGER" in user["roles"] or ("TECH" in user["roles"] and s["id"] in owned)
    r["reports"] = rows(
        db,
        "SELECT id,solicitud_id,version,nombre,tamano_bytes,creado_en,subido_por FROM informes\n        WHERE solicitud_id=:id ORDER BY version DESC",
        id=rid,
    )
    r["activity"] = rows(
        db,
        "SELECT a.id,a.tipo,a.mensaje,a.interno,a.creado_en,u.nombre actor_name,\n        CASE WHEN :staff THEN a.detalle ELSE '{}'::jsonb END detalle FROM actividad a LEFT JOIN usuarios u ON u.id=a.autor_id\n        WHERE a.solicitud_id=:id AND (:staff OR NOT a.interno) ORDER BY a.id DESC",
        id=rid,
        staff=is_staff(user) and (not technical_only(user) or bool(owned)),
    )
    if technical_only(user) and not client_view:
        r["tasks"] = [t for t in r["tasks"] if t["technician_id"] == user["id"]]
        sample_ids = {t["sample_id"] for t in r["tasks"]}
        r["samples"] = [s for s in r["samples"] if s["id"] in sample_ids]
        for s in r["samples"]:
            s["assay_ids"] = [t["assay_id"] for t in r["tasks"] if t["sample_id"] == s["id"]]
    for t in r["tasks"]:
        t["assigned"] = t["technician_id"] is not None
        t["allowed_actions"] = allowed_actions(user, t, r["status"])
    r["activity"] = readable_history(r, user)
    # Internal technical notes are not part of the client projection.
    for t in r["tasks"]:
        if not is_staff(user) or (technical_only(user) and t["technician_id"] != user["id"]):
            t["notes"] = ""
    return r


def save_samples(db, rid, samples):
    for s in samples:
        p = s.model_dump(exclude={"assay_ids"})
        for aid in s.assay_ids:
            if not one(db, "SELECT id FROM catalogo_ensayos WHERE id=:id AND activo", id=aid):
                raise AppError(400, "Selecciona ensayos activos del catálogo.")
        sample = one(
            db,
            "INSERT INTO muestras(solicitud_id,codigo_cliente,calicata_sondaje,material,profundidad_inicial,profundidad_final,cantidad,unidad,observaciones)\n            VALUES(:rid,:client_code,:borehole,:material,:depth_from,:depth_to,:quantity,:unit,:notes) RETURNING id",
            rid=rid,
            **p,
        )
        for aid in s.assay_ids:
            execute(
                db,
                "INSERT INTO ensayos_muestra(muestra_id,ensayo_id) VALUES(:sid,:aid)",
                sid=sample["id"],
                aid=aid,
            )


def create_request(db, user, data):
    require_role(user, "CLIENT")
    p = project_access(db, {**user, "roles": ["CLIENT"]}, data.project_id)
    if not p["active"]:
        raise AppError(409, "Proyecto inactivo.")
    r = one(
        db,
        "INSERT INTO solicitudes(proyecto_id,creado_por,titulo,observaciones,fecha_objetivo)\n        VALUES(:pid,:uid,:title,:notes,:date) RETURNING *",
        pid=data.project_id,
        uid=user["id"],
        title=data.title,
        notes=data.notes,
        date=data.target_date,
    )
    save_samples(db, r["id"], data.samples)
    audit(db, user, "Solicitud creada", r["id"], internal=False)
    return {"id": r["id"]}


def edit_request(db, user, rid, data):
    require_role(user, "CLIENT")
    r = request_access(db, user, rid, data.version)
    if r["status"] not in ("DRAFT", "OBSERVED"):
        raise AppError(409, "Solo se pueden editar borradores o solicitudes observadas.")
    if data.project_id != r["project_id"]:
        raise AppError(400, "No se puede cambiar de proyecto.")
    execute(db, "DELETE FROM muestras WHERE solicitud_id=:id", id=rid)
    save_samples(db, rid, data.samples)
    execute(
        db,
        "UPDATE solicitudes SET titulo=:title,observaciones=:notes,fecha_objetivo=:date WHERE id=:id",
        title=data.title,
        notes=data.notes,
        date=data.target_date,
        id=rid,
    )
    touch(db, rid)
    audit(db, user, "Solicitud corregida", rid, internal=False)
    return {"ok": True}


def action(db, user, rid, data):
    r = request_access(db, user, rid, data.version)
    transitions = {
        "submit": (("DRAFT", "OBSERVED"), "SUBMITTED"),
        "approve": (("SUBMITTED",), "APPROVED"),
        "observe": (("SUBMITTED",), "OBSERVED"),
        "reject": (("SUBMITTED",), "REJECTED"),
        "close": (("APPROVED",), "CLOSED"),
    }
    old, new = transitions[data.action]
    if data.action != "submit":
        require_role(user, "MANAGER")
    else:
        require_role(user, "CLIENT")
    if r["status"] not in old:
        raise AppError(409, "Esta transición no corresponde al estado actual.")
    if data.action in ("observe", "reject") and not data.reason:
        raise AppError(400, "Indica el motivo.")
    if data.action == "close":
        pending = one(
            db,
            "SELECT count(*) n FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id\n            WHERE s.solicitud_id=:id AND a.estado_ensayo NOT IN ('COMPLETED','CANCELLED')",
            id=rid,
        )["n"]
        if pending or not one(db, "SELECT 1 FROM informes WHERE solicitud_id=:id", id=rid):
            raise AppError(409, "Resuelve todos los ensayos y carga un informe antes de cerrar.")
    execute(db, "UPDATE solicitudes SET estado_solicitud=:status WHERE id=:id", status=new, id=rid)
    touch(db, rid)
    audit(
        db,
        user,
        {
            "submit": "Solicitud enviada",
            "approve": "Solicitud aprobada",
            "observe": "Solicitud observada",
            "reject": "Solicitud rechazada",
            "close": "Servicio cerrado",
        }[data.action]
        + (": " + data.reason if data.reason else ""),
        rid,
        {"from": r["status"], "to": new},
        internal=False,
    )
    return {"ok": True}


def reception(db, user, rid, data):
    require_role(user, "MANAGER", "TECH")
    require_approved(laboratory_access(db, user, rid, data.version))
    if len({s.sample_id for s in data.samples}) != len(data.samples):
        raise AppError(400, "Muestra duplicada.")
    changes = []
    for received in data.samples:
        old = one(
            db, "SELECT * FROM muestras WHERE id=:sid AND solicitud_id=:rid", sid=received.sample_id, rid=rid
        )
        if not old:
            raise AppError(404, "Muestra ajena a esta solicitud.")
        if "MANAGER" not in user["roles"] and not one(
            db,
            "SELECT 1 FROM ensayos_muestra WHERE muestra_id=:sid AND tecnico_id=:u",
            sid=old["id"],
            u=user["id"],
        ):
            raise AppError(404, "Muestra no encontrada.")
        if old["received_at"] and not data.reason:
            raise AppError(400, "Una corrección requiere motivo.")
        if received.condition != "OK" and one(
            db,
            "SELECT 1 FROM ensayos_muestra\n            WHERE muestra_id=:id AND estado_ensayo IN ('RUNNING','COMPLETED')",
            id=old["id"],
        ):
            raise AppError(409, "No puedes invalidar material con ensayos en ejecución o completados.")
        execute(
            db,
            "UPDATE muestras SET recibido_en=:at,recibido_por=:uid,transporte=:transport,\n            cantidad_recibida=:received_quantity,condicion=:condition,observaciones_recepcion=:reception_notes,\n            codigo_recepcion=:codigo_recepcion,codigo_laboratorio=:codigo_laboratorio WHERE id=:sample_id",
            at=data.received_at,
            uid=user["id"],
            transport=data.transport,
            **received.model_dump(),
        )
        changes.append(
            {
                "sample_id": old["id"],
                "before": {
                    k: old[k]
                    for k in (
                        "received_at",
                        "received_quantity",
                        "condition",
                        "transport",
                        "reception_notes",
                        "codigo_recepcion",
                        "codigo_laboratorio",
                    )
                },
                "after": received.model_dump(),
                "received_at": data.received_at,
                "transport": data.transport,
            }
        )
    touch(db, rid)
    audit(
        db,
        user,
        "Recepción registrada" + (": " + data.reason if data.reason else ""),
        rid,
        {"samples": changes},
        internal=False,
    )
    return {"ok": True}


def update_tasks(db, user, rid, data):
    require_role(user, "MANAGER", "TECH")
    require_approved(laboratory_access(db, user, rid, data.version))
    manager = "MANAGER" in user["roles"]
    if len(set(data.task_ids)) != len(data.task_ids):
        raise AppError(400, "Ensayo duplicado.")
    if data.action in ("assign", "cancel", "resume"):
        require_role(user, "MANAGER")
    if data.action in ("observe", "cancel", "resume") and not data.reason:
        raise AppError(400, "Indica un motivo.")
    if data.action == "assign" and not one(
        db,
        "SELECT 1 FROM usuarios WHERE id=:id AND activo\n        AND roles && ARRAY['TECH','MANAGER']",
        id=data.technician_id,
    ):
        raise AppError(400, "Selecciona un técnico activo.")
    for tid in set(data.task_ids):
        task = one(
            db,
            "SELECT a.*,s.condicion FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id\n            WHERE a.id=:id AND s.solicitud_id=:rid",
            id=tid,
            rid=rid,
        )
        if not task:
            raise AppError(404, "Ensayo no encontrado.")
        if not manager and task["technician_id"] != user["id"]:
            raise AppError(403, "Solo puedes modificar ensayos asignados a ti.")
        if data.action not in allowed_actions(user, task, "APPROVED"):
            raise AppError(
                409, "La acción requiere un estado, responsable y material compatibles. Recarga la lista."
            )
        new = {
            "assign": task["state"],
            "start": "RUNNING",
            "observe": "OBSERVED",
            "complete": "COMPLETED",
            "cancel": "CANCELLED",
            "resume": "RUNNING",
        }[data.action]
        execute(
            db,
            "UPDATE ensayos_muestra SET estado_ensayo=:state,\n            tecnico_id=CASE WHEN :action='assign' THEN :tech ELSE tecnico_id END,\n            inicio_previsto=CASE WHEN :action='assign' THEN :start ELSE inicio_previsto END,\n            fin_previsto=CASE WHEN :action='assign' THEN :end ELSE fin_previsto END,\n            iniciado_en=CASE WHEN :action='start' THEN coalesce(iniciado_en,now()) ELSE iniciado_en END,\n            completado_en=CASE WHEN :action='complete' THEN now() ELSE completado_en END,\n            observaciones=CASE WHEN :reason<>'' THEN :reason ELSE observaciones END WHERE id=:id",
            state=new,
            action=data.action,
            tech=data.technician_id,
            start=data.planned_start,
            end=data.planned_end,
            reason=data.reason,
            id=tid,
        )
        audit(
            db,
            user,
            "Ensayo actualizado",
            rid,
            {
                "task_id": tid,
                "from": task["state"],
                "to": new,
                "reason": data.reason,
                "action": data.action,
                "technician_name": one(db, "SELECT nombre FROM usuarios WHERE id=:id", id=data.technician_id)[
                    "name"
                ]
                if data.action == "assign"
                else None,
                "technician_id": data.technician_id if data.action == "assign" else task["technician_id"],
                "planned_start": data.planned_start,
                "planned_end": data.planned_end,
            },
            internal=True,
        )
    touch(db, rid)
    return {"ok": True}
