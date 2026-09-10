import axios from "axios";
let csrf = "";
export function setCsrf(value) {
  csrf = value || "";
}
export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  timeout: 60000,
});
api.interceptors.request.use((config) => {
  if (config.method !== "get" && csrf) config.headers["X-CSRF-Token"] = csrf;
  return config;
});
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (
      error.response?.status === 401 &&
      !error.config?.url?.startsWith("/auth/login")
    )
      window.dispatchEvent(new Event("session-expired"));
    return Promise.reject(error);
  },
);
export const messageOf = (e) =>
  e.response?.data?.error ||
  "No fue posible conectar con el laboratorio. Inténtalo nuevamente.";
export async function fetchPdf(path, name, preview = false) {
  const popup = preview ? window.open("about:blank", "_blank") : null;
  if (popup) popup.opener = null;
  try {
    const { data } = await api.get(path, { responseType: "blob" });
    const url = URL.createObjectURL(
      new Blob([data], { type: "application/pdf" }),
    );
    if (popup) popup.location.href = url;
    else {
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (error) {
    if (popup) popup.close();
    throw error;
  }
}
export function download(id, name, preview = false) {
  return fetchPdf(`/reports/${id}/download`, name, preview);
}
