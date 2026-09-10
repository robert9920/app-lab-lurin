-- OPCIONAL, producción. Ejecutar como propietario del esquema en lab_lc_v3.
-- Crear previamente el rol LOGIN lab_runtime y asignarle contraseña por un canal seguro.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE lab_lc_v3 TO lab_runtime;
GRANT USAGE ON SCHEMA public TO lab_runtime;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO lab_runtime;
GRANT INSERT, UPDATE, DELETE ON empresas,usuarios,proyectos,miembros_proyecto,catalogo_ensayos,
 solicitudes,muestras,ensayos_muestra,sesiones,limites_intentos TO lab_runtime;
GRANT INSERT ON informes,actividad TO lab_runtime;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO lab_runtime;
-- Sin UPDATE/DELETE en informes/actividad ni escritura en migraciones_esquema.

