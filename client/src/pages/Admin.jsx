import { useEffect, useState, useCallback } from "react";
import { Plus, Users, Building2, FolderKanban, TestTubes } from "lucide-react";
import { adminPayload, companySelection } from "../services/admin";
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
  function open(type, value = {}) {
    setError("");
    setForm(
      type === "users"
        ? {
            name: "",
            email: "",
            password: "",
            organization_id: "",
            roles: ["CLIENT"],
            project_ids: [],
            ...value,
          }
        : type === "projects"
          ? { organization_id: "", code: "", name: "", location: "", ...value }
          : type === "catalog"
            ? {
                code: "",
                name: "",
                method: "",
                category: "Geotecnia",
                active: true,
                ...value,
              }
            : { name: "", tax_id: "", ...value },
    );
    setModal(type);
  }
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    try {
      if (modal === "edit-user")
        await api.put(`/management/users/${form.id}`, {
          roles: form.roles,
          active: form.active,
          project_ids: form.project_ids,
          organization_id: form.organization_id || null,
        });
      else if (modal === "password") {
        if (form.password !== form.confirm)
          throw new Error("Las contraseñas no coinciden.");
        await api.post(`/management/users/${form.id}/password`, {
          password: form.password,
        });
      } else await api.post(`/management/${modal}`, adminPayload(modal, form));
      setModal("");
      await refresh();
    } catch (e) {
      setError(e.response ? messageOf(e) : e.message);
    } finally {
      setBusy(false);
    }
  }
  function field(key, label, type = "text") {
    return (
      <Field label={label}>
        <input
          type={type}
          minLength={
            type === "password"
              ? 15
              : modal === "projects" && key === "name"
                ? 3
                : key === "code" && modal === "projects"
                  ? 2
                  : undefined
          }
          maxLength={
            type === "password"
              ? 128
              : modal === "projects"
                ? key === "code"
                  ? 100
                  : 250
                : undefined
          }
          autoComplete={type === "password" ? "new-password" : undefined}
          required
          value={form[key] || ""}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
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
        description="Define quién puede ingresar y a qué proyectos tiene acceso."
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
          ["projects", "Proyectos", FolderKanban],
          ["catalog", "Catálogo", TestTubes],
        ].map(([k, t, Icon]) => (
          <button
            key={k}
            className={tab === k ? "active" : ""}
            onClick={() => setTab(k)}
          >
            <Icon size={16} />
            {t}
          </button>
        ))}
      </div>
      <section className="card">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>
                  {tab === "users"
                    ? "Correo / permisos"
                    : tab === "catalog"
                      ? "Método"
                      : "Código / empresa"}
                </th>
                <th>Estado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data[tab].map((item) => (
                <tr key={item.id}>
                  <td>
                    <b>{item.name}</b>
                  </td>
                  <td>
                    {item.email ||
                      item.method ||
                      item.code ||
                      item.tax_id ||
                      "—"}
                    {item.roles && (
                      <small className="block">
                        {item.roles.map((r) => labels[r]).join(" · ")}
                      </small>
                    )}
                  </td>
                  <td>
                    <Badge state={item.active === false ? "CANCELLED" : "OK"}>
                      {item.active === false
                        ? "Deshabilitado"
                        : item.activated === false
                          ? "Habilitado"
                          : "Habilitado"}
                    </Badge>
                  </td>
                  <td>
                    {tab === "users" && (
                      <div className="actions">
                        <Button
                          onClick={() => {
                            setForm(item);
                            setModal("edit-user");
                          }}
                        >
                          Permisos
                        </Button>
                        <Button
                          onClick={() => {
                            setForm({ id: item.id, password: "", confirm: "" });
                            setModal("password");
                          }}
                        >
                          Restablecer contraseña
                        </Button>
                      </div>
                    )}
                    {tab === "catalog" && (
                      <Button
                        onClick={() => {
                          const { code, name, method, category, active } = item;
                          open("catalog", {
                            code,
                            name,
                            method,
                            category,
                            active,
                          });
                        }}
                      >
                        Editar
                      </Button>
                    )}
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
            modal === "users"
              ? "Crear usuario"
              : modal === "edit-user"
                ? "Roles y proyectos"
                : modal === "password"
                  ? "Restablecer contraseña"
                  : "Guardar registro"
          }
          onClose={() => setModal("")}
        >
          <form className="modal-body" onSubmit={save}>
            <ErrorBox>{error}</ErrorBox>
            {!["edit-user", "password"].includes(modal) &&
              field("name", "Nombre")}
            {modal === "users" && field("email", "Correo electrónico", "email")}
            {["users", "password"].includes(modal) &&
              field(
                "password",
                "Contraseña (mínimo 15 caracteres)",
                "password",
              )}
            {modal === "password" &&
              field("confirm", "Repetir contraseña", "password")}
            {["users", "projects", "edit-user"].includes(modal) && (
              <Field label="Empresa">
                <select
                  required={
                    modal === "projects" || form.roles?.includes("CLIENT")
                  }
                  value={form.organization_id || ""}
                  onChange={(e) =>
                    setForm(
                      companySelection(
                        modal,
                        form,
                        e.target.value,
                        data.projects,
                      ),
                    )
                  }
                >
                  <option value="">Seleccionar empresa</option>
                  {data.organizations.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            {["users", "edit-user"].includes(modal) && (
              <>
                <span className="field-label">Roles</span>
                <div className="assay-chips">
                  {["CLIENT", "TECH", "MANAGER", "ADMIN"].map((role) => (
                    <label key={role}>
                      <input
                        type="checkbox"
                        checked={form.roles.includes(role)}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            roles: e.target.checked
                              ? [...form.roles, role]
                              : form.roles.filter((r) => r !== role),
                          })
                        }
                      />
                      {labels[role]}
                    </label>
                  ))}
                </div>
                <span className="field-label">Proyectos asignados</span>
                <div className="assay-chips">
                  {data.projects
                    .filter(
                      (p) =>
                        p.organization_id === form.organization_id &&
                        (p.active || form.project_ids.includes(p.id)),
                    )
                    .map((p) => (
                      <label key={p.id}>
                        <input
                          type="checkbox"
                          checked={form.project_ids.includes(p.id)}
                          onChange={(e) =>
                            setForm({
                              ...form,
                              project_ids: e.target.checked
                                ? [...form.project_ids, p.id]
                                : form.project_ids.filter((id) => id !== p.id),
                            })
                          }
                        />
                        {p.code}
                      </label>
                    ))}
                </div>
                {modal === "edit-user" && (
                  <label className="check-label">
                    <input
                      type="checkbox"
                      checked={form.active}
                      onChange={(e) =>
                        setForm({ ...form, active: e.target.checked })
                      }
                    />
                    Cuenta habilitada
                  </label>
                )}
                <p className="muted">
                  Los cambios revocan las sesiones existentes. Las contraseñas
                  nunca se muestran después de guardarlas.
                </p>
              </>
            )}
            {modal === "organizations" &&
              field("tax_id", "Identificación tributaria")}
            {["projects", "catalog"].includes(modal) && field("code", "Código")}
            {modal === "projects" && field("location", "Ubicación")}
            {modal === "catalog" && (
              <>
                {field("method", "Método / referencia")}
                {field("category", "Categoría")}
                <label className="check-label">
                  <input
                    type="checkbox"
                    checked={form.active}
                    onChange={(e) =>
                      setForm({ ...form, active: e.target.checked })
                    }
                  />
                  Ensayo habilitado
                </label>
              </>
            )}
            <div className="form-actions">
              <Button variant="primary" busy={busy}>
                {modal === "users" ? "Crear usuario" : "Guardar"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
