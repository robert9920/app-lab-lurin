const fields = {
  projects: ["name", "organization_id", "code", "location"],
  users: [
    "name",
    "email",
    "password",
    "organization_id",
    "roles",
    "project_ids",
  ],
  organizations: ["name", "tax_id"],
  catalog: ["code", "name", "method", "category", "active"],
};
export function adminPayload(type, form) {
  const payload = Object.fromEntries(
    fields[type].map((key) => [key, form[key]]),
  );
  if (type === "users") payload.organization_id ||= null;
  return payload;
}
export function companySelection(type, form, organizationId, projects) {
  const next = { ...form, organization_id: organizationId };
  if (type === "users")
    next.project_ids = projects
      .filter((p) => p.active && p.organization_id === organizationId)
      .map((p) => p.id);
  if (type === "edit-user") next.project_ids = [];
  return next;
}
