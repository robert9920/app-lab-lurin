import { useState } from "react";
import { api, messageOf } from "../services/api";
import { Button, Field, ErrorBox } from "./ui";
export default function ReportUpload({ request, onDone }) {
  const [file, setFile] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (!file || file.size > 20 * 1024 * 1024 || file.size === 0) {
        setError("Selecciona un PDF de hasta 20 MB.");
        return;
      }
      await api.post("/requests/" + request.id + "/reports", file, {
        headers: {
          "Content-Type": "application/pdf",
          "X-Request-Version": request.version,
        },
      });
      setFile(null);
      e.target.reset();
      await onDone();
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="bulk-panel">
      <ErrorBox>{error}</ErrorBox>
      <Field label="Cargar informe PDF (máximo 20 MB)">
        <input
          type="file"
          accept="application/pdf,.pdf"
          required
          onChange={(e) => setFile(e.target.files[0])}
        />
      </Field>
      <Button variant="primary" busy={busy} disabled={!file}>
        Subir y compartir informe
      </Button>
    </form>
  );
}
