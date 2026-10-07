import { useMemo, useState } from "react";
import { X } from "lucide-react";
import { availableAssays } from "../services/assaySelection";
import useErrorNotice from "../hooks/useErrorNotice";
import SearchSelect from "./SearchSelect";
import { Modal, Field, Button, Empty, ErrorBox } from "./ui";

export function SelectedAssays({ ids, catalog, locked = [], onRemove }) {
  return (
    <div className="selected-assays">
      {ids.length ? (
        ids.map((id) => {
          const assay = catalog.find((a) => a.id === id);
          return (
            <div className="selected-assay" key={id}>
              <div>
                <b>{assay?.name || "Ensayo registrado"}</b>
                <small className="block">
                  {assay?.method || "Método no indicado"}
                  {assay && !assay.active ? " · Deshabilitado" : ""}
                </small>
              </div>
              {onRemove && (
                <button
                  type="button"
                  className="icon-btn"
                  disabled={locked.includes(id)}
                  aria-label={`Retirar ${assay?.name || "ensayo"}`}
                  onClick={() => onRemove(id)}
                >
                  <X size={16} />
                </button>
              )}
            </div>
          );
        })
      ) : (
        <small>Sin ensayos definidos</small>
      )}
    </div>
  );
}

export default function AssayPicker({
  catalog,
  existing = [],
  onApply,
  onClose,
}) {
  const [query, setQuery] = useState(""),
    [category, setCategory] = useState(""),
    [selected, setSelected] = useState([]);
  const [error, setError] = useErrorNotice();
  const categories = useMemo(
    () =>
      [...new Set(catalog.filter((a) => a.active).map((a) => a.category))]
        .sort((a, b) => a.localeCompare(b, "es"))
        .map((name) => ({ id: name, name })),
    [catalog],
  );
  const visible = availableAssays(catalog, query, category);
  const groups = categories.filter((c) =>
    visible.some((a) => a.category === c.id),
  );
  function apply() {
    try {
      onApply(selected);
      onClose();
    } catch (e) {
      setError(e.message);
    }
  }
  return (
    <Modal title="Añadir ensayo" onClose={onClose}>
      <div className="modal-body assay-picker">
        <div className="form-grid">
          <Field label="Buscar ensayo">
            <input
              autoFocus
              value={query}
              placeholder="Nombre, código o método"
              onChange={(e) => setQuery(e.target.value)}
            />
          </Field>
          <Field label="Categoría">
            <SearchSelect
              value={category}
              onChange={setCategory}
              options={categories}
              placeholder="Todas las categorías"
            />
          </Field>
        </div>
        <ErrorBox>{error}</ErrorBox>
        <div className="assay-picker-list">
          {groups.length ? (
            groups.map((c) => (
              <section key={c.id}>
                <h3>{c.name}</h3>
                {visible
                  .filter((a) => a.category === c.id)
                  .map((a) => (
                    <label key={a.id} className="assay-option">
                      <input
                        type="checkbox"
                        disabled={existing.includes(a.id)}
                        checked={
                          existing.includes(a.id) || selected.includes(a.id)
                        }
                        onChange={(e) =>
                          setSelected((old) =>
                            e.target.checked
                              ? [...old, a.id]
                              : old.filter((id) => id !== a.id),
                          )
                        }
                      />
                      <span>
                        <b>{a.name}</b>
                        <small className="block">
                          {a.code} · {a.method || "Método no indicado"}
                        </small>
                      </span>
                    </label>
                  ))}
              </section>
            ))
          ) : (
            <Empty>No hay ensayos habilitados con esta búsqueda.</Empty>
          )}
        </div>
        <div className="form-actions">
          <span>{selected.length} seleccionados</span>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" disabled={!selected.length} onClick={apply}>
            Añadir seleccionados
          </Button>
        </div>
      </div>
    </Modal>
  );
}
