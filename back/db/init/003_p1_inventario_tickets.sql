-- 003 · P1: proveedores, tickets (OCR), lotes y caducidades, detecciones, precios y caja

CREATE TABLE proveedor (
  id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre   text NOT NULL UNIQUE,
  telefono text
);

-- Ticket / factura revisado por el tendero (receipt-ocr o captura manual)
CREATE TABLE comprobante (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  id_local      text NOT NULL UNIQUE,
  tipo          tipo_comprobante NOT NULL,
  proveedor_id  uuid REFERENCES proveedor(id),
  concepto      text,                                  -- "Luz del local", "Renta"
  fecha         date NOT NULL,
  total         numeric(10,2) NOT NULL CHECK (total >= 0),
  impuestos     numeric(10,2),
  inferencia_id uuid REFERENCES inferencia_vision(id),
  imagen_url    text,
  corregido     boolean NOT NULL DEFAULT false,
  registrado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX comprobante_fecha ON comprobante (fecha DESC);

CREATE TABLE comprobante_concepto (
  id             bigserial PRIMARY KEY,
  comprobante_id uuid NOT NULL REFERENCES comprobante(id) ON DELETE CASCADE,
  descripcion    text NOT NULL,
  monto          numeric(10,2),
  producto_id    uuid REFERENCES producto(id),
  cantidad       numeric(10,3)
);

CREATE TABLE lote (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  producto_id      uuid NOT NULL REFERENCES producto(id),
  comprobante_id   uuid REFERENCES comprobante(id),
  cantidad_inicial numeric(10,3) NOT NULL CHECK (cantidad_inicial > 0),
  cantidad_actual  numeric(10,3) NOT NULL CHECK (cantidad_actual >= 0),
  caducidad        date,
  costo_unitario   numeric(10,2),
  recibido_en      timestamptz NOT NULL DEFAULT now(),
  CHECK (cantidad_actual <= cantidad_inicial)
);
CREATE INDEX lote_fefo ON lote (producto_id, caducidad) WHERE cantidad_actual > 0;

CREATE TABLE deteccion (
  id            bigserial PRIMARY KEY,
  inferencia_id uuid NOT NULL REFERENCES inferencia_vision(id) ON DELETE CASCADE,
  etiqueta      text NOT NULL,
  producto_id   uuid REFERENCES producto(id),
  cantidad      integer NOT NULL DEFAULT 1,
  confianza     real NOT NULL CHECK (confianza BETWEEN 0 AND 1),
  caja          real[]  CHECK (caja IS NULL OR cardinality(caja) = 4)   -- [x, y, ancho, alto] 0–1
);

CREATE TABLE historial_precio (
  id              bigserial PRIMARY KEY,
  producto_id     uuid NOT NULL REFERENCES producto(id),
  precio_anterior numeric(10,2) NOT NULL,
  precio_nuevo    numeric(10,2) NOT NULL,
  cambiado_por    text NOT NULL DEFAULT 'tendero',
  cambiado_en     timestamptz NOT NULL DEFAULT now()
);

-- Registra solo cualquier cambio de precio (desde la app, el chat o una promo)
CREATE FUNCTION registrar_cambio_precio() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.precio_venta IS DISTINCT FROM OLD.precio_venta THEN
    INSERT INTO historial_precio (producto_id, precio_anterior, precio_nuevo, cambiado_por)
    VALUES (NEW.id, OLD.precio_venta, NEW.precio_venta,
            coalesce(current_setting('tiendita.cambiado_por', true), 'tendero'));
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER producto_precio AFTER UPDATE OF precio_venta ON producto
  FOR EACH ROW EXECUTE FUNCTION registrar_cambio_precio();

CREATE TABLE corte_caja (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dia                 date NOT NULL UNIQUE,
  ventas              integer NOT NULL,
  total_efectivo      numeric(10,2) NOT NULL,
  total_digital       numeric(10,2) NOT NULL,
  efectivo_contado    numeric(10,2),
  diferencia          numeric(10,2) GENERATED ALWAYS AS (efectivo_contado - total_efectivo) STORED,
  pagos_sin_conciliar integer NOT NULL DEFAULT 0,
  creado_en           timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE venta_item ADD FOREIGN KEY (deteccion_id) REFERENCES deteccion(id);
ALTER TABLE movimiento_inventario
  ADD FOREIGN KEY (lote_id) REFERENCES lote(id),
  ADD FOREIGN KEY (comprobante_id) REFERENCES comprobante(id);
