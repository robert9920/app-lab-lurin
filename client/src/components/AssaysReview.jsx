import { useState } from "react";
import useErrorNotice from "../hooks/useErrorNotice";
import { api, messageOf } from "../services/api";
import { Modal, Button, ErrorBox } from "./ui";

export default function AssaysReview({ request, onDone, onClose }) {
  const tasks = request.tasks.filter((t) => t.can_review);
  const [decisions, setDecisions] = useState({}),
    [attempted, setAttempted] = useState(false),
    [busy, setBusy] = useState(false);
  const [error, setError] = useErrorNotice();
  function update(id, key, value) {
    setDecisions((old) => ({ ...old, [id]: { ...old[id], [key]: value } }));
  }
  const selected = tasks.filter((t) => decisions[t.id]?.decision);
  async function save(e) {
    e.preventDefault();
    if (busy || !selected.length) return;
    setAttempted(true);
    if (
      selected.some(
        (t) =>
          decisions[t.id].decision === "REJECTED" &&
          !decisions[t.id].reason?.trim(),
      )
    ) {
      setError("Indica el motivo de cada ensayo que rechazas.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post(`/requests/${request.id}/assays/review`, {
        version: request.version,
        decisions: selected.map((t) => ({
          task_id: t.id,
          decision: decisions[t.id].decision,
          reason: decisions[t.id].reason || "",
        })),
      });
      onDone(data);
      onClose();
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Revisar ensayos" onClose={() => !busy && onClose()}>
      <form className="review-form" noValidate onSubmit={save}>
        <p>
          Elige una decisión para cada ensayo que quieras revisar. Los demás
          seguirán pendientes.
        </p>
        <ErrorBox>{error}</ErrorBox>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Muestra / ensayo</th>
                <th>Decisión</th>
                <th>Motivo</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id}>
                  <td>
                    <b>{t.sample_code}</b>
                    <small className="block">{t.name || t.assay_name}</small>
                  </td>
                  <td>
                    <select
                      disabled={busy}
                      aria-label={`Decisión · ${t.sample_code} · ${t.name || t.assay_name}`}
                      value={decisions[t.id]?.decision || ""}
                      onChange={(e) => update(t.id, "decision", e.target.value)}
                    >
                      <option value="">Sin decisión</option>
                      <option value="APPROVED">Aprobar</option>
                      <option value="REJECTED">Rechazar</option>
                    </select>
                  </td>
                  <td>
                    <textarea
                      disabled={busy || !decisions[t.id]?.decision}
                      aria-invalid={
                        attempted &&
                        decisions[t.id]?.decision === "REJECTED" &&
                        !decisions[t.id]?.reason?.trim()
                      }
                      aria-label={`Motivo · ${t.sample_code} · ${t.name || t.assay_name}`}
                      maxLength={3000}
                      placeholder={
                        decisions[t.id]?.decision === "REJECTED"
                          ? "Obligatorio al rechazar"
                          : "Opcional"
                      }
                      value={decisions[t.id]?.reason || ""}
                      onChange={(e) => update(t.id, "reason", e.target.value)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="form-actions">
          <Button type="button" disabled={busy} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            busy={busy}
            disabled={!selected.length}
          >
            Guardar decisiones ({selected.length})
          </Button>
        </div>
      </form>
    </Modal>
  );
}
