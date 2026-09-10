-- Versión 3: instalar exclusivamente en una base NUEVA y vacía.
BEGIN;
CREATE TABLE migraciones_esquema (version integer PRIMARY KEY, aplicado_en timestamptz NOT NULL DEFAULT now());
CREATE TABLE empresas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), nombre text NOT NULL,
 identificacion_tributaria text UNIQUE, activo boolean NOT NULL DEFAULT true
);
CREATE TABLE usuarios (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), empresa_id uuid REFERENCES empresas,
 nombre text NOT NULL, correo text NOT NULL UNIQUE CHECK(correo=lower(correo)),
 hash_contrasena text NOT NULL,
 roles text[] NOT NULL DEFAULT '{CLIENT}' CHECK(cardinality(roles)>0 AND roles <@ ARRAY['ADMIN','MANAGER','TECH','CLIENT']),
 activo boolean NOT NULL DEFAULT true, creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE proyectos (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), empresa_id uuid NOT NULL REFERENCES empresas,
 codigo text NOT NULL UNIQUE, nombre text NOT NULL, ubicacion text NOT NULL DEFAULT '', activo boolean NOT NULL DEFAULT true
);
CREATE TABLE miembros_proyecto (
 proyecto_id uuid NOT NULL REFERENCES proyectos, usuario_id uuid NOT NULL REFERENCES usuarios,
 PRIMARY KEY(proyecto_id,usuario_id)
);
CREATE TABLE catalogo_ensayos (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), codigo text NOT NULL UNIQUE, nombre text NOT NULL,
 metodo text NOT NULL DEFAULT '', categoria text NOT NULL DEFAULT 'Geotecnia', activo boolean NOT NULL DEFAULT true
);
CREATE SEQUENCE numero_solicitud;
CREATE TABLE solicitudes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 codigo text NOT NULL UNIQUE DEFAULT ('SOL-' || lpad(nextval('numero_solicitud')::text,8,'0')),
 proyecto_id uuid NOT NULL REFERENCES proyectos, creado_por uuid NOT NULL REFERENCES usuarios,
 titulo text NOT NULL, estado_solicitud text NOT NULL DEFAULT 'DRAFT'
 CHECK(estado_solicitud IN ('DRAFT','SUBMITTED','OBSERVED','APPROVED','REJECTED','CLOSED')),
 observaciones text NOT NULL DEFAULT '', fecha_objetivo date,
 version integer NOT NULL DEFAULT 1 CHECK(version>0),
 creado_en timestamptz NOT NULL DEFAULT now(), actualizado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE muestras (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), solicitud_id uuid NOT NULL REFERENCES solicitudes,
 codigo_cliente text NOT NULL, calicata_sondaje text NOT NULL DEFAULT '', material text NOT NULL DEFAULT 'Suelo',
 profundidad_inicial numeric CHECK(profundidad_inicial>=0), profundidad_final numeric CHECK(profundidad_final>=0),
 cantidad numeric CHECK(cantidad>0), unidad text NOT NULL DEFAULT 'kg', observaciones text NOT NULL DEFAULT '',
 recibido_en timestamptz, recibido_por uuid REFERENCES usuarios, transporte text NOT NULL DEFAULT '',
 cantidad_recibida numeric CHECK(cantidad_recibida>0), condicion text NOT NULL DEFAULT 'NOT_RECEIVED'
 CHECK(condicion IN ('NOT_RECEIVED','OK','OBSERVED','DAMAGED','INSUFFICIENT')),
 observaciones_recepcion text NOT NULL DEFAULT '',
 codigo_recepcion text CHECK(codigo_recepcion=upper(trim(codigo_recepcion)) AND length(codigo_recepcion) BETWEEN 1 AND 60),
 codigo_laboratorio text UNIQUE CHECK(codigo_laboratorio=upper(trim(codigo_laboratorio)) AND length(codigo_laboratorio) BETWEEN 1 AND 60),
 CHECK(condicion='NOT_RECEIVED' OR (codigo_recepcion IS NOT NULL AND codigo_laboratorio IS NOT NULL)),
 UNIQUE(solicitud_id,codigo_cliente), CHECK(profundidad_final IS NULL OR profundidad_inicial IS NULL OR profundidad_final>=profundidad_inicial),
 CHECK((condicion='NOT_RECEIVED' AND recibido_en IS NULL AND recibido_por IS NULL) OR
       (condicion<>'NOT_RECEIVED' AND recibido_en IS NOT NULL AND recibido_por IS NOT NULL)),
 CHECK(condicion IN ('NOT_RECEIVED','OK') OR length(trim(observaciones_recepcion))>0)
);
CREATE TABLE ensayos_muestra (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), muestra_id uuid NOT NULL REFERENCES muestras ON DELETE CASCADE,
 ensayo_id uuid NOT NULL REFERENCES catalogo_ensayos, tecnico_id uuid REFERENCES usuarios,
 estado_ensayo text NOT NULL DEFAULT 'PENDING' CHECK(estado_ensayo IN ('PENDING','RUNNING','OBSERVED','COMPLETED','CANCELLED')),
 inicio_previsto date, fin_previsto date, iniciado_en timestamptz, completado_en timestamptz,
 observaciones text NOT NULL DEFAULT '', UNIQUE(muestra_id,ensayo_id),
 CHECK(fin_previsto IS NULL OR inicio_previsto IS NULL OR fin_previsto>=inicio_previsto),
 CHECK(estado_ensayo NOT IN ('RUNNING','OBSERVED','COMPLETED') OR (tecnico_id IS NOT NULL AND iniciado_en IS NOT NULL)),
 CHECK(estado_ensayo<>'COMPLETED' OR completado_en IS NOT NULL),
 CHECK(completado_en IS NULL OR (iniciado_en IS NOT NULL AND completado_en>=iniciado_en))
);
CREATE TABLE informes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), solicitud_id uuid NOT NULL REFERENCES solicitudes,
 version integer NOT NULL CHECK(version>0), nombre text NOT NULL, clave_archivo text NOT NULL UNIQUE,
 sha256 text NOT NULL, tamano_bytes integer NOT NULL CHECK(tamano_bytes BETWEEN 1 AND 20971520),
 subido_por uuid NOT NULL REFERENCES usuarios, creado_en timestamptz NOT NULL DEFAULT now(),
 UNIQUE(solicitud_id,version)
);
CREATE TABLE actividad (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, solicitud_id uuid REFERENCES solicitudes,
 autor_id uuid REFERENCES usuarios, tipo text NOT NULL DEFAULT 'EVENT' CHECK(tipo IN ('EVENT','COMMENT')),
 mensaje text NOT NULL, detalle jsonb NOT NULL DEFAULT '{}', interno boolean NOT NULL DEFAULT true,
 creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE sesiones (
 hash_token text PRIMARY KEY, usuario_id uuid NOT NULL REFERENCES usuarios ON DELETE CASCADE,
 creado_en timestamptz NOT NULL DEFAULT now(), ultimo_acceso timestamptz NOT NULL DEFAULT now(),
 vence_en timestamptz NOT NULL
);
CREATE TABLE limites_intentos (
 clave_limite text PRIMARY KEY, numero_intentos integer NOT NULL DEFAULT 1, inicio_ventana timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON miembros_proyecto(usuario_id);
CREATE INDEX ON proyectos(empresa_id);
CREATE INDEX ON solicitudes(proyecto_id,estado_solicitud);
CREATE INDEX ON muestras(solicitud_id);
CREATE INDEX ON ensayos_muestra(estado_ensayo,fin_previsto);
CREATE INDEX ON ensayos_muestra(tecnico_id);
CREATE INDEX ON actividad(solicitud_id,id);
CREATE INDEX ON sesiones(usuario_id);
CREATE INDEX ON sesiones(vence_en);
CREATE FUNCTION historial_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'El historial es inmutable'; END $$;
CREATE TRIGGER actividad_inmutable BEFORE UPDATE OR DELETE ON actividad FOR EACH ROW EXECUTE FUNCTION historial_inmutable();
CREATE TRIGGER informes_inmutables BEFORE UPDATE OR DELETE ON informes FOR EACH ROW EXECUTE FUNCTION historial_inmutable();
INSERT INTO migraciones_esquema(version) VALUES(3);
COMMIT;

