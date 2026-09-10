import { describe, it, expect } from "vitest";
import { safeReturn, detailUrl } from "./navigation";
describe("navegación persistente", () => {
  it("conserva la sección y los filtros", () => {
    const url = detailUrl("id", "work", "/work?state=RUNNING&project=one");
    const query = new URLSearchParams(url.split("?")[1]);
    expect(query.get("tab")).toBe("work");
    expect(query.get("from")).toBe("/work?state=RUNNING&project=one");
  });
  it("rechaza destinos externos o desconocidos", () => {
    for (const value of [
      "//evil.test",
      "https://evil.test",
      "/requests/1",
      "/admin",
      null,
    ])
      expect(safeReturn(value)).toBe("/requests");
  });
});
