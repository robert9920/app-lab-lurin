import useErrorNotice from "../hooks/useErrorNotice";
import { useEffect, useId, useState } from "react";
import { Loading, ErrorBox } from "./ui";
import { api, messageOf } from "../services/api";

export default function ProjectSelect({ value, onChange, disabled = false }) {
  const id = useId(),
    [query, setQuery] = useState(value || ""),
    [open, setOpen] = useState(false),
    [data, setData] = useState(null),
    [error, setError] = useErrorNotice(),
    [cursor, setCursor] = useState(0),
    [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false),
    [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!open || disabled) return;
    let live = true;
    const timer = setTimeout(() => {
      setBusy(true);
      setFailed(false);
      api
        .get("/projects", { params: { scope: "catalog", q: query, limit: 30 } })
        .then((r) => {
          if (live) {
            setData(r.data);
            setError("");
            setCursor(0);
          }
        })
        .catch((e) => {
          if (live) {
            setData(null);
            setFailed(true);
            setError(messageOf(e));
          }
        })
        .finally(() => {
          if (live) setBusy(false);
        });
    }, 250);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [query, open, disabled, retry, setError]);
  function choose(p) {
    onChange(p.code);
    setQuery(p.code + " - " + p.name);
    setOpen(false);
  }
  async function more() {
    setBusy(true);
    try {
      const r = await api.get("/projects", {
        params: { scope: "catalog", q: query, page: data.page + 1, limit: 30 },
      });
      setData({ ...r.data, items: [...data.items, ...r.data.items] });
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="field project-select">
      <label htmlFor={id}>Proyecto *</label>
      <input
        id={id}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={id + "-options"}
        aria-activedescendant={
          open && data?.items[cursor] ? id + "-" + cursor : undefined
        }
        autoComplete="off"
        required
        disabled={disabled}
        value={
          open
            ? query
            : value
              ? query.startsWith(value + " - ")
                ? query
                : value
              : query
        }
        placeholder="Escribe código o nombre"
        onFocus={() => {
          if (!disabled) {
            setOpen(true);
            if (value) setQuery("");
          }
        }}
        onBlur={() => setOpen(false)}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange("");
          setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setOpen(true);
            setCursor((n) => Math.min(n + 1, (data?.items.length || 1) - 1));
          }
          if (e.key === "ArrowUp") {
            e.preventDefault();
            setCursor((n) => Math.max(0, n - 1));
          }
          if (e.key === "Enter" && open) {
            e.preventDefault();
            if (data?.items[cursor]) choose(data.items[cursor]);
          }
        }}
      />
      {open && (
        <div
          className="project-options"
          onMouseDown={(e) => e.preventDefault()}
        >
          {busy && <Loading compact>Buscando…</Loading>}
          {error && <ErrorBox>{error}</ErrorBox>}
          {failed && !busy && (
            <button
              type="button"
              className="btn"
              onClick={() => setRetry((n) => n + 1)}
            >
              Reintentar consulta
            </button>
          )}
          <ul id={id + "-options"} role="listbox">
            {data?.items.map((p, i) => (
              <li
                id={id + "-" + i}
                role="option"
                aria-selected={i === cursor}
                key={p.code}
                onMouseEnter={() => setCursor(i)}
              >
                <button type="button" onClick={() => choose(p)}>
                  <b>{p.code}</b>
                  <span>{p.name}</span>
                </button>
              </li>
            ))}
          </ul>
          {data && !data.items.length && !busy && <p>Sin coincidencias.</p>}
          {data?.items.length < data?.total && (
            <button
              type="button"
              className="btn"
              disabled={busy}
              onClick={more}
            >
              Ver más proyectos
            </button>
          )}
        </div>
      )}
      {!disabled && (
        <small>Selecciona una coincidencia para confirmar el proyecto.</small>
      )}
    </div>
  );
}
