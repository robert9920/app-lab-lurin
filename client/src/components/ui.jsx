import { assayStatuses, countLabel } from "../services/statuses";
import { useNetworkBusy } from "../services/api";
import { X, LoaderCircle, Inbox, ArrowUpRight } from "lucide-react";
import { cloneElement, isValidElement, useId } from "react";
export const labels = {
  CREATED: "Creado",
  PENDING_REVIEW: "Por aprobar",
  PENDING_EXECUTION: "Pendiente Ejecución",
  DRAFT: "Borrador",
  WAITING_ASSAYS: "Pendiente de ensayos",
  SUBMITTED: "En revisión",
  OBSERVED: "Observado",
  APPROVED: "Aprobado",
  REJECTED: "Rechazado",
  CLOSED: "Cerrado",
  PENDING: "Pendiente",
  RUNNING: "En ejecución",
  COMPLETED: "Completado",
  CANCELLED: "Cancelado",
  OK: "Conforme",
  DAMAGED: "Dañado",
  INSUFFICIENT: "Insuficiente",
  NOT_RECEIVED: "No recibida",
  MANAGER: "Jefe / supervisor",
  TECH: "Técnico",
  CLIENT: "Cliente",
  ADMIN: "Administrador",
};
export function Badge({ state, children }) {
  return (
    <span className={`badge badge-${state}`}>
      <i />
      {children || labels[state] || state}
    </span>
  );
}
export function Button({ children, variant = "", busy = false, ...props }) {
  return (
    <button
      className={`btn ${variant}`}
      {...props}
      disabled={busy || props.disabled}
    >
      {busy && <LoaderCircle size={16} className="spin" />}
      {children}
    </button>
  );
}
export function Field({ label, children, hint }) {
  const generatedId = useId();
  const id = children?.props?.id || generatedId;
  return (
    <div className="field">
      <label htmlFor={id}>
        <span>{label}</span>
      </label>
      {isValidElement(children) ? cloneElement(children, { id }) : children}
      {hint && <small>{hint}</small>}
    </div>
  );
}
export function Empty({ children = "Todavía no hay registros." }) {
  return (
    <div className="empty">
      <Inbox size={32} />
      <p>{children}</p>
    </div>
  );
}
export function ErrorBox({ children, inline = false }) {
  const Tag = inline ? "small" : "div";
  const message = children?.message ?? children;
  return children ? (
    <Tag
      key={children?.id ?? message}
      role="alert"
      className={`${inline ? "cell-error" : "error-box"} transient-error`}
    >
      {message}
    </Tag>
  ) : null;
}
export function Modal({ title, children, onClose }) {
  return (
    <div
      className="modal-back"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onKeyDown={(e) => {
          if (e.key === "Escape") onClose();
        }}
      >
        <header>
          <h2>{title}</h2>
          <button className="icon-btn" aria-label="Cerrar" onClick={onClose}>
            <X />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
export function PageHead({ eyebrow, title, description, children }) {
  return (
    <div className="page-head">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      <div className="actions">{children}</div>
    </div>
  );
}
export function CardTitle({ children, aside }) {
  return (
    <div className="card-title">
      <h2>{children}</h2>
      {aside || <ArrowUpRight size={18} />}
    </div>
  );
}
export const fmtDate = (value) =>
  value
    ? new Intl.DateTimeFormat("es-PE", {
        dateStyle: "medium",
        timeZone: "America/Lima",
      }).format(
        new Date(value.length === 10 ? `${value}T12:00:00-05:00` : value),
      )
    : "Sin fecha";

export function Loading({ children = "Cargando…", compact = false }) {
  return (
    <div
      className={`loading-state ${compact ? "compact" : ""}`}
      role="status"
      aria-live="polite"
    >
      <LoaderCircle className="spin" size={20} aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}
export function NetworkLoading() {
  const busy = useNetworkBusy();
  return busy ? (
    <div className="network-loading">
      <Loading compact>Actualizando información…</Loading>
    </div>
  ) : null;
}
export function RequestBadges({
  request,
  includeRequest = true,
  legacy = false,
}) {
  if (legacy)
    return (
      <div className="status-stack">
        <Badge state={request.status} />
        {request.status === "WAITING_ASSAYS" &&
          request.unapproved_count > 0 && <Badge state="SUBMITTED" />}
        {(request.pending_assays || request.undefined_samples > 0) &&
          request.status !== "WAITING_ASSAYS" && (
            <Badge state="WAITING_ASSAYS">Ensayos pendientes de definir</Badge>
          )}
        {request.status === "APPROVED" && request.unapproved_count > 0 && (
          <Badge state="PENDING">{request.unapproved_count} por aprobar</Badge>
        )}
      </div>
    );
  return (
    <div className="status-stack assay-counts">
      {includeRequest && <Badge state={request.request_status} />}
      {assayStatuses.map(({ id }) => {
        const n = Number(request.assay_counts?.[id] || 0);
        return n > 0 ? (
          <Badge key={id} state={id}>
            {countLabel(id, n)}
          </Badge>
        ) : null;
      })}
    </div>
  );
}

export function ReceptionBadges({ request }) {
  const conditions = [
    ["NOT_RECEIVED", "sin recibir", "sin recibir"],
    ["OBSERVED", "observada", "observadas"],
    ["DAMAGED", "dañada", "dañadas"],
    ["INSUFFICIENT", "insuficiente", "insuficientes"],
  ];
  return (
    <div className="status-stack">
      {conditions.map(([state, singular, plural]) => {
        const n = Number(request.reception_counts?.[state] || 0);
        return n > 0 ? (
          <Badge key={state} state={state}>
            {n} {n === 1 ? singular : plural}
          </Badge>
        ) : null;
      })}
      {!request.codigo_ot && <Badge state="NOT_RECEIVED">Sin OT</Badge>}
    </div>
  );
}

export function ClearFilters({ setParams, onClear }) {
  return (
    <Button
      type="button"
      onClick={() => {
        setParams(new URLSearchParams(), { replace: true });
        onClear();
      }}
    >
      Borrar filtros
    </Button>
  );
}
