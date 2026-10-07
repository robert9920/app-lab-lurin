from database import execute, one, rows
from errors import AppError
from security import (
    client_request,
    is_staff,
    laboratory_access,
    request_access,
    require_role,
    scope_params,
    technical_only,
)
from services.common import audit, touch
from services.projects import validate_code
from services.statuses import assay_case, request_counts
from validation import complete_request, validate_coordinates


def allowed_actions(user, task, request_status, codigo_ot=None):
    if (
        not task.get("approved")
        or request_status != "APPROVED"
        or task["state"] in ("COMPLETED", "CANCELLED")
    ):
        return []
    manager = "MANAGER" in user["roles"]
    owner = "TECH" in user["roles"] and task["technician_id"] == user["id"]
    if not (manager or owner):
        return []
    state, assigned = task["state"], task["technician_id"] is not None
    actions = []
    if manager:
        if state == "PENDING" and codigo_ot:
            actions.append("assign")
        actions.append("cancel")
        if (
            state == "OBSERVED"
            and assigned
            and task["started_at"]
            and task["condition"] == "OK"
            and codigo_ot
        ):
            actions.append("resume")
    if state == "PENDING" and assigned and task["condition"] == "OK" and codigo_ot:
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
                if raw.get("action") == "review":
                    lines.append(
                        "Aprobado para programación y ejecución"
                        if raw.get("to") == "APPROVED"
                        else "Ensayo rechazado"
                    )
                elif raw.get("action") == "resubmit":
                    lines.append("Solicitado nuevamente; pendiente de revisión")
                elif raw.get("action") == "approve":
                    lines.append("Aprobado para programación y ejecución")
                elif raw.get("action") == "assign":
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
        if "sample_id" in raw:
            sample = samples.get(str(raw["sample_id"]))
            if technical_only(user) and not sample:
                continue
            if sample:
                lines.append("Muestra: " + sample["client_code"])
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
                    ("received_quantity", "Recipientes recibidos"),
                    ("received_weight", "Peso recibido (kg)"),
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


def review_projection(db, tasks):
    """Only public review reasons for the already authorized task IDs."""
    if not tasks:
        return
    latest = rows(
        db,
        """SELECT DISTINCT ON (detalle->>'task_id') detalle->>'task_id' task_id,
        coalesce(detalle->>'reason','') reason FROM actividad
        WHERE NOT interno AND detalle->>'task_id'=ANY(:ids)
        AND detalle->>'action' IN ('review','resubmit')
        ORDER BY detalle->>'task_id',id DESC""",
        ids=[str(t["id"]) for t in tasks],
    )
    reasons = {x["task_id"]: x["reason"] for x in latest}
    for t in tasks:
        t["review_reason"] = reasons.get(str(t["id"]), "")


def state_reason_projection(db, tasks):
    """Public operational reasons only; IDs have already been scoped by the caller."""
    ids = [str(t["id"]) for t in tasks if t["state"] in ("OBSERVED", "CANCELLED")]
    events = (
        rows(
            db,
            """SELECT DISTINCT ON (a.detalle->>'task_id')
        a.detalle->>'task_id' task_id,a.detalle->>'to' target_state,
        coalesce(a.detalle->>'reason','') reason,u.nombre actor_name,a.creado_en
        FROM actividad a LEFT JOIN usuarios u ON u.id=a.autor_id
        WHERE a.tipo='EVENT' AND a.detalle->>'task_id'=ANY(:ids)
        AND a.detalle->>'action' IN ('observe','cancel')
        AND a.detalle->>'to' IN ('OBSERVED','CANCELLED')
        ORDER BY a.detalle->>'task_id',a.id DESC""",
            ids=ids,
        )
        if ids
        else []
    )
    latest = {e["task_id"]: e for e in events}
    for task in tasks:
        event = latest.get(str(task["id"]))
        if event and event["target_state"] == task["state"]:
            task["state_reason"] = event["reason"]
            task["state_reason_author"] = event["actor_name"]
            task["state_reason_at"] = event["created_at"]
        else:
            task["state_reason"] = ""
            task["state_reason_author"] = None
            task["state_reason_at"] = None


def detail(db, user, rid):
    r = request_access(db, user, rid)
    organization = one(db, "SELECT nombre,es_interna FROM empresas WHERE id=:id", id=r["organization_id"])
    r["is_internal"] = organization["is_internal"]
    r["project"] = {
        "id": r["project_id"],
        "code": r["project_id"],
        "name": r["project_id"],
        "organization_name": organization["name"],
    }
    r["can_cancel"] = (
        r["status"] != "DRAFT"
        and r["request_status"] == "CREATED"
        and (client_request(user, r) or "MANAGER" in user["roles"])
    )
    r["can_edit"] = (
        r["request_status"] == "CREATED"
        and client_request(user, r)
        and r["status"]
        in (
            "DRAFT",
            "WAITING_ASSAYS",
            "SUBMITTED",
            "OBSERVED",
        )
    )
    r["can_edit_assays"] = (
        r["request_status"] == "CREATED" and client_request(user, r) and r["status"] == "APPROVED"
    )
    r["samples"] = rows(
        db,
        "SELECT s.*,ARRAY(SELECT ensayo_id FROM ensayos_muestra WHERE muestra_id=s.id) assay_ids\n        FROM muestras s WHERE solicitud_id=:id ORDER BY codigo_cliente",
        id=rid,
    )
    r["tasks"] = rows(
        db,
        "SELECT a.*,("
        + assay_case()
        + ") assay_status,s.codigo_cliente sample_code,s.condicion,c.nombre,c.codigo assay_code,u.nombre technician_name\n        FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id JOIN catalogo_ensayos c ON c.id=a.ensayo_id\n        LEFT JOIN usuarios u ON u.id=a.tecnico_id WHERE s.solicitud_id=:id ORDER BY s.codigo_cliente,c.nombre",
        id=rid,
    )
    client_view = client_request(user, r)
    owned = {t["sample_id"] for t in r["tasks"] if t["technician_id"] == user["id"]}
    for s in r["samples"]:
        s["can_print"] = "MANAGER" in user["roles"] or ("TECH" in user["roles"] and s["id"] in owned)
        s["can_receive"] = r["request_status"] == "CREATED" and s["can_print"]
    r["reports"] = rows(
        db,
        "SELECT id,solicitud_id,version,nombre,tamano_bytes,creado_en,subido_por FROM informes\n        WHERE solicitud_id=:id ORDER BY version DESC",
        id=rid,
    )
    r["activity"] = rows(
        db,
        """SELECT a.id,a.tipo,a.mensaje,
        CASE WHEN NOT :staff AND a.tipo='EVENT' AND a.detalle->>'action' IN ('observe','cancel')
             THEN false ELSE a.interno END interno,
        a.creado_en,u.nombre actor_name,
        CASE WHEN :staff THEN a.detalle
             WHEN a.tipo='EVENT' AND a.detalle->>'action' IN ('observe','cancel','review','resubmit')
             THEN jsonb_build_object('task_id',a.detalle->>'task_id','action',a.detalle->>'action',
                  'from',a.detalle->>'from','to',a.detalle->>'to','reason',a.detalle->>'reason')
             ELSE '{}'::jsonb END detalle
        FROM actividad a LEFT JOIN usuarios u ON u.id=a.autor_id
        WHERE a.solicitud_id=:id AND (:staff OR NOT a.interno OR
          (a.tipo='EVENT' AND a.detalle->>'action' IN ('observe','cancel') AND
           EXISTS(SELECT 1 FROM ensayos_muestra ax JOIN muestras sx ON sx.id=ax.muestra_id
                  WHERE sx.solicitud_id=a.solicitud_id AND ax.id::text=a.detalle->>'task_id')))
        ORDER BY a.id DESC""",
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
        t["allowed_actions"] = (
            allowed_actions(user, t, r["status"], r["codigo_ot"]) if r["request_status"] == "CREATED" else []
        )
        t["can_review"] = (
            "MANAGER" in user["roles"]
            and r["request_status"] == "CREATED"
            and r["status"] in ("WAITING_ASSAYS", "SUBMITTED", "APPROVED")
            and t["review_status"] == "PENDING"
            and t["state"] == "PENDING"
        )
        t["can_resubmit"] = (
            client_request(user, r)
            and r["request_status"] == "CREATED"
            and r["status"] in ("WAITING_ASSAYS", "SUBMITTED", "OBSERVED", "APPROVED")
            and t["review_status"] == "REJECTED"
        )
    review_projection(db, r["tasks"])
    state_reason_projection(db, r["tasks"])
    r["undefined_samples"] = sum(not s["assay_ids"] for s in r["samples"])
    r["unapproved_count"] = sum(
        t["review_status"] == "PENDING" and t["state"] == "PENDING" for t in r["tasks"]
    )
    r["assay_counts"] = request_counts(
        db, rid, {**scope_params(user), "all_samples": not technical_only(user) or client_view}
    )
    r["activity"] = readable_history(r, user)
    # Internal technical notes are not part of the client projection.
    for t in r["tasks"]:
        if not is_staff(user) or (technical_only(user) and t["technician_id"] != user["id"]):
            t["notes"] = ""
    return r


def declared_samples(samples):
    """Keep partial draft rows, but do not persist a blank UI placeholder."""
    kept = [s for s in samples if any(value not in (None, "", []) for value in s.model_dump().values())]
    codes = [s.client_code for s in kept if s.client_code]
    if len(codes) != len(set(codes)):
        raise AppError(400, "Muestra: el código no puede repetirse dentro de la solicitud.")
    return kept


def save_samples(db, rid, samples):
    for s in samples:
        validate_coordinates(s)
        p = s.model_dump(exclude={"assay_ids", "id"})
        for aid in s.assay_ids:
            if not one(db, "SELECT id FROM catalogo_ensayos WHERE id=:id AND activo", id=aid):
                raise AppError(400, "Selecciona ensayos activos del catálogo.")
        sample = one(
            db,
            "INSERT INTO muestras(solicitud_id,codigo_cliente,calicata_sondaje,material,profundidad_inicial,profundidad_final,cantidad,peso,observaciones,coordenada_este,coordenada_norte)\n            VALUES(:rid,:client_code,:borehole,:material,:depth_from,:depth_to,:quantity,:weight,:notes,:easting,:northing) RETURNING id",
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


def organization_for(db, user):
    org = one(db, "SELECT * FROM empresas WHERE id=:id AND activo", id=user["organization_id"])
    if not org:
        raise AppError(400, "Asigna una empresa habilitada al solicitante.")
    return org


def create_request(db, user, data):
    require_role(user, "CLIENT")
    org = organization_for(db, user)
    code = (validate_code(data.project_id) if data.project_id else None) if org["is_internal"] else "EXTERNO"
    data.samples = declared_samples(data.samples)
    if any(s.id is not None for s in data.samples):
        raise AppError(400, "Una muestra nueva no debe incluir identificador.")
    r = one(
        db,
        "INSERT INTO solicitudes(proyecto_id,empresa_id,creado_por,observaciones,fecha_objetivo,"
        "fecha_estimada_arribo,distrito,provincia,departamento) "
        "VALUES(:pid,:org,:uid,:notes,:date,:arrival,:district,:province,:department) RETURNING *",
        pid=code,
        org=org["id"],
        uid=user["id"],
        notes=data.notes,
        date=data.target_date,
        arrival=data.estimated_arrival_date,
        district=data.district,
        province=data.province,
        department=data.department,
    )
    save_samples(db, r["id"], data.samples)
    audit(db, user, "Borrador guardado", r["id"], internal=False)
    return {"id": r["id"]}


def missing_assays(db, rid):
    return one(
        db,
        "SELECT count(*) n FROM muestras s WHERE s.solicitud_id=:id AND NOT EXISTS(SELECT 1 FROM ensayos_muestra a WHERE a.muestra_id=s.id)",
        id=rid,
    )["n"]


def edit_request(db, user, rid, data):
    require_role(user, "CLIENT")
    r = request_access(db, user, rid, data.version)
    if not client_request(user, r) or r["status"] not in ("DRAFT", "WAITING_ASSAYS", "SUBMITTED", "OBSERVED"):
        raise AppError(409, "Solo el autor puede editar una solicitud antes de su aprobación.")
    if r["status"] != "DRAFT":
        complete_request(data.model_dump(exclude={"version"}))
    data.samples = declared_samples(data.samples)
    org = one(db, "SELECT * FROM empresas WHERE id=:id", id=r["organization_id"])
    code = data.project_id if org["is_internal"] else "EXTERNO"
    # Existing historical codes are retained, including companies reclassified later.
    if r["status"] != "DRAFT":
        if data.project_id not in (None, r["project_id"]):
            raise AppError(400, "No se puede cambiar de proyecto después del envío.")
        code = r["project_id"]
    elif code and code != r["project_id"] and org["is_internal"]:
        validate_code(code)
    existing = {x["id"]: x for x in rows(db, "SELECT * FROM muestras WHERE solicitud_id=:id", id=rid)}
    ids = [s.id for s in data.samples if s.id]
    if len(ids) != len(set(ids)) or not set(ids).issubset(existing):
        raise AppError(400, "Identificadores de muestras inválidos o repetidos.")
    codes = [s.client_code for s in data.samples if s.client_code]
    if len(codes) != len(set(codes)):
        raise AppError(400, "Muestra: el código no puede repetirse dentro de la solicitud.")
    declared = (
        "client_code",
        "borehole",
        "material",
        "depth_from",
        "depth_to",
        "quantity",
        "weight",
        "easting",
        "northing",
        "notes",
    )
    changes = []
    for sample in data.samples:
        validate_coordinates(sample)
        if not sample.id:
            continue
        old = existing[sample.id]
        values = sample.model_dump(exclude={"id", "assay_ids"})
        if old["received_at"] and any(old[k] != values[k] for k in declared):
            raise AppError(
                409, "Los datos de una muestra recibida están protegidos. Puedes completar sus ensayos."
            )
        tasks = rows(db, "SELECT * FROM ensayos_muestra WHERE muestra_id=:id", id=sample.id)
        for t in tasks:
            if t["assay_id"] not in sample.assay_ids and (
                t["review_status"] != "PENDING"
                or t["technician_id"]
                or t["started_at"]
                or t["state"] != "PENDING"
            ):
                raise AppError(409, "No se puede retirar un ensayo asignado o iniciado.")
        changes.append(
            {
                "sample_id": sample.id,
                "client_code": sample.client_code,
                "before": {k: old[k] for k in declared},
                "after": values,
                "assay_ids": sample.assay_ids,
            }
        )
    for sid in set(existing) - set(ids):
        if existing[sid]["received_at"] or one(
            db,
            "SELECT 1 FROM ensayos_muestra WHERE muestra_id=:id AND (estado_revision<>'PENDING' OR tecnico_id IS NOT NULL OR iniciado_en IS NOT NULL OR estado_ensayo<>'PENDING')",
            id=sid,
        ):
            raise AppError(409, "No se puede eliminar una muestra recibida o con trabajo asignado.")
        execute(db, "DELETE FROM muestras WHERE id=:id", id=sid)
    # Permit code swaps without violating the per-request unique constraint.
    for sample in data.samples:
        if sample.id and existing[sample.id]["client_code"] != sample.client_code:
            execute(
                db,
                "UPDATE muestras SET codigo_cliente=:c WHERE id=:id",
                c="TEMP-" + str(sample.id),
                id=sample.id,
            )
    for sample in data.samples:
        if not sample.id:
            save_samples(db, rid, [sample])
            continue
        execute(
            db,
            "UPDATE muestras SET codigo_cliente=:client_code,calicata_sondaje=:borehole,material=:material,"
            "profundidad_inicial=:depth_from,profundidad_final=:depth_to,cantidad=:quantity,peso=:weight,observaciones=:notes,coordenada_este=:easting,coordenada_norte=:northing WHERE id=:sid",
            sid=sample.id,
            **sample.model_dump(exclude={"id", "assay_ids"}),
        )
        current = {
            t["assay_id"]
            for t in rows(db, "SELECT ensayo_id FROM ensayos_muestra WHERE muestra_id=:id", id=sample.id)
        }
        for aid in current - set(sample.assay_ids):
            execute(
                db,
                "DELETE FROM ensayos_muestra WHERE muestra_id=:sid AND ensayo_id=:aid",
                sid=sample.id,
                aid=aid,
            )
        for aid in set(sample.assay_ids) - current:
            if not one(db, "SELECT 1 FROM catalogo_ensayos WHERE id=:id AND activo", id=aid):
                raise AppError(400, "Selecciona ensayos activos del catálogo.")
            execute(
                db,
                "INSERT INTO ensayos_muestra(muestra_id,ensayo_id) VALUES(:sid,:aid)",
                sid=sample.id,
                aid=aid,
            )
    state = r["status"]
    if state in ("WAITING_ASSAYS", "SUBMITTED"):
        state = "WAITING_ASSAYS" if missing_assays(db, rid) else "SUBMITTED"
    execute(
        db,
        "UPDATE solicitudes SET proyecto_id=:pid,observaciones=:notes,fecha_objetivo=:date,fecha_estimada_arribo=:arrival,"
        "distrito=:district,provincia=:province,departamento=:department,estado_solicitud=:state WHERE id=:id",
        id=rid,
        pid=code,
        notes=data.notes,
        date=data.target_date,
        arrival=data.estimated_arrival_date,
        district=data.district,
        province=data.province,
        department=data.department,
        state=state,
    )
    touch(db, rid)
    audit(
        db,
        user,
        "Solicitud actualizada; datos y ensayos declarados",
        rid,
        {"sample_edits": changes, "from": r["status"], "to": state},
        internal=False,
    )
    return {"ok": True}


def edit_assays(db, user, rid, data):
    require_role(user, "CLIENT")
    r = request_access(db, user, rid, data.version)
    if not client_request(user, r) or r["status"] != "APPROVED":
        raise AppError(409, "Solo el autor puede solicitar ensayos de una solicitud aprobada abierta.")
    ids = [s.sample_id for s in data.samples]
    if len(set(ids)) != len(ids):
        raise AppError(400, "Muestras repetidas.")
    for sample in data.samples:
        if not one(
            db, "SELECT 1 FROM muestras WHERE id=:sid AND solicitud_id=:rid", sid=sample.sample_id, rid=rid
        ):
            raise AppError(404, "Muestra no encontrada.")
        current = {
            t["assay_id"]: t
            for t in rows(db, "SELECT * FROM ensayos_muestra WHERE muestra_id=:id", id=sample.sample_id)
        }
        removed = set(current) - set(sample.assay_ids)
        if any(
            current[aid]["review_status"] != "PENDING"
            or current[aid]["state"] != "PENDING"
            or current[aid]["technician_id"]
            for aid in removed
        ):
            raise AppError(409, "No se pueden retirar ensayos revisados o con trabajo registrado.")
        for aid in removed:
            execute(db, "DELETE FROM ensayos_muestra WHERE id=:id", id=current[aid]["id"])
        for aid in set(sample.assay_ids) - set(current):
            if not one(db, "SELECT 1 FROM catalogo_ensayos WHERE id=:id AND activo", id=aid):
                raise AppError(400, "Selecciona ensayos activos del catálogo.")
            execute(
                db,
                "INSERT INTO ensayos_muestra(muestra_id,ensayo_id) VALUES(:sid,:aid)",
                sid=sample.sample_id,
                aid=aid,
            )
        if removed or set(sample.assay_ids) - set(current):
            audit(
                db,
                user,
                "Selección de ensayos actualizada; pendiente de aprobación",
                rid,
                {"sample_id": sample.sample_id, "assay_ids": sample.assay_ids},
                internal=False,
            )
    touch(db, rid)


def action(db, user, rid, data):
    r = request_access(db, user, rid, data.version)
    if data.action == "approve":
        require_role(user, "MANAGER")
        raise AppError(409, "Selecciona los ensayos en Revisar ensayos para aprobarlos individualmente.")
    if data.action == "cancel":
        if r["status"] == "DRAFT":
            raise AppError(409, "Un borrador no puede cancelarse. Envíalo primero al laboratorio.")
        if not (client_request(user, r) or "MANAGER" in user["roles"]):
            raise AppError(403, "Solo el autor o jefatura pueden cancelar la solicitud.")
        if not data.reason:
            raise AppError(400, "Indica el motivo de cancelación.")
        cancelled = rows(
            db,
            "UPDATE ensayos_muestra a SET estado_ensayo='CANCELLED' FROM muestras s "
            "WHERE a.muestra_id=s.id AND s.solicitud_id=:id AND a.estado_revision<>'REJECTED' "
            "AND a.estado_ensayo NOT IN ('COMPLETED','CANCELLED') RETURNING a.id",
            id=rid,
        )
        for task in cancelled:
            audit(
                db,
                user,
                "Ensayo cancelado por cancelación de solicitud",
                rid,
                {"task_id": task["id"], "action": "cancel", "to": "CANCELLED", "reason": data.reason},
                internal=False,
            )
        execute(db, "UPDATE solicitudes SET estado_general='CANCELLED' WHERE id=:id", id=rid)
        touch(db, rid)
        audit(db, user, "Solicitud cancelada: " + data.reason, rid, {"reason": data.reason}, internal=False)
        return
    if data.action == "reject":
        raise AppError(409, "Usa Cancelar solicitud o revisa los ensayos individualmente.")
    transitions = {
        "submit": (("DRAFT", "OBSERVED", "WAITING_ASSAYS"), "SUBMITTED"),
        "approve": (("WAITING_ASSAYS", "SUBMITTED", "APPROVED"), "APPROVED"),
        "observe": (("SUBMITTED",), "OBSERVED"),
        "reject": (("SUBMITTED",), "REJECTED"),
        "close": (("APPROVED",), "CLOSED"),
    }
    old, new = transitions[data.action]
    if data.action != "submit":
        require_role(user, "MANAGER")
    else:
        require_role(user, "CLIENT")
        if not client_request(user, r):
            raise AppError(404, "Solicitud no encontrada.")
        complete_request(
            {
                **{
                    key: r[key]
                    for key in (
                        "project_id",
                        "notes",
                        "target_date",
                        "estimated_arrival_date",
                        "district",
                        "province",
                        "department",
                    )
                },
                "samples": [
                    {
                        **{
                            key: sample[key]
                            for key in (
                                "id",
                                "client_code",
                                "borehole",
                                "material",
                                "depth_from",
                                "depth_to",
                                "weight",
                                "easting",
                                "northing",
                                "notes",
                            )
                        },
                        "quantity": int(sample["quantity"])
                        if sample["quantity"] is not None and sample["quantity"] == int(sample["quantity"])
                        else sample["quantity"],
                    }
                    for sample in rows(
                        db,
                        "SELECT * FROM muestras WHERE solicitud_id=:id ORDER BY codigo_cliente NULLS LAST,id",
                        id=rid,
                    )
                ],
            }
        )
        org = one(db, "SELECT es_interna FROM empresas WHERE id=:id", id=r["organization_id"])
        if org["is_internal"] and not r["project_id"]:
            raise AppError(400, "Proyecto: selecciona un proyecto antes de enviar al laboratorio.")
        if missing_assays(db, rid):
            new = "WAITING_ASSAYS"
    if r["status"] not in old:
        raise AppError(409, "Esta transición no corresponde al estado actual.")
    if data.action in ("observe", "reject") and not data.reason:
        raise AppError(400, "Indica el motivo.")
    if data.action == "close":
        pending = one(
            db,
            "SELECT count(*) n FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id\n            WHERE s.solicitud_id=:id AND a.estado_revision<>'REJECTED' AND a.estado_ensayo NOT IN ('COMPLETED','CANCELLED')",
            id=rid,
        )["n"]
        if (
            missing_assays(db, rid)
            or not one(
                db,
                "SELECT 1 FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.solicitud_id=:id AND a.estado_revision='APPROVED' AND a.estado_ensayo='COMPLETED'",
                id=rid,
            )
            or pending
            or not one(db, "SELECT 1 FROM informes WHERE solicitud_id=:id", id=rid)
        ):
            raise AppError(
                409,
                "Completa al menos un ensayo, define los ensayos de todas las muestras, resuelve el trabajo pendiente y carga un informe antes de cerrar.",
            )
    execute(db, "UPDATE solicitudes SET estado_solicitud=:status WHERE id=:id", status=new, id=rid)
    if data.action == "close":
        execute(db, "UPDATE solicitudes SET estado_general='CLOSED' WHERE id=:id", id=rid)
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


def review_assays(db, user, rid, data):
    require_role(user, "MANAGER")
    r = request_access(db, user, rid, data.version)
    if r["status"] not in ("WAITING_ASSAYS", "SUBMITTED", "APPROVED"):
        raise AppError(409, "La solicitud debe estar enviada y abierta para revisar sus ensayos.")
    ids = [x.task_id for x in data.decisions]
    if len(set(ids)) != len(ids):
        raise AppError(400, "Ensayos repetidos en la revisión.")
    for decision in data.decisions:
        t = one(
            db,
            "SELECT a.* FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE a.id=:id AND s.solicitud_id=:rid",
            id=decision.task_id,
            rid=rid,
        )
        if not t:
            raise AppError(404, "Ensayo no encontrado en esta solicitud.")
        if (
            t["review_status"] != "PENDING"
            or t["state"] != "PENDING"
            or t["technician_id"]
            or t["started_at"]
        ):
            raise AppError(409, "Solo se pueden revisar ensayos pendientes sin trabajo registrado.")
    for decision in data.decisions:
        execute(
            db,
            "UPDATE ensayos_muestra SET estado_revision=:state WHERE id=:id",
            state=decision.decision,
            id=decision.task_id,
        )
        audit(
            db,
            user,
            "Ensayo aprobado por jefatura"
            if decision.decision == "APPROVED"
            else "Ensayo rechazado por jefatura",
            rid,
            {
                "task_id": decision.task_id,
                "action": "review",
                "from": "PENDING",
                "to": decision.decision,
                "reason": decision.reason,
            },
            internal=False,
        )
    statuses = {
        t["review_status"]
        for t in rows(
            db,
            "SELECT a.estado_revision FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id WHERE s.solicitud_id=:rid",
            rid=rid,
        )
    }
    new = "APPROVED" if "APPROVED" in statuses else "OBSERVED" if statuses == {"REJECTED"} else r["status"]
    execute(db, "UPDATE solicitudes SET estado_solicitud=:state WHERE id=:id", state=new, id=rid)
    touch(db, rid)
    if new != r["status"]:
        audit(
            db,
            user,
            "Solicitud aprobada"
            if new == "APPROVED"
            else "Solicitud observada; todos los ensayos fueron rechazados",
            rid,
            {"from": r["status"], "to": new},
            internal=False,
        )


def resubmit_assays(db, user, rid, data):
    require_role(user, "CLIENT")
    r = request_access(db, user, rid, data.version)
    if not client_request(user, r) or r["status"] not in (
        "WAITING_ASSAYS",
        "SUBMITTED",
        "OBSERVED",
        "APPROVED",
    ):
        raise AppError(409, "Solo el autor puede volver a solicitar ensayos de una solicitud abierta.")
    if len(set(data.task_ids)) != len(data.task_ids):
        raise AppError(400, "Ensayos repetidos.")
    for tid in data.task_ids:
        t = one(
            db,
            "SELECT a.*,c.activo FROM ensayos_muestra a JOIN muestras s ON s.id=a.muestra_id JOIN catalogo_ensayos c ON c.id=a.ensayo_id WHERE a.id=:id AND s.solicitud_id=:rid",
            id=tid,
            rid=rid,
        )
        if not t:
            raise AppError(404, "Ensayo no encontrado en esta solicitud.")
        if (
            t["review_status"] != "REJECTED"
            or t["state"] != "PENDING"
            or t["technician_id"]
            or t["started_at"]
        ):
            raise AppError(409, "Solo puedes volver a solicitar ensayos rechazados sin trabajo registrado.")
        if not t["active"]:
            raise AppError(409, "El ensayo ya no está habilitado en el catálogo.")
    for tid in data.task_ids:
        execute(db, "UPDATE ensayos_muestra SET estado_revision='PENDING' WHERE id=:id", id=tid)
        audit(
            db,
            user,
            "Ensayo solicitado nuevamente",
            rid,
            {"task_id": tid, "action": "resubmit", "from": "REJECTED", "to": "PENDING"},
            internal=False,
        )
    if r["status"] == "OBSERVED":
        execute(
            db,
            "UPDATE solicitudes SET estado_solicitud=:state WHERE id=:id",
            state="WAITING_ASSAYS" if missing_assays(db, rid) else "SUBMITTED",
            id=rid,
        )
    touch(db, rid)


def reception(db, user, rid, data):
    require_role(user, "MANAGER", "TECH")
    request = laboratory_access(db, user, rid, data.version)
    if request["status"] not in ("WAITING_ASSAYS", "SUBMITTED", "OBSERVED", "APPROVED"):
        raise AppError(409, "Envía la solicitud antes de registrar su recepción.")
    if "MANAGER" not in user["roles"]:
        require_approved(request)
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
            "UPDATE muestras SET recibido_en=:at,recibido_por=:uid,transporte=:transport,\n            cantidad_recibida=:received_quantity,peso_recibido=:received_weight,condicion=:condition,observaciones_recepcion=:reception_notes,\n            codigo_recepcion=:codigo_recepcion,codigo_laboratorio=:codigo_laboratorio WHERE id=:sample_id",
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
                        "received_weight",
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
    request = laboratory_access(db, user, rid, data.version)
    require_approved(request)
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
        if data.action not in allowed_actions(user, task, "APPROVED", request["codigo_ot"]):
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
            {"observe": "Ensayo observado", "cancel": "Ensayo cancelado"}.get(
                data.action, "Ensayo actualizado"
            ),
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
            internal=data.action not in ("observe", "cancel"),
        )
    touch(db, rid)
    return {"ok": True}


def work_order(db, user, rid, data):
    require_role(user, "MANAGER")
    r = laboratory_access(db, user, rid, data.version)
    if r["status"] not in ("WAITING_ASSAYS", "SUBMITTED", "OBSERVED", "APPROVED"):
        raise AppError(409, "La solicitud debe estar enviada y abierta.")
    if not one(db, "SELECT 1 FROM muestras WHERE solicitud_id=:id AND recibido_en IS NOT NULL", id=rid):
        raise AppError(409, "Recibe al menos una muestra antes de generar la OT.")
    if r["codigo_ot"] and not data.reason:
        raise AppError(400, "Corregir una OT requiere motivo.")
    execute(db, "UPDATE solicitudes SET codigo_ot=:code WHERE id=:id", code=data.codigo_ot, id=rid)
    touch(db, rid)
    audit(
        db,
        user,
        "OT registrada: " + data.codigo_ot + (" · " + data.reason if data.reason else ""),
        rid,
        {"previous_ot": r["codigo_ot"], "codigo_ot": data.codigo_ot, "reason": data.reason},
        internal=False,
    )
