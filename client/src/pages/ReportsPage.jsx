import useErrorNotice from "../hooks/useErrorNotice";
import SearchSelect from "../components/SearchSelect";
import RequesterFilters from "../components/RequesterFilters";
import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { api, messageOf, download } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  PageHead,
  ClearFilters,
  Loading,
  Field,
  ErrorBox,
  Button,
  Empty,
  fmtDate,
} from "../components/ui";
import { Pager } from "./Dashboard";
import { detailUrl } from "../services/navigation";
export default function ReportsPage() {
  const { user } = useAuth(),
    [params, setParams] = useSearchParams(),
    location = useLocation();
  const [data, setData] = useState(null),
    [projects, setProjects] = useState([]),
    [error, setError] = useErrorNotice();
  const readers = user.roles.some((r) =>
    ["ADMIN", "MANAGER", "TECH"].includes(r),
  );
  const [loading, setLoading] = useState(true);
  const [filterEpoch, setFilterEpoch] = useState(0);
  const query = params.toString();
  useEffect(() => {
    api
      .get("/projects")
      .then((r) => setProjects(r.data))
      .catch((e) => setError(messageOf(e)));
  }, [setError]);
  useEffect(() => {
    let live = true;
    setLoading(true);
    api
      .get("/reports?" + query)
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
  }, [query, setError]);
  function filter(k, v) {
    const p = new URLSearchParams(params);
    v ? p.set(k, v) : p.delete(k);
    p.delete("page");
    setParams(p, { replace: true });
  }
  return (
    <>
      <PageHead
        eyebrow="RESULTADOS DISPONIBLES"
        title="Informes"
        description="Consulta todas las versiones de los informes de tus solicitudes autorizadas."
      />
      <ErrorBox>{error}</ErrorBox>
      <div className="listing-layout reports-listing">
        <aside className="card form-card filters-panel">
          <details open>
            <summary>Filtros</summary>
            <div>
              <div className="filter-actions">
                <ClearFilters
                  setParams={setParams}
                  onClear={() => setFilterEpoch((n) => n + 1)}
                />
              </div>
              <div className="form-grid" key={filterEpoch}>
                <Field label="Buscar solicitud">
                  <input
                    placeholder="Código de solicitud"
                    value={params.get("q") || ""}
                    onChange={(e) => filter("q", e.target.value)}
                  />
                </Field>
                {(readers || user.is_internal) && (
                  <Field label="Proyecto">
                    <SearchSelect
                      value={params.get("project") || ""}
                      onChange={(v) => filter("project", v)}
                      options={projects}
                    />
                  </Field>
                )}
                {readers && (
                  <RequesterFilters
                    params={params}
                    filter={filter}
                    view="reports"
                  />
                )}
                {params.get("request") && (
                  <Button onClick={() => filter("request", "")}>
                    Quitar filtro de solicitud
                  </Button>
                )}
              </div>
            </div>
          </details>
        </aside>
        <section className="card results-panel" aria-busy={loading}>
          {loading && (
            <Loading>
              {data ? "Actualizando informes…" : "Cargando informes…"}
            </Loading>
          )}
          {data?.items.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Informe / versión</th>
                    <th>Solicitud / proyecto</th>
                    {readers && <th>Solicitante / Empresa</th>}
                    <th>Fecha de carga</th>
                    <th className="action-column" aria-label="Acciones" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((d) => (
                    <tr key={d.id}>
                      <td>
                        <b>{d.name}</b>
                        <small className="block">
                          Versión {d.version} · {(d.bytes / 1024).toFixed(0)} KB
                        </small>
                      </td>
                      <td>
                        <Link
                          className="text-link"
                          to={detailUrl(
                            d.request_id,
                            "documents",
                            location.pathname + location.search,
                          )}
                        >
                          {d.request_code}
                        </Link>
                        <small className="block">{d.project_code}</small>
                      </td>
                      {readers && (
                        <td>
                          <b>{d.requester_name}</b>
                          <small className="block">{d.organization_name}</small>
                        </td>
                      )}
                      <td>{fmtDate(d.created_at)}</td>
                      <td className="action-column">
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
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            data && <Empty>No hay informes con estos filtros.</Empty>
          )}
          {data && <Pager data={data} params={params} setParams={setParams} />}
        </section>
      </div>
    </>
  );
}
