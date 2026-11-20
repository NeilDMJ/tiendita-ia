-- 006 · Registro de venta en una sola transacción (plan §4.1).
-- Lo usan POST /ventas del back y la herramienta registrar_venta / commit_sale_transaction
-- de los agentes, para que ambos apliquen exactamente las mismas reglas.
--
-- Entrada: el JSON de SolicitudVenta (front/src/api/esquemas.ts) + "origen" opcional.
-- Salida:  el JSON de RespuestaVenta.
-- Errores (SQLSTATE → HTTP en el back):
--   TD409  sin existencia suficiente (solo ventas en línea). DETAIL = {"sku", "existencia"}
--   TD404  sku que no existe.                                DETAIL = {"sku"}
--   TD400  datos inválidos (cantidad decimal en producto por pieza, etc.)

CREATE FUNCTION respuesta_venta(p_venta_id uuid) RETURNS jsonb
LANGUAGE sql STABLE AS $$
  SELECT jsonb_build_object(
    'venta_id',    v.id,
    'folio',       v.folio,
    'total',       v.total,
    'creada_en',   v.ocurrida_en,
    'estado_pago', pg.estado,
    'existencias', coalesce((
        SELECT jsonb_agg(jsonb_build_object(
                 'sku', p.sku, 'nombre', p.nombre, 'quedan', p.existencia,
                 'bajo', p.existencia <= p.stock_minimo) ORDER BY p.nombre)
          FROM producto p
         WHERE p.id IN (SELECT producto_id FROM venta_item WHERE venta_id = v.id)
      ), '[]'::jsonb))
  FROM venta v LEFT JOIN pago pg ON pg.venta_id = v.id
  WHERE v.id = p_venta_id
$$;

CREATE FUNCTION registrar_venta(sol jsonb) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
  v_id        uuid;
  v_metodo    metodo_pago := (sol->>'metodo_pago')::metodo_pago;
  v_fuera     boolean := coalesce((sol->>'fuera_de_linea')::boolean, false);
  v_total     numeric(10,2);
  it          jsonb;
  prod        producto%ROWTYPE;
  cant        numeric(10,3);
  restante    numeric(10,3);
  lt          record;
  tomar       numeric(10,3);
BEGIN
  IF sol->>'id_local' IS NULL OR jsonb_array_length(coalesce(sol->'items', '[]')) = 0 THEN
    RAISE EXCEPTION 'Venta sin id_local o sin productos' USING ERRCODE = 'TD400';
  END IF;

  -- 1. Idempotencia: un reintento devuelve la venta ya registrada
  SELECT id INTO v_id FROM venta WHERE id_local = sol->>'id_local';
  IF FOUND THEN RETURN respuesta_venta(v_id); END IF;

  INSERT INTO venta (id_local, inferencia_id, origen, metodo_pago, total, recibido,
                     duracion_seg, fuera_de_linea, ocurrida_en)
  VALUES (sol->>'id_local',
          nullif(sol->>'imagen_id', '')::uuid,
          coalesce((sol->>'origen')::origen_venta,
                   CASE WHEN sol->>'imagen_id' IS NOT NULL THEN 'camara' ELSE 'manual' END::origen_venta),
          v_metodo, 0,
          (sol->>'recibido')::numeric,
          round((sol->>'duracion_seg')::numeric)::int,
          v_fuera,
          coalesce((sol->>'ocurrida_en')::timestamptz, now()))
  ON CONFLICT (id_local) DO NOTHING
  RETURNING id INTO v_id;
  IF v_id IS NULL THEN   -- otra petición con el mismo id_local ganó la carrera
    SELECT id INTO v_id FROM venta WHERE id_local = sol->>'id_local';
    RETURN respuesta_venta(v_id);
  END IF;

  -- 2. Ítems en orden de sku (evita interbloqueos entre ventas simultáneas)
  FOR it IN
    SELECT value FROM jsonb_array_elements(sol->'items') ORDER BY value->>'sku' NULLS LAST
  LOOP
    cant := (it->>'cantidad')::numeric;
    IF cant IS NULL OR cant <= 0 THEN
      RAISE EXCEPTION 'Cantidad inválida' USING ERRCODE = 'TD400';
    END IF;

    IF coalesce((it->>'libre')::boolean, false) THEN
      INSERT INTO venta_item (venta_id, nombre, cantidad, precio_unitario, libre, corregido)
      VALUES (v_id, it->>'nombre', cant, (it->>'precio_unitario')::numeric, true,
              coalesce((it->>'corregido')::boolean, false));
      CONTINUE;
    END IF;

    SELECT * INTO prod FROM producto WHERE sku = it->>'sku' AND activo FOR UPDATE;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'Producto no encontrado' USING ERRCODE = 'TD404',
        DETAIL = jsonb_build_object('sku', it->>'sku')::text;
    END IF;
    IF prod.unidad = 'pieza' AND cant <> trunc(cant) THEN
      RAISE EXCEPTION '% se vende por pieza: la cantidad debe ser entera', prod.nombre
        USING ERRCODE = 'TD400', DETAIL = jsonb_build_object('sku', prod.sku)::text;
    END IF;
    IF NOT v_fuera AND prod.existencia < cant THEN
      RAISE EXCEPTION 'Sin existencia suficiente de %', prod.nombre USING ERRCODE = 'TD409',
        DETAIL = jsonb_build_object('sku', prod.sku, 'existencia', prod.existencia)::text;
    END IF;

    UPDATE producto SET existencia = existencia - cant WHERE id = prod.id;

    INSERT INTO venta_item (venta_id, producto_id, nombre, cantidad, precio_unitario,
                            costo_unitario, corregido)
    VALUES (v_id, prod.id, prod.nombre, cant,
            coalesce((it->>'precio_unitario')::numeric, prod.precio_venta),
            prod.costo, coalesce((it->>'corregido')::boolean, false));

    -- FEFO: primero el lote que caduca antes
    restante := cant;
    FOR lt IN
      SELECT id, cantidad_actual FROM lote
       WHERE producto_id = prod.id AND cantidad_actual > 0
       ORDER BY caducidad NULLS LAST, recibido_en
       FOR UPDATE
    LOOP
      EXIT WHEN restante <= 0;
      tomar := least(restante, lt.cantidad_actual);
      UPDATE lote SET cantidad_actual = cantidad_actual - tomar WHERE id = lt.id;
      INSERT INTO movimiento_inventario (producto_id, lote_id, tipo, cantidad, venta_id)
      VALUES (prod.id, lt.id, 'venta', -tomar, v_id);
      restante := restante - tomar;
    END LOOP;
    IF restante > 0 THEN   -- sin lotes (producto que no caduca) o venta fuera de línea
      INSERT INTO movimiento_inventario (producto_id, tipo, cantidad, venta_id)
      VALUES (prod.id, 'venta', -restante, v_id);
    END IF;

    -- Alertas (las "dice" Bodega en el chat)
    IF prod.existencia - cant < 0 THEN
      INSERT INTO alerta (tipo, agente, producto_id, detalle)
      VALUES ('existencia_negativa', 'bodega', prod.id,
              jsonb_build_object('existencia', prod.existencia - cant,
                                 'mensaje', 'Revisa tu conteo: se vendió sin conexión más de lo registrado'))
      ON CONFLICT DO NOTHING;
    ELSIF prod.existencia - cant <= prod.stock_minimo THEN
      INSERT INTO alerta (tipo, agente, producto_id, detalle)
      VALUES ('stock_bajo', 'bodega', prod.id, jsonb_build_object('existencia', prod.existencia - cant))
      ON CONFLICT DO NOTHING;
    END IF;
  END LOOP;

  -- 3. Total calculado por la BD (manda sobre el del front)
  SELECT coalesce(sum(subtotal), 0) INTO v_total FROM venta_item WHERE venta_id = v_id;
  UPDATE venta SET total = v_total WHERE id = v_id;

  -- 4. Pago ligado a la venta
  IF v_total > 0 THEN
    INSERT INTO pago (venta_id, metodo, monto, estado, simulado, conciliado_en)
    VALUES (v_id, v_metodo, v_total,
            CASE WHEN v_metodo = 'efectivo' THEN 'conciliado' ELSE 'pendiente' END::estado_pago,
            v_metodo <> 'efectivo',
            CASE WHEN v_metodo = 'efectivo' THEN now() END);
  END IF;

  RETURN respuesta_venta(v_id);
END $$;
