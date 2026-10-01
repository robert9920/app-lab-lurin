const fields = {
  users: ["name", "email", "phone", "password", "organization_id", "roles"],
  organizations: ["name", "tax_id", "active", "is_internal"],
  catalog: ["code", "name", "method", "category", "active"],
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
