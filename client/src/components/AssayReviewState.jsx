import { useState } from "react";
import useErrorNotice from "../hooks/useErrorNotice";
import { api, messageOf } from "../services/api";
import { Badge, Button, ErrorBox } from "./ui";

export default function AssayReviewState({ task, request, onDone }) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useErrorNotice();
  async function resubmit() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post(
        `/requests/${request.id}/assays/resubmit`,
        { version: request.version, task_ids: [task.id] },
      );
      onDone(data);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  if (task.approved) return null;
  return (
    <div className="assay-review-state">
      {task.review_status === "REJECTED" ? (
        <>
          <Badge state="REJECTED">Ensayo rechazado</Badge>
          {task.review_reason && (
            <small className="block">Motivo: {task.review_reason}</small>
          )}
        </>
      ) : (
        <small className="approval-note">Por aprobar</small>
      )}
      {task.can_resubmit && (
        <Button type="button" busy={busy} onClick={resubmit}>
          Volver a solicitar
        </Button>
      )}
      <ErrorBox>{error}</ErrorBox>
    </div>
  );
}
