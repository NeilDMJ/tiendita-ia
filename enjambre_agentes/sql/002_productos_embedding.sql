-- Búsqueda híbrida de catálogo (resolve_product_hybrid): vector por producto.
-- Requiere que la tabla `productos` ya exista. Aplicar con:
--   uv run python -c "from tools_bridge import ensure_catalog_schema; ensure_catalog_schema()"
-- Poblar vectores con: index_catalog_embeddings()

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE productos ADD COLUMN IF NOT EXISTS texto_indexado TEXT;
ALTER TABLE productos ADD COLUMN IF NOT EXISTS embedding vector(1024);

CREATE INDEX IF NOT EXISTS idx_productos_embedding
    ON productos USING hnsw (embedding vector_cosine_ops);
