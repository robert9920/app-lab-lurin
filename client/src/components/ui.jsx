import { X, LoaderCircle, Inbox, ArrowUpRight } from "lucide-react";
import { cloneElement, isValidElement, useId } from "react";
export const labels = {
  DRAFT: "Borrador",
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
export function ErrorBox({ children }) {
  return children ? (
    <div role="alert" className="error-box">
      {children}
    </div>
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
