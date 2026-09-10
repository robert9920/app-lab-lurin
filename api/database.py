from functools import lru_cache

from sqlalchemy import create_engine, text

from config import settings
from schema_names import domain_row


@lru_cache
def engine():
    return create_engine(
        settings()["database"],
        pool_size=2,
        max_overflow=3,
        pool_timeout=10,
        pool_recycle=1800,
        pool_pre_ping=True,
    )


def rows(db, sql, **params):
    return [domain_row(r) for r in db.execute(text(sql), params).mappings()]


def one(db, sql, **params):
    result = rows(db, sql, **params)
    return result[0] if result else None


def execute(db, sql, **params):
    return db.execute(text(sql), params)
