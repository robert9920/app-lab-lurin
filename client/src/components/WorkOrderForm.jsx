import { useState } from "react";
import { api, messageOf } from "../services/api";
import { Button, Field, ErrorBox } from "./ui";
export default function WorkOrderForm({ request, onDone }) {
  const [code, setCode] = useState(request.codigo_ot || ""),
    [reason, setReason] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [editing, setEditing] = useState(false);
  const received = request.samples.some((s) => s.received_at);
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await api.post(`/requests/${request.id}/work-order`, {
        version: request.version,
        codigo_ot: code,
        reason,
      });
      onDone(r.data);
      setEditing(false);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="ot-panel">
      <div className="card-title">
        <h2>Orden de trabajo</h2>
        <b>{request.codigo_ot || "Sin OT"}</b>
      </div>
      <ErrorBox>{error}</ErrorBox>
      {!received ? (
        <p>Registra la llegada de al menos una muestra para generar la OT.</p>
      ) : !editing ? (
        <>
          <p className="muted">
            Puedes registrar la OT aunque falten muestras o existan
            observaciones. Cada ensayo requiere material conforme para
            iniciarse.
          </p>
          <Button onClick={() => setEditing(true)}>
            {request.codigo_ot ? "Corregir OT" : "Generar OT"}
          </Button>
        </>
      ) : (
        <form onSubmit={save}>
          <div className="form-grid">
            <Field label="Código OT *">
              <input
                required
                maxLength={60}
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </Field>
            {request.codigo_ot && (
              <Field label="Motivo de la corrección *">
                <input
                  required
                  maxLength={3000}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </Field>
            )}
          </div>
          <div className="actions">
            <Button type="button" onClick={() => setEditing(false)}>
              Cancelar
            </Button>
            <Button busy={busy} variant="primary">
              Guardar OT
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}
