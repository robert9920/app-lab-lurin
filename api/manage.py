"""Comandos locales. Las contraseñas se leen sin eco, nunca como argumentos."""

import argparse
import getpass
import json
import os
from pathlib import Path

local = Path(__file__).with_name("local.settings.json")
if local.exists():
    for key, value in json.loads(local.read_text(encoding="utf-8-sig"))["Values"].items():
        os.environ.setdefault(key, value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "demo", "bootstrap", "password"])
    parser.add_argument("--email")
    args = parser.parse_args()
    from config import settings
    from database import engine, execute, one

    if args.command in ("migrate", "demo"):
        import psycopg
        from sqlalchemy.engine import make_url

        url = make_url(settings()["database"])
        if url.database not in (
            "lab_lc",
            "lab_lc_v3",
            "lab_lc_v3_test",
            "lab_lc_release_test",
            "lab_lc_v4_test",
            "lab_lc_v4_unit_test",
            "lab_lc_v5_test",
            "lab_lc_v5_unit_test",
            "lab_lc_v6_test",
            "lab_lc_v6_unit_test",
        ):
            raise SystemExit(
                "Este instalador solo admite lab_lc, lab_lc_v3 o una base ficticia de pruebas prevista."
            )
        if args.command == "demo" and (settings()["production"] or url.database == "lab_lc"):
            raise SystemExit("No se permiten datos ficticios en producción.")
        sql_dir = Path(__file__).resolve().parents[1] / "sql"
        with psycopg.connect(
            url.set(drivername="postgresql").render_as_string(hide_password=False), autocommit=True
        ) as conn:
            installed = conn.execute("SELECT to_regclass('public.migraciones_esquema')").fetchone()[0]
            if not installed:
                if conn.execute(
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
                ).fetchone()[0]:
                    raise SystemExit("La base debe estar vacía.")
                if args.command == "demo":
                    raise SystemExit("Ejecuta migrate primero.")
                conn.execute((sql_dir / "01_schema.sql").read_text(encoding="utf-8"))
            else:
                version = conn.execute("SELECT max(version) FROM migraciones_esquema").fetchone()[0]
                if version == 3 and args.command == "migrate":
                    conn.execute((sql_dir / "05_actualizacion_solicitudes.sql").read_text(encoding="utf-8"))
                elif version == 4 and args.command == "migrate":
                    migration = (sql_dir / "05_actualizacion_solicitudes.sql").read_text(encoding="utf-8")
                    conn.execute(migration.split("-- SECCION_ESQUEMA_5", 1)[1])
                elif version == 5 and args.command == "migrate":
                    migration = (sql_dir / "05_actualizacion_solicitudes.sql").read_text(encoding="utf-8")
                    conn.execute(migration.split("-- SECCION_ESQUEMA_6", 1)[1])
                elif version != 6:
                    raise SystemExit(
                        "Versión incompatible; migrate actualiza esquema 3/4/5 a 6. Detén los servidores y respalda antes."
                    )
            conn.execute(
                (sql_dir / ("03_demo.sql" if args.command == "demo" else "02_catalog.sql")).read_text(
                    encoding="utf-8"
                )
            )
        print(
            "Datos ficticios preparados; inicializa las contraseñas con password."
            if args.command == "demo"
            else "Esquema 6 y catálogo preparados."
        )
        return
    from pydantic import EmailStr, TypeAdapter

    from security import hasher
    from services.common import audit

    email = str(TypeAdapter(EmailStr).validate_python(args.email or input("Correo: "))).lower()
    password = getpass.getpass("Contraseña (15 a 128 caracteres): ")
    if not 15 <= len(password) <= 128 or password != getpass.getpass("Repite contraseña: "):
        raise SystemExit("Contraseña inválida o distinta.")
    with engine().begin() as db:
        execute(db, "SELECT pg_advisory_xact_lock(481701)")
        user = one(db, "SELECT * FROM usuarios WHERE correo=:email FOR UPDATE", email=email)
        if args.command == "bootstrap":
            if one(db, "SELECT 1 FROM usuarios WHERE activo AND 'ADMIN'=ANY(roles)"):
                raise SystemExit("Ya existe un administrador. Usa la plataforma o el comando password.")
            if user:
                raise SystemExit("El correo ya existe.")
            name = input("Nombre del administrador: ").strip()
            if len(name) < 2:
                raise SystemExit("Nombre inválido.")
            user = one(
                db,
                "INSERT INTO usuarios(nombre,correo,hash_contrasena,roles)\n                VALUES(:name,:email,:hash,ARRAY['ADMIN']) RETURNING *",
                name=name,
                email=email,
                hash=hasher.hash(password),
            )
        else:
            if not user:
                raise SystemExit("Usuario no encontrado.")
            execute(
                db,
                "UPDATE usuarios SET hash_contrasena=:hash WHERE id=:id",
                hash=hasher.hash(password),
                id=user["id"],
            )
            execute(db, "DELETE FROM sesiones WHERE usuario_id=:id", id=user["id"])
        audit(db, user, "Cuenta inicializada por operador")
    print("Contraseña guardada con Argon2id. Sesiones anteriores revocadas.")


if __name__ == "__main__":
    main()
