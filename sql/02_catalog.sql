INSERT INTO catalogo_ensayos(codigo,nombre,metodo,categoria) VALUES
('HUM','Contenido de humedad','ASTM D2216','Caracterización'),
('GRAN','Granulometría por tamizado','ASTM D6913','Caracterización'),
('HID','Granulometría por sedimentación','ASTM D7928','Caracterización'),
('ATT','Límites de Atterberg','ASTM D4318','Caracterización'),
('GS','Gravedad específica','ASTM D854','Caracterización'),
('CD','Corte directo','ASTM D3080','Resistencia'),
('CU2','Triaxial CU 2 pulgadas','ASTM D4767','Resistencia'),
('CU4','Triaxial CU 4 pulgadas','ASTM D4767','Resistencia'),
('CON24','Consolidación unidimensional 2,4 pulgadas','ASTM D2435','Deformación'),
('PV','Peso volumétrico','ASTM D7263','Caracterización'),
('DMIN','Densidad mínima','Por confirmar con laboratorio','Caracterización'),
('DMAX','Densidad máxima','Por confirmar con laboratorio','Caracterización')
ON CONFLICT(codigo) DO NOTHING;
-- Referencias orientativas del material recibido; validar método/edición antes de operación.
