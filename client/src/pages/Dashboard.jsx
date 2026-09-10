import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { api, messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  PageHead,
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
  const [params, setParams] = useSearchParams(),
    location = useLocation();
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [projects, setProjects] = useState([]);
  const reception = mode === "reception";
  const query = params.toString();
  useEffect(() => {
    api
      .get("/projects")
      .then((r) => setProjects(r.data))
      .catch((e) => setError(messageOf(e)));
  }, []);
  useEffect(() => {
    let active = true;
    setData(null);
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
      });
    return () => {
      active = false;
    };
  }, [query, reception]);
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
            ? "Solicitudes aprobadas con muestras pendientes u observadas. Registra únicamente las que llegaron."
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
      <div className="card form-card">
        <div className="form-grid">
          <Field label="Buscar solicitud">
            <input
              placeholder="Código, título o proyecto"
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
          {reception && (
            <Field label="Estado de recepción">
              <select
                value={params.get("condition") || ""}
                onChange={(e) => filter("condition", e.target.value)}
              >
                <option value="">Todas por atender</option>
                <option value="NOT_RECEIVED">Con muestras sin recibir</option>
                <option value="issues">
                  Con muestras observadas, dañadas o insuficientes
                </option>
              </select>
            </Field>
          )}
          {!reception && (
            <Field label="Estado">
              <select
                value={params.get("status") || ""}
                onChange={(e) => filter("status", e.target.value)}
              >
                <option value="">Todos los estados</option>
                {[
                  ...(!user.roles.some((r) =>
                    ["ADMIN", "MANAGER", "TECH"].includes(r),
                  )
                    ? ["DRAFT"]
                    : []),
                  "SUBMITTED",
                  "OBSERVED",
                  "APPROVED",
                  "REJECTED",
                  "CLOSED",
                ].map((s) => (
                  <option key={s} value={s}>
                    {labels[s]}
                  </option>
                ))}
              </select>
            </Field>
          )}
        </div>
      </div>
      <section className="card section-gap">
        {!data ? (
          <p className="form-card">Cargando solicitudes…</p>
        ) : data.items.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Solicitud / proyecto</th>
                  <th>Estado</th>
                  <th>
                    {reception ? "Muestras por atender" : "Avance de ensayos"}
                  </th>
                  <th>Fecha objetivo</th>
                  <th />
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
                        <span>{r.title}</span>
                        <small>{r.project_code}</small>
                      </Link>
                    </td>
                    <td>
                      <Badge state={r.status} />
                    </td>
                    <td>
                      {reception ? (
                        r.pending_samples
                      ) : (
                        <>
                          <span>
                            {r.completed_count} de {r.task_count}
                          </span>
                          <progress
                            max={r.task_count || 1}
                            value={r.completed_count}
                          />
                        </>
                      )}
                    </td>
                    <td>{fmtDate(r.target_date)}</td>
                    <td>
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
    [error, setError] = useState("");
  useEffect(() => {
    if (canView)
      api
        .get("/dashboard")
        .then((r) => setData(r.data))
        .catch((e) => setError(messageOf(e)));
  }, [canView]);
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
                ? [data.totals.running, "En ejecución", "/work?state=RUNNING"]
                : [
                    data.totals.unassigned,
                    "Sin técnico asignado",
                    "/work?metric=unassigned",
                  ],
              data.personal
                ? [
                    data.totals.observed,
                    "Ensayos observados",
                    "/work?state=OBSERVED",
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
                      ? "/work?metric=open&state=" + t.id
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
      ) : (
        !error && <p>Cargando indicadores…</p>
      )}
    </>
  );
}
