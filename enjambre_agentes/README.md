# Tiendita IA — Enjambre Multiagente Comercial Multimodal

Ecosistema comercial con visión artificial, orquestación multiagente en **LangGraph**, base de datos **PostgreSQL (`tiendita-db` + `pgvector`)**, **RAG Dual especializado en CoDi / SPEI / DiMo** y tecnologías **NVIDIA (NIM / NeMo)**.

---

## Capacidades Principales

- **Orquestación Multiagente Optimizada (LangGraph):** 1 Supervisor Maestro + 6 Especialistas (`control`, `vendedor`, `analista`, `investigador`, `publicista`, `tutor_ui`) con razonamiento puro, encadenamiento compuesto sanitizado y salida directa a `END` para baja latencia.
- **Stack NVIDIA NIM / NeMo (100% NVIDIA por defecto):**
  - **LLMs NIM:** `nvidia/nemotron-3-super-120b-a12b` (`supervisor`, `analista`, `investigador`) y `nvidia/llama-3.1-nemotron-nano-8b-v1` (`control`, `vendedor`, `publicista`, `tutor_ui`), con cambio individual en vivo (`set_agent_brain`) y rescate silencioso `.with_fallbacks()` + Circuit Breaker (`Gemini → Groq → Cohere → Ollama`).
  - **NIM Vision (VL):** procesamiento real de imágenes desde disco o API (`/imagen`, `/catalog-scan`, `/pos-checkout`, `/receipt-ocr`).
  - **NeMo Retriever + RAG Dual:** 969 fragmentos oficiales de **CoDi, SPEI y DiMo** (`data/Embeddings/datos/`) indexados en `FAISS` (`data/vectorstores/faiss/`) y sincronizados en PostgreSQL `pgvector`.
  - **NeMo Guardrails:** reglas Colang en `config/guardrails/rails.co` + guardias en `tools/guards.py`.
  - **NeMo Customizer (SFT / LoRA):** recolección de feedback HITL y exportación JSONL (`scripts/export_nemo_sft.py`).
- **Base de Datos Real (`tiendita-db`):** pool thread-safe sobre PostgreSQL 16 consultando vistas oficiales (`v_inventario`, `v_por_caducar`, `v_stock_bajo`, `v_margen_producto`, `v_flujo_caja`, `v_ventas_dia`, `v_coocurrencia`) y `registrar_venta(jsonb)`.
- **Human-in-the-Loop (HITL) Real:** pausa en `approval_gate` (`[s] Aprobar / [n] Rechazar / [e] Editar`) antes de confirmar `COMMIT` sensibles en PostgreSQL.

---

## Arranque Rápido (`uv`)

```bash
# 1. Configurar entorno
cp .env.example .env
uv sync

# 2. Lanzar CLI interactivo conectado en vivo a PostgreSQL
uv run python main.py

# O iniciar con cerebros personalizados por subagente:
uv run python main.py \
  --agent-brain vendedor=Gemini:gemini-flash-lite-latest \
  --agent-brain investigador=Groq:openai/gpt-oss-120b

# 3. Levantar API REST + Streaming SSE
uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Comandos del CLI Interactivo
- `<texto libre>`: consulta inventario real, ventas, finanzas o investigación de mercado.
- `/cerebro <agente> <proveedor> <modelo>` · `/cerebros` · `/reset-cerebros`: gestión en vivo de modelos por subagente.
- `/imagen <ruta.jpg|png> <catalog|pos|ticket>`: análisis multimodal real con NIM Vision.
- `/pago <codi|spei|dimo> <pantalla> <paso> [error_code]`: asistencia del `tutor_ui` en máximo 2 oraciones respaldada por el RAG oficial.
- `/rag <consulta>`: consulta directa con scores de relevancia sobre el índice CoDi/SPEI/DiMo (`FAISS` / `pgvector`).
- `/cron` · `/estado` · `/ayuda` · `/salir`.

---

## Documentación Técnica Completa (`docs/`)

Para documentación profunda orientada a desarrolladores y **agentes de IA**, consulta [`docs/README.md`](./docs/README.md):

1. [`docs/01_ARQUITECTURA_Y_ORQUESTACION.md`](./docs/01_ARQUITECTURA_Y_ORQUESTACION.md) — Grafo LangGraph, `OrchestratorState`, routers y ciclo HITL.
2. [`docs/02_CATALOGO_AGENTES.md`](./docs/02_CATALOGO_AGENTES.md) — Fichas completas de los 7 agentes, prompts, tools y guardias.
3. [`docs/03_CATALOGO_TOOLS_Y_BD.md`](./docs/03_CATALOGO_TOOLS_Y_BD.md) — Todas las `@tool`, vistas/funciones PostgreSQL y manifiesto MCP.
4. [`docs/04_MEMORIA_Y_RAG_PAGOS.md`](./docs/04_MEMORIA_Y_RAG_PAGOS.md) — Las 5 capas de memoria y RAG Dual de CoDi, SPEI y DiMo.
5. [`docs/05_STACK_NVIDIA_Y_RESILIENCIA.md`](./docs/05_STACK_NVIDIA_Y_RESILIENCIA.md) — Tecnología NVIDIA (NIM/NeMo), `ResilientChatModel` y Circuit Breaker.
6. [`docs/06_OPERACION_CLI_API_Y_EXTENSION.md`](./docs/06_OPERACION_CLI_API_Y_EXTENSION.md) — Operación CLI/API y manual para extender el enjambre.
7. [`AGENTS.md`](./AGENTS.md) y [`ARCHITECTURE_GRAPH.md`](./ARCHITECTURE_GRAPH.md) — Resumen de roles y diagrama autogenerado.
