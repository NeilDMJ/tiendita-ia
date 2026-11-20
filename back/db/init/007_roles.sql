-- 007 · Roles por agente (matriz de idea.txt / plan §6).
-- Son NOLOGIN: el back se conecta con el usuario de la BD y, antes de correr el SQL de un agente,
-- hace  SET LOCAL ROLE ag_<agente>;  dentro de una transacción (y READ ONLY si solo lee).
-- Las escrituras de negocio (venta, pago, producto, lote, comprobante) NO las hace ningún
-- rol de agente: el agente propone (accion_propuesta) y el back ejecuta cuando el tendero confirma.

DO $$
DECLARE r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['ag_orquestador','ag_vendedor','ag_control','ag_analista',
                           'ag_investigador','ag_publicista','ag_tutor']
  LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN', r);
    END IF;
    EXECUTE format('GRANT %I TO %I', r, current_user);   -- permite SET ROLE desde el back
    EXECUTE format('GRANT USAGE ON SCHEMA public TO %I', r);
  END LOOP;
END $$;

-- Orquestador: historial del chat y propuestas
GRANT SELECT, INSERT ON conversacion, mensaje, accion_propuesta TO ag_orquestador;

-- Vendedor (Caja)
GRANT SELECT ON producto, producto_alias, categoria, promocion,
                v_inventario, v_coocurrencia, v_pagos_pendientes TO ag_vendedor;
GRANT EXECUTE ON FUNCTION buscar_productos(text, int) TO ag_vendedor;
GRANT SELECT, INSERT ON accion_propuesta TO ag_vendedor;

-- Control (Bodega)
GRANT SELECT ON producto, producto_alias, categoria, lote, movimiento_inventario, comprobante,
                proveedor, v_inventario, v_stock_bajo, v_por_caducar, v_caja_dia,
                v_pagos_pendientes TO ag_control;
GRANT EXECUTE ON FUNCTION buscar_productos(text, int) TO ag_control;
GRANT SELECT, INSERT, UPDATE ON alerta, corte_caja TO ag_control;
GRANT SELECT, INSERT ON accion_propuesta TO ag_control;

-- Analista (Cuentas): solo vistas + guardar reportes
GRANT SELECT ON v_ventas_dia, v_margen_producto, v_flujo_caja, v_por_caducar, v_stock_bajo,
                v_inventario, v_horas_pico, v_coocurrencia, v_caja_dia, v_precision_vision,
                negocio TO ag_analista;
GRANT SELECT, INSERT ON reporte TO ag_analista;

-- Investigador
GRANT SELECT ON v_ventas_dia, v_horas_pico, v_margen_producto, negocio TO ag_investigador;
GRANT SELECT, INSERT ON referencia_externa TO ag_investigador;

-- Publicista (Promociones)
GRANT SELECT ON producto, v_por_caducar, v_inventario, alerta TO ag_publicista;
GRANT SELECT, INSERT, UPDATE ON promocion TO ag_publicista;

-- Tutor (Ayuda de pagos)
GRANT SELECT ON documento, fragmento, v_pagos_pendientes TO ag_tutor;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ag_control, ag_analista, ag_investigador;
