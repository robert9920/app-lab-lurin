import { useState } from "react";
import { formatMoney } from "../services/assaySelection";
import { Button, Empty } from "./ui";

function Breakdown({ title, rows }) {
  const [expanded, setExpanded] = useState(false);
  const max = Math.max(1, ...rows.map((r) => Number(r.amount)));
  return (
    <section className="card form-card">
      <h3>{title}</h3>
      {rows.length ? (
        <>
          {(expanded ? rows : rows.slice(0, 10)).map((r) => (
            <div className="bar-row" key={r.id}>
              <div className="bar-caption">
                <span>{r.name}</span>
                <b>{formatMoney(r.amount)}</b>
              </div>
              <progress
                max={max}
                value={Number(r.amount)}
                aria-label={`${r.name}: ${formatMoney(r.amount)}`}
              />
            </div>
          ))}
          {rows.length > 10 && (
            <Button onClick={() => setExpanded(!expanded)}>
              {expanded ? "Ver diez principales" : "Ver todos"}
            </Button>
          )}
        </>
      ) : (
        <Empty>No hay ensayos completados.</Empty>
      )}
    </section>
  );
}

export default function EconomicDashboard({ data }) {
  const max = Math.max(1, ...data.monthly.map((m) => Number(m.amount)));
  return (
    <section className="economic-dashboard">
      <h2>Ingresos estimados (USD)</h2>
      <p className="muted">
        Valor de los ensayos a precios vigentes del catálogo. Los cambios de
        precio recalculan también los importes anteriores.
      </p>
      <div className="stats-grid economic-stats">
        {[
          [data.totals.completed_total, "Completados · acumulado"],
          [data.totals.completed_month, "Completados · mes actual"],
          [
            data.totals.projected_total,
            "Proyección · trabajo aprobado abierto",
          ],
        ].map(([value, label]) => (
          <div className="stat-card" key={label}>
            <div>
              <strong>{formatMoney(value)}</strong>
              <span>{label}</span>
            </div>
          </div>
        ))}
      </div>
      <section className="card form-card">
        <h3>Valor completado por mes</h3>
        <p className="muted">Últimos doce meses · fechas de Lima</p>
        <div className="income-chart-scroll">
          <div className="week-chart income-months">
            {data.monthly.map((m) => (
              <div className="week-column" key={m.month}>
                <strong>{formatMoney(m.amount)}</strong>
                <div
                  className="week-bar"
                  aria-label={formatMoney(m.amount)}
                  style={{
                    height: Math.max(2, (Number(m.amount) / max) * 140),
                  }}
                />
                <small>
                  {new Intl.DateTimeFormat("es-PE", {
                    month: "short",
                    year: "2-digit",
                    timeZone: "America/Lima",
                  }).format(new Date(m.month + "T12:00:00Z"))}
                </small>
              </div>
            ))}
          </div>
        </div>
      </section>
      <div className="chart-grid">
        <Breakdown
          title="Valor completado por tipo de ensayo"
          rows={data.by_type}
        />
        <Breakdown
          title="Valor completado por empresa"
          rows={data.by_organization}
        />
      </div>
    </section>
  );
}
