import { describe, expect, it } from "vitest";
import { availableAssays, formatDepth } from "./assaySelection";
import {
  blankSample,
  parseSamples,
  prepareSample,
  sampleErrors,
} from "./samples";
import { filterAdminRows } from "./admin";

describe("Esquema 8", () => {
  it("busca por nombre, código y método; solo habilitados y categoría combinada", () => {
    const list = [
      {
        id: "a",
        code: "LC-001",
        name: "Humedad",
        method: "ASTM D2216",
        category: "Suelo",
        active: true,
      },
      {
        id: "b",
        code: "LC-002",
        name: "Relaves",
        method: "Método B",
        category: "Relaves",
        active: false,
      },
    ];
    expect(availableAssays(list, "hum")[0].id).toBe("a");
    expect(availableAssays(list, "lc-001", "Suelo")).toHaveLength(1);
    expect(availableAssays(list, "d2216", "Relaves")).toHaveLength(0);
    expect(availableAssays(list, "relaves")).toHaveLength(0);
  });
  it("formatea profundidades sin cambiar el valor preparado ni inventar ceros", () => {
    expect(formatDepth("5")).toBe("5.00");
    expect(formatDepth("5.12345")).toBe("5.12");
    expect(formatDepth(null)).toBe("");
    expect(
      prepareSample({ ...blankSample(), depth_from: "5.12345" }).depth_from,
    ).toBe("5.12345");
    expect(
      prepareSample({ ...blankSample(), depth_from: "5.1234567890123456789" })
        .depth_from,
    ).toBe("5.1234567890123456789");
  });
  it("pega coordenadas independientes y valida peso sin redondear", () => {
    const [row] = parseSamples("DH\tM\t5\t6\tSuelo\t2\t1.2\tNota\t123456.7\t");
    expect(prepareSample(row).easting).toBe(123456.7);
    expect(prepareSample(row).northing).toBeNull();
    expect(sampleErrors(row, [row])).toEqual({});
    expect(
      sampleErrors({ ...row, weight: "1.23", northing: "999999" }, [row]),
    ).toHaveProperty("weight");
  });
  it("combina filtros administrativos y los roles mediante O", () => {
    const list = [
      { name: "Diego", organization_id: "a", roles: ["CLIENT"], active: true },
      { name: "Lucía", organization_id: "b", roles: ["TECH"], active: false },
    ];
    expect(
      filterAdminRows(
        list,
        { name: "DIE", organization: "a", role: "TECH,CLIENT", active: "true" },
        "users",
      ),
    ).toHaveLength(1);
    expect(filterAdminRows(list, { role: "ADMIN" }, "users")).toHaveLength(0);
    expect(filterAdminRows(list, {}, "users")).toHaveLength(2);
  });
});
