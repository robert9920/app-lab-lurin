import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse


@lru_cache
def settings():
    prod = os.getenv("APP_ENV", "development") == "production"
    if (os.getenv("WEBSITE_INSTANCE_ID") or os.getenv("WEBSITE_SITE_NAME")) and not prod:
        raise RuntimeError("Azure requiere APP_ENV=production")
    origin = os.getenv("APP_ORIGIN", "http://localhost:5173").rstrip("/")
    url = urlparse(origin)
    if url.scheme not in ("http", "https") or not url.netloc or url.path:
        raise RuntimeError("APP_ORIGIN inválido")
    database = os.environ["DATABASE_URL"]
    if not database.startswith("postgresql+psycopg://"):
        raise RuntimeError("Se requiere PostgreSQL con psycopg")
    mode = os.getenv("STORAGE_MODE", "azure" if prod else "local")
    if mode not in ("local", "azure"):
        raise RuntimeError("STORAGE_MODE inválido")
    if prod and (
        mode != "azure"
        or url.scheme != "https"
        or parse_qs(urlparse(database).query).get("sslmode") != ["verify-full"]
    ):
        raise RuntimeError("Producción requiere Blob privado, HTTPS y PostgreSQL verify-full")
    upload_dir = Path(os.getenv("UPLOAD_DIR", str(Path(__file__).parent / ".local" / "uploads"))).resolve()
    frontend = Path(__file__).resolve().parents[1] / "client"
    if upload_dir == frontend or frontend in upload_dir.parents:
        raise RuntimeError("Los archivos privados deben permanecer fuera del frontend")
    return {
        "database": database,
        "origin": origin,
        "production": prod,
        "storage_mode": mode,
        "upload_dir": upload_dir,
        "cookie": "lab_session",
        "idle_minutes": int(os.getenv("SESSION_IDLE_MINUTES", "30")),
        "session_hours": int(os.getenv("SESSION_HOURS", "8")),
    }
