import { describe, it, expect } from "vitest";
import {
  blankSample,
  parseSamples,
  prepareSample,
  sampleErrors,
  hasSampleData,
} from "./samples";
describe("Muestras horizontales", () => {
  it("conserva filas parciales y valida valores informados sin exigir datos de envío", () => {
    expect(hasSampleData(blankSample())).toBe(false);
    const partial = { ...blankSample(), borehole: "DH-01" };
    expect(hasSampleData(partial)).toBe(true);
    expect(hasSampleData({ ...blankSample(), id: "existing" })).toBe(true);
    expect(sampleErrors(partial, [partial], { required: false })).toEqual({});
    expect(
      sampleErrors({ ...partial, weight: "1.11" }, [partial], {
        required: false,
      }),
    ).toHaveProperty("weight");
    expect(
      sampleErrors({ ...partial, northing: "123456" }, [partial], {
        required: false,
      }),
    ).toHaveProperty("northing");
    expect(sampleErrors(partial, [partial])).toHaveProperty("client_code");
  });
  it("separa sacos y kg y mantiene desconocidos y profundidad cero", () => {
    const [s] = parseSamples("DH-01\tM-01\t0\t2.5\tSuelo\t\t15.4\tNota");
    const r = prepareSample(s);
    expect(r.client_code).toBe("M-01");
    expect(r.depth_from).toBe("0");
    expect(r.depth_to).toBe("2.5");
    expect(r.quantity).toBeNull();
    expect(r.weight).toBe("15.4");
    expect(r.assay_ids).toEqual([]);
    expect(r).not.toHaveProperty("unit");
  });
  it("conserva la calicata vacía al pegar columnas opcionales", () => {
    const [s] = parseSamples("\tM-02\t\t\tRelaves\t2\t\t");
    expect(s.borehole).toBe("");
    expect(s.client_code).toBe("M-02");
    expect(s.material).toBe("Relaves");
    expect(s.quantity).toBe("2");
    expect(s.weight).toBe("");
  });
  it("envía el ID para conservar recepciones y excluye metadatos de servidor", () => {
    const r = prepareSample({
      ...blankSample(),
      id: "id",
      received_at: "date",
      client_code: "M",
      material: "Suelo",
    });
    expect(r.id).toBe("id");
    expect(r).not.toHaveProperty("received_at");
  });
  it("valida campos obligatorios, duplicados, sacos enteros y profundidades", () => {
    const s = {
      ...blankSample(),
      client_code: "M",
      material: "Suelo",
      quantity: "1.5",
      depth_from: "3",
      depth_to: "2",
    };
    const e = sampleErrors(s, [s, s]);
    expect(e.client_code).toBeTruthy();
    expect(e.quantity).toBeTruthy();
    expect(e.depth_to).toBeTruthy();
    const good = { ...blankSample(), client_code: "A", material: "Relaves" };
    expect(sampleErrors(good, [good])).toEqual({});
  });
});
