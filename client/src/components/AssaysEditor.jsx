import AssayPicker, { SelectedAssays } from "./AssayPicker";
import useErrorNotice from "../hooks/useErrorNotice";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, messageOf } from "../services/api";
import { PageHead, Button, ErrorBox } from "./ui";

export default function AssaysEditor({ request, catalog }) {
  const navigate = useNavigate();
  const [picker, setPicker] = useState(null);
  const [selectedSamples, setSelectedSamples] = useState([]);
  const [samples, setSamples] = useState(request.samples),
    [busy, setBusy] = useState(false),
    [error, setError] = useErrorNotice();
  const locked = (sid, aid) =>
    request.tasks.some(
      (t) =>
        t.sample_id === sid &&
        t.assay_id === aid &&
        t.review_status !== "PENDING",
    );
  async function save() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await api.put(`/requests/${request.id}/assays`, {
        version: request.version,
        samples: samples.map((s) => ({
          sample_id: s.id,
          assay_ids: s.assay_ids,
        })),
      });
      navigate(`/requests/${request.id}`);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Link className="back-link" to={`/requests/${request.id}`}>
        ← Volver a la solicitud
      </Link>
      <PageHead
        title="Solicitar ensayos"
        eyebrow={request.code}
        description="Los ensayos revisados están protegidos. Jefatura revisará los nuevos sin detener los que ya están en curso. Para reenviar un ensayo rechazado usa Volver a solicitar en la pestaña Ensayos."
      />
      <ErrorBox>{error}</ErrorBox>
      <section className="card form-card">
        <div className="sample-toolbar">
          <span>{selectedSamples.length} muestras seleccionadas</span>
          <Button
            disabled={busy || !selectedSamples.length}
            onClick={() => setPicker(selectedSamples)}
          >
            Añadir ensayo a seleccionadas
          </Button>
        </div>
        <div className="table-scroll assay-edit-matrix assay-selector-table">
          <table>
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    aria-label="Seleccionar todas las muestras"
                    checked={selectedSamples.length === samples.length}
                    onChange={(e) =>
                      setSelectedSamples(
                        e.target.checked ? samples.map((s) => s.id) : [],
                      )
                    }
                  />
                </th>
                <th>Muestra</th>
                <th>Ensayos solicitados</th>
              </tr>
            </thead>
            <tbody>
              {samples.map((s) => (
                <tr key={s.id}>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Seleccionar muestra ${s.client_code}`}
                      checked={selectedSamples.includes(s.id)}
                      onChange={(e) =>
                        setSelectedSamples((old) =>
                          e.target.checked
                            ? [...old, s.id]
                            : old.filter((id) => id !== s.id),
                        )
                      }
                    />
                  </td>
                  <td>
                    <b>{s.client_code}</b>
                    <small className="block">{s.material}</small>
                  </td>
                  <td className="sample-assays-column">
                    <SelectedAssays
                      ids={s.assay_ids}
                      catalog={catalog}
                      locked={s.assay_ids.filter((aid) => locked(s.id, aid))}
                      onRemove={(aid) => {
                        if (!busy)
                          setSamples((old) =>
                            old.map((row) =>
                              row.id === s.id
                                ? {
                                    ...row,
                                    assay_ids: row.assay_ids.filter(
                                      (id) => id !== aid,
                                    ),
                                  }
                                : row,
                            ),
                          );
                      }}
                    />
                    <Button disabled={busy} onClick={() => setPicker([s.id])}>
                      Añadir ensayo
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="form-actions">
          <Button variant="primary" busy={busy} onClick={save}>
            Guardar ensayos para revisión
          </Button>
        </div>
      </section>
      {picker && (
        <AssayPicker
          catalog={catalog}
          existing={catalog
            .filter((a) =>
              picker.every((sid) =>
                samples.find((s) => s.id === sid).assay_ids.includes(a.id),
              ),
            )
            .map((a) => a.id)}
          onClose={() => setPicker(null)}
          onApply={(ids) => {
            if (
              samples.some(
                (s) =>
                  picker.includes(s.id) &&
                  new Set([...s.assay_ids, ...ids]).size > 40,
              )
            )
              throw new Error("Máximo 40 ensayos por muestra.");
            setSamples((old) =>
              old.map((s) =>
                picker.includes(s.id)
                  ? { ...s, assay_ids: [...new Set([...s.assay_ids, ...ids])] }
                  : s,
              ),
            );
          }}
        />
      )}
    </>
  );
}
