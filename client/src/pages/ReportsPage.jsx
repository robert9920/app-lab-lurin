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
import ReportUpload from "../components/ReportUpload";
import { Pager } from "./Dashboard";
import { detailUrl } from "../services/navigation";
export default function ReportsPage() {
  const { user } = useAuth(),
    staff = user.roles.some((r) => ["MANAGER", "TECH"].includes(r)),
    [params, setParams] = useSearchParams(),
    location = useLocation();
  const [data, setData] = useState(null),
    [projects, setProjects] = useState([]),
    [requests, setRequests] = useState([]),
    [request, setRequest] = useState(null),
    [search, setSearch] = useState(""),
    [error, setError] = useErrorNotice(),
    [revision, setRevision] = useState(0);
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
  }, [query, revision, setError]);
  useEffect(() => {
    if (staff) {
      let live = true;
      api
        .get(
          "/requests?status=APPROVED&limit=30&q=" + encodeURIComponent(search),
        )
        .then((r) => {
          if (live) setRequests(r.data.items);
        })
        .catch((e) => setError(messageOf(e)));
      return () => {
        live = false;
      };
    }
  }, [staff, search, revision, setError]);
  function filter(k, v) {
    const p = new URLSearchParams(params);
    v ? p.set(k, v) : p.delete(k);
    p.delete("page");
    setParams(p, { replace: true });
  }
  async function select(id) {
    setRequest(null);
    if (id)
      try {
        setRequest((await api.get("/requests/" + id)).data);
      } catch (e) {
        setError(messageOf(e));
      }
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
            <summary>Filtros e informes</summary>
            {staff && (
              <section className="card form-card">
                <h2>Subir un informe</h2>
                <div className="form-grid">
                  <Field label="Buscar solicitud aprobada">
                    <input
                      value={search}
                      onChange={(e) => {
                        setSearch(e.target.value);
                        setRequest(null);
                      }}
                      placeholder="Código o nombre (hasta 30 coincidencias)"
                    />
                  </Field>
                  <Field label="Solicitud de destino">
                    <select
                      value={request?.id || ""}
                      onChange={(e) => select(e.target.value)}
                    >
                      <option value="">Seleccionar solicitud</option>
                      {requests.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.code} · {r.title}
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>
                {request && (
                  <ReportUpload
                    key={request.id + "-" + request.version}
                    request={request}
                    onDone={async () => {
                      await select(request.id);
                      setRevision((v) => v + 1);
                    }}
                  />
                )}
              </section>
            )}
            <div>
              <div className="filter-actions">
                <ClearFilters
                  setParams={setParams}
                  onClear={() => setFilterEpoch((n) => n + 1)}
                />
              </div>
              <div className="form-grid" key={filterEpoch}>
                <Field label="Buscar informe por solicitud o proyecto">
                  <input
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
