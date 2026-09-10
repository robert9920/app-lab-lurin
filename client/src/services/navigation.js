export function safeReturn(value) {
  return /^\/(requests|reception|work|reports)(\?[^#]*)?$/.test(value || "") ||
    value === "/"
    ? value
    : "/requests";
}
export function detailUrl(id, tab, from) {
  return (
    "/requests/" +
    id +
    "?" +
    new URLSearchParams({ tab, from: safeReturn(from) })
  );
}
