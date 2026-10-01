"""Catálogo externo: dos columnas y transacciones de solo lectura, sin réplica local."""

import os
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from errors import AppError


@lru_cache
def source_engine():
    raw = os.getenv("PROJECTS_DATABASE_URL", "")
    if not raw:
        raise AppError(503, "El catálogo de proyectos no está configurado. Contacta al administrador.")
    try:
        url = make_url(raw)
        if url.drivername != "postgresql+psycopg":
            raise ValueError()
        if settings()["production"] and url.query.get("sslmode") != "verify-full":
            raise ValueError()
        return create_engine(
            url,
            pool_size=1,
            max_overflow=1,
            pool_timeout=5,
            pool_recycle=1800,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
    except (ValueError, SQLAlchemyError):
        raise AppError(503, "Revisa la configuración privada del catálogo de proyectos.") from None


def catalog(query="", page=1, limit=30, code=None):
    # Escape LIKE metacharacters: user text is a literal, never SQL.
    pattern = "%" + query[:150].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    where = "(id_proyecto ILIKE :q OR nombre ILIKE :q)" if code is None else "id_proyecto=:code"
    params = {"q": pattern, "code": code}
    try:
        with source_engine().begin() as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            db.execute(text("SET LOCAL statement_timeout = '3000ms'"))
            total = db.execute(
                text("SELECT count(*) FROM public.proyecto WHERE " + where), params
            ).scalar_one()
            items = [
                dict(r)
                for r in db.execute(
                    text(
                        "SELECT id_proyecto AS id,id_proyecto AS code,nombre AS name FROM public.proyecto WHERE "
                        + where
                        + " ORDER BY id_proyecto LIMIT :limit OFFSET :offset"
                    ),
                    {**params, "limit": limit, "offset": (page - 1) * limit},
                ).mappings()
            ]
        return {"items": items, "total": total, "page": page, "limit": limit}
    except SQLAlchemyError:
        raise AppError(503, "El catálogo de proyectos no está disponible. Intenta nuevamente.") from None


def validate_code(code):
    if not code or not catalog(code=code)["items"]:
        raise AppError(400, "Proyecto: selecciona un código disponible en el catálogo.")
    return code
