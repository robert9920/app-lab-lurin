// Custom increments leave manual decimal precision free of HTML stepMismatch.
export default function NumericInput({
  increment = 1,
  integer = false,
  value,
  onChange,
  readOnly,
  disabled,
  ...props
}) {
  function change(direction) {
    const current = value === "" || value == null ? 0 : Number(value);
    if (!Number.isFinite(current)) return;
    const decimals = Math.min(
      12,
      Math.max(
        String(value).split(".")[1]?.length || 0,
        String(increment).split(".")[1]?.length || 0,
      ),
    );
    const next = Number((current + direction * increment).toFixed(decimals));
    if (next <= 0) {
      if (!current) onChange({ target: { value: String(increment) } });
      return;
    }
    onChange({ target: { value: String(next) } });
  }
  return (
    <div className="numeric-input">
      <input
        {...props}
        type="number"
        step={integer ? "1" : "any"}
        min={integer ? "1" : "0"}
        data-increment={increment}
        value={value}
        onChange={onChange}
        readOnly={readOnly}
        disabled={disabled}
        onKeyDown={(e) => {
          if (
            !readOnly &&
            !disabled &&
            ["ArrowUp", "ArrowDown"].includes(e.key)
          ) {
            e.preventDefault();
            change(e.key === "ArrowUp" ? 1 : -1);
          }
        }}
      />
      {!readOnly && (
        <div className="numeric-buttons">
          <button
            type="button"
            disabled={disabled}
            aria-label="Aumentar valor"
            onClick={() => change(1)}
          >
            ▴
          </button>
          <button
            type="button"
            disabled={disabled}
            aria-label="Disminuir valor"
            onClick={() => change(-1)}
          >
            ▾
          </button>
        </div>
      )}
    </div>
  );
}
