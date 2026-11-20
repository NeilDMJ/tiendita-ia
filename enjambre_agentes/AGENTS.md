# AGENTS.md — Integración NVIDIA NeMo Microservices

Guía técnica de la capa NeMo del enjambre: modelos por rol (LoRA), recuperación semántica con
reranking, Data Flywheel hacia NeMo Customizer, guardrails híbridos y percepción con NIM Vision.
Para la arquitectura general del grafo ver `README.md`; este archivo cubre solo lo NeMo.

## 1. Principios

- **Mismo código en nube y en local.** Todo cliente resuelve su URL desde `NVIDIA_BASE_URL`
  (`https://integrate.api.nvidia.com/v1` o `http://localhost:8000/v1` en DGX Spark). Sin API key en local.
- **Cada capa degrada sin romper el grafo.** Sin NeMo, sin PostgreSQL o sin `nemoguardrails`, el sistema
  cae a los fallbacks deterministas previos (banco semilla, dataset del asistente, búsqueda léxica, reglas Python).
- **Gobernanza intacta.** `enforce_db_grounding` sigue siendo la última barrera y corre sobre el texto ya
  depurado por los rails. Toda mutación sigue pasando por HITL (`interrupt()`).
- **Percepción vs. decisión.** NIM Vision solo convierte píxeles en `vision_payload`; no ejecuta SQL.
  Su salida pasa por los input rails y por el HITL como cualquier payload.
- **Desacople de la UI.** Nada de esto importa librerías de interfaz; la app solo habla con `api.py`.

## 2. Mapa de cambios

| Archivo | Aporte |
|---|---|
| `models.py` | `get_llm(..., role=)`, `get_nemo_embeddings_client()`, `get_nemo_reranker_client()`, `run_sync`, `nemo_is_configured` |
| `few_shot_retriever.py` | pgvector Top-10 → reranker Top-3, `record_hitl_feedback`, `export_sft_dataset_jsonl`, CLI `init-db / seed / backfill` |
| `guards.py` | Capa híbrida: `check_input`, `scan_untrusted_inputs`, `check_tutor_output`, `check_cost_exposure`, `redact_internal_costs` |
| `tools_bridge.py` | `resolve_product_hybrid`, `NimVisionClient`, `vision_payload_from_image`, `ensure_catalog_schema`, `index_catalog_embeddings` |
| `graph.py` | Input rails en el supervisor, output rails en tutor/vendedor/analista, registro del flywheel en el nodo HITL |
| `api.py` | `image_base64` + `image_endpoint` en `/orchestrate` y `/orchestrate/stream` |
| `state.py` | `UIStateModel.elementos_visibles` (opcional) |
| `config/guardrails/` | `config.yml` + `rails.co` (Colang 1.0) |
| `sql/` | `001_ejemplos_few_shot.sql`, `002_productos_embedding.sql` |
| `scripts/export_nemo_sft.py` | CLI del export SFT |
| `test_nemo.py` | Pruebas de toda la capa (NIM falso local + PostgreSQL opcional) |

`resolve_product_hybrid` es una función auxiliar, no una `@tool`: `ALL_TOOLS` y `GET /mcp/tools` siguen exponiendo 17 herramientas.

## 3. Nube vs. despliegue local

| Servicio | Nube (`NVIDIA_BASE_URL` por defecto) | Local (DGX Spark / contenedores NIM) |
|---|---|---|
| LLM / VLM | `POST {base}/chat/completions` | `POST http://host:8000/v1/chat/completions` |
| Embeddings | `POST {base}/embeddings` | `POST {NEMO_EMBED_BASE_URL}/embeddings` |
| Reranker | `POST https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking` | `POST {NEMO_RERANK_BASE_URL}/ranking` |

El reranker hospedado **no** vive bajo `integrate.api.nvidia.com/v1`; el cliente lo detecta por el host y usa
la URL correcta. En local cada NIM suele ser un contenedor con su propio puerto: usa `NEMO_EMBED_BASE_URL`,
`NEMO_RERANK_BASE_URL` o la URL completa `NEMO_RERANK_URL`. Para un solo NIM local basta `NVIDIA_BASE_URL`.

`nemo_is_configured()` es `True` con `NVIDIA_API_KEY` (nube) o con endpoints locales; si es `False` no se
intenta ninguna llamada de red a NeMo.

## 4. Modelos por rol y adaptadores LoRA

`get_llm(provider, model_name, temperature, role="supervisor")` elige el modelo con esta prioridad
(solo proveedor NVIDIA/NIM; el resto de proveedores ignora `role`):

1. `model_name` explícito (p. ej. `--model` del CLI).
2. `NEMO_MODEL_<ROL>` — `SUPERVISOR`, `VENDEDOR`, `CONTROL`, `TUTOR` (alias `orquestador`, `tutor_ui`; cualquier otro rol usa `NEMO_MODEL_<ROL en mayúsculas>`).
3. `NVIDIA_REASONING_MODEL`.
4. `nvidia/nemotron-3.5-super-vl-120b-a12b`.

El valor es el nombre con el que tu NIM sirve el modelo base o el adaptador LoRA entrenado en Customizer.

> **Hoy solo el supervisor invoca un LLM** (fallback cuando las heurísticas no enrutan). `control`, `vendedor`
> y `tutor_ui` son deterministas, así que `NEMO_MODEL_VENDEDOR/CONTROL/TUTOR` quedan listas pero sin efecto
> hasta que esos nodos llamen `get_llm(role=...)`.

## 5. NeMo Retriever: few-shot semántico

```mermaid
flowchart LR
    Q["query del usuario"] --> E["nv-embedqa-e5-v5<br/>input_type=query"]
    E --> V["pgvector<br/>embedding <=> query_vec<br/>WHERE rol_agente AND verificado<br/>Top-10"]
    V --> R["nv-rerankqa-mistral-4b-v3<br/>Top-3"]
    R --> P["prompt del agente"]
    V -. "reranker caído" .-> P
```

`FewShotRetriever.get_few_shots(role, query)` prueba, en orden: (1) pipeline semántico (requiere `DATABASE_URL`,
NeMo alcanzable y `query`), (2) dataset del asistente para `control`, (3) últimos verificados en PostgreSQL,
(4) banco semilla en memoria. Si el reranker falla se usa el orden por coseno; cualquier otro error se registra
como warning y se pasa al siguiente nivel.

**Inicialización** (requiere PostgreSQL con la extensión `pgvector`):

```bash
export DATABASE_URL=postgresql://usuario:clave@localhost:5432/tiendita_ia
uv run python few_shot_retriever.py init-db     # extensión, tabla ejemplos_few_shot, índices (idempotente)
uv run python few_shot_retriever.py seed        # indexa semillas + dataset del asistente (idempotente por huella)
uv run python few_shot_retriever.py backfill    # embeddings pendientes (filas guardadas con NeMo caído)
```

Tabla `ejemplos_few_shot`: `rol_agente`, `entrada_json`, `salida_json`, `texto_indexado` (lo que se embebe: la
entrada), `embedding vector(1024)`, `origen` (`seed | assistant_dataset | hitl_aprobado | hitl_editado`),
`verificado`, `huella` (sha256 único), `creado_en`. Los documentos se indexan como `passage` y las consultas
como `query`. Si cambias de modelo de embeddings, ajusta `NEMO_EMBED_DIMS` **y** `vector(N)` en `sql/*.sql`:
el cliente rechaza vectores de otra dimensión.

## 6. Data Flywheel hacia NeMo Customizer

```mermaid
flowchart LR
    H["HITL: operador aprueba / edita"] --> F["record_hitl_feedback"]
    F -->|"DATABASE_URL"| PG[("ejemplos_few_shot<br/>verificado = true")]
    F -->|"sin BD o BD caída"| B["datasets/hitl_feedback.jsonl"]
    PG --> X["export_nemo_sft.py"]
    B --> X
    X --> T["train.jsonl + val.jsonl<br/>messages: system / user / assistant"]
    T --> C["NeMo Customizer<br/>SFT + LoRA por rol"]
    C --> M["adaptador servido por NIM"]
    M --> N["NEMO_MODEL_‹ROL›"]
    N -.-> H
```

**Qué se registra.** En `aprobacion_hitl_node`, tras ejecutar una mutación aprobada, se guarda un par
`(entrada, salida)` para el agente que la propuso (`sender`): la entrada es `event_source` + `query` +
`vision_payload`; la salida es `action_type` + `summary` + el payload realmente ejecutado.
Aprobado tal cual → `hitl_aprobado`; corregido por el operador (`edited_payload` distinto del propuesto) →
`hitl_editado` con el payload corregido. **Los rechazos no se registran.** El registro nunca interrumpe el HITL.

Sin `DATABASE_URL` (o si falla la inserción) el registro va a `datasets/hitl_feedback.jsonl`
(`NEMO_FLYWHEEL_BUFFER`); el export une BD y buffer y deduplica por huella. Si NeMo no responde al registrar,
la fila queda sin vector y `backfill` la completa.

**Exportar:**

```bash
uv run python scripts/export_nemo_sft.py                                   # todo lo verificado, split 90/10
uv run python scripts/export_nemo_sft.py --rol vendedor --solo-hitl        # un adaptador por rol, solo humanos
uv run python scripts/export_nemo_sft.py --rol tutor_ui --output datasets/tutor_train.jsonl --val-ratio 0.2
```

Genera `<nombre>_train.jsonl` y `<nombre>_val.jsonl` (split determinista por hash). Cada línea:

```json
{"messages": [
  {"role": "system", "content": "<ROLE_SYSTEM_PROMPTS[rol]>"},
  {"role": "user", "content": "<entrada_json>"},
  {"role": "assistant", "content": "<salida_json>"}]}
```

Desde Python: `export_sft_dataset_jsonl("datasets/nemo_sft_train.jsonl", roles=["vendedor"], solo_hitl=True)`.

**Lanzar el SFT.** Sube ambos archivos como dataset de tu instancia de Customizer y crea un *customization job*
`sft` con `finetuning_type: lora` sobre el modelo base de ese rol; al terminar, despliega el adaptador en el NIM y
pon su nombre en `NEMO_MODEL_<ROL>`. El esquema de la API cambia entre versiones de Customizer: sigue la guía de la
tuya (`docs.nvidia.com/nemo/microservices/latest/fine-tune/tutorials/lora-customization-job.html`). Las guías
recomiendan separar validación (10–20 %) y al menos 50–100 ejemplos; el script avisa si no se cumple.

> **Alinea los prompts.** El `system` del dataset es `ROLE_SYSTEM_PROMPTS[rol]` (`few_shot_retriever.py`); el
> adaptador debe invocarse con ese mismo prompt base. El supervisor aún usa su propio prompt en `graph.py` y le
> manda el `query` en texto plano (el dataset usa la entrada como JSON): unifícalos antes de desplegar un adaptador.

## 7. Guardrails híbridos

Dos capas con una sola fuente de verdad: las reglas son funciones puras de Python (`guards.py`), siempre activas.
Con `NEMO_GUARDRAILS_ENABLED=true` y el extra instalado, `config/guardrails/rails.co` ejecuta además esas mismas
reglas como flujos Colang (el resultado reporta `engine="nemo+python"` y el rail que bloqueó). Después de NeMo
**siempre** corre la capa Python, que es la que repara el texto.

```bash
uv sync --extra guardrails          # ojo: `uv sync` a secas desinstala el extra
NEMO_GUARDRAILS_ENABLED=true uv run python cli_tester.py
```

| Rail | Dónde | Regla |
|---|---|---|
| Input | `supervisor_node`, 1.ª iteración | Prompt injection en `query` **y en todos los strings de `vision_payload`** (nombres, descripciones, proveedor): ignorar instrucciones, revelar prompt, cambio de rol, marcadores `system:`, tokens de control, HTML oculto, exfiltración de claves, saltar HITL, texto invisible (ancho cero / tag chars). Si bloquea → `FIN`, sin `pending_approval`, `validation_errors` con la ruta (`guardrail:...@vision_payload.items[0].descripcion`). |
| Output | `tutor_ui_node` | ≤ 2 oraciones y ningún botón/campo entre comillas que no exista. Se descartan las oraciones inválidas; si no queda ninguna, se arma una guía segura solo con `campos_vacios` y `error_visible`. |
| Output | `vendedor_node`, `analista_node` | En fuentes públicas (`vision_api`, `ui_copilot`) se eliminan oraciones con costo/margen/utilidad o con un monto igual a un `costo_unitario` (salvo que también sea un precio público) y se quitan `costo_unitario`, `costo*` y `margen_*` de `db_evidence`. En `chat` y `cron_trigger` (dueño) no se toca nada. |

**Elementos de UI válidos.** Si la app envía `ui_state.elementos_visibles`, esa lista es la verdad (más
`campos_vacios`). Si no, se usa `UI_ELEMENT_CATALOG` en `guards.py` (SPEI, tarjeta, QR); en pantallas desconocidas no
se valida. Para validación autoritativa, envía siempre `elementos_visibles`.

Los rails de NeMo no usan LLM (`config.yml` no define `models`). Para añadir rails basados en LLM (p. ej.
`self check input`) agrega un modelo en `config.yml`.

## 8. Catálogo híbrido y NIM Vision

**`resolve_product_hybrid(vision_label)`** (usado por `build_pos_cart_from_vision` y `parse_vision_catalog_item`
cuando no hay SKU ni nombre exacto):

1. Coincidencia exacta de SKU, nombre o alias → `metodo="lexico"`, sin red.
2. `pgvector+rerank` — pgvector Top-10 + reranker (requiere `DATABASE_URL` y `productos.embedding`; devuelve filas SQL exactas).
3. `memoria+rerank` — igual sobre el catálogo en memoria, con caché de embeddings.
4. Sin coincidencia → `ambiguo=False, producto=None`.

Nunca adivina: si el mejor logit queda bajo `NEMO_RERANK_MIN_LOGIT` o a menos de `NEMO_RERANK_MIN_GAP` del segundo,
devuelve `ambiguo=True` con los candidatos; el POS no cobra ese ítem y agrega una alerta para el operador. Los
umbrales son heurísticos: calíbralos con tu catálogo. Las filas omiten `costo_unitario` y entran a `db_evidence`
(`resolucion_visual`). Para usar pgvector sobre `productos`:

```bash
uv run python -c "from tools_bridge import ensure_catalog_schema, index_catalog_embeddings; ensure_catalog_schema(); print(index_catalog_embeddings())"
```

**NIM Vision.** `NimVisionClient` (`meta/llama-3.2-90b-vision-instruct` o `NIM_VISION_URL`/`NIM_VISION_MODEL`)
convierte una imagen en un `VisionPayloadModel` validado por endpoint. Cumple las restricciones documentadas de los
VLM NIM (una imagen por petición, sin mensaje `system` con imágenes), instruye tratar el texto de la imagen como
datos, reintenta una vez si el JSON es inválido y recorta `confianza_global` a [0, 1] (0.5 si el modelo la omite).

```python
from tools_bridge import vision_payload_from_image
payload = vision_payload_from_image(open("mostrador.jpg", "rb").read(), "/pos-checkout")
run_orchestration(event_source="vision_api", vision_payload=payload)
```

Por API: `POST /orchestrate` con `{"image_base64": "...", "image_endpoint": "/pos-checkout"}` (fuerza
`event_source="vision_api"`; un `vision_payload` explícito tiene prioridad; 422 sin `image_endpoint`; 502 si el VLM falla).
Prueba con imágenes pequeñas: la API hospedada puede limitar las imágenes en línea; en local no aplica.

## 9. Variables de entorno

| Variable | Default | Uso |
|---|---|---|
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | Base de LLM, embeddings y visión (nube o NIM local) |
| `NVIDIA_API_KEY` / `NVAPI_KEY` | — | Solo nube |
| `NVIDIA_REASONING_MODEL` | `nvidia/nemotron-3.5-super-vl-120b-a12b` | Fallback de `get_llm(role=)` |
| `NEMO_MODEL_SUPERVISOR` `_VENDEDOR` `_CONTROL` `_TUTOR` | — | Modelo base o LoRA por rol |
| `NEMO_EMBED_MODEL` | `nvidia/nv-embedqa-e5-v5` | Modelo de embeddings |
| `NEMO_EMBED_DIMS` | `1024` | Dimensión esperada (debe coincidir con `vector(N)`) |
| `NEMO_EMBED_BASE_URL` | `NVIDIA_BASE_URL` | Override local del NIM de embeddings |
| `NEMO_RERANK_MODEL` | `nvidia/nv-rerankqa-mistral-4b-v3` | Modelo de reranking |
| `NEMO_RERANK_BASE_URL` | `NVIDIA_BASE_URL` | Override local (usa `{base}/ranking`) |
| `NEMO_RERANK_URL` | — | URL completa del endpoint de ranking (máxima prioridad) |
| `NEMO_RETRIEVER_ENABLED` | `true` | `false` desactiva embeddings/reranking (solo fallbacks) |
| `NEMO_RERANK_MIN_LOGIT` / `_MIN_GAP` | `0.0` / `1.0` | Umbrales de `resolve_product_hybrid` |
| `NIM_VISION_URL` / `NIM_VISION_MODEL` | `NVIDIA_BASE_URL` / `meta/llama-3.2-90b-vision-instruct` | NIM Vision |
| `NEMO_GUARDRAILS_ENABLED` | `false` | Activa la capa Colang (requiere el extra) |
| `NEMO_FLYWHEEL_BUFFER` | `datasets/hitl_feedback.jsonl` | Buffer local del flywheel |
| `DATABASE_URL` | — | Activa pgvector y el flywheel sobre PostgreSQL |

## 10. Pruebas

```bash
uv run python test_suite.py     # regresión del grafo (no usa NeMo)
uv run python test_nemo.py      # capa NeMo completa

# con PostgreSQL + pgvector real (opcional)
docker run -d --rm --name pgv -e POSTGRES_PASSWORD=test -e POSTGRES_DB=tiendita -p 55432:5432 pgvector/pgvector:pg16
TEST_DATABASE_URL=postgresql://postgres:test@localhost:55432/tiendita uv run python test_nemo.py
```

`test_nemo.py` levanta un **NIM falso** en localhost (embeddings por bolsa de palabras hasheada, ranking por
solapamiento, chat para visión) y apunta `NVIDIA_BASE_URL` a él: ejercita el camino httpx real, pero **no valida la
calidad de los modelos de NVIDIA ni sus endpoints reales**. Antes de producción, haz una prueba de humo con tu
`NVIDIA_API_KEY` o con tus NIM locales. Las pruebas de NeMo Guardrails se omiten si el extra no está instalado.

## 11. Invariantes y límites conocidos

- Toda mutación sigue requiriendo `pending_approval` + `interrupt()`; los rails y el flywheel no la sustituyen.
- Un nodo nuevo que muestre montos debe pasar por `enforce_db_grounding` y, si puede responder en mostrador, por
  `check_cost_exposure`.
- Las herramientas de `tools_bridge.py` siguen operando sobre `MockPostgresDB`. Con `DATABASE_URL` y una tabla
  `productos` con `embedding`, `resolve_product_hybrid` lee filas de PostgreSQL mientras los commits siguen yendo
  al mock: conecta las herramientas a PostgreSQL antes de usar ese tier en producción.
- `actualizar_precio`, `ajustar_stock` y `crear_producto` modifican el mock al **proponer** la acción (antes del
  HITL), no al confirmarla. Es un comportamiento previo a esta integración, pendiente de revisar.
