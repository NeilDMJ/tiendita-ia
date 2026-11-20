-- 004 · P2: negocio, conversación y aprobaciones, alertas, promociones, reportes, RAG
-- Las tablas del checkpointer de LangGraph las crea PostgresSaver.setup() (no van aquí).

CREATE TABLE negocio (
  id           boolean PRIMARY KEY DEFAULT true CHECK (id),   -- una sola fila
  nombre       text NOT NULL,
  giro         text NOT NULL DEFAULT 'abarrotes',
  responsable  text,
  municipio    text,
  horario      text,
  zona_horaria text NOT NULL DEFAULT 'America/Mexico_City'
);

-- id = thread_id de LangGraph
CREATE TABLE conversacion (
  id        text PRIMARY KEY,
  creada_en timestamptz NOT NULL DEFAULT now(),
  borrada   boolean NOT NULL DEFAULT false
);

CREATE TABLE mensaje (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversacion_id text NOT NULL REFERENCES conversacion(id) ON DELETE CASCADE,
  autor           text NOT NULL CHECK (autor IN ('tendero', 'asistente', 'sistema')),
  rol             rol_asistente,
  texto           text NOT NULL,
  contexto        jsonb,
  no_resuelto     boolean NOT NULL DEFAULT false,
  ruteo           jsonb,          -- agente del grafo, delegaciones, notas del supervisor
  herramientas    jsonb,          -- [{tool, args, resultado}]
  modelo_version  text,
  simulado        boolean NOT NULL DEFAULT false,
  creado_en       timestamptz NOT NULL DEFAULT now(),
  CHECK (autor <> 'asistente' OR rol IS NOT NULL)
);
CREATE INDEX mensaje_conversacion ON mensaje (conversacion_id, creado_en);

-- Propuesta de escritura (interrupt del grafo). Se ejecuta solo si el tendero confirma.
CREATE TABLE accion_propuesta (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mensaje_id  uuid NOT NULL REFERENCES mensaje(id) ON DELETE CASCADE,
  tipo        tipo_accion NOT NULL,
  titulo      text NOT NULL,
  tool        text,
  datos       jsonb NOT NULL,
  estado      estado_accion NOT NULL DEFAULT 'pendiente',
  venta_id    uuid REFERENCES venta(id),
  resuelta_en timestamptz
);
CREATE INDEX accion_pendiente ON accion_propuesta (estado) WHERE estado = 'pendiente';

CREATE TABLE alerta (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tipo        tipo_alerta NOT NULL,
  agente      rol_asistente NOT NULL,
  producto_id uuid REFERENCES producto(id),
  lote_id     uuid REFERENCES lote(id),
  pago_id     uuid REFERENCES pago(id),
  detalle     jsonb,
  atendida    boolean NOT NULL DEFAULT false,
  creada_en   timestamptz NOT NULL DEFAULT now(),
  CHECK (producto_id IS NOT NULL OR pago_id IS NOT NULL)
);
CREATE UNIQUE INDEX alerta_abierta ON alerta (
  tipo,
  coalesce(producto_id, '00000000-0000-0000-0000-000000000000'::uuid),
  coalesce(lote_id,     '00000000-0000-0000-0000-000000000000'::uuid),
  coalesce(pago_id,     '00000000-0000-0000-0000-000000000000'::uuid)
) WHERE NOT atendida;

CREATE TABLE promocion (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  producto_id   uuid NOT NULL REFERENCES producto(id),
  lote_id       uuid REFERENCES lote(id),
  alerta_id     uuid REFERENCES alerta(id),
  motivo        text NOT NULL,
  descuento     text,
  precio_promo  numeric(10,2) CHECK (precio_promo >= 0),
  bajo_costo    boolean NOT NULL DEFAULT false,
  copy          text NOT NULL,
  video_prompt  text,
  video_job_id  text,
  video_url     text,
  vigente_hasta date,
  estado        estado_promocion NOT NULL DEFAULT 'propuesta',
  simulada      boolean NOT NULL DEFAULT true,
  creada_en     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reporte (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  periodo_inicio date NOT NULL,
  periodo_fin    date NOT NULL CHECK (periodo_fin >= periodo_inicio),
  generado_por   rol_asistente NOT NULL DEFAULT 'cuentas',
  -- [{ "seccion": "...", "contenido": "...", "fuente": "bd" | "externa" | "hipotesis" }]
  secciones      jsonb NOT NULL CHECK (jsonb_typeof(secciones) = 'array'),
  resumen        text,
  creado_en      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE referencia_externa (
  id            bigserial PRIMARY KEY,
  tema          text NOT NULL,
  contenido     jsonb NOT NULL,
  url           text,
  simulada      boolean NOT NULL DEFAULT true,
  consultada_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX referencia_tema ON referencia_externa (tema, consultada_en DESC);

-- RAG. La dimensión depende del modelo de embeddings NVIDIA elegido:
-- 1024 = nvidia/nv-embedqa-e5-v5. Si cambia, ajustar aquí ANTES de cargar documentos.
CREATE TABLE documento (
  id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  titulo    text NOT NULL,
  fuente    text,
  creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE fragmento (
  id           bigserial PRIMARY KEY,
  documento_id uuid NOT NULL REFERENCES documento(id) ON DELETE CASCADE,
  texto        text NOT NULL,
  embedding    vector(1024) NOT NULL
);
CREATE INDEX fragmento_embedding ON fragmento USING hnsw (embedding vector_cosine_ops);
