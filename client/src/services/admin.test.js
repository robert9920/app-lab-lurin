import { describe, it, expect } from "vitest";
import { adminPayload } from "./admin";
describe("Administración sin membresías", () => {
  it("envía solo campos permitidos y conserva empresa y teléfono", () => {
    const p = adminPayload("users", {
      name: "Ana",
      email: "ana@example.com",
      phone: "+51 999123123",
      organization_id: "a",
      roles: ["CLIENT"],
      password: "private",
      project_ids: ["old"],
      id: "old",
    });
    expect(p).not.toHaveProperty("project_ids");
    expect(p).not.toHaveProperty("id");
    expect(p.phone).toBe("+51 999123123");
  });
  it("envía la clasificación explícita de la empresa", () => {
    expect(
      adminPayload("organizations", {
        name: "LC",
        tax_id: "",
        active: true,
        is_internal: true,
        unwanted: 1,
      }),
    ).toEqual({ name: "LC", tax_id: "", active: true, is_internal: true });
  });
});
