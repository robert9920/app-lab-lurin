import { describe, expect, it } from "vitest";
import {
  assayStatus,
  assayStatuses,
  countLabel,
  requestStatuses,
} from "./statuses";

describe("estados compartidos", () => {
  it("separa la revisión de la ejecución sin contar dos veces", () => {
    expect(assayStatus({ state: "CANCELLED", review_status: "PENDING" })).toBe(
      "CANCELLED",
    );
    expect(assayStatus({ state: "PENDING", review_status: "REJECTED" })).toBe(
      "REJECTED",
    );
    expect(assayStatus({ state: "PENDING", review_status: "PENDING" })).toBe(
      "PENDING_REVIEW",
    );
    expect(assayStatus({ state: "PENDING", review_status: "APPROVED" })).toBe(
      "PENDING_EXECUTION",
    );
    expect(assayStatus({ row_kind: "sample_without_assays" })).toBe(
      "WAITING_ASSAYS",
    );
    for (const state of ["RUNNING", "OBSERVED", "COMPLETED"])
      expect(assayStatus({ state, approved: true })).toBe(state);
  });
  it("presenta cantidades y distingue muestras de ensayos", () => {
    expect(countLabel("PENDING_REVIEW", 2)).toBe("2 por aprobar");
    expect(countLabel("PENDING_EXECUTION", 1)).toBe("1 pendiente ejecución");
    expect(countLabel("REJECTED", 2)).toBe("2 rechazados");
    expect(countLabel("WAITING_ASSAYS", 1)).toBe(
      "1 muestra pendiente de ensayos",
    );
    expect(countLabel("WAITING_ASSAYS", 2)).toBe(
      "2 muestras pendientes de ensayos",
    );
    expect(assayStatuses).toHaveLength(8);
    expect(requestStatuses.map((s) => s.name)).toEqual([
      "Creado",
      "Cancelado",
      "Cerrado",
    ]);
  });
});
