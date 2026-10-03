import useErrorNotice from "../hooks/useErrorNotice";
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api, messageOf } from "../services/api";
import { Loading, ErrorBox } from "./ui";

export const optionLabel = (o) =>
  o.code && o.code !== o.name ? `${o.code} · ${o.name}` : o.name || o.code;

export default function SearchSelect({
  id,
  value = "",
  onChange,
  options = [],
  remote,
  multiple = false,
  placeholder = "Todos",
  disabled = false,
}) {
  const generated = useId(),
    listId = generated + "-options",
    box = useRef(null),
    input = useRef(null);
  const [open, setOpen] = useState(false),
    [query, setQuery] = useState(""),
    [index, setIndex] = useState(0);
  const [items, setItems] = useState([]),
    [total, setTotal] = useState(0),
    [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false),
    [error, setError] = useErrorNotice(),
    [selectedName, setSelectedName] = useState("");
  const [position, setPosition] = useState({});
  const [failed, setFailed] = useState(false),
    [retry, setRetry] = useState(0);
  const values = value ? String(value).split(",") : [];
  const visible = remote
    ? items
    : options.filter((o) =>
        optionLabel(o)
          .toLocaleLowerCase("es")
          .includes(query.toLocaleLowerCase("es")),
      );
  const selected =
    options
      .filter((o) => values.includes(String(o.id)))
      .map(optionLabel)
      .join(", ") || selectedName;
  useEffect(() => {
    if (!remote || !value) return;
    let active = true;
    api
      .get(remote + "&selected=" + encodeURIComponent(value))
      .then((r) => {
        if (active) setSelectedName(r.data.items.map(optionLabel).join(", "));
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [remote, value]);
  useEffect(() => {
    if (!open || !remote) return;
    let active = true;
    setLoading(true);
    setError("");
    setFailed(false);
    if (page === 1) setItems([]);
    const timer = setTimeout(() => {
      api
        .get(
          remote + "&limit=30&page=" + page + "&q=" + encodeURIComponent(query),
        )
        .then((r) => {
          if (active) {
            setItems((old) =>
              page === 1 ? r.data.items : [...old, ...r.data.items],
            );
            setTotal(r.data.total);
          }
        })
        .catch((e) => {
          if (active) {
            setFailed(true);
            setError(messageOf(e));
          }
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 200);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [open, remote, query, page, retry, setError]);
  useEffect(() => {
    if (!open) return;
    const reposition = () => {
      const r = box.current.getBoundingClientRect();
      const below = window.innerHeight - r.bottom;
      const above = below < 200 && r.top > below;
      setPosition({
        left: r.left,
        width: r.width,
        top: above ? undefined : r.bottom + 4,
        bottom: above ? window.innerHeight - r.top + 4 : undefined,
        maxHeight: Math.min(300, (above ? r.top : below) - 12),
      });
    };
    const close = (e) => {
      if (
        !box.current?.contains(e.target) &&
        !document.getElementById(listId)?.contains(e.target)
      )
        setOpen(false);
    };
    reposition();
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    document.addEventListener("mousedown", close);
    return () => {
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
      document.removeEventListener("mousedown", close);
    };
  }, [open, listId]);
  useEffect(() => {
    if (open)
      document
        .getElementById(`${listId}-${index}`)
        ?.scrollIntoView({ block: "nearest" });
  }, [open, index, listId]);
  function choose(o) {
    const key = String(o.id);
    setSelectedName(optionLabel(o));
    onChange(
      multiple
        ? (values.includes(key)
            ? values.filter((v) => v !== key)
            : [...values, key]
          ).join(",")
        : key,
    );
    if (!multiple) {
      setOpen(false);
      input.current?.focus();
    }
  }
  return (
    <div className="search-select" ref={box}>
      <input
        id={id || generated}
        ref={input}
        role="combobox"
        autoComplete="off"
        disabled={disabled}
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={
          open && visible[index] ? `${listId}-${index}` : undefined
        }
        value={open ? query : value ? selected || "Filtro seleccionado" : ""}
        placeholder={placeholder}
        onClick={() => {
          if (!open) {
            setQuery("");
            setPage(1);
            setIndex(0);
            setOpen(true);
          }
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setPage(1);
          setIndex(0);
          setOpen(true);
        }}
        onBlur={(e) => {
          if (!document.getElementById(listId)?.contains(e.relatedTarget))
            setOpen(false);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
          if (["ArrowDown", "ArrowUp"].includes(e.key)) {
            e.preventDefault();
            if (!open) {
              setQuery("");
              setPage(1);
              setIndex(0);
              setOpen(true);
              return;
            }
            setOpen(true);
            setIndex((i) =>
              Math.max(
                0,
                Math.min(
                  visible.length - 1,
                  i + (e.key === "ArrowDown" ? 1 : -1),
                ),
              ),
            );
          }
          if (e.key === "Enter") {
            e.preventDefault();
            if (open && visible[index]) choose(visible[index]);
            else setOpen(true);
          }
        }}
      />
      {value && !disabled && (
        <button
          type="button"
          className="select-clear"
          aria-label="Limpiar selección"
          onClick={() => {
            onChange("");
            setQuery("");
            setSelectedName("");
          }}
        >
          ×
        </button>
      )}
      {open &&
        createPortal(
          <div
            id={listId}
            className="select-popover"
            style={position}
            onMouseDown={(e) => e.preventDefault()}
          >
            <div
              role="listbox"
              aria-label="Opciones"
              aria-multiselectable={multiple || undefined}
            >
              {visible.map((o, i) => (
                <button
                  type="button"
                  role="option"
                  id={`${listId}-${i}`}
                  aria-selected={values.includes(String(o.id))}
                  className={index === i ? "focused" : ""}
                  key={o.id}
                  onClick={() => choose(o)}
                >
                  {multiple && (
                    <span aria-hidden="true">
                      {values.includes(String(o.id)) ? "☑" : "☐"}
                    </span>
                  )}
                  {optionLabel(o)}
                </button>
              ))}
            </div>
            {loading && <Loading compact />}
            {error && <ErrorBox>{error}</ErrorBox>}
            {failed && !loading && (
              <button
                type="button"
                className="btn"
                onClick={() => setRetry((n) => n + 1)}
              >
                Reintentar consulta
              </button>
            )}
            {!loading && !failed && !visible.length && (
              <p>No hay coincidencias.</p>
            )}
            {remote && visible.length < total && (
              <button
                type="button"
                disabled={loading}
                className="btn"
                onClick={() => setPage((p) => p + 1)}
              >
                Ver más opciones
              </button>
            )}
          </div>,
          document.body,
        )}
    </div>
  );
}
