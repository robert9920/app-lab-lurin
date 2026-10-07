import {
  assayStatuses,
  requestStatuses,
  requestState,
} from "../services/statuses";
import useErrorNotice from "../hooks/useErrorNotice";
import SearchSelect from "../components/SearchSelect";
import RequesterFilters from "../components/RequesterFilters";
import EconomicDashboard from "../components/EconomicDashboard";
import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { api, messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  PageHead,
  ClearFilters,
  Loading,
  RequestBadges,
  ReceptionBadges,
  Badge,
  Empty,
  ErrorBox,
  Button,
  Field,
  fmtDate,
  labels,
} from "../components/ui";
import { detailUrl } from "../services/navigation";

export function Pager({ data, params, setParams }) {
  return (
    <nav className="pager" aria-label="Paginación">
      <span>
        {data.total} registros · Página {data.page}
      </span>
      <Button
        disabled={data.page <= 1}
        onClick={() => {
          const p = new URLSearchParams(params);
          p.set("page", data.page - 1);
          setParams(p);
        }}
      >
        Anterior
      </Button>
      <Button
        disabled={data.page * data.limit >= data.total}
        onClick={() => {
          const p = new URLSearchParams(params);
          p.set("page", data.page + 1);
          setParams(p);
        }}
      >
        Siguiente
      </Button>
    </nav>
  );
}
export function RequestList({ mode = "requests" }) {
  const { user } = useAuth();
  const canRequest = user.roles.includes("CLIENT");
  const staff = user.roles.some((r) =>
    ["ADMIN", "MANAGER", "TECH"].includes(r),
  );
  const [params, setParams] = useSearchParams(),
    location = useLocation();
  const [data, setData] = useState(null),
    [error, setError] = useErrorNotice(),
    [projects, setProjects] = useState([]),
    [loading, setLoading] = useState(true);
  const [filterEpoch, setFilterEpoch] = useState(0);
  const reception = mode === "reception";
  const queryParams = new URLSearchParams(params);
  if (reception && queryParams.has("status")) {
    queryParams.delete("status");
    queryParams.delete("page");
  }
  const query = queryParams.toString();
  useEffect(() => {
    if (reception && params.has("status")) {
      setParams(new URLSearchParams(query), { replace: true });
    }
  }, [params, query, reception, setParams]);
  useEffect(() => {
    api
      .get("/projects")
      .then((r) => setProjects(r.data))
      .catch((e) => setError(messageOf(e)));
  }, [setError]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .get("/requests?" + query + (reception ? "&view=reception" : ""))
      .then((r) => {
        if (active) {
          setData(r.data);
          setError("");
        }
      })
      .catch((e) => {
        if (active) setError(messageOf(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [query, reception, setError]);
  function filter(k, v) {
    const p = new URLSearchParams(params);
    v ? p.set(k, v) : p.delete(k);
    p.delete("page");
    setParams(p, { replace: true });
  }
  const from = location.pathname + location.search;
  return (
    <>
      <PageHead
        eyebrow={reception ? "CONTROL DE MATERIAL" : "GESTIÓN DE SERVICIOS"}
        title={reception ? "Recepción" : "Solicitudes"}
        description={
          reception
            ? "Solicitudes enviadas con muestras por atender u OT pendiente. Registra únicamente las que llegaron."
            : "Crea, revisa y sigue el avance de cada solicitud."
        }
      >
        {!reception && canRequest && (
          <Link className="btn primary" to="/requests/new">
            Nueva solicitud
          </Link>
        )}
      </PageHead>
      <ErrorBox>{error}</ErrorBox>
      <div className="listing-layout">
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
              <Field label="Buscar solicitud">
                <input
                  placeholder="Código de solicitud o proyecto"
                  value={params.get("q") || ""}
                  onChange={(e) => filter("q", e.target.value)}
                />
              </Field>
              {(staff || user.is_internal) && (
                <Field label="Proyecto">
                  <SearchSelect
                    options={projects}
                    value={params.get("project") || ""}
                    onChange={(v) => filter("project", v)}
                  />
                </Field>
              )}
              {staff && (
                <RequesterFilters params={params} filter={filter} view={mode} />
              )}
              {reception && (
                <Field label="Estado de recepción">
                  <SearchSelect
                    value={params.get("condition") || ""}
                    onChange={(v) => filter("condition", v)}
                    options={[
                      { id: "NOT_RECEIVED", name: "Con muestras sin recibir" },
                      { id: "NO_OT", name: "Sin OT" },
                      {
                        id: "issues",
                        name: "Con muestras observadas, dañadas o insuficientes",
                      },
                    ]}
                  />
                </Field>
              )}
              {!reception && (
                <>
                  <Field label="Estado Ensayo">
                    <SearchSelect
                      multiple
                      options={assayStatuses}
                      value={params.get("assay_status") || ""}
                      onChange={(v) => filter("assay_status", v)}
                    />
                  </Field>
                  <Field label="Estado Solicitud">
                    <SearchSelect
                      multiple
                      options={requestStatuses.filter(
                        (state) => state.id !== "DRAFT" || canRequest,
                      )}
                      value={params.get("request_status") || ""}
                      onChange={(v) => filter("request_status", v)}
                    />
                  </Field>
                </>
              )}
              {!reception && (
                <>
                  {[
                    ["created_from", "Creada desde"],
                    ["created_to", "Creada hasta"],
                  ].map(([key, label]) => (
                    <Field key={key} label={label}>
                      <input
                        type="date"
                        value={params.get(key) || ""}
                        onChange={(e) => filter(key, e.target.value)}
                      />
                    </Field>
                  ))}
                </>
              )}
            </div>
          </details>
        </aside>
        <section className="card results-panel" aria-busy={loading}>
          {loading && (
            <Loading>
              {data ? "Actualizando solicitudes…" : "Cargando solicitudes…"}
            </Loading>
          )}
          {!data ? null : data.items.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Solicitud / proyecto</th>
                    {staff && <th>Solicitante / Empresa</th>}
                    <th
                      className={reception ? undefined : "assay-status-column"}
                    >
                      {reception ? "Estado Recepción" : "Estado Ensayo"}
                    </th>
                    {!reception && <th>Estado Solicitud</th>}
                    {!reception && (
                      <th className="comments-column">
                        Indicaciones generales
                      </th>
                    )}
                    <th>
                      {reception ? "Muestras por atender" : "Avance de ensayos"}
                    </th>
                    {!reception && <th>Fecha de creación</th>}
                    <th>Fecha objetivo</th>
                    <th className="action-column" aria-label="Acciones" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <Link
                          className="table-link"
                          to={detailUrl(
                            r.id,
                            reception ? "reception" : "summary",
                            from,
                          )}
                        >
                          <b>{r.code}</b>

                          <small>{r.project_code}</small>
                        </Link>
                      </td>
                      {staff && (
                        <td>
                          <b>{r.requester_name}</b>
                          <small className="block">{r.organization_name}</small>
                        </td>
                      )}
                      <td
                        className={
                          reception ? undefined : "assay-status-column"
                        }
                      >
                        {reception ? (
                          <ReceptionBadges request={r} />
                        ) : (
                          <RequestBadges request={r} includeRequest={false} />
                        )}
                      </td>
                      {!reception && (
                        <td>
                          <Badge state={requestState(r)} />
                        </td>
                      )}
                      {!reception && (
                        <td className="comments-column">
                          {r.notes && (
                            <span className="comment-text">{r.notes}</span>
                          )}
                        </td>
                      )}
                      <td>
                        {reception ? (
                          r.pending_samples
                        ) : (
                          <>
                            <span>
                              {Number(r.task_count)
                                ? `${r.completed_count} de ${r.task_count}`
                                : "Ensayos por definir"}
                            </span>
                            <progress
                              max={r.task_count || 1}
                              value={r.completed_count}
                            />
                          </>
                        )}
                      </td>
                      {!reception && <td>{fmtDate(r.created_at)}</td>}
                      <td>{fmtDate(r.target_date)}</td>
                      <td className="action-column">
                        <Link
                          className="btn"
                          to={detailUrl(
                            r.id,
                            reception ? "reception" : "summary",
                            from,
                          )}
                        >
                          {reception ? "Registrar recepción" : "Abrir"}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty>No hay solicitudes con estos filtros.</Empty>
          )}
          {data && <Pager data={data} params={params} setParams={setParams} />}
        </section>
      </div>
    </>
  );
}
const states = ["PENDING", "RUNNING", "OBSERVED"];
const colors = {
  PENDING: "#a86b10",
  RUNNING: "#2563eb",
  OBSERVED: "#b51d2a",
};
export default function Dashboard() {
  const { user } = useAuth(),
    canView = user.roles.some((r) => ["ADMIN", "MANAGER", "TECH"].includes(r));
  const [data, setData] = useState(null),
    [error, setError] = useErrorNotice();
  const [loading, setLoading] = useState(canView),
    [retry, setRetry] = useState(0);
  useEffect(() => {
    if (canView) {
      setLoading(true);
      api
        .get("/dashboard")
        .then((r) => setData(r.data))
        .catch((e) => setError(messageOf(e)))
        .finally(() => setLoading(false));
    }
  }, [canView, retry, setError]);
  if (!canView)
    return (
      <>
        <PageHead
          eyebrow="LABORATORIO LURÍN"
          title={"Hola, " + user.name.split(" ")[0]}
          description="Tus solicitudes, muestras y resultados en un solo lugar."
        />
        <section className="welcome-banner">
          <div>
            <h2>Todo listo para tu próximo estudio</h2>
            <p>
              Consulta el estado de tus solicitudes y accede a los informes
              disponibles.
            </p>
            <Link className="btn" to="/requests">
              Ver solicitudes
            </Link>{" "}
            <Link className="btn" to="/reports">
              Consultar informes
            </Link>
          </div>
        </section>
      </>
    );
  const types = data
    ? Object.values(
        data.by_type.reduce((acc, row) => {
          acc[row.id] ??= { id: row.id, name: row.name, total: 0 };
          acc[row.id][row.state] = Number(row.count);
          acc[row.id].total += Number(row.count);
          return acc;
        }, {}),
      ).sort((a, b) => b.total - a.total)
    : [];
  const max = Math.max(1, ...types.map((x) => x.total));
  return (
    <>
      <PageHead
        eyebrow="OPERACIÓN DEL LABORATORIO"
        title={data?.personal ? "Mi carga de trabajo" : "Carga actual"}
        description={
          data?.personal
            ? "Tus ensayos asignados: avance, observaciones y próximas fechas."
            : "Ensayos abiertos en solicitudes aprobadas. Cantidades de ensayos, sin estimaciones de horas."
        }
      />
      <ErrorBox>{error}</ErrorBox>
      {data ? (
        <>
          <div className="stats-grid">
            {[
              [data.totals.open, "Ensayos abiertos", "/work?metric=open"],
              [data.totals.overdue, "Ensayos vencidos", "/work?metric=overdue"],
              data.personal
                ? [
                    data.totals.running,
                    "En ejecución",
                    "/work?assay_status=RUNNING",
                  ]
                : [
                    data.totals.unassigned,
                    "Sin técnico asignado",
                    "/work?metric=unassigned",
                  ],
              data.personal
                ? [
                    data.totals.observed,
                    "Ensayos observados",
                    "/work?assay_status=OBSERVED",
                  ]
                : [
                    data.totals.pending_samples,
                    "Muestras sin recibir",
                    "/reception?condition=NOT_RECEIVED",
                  ],
            ].map(([n, label, to]) => (
              <Link key={label} to={to} className="stat-card">
                <div>
                  <strong>{n}</strong>
                  <span>{label}</span>
                </div>
              </Link>
            ))}
          </div>
          {data.economics && <EconomicDashboard data={data.economics} />}
          <div className="chart-grid">
            <section className="card form-card">
              <h2>Carga abierta por tipo de ensayo</h2>
              <div className="chart-legend">
                {states.map((s) => (
                  <span key={s}>
                    <i style={{ background: colors[s] }} />
                    {labels[s]}
                  </span>
                ))}
              </div>
              {types.length ? (
                types.map((t) => (
                  <Link
                    className="bar-row"
                    key={t.id}
                    to={"/work?metric=open&assay=" + t.id}
                  >
                    <div className="bar-caption">
                      <span>{t.name}</span>
                      <b>{t.total}</b>
                    </div>
                    <div className="bar-track">
                      {states.map((s) => (
                        <span
                          key={s}
                          title={labels[s] + ": " + (t[s] || 0)}
                          aria-label={labels[s] + ": " + (t[s] || 0)}
                          style={{
                            width: ((t[s] || 0) / max) * 100 + "%",
                            background: colors[s],
                          }}
                        />
                      ))}
                    </div>
                    <small>
                      {states
                        .filter((s) => t[s])
                        .map((s) => labels[s] + ": " + t[s])
                        .join(" · ")}
                    </small>
                  </Link>
                ))
              ) : (
                <Empty>No hay ensayos abiertos.</Empty>
              )}
            </section>
            <section className="card form-card">
              <h2>
                {data.personal
                  ? "Estado de mis ensayos abiertos"
                  : "Distribución por técnico"}
              </h2>
              {(data.personal
                ? states.map((state) => ({
                    id: state,
                    name: labels[state],
                    count: data.by_type
                      .filter((t) => t.state === state)
                      .reduce((n, t) => n + Number(t.count), 0),
                  }))
                : data.by_technician
              ).map((t) => (
                <Link
                  key={t.id || "unassigned"}
                  className="bar-row"
                  to={
                    data.personal
                      ? "/work?metric=open&assay_status=" +
                        (t.id === "PENDING" ? "PENDING_EXECUTION" : t.id)
                      : "/work?metric=open&technician=" + (t.id || "unassigned")
                  }
                >
                  <div className="bar-caption">
                    <span>{t.name}</span>
                    <b>{t.count}</b>
                  </div>
                  <progress
                    max={Math.max(1, Number(data.totals.open))}
                    value={t.count}
                  />
                </Link>
              ))}
              <p className="muted">
                Incluye material pendiente de recepción. Consulta la condición
                de cada muestra antes de iniciar.
              </p>
            </section>
            <section className="card form-card">
              <h2>Completados por semana</h2>
              <p className="muted">
                Últimas ocho semanas · semana actual en curso
              </p>
              <div className="week-chart">
                {data.weekly.map((w) => (
                  <div className="week-column" key={w.week}>
                    <strong>{w.count}</strong>
                    <div
                      className="week-bar"
                      style={{
                        height: Math.max(
                          2,
                          (Number(w.count) /
                            Math.max(
                              1,
                              ...data.weekly.map((x) => Number(x.count)),
                            )) *
                            140,
                        ),
                      }}
                    />
                    <small>
                      {w.week.slice(5).split("-").reverse().join("/")}
                    </small>
                  </div>
                ))}
              </div>
              <p className="muted">Fecha de inicio de semana (Lima).</p>
            </section>
            <section className="card form-card">
              <h2>Próximos vencimientos</h2>
              {data.upcoming.length ? (
                data.upcoming.map((t) => (
                  <Link
                    className="due-row"
                    key={t.id}
                    to={detailUrl(t.request_id, "work", "/")}
                  >
                    <div>
                      <b>{t.name}</b>
                      <small className="block">
                        {t.request_code} · {t.client_code}
                      </small>
                    </div>
                    <span>{fmtDate(t.planned_end)}</span>
                  </Link>
                ))
              ) : (
                <Empty>No hay fechas próximas.</Empty>
              )}
              <Link className="text-link" to="/work?metric=upcoming">
                Ver todos los próximos vencimientos →
              </Link>
            </section>
          </div>
        </>
      ) : loading ? (
        <Loading>Cargando indicadores…</Loading>
      ) : (
        <Button onClick={() => setRetry((n) => n + 1)}>
          Reintentar consulta
        </Button>
      )}
    </>
  );
}
