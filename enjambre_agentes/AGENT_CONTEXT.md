# 🤖 AGENT_CONTEXT.md — Especificación Técnica para Agentes de IA

> **Propósito de este documento:** Este archivo está optimizado para consumo directo por agentes autónomos de codificación (LLMs). Define contratos de estado, firmas de funciones, invariantes arquitectónicas y reglas operativas para extender, refactorizar o consumir `enjambre_agentes` sin degradar la coherencia del sistema.

---

## 1. Mapeo Rápido de Componentes (Filesystem)

| Archivo | Rol Técnico | Símbolos Exportados Clave |
|---|---|---|
| [`state.py`](file:///./state.py) | Esquema de datos y memoria LangGraph | `OrchestratorState`, `EvidencePackage`, `DomainToolResult`, `SupervisorDecision` |
| [`models.py`](file:///./models.py) | Fábrica desacoplada de LLMs / Embeddings | `get_llm`, `get_embeddings_model`, `get_available_models` |
| [`tools_bridge.py`](file:///./tools_bridge.py) | Herramientas `@tool` + Protocolo MCP | `RESEARCHER_TOOLS`, `SPECIALIST_TOOLS`, `REPORTER_TOOLS`, `to_mcp_tool_definitions` |
| [`graph.py`](file:///./graph.py) | Ensamblaje StateGraph y ciclo de vida | `build_orchestrator`, `orchestrator_graph`, `run_orchestration`, `run_orchestration_stream` |
| [`__init__.py`](file:///./__init__.py) | Fachada pública del módulo | Re-exporta API unificada |

---

## 2. Contrato de Estado (`OrchestratorState`)

`OrchestratorState` es un `TypedDict(total=False)` de LangGraph con canales de agregación (`Annotated`):

```python
class OrchestratorState(TypedDict, total=False):
    # CANALES DE MENSAJES Y CONVERSACIÓN
    messages: Annotated[List[BaseMessage], add_messages]  # Historial acumulado con add_messages
    query: str                                            # Prompt u objetivo inicial del usuario

    # CONTROL DE ENRUTAMIENTO DEL SUPERVISOR
    next_agent: Literal["investigador", "especialista", "reportador", "FIN"]
    sender: str                                           # Último nodo que mutó el estado
    supervisor_notes: str                                 # Justificación técnica de la delegación
    iteration_count: int                                  # Contador de ciclos (Guardia: iteración > 6 fuerza FIN)

    # PARÁMETROS DEL MODELO
    provider: str                                         # 'NVIDIA' | 'Gemini' | 'Groq' | 'Cohere' | 'Ollama'
    model_name: Optional[str]                             # Ej: 'meta/llama-3.3-70b-instruct'
    temperature: float                                    # Típico: 0.0 (routing) a 0.2 (redacción)
    flow_type: str                                        # 'Híbrido' | 'Solo RAG' | 'Solo Dominio' | 'Completo'
    response_mode: str                                    # 'Resumen' (1 párrafo) | 'Científico' (Dossier completo)

    # RAG DOCUMENTAL (INVESTIGADOR)
    evidence_packages: Annotated[List[Dict[str, Any]], operator.add]
    rag_context: str                                      # Resumen textual recuperado
    rag_sources: Annotated[List[str], operator.add]       # [Package N], URLs, DOIs, arXiv IDs

    # DOMINIO Y CÁLCULOS (ESPECIALISTA)
    domain_results: Dict[str, Any]                        # Salidas de SymPy, patentes, etc.
    domain_context: str                                   # Explicación o deducción matemática

    # CONSOLIDACIÓN (REPORTADOR)
    fused_context: str                                    # Concatenación RAG + Dominio
    final_report: str                                     # Informe en Markdown final entregado al usuario

    # ACCIONES EXTERNAS
    email_recipient: Optional[str]                        # Si presente, activa envío SMTP
    email_subject: Optional[str]
    email_sent: bool
    email_status: Optional[str]

    # DIAGNÓSTICO
    errors: Annotated[List[str], operator.add]
```

---

## 3. Matriz de Mutación por Nodo (Input / Output Contract)

Cada nodo recibe el estado completo y devuelve **únicamente** los deltas que modifica:

```
                          ┌────────────────────────┐
                          │   OrchestratorState    │
                          └───────────┬────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ supervisor_node  │        │investigador_node │        │especialista_node │
├──────────────────┤        ├──────────────────┤        ├──────────────────┤
│ READS:           │        │ READS:           │        │ READS:           │
│ • query          │        │ • query          │        │ • query          │
│ • rag_context    │        │ • messages       │        │ • rag_context    │
│ • domain_context │        │ • provider/model │        │ • messages       │
│ • iteration_count│        │                  │        │ • provider/model │
│                  │        │ WRITES:          │        │                  │
│ WRITES:          │        │ • rag_context    │        │ WRITES:          │
│ • next_agent     │        │ • rag_sources    │        │ • domain_context │
│ • iteration_count│        │ • sender         │        │ • domain_results │
│ • supervisor_note│        │ • messages (AIMsg│        │ • sender         │
└─────────┬────────┘        └─────────┬────────┘        │ • messages (AIMsg│
          │                           │                 └─────────┬────────┘
          │                           │                           │
          │                           ▼                           │
          │                 ┌──────────────────┐                  │
          │                 │ reportador_node  │                  │
          │                 ├──────────────────┤                  │
          │                 │ READS:           │                  │
          │                 │ • query          │                  │
          │                 │ • rag_context    │                  │
          │                 │ • domain_context │                  │
          │                 │ • response_mode  │                  │
          │                 │ • email_recipient│                  │
          │                 │                  │                  │
          │                 │ WRITES:          │                  │
          │                 │ • final_report   │                  │
          │                 │ • fused_context  │                  │
          │                 │ • email_sent     │                  │
          │                 │ • next_agent=FIN │                  │
          │                 │ • messages (AIMsg│                  │
          │                 └─────────┬────────┘                  │
          │                           │                           │
          └───────────────────────────┴───────────────────────────┘
```

---

## 4. Invariantes del Sistema (Reglas NO Negociables para Nuevos Agentes)

Cualquier agente que modifique este código DEBE respetar estas reglas:

### Regla 1: Zero Hardcoded Keys
- **NUNCA** importar `my_keys.py` ni leer `.env` directamente.
- Toda credencial se resuelve mediante `os.getenv("VAR_NAME")`.
- Si una variable falta, proveer fallback gracefully o advertencia clara.

### Regla 2: Filtro Determinista Anti-Alucinaciones (Patrón Nemotron `rag.py`)
- Al generar respuestas RAG documentales, **siempre aplicar** `_drop_ungrounded_sentences(answer, allowed_ids)`.
- Si el LLM menciona un `[Package X]` que no fue parte de `allowed_ids`, se descarta la oración completa.
- Si todas las oraciones son eliminadas, marcar explícitamente `insufficient_evidence: True`.

### Regla 3: Salvaguarda de Ciclos Acotados
- Todo nodo Supervisor debe incrementar `iteration_count`.
- Si `iteration_count > 6`, está **estrictamente prohibido** volver a llamar a `investigador` o `especialista`. Debe enrutar forzosamente a `reportador` o `END`.

### Regla 4: Desacoplamiento de UI
- No importar Streamlit, Gradio, FastHTML ni librerías de interfaz gráfica dentro de `multiagent_template/`.
- La orquestación debe poder ejecutarse en CLI, API REST (FastAPI) o worker en segundo plano (Celery/Temporal).

---

## 5. Catálogo de Herramientas (`tools_bridge.py`)

### Kit de Investigación (`RESEARCHER_TOOLS`)
1. `consultar_nemotron_grounded(pregunta: str, limite: int = 5) -> str`:
   - RAG con razonamiento Nemotron en hardware NVIDIA DGX Spark / NIM.
   - Aplica validación estricta y purga de alucinaciones.
2. `buscar_conocimiento_backend(query: str, limit: int = 5) -> str`:
   - Consulta SQLite FTS5 / BM25 directo contra `packages` y `package_search`.
3. `sintetizar_paquete_evidencia(evidencia_json: str, titulo: str) -> str`:
   - Agregador determinista de respaldo sin dependencias externas.
4. `reconstruir_indice_busqueda() -> str`:
   - Reindexa la tabla virtual FTS5.
5. `buscador_arxiv(query: str) -> str`:
   - Cliente oficial de arXiv API.
6. `buscador_semantic_scholar(query: str) -> str`:
   - Búsqueda REST en el corpus de Semantic Scholar.

### Kit de Especialista (`SPECIALIST_TOOLS`)
1. `optimizador_ecuaciones(ecuacion_str: str) -> str`:
   - `sp.simplify()` de SymPy. Retorna formato estricto `$$...$$`.
2. `diccionario_optica(termino: str) -> str`:
   - Definición ontológica formal vía LLM a temperatura 0.1.
3. `traductor_didactico(concepto_complejo: str) -> str`:
   - Redacción analógica pedagógica para divulgación sin perder rigor.
4. `buscador_patentes(query: str) -> str`:
   - Consulta con foco `site:patents.google.com` vía Tavily Search.
5. `buscador_wikipedia(query: str) -> str`:
   - Resumen de 3 oraciones en Wikipedia en español.
6. `lector_web_profundo(url: str) -> str`:
   - Extractor con `BeautifulSoup` filtrando scripts y etiquetas visuales.

### Kit de Reporte (`REPORTER_TOOLS`)
1. `formateador_citas_ieee(autor: str, titulo: str, anio: str, url: str) -> str`:
   - Produce citas bajo norma IEEE: `Autor, "Título," Año. [Online]. Disponible en: URL`.
2. `enviar_email_reporte(destinatario: str, asunto: str, contenido_markdown: str) -> str`:
   - Despacho SMTP SSL puerto 465 con `EMAIL_SENDER` y `EMAIL_PASSWORD`.

---

## 6. Variables de Entorno de Referencia

| Variable | Descripción | Valor por Defecto si se omite |
|---|---|---|
| `NVIDIA_API_KEY` | Clave API para NVIDIA NIM / NGC | `None` (requerida para NIM) |
| `NVIDIA_BASE_URL` | Endpoint base de NIM o DGX Spark local | `https://integrate.api.nvidia.com/v1` |
| `NVIDIA_REASONING_MODEL` | Modelo Nemotron para RAG | `nvidia/llama-3.1-nemotron-70b-instruct` |
| `DEFAULT_LLM_PROVIDER` | Proveedor primario de inferencia | `NVIDIA` |
| `GEMINI_API_KEY` | Clave de Google AI Studio | Requerida si proveedor = Gemini |
| `GROQ_API_KEY` | Clave de Groq Cloud | Requerida si proveedor = Groq |
| `COHERE_API_KEY` | Clave de Cohere | Requerida si proveedor = Cohere |
| `KNOWLEDGE_DB_PATH` | Ruta absoluta a `knowledge.db` | Busca en rutas relativas de `Research-Knowledge-Backend` |
| `TAVILY_API_KEY` | Clave para búsqueda de patentes en vivo | Opcional (modo simulación si falta) |
| `EMAIL_SENDER` | Dirección Gmail emisora | Opcional (omite envío si falta) |
| `EMAIL_PASSWORD` | App Password de Google | Opcional |

---

## 7. Instrucciones para Nuevos Agentes que Extiendan este Código

1. **Para agregar un nuevo Sub-Agente:**
   - Define su nodo en `graph.py` (ej. `validador_seguridad_node(state)`).
   - Añade el nodo al StateGraph: `builder.add_node("seguridad", validador_seguridad_node)`.
   - Modifica `supervisor_node` para que su prompt incluya la opción `'seguridad'`.
   - Agrega la arista de retorno: `builder.add_edge("seguridad", "supervisor")`.
   - Actualiza `router_supervisor` para contemplar la nueva opción de destino.

2. **Para añadir una nueva Herramienta:**
   - Crea la función en `tools_bridge.py` decorada con `@tool`.
   - Agrégala a la lista correspondiente (`RESEARCHER_TOOLS`, `SPECIALIST_TOOLS` o `REPORTER_TOOLS`).
   - Todos los sub-agentes ReAct la heredarán automáticamente sin modificar `graph.py`.

3. **Para verificar cambios sintácticos y de tipado:**
   ```bash
   python -m py_compile state.py models.py tools_bridge.py graph.py __init__.py
   ```
