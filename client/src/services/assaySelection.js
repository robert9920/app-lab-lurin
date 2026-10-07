export function availableAssays(catalog, query = "", category = "") {
  const needle = query.trim().toLocaleLowerCase("es");
  return catalog.filter(
    (a) =>
      a.active &&
      (!category || a.category === category) &&
      [a.name, a.code, a.method].some((v) =>
        String(v || "")
          .toLocaleLowerCase("es")
          .includes(needle),
      ),
  );
}
export const formatDepth = (value) =>
  value === "" || value == null
    ? ""
    : Number.isFinite(Number(value))
      ? Number(value).toFixed(2)
      : value;
export const formatMoney = (value) =>
  new Intl.NumberFormat("es-PE", { style: "currency", currency: "USD" }).format(
    Number(value),
  );
