export const blankSample = () => ({
  client_code: "",
  borehole: "",
  material: "Suelo",
  depth_from: "",
  depth_to: "",
  quantity: "",
  unit: "kg",
  notes: "",
  assay_ids: [],
});
export function parseSamples(text) {
  return text
    .trim()
    .split(/\r?\n/)
    .filter(Boolean)
    .map((row) => {
      const [
        client_code = "",
        borehole = "",
        depth_from = "",
        depth_to = "",
        quantity = "",
        unit = "kg",
        notes = "",
      ] = row.split("\t");
      return {
        ...blankSample(),
        client_code,
        borehole,
        depth_from,
        depth_to,
        quantity,
        unit,
        notes,
      };
    });
}
export function prepareSample(s) {
  return {
    ...s,
    depth_from: s.depth_from === "" ? null : Number(s.depth_from),
    depth_to: s.depth_to === "" ? null : Number(s.depth_to),
    quantity: s.quantity === "" ? null : Number(s.quantity),
  };
}
