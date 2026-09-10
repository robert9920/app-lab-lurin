import { useState, useEffect } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, messageOf, download, fetchPdf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { safeReturn } from "../services/navigation";
import {
  PageHead,
  Badge,
  Button,
  Field,
  ErrorBox,
  Empty,
  fmtDate,
} from "../components/ui";
import ReceptionForm from "../components/ReceptionForm";
import WorkPanel from "../components/WorkPanel";
import ReportUpload from "../components/ReportUpload";
export default function RequestDetail() {
  const { id } = useParams(),
    { user } = useAuth(),
    [params, setParams] = useSearchParams();
  const [r, setR] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [reason, setReason] = useState(""),
    [comment, setComment] = useState(""),
    [internal, setInternal] = useState(false),
    [labelIds, setLabelIds] = useState([]);
  const staff = user.roles.some((x) => ["TECH", "MANAGER"].includes(x)),
    manager = user.roles.includes("MANAGER"),
    canWrite = staff || user.roles.includes("CLIENT"),
    canRequest = user.roles.includes("CLIENT");
  const tab = ["summary", "reception", "work", "documents", "history"].includes(
    params.get("tab"),
  )
    ? params.get("tab")
    : "summary";
  useEffect(() => {
    let active = true;
    api
      .get("/requests/" + id)
      .then((x) => {
        if (active) setR(x.data);
      })
      .catch((e) => {
        if (active) setError(messageOf(e));
      });
    return () => {
      active = false;
    };
  }, [id]);
  async function act(action) {
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/requests/" + id + "/actions", {
        version: r.version,
        action,
        reason,
      });
      setR(data);
      setReason("");
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  async function addComment(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/requests/" + id + "/comments", {
        version: r.version,
        body: comment,
        internal,
      });
      setR(data);
      setComment("");
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  async function print(kind) {
    try {
      await fetchPdf(
        "/requests/" +
          id +
          "/print/" +
          kind +
          (kind === "labels" ? "?sample_ids=" + labelIds.join(",") : ""),
        kind + ".pdf",
      );
    } catch (e) {
      setError(messageOf(e));
    }
  }
  const back = safeReturn(params.get("from"));
  return (
    <>
      <Link className="back-link" to={back}>
        ← Volver a la lista
      </Link>
      <ErrorBox>{error}</ErrorBox>
      {r ? (
        <>
          <PageHead
            eyebrow={r.code + " · " + r.project.code}
            title={r.title}
            description={r.project.name}
          >
            <Badge state={r.status} />
          </PageHead>
          <div className="tabs">
            {[
              ["summary", "Resumen y muestras"],
              ["reception", "Recepción"],
              ["work", "Ensayos"],
              ["documents", "Documentos"],
              ["history", "Historial"],
            ].map(([key, name]) => (
              <button
                key={key}
                className={tab === key ? "active" : ""}
                onClick={() => {
                  const p = new URLSearchParams(params);
                  p.set("tab", key);
                  setParams(p);
                }}
              >
                {name}
              </button>
            ))}
          </div>
          <section className={"card form-card" + (tab === "summary" ? " request-summary" : "")}>
            {tab === "summary" && (
              <>
                <div className="summary-heading">
                  <h2>Solicitud y muestras</h2>
                  {canRequest && ["DRAFT", "OBSERVED"].includes(r.status) && (
                    <Link className="btn" to={"/requests/" + id + "/edit"}>
                      Editar solicitud
                    </Link>
                  )}
                </div>
                {r.notes && <p>{r.notes}</p>}
                <p className="muted">
                  Fecha objetivo: {fmtDate(r.target_date)} · Versión {r.version}
                </p>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Muestra</th>
                        <th>Material / cantidad</th>
                        <th>Ensayos solicitados</th>
                        <th>Recepción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {r.samples.map((s) => (
                        <tr key={s.id}>
                          <td>
                            <b>{s.client_code}</b>
                            <small className="block">
                              {s.borehole} · {s.notes}
                            </small>
                          </td>
                          <td>
                            {s.material}
                            <small className="block">
                              {s.quantity ?? "No informada"} {s.unit}
                            </small>
                          </td>
                          <td>
                            {r.tasks
                              .filter((t) => t.sample_id === s.id)
                              .map((t) => t.assay_name || t.name)
                              .join(", ")}
                          </td>
                          <td>
                            <Badge state={s.condition} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="form-actions">
                  {canRequest && ["DRAFT", "OBSERVED"].includes(r.status) && (
                    <Button
                      variant="primary"
                      busy={busy}
                      onClick={() => act("submit")}
                    >
                      Enviar al laboratorio
                    </Button>
                  )}
                  {manager && r.status === "SUBMITTED" && (
                    <>
                      <Field label="Motivo (observar o rechazar)">
                        <input
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                        />
                      </Field>
                      <Button
                        busy={busy}
                        disabled={!reason.trim()}
                        onClick={() => act("observe")}
                      >
                        Observar
                      </Button>
                      <Button
                        busy={busy}
                        disabled={!reason.trim()}
                        onClick={() => act("reject")}
                      >
                        Rechazar
                      </Button>
                      <Button
                        busy={busy}
                        variant="primary"
                        onClick={() => act("approve")}
                      >
                        Aprobar
                      </Button>
                    </>
                  )}
                  {manager && r.status === "APPROVED" && (
                    <Button busy={busy} onClick={() => act("close")}>
                      Cerrar servicio
                    </Button>
                  )}
                </div>
              </>
            )}
            {tab === "reception" && (
              <>
                {(manager || r.samples.some((s) => s.can_receive)) && r.status === "APPROVED" ? (
                  <ReceptionForm key={r.version} request={r} onDone={setR} />
                ) : (
                  <>
                    <h2>Estado de recepción</h2>
                    {r.samples.map((s) => (
                      <div className="due-row" key={s.id}>
                        <div>
                          <b>{s.client_code}</b>
                          <p>{s.reception_notes}</p>
                          <small>
                            {fmtDate(s.received_at && s.can_receive)} · {s.transport}
                          </small>
                        </div>
                        <Badge state={s.condition} />
                      </div>
                    ))}
                  </>
                )}
                {staff && (manager || r.samples.some((s) => s.can_receive)) && (
                  <fieldset className="label-picker">
                    <legend>Seleccionar etiquetas · 95 × 68 mm · A4</legend>
                    <label className="check-label">
                      <input
                        type="checkbox"
                        checked={
                          r.samples.some((s) => s.received_at && s.can_receive) &&
                          labelIds.length ===
                            r.samples.filter((s) => s.received_at && s.can_receive).length
                        }
                        onChange={(e) =>
                          setLabelIds(
                            e.target.checked
                              ? r.samples
                                  .filter((s) => s.received_at && s.can_receive)
                                  .map((s) => s.id)
                              : [],
                          )
                        }
                      />
                      Todas las muestras recibidas
                    </label>
                    {r.samples
                      .filter((s) => s.received_at && s.can_receive)
                      .map((s) => (
                        <label className="check-label" key={s.id}>
                          <input
                            type="checkbox"
                            checked={labelIds.includes(s.id)}
                            onChange={(e) =>
                              setLabelIds(
                                e.target.checked
                                  ? [...labelIds, s.id]
                                  : labelIds.filter((id) => id !== s.id),
                              )
                            }
                          />
                          {s.client_code} · {s.codigo_laboratorio}
                        </label>
                      ))}
                    <p className="muted">
                      Dos columnas, ocho etiquetas por hoja. Imprime a tamaño
                      real (100 %).
                    </p>
                  </fieldset>
                )}
                {staff && (manager || r.samples.some((s) => s.can_receive)) && (
                  <div className="form-actions">
                    <Button onClick={() => print("receipt")}>
                      Descargar acta actual
                    </Button>
                    <Button
                      disabled={!labelIds.length}
                      onClick={() => print("labels")}
                    >
                      Imprimir etiquetas
                    </Button>
                  </div>
                )}
              </>
            )}
            {tab === "work" && (
              <WorkPanel request={r} user={user} onDone={setR} />
            )}{" "}
            {tab === "documents" && (
              <>
                <h2>Informes PDF</h2>
                <p className="muted">
                  Cada carga conserva una versión y queda disponible
                  inmediatamente para las personas autorizadas del proyecto.
                </p>
                {(manager || r.samples.some((s) => s.can_receive)) && r.status === "APPROVED" && (
                  <ReportUpload
                    request={r}
                    onDone={() =>
                      api.get("/requests/" + id).then((x) => setR(x.data))
                    }
                  />
                )}{" "}
                {r.reports.length ? (
                  r.reports.map((d) => (
                    <div className="due-row" key={d.id}>
                      <div>
                        <b>
                          {d.name} · Versión {d.version}
                        </b>
                        <small className="block">
                          {fmtDate(d.created_at)} ·{" "}
                          {(d.bytes / 1024).toFixed(0)} KB
                        </small>
                      </div>
                      <div className="actions">
                        <Button
                          onClick={() =>
                            download(d.id, d.name, true).catch((e) =>
                              setError(messageOf(e)),
                            )
                          }
                        >
                          Ver PDF
                        </Button>
                        <Button
                          onClick={() =>
                            download(d.id, d.name).catch((e) =>
                              setError(messageOf(e)),
                            )
                          }
                        >
                          Descargar
                        </Button>
                      </div>
                    </div>
                  ))
                ) : (
                  <Empty>No hay informes disponibles.</Empty>
                )}
              </>
            )}
            {tab === "history" && (
              <>
                <h2>Historial y comentarios</h2>
                {canWrite && r.status !== "CLOSED" && (
                  <form onSubmit={addComment}>
                    <Field label="Comentario">
                      <textarea
                        required
                        maxLength={5000}
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                      />
                    </Field>
                    {staff && (manager || r.samples.some((s) => s.can_receive)) && (
                      <label className="check-label">
                        <input
                          type="checkbox"
                          checked={internal}
                          onChange={(e) => setInternal(e.target.checked)}
                        />
                        Solo laboratorio
                      </label>
                    )}
                    <Button busy={busy} variant="primary">
                      Añadir comentario
                    </Button>
                  </form>
                )}
                {r.activity.map((a) => (
                  <article className="history-entry" key={a.id}>
                    <b>{a.message}</b>
                    <small className="block">
                      {a.actor_name} ·{" "}
                      {new Date(a.created_at).toLocaleString("es-PE", {
                        timeZone: "America/Lima",
                      })}
                      {a.internal ? " · Interno" : ""}
                    </small>
                    {a.description_lines?.map((line, i) => (
                      <p className="history-description" key={i}>
                        {line}
                      </p>
                    ))}
                  </article>
                ))}
              </>
            )}
          </section>
        </>
      ) : (
        !error && <p>Cargando solicitud…</p>
      )}
    </>
  );
}
