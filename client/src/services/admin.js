const fields = {
  users: ["name", "email", "phone", "password", "organization_id", "roles"],
  organizations: ["name", "tax_id", "active", "is_internal"],
  catalog: ["code", "name", "method", "category", "price", "active"],
};
export function adminPayload(type, form) {
  const payload = Object.fromEntries(
    fields[type].map((key) => [key, form[key]]),
  );
  if (type === "users") {
    payload.organization_id ||= null;
    payload.phone ||= null;
  }
  return payload;
}

export function filterAdminRows(rows, filters, type) {
  const normalize = (text) =>
    text
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("es");
  const roles = (filters.role || "").split(",").filter(Boolean);
  return rows.filter(
    (row) =>
      (!filters.name ||
        normalize(row.name).includes(normalize(filters.name))) &&
      (!filters.active || String(row.active) === filters.active) &&
      (type !== "users" ||
        ((!filters.organization ||
          row.organization_id === filters.organization) &&
          (!roles.length || roles.some((r) => row.roles.includes(r))))) &&
      (type !== "catalog" ||
        !filters.category ||
        row.category === filters.category),
  );
}
