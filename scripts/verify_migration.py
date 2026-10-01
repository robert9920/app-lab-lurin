"""Verifica SQL 05 solo en una base vacía ficticia; nunca elimina bases existentes."""

import json
import os
from pathlib import Path

import psycopg
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = os.environ.get("TEST_MIGRATION_DATABASE_URL", "")
    if not raw:
        raise SystemExit(
            "Configura TEST_MIGRATION_DATABASE_URL para una base vacía ficticia."
        )
    url = make_url(raw)
    if url.database != "lab_lc_v4_migration_test":
        raise SystemExit(
            "Solo se admite lab_lc_v4_migration_test; no se alteran otras bases."
        )
    with psycopg.connect(
        url.set(drivername="postgresql").render_as_string(hide_password=False),
        autocommit=True,
    ) as db:
        if db.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
        ).fetchone()[0]:
            raise SystemExit(
                "La base de pruebas debe estar vacía; no se borrarán sus datos."
            )
        db.execute(
            (ROOT / "api/tests/fixtures/schema_v3.sql").read_text(encoding="utf-8")
        )
        org = db.execute(
            "INSERT INTO empresas(nombre) VALUES ('Empresa histórica ficticia') RETURNING id"
        ).fetchone()[0]
        user = db.execute(
            "INSERT INTO usuarios(nombre,correo,empresa_id,hash_contrasena) VALUES ('Cliente','migracion@example.com',%s,'!NOT_INITIALIZED') RETURNING id",
            (org,),
        ).fetchone()[0]
        project = db.execute(
            "INSERT INTO proyectos(empresa_id,codigo,nombre) VALUES (%s,'PR-HISTORICO','Nombre antiguo') RETURNING id",
            (org,),
        ).fetchone()[0]
        db.execute("INSERT INTO miembros_proyecto VALUES (%s,%s)", (project, user))
        request = db.execute(
            "INSERT INTO solicitudes(proyecto_id,creado_por,titulo,estado_solicitud) VALUES (%s,%s,'Histórico','APPROVED') RETURNING id",
            (project, user),
        ).fetchone()[0]
        sample = db.execute(
            "INSERT INTO muestras(solicitud_id,codigo_cliente,cantidad,unidad) VALUES (%s,'M-HIST',2.5,'kg') RETURNING id",
            (request,),
        ).fetchone()[0]
        migration = (ROOT / "sql/05_actualizacion_solicitudes.sql").read_text(
            encoding="utf-8"
        )
        try:
            db.execute(migration)
        except psycopg.errors.RaiseException:
            db.execute("ROLLBACK")
        else:
            raise AssertionError("Debe rechazar sacos fraccionarios.")
        assert (
            db.execute("SELECT max(version) FROM migraciones_esquema").fetchone()[0]
            == 3
        )
        assert not db.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='muestras' AND column_name='peso'"
        ).fetchone()
        db.execute("UPDATE muestras SET cantidad=2 WHERE id=%s", (sample,))
        db.execute(migration)
        assert (
            db.execute("SELECT max(version) FROM migraciones_esquema").fetchone()[0]
            == 4
        )
        assert db.execute(
            "SELECT proyecto_id,empresa_id FROM solicitudes WHERE id=%s", (request,)
        ).fetchone() == ("PR-HISTORICO", org)
        assert db.execute(
            "SELECT cantidad,peso,peso_recibido FROM muestras WHERE id=%s", (sample,)
        ).fetchone() == (2, None, None)
        actual = db.execute(
            "SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public'"
        ).fetchall()
        expected = json.loads(
            (ROOT / "docs/schema-columns.json").read_text(encoding="utf-8")
        )
        keys = (
            "table_name",
            "column_name",
            "data_type",
            "is_nullable",
            "column_default",
        )
        assert sorted(actual) == sorted(tuple(c[k] for k in keys) for c in expected)
        assert len({c[0] for c in actual}) == 11
        try:
            db.execute(migration)
        except psycopg.errors.RaiseException:
            db.execute("ROLLBACK")
        else:
            raise AssertionError("No debe aplicar SQL 05 dos veces.")
    print("Migracion verificada: rollback, preservacion y coherencia del esquema.")


if __name__ == "__main__":
    main()
