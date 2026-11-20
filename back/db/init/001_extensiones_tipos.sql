-- 001 · Extensiones y tipos compartidos
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- búsqueda tolerante a errores ("q=coca")
CREATE EXTENSION IF NOT EXISTS unaccent;   -- alias sin acentos
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector (RAG del asistente)

DO $$ BEGIN
  EXECUTE format('ALTER DATABASE %I SET timezone TO %L', current_database(), 'America/Mexico_City');
END $$;

-- Mismos valores que front/src/api/esquemas.ts → MetodoPago
CREATE TYPE metodo_pago      AS ENUM ('efectivo', 'transferencia', 'qr', 'tarjeta');
-- Solo avanza; el orden del enum permite comparar (estado < 'recibido')
CREATE TYPE estado_pago      AS ENUM ('pendiente', 'enviado', 'recibido', 'conciliado');
CREATE TYPE estado_venta     AS ENUM ('registrada', 'cancelada');
CREATE TYPE origen_venta     AS ENUM ('camara', 'manual', 'asistente');
CREATE TYPE endpoint_vision  AS ENUM ('pos_checkout', 'catalog_scan', 'receipt_ocr', 'payment_proof');
-- entrada | salida | merma = valores de la herramienta ajustar_stock
CREATE TYPE tipo_movimiento  AS ENUM ('venta', 'entrada', 'salida', 'merma', 'cancelacion');
-- Mismos valores que parse_receipt_ocr (enjambre_agentes)
CREATE TYPE tipo_comprobante AS ENUM ('gasto_operativo', 'inversion_inventario', 'inversion_activo');
CREATE TYPE unidad_medida    AS ENUM ('pieza', 'kg', 'litro');

-- Asistente (nombres que ve el tendero; el adaptador traduce los del grafo)
CREATE TYPE rol_asistente    AS ENUM ('caja', 'bodega', 'cuentas', 'promociones', 'tutor', 'general');
CREATE TYPE tipo_accion      AS ENUM ('confirmar_venta', 'confirmar_alta', 'aprobar_promo',
                                      'abrir_pantalla', 'modificar_item', 'registrar_pago',
                                      'ajustar_stock', 'actualizar_precio', 'registrar_gasto',
                                      'conciliar_pagos');
CREATE TYPE estado_accion    AS ENUM ('pendiente', 'confirmada', 'rechazada', 'caducada');
CREATE TYPE tipo_alerta      AS ENUM ('stock_bajo', 'caducidad', 'baja_rotacion', 'pago_sin_conciliar',
                                      'existencia_negativa');
CREATE TYPE estado_promocion AS ENUM ('propuesta', 'aprobada', 'rechazada', 'expirada');

-- Texto normalizado para alias y búsquedas: minúsculas, sin acentos, sin espacios extra
CREATE FUNCTION normalizar(t text) RETURNS text
  LANGUAGE sql STABLE AS $$ SELECT regexp_replace(lower(unaccent(trim(t))), '\s+', ' ', 'g') $$;

CREATE FUNCTION tocar_actualizado_en() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.actualizado_en := now(); RETURN NEW; END $$;
