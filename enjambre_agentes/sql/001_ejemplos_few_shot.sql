-- Ejemplos few-shot + Data Flywheel (NeMo Retriever sobre pgvector).
-- Aplicar con:  uv run python few_shot_retriever.py init-db
-- La dimensión 1024 corresponde a nvidia/nv-embedqa-e5-v5 (NEMO_EMBED_DIMS).
-- HNSW requiere pgvector >= 0.5.0.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS ejemplos_few_shot (
    id             BIGSERIAL    PRIMARY KEY,
    rol_agente     TEXT         NOT NULL,
    entrada_json   JSONB        NOT NULL,
    salida_json    JSONB        NOT NULL,
    texto_indexado TEXT         NOT NULL,          -- texto embebido (derivado de entrada_json)
    embedding      vector(1024),                   -- NULL hasta ejecutar backfill si NeMo no respondió
    origen         TEXT         NOT NULL DEFAULT 'seed'
                   CHECK (origen IN ('seed', 'assistant_dataset', 'hitl_aprobado', 'hitl_editado')),
    verificado     BOOLEAN      NOT NULL DEFAULT FALSE,
    huella         TEXT         NOT NULL UNIQUE,   -- sha256(rol + entrada + salida): deduplicación
    creado_en      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ejemplos_rol_verificado
    ON ejemplos_few_shot (rol_agente) WHERE verificado;

CREATE INDEX IF NOT EXISTS idx_ejemplos_embedding
    ON ejemplos_few_shot USING hnsw (embedding vector_cosine_ops);
