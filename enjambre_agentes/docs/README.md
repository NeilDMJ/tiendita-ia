# Documentación Técnica del Enjambre de Agentes — Tiendita IA

> **Propósito de este directorio (`docs/`):** Proveer contexto técnico completo, exacto y modular para que tanto ingenieros como **agentes de IA** puedan comprender, operar, auditar y extender el ecosistema multiagente de **Tiendita IA** sin asumir comportamientos ni inspeccionar el repositorio a ciegas.

---

## Mapa de Documentación (Qué leer según tu necesidad)

| Documento | Audiencia / Cuándo consultarlo | Contenido clave |
|---|---|---|
| [01_ARQUITECTURA_Y_ORQUESTACION.md](./01_ARQUITECTURA_Y_ORQUESTACION.md) | Entender el flujo de ejecución, estado global y HITL | Grafo LangGraph, `OrchestratorState`, enrutamiento puro, `compound_chain`, `approval_gate`, `resume_orchestration`, contratos Pydantic (`schemas/`). |
| [02_CATALOGO_AGENTES.md](./02_CATALOGO_AGENTES.md) | Conocer qué hace cada agente, sus límites y cómo opera | Fichas técnicas de los 7 roles (`supervisor`, `control`, `vendedor`, `analista`, `investigador`, `publicista`, `tutor_ui`), prompts, tools asignadas y guardias. |
| [03_CATALOGO_TOOLS_Y_BD.md](./03_CATALOGO_TOOLS_Y_BD.md) | Consultar/modificar herramientas, SQL o MCP | Inventario completo de `@tool`, pool PostgreSQL (`tiendita-db`), vistas oficiales (`v_*`), funciones PL/pgSQL (`registrar_venta`, `buscar_productos`), enums y MCP. |
| [04_MEMORIA_Y_RAG_PAGOS.md](./04_MEMORIA_Y_RAG_PAGOS.md) | Trabajar con memoria, FAISS, `pgvector` o CoDi/SPEI/DiMo | Las 5 capas de memoria, indexación de `data/Embeddings/datos/`, sincronización `pgvector`, `buscar_guia_pago()`, `buscar_rag_pagos()` y reportes históricos. |
| [05_STACK_NVIDIA_Y_RESILIENCIA.md](./05_STACK_NVIDIA_Y_RESILIENCIA.md) | Configurar modelos, NVIDIA NIM/NeMo, fallbacks o seguridad | NIM LLMs, NIM Vision, NeMo Retriever, NeMo Guardrails (Colang), NeMo Customizer (LoRA/SFT), `ACTIVE_AGENT_BRAINS`, `ResilientChatModel` y Circuit Breaker. |
| [06_OPERACION_CLI_API_Y_EXTENSION.md](./06_OPERACION_CLI_API_Y_EXTENSION.md) | Ejecutar el sistema o añadir nuevos agentes/tools | Comandos CLI (`main.py`, `scripts/cli_tester.py`), endpoints FastAPI (`api.py`), variables `.env` y guías paso a paso para extender el enjambre. |
| [07_CONSUMO_API_LAN_Y_REMOTO.md](./07_CONSUMO_API_LAN_Y_REMOTO.md) | Consumir la API desde otra PC en Wi-Fi, app móvil o Internet | Guía paso a paso de `main.py --serve`, firewall LAN, túneles `ssh`, ejemplos `curl`/Python/JS para todos los endpoints REST y WebSocket bidireccional con HITL. |

Documentos complementarios en la raíz del repositorio:
- [AGENTS.md](../AGENTS.md) — Resumen ejecutivo de roles y reglas para agentes de IA.
- [ARCHITECTURE_GRAPH.md](../ARCHITECTURE_GRAPH.md) — Diagrama Mermaid autogenerado directamente desde el grafo compilado (`scripts/generar_diagrama.py`).
- [README.md](../README.md) — Guía rápida de arranque.

---

## Reglas Inquebrantables del Repositorio (Leer Antes de Modificar Código)

Cualquier agente de IA o desarrollador que trabaje sobre `enjambre_agentes/` **debe respetar estas 7 invariantes**:

1. **Razonamiento Puro (Cero enrutamiento por palabras clave):**
   - Está estrictamente prohibido usar condicionales por palabras clave (`if "palabra" in query`) para enrutar agentes o seleccionar herramientas en `agents/` o `tools/`.
   - El enrutamiento del `supervisor` usa salida estructurada Pydantic (`with_structured_output(SupervisorDecision)`) y los especialistas seleccionan sus `@tool` mediante *Tool Calling* nativo del LLM.
2. **Directorios Intocables:**
   - Nunca modificar ni eliminar `Referencias/` (`OptiAgent/`, `Research-Knowledge-Backend/`) ni los scripts SQL del backend (`../back/db/init/`).
3. **100% NVIDIA NIM por Defecto + Overrides Dinámicos en Runtime:**
   - Todos los agentes resuelven su LLM en tiempo de ejecución vía `get_llm(role="<rol>")` desde `ACTIVE_AGENT_BRAINS` (`config/models.py`).
   - Default exclusivo NVIDIA: `supervisor`, `analista`, `investigador` → `nvidia/nemotron-3-super-120b-a12b`; `control`, `vendedor`, `publicista`, `tutor_ui` → `nvidia/llama-3.1-nemotron-nano-8b-v1`.
   - El rescate hacia `Gemini → Groq → Cohere → Ollama` opera de forma silenciosa mediante `.with_fallbacks()` y Circuit Breaker.
4. **Base de Datos Real (`tiendita-db`), Sin Mocks Operativos:**
   - Las lecturas consultan las vistas oficiales (`v_inventario`, `v_por_caducar`, `v_stock_bajo`, `v_margen_producto`, `v_flujo_caja`, `v_ventas_dia`, `v_coocurrencia`) y `buscar_productos()`.
   - Las ventas usan la función transaccional `registrar_venta(jsonb)` en PostgreSQL respetando los enums reales (`origen_venta`: `'asistente'`, `tipo_movimiento`: `'entrada'|'salida'|'merma'`, `metodo_pago`: `'efectivo'|'tarjeta'|'transferencia'|'qr'`).
5. **Contratos de Funciones de Orquestación (`agents/graph.py`):**
   - Mantener exactamente las firmas públicas `run_orchestration`, `run_orchestration_stream`, `resume_orchestration` y `get_graph_state`.
6. **Seguridad y Guardias Obligatorias:**
   - Nunca exponer `costo` / `costo_unitario` en mostrador (`vendedor` pasa por `prevent_cost_leakage` y `rails.co`).
   - `tutor_ui` responde en **máximo 2 oraciones accionables** (`TutorResponse` + `enforce_max_sentences`) respaldadas por el RAG de CoDi/SPEI/DiMo.
   - `analista` es estrictamente de **Solo Lectura**.
   - Acciones sensibles de `control`, `vendedor` y `publicista` se pausan en `approval_gate` (HITL) antes de ejecutar `COMMIT`.
7. **Dependencias Prohibidas:**
   - No reintroducir `chromadb`, `pinecone`, `geopandas`, `spacy` ni `torchvision` en `pyproject.toml` o `requirements.txt`.

---

## Mapa de Directorios

```text
enjambre_agentes/
├── main.py                      # Entrada CLI directa (lanza cli_tester; soporta --agent-brain)
├── api.py                       # Servidor FastAPI (REST + SSE streaming + HITL + visión)
├── AGENTS.md                    # Resumen de agentes y reglas para asistentes IA
├── ARCHITECTURE_GRAPH.md        # Diagrama Mermaid autogenerado del grafo LangGraph
├── pyproject.toml               # Dependencias gestionadas con uv
├── requirements.txt             # Lista sincronizada de dependencias
├── agents/                      # 1 Supervisor + 6 Especialistas + Grafo LangGraph
│   ├── graph.py                 # StateGraph, routers, approval_gate, checkpointer, API pública
│   ├── supervisor.py            # Enrutador central por razonamiento puro (SupervisorDecision)
│   ├── control.py               # Inventario, catálogo visual, OCR tickets y alertas caducidad
│   ├── vendedor.py              # Mostrador POS, carritos, upselling y reglas CoDi/SPEI/DiMo
│   ├── analista.py              # Finanzas y auditoría de Solo Lectura (flujo, márgenes, rotación)
│   ├── investigador.py          # Estrategia comercial (Tavily + scraping + RAG) en 9 secciones
│   ├── publicista.py            # Campañas de rescate por caducidad, CTA y video vertical 9:16
│   └── tutor_ui.py              # Copiloto de pantalla CoDi/SPEI/DiMo (máx. 2 oraciones)
├── config/                      # Fábrica de cerebros, proveedores, claves y NeMo Guardrails
│   ├── models.py                # ACTIVE_AGENT_BRAINS, ResilientChatModel, Circuit Breaker, get_llm
│   ├── agentes.yaml             # Configuración declarativa por rol y adaptadores LoRA
│   ├── keys.py                  # Carga centralizada de .env (sin llaves hardcodeadas)
│   ├── models_nvidia.py         # Introspección en vivo NVIDIA NIM (/v1/models, timeout <= 4s)
│   ├── models_gemini.py         # Introspección en vivo Google Gemini
│   ├── models_groq.py           # Introspección en vivo Groq
│   ├── models_cohere.py         # Introspección en vivo Cohere
│   ├── models_ollama.py         # Introspección en vivo Ollama local (/api/tags)
│   ├── logger.py                # Logging estructurado con Rich
│   └── guardrails/              # NeMo Guardrails (config.yml + rails.co en Colang)
├── schemas/                     # Contratos Pydantic y estado compartido
│   ├── state.py                 # OrchestratorState (TypedDict de LangGraph)
│   ├── commerce.py              # Producto, Lote, CarritoPOS, ApprovalPayload
│   ├── vision.py                # CatalogScan*, POSCheckout*, ReceiptOCR*
│   ├── ui_copilot.py            # UIState, TutorResponse (validador <= 2 oraciones)
│   └── reports.py               # StrategicReport (9 secciones), VideoPrompt (9:16), PromoAssets
├── tools/                       # Herramientas @tool, clientes BD/Visión/RAG y guardias
│   ├── db_client.py             # Pool PostgreSQL thread-safe + vistas oficiales
│   ├── inventory_tools.py       # Altas, movimientos de stock, alertas caducidad y stock bajo
│   ├── pos_tools.py             # Carritos, registrar_venta(), upsell y reglas CoDi/SPEI/DiMo
│   ├── analytics_tools.py       # Flujo de caja, márgenes, rotación, Tavily y scraping web
│   ├── media_tools.py           # Copys, video 9:16, CTA y consultar_guia_pago_digital
│   ├── vision_nim.py            # Cliente multimodal NVIDIA NIM Vision + buffer imagen activa
│   ├── rag_nemo.py              # RAG Dual (FAISS + pgvector + NeMo Rerank) CoDi/SPEI/DiMo
│   ├── few_shot_retriever.py    # Ejemplos Few-Shot dinámicos + registro HITL SFT (JSONL)
│   ├── guards.py                # prevent_cost_leakage, enforce_max_sentences, enforce_db_grounding
│   └── mcp_exporter.py          # Manifiesto MCP de todas las herramientas comerciales
├── scripts/                     # Herramientas ejecutables
│   ├── cli_tester.py            # CLI interactivo real conectado a PostgreSQL y LangGraph
│   ├── run_server.py            # Lanzador nativo LAN + túneles SSH (localhost.run / pinggy / vps)
│   ├── test_client.py           # Cliente de prueba remoto REST + WebSocket + HITL
│   ├── export_nemo_sft.py       # Exportador HITL -> JSONL SFT para NeMo Customizer (LoRA)
│   ├── generar_diagrama.py      # Regenera ARCHITECTURE_GRAPH.md desde tiendita_graph
│   └── test_tools.py            # Pruebas de integración contra tiendita-db
├── data/                        # Persistencia local y conocimiento precalculado
│   ├── Embeddings/datos/        # conocimiento.jsonl (934), embeddings.npz (4096-d), guias.json
│   ├── vectorstores/faiss/      # Índice FAISS persistente + respaldo 4096-d + manifiesto
│   ├── reportes/                # Reportes estratégicos históricos (.json y .md)
│   └── hitl_feedback/           # Feedback HITL y dataset SFT para NeMo Customizer
├── docs/                        # Esta suite de documentación modular
├── tests/                       # Banco de pruebas JSON (test_cases.json)
└── Referencias/                 # [INTOCABLE] Proyectos de referencia originales
```
