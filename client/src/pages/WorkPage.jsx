import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { PageHead, Field, ErrorBox, Empty, labels } from "../components/ui";
import WorkPanel from "../components/WorkPanel";
import { Pager } from "./Dashboard";
export default function WorkPage() {
  const { user } = useAuth(),
    [params, setParams] = useSearchParams();
  const [data, setData] = useState(null),
    [options, setOptions] = useState({
      projects: [],
      technicians: [],
      catalog: [],
    }),
    [error, setError] = useState(""),
    [revision, setRevision] = useState(0);
  const query = params.toString();
  useEffect(() => {
    Promise.all([
      api.get("/projects"),
      api.get("/technicians"),
      api.get("/catalog"),
    ])
      .then(([p, t, c]) =>
        setOptions({ projects: p.data, technicians: t.data, catalog: c.data }),
      )
      .catch((e) => setError(messageOf(e)));
  }, []);
  useEffect(() => {
    let live = true;
    setData(null);
    api
      .get("/work?" + query)
      .then((r) => {
        if (live) {
          setData(r.data);
          setError("");
        }
      })
      .catch((e) => {
        if (live) setError(messageOf(e));
      });
    return () => {
      live = false;
    };
  }, [query, revision]);
  function filter(k, v) {
    const p = new URLSearchParams(params);
    v ? p.set(k, v) : p.delete(k);
    p.delete("page");
    setParams(p, { replace: true });
  }
  return (
    <>
      <PageHead
        eyebrow="PROGRAMACIÓN Y EJECUCIÓN"
        title="Trabajo de laboratorio"
        description="Filtra los ensayos y selecciona uno o varios para asignarlos o actualizar su estado."
      />
      <ErrorBox>{error}</ErrorBox>
      <section className="card form-card">
        <div className="form-grid">
          <Field label="Solicitud (código o título)">
            <input
              value={params.get("request_q") || ""}
              onChange={(e) => filter("request_q", e.target.value)}
            />
          </Field>
          {[
            ["project", "Proyecto", options.projects],
            [
              "technician",
              "Técnico",
              [
                { id: "unassigned", name: "Sin asignar" },
                ...options.technicians,
              ],
            ],
            ["assay", "Tipo de ensayo", options.catalog],
            [
              "state",
              "Estado",
              ["PENDING", "RUNNING", "OBSERVED", "COMPLETED", "CANCELLED"].map(
                (id) => ({ id, name: labels[id] }),
              ),
            ],
            [
              "metric",
              "Carga",
              [
                { id: "open", name: "Carga abierta" },
                { id: "overdue", name: "Vencidos" },
                { id: "unassigned", name: "Sin asignar" },
                { id: "undated", name: "Sin fecha" },
                { id: "upcoming", name: "Próximos vencimientos" },
              ],
            ],
          ]
            .filter(
              ([key]) =>
                key !== "technician" ||
                user.roles.some((r) => ["ADMIN", "MANAGER"].includes(r)),
            )
            .map(([key, label, items]) => (
              <Field key={key} label={label}>
                <select
                  value={params.get(key) || ""}
                  onChange={(e) => filter(key, e.target.value)}
                >
                  <option value="">Todos</option>
                  {items.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.code ? o.code + " · " : ""}
                      {o.name}
                    </option>
                  ))}
                </select>
              </Field>
            ))}
          {params.get("request") && (
            <Field label="Solicitud seleccionada">
              <button className="btn" onClick={() => filter("request", "")}>
                Quitar filtro de solicitud
              </button>
            </Field>
          )}
        </div>
      </section>
      <section className="card form-card section-gap">
        {data ? (
          <>
            <WorkPanel
              key={query + "-" + revision}
              request={{
                id: null,
                version: 1,
                status: "APPROVED",
                tasks: data.items,
              }}
              user={user}
              onDone={() => setRevision((v) => v + 1)}
              bulk
            />
            <Pager data={data} params={params} setParams={setParams} />
          </>
        ) : (
          <Empty>Cargando ensayos…</Empty>
        )}
      </section>
    </>
  );
}
