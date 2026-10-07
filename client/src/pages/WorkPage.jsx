import { assayStatuses } from "../services/statuses";
import useErrorNotice from "../hooks/useErrorNotice";
import SearchSelect from "../components/SearchSelect";
import RequesterFilters from "../components/RequesterFilters";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  PageHead,
  ClearFilters,
  Field,
  ErrorBox,
  Loading,
} from "../components/ui";
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
    [error, setError] = useErrorNotice(),
    [revision, setRevision] = useState(0),
    [loading, setLoading] = useState(true);
  const [filterEpoch, setFilterEpoch] = useState(0);
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
  }, [setError]);
  useEffect(() => {
    let live = true;
    setLoading(true);
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
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [query, revision, setError]);
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
      <div className="listing-layout work-listing">
        <aside className="card form-card filters-panel">
          <details open>
            <summary>Filtros</summary>
            <div className="filter-actions">
              <ClearFilters
                setParams={setParams}
                onClear={() => setFilterEpoch((n) => n + 1)}
              />
            </div>
            <div className="form-grid" key={filterEpoch}>
              <Field label="Solicitud (código)">
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
                ["assay_status", "Estado Ensayo", assayStatuses],
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
                    <SearchSelect
                      multiple={key === "assay_status"}
                      value={params.get(key) || ""}
                      onChange={(v) => filter(key, v)}
                      options={items}
                    />
                  </Field>
                ))}
              <RequesterFilters params={params} filter={filter} view="work" />
              {params.get("request") && (
                <Field label="Solicitud seleccionada">
                  <button className="btn" onClick={() => filter("request", "")}>
                    Quitar filtro de solicitud
                  </button>
                </Field>
              )}
            </div>
          </details>
        </aside>
        <section className="card form-card results-panel" aria-busy={loading}>
          {loading && (
            <Loading>
              {data ? "Actualizando ensayos…" : "Cargando ensayos…"}
            </Loading>
          )}
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
          ) : null}
        </section>
      </div>
    </>
  );
}
