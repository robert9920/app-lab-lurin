import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { api, messageOf, download } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  PageHead,
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
    [error, setError] = useState(""),
    [revision, setRevision] = useState(0);
  const query = params.toString();
  useEffect(() => {
    api
      .get("/projects")
      .then((r) => setProjects(r.data))
      .catch((e) => setError(messageOf(e)));
  }, []);
  useEffect(() => {
    let live = true;
    api
      .get("/reports?" + query)
      .then((r) => {
        if (live) setData(r.data);
      })
      .catch((e) => {
        if (live) setError(messageOf(e));
      });
    return () => {
      live = false;
    };
  }, [query, revision]);
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
  }, [staff, search, revision]);
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
        description="Consulta todas las versiones de los informes de tus proyectos."
      />
      <ErrorBox>{error}</ErrorBox>
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
      <section className="card form-card section-gap">
        <div className="form-grid">
          <Field label="Buscar informe por solicitud o proyecto">
            <input
              value={params.get("q") || ""}
              onChange={(e) => filter("q", e.target.value)}
            />
          </Field>
          <Field label="Proyecto">
            <select
              value={params.get("project") || ""}
              onChange={(e) => filter("project", e.target.value)}
            >
              <option value="">Todos mis proyectos</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} · {p.name}
                </option>
              ))}
            </select>
          </Field>
          {params.get("request") && (
            <Button onClick={() => filter("request", "")}>
              Quitar filtro de solicitud
            </Button>
          )}
        </div>
        {data?.items.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Informe / versión</th>
                  <th>Solicitud / proyecto</th>
                  <th>Fecha de carga</th>
                  <th />
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
                    <td>{fmtDate(d.created_at)}</td>
                    <td>
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
          <Empty>
            {data ? "No hay informes con estos filtros." : "Cargando informes…"}
          </Empty>
        )}
        {data && <Pager data={data} params={params} setParams={setParams} />}
      </section>
    </>
  );
}
