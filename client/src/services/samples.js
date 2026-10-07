export const blankSample = () => ({
  client_code: "",
  borehole: "",
  material: "",
  depth_from: "",
  depth_to: "",
  quantity: "",
  weight: "",
  easting: "",
  northing: "",
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
        easting = "",
        northing = "",
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
        easting,
        northing,
      };
    });
}
export function prepareSample(s) {
  const nullable = (v) => (v === "" || v == null ? null : Number(v));
  // Decimal strings preserve PostgreSQL precision beyond JavaScript's float range.
  const depth = (v) => (v === "" || v == null ? null : String(v));
  return {
    ...(s.id ? { id: s.id } : {}),
    client_code: s.client_code,
    borehole: s.borehole,
    material: s.material,
    depth_from: depth(s.depth_from),
    depth_to: depth(s.depth_to),
    quantity: nullable(s.quantity),
    weight: depth(s.weight),
    easting: nullable(s.easting),
    northing: nullable(s.northing),
    notes: s.notes,
    assay_ids: s.assay_ids,
  };
}
export function hasSampleData(s) {
  return Object.entries(s).some(([key, value]) =>
    key === "id"
      ? !!value
      : Array.isArray(value)
        ? value.length > 0
        : value != null && String(value).trim() !== "",
  );
}

export function sampleErrors(s, rows, { required = true } = {}) {
  const errors = {};
  if (required && !s.client_code.trim())
    errors.client_code = "Indica la muestra.";
  else if (
    s.client_code.trim() &&
    rows.filter((r) => r.client_code.trim() === s.client_code.trim()).length > 1
  )
    errors.client_code = "Código repetido.";
  if (required && !s.material.trim()) errors.material = "Indica el tipo.";
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
    errors.quantity = "Recipientes enteros.";
  if (
    s.weight !== "" &&
    s.weight != null &&
    Math.abs(Number(s.weight) * 10 - Math.round(Number(s.weight) * 10)) > 1e-8
  )
    errors.weight = "Peso: máximo un decimal.";
  for (const [key, low, high, name] of [
    ["easting", 100000, 1000000, "Este"],
    ["northing", 1000000, 10000000, "Norte"],
  ]) {
    if (
      s[key] !== "" &&
      s[key] != null &&
      (!Number.isFinite(Number(s[key])) ||
        Number(s[key]) < low ||
        Number(s[key]) >= high)
    )
      errors[key] =
        `Coordenadas ${name}: ${key === "easting" ? 6 : 7} dígitos enteros.`;
  }
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
