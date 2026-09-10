import { describe, it, expect } from "vitest";
import { parseSamples, prepareSample } from "./samples";
describe("Ingreso de muestras", () => {
  it("preserva códigos, cantidades desconocidas y ceros al pegar Excel", () => {
    const [s] = parseSamples(
      "M-01\tDH-01\t0\t2.5\t\tkg\tMuestra sin masa informada",
    );
    const r = prepareSample(s);
    expect(r.client_code).toBe("M-01");
    expect(r.depth_from).toBe(0);
    expect(r.depth_to).toBe(2.5);
    expect(r.quantity).toBeNull();
    expect(r.assay_ids).toEqual([]);
  });
  it("lee varias filas sin tratarlas como un ensayo individual", () => {
    expect(parseSamples("A\tS1\r\nB\tS2")).toHaveLength(2);
  });
});
