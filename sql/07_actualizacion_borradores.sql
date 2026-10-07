-- ESQUEMA 8 → 9: borradores incompletos, sin eliminar ni reiniciar datos.
-- Ejecutar UNA VEZ como propietario, con respaldo y API detenida.
-- NO ejecutar SQL06 otra vez: su reinicio operativo no pertenece a esta actualización.
BEGIN;
LOCK TABLE migraciones_esquema,solicitudes,muestras IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF (SELECT max(version) FROM migraciones_esquema) IS DISTINCT FROM 8 THEN
  RAISE EXCEPTION 'SQL07 requiere esquema 8; no repetir ni ejecutar sobre otra versión';
 END IF;
END $$;
-- Los NULL representan datos aún no informados en borradores privados.
-- La API exige proyecto interno, datos generales y muestras completas antes del envío.
ALTER TABLE solicitudes ALTER COLUMN proyecto_id DROP NOT NULL;
ALTER TABLE muestras ALTER COLUMN codigo_cliente DROP NOT NULL,
 ALTER COLUMN material DROP NOT NULL;
-- UNIQUE(solicitud_id,codigo_cliente) sigue vigente para códigos informados.
-- Se conservan IDs, correlativos, estados, historial, informes y todos los valores existentes.
INSERT INTO migraciones_esquema(version) VALUES(9);
COMMIT;
