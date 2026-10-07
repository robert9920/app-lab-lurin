-- ESQUEMA 7 → 8. REINICIO OPERATIVO EXPRESAMENTE SOLICITADO.
-- Ejecutar UNA VEZ como propietario, con la aplicación detenida y respaldo previo.
-- Borra solicitudes, muestras, ensayos, informes (metadatos), actividad asociada y catálogo.
-- Conserva empresas, usuarios, contraseñas, sesiones, actividad administrativa y correlativos.
-- Los PDF físicos NO se borran. Guardar antes SELECT clave_archivo FROM informes para limpieza separada.
BEGIN;
LOCK TABLE migraciones_esquema,solicitudes,muestras,ensayos_muestra,informes,actividad,catalogo_ensayos IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF (SELECT max(version) FROM migraciones_esquema) IS DISTINCT FROM 7 THEN
  RAISE EXCEPTION 'SQL06 requiere esquema 7; no repetir ni ejecutar sobre otra versión';
 END IF;
END $$;
ALTER TABLE actividad DISABLE TRIGGER actividad_inmutable;
ALTER TABLE informes DISABLE TRIGGER informes_inmutables;
DELETE FROM actividad WHERE solicitud_id IS NOT NULL;
DELETE FROM informes;
DELETE FROM ensayos_muestra;
DELETE FROM muestras;
DELETE FROM solicitudes;
DELETE FROM catalogo_ensayos;
ALTER TABLE actividad ENABLE TRIGGER actividad_inmutable;
ALTER TABLE informes ENABLE TRIGGER informes_inmutables;
ALTER TABLE catalogo_ensayos ADD COLUMN precio numeric NOT NULL
 CONSTRAINT catalogo_precio_valido CHECK(precio>0 AND precio=round(precio,2) AND precio NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric));
ALTER TABLE solicitudes DROP COLUMN titulo, DROP COLUMN coordenada_este, DROP COLUMN coordenada_norte, ADD COLUMN fecha_estimada_arribo date;
ALTER TABLE muestras ADD COLUMN coordenada_este numeric CONSTRAINT muestras_este_valido CHECK(coordenada_este>=100000 AND coordenada_este<1000000),
 ADD COLUMN coordenada_norte numeric CONSTRAINT muestras_norte_valido CHECK(coordenada_norte>=1000000 AND coordenada_norte<10000000),
 ADD CONSTRAINT muestras_peso_precision CHECK(peso=round(peso,1)),
 ADD CONSTRAINT muestras_peso_recibido_precision CHECK(peso_recibido=round(peso_recibido,1));
-- Catálogo oficial: Referencia/Ensayos_Laboratorio_Lurin.xlsx, ID_Ensayos A2:B59. Precios en USD.
-- Excluidos Trabajo de Campo y Trabajo de Oficina (sin precio). Catálogo reemplazado por completo.
INSERT INTO catalogo_ensayos(codigo,nombre,metodo,categoria,precio,activo) VALUES
('LC-001','Contenido de Humedad','Por confirmar con laboratorio','Caracterización',11,true),
('LC-002','Análisis Granulométrico por Tamizado < N° 3in.','Por confirmar con laboratorio','Caracterización',27,true),
('LC-003','Análisis Granulométrico por Sedimentación (Hidrómetro). Incluye Gs. < N° 4','Por confirmar con laboratorio','Caracterización',70,true),
('LC-004','Límites de Consistencia < N° 4','Por confirmar con laboratorio','Caracterización',20,true),
('LC-005','Clasificación por SUCS','Por confirmar con laboratorio','Caracterización',5,true),
('LC-006','Gravedad Específica de Suelos Finos < N° 4','Por confirmar con laboratorio','Caracterización',22,true),
('LC-007','Peso Volumétrico de Suelos Cohesivos (Parafina)','Por confirmar con laboratorio','Caracterización',25,true),
('LC-008','Densidad Máxima','Por confirmar con laboratorio','Caracterización',20,true),
('LC-009','Densidad Mínima','Por confirmar con laboratorio','Caracterización',35,true),
('LC-010','Medición de PH','Por confirmar con laboratorio','Caracterización',15,true),
('LC-011','Medición de turbidez','Por confirmar con laboratorio','Caracterización',15,true),
('LC-012','Medición de solidos suspendidos','Por confirmar con laboratorio','Caracterización',40,true),
('LC-013','Proctor Estándar','Por confirmar con laboratorio','Compactación',70,true),
('LC-014','Proctor Modificado','Por confirmar con laboratorio','Compactación',80,true),
('LC-015','Compresión No Confinada en Suelos Cohesivos (incluye Gs)','Por confirmar con laboratorio','Resistencia',80,true),
('LC-016','Triaxial UU Ø 2" — 3 especímenes','Por confirmar con laboratorio','Resistencia',235,true),
('LC-017','Triaxial UU Ø 2.8" — 3 especímenes','Por confirmar con laboratorio','Resistencia',250,true),
('LC-018','Triaxial UU Ø 4" — 3 especímenes','Por confirmar con laboratorio','Resistencia',335,true),
('LC-019','Triaxial UU Ø 6" — 3 especímenes','Por confirmar con laboratorio','Resistencia',400,true),
('LC-020','Triaxial CU Ø 2" — 3 especímenes','Por confirmar con laboratorio','Resistencia',835,true),
('LC-021','Triaxial CU Ø 2.8" — 3 especímenes','Por confirmar con laboratorio','Resistencia',850,true),
('LC-022','Triaxial CU Ø 4" — 3 especímenes','Por confirmar con laboratorio','Resistencia',985,true),
('LC-023','Triaxial CU Ø 6" — 3 especímenes','Por confirmar con laboratorio','Resistencia',1100,true),
('LC-024','Triaxial CD Ø 2" — 3 especímenes','Por confirmar con laboratorio','Resistencia',900,true),
('LC-025','Triaxial CD Ø 2.8" — 3 especímenes','Por confirmar con laboratorio','Resistencia',950,true),
('LC-026','Triaxial CD Ø 4" — 3 especímenes','Por confirmar con laboratorio','Resistencia',1200,true),
('LC-027','Triaxial CD Ø 6" — 3 especímenes','Por confirmar con laboratorio','Resistencia',1300,true),
('LC-028','Corte Directo < N°4 (≤400 kPa, 3 especímenes)','Por confirmar con laboratorio','Resistencia',350,true),
('LC-029','Pared Flexible (Suelo Cohesivo) Ø 2" — 1 especímen','Por confirmar con laboratorio','Permeabilidad',300,true),
('LC-030','Pared Flexible (Suelo Cohesivo) Ø 2.8" — 1 especímen','Por confirmar con laboratorio','Permeabilidad',300,true),
('LC-031','Pared Flexible (Suelo Cohesivo) Ø 4" — 1 especímen','Por confirmar con laboratorio','Permeabilidad',340,true),
('LC-032','Pared Flexible (Suelo Cohesivo) Ø 6" — 1 especímen','Por confirmar con laboratorio','Permeabilidad',360,true),
('LC-033','Consolidación Unidimensional hasta 600 kPa','Por confirmar con laboratorio','Consolidación',300,true),
('LC-034','Consolidación Unidimensional hasta 1200 kPa','Por confirmar con laboratorio','Consolidación',350,true),
('LC-035','Consolidación Unidimensional hasta 2400 kPa','Por confirmar con laboratorio','Consolidación',375,true),
('LC-036','Expansión o Colapso Unidimensional — Método C','Por confirmar con laboratorio','Consolidación',300,true),
('LC-037','Sedimentación estática: Selección de floculante (15), optima dilución del relave, optima dosificación de floculante y densificación de relave','Por confirmar con laboratorio','Procesamiento de relaves',1200,true),
('LC-038','Selección de floculante: Se realizan pruebas con 50 floculantes, controlando la velocidad de particulas, turbidez del liquido filtrado y tasa de asentamiento.','Por confirmar con laboratorio','Procesamiento de relaves',500,true),
('LC-039','Sedimentación dinámica: se realizan de sedimentación variando el area unitaria (03)','Por confirmar con laboratorio','Procesamiento de relaves',1500,true),
('LC-040','Centrifugado: Con y sin floculante, con 02 velocidades de tambor','Por confirmar con laboratorio','Procesamiento de relaves',1500,true),
('LC-041','Filtración al vacío: Selección de medio filtrante, 3 espesores de torta, 4 tiempos de secado.','Por confirmar con laboratorio','Procesamiento de relaves',1500,true),
('LC-042','Filtración al vacío: Selección de medio filtrante, 3 espesores de torta, 4 tiempos de secado con etapas de lavado en CO - CC. No incluye analisis quimicos de liquidos o tortas.','Por confirmar con laboratorio','Procesamiento de relaves',2000,true),
('LC-043','Filtración a presión: selección de medio filtrante, 3 espesores de torta','Por confirmar con laboratorio','Procesamiento de relaves',2000,true),
('LC-044','Reología completa: tensión de fluencia y viscocidad dinamica','Por confirmar con laboratorio','Reología',2000,true),
('LC-045','Medición de tensión de fluencia 10 puntos, yield stress vs contenido de sólidos','Por confirmar con laboratorio','Reología',800,true),
('LC-046','Viscosidad dinamica 10 puntos, con sensor de cilindros concentricos, Shear rate vs viscocidad','Por confirmar con laboratorio','Reología',1200,true),
('LC-047','Medición de slump para un contenido de sólidos, altura del cono 30 cm','Por confirmar con laboratorio','Reología',60,true),
('LC-048','Medición de slump para un contenido de sólidos, altura del cono 15 cm','Por confirmar con laboratorio','Reología',25,true),
('LC-049','Pruebas de exudación a un contenido de sólidos','Por confirmar con laboratorio','Reología',50,true),
('LC-050','UCS por diseño (Un contenido de sólidos, un contenido de cemento y 05 tiempos de curado: 7, 15, 28, 60 y 90 días) total 15 probetas 2"X 4". No incluye cemento.','Por confirmar con laboratorio','Relaves cementados',400,true),
('LC-051','Medición de contenido de humedad a 7, 15, 28, 60 y 90 días curado (por  diseño)','Por confirmar con laboratorio','Relaves cementados',50,true),
('LC-052','Medición de pH a las probetas  a 7, 15, 28, 60 y 90 días curado (por  diseño)','Por confirmar con laboratorio','Relaves cementados',40,true),
('LC-053','Celda de desecación: control de temperatura, humedad relativa y radiación.','Por confirmar con laboratorio','Desecación',2000,true),
('LC-054','Apertura de Tubo Shelby','Por confirmar con laboratorio','Manejo de muestras',35,true),
('LC-055','Preparación de Muestras para Relaves por 30kg','Por confirmar con laboratorio','Manejo de muestras',30,true),
('LC-056','Salud y Seguridad de Muestras para Relaves','Por confirmar con laboratorio','Manejo de muestras',150,true),
('LC-057','Eliminación de Muestras por 30kg','Por confirmar con laboratorio','Manejo de muestras',30,true),
('LC-058','Limite de Contracción','Por confirmar con laboratorio','Caracterización',20,true)
ON CONFLICT(codigo) DO NOTHING;
INSERT INTO migraciones_esquema(version) VALUES(8);
COMMIT;
