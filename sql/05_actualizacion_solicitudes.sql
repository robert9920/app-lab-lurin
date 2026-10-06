-- Actualización 3 → 4. Ejecutar en lab_lc (Azure) o lab_lc_v3 (local), en mantenimiento.
-- Respaldar previamente base y PDF. No ejecutar 01_schema.sql sobre una base existente.
BEGIN;
DO $$ BEGIN
 IF (SELECT max(version) FROM migraciones_esquema) IS DISTINCT FROM 3 THEN
  RAISE EXCEPTION 'Se requiere esquema 3; actualización ya aplicada o base incompatible';
 END IF;
END $$;
LOCK TABLE empresas,usuarios,proyectos,miembros_proyecto,solicitudes,muestras IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM muestras WHERE cantidad <> trunc(cantidad) OR cantidad_recibida <> trunc(cantidad_recibida) OR cantidad IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) OR cantidad_recibida IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric)) THEN
  RAISE EXCEPTION 'Revisar cantidades: los sacos deben ser enteros. No se convertirán automáticamente';
 END IF;
END $$;
ALTER TABLE empresas ADD COLUMN es_interna boolean NOT NULL DEFAULT false;
CREATE UNIQUE INDEX una_empresa_interna ON empresas(es_interna) WHERE es_interna;
ALTER TABLE usuarios ADD COLUMN num_telefono text;
ALTER TABLE solicitudes ADD COLUMN empresa_id uuid REFERENCES empresas;
UPDATE solicitudes s SET empresa_id=p.empresa_id FROM proyectos p WHERE p.id=s.proyecto_id;
ALTER TABLE solicitudes ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE solicitudes DROP CONSTRAINT solicitudes_proyecto_id_fkey;
ALTER TABLE solicitudes ALTER COLUMN proyecto_id TYPE text USING proyecto_id::text;
UPDATE solicitudes s SET proyecto_id=p.codigo FROM proyectos p WHERE s.proyecto_id=p.id::text;
ALTER TABLE solicitudes ADD COLUMN distrito text, ADD COLUMN provincia text, ADD COLUMN departamento text,
 ADD COLUMN coordenada_este numeric, ADD COLUMN coordenada_norte numeric, ADD COLUMN codigo_ot text;
ALTER TABLE solicitudes DROP CONSTRAINT solicitudes_estado_solicitud_check;
ALTER TABLE solicitudes ADD CONSTRAINT solicitudes_estado_solicitud_check
 CHECK(estado_solicitud IN ('DRAFT','WAITING_ASSAYS','SUBMITTED','OBSERVED','APPROVED','REJECTED','CLOSED'));
ALTER TABLE solicitudes ADD CONSTRAINT codigo_ot_valido CHECK(codigo_ot IS NULL OR (codigo_ot=upper(trim(codigo_ot)) AND length(codigo_ot) BETWEEN 1 AND 60));
CREATE INDEX solicitudes_autor ON solicitudes(creado_por);
CREATE INDEX solicitudes_empresa ON solicitudes(empresa_id);
ALTER TABLE muestras ADD COLUMN peso numeric CHECK(peso>0 AND peso NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric)),
 ADD COLUMN peso_recibido numeric CHECK(peso_recibido>0 AND peso_recibido NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric));
ALTER TABLE muestras ADD CONSTRAINT sacos_enteros CHECK(cantidad IS NULL OR (cantidad=trunc(cantidad) AND cantidad NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
 ADD CONSTRAINT sacos_recibidos_enteros CHECK(cantidad_recibida IS NULL OR (cantidad_recibida=trunc(cantidad_recibida) AND cantidad_recibida NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric)));
ALTER TABLE muestras DROP COLUMN unidad;
DROP TABLE miembros_proyecto;
DROP TABLE proyectos;
INSERT INTO migraciones_esquema(version) VALUES(4);
COMMIT;


-- NUEVA SECCIÓN — Actualización de esquema 4 a 5: aprobación parcial de ensayos
-- SECCION_ESQUEMA_5
-- Si ya aplicaste 3→4, ejecuta SOLO desde este encabezado hasta el COMMIT final.
-- No volver a ejecutar el bloque 3→4 de arriba sobre una base con esquema 4.
BEGIN;
DO $$ BEGIN
 IF (SELECT max(version) FROM migraciones_esquema) IS DISTINCT FROM 4 THEN
  RAISE EXCEPTION 'Se requiere esquema 4; actualización 4→5 ya aplicada o base incompatible';
 END IF;
END $$;
LOCK TABLE solicitudes,ensayos_muestra IN ACCESS EXCLUSIVE MODE;
ALTER TABLE ensayos_muestra ADD COLUMN aprobado boolean NOT NULL DEFAULT false;
UPDATE ensayos_muestra a SET aprobado=true
 FROM muestras m JOIN solicitudes s ON s.id=m.solicitud_id
 WHERE a.muestra_id=m.id AND s.estado_solicitud IN ('APPROVED','CLOSED');
INSERT INTO migraciones_esquema(version) VALUES(5);
COMMIT;

-- NUEVA SECCIÓN — Actualización de esquema 5 a 6: revisión individual de ensayos
-- SECCION_ESQUEMA_6
-- Si tu base está en versión 5, ejecuta SOLO esta sección hasta su COMMIT.
-- No repetir las secciones anteriores ni el esquema de instalación sobre esa base.
BEGIN;
LOCK TABLE solicitudes,ensayos_muestra,migraciones_esquema IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF (SELECT max(version) FROM migraciones_esquema) IS DISTINCT FROM 5 THEN
  RAISE EXCEPTION 'Se requiere esquema 5; actualización 5→6 ya aplicada o base incompatible';
 END IF;
END $$;
ALTER TABLE ensayos_muestra ADD COLUMN estado_revision text NOT NULL DEFAULT 'PENDING'
 CHECK(estado_revision IN ('PENDING','APPROVED','REJECTED'));
UPDATE ensayos_muestra SET estado_revision=CASE WHEN aprobado THEN 'APPROVED' ELSE 'PENDING' END;
ALTER TABLE ensayos_muestra DROP COLUMN aprobado;
INSERT INTO migraciones_esquema(version) VALUES(6);
COMMIT;

-- NUEVA SECCIÓN — Actualización de esquema 6 a 7: estados de solicitud y resumen de ensayos
-- SECCION_ESQUEMA_7
-- Base en versión 6: ejecutar SOLO desde este marcador hasta el COMMIT de esta sección.
-- Detener la aplicación anterior y respaldar antes. No repetir bloques anteriores ni 01_schema.sql.
BEGIN;
LOCK TABLE solicitudes,ensayos_muestra,migraciones_esquema IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF (SELECT max(version) FROM migraciones_esquema) IS DISTINCT FROM 6 THEN
  RAISE EXCEPTION 'Se requiere esquema 6; actualización 6→7 ya aplicada o base incompatible';
 END IF;
END $$;
ALTER TABLE solicitudes ADD COLUMN estado_general text NOT NULL DEFAULT 'CREATED'
 CONSTRAINT solicitudes_estado_general_valido CHECK(estado_general IN ('CREATED','CANCELLED','CLOSED'));
UPDATE solicitudes SET estado_general=CASE estado_solicitud
 WHEN 'CLOSED' THEN 'CLOSED' WHEN 'REJECTED' THEN 'CANCELLED' ELSE 'CREATED' END;
WITH cancelados AS (
 UPDATE ensayos_muestra a SET estado_ensayo='CANCELLED'
 FROM muestras m JOIN solicitudes r ON r.id=m.solicitud_id
 WHERE a.muestra_id=m.id AND r.estado_general='CANCELLED'
 AND a.estado_revision<>'REJECTED' AND a.estado_ensayo NOT IN ('COMPLETED','CANCELLED')
 RETURNING a.id,m.solicitud_id
)
INSERT INTO actividad(solicitud_id,mensaje,detalle,interno)
 SELECT solicitud_id,'Ensayo cancelado al actualizar una solicitud previamente rechazada',
 jsonb_build_object('task_id',id,'action','cancel','to','CANCELLED',
 'reason','Solicitud rechazada antes de instalar el esquema 7'),false FROM cancelados;
-- Se conservan IDs, decisiones, técnicos, fechas, informes y cierres históricos.
INSERT INTO migraciones_esquema(version) VALUES(7);
COMMIT;
