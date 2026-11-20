-- 005 · Vistas de lectura para los agentes (Analista, Control, Investigador, Vendedor) y el dashboard.
-- Los agentes consultan vistas, no tablas. "Día" = zona horaria de la BD (America/Mexico_City).

CREATE VIEW v_ventas_dia AS
SELECT (ocurrida_en)::date AS dia, count(*) AS ventas, sum(total) AS ingresos,
       round(avg(total), 2) AS ticket_promedio
  FROM venta WHERE estado = 'registrada' GROUP BY 1;

CREATE VIEW v_margen_producto AS
SELECT p.sku, p.nombre, c.nombre AS categoria,
       sum(vi.cantidad) AS unidades,
       sum(vi.subtotal) AS ingresos,
       sum(vi.subtotal - vi.cantidad * coalesce(vi.costo_unitario, 0)) AS margen,
       round(100 * sum(vi.subtotal - vi.cantidad * coalesce(vi.costo_unitario, 0))
             / nullif(sum(vi.subtotal), 0), 1) AS margen_pct
  FROM venta_item vi
  JOIN venta v ON v.id = vi.venta_id AND v.estado = 'registrada'
  JOIN producto p ON p.id = vi.producto_id
  LEFT JOIN categoria c ON c.id = p.categoria_id
 GROUP BY p.sku, p.nombre, c.nombre;

CREATE VIEW v_flujo_caja AS
SELECT dia, sum(ingreso) AS ingresos,
       sum(gasto_operativo) AS gasto_operativo,
       sum(inversion) AS inversion,
       sum(ingreso - gasto_operativo - inversion) AS neto
  FROM (
    SELECT ocurrida_en::date AS dia, total AS ingreso, 0 AS gasto_operativo, 0 AS inversion
      FROM venta WHERE estado = 'registrada'
    UNION ALL
    SELECT fecha,
           0,
           CASE WHEN tipo = 'gasto_operativo' THEN total ELSE 0 END,
           CASE WHEN tipo <> 'gasto_operativo' THEN total ELSE 0 END
      FROM comprobante
  ) t
 GROUP BY dia;

CREATE VIEW v_por_caducar AS
SELECT p.sku, p.nombre, l.id AS lote_id, l.cantidad_actual, l.caducidad,
       l.caducidad - current_date AS dias_restantes,
       p.precio_venta, p.costo
  FROM lote l JOIN producto p ON p.id = l.producto_id
 WHERE l.cantidad_actual > 0 AND l.caducidad IS NOT NULL
   AND l.caducidad <= current_date + 7;

CREATE VIEW v_stock_bajo AS
SELECT sku, nombre, unidad, existencia, stock_minimo
  FROM producto
 WHERE activo AND existencia <= stock_minimo;

CREATE VIEW v_inventario AS
SELECT p.sku, p.nombre, c.nombre AS categoria, p.unidad, p.precio_venta, p.costo,
       p.existencia, p.stock_minimo, p.existencia <= p.stock_minimo AS bajo,
       (SELECT min(l.caducidad) FROM lote l
         WHERE l.producto_id = p.id AND l.cantidad_actual > 0) AS proxima_caducidad
  FROM producto p LEFT JOIN categoria c ON c.id = p.categoria_id
 WHERE p.activo;

-- Horarios pico reales (get_sales_cohort_metrics)
CREATE VIEW v_horas_pico AS
SELECT extract(isodow FROM ocurrida_en)::int AS dia_semana,   -- 1 = lunes
       extract(hour FROM ocurrida_en)::int   AS hora,
       count(*) AS ventas, round(avg(total), 2) AS ticket_promedio
  FROM venta WHERE estado = 'registrada' GROUP BY 1, 2;

-- Venta cruzada real (get_cross_sell_recommendations)
CREATE VIEW v_coocurrencia AS
SELECT pa.sku AS sku_a, pb.sku AS sku_b, count(*) AS veces
  FROM venta_item a
  JOIN venta_item b ON a.venta_id = b.venta_id AND a.producto_id < b.producto_id
  JOIN producto pa ON pa.id = a.producto_id
  JOIN producto pb ON pb.id = b.producto_id
 GROUP BY 1, 2;

-- cierre_de_caja
CREATE VIEW v_caja_dia AS
SELECT v.ocurrida_en::date AS dia,
       count(*) AS ventas,
       coalesce(sum(v.total) FILTER (WHERE v.metodo_pago = 'efectivo'), 0)  AS efectivo,
       coalesce(sum(v.total) FILTER (WHERE v.metodo_pago <> 'efectivo'), 0) AS digital,
       count(*) FILTER (WHERE p.estado <> 'conciliado') AS pagos_sin_conciliar
  FROM venta v LEFT JOIN pago p ON p.venta_id = v.id
 WHERE v.estado = 'registrada' GROUP BY 1;

-- conciliar_pagos / registrar_pago
CREATE VIEW v_pagos_pendientes AS
SELECT p.id AS pago_id, p.metodo, p.monto, p.estado, p.referencia, v.folio, p.creado_en,
       p.venta_id IS NULL AS sin_venta
  FROM pago p LEFT JOIN venta v ON v.id = p.venta_id
 WHERE p.estado <> 'conciliado';

-- "La IA acertó el X % de las veces" (para la demo)
CREATE VIEW v_precision_vision AS
SELECT i.modelo_version, count(*) AS items,
       round(avg((NOT vi.corregido)::int) * 100, 1) AS acierto_pct
  FROM venta_item vi
  JOIN venta v ON v.id = vi.venta_id
  JOIN inferencia_vision i ON i.id = v.inferencia_id
 GROUP BY i.modelo_version;

-- Búsqueda por nombre, sku o alias ("la coca") — find_product_by_name_or_alias y GET /productos?q=
CREATE FUNCTION buscar_productos(q text, limite int DEFAULT 10)
RETURNS TABLE (sku text, nombre text, precio_unitario numeric, existencia numeric,
               unidad unidad_medida, similitud real)
LANGUAGE sql STABLE AS $$
  WITH t AS (SELECT normalizar(q) AS q),
  candidatos AS (
    SELECT p.id, greatest(similarity(normalizar(p.nombre), t.q),
                          coalesce(max(similarity(a.alias, t.q)), 0)) AS s,
           -- coalesce: codigo_barras/alias nulos darían NULL y NULL va primero en ORDER BY DESC
           coalesce(bool_or(p.sku = upper(q) OR p.codigo_barras = q OR a.alias = t.q), false) AS exacto
      FROM producto p CROSS JOIN t
      LEFT JOIN producto_alias a ON a.producto_id = p.id
     WHERE p.activo
     GROUP BY p.id, p.nombre, t.q
  )
  SELECT p.sku, p.nombre, p.precio_venta, p.existencia, p.unidad, c.s
    FROM candidatos c JOIN producto p ON p.id = c.id
   WHERE c.exacto OR c.s >= 0.35 OR normalizar(p.nombre) LIKE '%' || (SELECT q FROM t) || '%'
   ORDER BY c.exacto DESC, c.s DESC, p.nombre
   LIMIT limite
$$;
