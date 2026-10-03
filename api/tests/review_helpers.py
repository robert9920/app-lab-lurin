from services import workflow as w
from validation import AssaysReview


def approve_defined(db, user, rid, version):
    tasks = w.detail(db, user, rid)["tasks"]
    w.review_assays(
        db,
        user,
        rid,
        AssaysReview(
            version=version,
            decisions=[{"task_id": t["id"], "decision": "APPROVED"} for t in tasks if t["can_review"]],
        ),
    )
