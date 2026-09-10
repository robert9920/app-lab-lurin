-- SOLO DESARROLLO. Datos ficticios. No contiene contraseñas ni archivos privados.
-- Puede ejecutarse de nuevo: los códigos/UUID estables evitan duplicados.
BEGIN;
INSERT INTO empresas(id,nombre,identificacion_tributaria) VALUES
('10000000-0000-0000-0000-000000000001','Lara Consulting · demostración','DEMO-LARA'),
('10000000-0000-0000-0000-000000000002','Minera Horizonte · ficticia','DEMO-HORIZONTE') ON CONFLICT DO NOTHING;
INSERT INTO usuarios(id,empresa_id,nombre,correo,roles,hash_contrasena) VALUES
('20000000-0000-0000-0000-000000000001',NULL,'Administrador del piloto','admin@example.com','{ADMIN,MANAGER}','!NOT_INITIALIZED'),
('20000000-0000-0000-0000-000000000002',NULL,'Jefatura de laboratorio','jefe@example.com','{MANAGER}','!NOT_INITIALIZED'),
('20000000-0000-0000-0000-000000000003',NULL,'Lucía Torres','tecnico@example.com','{TECH}','!NOT_INITIALIZED'),
('20000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000001','Diego · cliente interno','cliente@example.com','{CLIENT}','!NOT_INITIALIZED'),
('20000000-0000-0000-0000-000000000005','10000000-0000-0000-0000-000000000002','María · cliente externo','externo@example.com','{CLIENT}','!NOT_INITIALIZED') ON CONFLICT DO NOTHING;
INSERT INTO proyectos(id,empresa_id,codigo,nombre,ubicacion) VALUES
('30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','DEMO-001','Recrecimiento del depósito de relaves','Lurín, Lima'),
('30000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000001','DEMO-002','Planta de relaves filtrados','Moquegua'),
('30000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000002','DEMO-003','Caracterización geotécnica Horizonte','Arequipa') ON CONFLICT DO NOTHING;
INSERT INTO miembros_proyecto(usuario_id,proyecto_id) VALUES
('20000000-0000-0000-0000-000000000004','30000000-0000-0000-0000-000000000001'),
('20000000-0000-0000-0000-000000000004','30000000-0000-0000-0000-000000000002'),
('20000000-0000-0000-0000-000000000005','30000000-0000-0000-0000-000000000003') ON CONFLICT DO NOTHING;
INSERT INTO solicitudes(id,codigo,proyecto_id,creado_por,titulo,estado_solicitud,fecha_objetivo,observaciones) VALUES
('40000000-0000-0000-0000-000000000001','SOL-DEMO-001','30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000004','Caracterización de suelos del dique norte','APPROVED',current_date+14,'Datos ficticios para practicar recepción parcial.'),
('40000000-0000-0000-0000-000000000002','SOL-DEMO-002','30000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000004','Evaluación de relaves filtrados','SUBMITTED',current_date+21,''),
('40000000-0000-0000-0000-000000000003','SOL-DEMO-003','30000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000005','Ensayos de resistencia Horizonte','DRAFT',current_date+30,'Este registro es exclusivo del cliente externo.') ON CONFLICT DO NOTHING;
INSERT INTO muestras(id,solicitud_id,codigo_cliente,calicata_sondaje,profundidad_inicial,profundidad_final,cantidad,observaciones) VALUES
('50000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000001','M-01','DH-01',1,2.5,15,'Material granular'),
('50000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000001','M-02','DH-02',3,4.5,12,'Arribo adicional pendiente'),
('50000000-0000-0000-0000-000000000003','40000000-0000-0000-0000-000000000002','RF-01','Planta piloto',NULL,NULL,20,''),
('50000000-0000-0000-0000-000000000004','40000000-0000-0000-0000-000000000003','MH-01','DH-H01',5,8,25,'') ON CONFLICT DO NOTHING;
INSERT INTO ensayos_muestra(muestra_id,ensayo_id)
SELECT s.id,a.id FROM muestras s CROSS JOIN catalogo_ensayos a WHERE s.codigo_cliente IN('M-01','M-02','RF-01','MH-01') AND a.codigo IN('HUM','GRAN') ON CONFLICT DO NOTHING;

UPDATE muestras SET codigo_recepcion='REC-DEMO-001',codigo_laboratorio='LAB-DEMO-001',recibido_en=now()-interval '2 days',recibido_por='20000000-0000-0000-0000-000000000003',transporte='Transporte demo',cantidad_recibida=15,condicion='OK'
WHERE codigo_cliente='M-01' AND solicitud_id='40000000-0000-0000-0000-000000000001' AND condicion='NOT_RECEIVED';
UPDATE ensayos_muestra SET tecnico_id='20000000-0000-0000-0000-000000000003',estado_ensayo='RUNNING',inicio_previsto=current_date-2,fin_previsto=current_date-1,iniciado_en=now()-interval '1 day'
WHERE muestra_id='50000000-0000-0000-0000-000000000001' AND ensayo_id=(SELECT id FROM catalogo_ensayos WHERE codigo='HUM') AND estado_ensayo='PENDING';
UPDATE ensayos_muestra SET tecnico_id='20000000-0000-0000-0000-000000000003',estado_ensayo='PENDING',inicio_previsto=current_date,fin_previsto=current_date+3
WHERE muestra_id='50000000-0000-0000-0000-000000000001' AND ensayo_id=(SELECT id FROM catalogo_ensayos WHERE codigo='GRAN') AND estado_ensayo='PENDING';
-- Historial ficticio para visualizar completados por semana (sin documentos reales).
INSERT INTO muestras(id,solicitud_id,codigo_cliente,material,observaciones,codigo_recepcion,codigo_laboratorio,recibido_en,recibido_por,condicion)
SELECT md5('v2-week-sample-'||n)::uuid,'40000000-0000-0000-0000-000000000001',
 'Z-HIST-'||n,'Suelo','Muestra histórica ficticia para gráficos','REC-HIST-'||n,'LAB-HIST-'||n,
 now()-make_interval(weeks=>n)-interval '1 day','20000000-0000-0000-0000-000000000003','OK'
FROM generate_series(0,7) n ON CONFLICT DO NOTHING;
INSERT INTO ensayos_muestra(muestra_id,ensayo_id,tecnico_id,estado_ensayo,iniciado_en,completado_en)
SELECT md5('v2-week-sample-'||n)::uuid,c.id,'20000000-0000-0000-0000-000000000003',
 'COMPLETED',now()-make_interval(weeks=>n)-interval '1 day',now()-make_interval(weeks=>n)
FROM generate_series(0,7) n CROSS JOIN catalogo_ensayos c WHERE c.codigo='GS' ON CONFLICT DO NOTHING;
INSERT INTO muestras(id,solicitud_id,codigo_cliente,material,observaciones,recibido_en,recibido_por,condicion,observaciones_recepcion,codigo_recepcion,codigo_laboratorio)
VALUES('50000000-0000-0000-0000-000000000009','40000000-0000-0000-0000-000000000001','Z-OBS',
 'Mezcla de relaves','Componentes A y B; datos ficticios',now(),'20000000-0000-0000-0000-000000000003','INSUFFICIENT',
 'Falta material para preparar la probeta','REC-DEMO-002','LAB-DEMO-009') ON CONFLICT DO NOTHING;
INSERT INTO ensayos_muestra(muestra_id,ensayo_id,tecnico_id,estado_ensayo,fin_previsto,observaciones,iniciado_en)
SELECT '50000000-0000-0000-0000-000000000009',id,'20000000-0000-0000-0000-000000000003',
 'OBSERVED',current_date+2,'Esperando material adicional',now()-interval '1 day' FROM catalogo_ensayos WHERE codigo='CU4' ON CONFLICT DO NOTHING;
COMMIT;
