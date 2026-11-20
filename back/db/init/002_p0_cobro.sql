-- 002 · P0: catálogo, visión, ventas, inventario y pagos (recorrido Cobrar)

CREATE TABLE categoria (
  id     smallserial PRIMARY KEY,
  nombre text NOT NULL UNIQUE
);

CREATE TABLE producto (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sku                text NOT NULL UNIQUE,                 -- el front y los agentes usan sku
  nombre             text NOT NULL,
  categoria_id       smallint REFERENCES categoria(id),
  etiqueta_vision    text UNIQUE,                          -- clase del detector (back/datos/catalogo.csv)
  codigo_barras      text,
  unidad             unidad_medida NOT NULL DEFAULT 'pieza',
  precio_venta       numeric(10,2) NOT NULL CHECK (precio_venta >= 0),   -- por unidad
  costo              numeric(10,2) CHECK (costo >= 0),
  existencia         numeric(10,3) NOT NULL DEFAULT 0,     -- caché de movimiento_inventario
  stock_minimo       numeric(10,3) NOT NULL DEFAULT 3,
  atributos_visuales jsonb,
  activo             boolean NOT NULL DEFAULT true,
  origen             text NOT NULL DEFAULT 'tendero'
                     CHECK (origen IN ('semilla', 'tendero', 'catalog_scan', 'chat')),
  creado_en          timestamptz NOT NULL DEFAULT now(),
  actualizado_en     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX producto_nombre_trgm ON producto USING gin (nombre gin_trgm_ops);
CREATE TRIGGER producto_actualizado BEFORE UPDATE ON producto
  FOR EACH ROW EXECUTE FUNCTION tocar_actualizado_en();

-- "la coca", "blanquillos": guardar con normalizar(alias)
CREATE TABLE producto_alias (
  producto_id uuid NOT NULL REFERENCES producto(id) ON DELETE CASCADE,
  alias       text NOT NULL CHECK (alias = normalizar(alias)),
  PRIMARY KEY (producto_id, alias)
);
CREATE UNIQUE INDEX producto_alias_unico ON producto_alias (alias);
CREATE INDEX producto_alias_trgm ON producto_alias USING gin (alias gin_trgm_ops);

-- Cada foto enviada a visión. Su id ES el `imagen_id` del contrato.
CREATE TABLE inferencia_vision (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  endpoint       endpoint_vision NOT NULL,
  imagen_url     text,
  modelo_version text NOT NULL,
  estado_http    smallint NOT NULL,
  respuesta      jsonb,
  latencia_ms    integer,
  creada_en      timestamptz NOT NULL DEFAULT now()
);

CREATE SEQUENCE folio_venta_seq;

CREATE TABLE venta (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  id_local       text NOT NULL UNIQUE,                  -- idempotencia
  folio          text NOT NULL UNIQUE
                 DEFAULT 'V-' || lpad(nextval('folio_venta_seq')::text, 4, '0'),
  inferencia_id  uuid REFERENCES inferencia_vision(id),
  origen         origen_venta NOT NULL,
  metodo_pago    metodo_pago NOT NULL,
  total          numeric(10,2) NOT NULL CHECK (total >= 0),
  recibido       numeric(10,2),
  duracion_seg   integer,
  fuera_de_linea boolean NOT NULL DEFAULT false,
  estado         estado_venta NOT NULL DEFAULT 'registrada',
  ocurrida_en    timestamptz NOT NULL DEFAULT now(),
  registrada_en  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX venta_ocurrida_en ON venta (ocurrida_en DESC);

CREATE TABLE venta_item (
  id              bigserial PRIMARY KEY,
  venta_id        uuid NOT NULL REFERENCES venta(id) ON DELETE CASCADE,
  producto_id     uuid REFERENCES producto(id),
  deteccion_id    bigint,                                -- FK en 003
  nombre          text NOT NULL,
  cantidad        numeric(10,3) NOT NULL CHECK (cantidad > 0),
  precio_unitario numeric(10,2) NOT NULL CHECK (precio_unitario >= 0),
  costo_unitario  numeric(10,2),
  subtotal        numeric(10,2) GENERATED ALWAYS AS (round(cantidad * precio_unitario, 2)) STORED,
  libre           boolean NOT NULL DEFAULT false,
  corregido       boolean NOT NULL DEFAULT false,
  CHECK (libre OR producto_id IS NOT NULL)
);
CREATE INDEX venta_item_venta ON venta_item (venta_id);
CREATE INDEX venta_item_producto ON venta_item (producto_id);

CREATE TABLE movimiento_inventario (
  id             bigserial PRIMARY KEY,
  producto_id    uuid NOT NULL REFERENCES producto(id),
  lote_id        uuid,                                   -- FK en 003
  tipo           tipo_movimiento NOT NULL,
  cantidad       numeric(10,3) NOT NULL CHECK (cantidad <> 0),   -- negativa = sale
  venta_id       uuid REFERENCES venta(id),
  comprobante_id uuid,                                   -- FK en 003
  nota           text,
  creado_en      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX movimiento_producto ON movimiento_inventario (producto_id, creado_en DESC);

-- Efectivo nace 'conciliado'; digitales nacen 'pendiente'. venta_id null = transferencia sin venta.
CREATE TABLE pago (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  venta_id       uuid UNIQUE REFERENCES venta(id),
  metodo         metodo_pago NOT NULL,
  monto          numeric(10,2) NOT NULL CHECK (monto > 0),
  estado         estado_pago NOT NULL DEFAULT 'pendiente',
  referencia     text,
  inferencia_id  uuid REFERENCES inferencia_vision(id),
  simulado       boolean NOT NULL DEFAULT true,          -- demo: no hay pasarela real
  creado_en      timestamptz NOT NULL DEFAULT now(),
  enviado_en     timestamptz,
  recibido_en    timestamptz,
  conciliado_en  timestamptz,
  CHECK (metodo = 'efectivo' OR estado IN ('pendiente', 'enviado')
         OR referencia IS NOT NULL OR inferencia_id IS NOT NULL)
);
CREATE INDEX pago_sin_conciliar ON pago (creado_en) WHERE estado <> 'conciliado';

-- El estado del pago solo avanza
CREATE FUNCTION pago_solo_avanza() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.estado < OLD.estado THEN
    RAISE EXCEPTION 'El pago % no puede regresar de % a %', OLD.id, OLD.estado, NEW.estado;
  END IF;
  IF NEW.estado = 'enviado'    AND OLD.estado < 'enviado'    THEN NEW.enviado_en    := coalesce(NEW.enviado_en, now()); END IF;
  IF NEW.estado = 'recibido'   AND OLD.estado < 'recibido'   THEN NEW.recibido_en   := coalesce(NEW.recibido_en, now()); END IF;
  IF NEW.estado = 'conciliado' AND OLD.estado < 'conciliado' THEN NEW.conciliado_en := coalesce(NEW.conciliado_en, now()); END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER pago_estado BEFORE UPDATE OF estado ON pago
  FOR EACH ROW EXECUTE FUNCTION pago_solo_avanza();
