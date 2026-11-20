# 05 · Stack de Tecnología NVIDIA (NIM / NeMo) y Resiliencia Multicapa

Este documento explica **exactamente dónde y cómo se aplica cada componente de NVIDIA** en el repositorio, cómo se administran los cerebros por agente en runtime y cómo opera el rescate automático entre proveedores.

---

## 1. Mapa de Tecnologías NVIDIA Aplicadas

| Pilar NVIDIA | Modelos / Estándares | Dónde vive en el código | Rol en Tiendita IA |
|---|---|---|---|
| **NVIDIA NIM — LLMs de Razonamiento** | `nvidia/nemotron-3-super-120b-a12b` | [config/models.py](../config/models.py), [config/agentes.yaml](../config/agentes.yaml), [config/models_nvidia.py](../config/models_nvidia.py) | Cerebro por defecto de `supervisor`, `analista` e `investigador` (enrutamiento estructurado, finanzas y reportes de 9 secciones). |
| **NVIDIA NIM — LLMs de Baja Latencia (LoRA-ready)** | `nvidia/llama-3.1-nemotron-nano-8b-v1` | [config/models.py](../config/models.py), [config/agentes.yaml](../config/agentes.yaml) | Cerebro por defecto de `control`, `vendedor`, `publicista` y `tutor_ui` (operación ágil en caja y pantalla). |
| **NVIDIA NIM — Vision (VL Multimodal)** | `nvidia/nemotron-3.5-super-vl-120b-a12b`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, `google/gemma-3-12b-it` | [tools/vision_nim.py](../tools/vision_nim.py) | Análisis real de fotos desde disco/API en `/catalog-scan`, `/pos-checkout`, `/receipt-ocr` y `/imagen`. |
| **NVIDIA NeMo Retriever** | `nvidia/nemotron-3.5-embed-8b` (vectores precalculados en `embeddings.npz`) + `nvidia/nv-rerankqa-mistral-4b-v3` | [tools/rag_nemo.py](../tools/rag_nemo.py), `data/Embeddings/datos/embeddings.npz` | Vectores 4096-dim precalculados para el corpus Banxico + reranking semántico sobre candidatos recuperados en FAISS. |
| **NVIDIA NeMo Guardrails (Colang)** | Reglas Colang + guardias programáticas | [config/guardrails/config.yml](../config/guardrails/config.yml), [config/guardrails/rails.co](../config/guardrails/rails.co), [tools/guards.py](../tools/guards.py) | Bloqueo de *prompt injections*, enmascaramiento de `costo_unitario` en mostrador y límite estricto de 2 oraciones en `tutor_ui`. |
| **NVIDIA NeMo Customizer (SFT / LoRA)** | Pipeline de exportación JSONL formato chat SFT | [tools/few_shot_retriever.py](../tools/few_shot_retriever.py), [scripts/export_nemo_sft.py](../scripts/export_nemo_sft.py) | Convierte decisiones aprobadas/corregidas por humanos en HITL (`nemo_sft_dataset.jsonl`) a `nemo_customizer_train.jsonl` para entrenar los adaptadores LoRA declarados en `agentes.yaml` (`control_inventory_v1`, `pos_upsell_v1`, `promo_copy_v1`, `tutor_ui_concise_v1`). |

---

## 2. Introspección en Vivo y Compatibilidad Cloud / DGX On-Premise

En [config/models_nvidia.py](../config/models_nvidia.py):
- `obtener_modelos_nvidia(timeout=4.0, strict=False)` consulta `GET {NVIDIA_BASE_URL}/models` con `Authorization: Bearer {NVIDIA_API_KEY}`.
- Soporta tanto el endpoint cloud de NVIDIA (`https://integrate.api.nvidia.com/v1`) como un servidor **NVIDIA DGX Spark / NIM local** cambiando únicamente `NVIDIA_BASE_URL` en `.env`.
- Los módulos hermanos (`models_gemini.py`, `models_groq.py`, `models_cohere.py`, `models_ollama.py`) siguen exactamente el mismo contrato (`timeout <= 4.0`, `strict=True/False`) para que `detectar_proveedores_activos()` sondee los 5 proveedores **en paralelo** con `ThreadPoolExecutor` en menos de 4 segundos (con caché TTL de 120 s).

---

## 3. Gestión de Cerebros en Runtime (`ACTIVE_AGENT_BRAINS`)

Definido en [config/models.py](../config/models.py):

```python
DEFAULT_NVIDIA_BRAINS = {
    "supervisor":   ("NVIDIA", "nvidia/nemotron-3-super-120b-a12b"),
    "analista":     ("NVIDIA", "nvidia/nemotron-3-super-120b-a12b"),
    "investigador": ("NVIDIA", "nvidia/nemotron-3-super-120b-a12b"),
    "control":      ("NVIDIA", "nvidia/llama-3.1-nemotron-nano-8b-v1"),
    "vendedor":     ("NVIDIA", "nvidia/llama-3.1-nemotron-nano-8b-v1"),
    "publicista":   ("NVIDIA", "nvidia/llama-3.1-nemotron-nano-8b-v1"),
    "tutor_ui":     ("NVIDIA", "nvidia/llama-3.1-nemotron-nano-8b-v1"),
}
```

### API de control en vivo (sin reiniciar el proceso):
- `set_agent_brain(role, provider, model_name)`: cambia el proveedor/modelo de un subagente individual y limpia su Circuit Breaker.
- `reset_brains_to_nvidia_default()`: restaura los 7 roles al perfil 100% NVIDIA NIM y limpia todos los cooldowns.
- `get_active_brains() -> dict[str, dict]`: devuelve proveedor, modelo, temperatura, perfil, bandera `is_custom` y cadena de rescate para cada rol.
- `override_model_context(provider, model_name)`: context manager basado en `contextvars` seguro para concurrencia en FastAPI (`POST /orchestrate`).

### Orden de resolución en `get_llm(provider=None, model_name=None, temperature=None, role=None)`:
1. Argumento explícito `provider` / `model_name` pasado directamente a `get_llm(...)`.
2. Override de contexto por petición (`override_model_context`) u override global de sesión.
3. Entrada viva en `ACTIVE_AGENT_BRAINS[role]` (100% NVIDIA por defecto o cerebro personalizado).
4. Envoltura obligatoria en `ResilientChatModel` con los demás proveedores activos en orden `NVIDIA → Gemini → Groq → Cohere → Ollama`.

---

## 4. Resiliencia: `ResilientChatModel` y Circuit Breaker

En LangChain estándar, `RunnableWithFallbacks` **no implementa** `.bind_tools()` ni `.with_structured_output()`, lo que rompería tanto `create_react_agent` como `SupervisorDecision`.

[config/models.py](../config/models.py) resuelve esto con **`ResilientChatModel(RunnableWithFallbacks)`**:
1. **Propagación de `.bind_tools()`:** vincula las herramientas al modelo primario **y** a cada modelo de la lista de fallbacks, envolviendo todo nuevamente en `ResilientChatModel`.
2. **Propagación de `.with_structured_output(schema)`:** aplica el esquema Pydantic al primario y a cada fallback, devolviendo un `ResilientChatModel` estructurado.
3. **Timeouts y reintentos acotados:** `timeout=15s` en primario, `12s` y `max_retries=0` en fallbacks, priorizando modelos de baja latencia (`gemini-flash-lite-latest`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`) para evitar errores `504 DEADLINE_EXCEEDED`.
4. **Circuit Breaker de sesión (`_CIRCUIT_COOLDOWN_SECONDS = 90.0`):**
   - Si un proveedor falla en inferencia (red inalcanzable, `504`, `429`, error de socket), `ResilientChatModel.invoke()` conmuta al siguiente proveedor saludable y marca el proveedor caído en cooldown por 90 s.
   - En los nodos siguientes del mismo turno (o turnos consecutivos), `get_llm()` promueve directamente un respaldo sano en `0 ms` sin volver a esperar timeouts repetidos.
   - Al ejecutar `/cerebro` o `/reset-cerebros`, el cooldown se limpia de inmediato.

---

## 5. Seguridad y Guardrails (`config/guardrails/` y `tools/guards.py`)

El sistema aplica **defensa en profundidad** en dos niveles:

1. **Nivel declarativo Colang ([config/guardrails/rails.co](../config/guardrails/rails.co)):**
   - `check prompt injection`: rechaza intentos de extraer el system prompt o ejecutar acciones destructivas (`drop database`, `borra el inventario`).
   - `prevent cost leakage`: intercepta menciones a `costo unitario`, `nos cuesta` o `precio de adquisición` en mostrador.
   - `enforce concise ui sentences`: acota salidas verbosas en `tutor_ui`.
2. **Nivel programático determinista ([tools/guards.py](../tools/guards.py)):**
   - `prevent_cost_leakage(text)`: reemplaza montos asociados a costo unitario por `[CONFIDENCIAL]` antes de entregar la respuesta de `vendedor`.
   - `enforce_max_sentences(text, max_sentences=2)`: garantiza matemáticamente que `tutor_ui` nunca exceda 2 oraciones.
   - `enforce_db_grounding(response_text, db_evidence)`: agrega nota de cautela si se afirman existencias numéricas sin evidencia confirmada de BD.
