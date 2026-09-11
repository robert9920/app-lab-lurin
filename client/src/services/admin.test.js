import { describe, it, expect } from "vitest";
import { adminPayload, companySelection } from "./admin";
describe("administración y empresas", () => {
  const projects = [
    { id: "p1", organization_id: "a", active: true },
    { id: "p2", organization_id: "b", active: true },
    { id: "p3", organization_id: "a", active: false },
  ];
  it("proyecto no envía asignaciones del modal", () => {
    const form = companySelection(
      "projects",
      { name: "Proyecto", code: "P1", location: "Lurín" },
      "a",
      projects,
    );
    expect(form).not.toHaveProperty("project_ids");
    expect(adminPayload("projects", { ...form, project_ids: ["p1"] })).toEqual(
      form,
    );
  });
  it("preselecciona activos de la empresa y conserva exclusiones al guardar", () => {
    const form = companySelection(
      "users",
      { project_ids: ["p2"] },
      "a",
      projects,
    );
    expect(form.project_ids).toEqual(["p1"]);
    expect(
      adminPayload("users", { ...form, project_ids: [] }).project_ids,
    ).toEqual([]);
    expect(companySelection("users", form, "b", projects).project_ids).toEqual([
      "p2",
    ]);
    expect(companySelection("users", form, "", projects).project_ids).toEqual(
      [],
    );
  });
});
