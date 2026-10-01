export const blankSample = () => ({
  client_code: "",
  borehole: "",
  material: "",
  depth_from: "",
  depth_to: "",
  quantity: "",
  weight: "",
  notes: "",
  assay_ids: [],
});
export function parseSamples(text) {
  return text
    .replace(/^[\r\n]+|[\r\n]+$/g, "")
    .split(/\r?\n/)
    .filter((row) => row.trim())
    .map((row) => {
      const [
        borehole = "",
        client_code = "",
        depth_from = "",
        depth_to = "",
        material = "",
        quantity = "",
        weight = "",
        notes = "",
      ] = row.split("\t");
      return {
        ...blankSample(),
        borehole,
        client_code,
        depth_from,
        depth_to,
        material,
        quantity,
        weight,
        notes,
      };
    });
}
export function prepareSample(s) {
  const nullable = (v) => (v === "" || v == null ? null : Number(v));
  return {
    ...(s.id ? { id: s.id } : {}),
    client_code: s.client_code,
    borehole: s.borehole,
    material: s.material,
    depth_from: nullable(s.depth_from),
    depth_to: nullable(s.depth_to),
    quantity: nullable(s.quantity),
    weight: nullable(s.weight),
    notes: s.notes,
    assay_ids: s.assay_ids,
  };
}
export function sampleErrors(s, rows) {
  const errors = {};
  if (!s.client_code.trim()) errors.client_code = "Indica la muestra.";
  else if (
    rows.filter((r) => r.client_code.trim() === s.client_code.trim()).length > 1
  )
    errors.client_code = "Código repetido.";
  if (!s.material.trim()) errors.material = "Indica el tipo.";
  for (const k of ["depth_from", "depth_to", "quantity", "weight"]) {
    if (
      s[k] !== "" &&
      s[k] != null &&
      (!Number.isFinite(Number(s[k])) ||
        Number(s[k]) < 0 ||
        (["quantity", "weight"].includes(k) && Number(s[k]) === 0))
    )
      errors[k] = "Revisa el valor.";
  }
  if (
    s.quantity !== "" &&
    s.quantity != null &&
    !Number.isInteger(Number(s.quantity))
  )
    errors.quantity = "Sacos enteros.";
  if (
    s.depth_from !== "" &&
    s.depth_to !== "" &&
    s.depth_from != null &&
    s.depth_to != null &&
    Number(s.depth_to) < Number(s.depth_from)
  )
    errors.depth_to = "Menor que inicial.";
  return errors;
}
