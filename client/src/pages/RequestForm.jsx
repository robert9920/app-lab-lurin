import useErrorNotice from "../hooks/useErrorNotice";
import AssaysEditor from "../components/AssaysEditor";
import NumericInput from "../components/NumericInput";
import DepthInput from "../components/DepthInput";
import AssayPicker, { SelectedAssays } from "../components/AssayPicker";
import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import {
  Plus,
  Copy,
  Trash2,
  ClipboardPaste,
  ArrowLeft,
  Check,
} from "lucide-react";
import { api, messageOf } from "../services/api";
import {
  PageHead,
  Button,
  Field,
  ErrorBox,
  Modal,
  Loading,
} from "../components/ui";
import ProjectSelect from "../components/ProjectSelect";
import { useAuth } from "../context/AuthContext";
import {
  blankSample,
  parseSamples,
  prepareSample,
  sampleErrors,
  hasSampleData,
} from "../services/samples";

const columns = [
  ["borehole", "Calicata / sondaje"],
  ["client_code", "Muestra *"],
  ["depth_from", "Prof. inicial (m)"],
  ["depth_to", "Prof. final (m)"],
  ["material", "Tipo de muestra *"],
  ["quantity", "Recipientes"],
  ["weight", "Peso (kg)"],
  ["easting", "Coordenadas Este"],
  ["northing", "Coordenadas Norte"],
];
const numbers = [
  "depth_from",
  "depth_to",
  "quantity",
  "weight",
  "easting",
  "northing",
];
function SampleValueInput({ kind, ...props }) {
  if (["depth_from", "depth_to"].includes(kind))
    return <DepthInput {...props} />;
  return ["quantity", "weight"].includes(kind) ? (
    <NumericInput
      {...props}
      integer={kind === "quantity"}
      increment={kind === "quantity" ? 1 : 0.1}
    />
  ) : (
    <input {...props} />
  );
}
export default function RequestForm() {
  const { id } = useParams(),
    navigate = useNavigate(),
    { user } = useAuth();
  const [ready, setReady] = useState(false),
    [assaysRequest, setAssaysRequest] = useState(null),
    [reviewedTasks, setReviewedTasks] = useState([]),
    [denied, setDenied] = useState(false),
    [catalog, setCatalog] = useState([]),
    [form, setForm] = useState({
      project_id: "",
      notes: "",
      target_date: "",
      estimated_arrival_date: "",
      district: "",
      province: "",
      department: "",
      samples: [blankSample()],
    }),
    [version, setVersion] = useState(1),
    [status, setStatus] = useState("DRAFT"),
    [internal, setInternal] = useState(user.is_internal),
    [step, setStep] = useState(0),
    [error, setError] = useErrorNotice(),
    [busy, setBusy] = useState(false),
    [paste, setPaste] = useState(false),
    [text, setText] = useState(""),
    [selected, setSelected] = useState([]),
    [picker, setPicker] = useState(null),
    [showErrors, setShowErrors] = useState(false);
  useEffect(() => {
    Promise.all([
      api.get("/catalog"),
      id ? api.get(`/requests/${id}`) : Promise.resolve(null),
    ])
      .then(([c, r]) => {
        setCatalog(c.data);
        if (r?.data.can_edit_assays) {
          setCatalog(c.data);
          setAssaysRequest(r.data);
          return;
        }
        if (r) {
          const d = r.data;
          setReviewedTasks(
            d.tasks.filter((t) => t.review_status !== "PENDING"),
          );
          if (!d.can_edit) {
            setDenied(true);
            setError("Esta solicitud ya no admite edición.");
            return;
          }
          setVersion(d.version);
          setStatus(d.status);
          setInternal(d.is_internal);
          const f = {};
          for (const k of [
            "project_id",
            "notes",
            "target_date",
            "estimated_arrival_date",
            "district",
            "province",
            "department",
          ])
            f[k] = d[k] ?? "";
          f.samples = d.samples.map((s) => ({
            ...blankSample(),
            ...Object.fromEntries(
              [
                "id",
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
                "assay_ids",
                "received_at",
              ].map((k) => [k, s[k] ?? (k === "assay_ids" ? [] : "")]),
            ),
          }));
          if (!f.samples.length) f.samples = [blankSample()];
          setForm(f);
        }
      })
      .catch((e) => {
        setError(messageOf(e));
        if (id) setDenied(true);
      })
      .finally(() => setReady(true));
  }, [id, setError]);
  function update(i, k, v) {
    setForm((f) => ({
      ...f,
      samples: f.samples.map((s, j) => (j === i ? { ...s, [k]: v } : s)),
    }));
  }
  function change(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }
  const errors = form.samples.map((s) => sampleErrors(s, form.samples));
  const pending = form.samples.filter((s) => !s.assay_ids.length).length;
  const [cellNotice, setCellNotice] = useErrorNotice();
  function next(e) {
    e.preventDefault();
    if (internal && !form.project_id) {
      setError("Selecciona un proyecto disponible.");
      return;
    }
    setError("");
    setStep(1);
  }
  function review() {
    setShowErrors(true);
    if (errors.some((e) => Object.keys(e).length)) {
      setError("Revisa las celdas marcadas antes de continuar.");
      setCellNotice("Revisa las celdas");
      return;
    }
    setError("");
    setStep(2);
  }
  async function save(submit = false) {
    if (busy) return;
    const draft = status === "DRAFT" && !submit;
    const samples = form.samples.filter(hasSampleData);
    if (
      samples.some(
        (sample) =>
          Object.keys(sampleErrors(sample, samples, { required: !draft }))
            .length,
      )
    ) {
      setShowErrors(true);
      setError("Revisa los valores de las muestras antes de guardar.");
      setCellNotice("Revisa las celdas");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const payload = {
        ...form,
        project_id: internal ? form.project_id : id ? form.project_id : null,
        target_date: form.target_date || null,
        estimated_arrival_date: form.estimated_arrival_date || null,
        samples: samples.map(prepareSample),
        ...(id ? { version } : {}),
      };
      const { data } = await api[id ? "put" : "post"](
        id ? `/requests/${id}` : "/requests",
        payload,
      );
      if (submit && ["DRAFT", "OBSERVED"].includes(data.status))
        await api.post(`/requests/${data.id}/actions`, {
          version: data.version,
          action: "submit",
        });
      navigate(`/requests/${data.id}`);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  function setAssay(aid, checked, indices) {
    setForm((f) => ({
      ...f,
      samples: f.samples.map((s, i) =>
        indices.includes(i) &&
        !reviewedTasks.some((t) => t.sample_id === s.id && t.assay_id === aid)
          ? {
              ...s,
              assay_ids: checked
                ? [...new Set([...s.assay_ids, aid])]
                : s.assay_ids.filter((a) => a !== aid),
            }
          : s,
      ),
    }));
  }
  if (!ready) return <Loading>Cargando solicitud y catálogo…</Loading>;
  if (assaysRequest)
    return <AssaysEditor request={assaysRequest} catalog={catalog} />;
  if (denied)
    return (
      <>
        <Link to={`/requests/${id}`} className="back-link">
          Volver
        </Link>
        <ErrorBox>{error}</ErrorBox>
      </>
    );
  return (
    <>
      <Link to={id ? `/requests/${id}` : "/requests"} className="back-link">
        <ArrowLeft size={16} />
        Volver
      </Link>
      <PageHead
        eyebrow="SOLICITUD DE SERVICIO"
        title={id ? "Editar solicitud" : "Nueva solicitud"}
        description="Registra las muestras que enviarás. Puedes definir sus ensayos después."
      />
      <div className="steps">
        {["Datos del servicio", "Muestras y ensayos", "Revisar y enviar"].map(
          (n, i) => (
            <button
              key={n}
              onClick={() => i < step && setStep(i)}
              className={i <= step ? "active" : ""}
            >
              <span>{i < step ? <Check size={16} /> : i + 1}</span>
              {n}
            </button>
          ),
        )}
      </div>
      <ErrorBox>{error}</ErrorBox>
      <section className="card form-card request-form">
        {step === 0 ? (
          <form onSubmit={next}>
            <div className="service-heading">
              <h2>Datos del servicio</h2>
              {!internal && (
                <span className="external-service">
                  Solicitud de cliente externo
                </span>
              )}
            </div>
            <div className="form-grid">
              {internal ? (
                <ProjectSelect
                  value={form.project_id}
                  disabled={!!id && status !== "DRAFT"}
                  onChange={(v) => change("project_id", v)}
                />
              ) : null}
              <Field label="Fecha objetivo entrega resultados (opcional)">
                <input
                  type="date"
                  value={form.target_date}
                  onChange={(e) => change("target_date", e.target.value)}
                />
              </Field>
              <Field label="Fecha estimada arribo muestra (opcional)">
                <input
                  type="date"
                  value={form.estimated_arrival_date}
                  onChange={(e) =>
                    change("estimated_arrival_date", e.target.value)
                  }
                />
              </Field>
              {[
                ["district", "Distrito"],
                ["province", "Provincia"],
                ["department", "Departamento"],
              ].map(([k, l]) => (
                <Field key={k} label={l + " *"}>
                  <input
                    required
                    maxLength={100}
                    value={form[k]}
                    onChange={(e) => change(k, e.target.value)}
                  />
                </Field>
              ))}
            </div>
            <Field label="Indicaciones generales (opcional)">
              <textarea
                maxLength={5000}
                value={form.notes}
                onChange={(e) => change("notes", e.target.value)}
              />
            </Field>
            <div className="form-actions">
              {status === "DRAFT" && (
                <Button type="button" busy={busy} onClick={() => save(false)}>
                  Guardar borrador
                </Button>
              )}
              <Button variant="primary">Continuar con las muestras</Button>
            </div>
          </form>
        ) : step === 1 ? (
          <>
            <div className="card-title">
              <h2>Muestras y ensayos</h2>
              <div className="actions">
                <Button onClick={() => setPaste(true)}>
                  <ClipboardPaste size={16} />
                  Pegar Excel
                </Button>
                <Button
                  disabled={form.samples.length >= 200}
                  onClick={() =>
                    setForm({
                      ...form,
                      samples: [...form.samples, blankSample()],
                    })
                  }
                >
                  <Plus size={16} />
                  Añadir muestra
                </Button>
              </div>
            </div>
            <p className="muted">
              Una fila por muestra. Añade los ensayos conocidos; puedes
              definirlos después. Las muestras recibidas conservan sus datos
              declarados.
            </p>
            {selected.length > 0 && (
              <div className="actions sample-bulk-actions">
                <Button onClick={() => setPicker([...selected])}>
                  Añadir ensayos a {selected.length} muestras seleccionadas
                </Button>
              </div>
            )}
            <div className="table-scroll sample-matrix">
              <table>
                <thead>
                  <tr>
                    <th>
                      <input
                        type="checkbox"
                        aria-label="Seleccionar todas las filas"
                        checked={selected.length === form.samples.length}
                        onChange={(e) =>
                          setSelected(
                            e.target.checked
                              ? form.samples.map((_, i) => i)
                              : [],
                          )
                        }
                      />
                    </th>
                    {columns.map(([k, l]) => (
                      <th key={k}>{l}</th>
                    ))}
                    <th className="sample-assays-column">
                      Ensayos solicitados
                    </th>
                    <th>Observaciones</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {form.samples.map((s, i) => (
                    <tr key={s.id || i}>
                      <td>
                        <input
                          type="checkbox"
                          aria-label={"Seleccionar fila " + (i + 1)}
                          checked={selected.includes(i)}
                          onChange={(e) =>
                            setSelected(
                              e.target.checked
                                ? [...selected, i]
                                : selected.filter((n) => n !== i),
                            )
                          }
                        />
                        <small className="block">{i + 1}</small>
                      </td>
                      {columns.map(([k, l]) => (
                        <td key={k}>
                          <SampleValueInput
                            kind={k}
                            aria-label={l + " · fila " + (i + 1)}
                            aria-invalid={showErrors && !!errors[i][k]}
                            readOnly={!!s.received_at}
                            required={["client_code", "material"].includes(k)}
                            type={numbers.includes(k) ? "number" : "text"}
                            step={k === "quantity" ? "1" : "any"}
                            min={
                              numbers.includes(k)
                                ? k === "quantity"
                                  ? "1"
                                  : k === "weight"
                                    ? "0.1"
                                    : "0"
                                : undefined
                            }
                            maxLength={100}
                            value={s[k]}
                            onChange={(e) => update(i, k, e.target.value)}
                          />
                          {cellNotice && errors[i][k] && (
                            <ErrorBox inline>
                              {{ ...cellNotice, message: errors[i][k] }}
                            </ErrorBox>
                          )}
                        </td>
                      ))}
                      <td className="sample-assays-column">
                        <SelectedAssays
                          ids={s.assay_ids}
                          catalog={catalog}
                          locked={reviewedTasks
                            .filter((t) => t.sample_id === s.id)
                            .map((t) => t.assay_id)}
                          onRemove={(aid) => setAssay(aid, false, [i])}
                        />
                        <Button onClick={() => setPicker([i])}>
                          Añadir ensayo
                        </Button>
                      </td>
                      <td>
                        <textarea
                          aria-label={"Observaciones · fila " + (i + 1)}
                          readOnly={!!s.received_at}
                          maxLength={3000}
                          value={s.notes}
                          onChange={(e) => update(i, "notes", e.target.value)}
                        />
                      </td>
                      <td>
                        <div className="actions">
                          <button
                            className="icon-btn"
                            title="Duplicar muestra"
                            disabled={form.samples.length >= 200}
                            onClick={() =>
                              setForm({
                                ...form,
                                samples: [
                                  ...form.samples,
                                  {
                                    ...s,
                                    id: undefined,
                                    received_at: null,
                                    client_code: s.client_code + "-copia",
                                  },
                                ],
                              })
                            }
                          >
                            <Copy size={16} />
                          </button>
                          <button
                            className="icon-btn"
                            title="Eliminar muestra"
                            disabled={
                              !!s.received_at || form.samples.length === 1
                            }
                            onClick={() => {
                              setForm({
                                ...form,
                                samples: form.samples.filter((_, j) => j !== i),
                              });
                              setSelected([]);
                            }}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                        {s.received_at && <small>Recibida</small>}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={columns.length + 4}>
                      {form.samples.length} muestras · {pending} con ensayos por
                      definir
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
            <div className="form-actions">
              <Button onClick={() => setStep(0)}>Atrás</Button>
              {status === "DRAFT" && (
                <Button busy={busy} onClick={() => save(false)}>
                  Guardar borrador
                </Button>
              )}
              <Button variant="primary" onClick={review}>
                Revisar solicitud
              </Button>
            </div>
          </>
        ) : (
          <>
            <h2>Revisa tu solicitud</h2>
            <div className="review-summary">
              <p>
                {internal ? form.project_id : "Cliente externo"} ·{" "}
                {form.district}, {form.province}, {form.department}
              </p>
              <strong>{form.samples.length} muestras</strong> ·{" "}
              {form.samples.reduce((n, s) => n + s.assay_ids.length, 0)} ensayos
              <p>
                {pending
                  ? `${pending} muestras quedarán pendientes de definir ensayos. El laboratorio podrá registrar su recepción.`
                  : "El laboratorio revisará los ensayos antes de aprobar."}
              </p>
            </div>
            <div className="form-actions">
              <Button onClick={() => setStep(1)}>Volver a muestras</Button>
              {status === "DRAFT" && (
                <Button busy={busy} onClick={() => save(false)}>
                  Guardar borrador
                </Button>
              )}
              <Button variant="primary" busy={busy} onClick={() => save(true)}>
                {["DRAFT", "OBSERVED"].includes(status)
                  ? "Enviar al laboratorio"
                  : pending
                    ? "Guardar cambios"
                    : "Guardar y enviar a revisión"}
              </Button>
            </div>
          </>
        )}
      </section>
      {picker && (
        <AssayPicker
          catalog={catalog}
          existing={catalog
            .filter((a) =>
              picker.every((i) => form.samples[i].assay_ids.includes(a.id)),
            )
            .map((a) => a.id)}
          onClose={() => setPicker(null)}
          onApply={(ids) => {
            if (
              picker.some(
                (i) =>
                  new Set([...form.samples[i].assay_ids, ...ids]).size > 40,
              )
            )
              throw new Error("Máximo 40 ensayos por muestra.");
            ids.forEach((aid) => setAssay(aid, true, picker));
          }}
        />
      )}
      {paste && (
        <Modal
          title="Pegar muestras desde Excel"
          onClose={() => setPaste(false)}
        >
          <div className="modal-body">
            <p>Copia filas sin encabezados, en este orden:</p>
            <p>
              Calicata / sondaje · Muestra · Prof. inicial · Prof. final · Tipo
              · Recipientes · Peso (kg) · Observaciones · Coordenadas Este ·
              Coordenadas Norte
            </p>
            <textarea
              rows={8}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Celdas separadas por tabulaciones"
            />
            <Button
              variant="primary"
              disabled={!text.trim()}
              onClick={() => {
                const rows = parseSamples(text);
                const current = form.samples.filter(
                  (s) => s.client_code || s.received_at,
                );
                if (current.length + rows.length > 200) {
                  setError("Máximo 200 muestras por solicitud.");
                  return;
                }
                setForm({ ...form, samples: [...current, ...rows] });
                setPaste(false);
                setSelected([]);
              }}
            >
              Incorporar filas
            </Button>
          </div>
        </Modal>
      )}
    </>
  );
}
