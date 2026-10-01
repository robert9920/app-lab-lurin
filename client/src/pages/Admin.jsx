import { useEffect, useState, useCallback } from "react";
import { Plus, Users, Building2, TestTubes } from "lucide-react";
import { api, messageOf } from "../services/api";
import {
  PageHead,
  Button,
  Field,
  Modal,
  ErrorBox,
  Badge,
  labels,
} from "../components/ui";
export default function Admin() {
  const [data, setData] = useState(null),
    [tab, setTab] = useState("users"),
    [modal, setModal] = useState(""),
    [form, setForm] = useState({}),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const refresh = useCallback(
    () =>
      api
        .get("/management/data")
        .then((r) => setData(r.data))
        .catch((e) => setError(messageOf(e))),
    [],
  );
  useEffect(() => {
    refresh();
  }, [refresh]);
  function open(type, item = {}) {
    setError("");
    setModal(type);
    setForm(
      type === "users"
        ? {
            name: "",
            email: "",
            phone: "",
            password: "",
            organization_id: "",
            roles: ["CLIENT"],
            active: true,
            ...item,
          }
        : type === "organizations"
          ? { name: "", tax_id: "", active: true, is_internal: false, ...item }
          : type === "password"
            ? { password: "", confirm: "", ...item }
            : {
                code: "",
                name: "",
                method: "",
                category: "Geotecnia",
                active: true,
                ...item,
              },
    );
  }
  function change(k, v) {
    setForm({ ...form, [k]: v });
  }
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      let payload;
      if (modal === "password") {
        if (form.password !== form.confirm)
          throw new Error("Las contraseñas no coinciden.");
        await api.post(`/management/users/${form.id}/password`, {
          password: form.password,
        });
      } else {
        const keys =
          modal === "users"
            ? [
                "name",
                "email",
                "phone",
                "organization_id",
                "roles",
                ...(form.id ? ["active"] : ["password"]),
              ]
            : modal === "organizations"
              ? ["name", "tax_id", "active", "is_internal"]
              : ["code", "name", "method", "category", "active"];
        payload = Object.fromEntries(keys.map((k) => [k, form[k]]));
        if (modal === "users") {
          payload.organization_id ||= null;
          payload.phone ||= null;
        }
        const editing = !!form.id && modal !== "catalog";
        await api[editing ? "put" : "post"](
          `/management/${modal}${editing ? "/" + form.id : ""}`,
          payload,
        );
      }
      setModal("");
      await refresh();
    } catch (e) {
      setError(e.response ? messageOf(e) : e.message);
    } finally {
      setBusy(false);
    }
  }
  function field(k, l, { type = "text", required = false, max = 200 } = {}) {
    return (
      <Field label={l}>
        <input
          type={type}
          required={required}
          maxLength={max}
          minLength={type === "password" ? 15 : undefined}
          autoComplete={type === "password" ? "new-password" : undefined}
          value={form[k] || ""}
          onChange={(e) => change(k, e.target.value)}
        />
      </Field>
    );
  }
  if (!data) return <ErrorBox>{error}</ErrorBox>;
  return (
    <>
      <PageHead
        eyebrow="CONFIGURACIÓN DEL LABORATORIO"
        title="Administración"
        description="Gestiona empresas, personas y permisos de acceso."
      >
        <Button variant="primary" onClick={() => open(tab)}>
          <Plus size={17} />
          {tab === "users" ? "Crear usuario" : "Agregar registro"}
        </Button>
      </PageHead>
      <ErrorBox>{error}</ErrorBox>
      <div className="tabs">
        {[
          ["users", "Usuarios", Users],
          ["organizations", "Empresas", Building2],
          ["catalog", "Catálogo", TestTubes],
        ].map(([k, l, Icon]) => (
          <button
            key={k}
            className={tab === k ? "active" : ""}
            onClick={() => setTab(k)}
          >
            <Icon size={16} />
            {l}
          </button>
        ))}
      </div>
      <section className="card admin-table">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>
                  {tab === "users"
                    ? "Correo / teléfono / empresa"
                    : tab === "catalog"
                      ? "Método"
                      : "Identificación tributaria"}
                </th>
                <th>Permisos / clasificación</th>
                <th>Estado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data[tab].map((x) => (
                <tr key={x.id}>
                  <td>
                    <b>{x.name}</b>
                  </td>
                  <td>
                    {x.email || x.method || x.tax_id || "—"}
                    {x.phone && <small className="block">{x.phone}</small>}
                    {tab === "users" && (
                      <small className="block">
                        {data.organizations.find(
                          (o) => o.id === x.organization_id,
                        )?.name || "Sin empresa"}
                      </small>
                    )}
                  </td>
                  <td>
                    {x.roles
                      ? x.roles.map((r) => labels[r]).join(" · ")
                      : tab === "organizations"
                        ? x.is_internal
                          ? "Empresa interna"
                          : "Empresa externa"
                        : x.category}
                  </td>
                  <td>
                    <Badge state={x.active ? "OK" : "CANCELLED"}>
                      {x.active ? "Habilitado" : "Deshabilitado"}
                    </Badge>
                  </td>
                  <td>
                    <div className="actions">
                      <Button onClick={() => open(tab, x)}>Editar</Button>
                      {tab === "users" && (
                        <Button onClick={() => open("password", { id: x.id })}>
                          Restablecer contraseña
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {modal && (
        <Modal
          title={
            modal === "password"
              ? "Restablecer contraseña"
              : (form.id ? "Editar " : "Crear ") +
                (modal === "users"
                  ? "usuario"
                  : modal === "organizations"
                    ? "empresa"
                    : "ensayo")
          }
          onClose={() => setModal("")}
        >
          <form className="modal-body" onSubmit={save}>
            <ErrorBox>{error}</ErrorBox>
            {modal !== "password" &&
              field("name", "Nombre *", { required: true })}
            {modal === "users" && (
              <>
                {field("email", "Correo electrónico *", {
                  type: "email",
                  required: true,
                })}
                {field("phone", "Teléfono (opcional)", {
                  type: "tel",
                  max: 30,
                })}
                <Field label="Empresa">
                  <select
                    value={form.organization_id || ""}
                    required={form.roles.includes("CLIENT")}
                    onChange={(e) => change("organization_id", e.target.value)}
                  >
                    <option value="">Sin empresa</option>
                    {data.organizations
                      .filter((o) => o.active || o.id === form.organization_id)
                      .map((o) => (
                        <option key={o.id} value={o.id}>
                          {o.name}
                          {o.is_internal ? " · Interna" : ""}
                        </option>
                      ))}
                  </select>
                </Field>
                <fieldset className="roles-field">
                  <legend>Roles</legend>
                  {["CLIENT", "TECH", "MANAGER", "ADMIN"].map((r) => (
                    <label className="check-label" key={r}>
                      <input
                        type="checkbox"
                        checked={form.roles.includes(r)}
                        onChange={(e) =>
                          change(
                            "roles",
                            e.target.checked
                              ? [...form.roles, r]
                              : form.roles.filter((v) => v !== r),
                          )
                        }
                      />
                      {labels[r]}
                    </label>
                  ))}
                </fieldset>
              </>
            )}
            {((modal === "users" && !form.id) || modal === "password") &&
              field("password", "Contraseña (mínimo 15 caracteres)", {
                type: "password",
                required: true,
                max: 128,
              })}
            {modal === "password" &&
              field("confirm", "Repetir contraseña", {
                type: "password",
                required: true,
                max: 128,
              })}
            {modal === "organizations" && (
              <>
                {field("tax_id", "Identificación tributaria (opcional)", {
                  max: 30,
                })}
                <label className="check-label">
                  <input
                    type="checkbox"
                    checked={form.is_internal}
                    onChange={(e) => change("is_internal", e.target.checked)}
                  />
                  Es la empresa interna
                </label>
                <p className="muted">
                  Solo puede haber una empresa interna. Sus clientes seleccionan
                  proyectos de AppControlHH; las demás empresas usan solicitudes
                  externas.
                </p>
              </>
            )}
            {modal === "catalog" && (
              <>
                {field("code", "Código *", { required: true, max: 30 })}
                {field("method", "Método (opcional)")}
                {field("category", "Categoría *", { required: true, max: 100 })}
              </>
            )}
            {(modal === "organizations" ||
              modal === "catalog" ||
              (modal === "users" && form.id)) && (
              <label className="check-label">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(e) => change("active", e.target.checked)}
                />
                {modal === "users"
                  ? "Cuenta habilitada"
                  : "Registro habilitado"}
              </label>
            )}
            <div className="form-actions">
              <Button onClick={() => setModal("")} type="button">
                Cancelar
              </Button>
              <Button
                variant="primary"
                busy={busy}
                disabled={modal === "users" && !form.roles.length}
              >
                Guardar registro
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
