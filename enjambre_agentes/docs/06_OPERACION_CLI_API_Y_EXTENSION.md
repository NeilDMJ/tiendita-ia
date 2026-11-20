# 06 · Operación (CLI, API REST) y Manual de Extensión para Agentes de IA

Guía operativa práctica para ejecutar Tiendita IA y recetas exactas para que un agente de IA o desarrollador amplíe el sistema sin romper sus invariantes.

---

## 1. Requisitos y Variables de Entorno (`.env`)

Las claves se cargan únicamente desde [config/keys.py](../config/keys.py) vía `python-dotenv`.

| Variable | Obligatoria | Propósito |
|---|---|---|
| `DATABASE_URL` | **Sí** | DSN de PostgreSQL (`tiendita-db`), ej. `postgresql://tiendita:...@localhost:5432/tiendita`. |
| `NVIDIA_API_KEY` | **Sí** (default) | API key de NVIDIA NIM (`nvapi-...`) para LLMs y Vision VL. |
| `NVIDIA_BASE_URL` | Opcional | Default: `https://integrate.api.nvidia.com/v1` (ajustable para DGX Spark local). |
| `GEMINI_API_KEY` | Recomendada | Respaldo silencioso de baja latencia (`gemini-flash-lite-latest`). |
| `GROQ_API_KEY` | Recomendada | Respaldo ultrarrápido (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`). |
| `COHERE_API_KEY` | Opcional | Respaldo adicional (`command-r-08-2024`). |
| `OLLAMA_BASE_URL` | Opcional | Respaldo 100% local offline (default `http://localhost:11434`). |
| `TAVILY_API_KEY` | Para `investigador` | Búsqueda web en tiempo real (`search_web_tavily`). |
| `HF_TOKEN` | Opcional | Acceso a modelos/embeddings de HuggingFace. |
| `LANGSMITH_TRACING` | Opcional | `"false"` por defecto; activar `"true"` con `LANGSMITH_API_KEY` para trazas. |

### Instalación de dependencias con `uv`
```bash
cd /home/m4r10/Documents/tiendita-ia/enjambre_agentes
uv sync
```

---

## 2. Interfaz CLI Interactiva (`main.py` y `scripts/cli_tester.py`)

### Modos de arranque
```bash
# 1. Arrancar CLI interactivo (100% NVIDIA por defecto)
uv run python main.py

# 2. Arrancar CLI con cerebros personalizados desde línea de comandos
uv run python main.py \
  --agent-brain vendedor=Gemini:gemini-flash-lite-latest \
  --agent-brain investigador=Groq:openai/gpt-oss-120b

# 3. Arrancar directamente el módulo del CLI
uv run python -m scripts.cli_tester

# 4. Consulta puntual (one-shot) no interactiva
uv run python main.py --query "¿Cuáles son los 3 productos más vendidos?"

# 5. Inspeccionar modelos o cerebros activos
uv run python main.py --list-models
uv run python main.py --brains
```

### Comandos dentro del CLI interactivo

| Comando | Qué hace |
|---|---|
| `<texto libre>` | Envía una consulta o instrucción comercial real (`event_source="chat"`) contra PostgreSQL / Tavily / RAG. |
| `/cerebro <agente> <proveedor> <modelo>` | Cambia el LLM de un subagente en vivo sin reiniciar (ej. `/cerebro vendedor Gemini gemini-flash-lite-latest`). |
| `/cerebros` | Abre el asistente interactivo con `listar_modelos_disponibles()` para asignar modelos por subagente. |
| `/reset-cerebros` | Restaura los 7 agentes al perfil 100% NVIDIA NIM y limpia cooldowns. |
| `/imagen <ruta.jpg\|png> <catalog\|pos\|ticket>` | Lee una imagen real del disco, la codifica en base64 y la procesa vía NVIDIA NIM Vision (`event_source="vision_api"`). |
| `/pago <codi\|spei\|dimo> <pantalla> <paso> [error_code]` | Envía `ui_state` real a `tutor_ui` y responde en máximo 2 oraciones respaldadas por el RAG de Banxico. |
| `/rag <consulta>` | Consulta el índice RAG (`FAISS` / `pgvector`) de CoDi, SPEI y DiMo mostrando método, documento, sección y score. Acepta prefijo `codi:`, `spei:` o `dimo:`. |
| `/cron` | Ejecuta el barrido real de lotes por caducar y stock crítico en PostgreSQL (`control` → `publicista`). |
| `/estado` | Inspecciona el `OrchestratorState` actual en el checkpointer y las métricas vivas de `tiendita-db`. |
| `/ayuda` | Muestra la tabla de comandos disponibles. |
| `/salir` o `/exit` | Cierra limpiamente el pool de PostgreSQL (`close_db_pool()`) y sale. |

### Interacción HITL en terminal
Cuando un agente detona `approval_gate`, el CLI pausa el flujo, imprime el `ApprovalPayload` real en un panel `rich` y pregunta:
- `s` — Aprobar: ejecuta `resume_orchestration(..., approved=True)` y confirma el `COMMIT` en PostgreSQL.
- `n` — Rechazar: cancela sin escribir en PostgreSQL y guarda el motivo en el log SFT.
- `e` — Editar: aplica la corrección del operador antes de aprobar y registrar el ejemplo para NeMo Customizer.

---

## 3. API REST y Streaming SSE ([api.py](../api.py))

Arranque del servidor:
```bash
uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

| Método y Ruta | Contrato / Función |
|---|---|
| `GET /health` | Estado del servicio, capacidades multimodales, Dual RAG y proveedores soportados. |
| `GET /models?provider=...` | Lista de modelos por proveedor, estado en vivo (`obtener_estado_proveedores`) y asignación de los 7 cerebros. |
| `POST /orchestrate` | Ejecución síncrona (`input_text`, `thread_id`, `event_source`, `vision_payload`, `ui_state`, `provider`, `model_name`). |
| `POST /orchestrate/stream` | Streaming `text/event-stream` (SSE) nodo por nodo. |
| `POST /orchestrate/resume` | Reanuda un `thread_id` pausado en `approval_gate` (`approved`, `correction`, `notes`). |
| `POST /catalog-scan` | Atajo especializado para fotos de catálogo/anaquel (`CatalogScanRequest`). |
| `POST /pos-checkout` | Atajo especializado para visión en barra POS (`POSCheckoutRequest`). |
| `POST /receipt-ocr` | Atajo especializado para OCR y clasificación contable (`ReceiptOCRRequest`). |
| `GET /reports/history` | Lista hasta los 20 reportes estratégicos más recientes guardados en `data/reportes/`. |

---

## 4. Scripts Auxiliares (`scripts/`)

- **Exportar dataset SFT para NeMo Customizer (LoRA):**
  ```bash
  uv run python scripts/export_nemo_sft.py
  # Genera data/hitl_feedback/nemo_customizer_train.jsonl
  ```
- **Regenerar diagrama Mermaid del grafo compilado:**
  ```bash
  uv run python scripts/generar_diagrama.py
  # Actualiza ARCHITECTURE_GRAPH.md
  ```
- **Verificar integración real de herramientas con `tiendita-db`:**
  ```bash
  PYTHONPATH=. uv run python scripts/test_tools.py
  ```

---

## 5. Recetas de Extensión (Guía para Agentes de IA)

### Receta A: Agregar una nueva herramienta `@tool`
1. Crea la función decorada con `@tool` y docstring claro (sin enrutamiento por palabras clave) en el módulo temático de `tools/`.
2. Si accede a PostgreSQL, usa `with _get_connection() as conn:` de [tools/db_client.py](../tools/db_client.py), consulta las vistas `v_*` existentes y respeta los enums de `back/db/init/`.
3. Expórtala en [tools/__init__.py](../tools/__init__.py) y agrégala a `ALL_COMMERCE_TOOLS` en [tools/mcp_exporter.py](../tools/mcp_exporter.py).
4. Inclúyela en la lista `tools=[...]` únicamente del agente especialista responsable en `agents/<rol>.py`.

### Receta B: Agregar un nuevo agente especialista
1. Declara su modelo por defecto en [config/agentes.yaml](../config/agentes.yaml) y en `AGENT_ROLES`, `DEFAULT_NVIDIA_BRAINS`, `DEFAULT_ROLE_TEMPERATURES` y `_ROLE_PROFILES` de [config/models.py](../config/models.py).
2. Crea `agents/<nuevo_rol>.py` llamando a `get_llm(role="<nuevo_rol>")` en runtime y filtrando los mensajes `(・_・)? [SUPERVISOR]` del historial.
3. Regístralo en `SupervisorDecision.next_agent`, `SUPERVISOR_SYSTEM_PROMPT` y `valid_specialists` dentro de [agents/supervisor.py](../agents/supervisor.py).
4. Conecta el nodo en `build_graph()` dentro de [agents/graph.py](../agents/graph.py) usando `router_approval` (si realiza escrituras sensibles HITL) o `router_post_specialist` (si es de solo lectura).
5. Ejecuta `uv run python scripts/generar_diagrama.py` para mantener actualizado [ARCHITECTURE_GRAPH.md](../ARCHITECTURE_GRAPH.md).

### Receta C: Agregar una acción diferida con `COMMIT` en HITL
1. En el nodo del agente, asigna `pending_approval` con `requires_human=True`, `status="pending"` y `proposed_data={"op": "<nombre_op>", ...}`.
2. En `_commit_approved_db_action()` de [agents/graph.py](../agents/graph.py), implementa la rama `if op == "<nombre_op>":` ejecutando la transacción real en PostgreSQL dentro de `with _get_connection() as conn:` + `conn.commit()`.
3. Verifica que si `status == "rejected"`, no se modifique ninguna tabla.
