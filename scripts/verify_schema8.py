"""Only fresh, explicitly named disposable databases; never delete an existing DB."""

import os
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
names = ["lab_lc_v8_clean_test", "lab_lc_v8_reset_test"]
urls = {}
for name, key in zip(names, ["TEST_CLEAN_DATABASE_URL", "TEST_MIGRATION_DATABASE_URL"]):
    raw = os.environ.get(key)
    if not raw:
        raise SystemExit("Configura " + key + " para " + name + ", base local vacía creada previamente.")
    url = make_url(raw)
    if url.database != name or url.host not in ("localhost", "127.0.0.1"):
        raise SystemExit("Solo se admiten bases ficticias locales con los nombres previstos.")
    urls[name] = url


def connect(name):
    return psycopg.connect(
        urls[name].set(drivername="postgresql").render_as_string(hide_password=False),
        autocommit=True,
    )


for name in names:
    with connect(name) as db:
        if db.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
        ).fetchone()[0]:
            raise SystemExit(name + " debe estar vacía; no se modifica una base preexistente.")
with connect(names[0]) as db:
    for file in ["01_schema.sql", "02_catalog.sql", "03_demo.sql"]:
        source = root / "api/tests/fixtures/schema_v8.sql" if file == "01_schema.sql" else root / "sql" / file
        db.execute(source.read_text(encoding="utf-8"))
    assert db.execute("SELECT count(*) FROM catalogo_ensayos").fetchone()[0] == 58
with connect(names[1]) as db:
    db.execute((root / "api/tests/fixtures/schema_v7.sql").read_text(encoding="utf-8"))
    org = db.execute("INSERT INTO empresas(nombre) VALUES ('Prueba conservada') RETURNING id").fetchone()[0]
    user = db.execute(
        "INSERT INTO usuarios(empresa_id,nombre,correo,hash_contrasena) VALUES (%s,'Cliente','v8@example.com','!NOT_INITIALIZED') RETURNING id",
        (org,),
    ).fetchone()[0]
    rid = db.execute(
        "INSERT INTO solicitudes(empresa_id,creado_por,proyecto_id,titulo,coordenada_este) VALUES (%s,%s,'DEMO','Antigua',123456) RETURNING id",
        (org, user),
    ).fetchone()[0]
    sample = db.execute(
        "INSERT INTO muestras(solicitud_id,codigo_cliente,peso) VALUES (%s,'M',1.234) RETURNING id",
        (rid,),
    ).fetchone()[0]
    assay = db.execute(
        "INSERT INTO catalogo_ensayos(codigo,nombre) VALUES ('ANT','Antiguo') RETURNING id"
    ).fetchone()[0]
    db.execute(
        "INSERT INTO ensayos_muestra(muestra_id,ensayo_id) VALUES (%s,%s)",
        (sample, assay),
    )
    db.execute(
        "INSERT INTO informes(solicitud_id,version,nombre,clave_archivo,sha256,tamano_bytes,subido_por) VALUES (%s,1,'Ficticio.pdf','ficticio','hash',100,%s)",
        (rid, user),
    )
    db.execute("INSERT INTO actividad(solicitud_id,mensaje) VALUES (%s,'Operativo')", (rid,))
    db.execute("INSERT INTO actividad(mensaje) VALUES ('Administrativo conservado')")
    db.execute(
        "INSERT INTO sesiones(hash_token,usuario_id,vence_en) VALUES ('ficticio',%s,now()+interval '1 hour')",
        (user,),
    )
    sequence = db.execute("SELECT last_value FROM numero_solicitud").fetchone()[0]
    migration = (root / "sql/06_actualizacion_catalogo_muestras.sql").read_text(encoding="utf-8")
    db.execute(migration)
    assert db.execute("SELECT max(version) FROM migraciones_esquema").fetchone()[0] == 8
    assert db.execute("SELECT count(*) FROM usuarios").fetchone()[0] == 1
    assert db.execute("SELECT hash_contrasena FROM usuarios").fetchone()[0] == "!NOT_INITIALIZED"
    assert db.execute("SELECT count(*) FROM empresas").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM sesiones").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM actividad").fetchone()[0] == 1
    for table in ["solicitudes", "muestras", "ensayos_muestra", "informes"]:
        assert db.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM catalogo_ensayos").fetchone()[0] == 58
    assert db.execute("SELECT last_value FROM numero_solicitud").fetchone()[0] == sequence
    assert (
        db.execute(
            "SELECT count(*) FROM pg_trigger WHERE tgname IN ('actividad_inmutable','informes_inmutables') AND tgenabled='O'"
        ).fetchone()[0]
        == 2
    )
    try:
        db.execute(migration)
    except psycopg.errors.RaiseException:
        db.execute("ROLLBACK")
    else:
        raise AssertionError("Debe rechazar repetición de SQL06")
    try:
        db.execute("DELETE FROM actividad")
    except psycopg.errors.RaiseException:
        pass
    else:
        raise AssertionError("Debe conservar historial inmutable")


def columns(db):
    return db.execute(
        "SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' ORDER BY 1,2"
    ).fetchall()


with connect(names[0]) as a, connect(names[1]) as b:
    assert columns(a) == columns(b)
print(
    "Instalacion limpia, 58 ensayos, reinicio 7 a 8, preservacion y protecciones verificados en bases ficticias."
)
