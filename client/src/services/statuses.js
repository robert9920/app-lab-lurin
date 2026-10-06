export const assayStatuses = [
  ["PENDING_REVIEW", "Por aprobar"],
  ["PENDING_EXECUTION", "Pendiente Ejecución"],
  ["RUNNING", "En Ejecución"],
  ["WAITING_ASSAYS", "Pendiente Ensayos"],
  ["REJECTED", "Rechazado"],
  ["COMPLETED", "Completado"],
  ["CANCELLED", "Cancelado"],
  ["OBSERVED", "Observado"],
].map(([id, name]) => ({ id, name }));

export const requestStatuses = [
  ["CREATED", "Creado"],
  ["CANCELLED", "Cancelado"],
  ["CLOSED", "Cerrado"],
].map(([id, name]) => ({ id, name }));

export function assayStatus(task) {
  if (task.row_kind === "sample_without_assays") return "WAITING_ASSAYS";
  if (task.state === "CANCELLED") return "CANCELLED";
  if (task.review_status === "REJECTED") return "REJECTED";
  if (task.review_status === "PENDING" || task.approved === false)
    return "PENDING_REVIEW";
  return task.state === "PENDING" ? "PENDING_EXECUTION" : task.state;
}

export function countLabel(status, n) {
  if (status === "WAITING_ASSAYS")
    return `${n} ${n === 1 ? "muestra pendiente" : "muestras pendientes"} de ensayos`;
  const labels = {
    PENDING_REVIEW: "por aprobar",
    PENDING_EXECUTION: n === 1 ? "pendiente ejecución" : "pendientes ejecución",
    RUNNING: "en ejecución",
    REJECTED: n === 1 ? "rechazado" : "rechazados",
    COMPLETED: n === 1 ? "completado" : "completados",
    CANCELLED: n === 1 ? "cancelado" : "cancelados",
    OBSERVED: n === 1 ? "observado" : "observados",
  };
  return `${n} ${labels[status]}`;
}
