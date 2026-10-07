"""Validate clean v9 and non-destructive 8→9 only in empty, named local test databases."""

import argparse
import os
from pathlib import Path

import psycopg
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--suffix", choices=("", "_recheck"), default="")
suffix = parser.parse_args().suffix
names = ["lab_lc_v9_clean_test" + suffix, "lab_lc_v9_migration_test" + suffix]
urls = {}
for name, variable in zip(names, ["TEST_CLEAN_DATABASE_URL", "TEST_MIGRATION_DATABASE_URL"]):
    url = make_url(os.environ.get(variable, ""))
    if url.database != name or url.host not in ("localhost", "127.0.0.1"):
        raise SystemExit("Configura " + variable + " para la base ficticia local " + name)
    urls[name] = url.set(drivername="postgresql").render_as_string(hide_password=False)


def connect(name):
    return psycopg.connect(urls[name], autocommit=True)


def snapshot(db):
    tables = [
        r[0]
        for r in db.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1"
        )
        if r[0] != "migraciones_esquema"
    ]
    return {
        table: db.execute("SELECT to_jsonb(t) FROM " + table + " t ORDER BY to_jsonb(t)::text").fetchall()
        for table in tables
    }


def columns(db):
    return db.execute(
        "SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' ORDER BY 1,2"
    ).fetchall()


for name in names:
    with connect(name) as db:
        if db.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
        ).fetchone()[0]:
            raise SystemExit(name + " debe estar vacía; no se modifican bases preexistentes.")

with connect(names[0]) as db:
    for file in ("01_schema.sql", "02_catalog.sql", "03_demo.sql"):
        db.execute((ROOT / "sql" / file).read_text(encoding="utf-8"))
    expected = columns(db)
    assert db.execute("SELECT max(version) FROM migraciones_esquema").fetchone()[0] == 9

with connect(names[1]) as db:
    db.execute((ROOT / "api/tests/fixtures/schema_v8.sql").read_text(encoding="utf-8"))
    for file in ("02_catalog.sql", "03_demo.sql"):
        db.execute((ROOT / "sql" / file).read_text(encoding="utf-8"))
    before, sequence = (
        snapshot(db),
        db.execute("SELECT last_value FROM numero_solicitud").fetchone(),
    )
    db.execute((ROOT / "sql/07_actualizacion_borradores.sql").read_text(encoding="utf-8"))
    assert snapshot(db) == before
    assert db.execute("SELECT last_value FROM numero_solicitud").fetchone() == sequence
    assert columns(db) == expected
    assert db.execute("SELECT max(version) FROM migraciones_esquema").fetchone()[0] == 9
    for table, trigger in (
        ("actividad", "actividad_inmutable"),
        ("informes", "informes_inmutables"),
    ):
        assert (
            db.execute(
                "SELECT tgenabled FROM pg_trigger WHERE tgname=%s AND tgrelid=%s::regclass",
                (trigger, table),
            ).fetchone()[0]
            == "O"
        )
    try:
        db.execute((ROOT / "sql/07_actualizacion_borradores.sql").read_text(encoding="utf-8"))
        raise AssertionError("Una actualización repetida debe rechazarse")
    except psycopg.Error:
        db.execute("ROLLBACK")
    assert snapshot(db) == before
    assert db.execute("SELECT count(*) FROM migraciones_esquema WHERE version=9").fetchone()[0] == 1

print(
    "Instalacion limpia, migracion 8 a 9, conservacion completa, correlativos, triggers y coherencia verificados."
)
