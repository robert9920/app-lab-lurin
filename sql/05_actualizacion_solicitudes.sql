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
