import { describe, it, expect } from "vitest";
import { adminPayload, filterAdminRows } from "./admin";
describe("Administración sin membresías", () => {
  it("busca nombres sin tildes ni diferencias de mayúsculas en las tres vistas", () => {
    for (const [type, name, query] of [
      ["users", "Lucía Torres", "LUCIA"],
      ["organizations", "Compañía Perú", "compania peru"],
      ["catalog", "Análisis Granulométrico", "analisis granulo"],
    ]) {
      const row = {
        name,
        active: true,
        roles: ["TECH"],
        organization_id: "a",
        category: "Suelos",
      };
      expect(
        filterAdminRows([row], { name: query, active: "true" }, type),
      ).toEqual([row]);
      expect(
        filterAdminRows([row], { name: query, active: "false" }, type),
      ).toEqual([]);
    }
  });
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
