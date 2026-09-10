import { useEffect, useState } from "react";
import { api, messageOf } from "../services/api";
import { Badge, Button, Field, ErrorBox, Empty, fmtDate } from "./ui";
export default function WorkPanel({ request, user, onDone, bulk = false }) {
  const [selected, setSelected] = useState([]),
    [technicians, setTechnicians] = useState([]),
    [action, setAction] = useState(
      user.roles.includes("MANAGER") ? "assign" : "start",
    ),
    [tech, setTech] = useState(""),
    [start, setStart] = useState(""),
    [end, setEnd] = useState(""),
    [reason, setReason] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const staff = user.roles.some((r) => ["TECH", "MANAGER"].includes(r)),
    manager = user.roles.includes("MANAGER");
  const chosen = request.tasks.filter((t) => selected.includes(t.id));
  const actions = chosen.length
    ? (chosen[0].allowed_actions || []).filter((a) =>
        chosen.every((t) => t.allowed_actions?.includes(a)),
      )
    : [];
  const effectiveAction = actions.includes(action) ? action : actions[0] || "";
  const selectable = request.tasks.filter((t) => t.allowed_actions?.length);
  useEffect(() => {
    if (manager)
      api
        .get("/technicians")
        .then((r) => setTechnicians(r.data))
        .catch((e) => setError(messageOf(e)));
  }, [manager]);
  async function apply() {
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post(
        bulk ? "/work" : `/requests/${request.id}/tasks`,
        {
          ...(bulk
            ? {
                requests: Object.values(
                  request.tasks
                    .filter((t) => selected.includes(t.id))
                    .reduce((acc, t) => {
                      acc[t.request_id] ??= {
                        request_id: t.request_id,
                        version: t.request_version,
                        task_ids: [],
                      };
                      acc[t.request_id].task_ids.push(t.id);
                      return acc;
                    }, {}),
                ),
              }
            : { version: request.version, task_ids: selected }),
          action: effectiveAction,
          technician_id: tech || null,
          planned_start: start || null,
          planned_end: end || null,
          reason,
        },
      );
      onDone(data);
      setSelected([]);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <ErrorBox>{error}</ErrorBox>
      <div className="card-title">
        <h2>Ensayos y programación</h2>
        <span className="muted">{request.tasks.length + " ensayos"}</span>
      </div>
      {request.tasks.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {staff && (
                  <th>
                    <input
                      aria-label="Seleccionar todos"
                      type="checkbox"
                      disabled={!selectable.length}
                      checked={
                        selectable.length > 0 &&
                        selected.length === selectable.length
                      }
                      onChange={(e) =>
                        setSelected(
                          e.target.checked ? selectable.map((t) => t.id) : [],
                        )
                      }
                    />
                  </th>
                )}
                <th>Muestra / ensayo</th>
                <th>Estado</th>
                <th>Técnico</th>
                <th>Programación</th>
                <th>Inicio / fin real</th>
              </tr>
            </thead>
            <tbody>
              {request.tasks.map((t) => (
                <tr key={t.id}>
                  {staff && (
                    <td>
                      <input
                        aria-label={`Seleccionar ${t.sample_code} ${t.assay_name || t.name}`}
                        disabled={!t.allowed_actions?.length}
                        type="checkbox"
                        checked={selected.includes(t.id)}
                        onChange={(e) =>
                          setSelected(
                            e.target.checked
                              ? [...selected, t.id]
                              : selected.filter((id) => id !== t.id),
                          )
                        }
                      />
                    </td>
                  )}
                  <td>
                    <b>{t.sample_code}</b>
                    {bulk && (
                      <small className="block">
                        {t.request_code} · {t.project_code}
                      </small>
                    )}
                    <small className="block">
                      Material: <Badge state={t.condition} />
                    </small>
                    <small className="block">{t.assay_name || t.name}</small>
                  </td>
                  <td>
                    <Badge state={t.state} />
                  </td>
                  <td>{t.technician_name || "Sin asignar"}</td>
                  <td>
                    {fmtDate(t.planned_start)}
                    <small className="block">{fmtDate(t.planned_end)}</small>
                  </td>
                  <td>
                    {fmtDate(t.started_at)}
                    <small className="block">{fmtDate(t.completed_at)}</small>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty>No hay ensayos con estos filtros.</Empty>
      )}
      {staff && selected.length > 0 && request.status !== "CLOSED" && (
        <div className="bulk-panel">
          <b>{selected.length} ensayos seleccionados</b>
          <div className="form-grid">
            <Field label="Acción">
              <select
                value={effectiveAction}
                onChange={(e) => setAction(e.target.value)}
              >
                {[
                  ["assign", "Asignar / programar"],
                  ["cancel", "Cancelar con motivo"],
                  ["resume", "Retomar observado"],
                  ["start", "Iniciar"],
                  ["observe", "Observar"],
                  ["complete", "Completar"],
                ]
                  .filter(([v]) => actions.includes(v))
                  .map(([v, t]) => (
                    <option key={v} value={v}>
                      {t}
                    </option>
                  ))}
              </select>
            </Field>
            {effectiveAction === "assign" && (
              <Field label="Técnico">
                <select value={tech} onChange={(e) => setTech(e.target.value)}>
                  <option value="">Seleccionar</option>
                  {technicians.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </Field>
            )}
          </div>
          {effectiveAction === "assign" && (
            <div className="form-grid">
              <Field label="Inicio previsto">
                <input
                  type="date"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                />
              </Field>
              <Field label="Fin previsto">
                <input
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                />
              </Field>
            </div>
          )}
          <Field label="Motivo / nota interna">
            <input value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
          {!actions.length && (
            <p role="status">
              La selección combina ensayos sin acciones comunes. Selecciona un
              grupo compatible.
            </p>
          )}
          <Button
            variant="primary"
            busy={busy}
            disabled={!effectiveAction}
            onClick={apply}
          >
            Aplicar a seleccionados
          </Button>
        </div>
      )}
    </>
  );
}
