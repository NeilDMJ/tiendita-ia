# Plan de Transformación: AgriPoli → Tiendita IA

> [!IMPORTANT]
> **Ecosistema Comercial Multimodal con Visión Artificial, Orquestación Multiagente en LangGraph y Tecnología NVIDIA (NIM / NeMo)**
> Este plan cubre las 5 fases de transformación del repositorio `enjambre_agentes`. Cada tarea incluye el archivo origen de agripoli como referencia, el archivo destino, y la descripción precisa de lo que se debe crear.

---

## Reglas Inquebrantables

| # | Regla | Verificación |
|---|-------|-------------|
| R1 | No eliminar archivos agripoli hasta Fase 5 | Los archivos agrícolas sirven de plantilla durante Fases 2-4 |
| R2 | `Referencias/` intacto | `OptiAgent/` y `Research-Knowledge-Backend/` NO SE TOCAN |
| R3 | Sin ejecución de tests ni contenedores | Solo escritura de código, configuración y dependencias |
| R4 | Razonamiento puro — cero `if "palabra" in query` | Todo enrutamiento vía `with_structured_output` y Tool Calling nativo |

---

## Inventario del Repositorio Actual (Auditado)

### `agents/` — 15 archivos Python + `groups/`

| Archivo | Rol agripoli | Destino Tiendita IA |
|---------|-------------|---------------------|
| [supervisor.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/supervisor.py) | Orquestador con `create_react_agent` + 7 `@tool` | → **`agents/supervisor.py`** (nuevo) |
| [graph.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/graph.py) | `StateGraph` lineal 3 nodos + `MemorySaver` | → **`agents/graph.py`** (nuevo) |
| [state.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/state.py) | `ScrapingState(TypedDict)` 15 campos | → **`schemas/state.py`** |
| [state_v3.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/state_v3.py) | Estados jerárquicos por grupo con loops | Patrón de `iteration_count` y `Annotated[list, add]` |
| [extractor.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/extractor.py) | Recopilador de contexto con 8 tools | → **`agents/control.py`** |
| [investigador.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/investigador.py) | Nodo de búsqueda con `with_structured_output(ConsultasBusqueda)` | → **`agents/investigador.py`** (comercial) |
| [agro_experto.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/agro_experto.py) | Experto agrícola con RAG + tools dinámicos | → **`agents/vendedor.py`** |
| [ecologico.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/ecologico.py) | Diseñador de islas con 2 tools y `create_react_agent` | → **`agents/analista.py`** |
| [fusionador_prompts.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/fusionador_prompts.py) | Fusión de prompts visuales con `get_llm_para_agente` | → **`agents/publicista.py`** |
| [mini_prompt_isla.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/mini_prompt_isla.py) | Generador de prompts hiperrealistas | Patrón reutilizado en `publicista.py` |
| [mini_prompt_cultivo.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/mini_prompt_cultivo.py) | Generador de prompts de parcela | Patrón reutilizado en `publicista.py` |
| [estructurador.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/estructurador.py) | `with_structured_output(Mapa3D)` sin tools | → **`agents/tutor_ui.py`** |
| [sintetizador.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/sintetizador.py) | Nodo que usa `with_structured_output(DatosRegion)` con fallback | Patrón de structured output + fallback reutilizado en todos los agentes |
| [scraper.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/scraper.py) | Nodo de extracción web | Eliminado en Fase 5 |
| [supervisor_v2.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/supervisor_v2.py) | Versión expandida del supervisor | Referencia para complejidad del grafo |
| `graph_v2.py`, `graph_v3.py`, `state_v2.py` | Versiones anteriores | Eliminados en Fase 5 |
| `groups/` (4 archivos) | Sub-grafos por grupo | Eliminados en Fase 5 |

### `schemas/` — 3 archivos

| Archivo | Contenido | Destino |
|---------|-----------|---------|
| [agriculture.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/schemas/agriculture.py) | `Cultivo`, `AgroRegionData` con `Config.json_schema_extra` | Patrón para `schemas/commerce.py` |
| [ecology.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/schemas/ecology.py) | `DatosRegion` completo (270 líneas, 9 sub-modelos) | Patrón para `schemas/reports.py` |
| [threejs_schema.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/schemas/threejs_schema.py) | `Mapa3D` para Three.js | Eliminado en Fase 5 |

### `tools/` — 10 archivos

| Archivo | Función | Destino |
|---------|---------|---------|
| [rag.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/tools/rag.py) | RAG temporal FAISS en memoria (103 líneas) | Patrón para `tools/rag_nemo.py` |
| [rag_engine.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/tools/rag_engine.py) | Motor RAG híbrido (FAISS/Pinecone/Chroma, 373 líneas) | Patrón para `tools/rag_nemo.py` |
| Otros 8 archivos agrícolas | INEGI, GBIF, UNAM, scraper, search, etc. | Eliminados en Fase 5 |

### `config/` — 7 archivos

| Archivo | Función | Destino |
|---------|---------|---------|
| [models.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/models.py) | Fábrica LLM con fallbacks cruzados (613 líneas) | → **`config/models.py`** (extendido con NVIDIA + Ollama dinámico) |
| [agentes.yaml](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/agentes.yaml) | 25 agentes con proveedor/modelo/temperatura | → **`config/agentes.yaml`** (7 agentes comerciales) |
| [keys.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/keys.py) | Carga de API keys desde `.env` | → **`config/keys.py`** (extendido con NVIDIA) |
| [agri_logger.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/agri_logger.py) | Logger expresivo con kaomojis (113 líneas) | → **`config/logger.py`** |
| [silenciador.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/silenciador.py) | Supresión de warnings (52 líneas) | Se conserva tal cual |
| [models_gemini.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/models_gemini.py) | Introspección dinámica Gemini | Se conserva tal cual |
| [models_groq.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/models_groq.py) | Introspección dinámica Groq | Se conserva tal cual |
| [models_cohere.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/models_cohere.py) | Introspección dinámica Cohere | Se conserva tal cual |

---

## Fase 1: Actualización de Dependencias

### Tarea 1.1 — Reescribir `pyproject.toml`

**Archivo:** [pyproject.toml](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/pyproject.toml)

**Acciones:**
1. Cambiar metadatos del proyecto:
   - `name` → `"tiendita-ia"`
   - `description` → `"Ecosistema Comercial Multimodal con Visión Artificial, Orquestación Multiagente en LangGraph y Tecnología NVIDIA"`
2. **Añadir** dependencias nuevas (no eliminar las de LangChain que se reutilizan):

| Categoría | Paquetes a añadir |
|-----------|-------------------|
| NVIDIA & LangChain | `langchain-nvidia-ai-endpoints`, `nemoguardrails`, `langchain-groq`, `langchain-cohere`, `langchain-ollama` |
| Base de datos + RAG vectorial | `psycopg[binary]`, `asyncpg`, `sqlalchemy[asyncio]`, `pgvector` |
| API + HTTP + CLI | `fastapi`, `uvicorn[standard]`, `httpx`, `pydantic>=2.0`, `pyyaml`, `rich` |

3. **Eliminar** dependencias que ya no se necesitan:
   - `INEGIpy`, `torch`, `torchvision`, `transformers`, `huggingface-hub`, `sentence-transformers`, `selenium`, `webdriver-manager`, `playwright`, `sympy`, `arxiv`, `wikipedia`, `unstructured`, `unstructured-client`, `pinecone`, `langchain-pinecone`, `langchain-chroma`, `chromadb`, `langchain-tavily`, `tavily-python`, `faiss-cpu`, `langchain-huggingface`
4. Mantener `requires-python = ">=3.10"` y la sección `[tool.uv]`

### Tarea 1.2 — Reescribir `requirements.txt`

Sincronizar con las mismas dependencias del `pyproject.toml` actualizado, sin el index de PyTorch CPU.

### Tarea 1.3 — Actualizar `.env` y `.env.example`

**Archivo:** [.env](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/.env)

**Añadir variables:**
```env
# NVIDIA
NVIDIA_API_KEY=<tu-nvidia-api-key>
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tiendita

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
```

**Eliminar variables obsoletas:**
- `INEGI_API_TOKEN`, `PINECONE_API_KEY`, `TAVILY_API_KEY`, `TAVILY_MAX_RESULTS`, `HF_TOKEN`, `EMAIL_SENDER`, `EMAIL_PASSWORD`

> [!NOTE]
> Las keys de Gemini, Groq, Cohere, LangSmith y Ollama se mantienen.

---

## Fase 2: Mapeo y Adaptación Arquitectónica

### Tarea 2.1 — `schemas/state.py` — OrchestratorState

**Origen:** [agents/state.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/state.py) (50 líneas, `ScrapingState`) + [agents/state_v3.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/state_v3.py) (164 líneas, `EstadoMaestroV3`)

**Destino:** `schemas/state.py`

**Patrones a reutilizar:**
- `Annotated[list, add]` para campos acumulativos (de `state.py` L26)
- `Annotated[list, add_messages]` para historial de mensajes (de `state_v3.py` L142)
- Contadores con `total=False` para campos opcionales (de `state_v3.py` L19)

**Campos del nuevo `OrchestratorState(TypedDict)`:**

```python
class OrchestratorState(TypedDict, total=False):
    messages: Annotated[list, add_messages]  # Historial LangGraph
    event_source: str                         # "chat" | "catalog-scan" | "pos-checkout" | "receipt-ocr" | "cron"
    vision_payload: Optional[dict]            # {image_b64, mime_type, endpoint}
    ui_state: Optional[dict]                  # {screen, step, payment_method, error_code}
    db_evidence: Optional[str]                # Resultados de consultas SQL/RAG
    few_shot_examples: Optional[list[dict]]   # Ejemplos dinámicos para el agente activo
    strategic_report: Optional[dict]          # Reporte del Investigador (9 secciones)
    promo_assets: Optional[dict]             # Copy + video_prompt del Publicista
    pending_approval: Optional[dict]          # ApprovalPayload para HITL
    next_agent: Optional[str]                 # Agente destino (decisión del Supervisor)
    iteration_count: int                      # Contador de iteraciones (max 6)
```

### Tarea 2.2 — `schemas/vision.py` — Contratos de Visión

**Destino:** `schemas/vision.py`

```python
class CatalogScanRequest(BaseModel):    # /catalog-scan
class CatalogScanResult(BaseModel):     # Productos detectados con SKU, precio, lote
class POSCheckoutRequest(BaseModel):    # /pos-checkout
class POSCheckoutResult(BaseModel):     # Items del carrito con cantidades
class ReceiptOCRRequest(BaseModel):     # /receipt-ocr
class ReceiptOCRResult(BaseModel):      # Clasificación: inversion_inventario | gasto_operativo
```

### Tarea 2.3 — `schemas/ui_copilot.py` — Contrato del Tutor UI

**Origen:** [agents/estructurador.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/estructurador.py) (patrón `with_structured_output`)

**Destino:** `schemas/ui_copilot.py`

```python
class UIState(BaseModel):
    screen: str         # "payment_method_select" | "nip_entry" | "qr_scan" | ...
    step: int
    payment_method: Optional[str]
    error_code: Optional[str]

class TutorResponse(BaseModel):
    action_sentence_1: str = Field(max_length=120)
    action_sentence_2: Optional[str] = Field(max_length=120, default=None)
    # Validador: máximo 2 oraciones accionables
```

### Tarea 2.4 — `schemas/commerce.py` — Modelos Comerciales

**Origen:** [schemas/agriculture.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/schemas/agriculture.py) (patrón `Cultivo` → `Producto`, `Config.json_schema_extra`)

**Destino:** `schemas/commerce.py`

```python
class Producto(BaseModel):         # SKU, nombre, precio, unidad, lote, fecha_caducidad
class Lote(BaseModel)              # lote_id, producto_sku, cantidad, fecha_ingreso, fecha_caducidad
class CartItem(BaseModel)          # producto, cantidad, precio_unitario, subtotal
class CarritoPOS(BaseModel)        # items: list[CartItem], total, metodo_pago
class Venta(BaseModel)             # venta_id, carrito, timestamp, vendedor
class MovimientoFinanciero(BaseModel)  # tipo: inversion_inventario | gasto_operativo
class ApprovalPayload(BaseModel)   # action, data, reason, requires_human: bool
```

### Tarea 2.5 — `schemas/reports.py` — Reportes y Activos

**Origen:** [schemas/ecology.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/schemas/ecology.py) (patrón `DatosRegion` con sub-modelos Pydantic)

**Destino:** `schemas/reports.py`

```python
class StrategicReport(BaseModel):
    identificacion_sector: str
    mercado_tendencias: str
    clientes: str
    problemas: str
    soluciones: str
    hipotesis: str
    objetivos: str
    impacto: str
    hallazgos: str

class VideoPrompt(BaseModel):
    aspect_ratio: Literal["9:16"] = "9:16"
    duration_seconds: int = 5
    prompt_text: str
    trigger: str  # "caducidad" | "sobrestock"

class PromoAssets(BaseModel):
    copy_text: str
    cta: str  # Call to Action
    video_prompt: Optional[VideoPrompt]
```

### Tarea 2.6 — `schemas/__init__.py`

Exportar todos los schemas públicos.

---

### Tarea 2.7 — `agents/supervisor.py` — Supervisor Comercial

**Origen:** [agents/supervisor.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/supervisor.py) (203 líneas)

**Patrones a reutilizar:**
- `create_react_agent(llm, tools, prompt)` de L201
- System prompt extenso con reglas de enrutamiento (L176-L198)
- Lazy loading de sub-agentes (L21-L29)

**Cambios clave:**
1. **Enrutamiento por razonamiento puro**: El supervisor recibe `event_source` y `messages` y usa `with_structured_output` para decidir `next_agent` entre los 6 especialistas. **Prohibido**: `if "pos" in query`.
2. **Encadenamiento compuesto**: Puede invocar secuencialmente (ej: `control → vendedor → analista`).
3. **Límite**: `iteration_count <= 6`, y si se alcanza, retorna con resumen parcial.
4. Los `@tool` del supervisor delegan a los agentes especialistas (patrón de `delegar_investigador` y `consultar_agroexperto` de L33-L62).

```python
# Esquema de decisión (structured output)
class SupervisorDecision(BaseModel):
    next_agent: Literal["control", "vendedor", "analista", "investigador", "publicista", "tutor_ui", "FINISH"]
    reasoning: str
    compound_chain: Optional[list[str]] = None  # Encadenamiento secuencial
```

### Tarea 2.8 — `agents/graph.py` — Grafo LangGraph con HITL

**Origen:** [agents/graph.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/graph.py) (147 líneas)

**Patrones a reutilizar:**
- `StateGraph(State)` + `add_node` + `add_edge` (L32-L44)
- `MemorySaver()` como checkpointer (L47)
- Funciones `run_*` con `initial_state` y `config = {"configurable": {"thread_id": ...}}` (L104-L144)

**Cambios clave:**
1. `StateGraph(OrchestratorState)` en lugar de `ScrapingState`
2. Nodo `supervisor` como hub central con condicional `should_continue` (en vez de flujo lineal)
3. **Checkpointer**: `MemorySaver()` (y luego `AsyncPostgresSaver` para producción)
4. **Interrupciones HITL**: `interrupt_before=["approval_gate"]` donde `approval_gate` verifica `pending_approval`
5. Funciones públicas:
   - `build_graph() -> CompiledStateGraph`
   - `run_orchestrator(input, thread_id, provider) -> dict`
   - `run_orchestrator_stream(input, thread_id, provider) -> AsyncGenerator`
   - `resume_orchestrator(thread_id, approval) -> dict`

```mermaid
flowchart TD
    START["__start__"] --> supervisor
    supervisor -->|"next_agent"| control["control"]
    supervisor -->|"next_agent"| vendedor["vendedor"]
    supervisor -->|"next_agent"| analista["analista"]
    supervisor -->|"next_agent"| investigador["investigador"]
    supervisor -->|"next_agent"| publicista["publicista"]
    supervisor -->|"next_agent"| tutor_ui["tutor_ui"]
    supervisor -->|"FINISH"| END["__end__"]
    control --> approval_gate{"approval_gate\n(HITL interrupt)"}
    vendedor --> approval_gate
    analista --> supervisor
    investigador --> supervisor
    publicista --> supervisor
    tutor_ui --> supervisor
    approval_gate -->|approved| supervisor
    approval_gate -->|rejected| supervisor
```

### Tarea 2.9 — `agents/control.py` — Controlador de Inventario + Visión

**Origen:** [agents/extractor.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/extractor.py) (55 líneas)

**Patrones a reutilizar:**
- `create_react_agent(llm, tools, prompt)` de L54
- System prompt como string con misión clara (L44-L51)
- Lista de tools inyectada como argumento (L33-L41)

**Responsabilidades nuevas:**
- `/catalog-scan` → llama `tools/vision_nim.py` para detectar productos en foto
- `/receipt-ocr` → llama `tools/vision_nim.py` + clasifica en `inversion_inventario` vs `gasto_operativo`
- Alertas de caducidad y stock crítico → consulta `tools/db_client.py`
- **Sin condicionales por palabra clave**: Tool Calling nativo decide qué herramienta usar

### Tarea 2.10 — `agents/vendedor.py` — Vendedor POS + Upselling

**Origen:** [agents/agro_experto.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/agro_experto.py) (219 líneas) + [agents/ecologico.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/ecologico.py) (55 líneas)

**Patrones a reutilizar:**
- `create_react_agent` con tools internos definidos como `@tool` dentro de la función factory (agro_experto L64-L80)
- RAG consultado dentro de un `@tool` (agro_experto L65-L71)
- System prompt con reglas de kaomojis y metodología (ecologico L37-L51)

**Responsabilidades nuevas:**
- Carrito POS por cámara (recibe `vision_payload` de `/pos-checkout`)
- Cotización contra BD (`tools/pos_tools.py`)
- Upselling inteligente basado en historial y margen

### Tarea 2.11 — `agents/analista.py` — Analista Financiero (Solo Lectura)

**Origen:** [agents/ecologico.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/ecologico.py)

**Responsabilidades nuevas:**
- Flujo de caja, márgenes y rotación por SKU
- Solo lectura: NO puede modificar inventario ni aprobar operaciones
- Usa `tools/analytics_tools.py`

### Tarea 2.12 — `agents/investigador.py` — Investigador Comercial

**Origen:** [agents/investigador.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/investigador.py) (236 líneas)

**Patrones a reutilizar:**
- `with_structured_output(ConsultasBusqueda)` para generar queries dinámicas (L131-L133)
- Schema Pydantic `ConsultasBusqueda` para las queries (L26-L46)
- Función de nodo `investigador_node(state) -> dict` (L107-L236)
- Fallback con queries por defecto si structured output falla (L136-L159)

**Cambios clave:**
- El schema de salida ahora es `StrategicReport` con las **9 secciones obligatorias**
- Usa herramientas de búsqueda web genéricas (no CONABIO/INEGI)
- El `with_structured_output(StrategicReport)` fuerza el formato

### Tarea 2.13 — `agents/publicista.py` — Generador de Contenido Comercial

**Origen:** [agents/fusionador_prompts.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/fusionador_prompts.py) (326 líneas) + mini_prompt_*.py

**Patrones a reutilizar:**
- Orquestación de sub-generadores (fusionador L28-L48)
- Uso de `get_llm_para_agente(nombre)` para modelos por rol (L56)
- Generación de prompts extensos con LLM (L58-L120)
- Guardado en disco de resultados (L31, `guardar_en_disco`)

**Responsabilidades nuevas:**
- Generación de copys comerciales y CTAs
- `video_prompt` vertical 9:16 de 5 segundos ante alertas de caducidad/sobrestock
- Usa `tools/media_tools.py`

### Tarea 2.14 — `agents/tutor_ui.py` — Copiloto de Pagos Digitales

**Origen:** [agents/estructurador.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/estructurador.py) (50 líneas) + [agents/sintetizador.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/agents/sintetizador.py) (197 líneas)

**Patrones a reutilizar:**
- `with_structured_output(Schema)` sin tools — solo razonamiento (estructurador L19)
- `ChatPromptTemplate.from_messages([(system, ...), (human, ...)])` (estructurador L29-L31)
- Chain `prompt | llm_structured` (estructurador L34)
- Fallback de `with_structured_output` → texto + parsing manual (sintetizador L141-L163)

**Responsabilidades nuevas:**
- Lee `ui_state` (pantalla actual, paso, método de pago, código de error)
- Responde con `TutorResponse`: **máximo 2 oraciones accionables**
- NO tiene tools — solo razonamiento puro sobre el estado de la UI

### Tarea 2.15 — `agents/__init__.py`

Actualizar exportaciones para los 7 agentes nuevos.

---

### Tarea 2.16 — `tools/rag_nemo.py` — Pipeline NeMo Retriever

**Origen:** [tools/rag.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/tools/rag.py) (103 líneas) + [tools/rag_engine.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/tools/rag_engine.py) (373 líneas)

**Patrones a reutilizar:**
- `vectorizar_temporal()` con FAISS (rag.py L27-L91)
- `build_vectorstore()` con múltiples backends (rag_engine.py L65-L98)
- `_chunk_documents()` con `RecursiveCharacterTextSplitter` (rag_engine.py L51-L62)
- Caché de retrievers `_retriever_cache` (rag_engine.py L28)
- Fallback de embeddings si cuota excedida (rag_engine.py L128-L136)

**Cambios clave:**
- Embeddings: `nvidia/nv-embedqa-e5-v5` vía `langchain-nvidia-ai-endpoints`
- Vectorstore: `pgvector` en PostgreSQL (en vez de FAISS/Pinecone/Chroma)
- Reranking: `nvidia/nv-rerankqa-mistral-4b-v3`
- Pipeline: `embed → pgvector search → rerank → return top_k`

### Tarea 2.17 — `tools/db_client.py` — Pool Asíncrono PostgreSQL

**Destino:** `tools/db_client.py`

```python
# Pool con SQLAlchemy async
async def get_db_pool() -> AsyncEngine
async def execute_query(query: str, params: dict) -> list[dict]

@tool
def query_inventory(sku: Optional[str], category: Optional[str]) -> str
@tool
def query_sales(date_from: str, date_to: str, sku: Optional[str]) -> str
@tool
def query_expiring_soon(days_ahead: int = 7) -> str
```

### Tarea 2.18 — `tools/vision_nim.py` — Cliente Multimodal NIM Vision

**Destino:** `tools/vision_nim.py`

```python
@tool
def analyze_catalog_photo(image_b64: str) -> str
    """Envía imagen a NIM Vision para detectar productos en anaquel"""

@tool
def analyze_receipt(image_b64: str) -> str
    """Envía imagen de ticket a NIM Vision para OCR y clasificación"""

@tool
def analyze_pos_items(image_b64: str) -> str
    """Envía foto del mostrador a NIM Vision para identificar items de venta"""
```

### Tarea 2.19 — `tools/few_shot_retriever.py`

**Destino:** `tools/few_shot_retriever.py`

```python
@tool
def retrieve_few_shots(agent_role: str, query: str, k: int = 3) -> str
    """Recupera ejemplos few-shot dinámicos del pgvector según el rol del agente activo"""

def record_hitl_feedback(example: dict, approved: bool, correction: Optional[str]) -> None
    """Registra feedback HITL para NeMo Customizer (SFT futuro)"""
```

### Tarea 2.20 — `tools/guards.py` — Guardrails de Grounding

**Destino:** `tools/guards.py`

```python
def enforce_db_grounding(response: str, db_evidence: str) -> str
    """Verifica que la respuesta del LLM esté fundamentada en evidencia de BD.
    Rechaza alucinaciones si no hay respaldo en db_evidence."""
```

### Tarea 2.21 — `tools/mcp_exporter.py`

**Destino:** `tools/mcp_exporter.py`

Expone las herramientas como servidor MCP para clientes externos.

### Tarea 2.22 — `tools/inventory_tools.py` — Herramientas de Inventario

**Destino:** `tools/inventory_tools.py`

```python
@tool
def register_product(name: str, sku: str, price: float, ...) -> str
@tool
def update_stock(sku: str, quantity: int, movement_type: str) -> str
@tool
def check_expiry_alerts(days_ahead: int = 7) -> str
@tool
def get_low_stock_alerts(threshold: int = 5) -> str
```

### Tarea 2.23 — `tools/pos_tools.py` — Herramientas POS

**Destino:** `tools/pos_tools.py`

```python
@tool
def create_cart() -> str
@tool
def add_to_cart(cart_id: str, sku: str, quantity: int) -> str
@tool
def checkout_cart(cart_id: str, payment_method: str) -> str
@tool
def suggest_upsell(cart_id: str) -> str
```

### Tarea 2.24 — `tools/analytics_tools.py` — Herramientas Analíticas

**Destino:** `tools/analytics_tools.py`

```python
@tool
def get_cash_flow(date_from: str, date_to: str) -> str
@tool
def get_margins_by_sku(sku: Optional[str] = None) -> str
@tool
def get_rotation_by_sku(days: int = 30) -> str
@tool
def get_sales_summary(period: str = "week") -> str
```

### Tarea 2.25 — `tools/media_tools.py` — Herramientas de Medios

**Destino:** `tools/media_tools.py`

```python
@tool
def generate_promo_copy(product_name: str, trigger: str) -> str
@tool
def generate_video_prompt(product_name: str, trigger: str) -> str
    """Genera prompt de video vertical 9:16 de 5 segundos"""
@tool
def generate_cta(product_name: str, discount_pct: float) -> str
```

### Tarea 2.26 — `tools/__init__.py`

Actualizar exportaciones.

---

## Fase 3: Configuración y Descubrimiento Dinámico

### Tarea 3.1 — Conservar sin cambios

Archivos que se mantienen tal cual:
- `config/models_gemini.py`
- `config/models_groq.py`
- `config/models_cohere.py`
- `config/silenciador.py`

### Tarea 3.2 — `config/keys.py` — Extender con NVIDIA

**Origen:** [config/keys.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/keys.py) (49 líneas)

**Cambios:**
```python
# Añadir:
NVIDIA_API_KEY: str | None = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
DATABASE_URL: str | None = os.getenv("DATABASE_URL")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
```

Actualizar `validate_keys` y su `key_map` con las nuevas variables.

### Tarea 3.3 — `config/logger.py` — Renombrar agri_logger

**Origen:** [config/agri_logger.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/agri_logger.py) (113 líneas)

**Cambios:**
- Copiar íntegro como `config/logger.py`
- Cambiar docstring de "AgriPoli" a "Tiendita IA"
- Actualizar kaomojis de emociones si se desea agregar estados comerciales (ej. `"VENTA"`, `"ALERTA_STOCK"`)

### Tarea 3.4 — `config/models_nvidia.py` — Introspección NIM

**Destino:** `config/models_nvidia.py`

```python
FALLBACK_MODELS_NVIDIA = [
    "meta/llama-3.1-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "mistralai/mistral-large-2-instruct",
]

def obtener_modelos_nvidia() -> list[str]:
    """GET {NVIDIA_BASE_URL}/models — compatible con NIM Cloud y DGX Spark local"""
```

### Tarea 3.5 — `config/models_ollama.py` — Introspección Ollama Dinámica

**Destino:** `config/models_ollama.py`

```python
FALLBACK_MODELS_OLLAMA = ["llama3.2", "mistral", "gemma2", "deepseek-r1"]

def obtener_modelos_ollama() -> list[str]:
    """GET {OLLAMA_BASE_URL}/api/tags — descubre modelos instalados en vivo"""
```

### Tarea 3.6 — `config/models.py` — Extender fábrica LLM

**Origen:** [config/models.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/models.py) (613 líneas)

**Cambios:**
1. Añadir proveedor `"NVIDIA"` en `get_llm()`:
   ```python
   elif provider == "NVIDIA":
       from langchain_nvidia_ai_endpoints import ChatNVIDIA
       primary = ChatNVIDIA(model=model_name or ..., nvidia_api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)
   ```
2. Añadir `"NVIDIA"` en `_crear_fallbacks_cruzados()` y en `PROVIDERS`
3. Reescribir `obtener_modelos_disponibles()` para aceptar `provider="NVIDIA"` → delega a `config/models_nvidia.py`
4. Reescribir `obtener_modelos_disponibles()` para `provider="Ollama"` → delega a `config/models_ollama.py` (en vez de usar `import ollama` directo)
5. **Nueva función:**
   ```python
   def listar_modelos_disponibles(provider: Optional[str] = None) -> dict[str, list[str]]:
       """Devuelve {proveedor: [modelos]} en vivo para todos los proveedores configurados"""
   ```
6. Actualizar `get_llm()` para aceptar `role: Optional[str] = None` (futuro: adaptadores LoRA)
7. Actualizar `_MODELOS_POR_AGENTE_DEFAULT` para los 7 agentes comerciales
8. Cambiar docstrings de "AgriPoli" a "Tiendita IA"

### Tarea 3.7 — `config/agentes.yaml` — Reescribir para Tiendita IA

**Origen:** [config/agentes.yaml](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/config/agentes.yaml) (133 líneas, 25 agentes)

**Destino:** Mismo archivo, contenido nuevo:

```yaml
modelos:
  supervisor:
    proveedor: Gemini
    modelo: gemini-2.5-flash
    temperatura: 0.1
  control:
    proveedor: NVIDIA
    modelo: meta/llama-3.1-70b-instruct
    temperatura: 0.1
  vendedor:
    proveedor: Gemini
    modelo: gemini-2.5-flash
    temperatura: 0.2
  analista:
    proveedor: Gemini
    modelo: gemini-2.5-flash
    temperatura: 0.1
  investigador:
    proveedor: Groq
    modelo: llama-3.3-70b-versatile
    temperatura: 0.3
  publicista:
    proveedor: Gemini
    modelo: gemini-2.5-flash
    temperatura: 0.5
  tutor_ui:
    proveedor: Gemini
    modelo: gemini-flash-lite-latest
    temperatura: 0.0
configuracion:
  max_iteraciones_supervisor: 6
  confirmacion_hitl: manual
  flow_type: Orquestado
  guardar_feedback_local: true
```

### Tarea 3.8 — `config/guardrails/` — NeMo Guardrails

**Destino:** `config/guardrails/config.yml` y `config/guardrails/rails.co`

```yaml
# config.yml
models:
  - type: main
    engine: nvidia-ai-endpoints
    model: meta/llama-3.1-70b-instruct

rails:
  input:
    flows:
      - check grounding
  output:
    flows:
      - enforce db grounding
      - check response length
```

```colang
# rails.co
define flow check grounding
  """Verifica que la respuesta esté respaldada por evidencia de BD"""

define flow enforce db grounding
  """Rechaza respuestas que no tengan respaldo en db_evidence"""

define flow check response length
  """Para tutor_ui: máximo 2 oraciones"""
```

### Tarea 3.9 — `config/__init__.py`

Actualizar exportaciones.

---

## Fase 4: Puntos de Entrada y CLI

### Tarea 4.1 — `api.py` — API REST con FastAPI

**Destino:** `api.py` (raíz del proyecto)

```python
app = FastAPI(title="Tiendita IA API")

@app.get("/models")
@app.post("/orchestrate")
@app.post("/orchestrate/stream")  # SSE con EventSourceResponse
@app.post("/orchestrate/resume")  # HITL: recibe aprobación/rechazo
@app.get("/health")
```

### Tarea 4.2 — `scripts/cli_tester.py` — CLI Interactivo

**Destino:** `scripts/cli_tester.py`

Funcionalidades:
- `/modelo` → selector interactivo conectado a `listar_modelos_disponibles()`
- Confirmación HITL: `[s/n/e]` (sí / no / editar)
- Comandos: `/pos`, `/ticket`, `/pago`, `/cron`, `/estado`
- Usa `rich` para formato terminal

### Tarea 4.3 — `scripts/export_nemo_sft.py`

**Destino:** `scripts/export_nemo_sft.py`

Exporta el feedback HITL acumulado en formato compatible con NeMo Customizer para SFT.

### Tarea 4.4 — `scripts/generar_diagrama.py`

**Destino:** `scripts/generar_diagrama.py`

Genera diagramas Mermaid del grafo LangGraph actual.

### Tarea 4.5 — `main.py` — Actualizar Entry Point

**Origen:** [main.py](file:///home/m4r10/Documents/tiendita-ia/enjambre_agentes/main.py) (170 líneas)

**Cambios:**
- Banner de "Tiendita IA" en vez de "AgriPoli"
- Invocar `run_orchestrator()` en vez de `run_agripoli()`
- Argparse con `--provider`, `--model`, `--event-source`, `--thread-id`
- Integrar con `listar_modelos_disponibles()` para `--list-models`

### Tarea 4.6 — `AGENTS.md` y `README.md`

Documentar la nueva arquitectura, los 7 agentes, flujo HITL, y stack tecnológico.

---

## Fase 5: Limpieza Final del Dominio Agrícola

> [!CAUTION]
> **Ejecutar SOLO después de que todos los archivos nuevos de las Fases 2-4 estén creados y los imports verificados.**

### Tarea 5.1 — Verificación previa de imports

Ejecutar un script que haga `import` de cada módulo nuevo para verificar que no hay errores de sintaxis ni imports rotos:

```python
# Verificar que todos los módulos nuevos importan correctamente
import schemas.state
import schemas.vision
import schemas.ui_copilot
import schemas.commerce
import schemas.reports
import agents.supervisor
import agents.graph
import agents.control
import agents.vendedor
import agents.analista
import agents.investigador
import agents.publicista
import agents.tutor_ui
import tools.rag_nemo
import tools.db_client
import tools.vision_nim
# ... etc.
```

### Tarea 5.2 — Eliminar archivos agrícolas

**Archivos a eliminar en `agents/`:**
- `agro_experto.py`, `ecologico.py`, `estructurador.py`, `extractor.py`
- `fusionador_prompts.py`, `mini_prompt_isla.py`, `mini_prompt_cultivo.py`
- `graph_v2.py`, `graph_v3.py`, `state.py`, `state_v2.py`, `state_v3.py`
- `supervisor_v2.py`, `scraper.py`, `sintetizador.py`
- `groups/` (directorio completo)

**Archivos a eliminar en `schemas/`:**
- `agriculture.py`, `ecology.py`, `threejs_schema.py`

**Archivos a eliminar en `tools/`:**
- `agro_data.py`, `gbif_client.py`, `inegi_client.py`, `unam_data.py`
- `rag.py`, `rag_engine.py` (reemplazados por `rag_nemo.py`)
- `catalogo_biodiversidad.py`, `descargador_masivo.py`, `gestor_regiones.py`
- `herramientas_cientificas.py`, `scraper.py`, `search.py`

**Archivos a eliminar en `config/`:**
- `agri_logger.py` (reemplazado por `logger.py`)

**Archivos a eliminar en `scripts/`:**
- `agente_rescate.py`, `consulta_agricola.py`, `descarga_agricola.py`
- `descargar_catalogo.py`, `descarga_unam.py`
- `main_supervisor.py`, `main_supervisor_v2.py`
- `probar_generacion_prompts.py`, `render_playwright.py`
- `generar_diagrama.py` (versión vieja), `generar_diagrama_v3.py`

### Tarea 5.3 — Limpiar `__pycache__/`

```bash
find enjambre_agentes -type d -name __pycache__ -exec rm -rf {} +
```

---

## Resumen de Archivos Resultantes

```
enjambre_agentes/
├── agents/
│   ├── __init__.py
│   ├── supervisor.py        ← NUEVO (Fase 2.7)
│   ├── graph.py             ← NUEVO (Fase 2.8)
│   ├── control.py           ← NUEVO (Fase 2.9)
│   ├── vendedor.py          ← NUEVO (Fase 2.10)
│   ├── analista.py          ← NUEVO (Fase 2.11)
│   ├── investigador.py      ← NUEVO (Fase 2.12)
│   ├── publicista.py        ← NUEVO (Fase 2.13)
│   └── tutor_ui.py          ← NUEVO (Fase 2.14)
├── schemas/
│   ├── __init__.py           ← NUEVO (Fase 2.6)
│   ├── state.py             ← NUEVO (Fase 2.1)
│   ├── vision.py            ← NUEVO (Fase 2.2)
│   ├── ui_copilot.py        ← NUEVO (Fase 2.3)
│   ├── commerce.py          ← NUEVO (Fase 2.4)
│   └── reports.py           ← NUEVO (Fase 2.5)
├── tools/
│   ├── __init__.py           ← NUEVO (Fase 2.26)
│   ├── rag_nemo.py          ← NUEVO (Fase 2.16)
│   ├── db_client.py         ← NUEVO (Fase 2.17)
│   ├── vision_nim.py        ← NUEVO (Fase 2.18)
│   ├── few_shot_retriever.py ← NUEVO (Fase 2.19)
│   ├── guards.py            ← NUEVO (Fase 2.20)
│   ├── mcp_exporter.py      ← NUEVO (Fase 2.21)
│   ├── inventory_tools.py   ← NUEVO (Fase 2.22)
│   ├── pos_tools.py         ← NUEVO (Fase 2.23)
│   ├── analytics_tools.py   ← NUEVO (Fase 2.24)
│   └── media_tools.py       ← NUEVO (Fase 2.25)
├── config/
│   ├── __init__.py           ← ACTUALIZADO (Fase 3.9)
│   ├── keys.py              ← EXTENDIDO (Fase 3.2)
│   ├── logger.py            ← RENOMBRADO (Fase 3.3)
│   ├── silenciador.py       ← SIN CAMBIOS
│   ├── models.py            ← EXTENDIDO (Fase 3.6)
│   ├── models_gemini.py     ← SIN CAMBIOS
│   ├── models_groq.py       ← SIN CAMBIOS
│   ├── models_cohere.py     ← SIN CAMBIOS
│   ├── models_nvidia.py     ← NUEVO (Fase 3.4)
│   ├── models_ollama.py     ← NUEVO (Fase 3.5)
│   ├── agentes.yaml         ← REESCRITO (Fase 3.7)
│   └── guardrails/
│       ├── config.yml       ← NUEVO (Fase 3.8)
│       └── rails.co         ← NUEVO (Fase 3.8)
├── scripts/
│   ├── cli_tester.py        ← NUEVO (Fase 4.2)
│   ├── export_nemo_sft.py   ← NUEVO (Fase 4.3)
│   └── generar_diagrama.py  ← NUEVO (Fase 4.4)
├── Referencias/              ← INTACTO (R2)
│   ├── OptiAgent/
│   └── Research-Knowledge-Backend/
├── api.py                    ← NUEVO (Fase 4.1)
├── main.py                   ← ACTUALIZADO (Fase 4.5)
├── AGENTS.md                 ← NUEVO (Fase 4.6)
├── README.md                 ← ACTUALIZADO (Fase 4.6)
├── pyproject.toml            ← ACTUALIZADO (Fase 1.1)
├── requirements.txt          ← ACTUALIZADO (Fase 1.2)
└── .env                      ← ACTUALIZADO (Fase 1.3)
```

---

## Orden de Ejecución Recomendado

```mermaid
flowchart LR
    F1["Fase 1\nDependencias"] --> F2S["Fase 2\nSchemas"]
    F2S --> F2T["Fase 2\nTools"]
    F2T --> F2A["Fase 2\nAgents"]
    F2A --> F3["Fase 3\nConfig"]
    F3 --> F4["Fase 4\nAPI + CLI + main"]
    F4 --> F5["Fase 5\nLimpieza"]
```

Dentro de cada sub-fase, los archivos son independientes y pueden crearse en paralelo:

| Sub-fase | Archivos paralelos |
|----------|-------------------|
| **2 Schemas** | `state.py`, `vision.py`, `ui_copilot.py`, `commerce.py`, `reports.py` (5 en paralelo) |
| **2 Tools** | `rag_nemo.py`, `db_client.py`, `vision_nim.py`, `few_shot_retriever.py`, `guards.py`, `mcp_exporter.py`, `inventory_tools.py`, `pos_tools.py`, `analytics_tools.py`, `media_tools.py` (10 en paralelo) |
| **2 Agents** | `control.py`, `vendedor.py`, `analista.py`, `investigador.py`, `publicista.py`, `tutor_ui.py` (6 en paralelo, pero dependen de schemas+tools) → luego `supervisor.py` → luego `graph.py` |
| **3 Config** | `keys.py`, `logger.py`, `models_nvidia.py`, `models_ollama.py` (4 en paralelo) → luego `models.py` → luego `agentes.yaml` + `guardrails/` |
| **4 Entrada** | `api.py`, `cli_tester.py`, `export_nemo_sft.py`, `generar_diagrama.py` (4 en paralelo) → luego `main.py` → luego `AGENTS.md` + `README.md` |

---

> [!TIP]
> **Total de archivos nuevos/modificados: 38** (26 nuevos + 7 modificados + 5 conservados sin cambios)
> **Total de archivos a eliminar en Fase 5: ~30** archivos agrícolas + `__pycache__/`
