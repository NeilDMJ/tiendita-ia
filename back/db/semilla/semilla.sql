-- Datos de ejemplo SINTÉTICOS para la demo. En la UI se presentan como "datos de ejemplo".
-- Fuente única del catálogo: back/datos/catalogo.csv (mismas clases que el detector de visión).
\set ON_ERROR_STOP on
BEGIN;

SELECT setseed(0.42);   -- mismas ventas "aleatorias" en cada arranque

-- 1. Negocio (ficticio)
INSERT INTO negocio (nombre, giro, responsable, municipio, horario)
VALUES ('Tiendita de demostración', 'abarrotes', 'Tendero de ejemplo', 'Oaxaca de Juárez', '7:00–22:00');

-- 2. Catálogo desde el CSV
CREATE TEMP TABLE catalogo_csv (
  sku text, clase_vision text, nombre text, categoria text, unidad text,
  precio numeric, costo numeric, existencia numeric, stock_minimo numeric,
  caduca text, alias text
);
\copy catalogo_csv FROM '/datos/catalogo.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO categoria (nombre) SELECT DISTINCT categoria FROM catalogo_csv ORDER BY 1;

INSERT INTO producto (sku, nombre, categoria_id, etiqueta_vision, unidad, precio_venta, costo,
                      existencia, stock_minimo, origen)
SELECT c.sku, c.nombre, cat.id, nullif(c.clase_vision, ''), c.unidad::unidad_medida,
       c.precio, c.costo, c.existencia, c.stock_minimo, 'semilla'
  FROM catalogo_csv c JOIN categoria cat ON cat.nombre = c.categoria;

INSERT INTO producto_alias (producto_id, alias)
SELECT DISTINCT p.id, normalizar(a)
  FROM catalogo_csv c
  JOIN producto p ON p.sku = c.sku
  CROSS JOIN LATERAL unnest(string_to_array(c.alias, '|')) AS a
 WHERE trim(a) <> ''
ON CONFLICT DO NOTHING;

-- 3. Proveedores y comprobantes (gastos e inversiones de las últimas semanas)
INSERT INTO proveedor (nombre) VALUES
  ('Coca-Cola FEMSA'), ('Grupo Bimbo'), ('Distribuidora de abarrotes del Valle'), ('CFE'), ('Arrendador del local');

INSERT INTO comprobante (id_local, tipo, proveedor_id, concepto, fecha, total)
SELECT x.id_local, x.tipo::tipo_comprobante, pr.id, x.concepto, current_date - x.dias, x.total
  FROM (VALUES
    ('semilla-c1', 'inversion_inventario', 'Coca-Cola FEMSA',                      'Refrescos y agua',       4, 2400.00),
    ('semilla-c2', 'inversion_inventario', 'Grupo Bimbo',                          'Pan de caja y Gansitos', 5, 1250.00),
    ('semilla-c3', 'inversion_inventario', 'Distribuidora de abarrotes del Valle', 'Despensa y limpieza',    8, 3180.00),
    ('semilla-c4', 'gasto_operativo',      'CFE',                                  'Luz del local y refrigeradores', 3, 1150.00),
    ('semilla-c5', 'gasto_operativo',      'Arrendador del local',                 'Renta mensual',         15, 4500.00)
  ) AS x(id_local, tipo, proveedor, concepto, dias, total)
  JOIN proveedor pr ON pr.nombre = x.proveedor;

-- 4. Lotes de lo que caduca (la existencia actual repartida en lotes).
--    Leche y pan con un lote a punto de caducar para disparar la promoción en la demo.
INSERT INTO lote (producto_id, cantidad_inicial, cantidad_actual, caducidad, costo_unitario, recibido_en)
SELECT p.id, p.existencia, p.existencia,
       current_date + CASE p.unidad WHEN 'kg' THEN 3 ELSE 30 + (random() * 60)::int END,
       p.costo, now() - interval '5 days'
  FROM producto p JOIN catalogo_csv c ON c.sku = p.sku
 WHERE c.caduca = 'si' AND p.sku NOT IN ('LALA-1L', 'BIMB-BLAN') AND p.existencia > 0;

INSERT INTO lote (producto_id, cantidad_inicial, cantidad_actual, caducidad, costo_unitario, recibido_en)
SELECT p.id, x.cantidad, x.cantidad, current_date + x.dias, p.costo, now() - x.recibido
  FROM (VALUES
    ('LALA-1L',   6, 2, interval '8 days'),     -- caduca en 2 días
    ('LALA-1L',   8, 12, interval '1 day'),
    ('BIMB-BLAN', 4, 3, interval '4 days'),     -- caduca en 3 días
    ('BIMB-BLAN', 3, 8, interval '1 day')
  ) AS x(sku, cantidad, dias, recibido)
  JOIN producto p ON p.sku = x.sku;

-- Entrada inicial en la bitácora (cuadra existencia = suma de movimientos)
INSERT INTO movimiento_inventario (producto_id, lote_id, tipo, cantidad, nota, creado_en)
SELECT l.producto_id, l.id, 'entrada', l.cantidad_inicial, 'Inventario inicial (semilla)', l.recibido_en
  FROM lote l;
INSERT INTO movimiento_inventario (producto_id, tipo, cantidad, nota, creado_en)
SELECT p.id, 'entrada', p.existencia, 'Inventario inicial (semilla)', now() - interval '5 days'
  FROM producto p
 WHERE p.existencia > 0 AND NOT EXISTS (SELECT 1 FROM lote l WHERE l.producto_id = p.id);

-- 5. Historial de ventas: 21 días, más ventas en la mañana temprano y en la tarde-noche.
--    Es historial: NO descuenta la existencia actual (que es la del CSV).
DO $$
DECLARE
  d int; n int; i int; k int; nitems int;
  v_id uuid; v_metodo metodo_pago; v_hora timestamptz; v_total numeric;
  r float; prod record; cant numeric; contador int := 0;
  horas int[] := ARRAY[7,8,8,9,10,11,12,13,14,15,17,18,18,19,19,20,20,21];
BEGIN
  FOR d IN REVERSE 21..0 LOOP
    n := 14 + (random() * 12)::int + CASE WHEN extract(isodow FROM current_date - d) IN (6,7) THEN 8 ELSE 0 END;
    IF d = 0 THEN n := least(n, 9); END IF;   -- hoy apenas va empezando
    FOR i IN 1..n LOOP
      contador := contador + 1;
      v_hora := (current_date - d) + make_interval(hours => horas[1 + (random() * (array_length(horas,1) - 1))::int],
                                                   mins  => (random() * 59)::int);
      IF d = 0 AND v_hora > now() THEN v_hora := now() - make_interval(mins => (random() * 120)::int); END IF;
      r := random();
      v_metodo := CASE WHEN r < 0.70 THEN 'efectivo' WHEN r < 0.85 THEN 'transferencia'
                       WHEN r < 0.95 THEN 'qr' ELSE 'tarjeta' END;

      INSERT INTO venta (id_local, origen, metodo_pago, total, duracion_seg, ocurrida_en, registrada_en)
      VALUES ('semilla-v' || contador,
              CASE WHEN random() < 0.65 THEN 'camara' ELSE 'manual' END::origen_venta,
              v_metodo, 0, 25 + (random() * 40)::int, v_hora, v_hora)
      RETURNING id INTO v_id;

      nitems := 1 + (random() * 3)::int;
      FOR k IN 1..nitems LOOP
        SELECT * INTO prod FROM producto
         WHERE id NOT IN (SELECT producto_id FROM venta_item WHERE venta_id = v_id)
         ORDER BY random() LIMIT 1;
        cant := CASE WHEN prod.unidad = 'kg' THEN (ARRAY[0.5, 1, 1, 1.5, 2])[1 + (random() * 4)::int]
                     ELSE 1 + (random() * random() * 3)::int END;
        INSERT INTO venta_item (venta_id, producto_id, nombre, cantidad, precio_unitario, costo_unitario, corregido)
        VALUES (v_id, prod.id, prod.nombre, cant, prod.precio_venta, prod.costo, random() < 0.08);
      END LOOP;

      SELECT sum(subtotal) INTO v_total FROM venta_item WHERE venta_id = v_id;
      UPDATE venta SET total = v_total WHERE id = v_id;

      INSERT INTO pago (venta_id, metodo, monto, estado, referencia, simulado, creado_en,
                        enviado_en, recibido_en, conciliado_en)
      VALUES (v_id, v_metodo, v_total,
              CASE WHEN v_metodo = 'efectivo' OR d > 0 THEN 'conciliado'
                   ELSE 'pendiente' END::estado_pago,
              CASE WHEN v_metodo <> 'efectivo' AND d > 0 THEN 'SIM-' || (100000 + contador) END,
              v_metodo <> 'efectivo', v_hora,
              CASE WHEN v_metodo <> 'efectivo' AND d > 0 THEN v_hora END,
              CASE WHEN v_metodo <> 'efectivo' AND d > 0 THEN v_hora + interval '1 minute' END,
              CASE WHEN v_metodo = 'efectivo' OR d > 0 THEN v_hora + interval '2 minutes' END);
    END LOOP;
  END LOOP;
END $$;

-- 6. Una transferencia que llegó sin venta asociada (para la demo de conciliación)
WITH p AS (
  INSERT INTO pago (metodo, monto, estado, referencia, simulado, creado_en, enviado_en, recibido_en)
  VALUES ('transferencia', 58.00, 'recibido', '99887', true,
          now() - interval '40 minutes', now() - interval '40 minutes', now() - interval '39 minutes')
  RETURNING id
)
INSERT INTO alerta (tipo, agente, pago_id, detalle)
SELECT 'pago_sin_conciliar', 'caja', p.id,
       '{"mensaje": "Hay una transferencia de $58.00 sin venta asociada"}'::jsonb FROM p;

-- 7. Alertas de caducidad y stock bajo + una promoción propuesta (simulada)
INSERT INTO alerta (tipo, agente, producto_id, lote_id, detalle)
SELECT 'caducidad', 'bodega', l.producto_id, l.id,
       jsonb_build_object('caducidad', l.caducidad, 'cantidad', l.cantidad_actual)
  FROM lote l WHERE l.caducidad <= current_date + 3 AND l.cantidad_actual > 0;

INSERT INTO alerta (tipo, agente, producto_id, detalle)
SELECT 'stock_bajo', 'bodega', p.id, jsonb_build_object('existencia', p.existencia)
  FROM producto p WHERE p.existencia <= p.stock_minimo
ON CONFLICT DO NOTHING;

INSERT INTO promocion (producto_id, lote_id, alerta_id, motivo, descuento, precio_promo, copy,
                       vigente_hasta, estado, simulada)
SELECT a.producto_id, a.lote_id, a.id, 'Lote por caducar en 2 días', '2 por $50', 25.00,
       '¡Oferta! Leche Lala 1 L: llévate 2 por $50 solo hasta pasado mañana.',
       current_date + 2, 'propuesta', true
  FROM alerta a JOIN producto p ON p.id = a.producto_id
 WHERE a.tipo = 'caducidad' AND p.sku = 'LALA-1L';

COMMIT;

-- Resumen en el log del contenedor
SELECT (SELECT count(*) FROM producto) AS productos,
       (SELECT count(*) FROM producto_alias) AS alias,
       (SELECT count(*) FROM lote) AS lotes,
       (SELECT count(*) FROM venta) AS ventas,
       (SELECT count(*) FROM comprobante) AS comprobantes,
       (SELECT count(*) FROM alerta) AS alertas;
