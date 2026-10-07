import useErrorNotice from "../hooks/useErrorNotice";
import NumericInput from "./NumericInput";
import { useState } from "react";
import { api, messageOf } from "../services/api";
import { Badge, Button, Field, ErrorBox, labels } from "./ui";
export default function ReceptionForm({ request, onDone }) {
  const eligible = request.samples.filter((s) => s.can_receive);
  const initial = new Date(Date.now() - 5 * 3600000).toISOString().slice(0, 16);
  const [at, setAt] = useState(initial),
    [transport, setTransport] = useState(""),
    [receiptCode, setReceiptCode] = useState(""),
    [reason, setReason] = useState(""),
    [selected, setSelected] = useState([]),
    [error, setError] = useErrorNotice(),
    [busy, setBusy] = useState(false);
  const [samples, setSamples] = useState(
    eligible.map((s) => ({
      sample_id: s.id,
      codigo_recepcion: s.codigo_recepcion || "",
      codigo_laboratorio: s.codigo_laboratorio || "",
      condition: s.condition === "NOT_RECEIVED" ? "OK" : s.condition,
      received_quantity: s.received_quantity ?? "",
      received_weight: s.received_weight ?? "",
      reception_notes: s.reception_notes,
    })),
  );
  function edit(id, key, value) {
    setSamples(
      samples.map((s) => (s.sample_id === id ? { ...s, [key]: value } : s)),
    );
  }
  const correcting = eligible.some(
    (s) => selected.includes(s.id) && s.received_at,
  );
  async function submit(e) {
    e.preventDefault();
    setError("");
    for (const s of samples.filter((s) => selected.includes(s.sample_id))) {
      const weight = Number(s.received_weight);
      if (
        s.received_weight !== "" &&
        s.received_weight != null &&
        (!Number.isFinite(weight) ||
          weight <= 0 ||
          Math.abs(weight * 10 - Math.round(weight * 10)) > 1e-8)
      ) {
        setError(
          "Peso recibido: utiliza un valor positivo con máximo un decimal.",
        );
        return;
      }
    }
    setBusy(true);
    try {
      const { data } = await api.post(
        "/requests/" + request.id + "/receptions",
        {
          version: request.version,
          received_at: new Date(at + "-05:00").toISOString(),
          transport,
          reason,
          samples: samples
            .filter((s) => selected.includes(s.sample_id))
            .map((s) => ({
              ...s,
              received_quantity:
                s.received_quantity === "" ? null : Number(s.received_quantity),
              received_weight:
                s.received_weight === "" ? null : String(s.received_weight),
            })),
        },
      );
      onDone(data);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit}>
      <h2>Registrar recepción</h2>
      <p className="muted">
        Selecciona las muestras recibidas. La fecha/hora y el transporte se
        aplican a las filas seleccionadas. Para distintas fechas, guarda cada
        grupo por separado.
      </p>
      <ErrorBox>{error}</ErrorBox>
      <div className="form-grid">
        <Field label="Fecha y hora de recepción (Lima)">
          <input
            type="datetime-local"
            required
            value={at}
            onChange={(e) => setAt(e.target.value)}
          />
        </Field>
        <Field label="Código de recepción común (opcional)">
          <input
            maxLength={60}
            value={receiptCode}
            onChange={(e) => {
              setReceiptCode(e.target.value);
              setSamples((current) =>
                current.map((s) =>
                  selected.includes(s.sample_id)
                    ? { ...s, codigo_recepcion: e.target.value }
                    : s,
                ),
              );
            }}
            placeholder="REC-26-024"
          />
        </Field>
        <Field label="Transporte">
          <input
            maxLength={200}
            value={transport}
            onChange={(e) => setTransport(e.target.value)}
            placeholder="Empresa, vehículo o persona que entrega"
          />
        </Field>
      </div>
      {eligible.map((original) => {
        const s = samples.find((x) => x.sample_id === original.id),
          checked = selected.includes(original.id);
        return (
          <div className="sample-editor" key={s.sample_id}>
            <label className="check-label">
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) => {
                  if (e.target.checked && receiptCode)
                    edit(s.sample_id, "codigo_recepcion", receiptCode);
                  setSelected(
                    e.target.checked
                      ? [...selected, s.sample_id]
                      : selected.filter((id) => id !== s.sample_id),
                  );
                }}
              />
              <b>{original.client_code}</b> · {original.material}{" "}
              <Badge state={original.condition} />
            </label>
            <p className="muted">
              Declarado: {original.quantity ?? "Sin dato"} recipientes ·{" "}
              {original.weight ?? "Sin dato"} kg
            </p>
            {original.received_at && (
              <p className="muted">
                Última recepción:{" "}
                {new Date(original.received_at).toLocaleString("es-PE", {
                  timeZone: "America/Lima",
                })}{" "}
                · {original.transport || "Sin transporte"}
              </p>
            )}
            {checked && (
              <div className="form-grid">
                <Field label="Código de recepción">
                  <input
                    required
                    maxLength={60}
                    value={s.codigo_recepcion}
                    onChange={(e) =>
                      edit(s.sample_id, "codigo_recepcion", e.target.value)
                    }
                  />
                </Field>
                <Field label="Código de laboratorio">
                  <input
                    required
                    maxLength={60}
                    value={s.codigo_laboratorio}
                    onChange={(e) =>
                      edit(s.sample_id, "codigo_laboratorio", e.target.value)
                    }
                    placeholder="M-26-024-001"
                  />
                </Field>
                <Field label="Recipientes recibidos (opcional)">
                  <NumericInput
                    integer
                    increment={1}
                    type="number"
                    step="1"
                    min="1"
                    value={s.received_quantity}
                    onChange={(e) =>
                      edit(s.sample_id, "received_quantity", e.target.value)
                    }
                    placeholder="Desconocida"
                  />
                </Field>
                <Field label="Peso recibido (kg, opcional)">
                  <NumericInput
                    increment={0.1}
                    type="number"
                    min="0.1"
                    step="any"
                    value={s.received_weight}
                    onChange={(e) =>
                      edit(s.sample_id, "received_weight", e.target.value)
                    }
                    placeholder="Desconocido"
                  />
                </Field>
                <Field label="Condición">
                  <select
                    value={s.condition}
                    onChange={(e) =>
                      edit(s.sample_id, "condition", e.target.value)
                    }
                  >
                    {["OK", "OBSERVED", "DAMAGED", "INSUFFICIENT"].map((v) => (
                      <option key={v} value={v}>
                        {labels[v]}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Observaciones de recepción">
                  <textarea
                    required={s.condition !== "OK"}
                    maxLength={3000}
                    value={s.reception_notes}
                    onChange={(e) =>
                      edit(s.sample_id, "reception_notes", e.target.value)
                    }
                  />
                </Field>
              </div>
            )}
          </div>
        );
      })}
      {correcting && (
        <Field label="Motivo de la corrección">
          <textarea
            required
            maxLength={3000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </Field>
      )}
      <div className="form-actions">
        <span>{selected.length} muestras seleccionadas</span>
        <Button variant="primary" busy={busy} disabled={!selected.length}>
          Guardar recepción
        </Button>
      </div>
    </form>
  );
}
