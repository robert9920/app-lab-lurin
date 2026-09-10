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
if urlparse(os.environ["DATABASE_URL"]).path != "/lab_lc_v3_test":
    raise RuntimeError("Pruebas limitadas a lab_lc_v3_test")
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
