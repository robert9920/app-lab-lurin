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
import { PageHead, Button, Field, ErrorBox, Modal } from "../components/ui";
import { blankSample, parseSamples, prepareSample } from "../services/samples";
export default function RequestForm() {
  const { id } = useParams(),
    navigate = useNavigate(),
    [projects, setProjects] = useState([]),
    [catalog, setCatalog] = useState([]),
    [form, setForm] = useState({
      project_id: "",
      title: "",
      notes: "",
      target_date: "",
      samples: [blankSample()],
    }),
    [version, setVersion] = useState(1),
    [step, setStep] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [paste, setPaste] = useState(false),
    [text, setText] = useState("");
  useEffect(() => {
    Promise.all([
      api.get("/projects"),
      api.get("/catalog"),
      id ? api.get(`/requests/${id}`) : Promise.resolve(null),
    ])
      .then(([p, c, r]) => {
        setProjects(p.data.filter((p) => p.active));
        setCatalog(c.data.filter((a) => a.active));
        if (r) {
          const d = r.data;
          setVersion(d.version);
          setForm({
            project_id: d.project_id,
            title: d.title,
            notes: d.notes,
            target_date: d.target_date || "",
            samples: d.samples.map((s) => {
              const {
                client_code,
                borehole,
                material,
                depth_from,
                depth_to,
                quantity,
                unit,
                notes,
                assay_ids,
              } = s;
              return {
                client_code,
                borehole,
                material,
                depth_from: depth_from ?? "",
                depth_to: depth_to ?? "",
                quantity: quantity ?? "",
                unit,
                notes,
                assay_ids,
              };
            }),
          });
        }
      })
      .catch((e) => setError(messageOf(e)));
  }, [id]);
  function update(i, k, v) {
    setForm((f) => ({
      ...f,
      samples: f.samples.map((s, j) => (j === i ? { ...s, [k]: v } : s)),
    }));
  }
  function next(e) {
    e.preventDefault();
    setStep(step + 1);
  }
  async function save(submit = false) {
    setBusy(true);
    setError("");
    try {
      const payload = {
        ...form,
        target_date: form.target_date || null,
        samples: form.samples.map(prepareSample),
        ...(id ? { version } : {}),
      };
      const { data } = await api[id ? "put" : "post"](
        id ? `/requests/${id}` : "/requests",
        payload,
      );
      if (submit)
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
  return (
    <>
      <Link to={id ? `/requests/${id}` : "/requests"} className="back-link">
        <ArrowLeft size={16} />
        Volver
      </Link>
      <PageHead
        eyebrow="SOLICITUD DE SERVICIO"
        title={id ? "Editar solicitud" : "Cuéntanos qué necesitas"}
        description="Completa los datos del proyecto y selecciona los ensayos para cada muestra."
      />
      <div className="steps">
        {["Proyecto y servicio", "Muestras y ensayos", "Revisar y enviar"].map(
          (name, i) => (
            <button
              key={name}
              onClick={() => i < step && setStep(i)}
              className={i <= step ? "active" : ""}
            >
              <span>{i < step ? <Check size={16} /> : i + 1}</span>
              {name}
            </button>
          ),
        )}
      </div>
      <ErrorBox>{error}</ErrorBox>
      <section className="card form-card">
        {step === 0 ? (
          <form onSubmit={next}>
            <h2>Datos del servicio</h2>
            <div className="form-grid">
              <Field label="Proyecto">
                <select
                  required
                  value={form.project_id}
                  disabled={!!id}
                  onChange={(e) =>
                    setForm({ ...form, project_id: e.target.value })
                  }
                >
                  <option value="">Selecciona tu proyecto</option>
                  {projects.map((p) => (
                    <option value={p.id} key={p.id}>
                      {p.code} · {p.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Fecha objetivo (opcional)">
                <input
                  type="date"
                  value={form.target_date}
                  onChange={(e) =>
                    setForm({ ...form, target_date: e.target.value })
                  }
                />
              </Field>
            </div>
            <Field label="Nombre de la solicitud">
              <input
                required
                minLength={3}
                maxLength={180}
                value={form.title}
                placeholder="Ej. Caracterización de suelos del dique norte"
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </Field>
            <Field label="Indicaciones generales">
              <textarea
                value={form.notes}
                placeholder="Indica antecedentes o instrucciones relevantes para el laboratorio."
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </Field>
            <div className="form-actions">
              <Button variant="primary">Continuar con las muestras</Button>
            </div>
          </form>
        ) : step === 1 ? (
          <>
            <div className="card-title">
              <h2>Muestras declaradas</h2>
              <div className="actions">
                <Button onClick={() => setPaste(true)}>
                  <ClipboardPaste size={16} />
                  Pegar Excel
                </Button>
                <Button
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
            {form.samples.map((s, i) => (
              <div className="sample-editor" key={i}>
                <header>
                  <b>Muestra {i + 1}</b>
                  <div>
                    <button
                      title="Duplicar muestra"
                      className="icon-btn"
                      onClick={() =>
                        setForm({
                          ...form,
                          samples: [
                            ...form.samples,
                            { ...s, client_code: s.client_code + "-copia" },
                          ],
                        })
                      }
                    >
                      <Copy size={17} />
                    </button>
                    <button
                      title="Eliminar muestra"
                      className="icon-btn"
                      disabled={form.samples.length === 1}
                      onClick={() =>
                        setForm({
                          ...form,
                          samples: form.samples.filter((_, j) => j !== i),
                        })
                      }
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                </header>
                <div className="form-grid four">
                  {[
                    ["client_code", "Código de muestra"],
                    ["borehole", "Calicata / sondaje"],
                    ["quantity", "Cantidad"],
                    ["unit", "Unidad"],
                  ].map(([key, label]) => (
                    <Field label={label} key={key}>
                      <input
                        type={key === "quantity" ? "number" : "text"}
                        min={key === "quantity" ? "0.001" : undefined}
                        step="any"
                        value={s[key]}
                        onChange={(e) => update(i, key, e.target.value)}
                      />
                    </Field>
                  ))}
                </div>
                <div className="form-grid four">
                  <Field label="Material">
                    <input
                      value={s.material}
                      onChange={(e) => update(i, "material", e.target.value)}
                    />
                  </Field>
                  <Field label="Profundidad desde (m)">
                    <input
                      type="number"
                      min="0"
                      step="any"
                      value={s.depth_from}
                      onChange={(e) => update(i, "depth_from", e.target.value)}
                    />
                  </Field>
                  <Field label="Hasta (m)">
                    <input
                      type="number"
                      min="0"
                      step="any"
                      value={s.depth_to}
                      onChange={(e) => update(i, "depth_to", e.target.value)}
                    />
                  </Field>
                  <Field label="Observaciones">
                    <input
                      value={s.notes}
                      onChange={(e) => update(i, "notes", e.target.value)}
                    />
                  </Field>
                </div>
                <span className="field-label">Ensayos solicitados</span>
                <div className="assay-chips">
                  {catalog.map((a) => (
                    <label
                      className={s.assay_ids.includes(a.id) ? "selected" : ""}
                      key={a.id}
                    >
                      <input
                        type="checkbox"
                        checked={s.assay_ids.includes(a.id)}
                        onChange={(e) =>
                          update(
                            i,
                            "assay_ids",
                            e.target.checked
                              ? [...s.assay_ids, a.id]
                              : s.assay_ids.filter((v) => v !== a.id),
                          )
                        }
                      />
                      {a.name}
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <div className="form-actions">
              <Button onClick={() => setStep(0)}>Atrás</Button>
              <Button
                variant="primary"
                disabled={form.samples.some(
                  (s) => !s.client_code || !s.assay_ids.length,
                )}
                onClick={() => setStep(2)}
              >
                Revisar solicitud
              </Button>
            </div>
          </>
        ) : (
          <>
            <h2>Todo listo para la revisión</h2>
            <p className="muted">
              El laboratorio verificará tu solicitud antes de recibir el
              material.
            </p>
            <div className="review-summary">
              <h3>{form.title}</h3>
              <p>{projects.find((p) => p.id === form.project_id)?.name}</p>
              <strong>{form.samples.length} muestras</strong>
              <span>
                {" "}
                · {form.samples.reduce(
                  (sum, s) => sum + s.assay_ids.length,
                  0,
                )}{" "}
                ensayos solicitados
              </span>
            </div>
            <div className="form-actions">
              <Button onClick={() => setStep(1)}>Volver a muestras</Button>
              <Button busy={busy} onClick={() => save(false)}>
                Guardar borrador
              </Button>
              <Button variant="primary" busy={busy} onClick={() => save(true)}>
                Enviar al laboratorio
              </Button>
            </div>
          </>
        )}
      </section>
      {paste && (
        <Modal
          title="Pegar muestras desde Excel"
          onClose={() => setPaste(false)}
        >
          <div className="modal-body">
            <p>Copia las filas sin encabezados en este orden:</p>
            <p className="muted">
              Código · Sondaje · Desde · Hasta · Cantidad · Unidad ·
              Observaciones
            </p>
            <textarea
              rows={8}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Pega aquí las celdas separadas por tabulaciones"
            />
            <p>Luego selecciona los ensayos de cada muestra.</p>
            <Button
              variant="primary"
              disabled={!text.trim()}
              onClick={() => {
                setForm({
                  ...form,
                  samples: [
                    ...form.samples.filter((s) => s.client_code),
                    ...parseSamples(text),
                  ],
                });
                setPaste(false);
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
