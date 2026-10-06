import os
import sys
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://lab@127.0.0.1:55432/lab_lc_v3_test"
)
if urlparse(os.environ["DATABASE_URL"]).path not in (
    "/lab_lc_v3_test",
    "/lab_lc_release_test",
    "/lab_lc_v4_test",
    "/lab_lc_v4_unit_test",
    "/lab_lc_v5_unit_test",
    "/lab_lc_v5_test",
    "/lab_lc_v6_unit_test",
    "/lab_lc_v6_test",
    "/lab_lc_v7_unit_test",
    "/lab_lc_v7_test",
):
    raise RuntimeError(
        "TEST_DATABASE_URL debe apuntar a una base ficticia de pruebas admitida, con esquema 7."
    )
os.environ["APP_ENV"] = "development"
os.environ["APP_ORIGIN"] = "http://localhost:5173"
os.environ["STORAGE_MODE"] = "local"


@pytest.fixture
def db(monkeypatch, tmp_path):
    import http_helpers
    from config import settings
    from database import engine

    settings.cache_clear()
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    with engine().connect() as connection:
        tx = connection.begin()

        class TestEngine:
            @contextmanager
            def begin(self):
                with connection.begin_nested():
                    yield connection

        monkeypatch.setattr(http_helpers, "engine", lambda: TestEngine())
        try:
            yield connection
        finally:
            tx.rollback()


@pytest.fixture
def users(db):
    from database import rows

    return {u["email"].split("@")[0]: u for u in rows(db, "SELECT * FROM usuarios")}


@pytest.fixture(autouse=True)
def catalog_fixture(monkeypatch):
    # Only synthetic catalog codes; operational tests never write AppControlHH.
    from services import projects, workflow

    def catalog(query="", page=1, limit=30, code=None):
        items = [
            {"id": "DEMO-001", "code": "DEMO-001", "name": "Recrecimiento demo"},
            {"id": "DEMO-002", "code": "DEMO-002", "name": "Planta demo"},
        ]
        if code is not None:
            items = [x for x in items if x["code"] == code]
        else:
            items = [
                x for x in items if query.lower() in x["code"].lower() or query.lower() in x["name"].lower()
            ]
        return {
            "items": items[(page - 1) * limit : page * limit],
            "total": len(items),
            "page": page,
            "limit": limit,
        }

    monkeypatch.setattr(projects, "catalog", catalog)
    monkeypatch.setattr(workflow, "validate_code", projects.validate_code)
