import useErrorNotice from "../hooks/useErrorNotice";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, messageOf } from "../services/api";
import { PageHead, Button, ErrorBox } from "./ui";

export default function AssaysEditor({ request, catalog }) {
  const navigate = useNavigate();
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
  const columns = catalog.filter(
    (a) => a.active || samples.some((s) => s.assay_ids.includes(a.id)),
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
        <div className="table-scroll assay-edit-matrix">
          <table>
            <thead>
              <tr>
                <th>Muestra</th>
                {columns.map((a) => (
                  <th key={a.id}>{a.name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {samples.map((s) => (
                <tr key={s.id}>
                  <td>
                    <b>{s.client_code}</b>
                    <small className="block">{s.material}</small>
                  </td>
                  {columns.map((a) => (
                    <td key={a.id}>
                      <input
                        type="checkbox"
                        aria-label={`${a.name} · ${s.client_code}`}
                        checked={s.assay_ids.includes(a.id)}
                        disabled={
                          busy ||
                          locked(s.id, a.id) ||
                          (!a.active && !s.assay_ids.includes(a.id))
                        }
                        onChange={(e) =>
                          setSamples((old) =>
                            old.map((row) =>
                              row.id !== s.id
                                ? row
                                : {
                                    ...row,
                                    assay_ids: e.target.checked
                                      ? [...row.assay_ids, a.id]
                                      : row.assay_ids.filter((v) => v !== a.id),
                                  },
                            ),
                          )
                        }
                      />
                      {locked(s.id, a.id) && (
                        <small className="block">
                          {request.tasks.find(
                            (t) => t.sample_id === s.id && t.assay_id === a.id,
                          )?.approved
                            ? "Aprobado"
                            : "Rechazado"}
                        </small>
                      )}
                    </td>
                  ))}
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
    </>
  );
}
