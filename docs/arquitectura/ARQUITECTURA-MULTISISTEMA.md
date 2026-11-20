# Tiendita IA — Arquitectura multisistema (contexto para agentes de IA)

> **Para qué sirve:** inyectar contexto de sistema a otros agentes de IA. Describe cómo está construido el proyecto
> **hoy**, módulo por módulo, los servicios de NVIDIA que usa, y qué partes de la documentación existente **no** están en código.
> **Regla de verdad:** todo lo afirmado aquí se verificó leyendo el código de la rama `test-prototipado`
> (base: `development` @ `e7e00c9` + commit `feat:LoRa` `53fabee`, 20-nov-2026). Si este documento y otro texto
> (README, `enjambre_agentes/docs/*`) discrepan, **manda el código**; las discrepancias conocidas están en la sección 9.
> **Cómo se verificó:** lectura de código y análisis estático. El servidor unido del enjambre **no se ha ejecutado** en esta
> verificación (no hay Docker, `.env` ni claves en la máquina de revisión).

---

## 1. Resumen en 8 líneas

1. **Tiendita IA** es una app móvil para tenderos (Expo / React Native) con cuatro módulos: **Inicio, Cobrar, Inventario, Asistente**.
2. **Cobrar** (venta) e **Inventario** (compra/alta de mercancía) identifican productos con un **modelo de visión propio**: YOLO11n-cls entrenado en NVIDIA DLI, servido con ONNX Runtime desde `back/vision/` (rutas `/vision/*`).
3. El **Asistente** es el único módulo que habla con el **enjambre de agentes** (LangGraph: 1 supervisor + 6 especialistas, modelos NVIDIA NIM) mediante la API de `enjambre_agentes/api.py`.
4. El enjambre tiene **sus propias herramientas de visión (NVIDIA NIM Vision, en la nube)**, pensadas **solo** para que el Asistente reciba fotos. **No usan el modelo ONNX.**
5. Un solo proceso (`enjambre_agentes/api.py`, puerto 8000) **monta** además `back/vision` (`/vision/*`) y el asistente bancario (`back/app`: `/asistente/mensaje`, `/salud`).
6. Datos: PostgreSQL 16 + pgvector (`back/docker-compose.yml`, esquema en `back/db/init/`).
7. **Los datos de negocio de la app (ventas, productos, altas de inventario) no tienen servidor:** la app los resuelve con mocks y una cola local en SQLite.
8. El modelo de visión (`best.onnx`) **no está en GitHub** (`.gitignore` excluye `*.onnx`): hay que entregarlo aparte en `vision/artefactos/v1/`.

---

## 2. Mapa del sistema

```
┌──────────────────────────── APP MÓVIL (front/, Expo SDK 58, RN 0.88, TypeScript) ───────────────────────────┐
│  Inicio        Cobrar              Inventario            Asistente (+ hoja "Pregúntale a Caja")           │
│  (métricas)    (foto→revisión→     (consulta, alta       chat, tarjetas de aprobación (HITL), tutor       │
│                 cobro→comprobante)  con foto)                                                              │
└────────────────────────┬──────────────────────┬──────────────────────────────┬─────────────────────────────┘
        datos de negocio │  visión (ONNX)       │                              │ API del enjambre
 /productos /ventas      │  /vision/pos-checkout│                              │ /orchestrate · /orchestrate/resume
 /inventario/altas       │  /vision/catalog-scan│                              │ /pago · /health · /state · /rag/search · /imagen
 ──► SIN SERVIDOR        │  /vision/receipt-ocr │                              │
 (mocks + cola SQLite)   ▼  (simulado)          ▼                              ▼
                  ┌────────────────────────────────────────────────────────────────────────────────┐
                  │  PROCESO ÚNICO  enjambre_agentes/api.py  (FastAPI, :8000)                       │
                  │   ├─ back/vision   → clasificador ONNX (onnxruntime)                            │
                  │   ├─ back/app      → asistente bancario /asistente/mensaje, /salud              │
                  │   └─ API del enjambre → LangGraph: supervisor + control/vendedor/analista/       │
                  │        investigador/publicista/tutor_ui + approval_gate (HITL)                  │
                  └───────────────┬──────────────────────────────┬──────────────────────────────────┘
                                  ▼                              ▼
                      PostgreSQL 16 + pgvector          NVIDIA NIM (nube): LLMs, Vision-Language,
                      (tiendita-db, Docker)             embeddings*, reranker* (*condicionales)
```

---

## 3. Reglas de alcance del proyecto (decisión del equipo)

| Capacidad | Es exclusiva de… | Cómo se materializa |
|---|---|---|
| Modelo de visión ONNX (productos) | **Venta (Cobrar) y compra/alta (Inventario)** | `front/src/api/vision.ts` → `/vision/pos-checkout`, `/vision/catalog-scan` |
| Enjambre de agentes | **Módulo Asistente** | `front/src/api/enjambre.ts` → API de `enjambre_agentes/api.py` |
| Visión NIM del enjambre (`analyze_*`) | **Asistente** (cuando el agente reciba una foto) | `tools/vision_nim.py`, endpoint `/imagen` |

El Asistente, con `EXPO_PUBLIC_ASISTENTE_ENJAMBRE=1`, usa **solo** endpoints de la API del enjambre (sección 4.6).

---

## 4. Módulos

### 4.1 App móvil (`front/`)

- **Stack:** Expo SDK 58, React Native 0.88, React 19, Expo Router (rutas por archivo), TypeScript, `zod` (validación de toda respuesta), `@tanstack/react-query`, `expo-sqlite` (borrador de venta, cola de ventas sin conexión y chat guardado), `expo-camera` / `expo-image-picker`.
- **Rutas:** pestañas `Inicio · Cobrar · Inventario · Asistente`; modales `camara` (modos `cobro|alta|ticket`), `revision/[modo]`, `venta/[id]`, `historial`.
- **Capa de API (`front/src/api/`):** `cliente.ts` (HTTP con timeout, cancelación y errores tipados), `esquemas.ts` (contratos zod), `vision.ts`, `negocio.ts`, `asistente.ts`, `acciones-asistente.ts`, `enjambre.ts`, `mocks/`.
- **Mocks:** `EXPO_PUBLIC_USE_MOCKS=1` simula negocio, asistente y visión. Flags que fuerzan lo real aunque haya mocks: `EXPO_PUBLIC_VISION_REAL` (visión), `EXPO_PUBLIC_ASISTENTE_REAL` (asistente bancario) y `EXPO_PUBLIC_ASISTENTE_ENJAMBRE` (enjambre).
- **Privacidad en el cliente:** `utils/anonimizar.ts` enmascara montos y celulares y **bloquea** el envío de tarjeta/CLABE/NIP/claves antes de llamar al servidor.
- **Sin conexión:** las ventas se guardan en una cola local (`estado/cola-ventas.ts`) y se reenvían al reconectar.

**Qué módulo de la app tiene servidor hoy:**

| Módulo | Endpoints que llama | ¿Existe servidor? |
|---|---|---|
| Cobrar / Inventario — visión | `POST /vision/pos-checkout`, `/vision/catalog-scan`, `/vision/receipt-ocr` | **Sí** (`back/vision`, OCR de tickets es **simulación**) |
| Cobrar / Inicio / Inventario — datos | `GET /productos`, `/productos/mas-vendidos`, `POST /ventas`, `GET /ventas`, `/ventas/{id}`, `POST /inventario/altas` | **No.** Ningún servidor los implementa; solo funcionan con mocks |
| Asistente (flag apagado) | `POST /asistente/mensaje` | Sí (`back/app`, asistente bancario). `/asistente/acciones/{id}/resultado` y `/asistente/tutor` **no existen** |
| Asistente (flag encendido) | `POST /orchestrate`, `/orchestrate/resume`, `/pago` | **Sí** (API del enjambre) |

### 4.2 Modelo de visión (`vision/` entrenamiento + `back/vision/` servicio)

- **Tarea:** clasificación de **un producto por foto** (no detección: no hay cajas ni conteo; `cantidad` = 1).
- **Modelo:** `YOLO11n-cls` (Ultralytics, preentrenado en ImageNet-1k) con transfer learning. 7 clases: `agua_1l, agua_bonafont, agua_members_mark, chokis, coca_cola, doritos, fondo` (30 épocas, 224 px). Clase `fondo` = no hay producto → la API devuelve `items: []`.
- **Entrenamiento:** `vision/train.py`, en el entorno **NVIDIA DLI** (Tesla T4, CUDA 12.1). Artefactos versionados en `vision/artefactos/v1/` (`registro.json`, `eval/metricas.json`, `benchmark.json`, matrices de confusión).
- **Métricas:** exactitud top-1 **0.9526** sobre 801 fotos de sesiones reservadas (`eval/metricas.json`); el benchmark reporta 0.9551 en su propio conjunto.
- **Optimización NVIDIA TensorRT:** `vision/export_trt.py` exporta `best.pt → best.onnx → best.engine` (FP16). Benchmark en T4: **PyTorch FP32 8.76 ms** vs **TensorRT FP16 1.04 ms** por inferencia, misma exactitud. El `.engine` solo corre en esa GPU.
- **Servicio en la app:** `back/vision/modelo.py` carga **`best.onnx` con onnxruntime** (CPU, o CUDA si hay `onnxruntime-gpu`); preprocesado idéntico al de Ultralytics. Ruta del modelo: `VISION_MODELO` o `vision/artefactos/v1/best.onnx`.
- **Salida:** cada ítem trae `sku, nombre, cantidad, precio_unitario, confianza, requiere_confirmacion (< VISION_UMBRAL=0.6), alternativas[]`. La clase se traduce a producto con `back/vision/catalogo_vision.json`, cuyos SKU/precios coinciden con `back/datos/catalogo.csv` (semilla de la base de datos).
- **Privacidad:** la foto se procesa en memoria; no se guarda. Límite 15 MB (413); imagen ilegible 422; sin modelo, `/vision/salud` responde 503.
- **Faltante:** el archivo `best.onnx` no está en el repositorio.

### 4.3 Enjambre de agentes (`enjambre_agentes/`)

- **Orquestación:** LangGraph con `MemorySaver` (**memoria en RAM: se pierde al reiniciar el servidor**). Grafo: `START → supervisor → {control, vendedor, analista, investigador, publicista, tutor_ui} → (approval_gate | supervisor | END)`. Límite estricto de 6 iteraciones. `interrupt_before=["approval_gate"]` pausa las acciones sensibles.
- **Supervisor:** decide con salida estructurada (`SupervisorDecision`) y, si el modelo falla, por reglas según `event_source` (en `chat` cae a `vendedor`).
- **Agentes** (cada uno es un agente ReAct de `langgraph.prebuilt`) y herramientas reales:

| Agente | Rol en la app | Modelo NIM por defecto | Herramientas principales |
|---|---|---|---|
| `supervisor` | — | `nvidia/nemotron-3-super-120b-a12b` | enrutamiento |
| `vendedor` | Caja | `nvidia/llama-3.1-nemotron-nano-8b-v1` | `analyze_pos_items`, carrito (`create_cart`, `add_to_cart`, `checkout_cart`), `suggest_upsell`, guías de pago, `query_inventory` |
| `control` | Bodega | `…nemotron-nano-8b-v1` | `analyze_catalog_photo`, `analyze_receipt`, `register_product`, `update_stock`, alertas de caducidad y stock |
| `analista` | Cuentas | `…nemotron-3-super-120b-a12b` | flujo de caja, márgenes, rotación, resumen de ventas |
| `investigador` | (general) | `…nemotron-3-super-120b-a12b` | reportes pasados, `search_web_tavily`, `scrape_webpage_clean`, conocimiento comercial |
| `publicista` | Promociones | `…nemotron-nano-8b-v1` | textos promocionales, prompts de video, CTA |
| `tutor_ui` | Ayuda de pagos | `…nemotron-nano-8b-v1` | guía de pago digital (RAG), respuesta ≤ 2 oraciones |

- **Resiliencia:** cada agente puede cambiar de proveedor en vivo (`set_agent_brain`, `PUT /brains/{rol}`); `ResilientChatModel` aplica `.with_fallbacks()` con orden **NVIDIA → Gemini → Groq → Cohere → Ollama** y un cooldown por proveedor que falla (circuit breaker).
- **Herramientas:** 33 `@tool` en total; el manifiesto MCP (`GET /tools/mcp`) exporta 24.
- **Guardias en código** (`tools/guards.py`): `enforce_max_sentences` (la usa `tutor_ui`) y `prevent_cost_leakage` (la usa `vendedor`). `enforce_db_grounding` está definida y exportada, pero **ningún agente la invoca**.
- **Human-in-the-Loop:** `vendedor` (descuentos), `control` (altas de catálogo / gastos críticos) y `publicista` (campañas) generan `pending_approval`; el grafo se pausa y se reanuda con `POST /orchestrate/resume` (o por WebSocket). Al aprobar, `approval_gate` hace el COMMIT en PostgreSQL; al rechazar, no escribe nada. Cada decisión se registra para entrenamiento (`record_hitl_feedback`).
- **Memoria y RAG de pagos:** RAG sobre CoDi/SPEI/DiMo (`tools/rag_nemo.py`): FAISS local + pgvector (`documento`/`fragmento`, `vector(1024)`); consulta con `all-MiniLM-L6-v2` (HuggingFace, local) y reranker NVIDIA **solo si hay clave autorizada**. Reportes estratégicos se guardan en `enjambre_agentes/data/reportes/`.
- **LoRa (local, opcional):** `scripts/build_lora_dataset.py` → `train_lora_local.py` (PyTorch + PEFT, r=16, GPU local) → `export_lora_ollama.py` (GGUF para Ollama). Los datasets se generan en `enjambre_agentes/data/hitl_feedback/` (carpeta **no versionada**). No usa el servicio NeMo Customizer.
- **Superficies:** CLI (`uv run python main.py`; banderas `--serve --host --port --tunnel --reload --agent-brain --query --source --list-models --brains`), REST, SSE (`/orchestrate/stream`), WebSocket (`/ws/orchestrate`, con HITL en el mismo socket).
- **Seguridad:** si `TIENDITA_API_KEY` está definida, **todas** las rutas (incluidas `/vision/*` y `/asistente/mensaje`) exigen `X-API-Key`, salvo `/health`, `/docs`, `/redoc`, `/openapi.json`. La app **no envía** ese encabezado: déjala vacía al usar la app.

### 4.4 Asistente bancario (`back/app/`)

Guía paso a paso para operaciones bancarias y consultas sobre DiMo/CoDi/SPEI. Es **independiente** del enjambre pero corre dentro del mismo servidor.

- **Endpoints:** `POST /asistente/mensaje`, `GET /salud`.
- **El modelo solo redacta:** los pasos salen de `app/datos/guias.json`; `app/filtro.py` descarta botones, listas o claves que el modelo invente; hay bloqueo de datos sensibles y de temas fuera de alcance.
- **LLM:** `LLM_PROVIDER=nim` (por defecto `nvidia/nemotron-3.5-bolt-e4b` en `integrate.api.nvidia.com`) u `ollama` (por defecto `qwen2.5:3b`, local, sin que salga nada del equipo).
- **Conocimiento:** búsqueda **híbrida** BM25 + embeddings de NVIDIA (`nvidia/nemotron-3.5-embed-8b`, HTTP `/embeddings`) con RRF sobre `app/datos/conocimiento.jsonl` (**934 fragmentos**) y `embeddings.npz`; si NVIDIA falla, usa solo BM25.
- Verificado funcionando en local con Ollama: respuestas en ~4 s, rechazo de temas fuera de alcance.

### 4.5 Base de datos (`back/db/`, `back/docker-compose.yml`)

PostgreSQL 16 + pgvector (contenedor `tiendita-db`). Esquema en `db/init/001…007`: `producto, producto_alias, categoria, venta, venta_item, movimiento_inventario, pago, lote, proveedor, comprobante, comprobante_concepto, deteccion, inferencia_vision, historial_precio, corte_caja, negocio, conversacion, mensaje, accion_propuesta, alerta, promocion, reporte, referencia_externa, documento, fragmento`. Vistas usadas por el enjambre: `v_inventario, v_por_caducar, v_stock_bajo, v_margen_producto, v_flujo_caja, v_ventas_dia, v_coocurrencia`; función `registrar_venta(jsonb)`. Semilla: `back/datos/catalogo.csv` (21 productos, columna `clase_vision`).

### 4.5-bis Dataset sintético `assistant/`

`assistant/gen_data.py` genera (semilla 7, marcado `sintetico: true`) un dataset de ajuste fino de un "asistente de catálogo" que responde **solo con JSON** de llamada a herramienta (`crear_producto`, `actualizar_precio`, `consultar_inventario`, `ajustar_stock`…): 961 ejemplos de entrenamiento, 119 de validación y 119 de prueba (`assistant/data/`); `assistant/eval.py` lo evalúa. **Ningún código de ejecución lo usa** (ni la app, ni el enjambre, ni `back/`).

### 4.6 Integración Asistente ↔ Enjambre (`front/src/api/enjambre.ts`)

Adición **no destructiva**: con `EXPO_PUBLIC_ASISTENTE_ENJAMBRE=0` (por defecto) el Asistente funciona como antes.

| Función de la app | Endpoint | Qué hace |
|---|---|---|
| `enviarMensajeEnjambre` | `POST /orchestrate` | Chat: manda solo el mensaje nuevo + `thread_id` + `event_source:"chat"`. El servidor guarda el historial por hilo. |
| `reanudarAprobacion` | `POST /orchestrate/resume` | Aprobar/rechazar una acción pausada (HITL): `{thread_id, approved}`. |
| `pedirAyudaTutorEnjambre` | `POST /pago` | Tutor de pagos CoDi/SPEI/DiMo/tarjeta. |
| `consultarSaludEnjambre`, `obtenerEstadoHilo`, `buscarEnRagPagos`, `enviarImagenAlEnjambre` | `GET /health`, `GET /state/{id}`, `GET /rag/search`, `POST /imagen` | Disponibles como funciones; **ninguna pantalla las llama todavía**. |

- **Traducción de respuesta:** la etiqueta del agente (`[VENDEDOR]:`…) fija el oficio mostrado (`vendedor→caja, control→bodega, analista→cuentas, publicista→promociones, tutor_ui→tutor, investigador→general`). Texto vacío → `no_resuelto`.
- **Aprobaciones (HITL):** un `pending_approval` se muestra como tarjeta nueva `aprobar_enjambre` (Aprobar / No). Confirmar llama a `/orchestrate/resume` con `approved:true`; rechazar, con `false`.
- **Hilos:** un `thread_id` por canal (`asistente` y `caja`), guardado en el teléfono; "Borrar chat" crea uno nuevo.
- **Límites conocidos:** el enjambre no recibe el contexto de la venta en revisión (solo el texto); no devuelve `sugerencias` ni propuestas estructuradas (`confirmar_venta`, `confirmar_alta`) — su aprobación es texto libre; el timeout es 90 s (el enjambre es síncrono).
- **Probado:** tipos (`tsc`), lint de los archivos tocados y 17 pruebas ejecutables (traducción de respuestas, cuerpos de las llamadas HTTP, hilos, y que con el flag apagado no se escriba nada) con respuestas de ejemplo de la forma exacta de `_formatear_respuesta_orquestacion`. El script de prueba no está versionado. **No** probado contra un servidor real.

---

## 5. Servicios de NVIDIA

**Usados en código:**

| Servicio | Dónde | Notas |
|---|---|---|
| **NIM — LLMs de chat** | `enjambre_agentes/config/models.py` (`ChatNVIDIA`, `langchain-nvidia-ai-endpoints`); `back/app/llm.py` | `nvidia/nemotron-3-super-120b-a12b`, `nvidia/llama-3.1-nemotron-nano-8b-v1` (enjambre); `nvidia/nemotron-3.5-bolt-e4b` (asistente bancario). Requiere `NVIDIA_API_KEY`. |
| **NIM Vision (VL)** | `enjambre_agentes/tools/vision_nim.py` (REST `chat/completions`) | Orden: `nvidia/nemotron-3.5-super-vl-120b-a12b`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, `google/gemma-3-12b-it`. Solo para el Asistente. |
| **NIM — embeddings** | `back/app/conocimiento.py` (HTTP `/embeddings`) | `nvidia/nemotron-3.5-embed-8b`; opcional con respaldo a BM25. |
| **NVIDIA DLI** (entorno de entrenamiento) | `vision/train.py`, `vision/artefactos/v1/registro.json` | Entrenamiento en Tesla T4 (CUDA 12.1). |
| **TensorRT** | `vision/export_trt.py`, `benchmark.json` | Motor FP16 de 1.04 ms; **no** es lo que sirve la app (la app usa ONNX). |
| **GPU NVIDIA local (CUDA)** | `enjambre_agentes/scripts/train_lora_local.py` | Entrenamiento LoRA con PyTorch + PEFT. |

**Condicionales / presentes pero no activos por defecto:** `NVIDIAEmbeddings` (`config/models.py`, solo si se elige como proveedor de embeddings) y reranker `nvidia/nv-rerankqa-mistral-4b-v3` (`tools/rag_nemo.py`, solo si la clave está autorizada).

**Documentados pero NO implementados en código:** ver sección 9 (NeMo Guardrails, NeMo Customizer, NeMo Retriever como servicio).

---

## 6. Endpoints por servidor

**API del enjambre (`enjambre_agentes/api.py`)**
`GET /health · GET /models · GET /tools/mcp · GET /brains · PUT /brains/{role} · POST /brains/reset · POST /orchestrate · POST /orchestrate/stream (SSE) · POST /orchestrate/resume · GET /state/{thread_id} · POST /pago (= /ui-copilot) · POST|GET /rag/search · POST /imagen · POST /catalog-scan · POST /pos-checkout · POST /receipt-ocr · POST /cron · GET /reports/history · GET /reports/{id} · WS /ws/orchestrate`
(`/catalog-scan`, `/pos-checkout`, `/receipt-ocr` del enjambre usan **NIM Vision**; **no** son los `/vision/*` del modelo ONNX.)

**Visión ONNX (`back/vision`, prefijo `/vision`)** — `POST /pos-checkout · POST /catalog-scan · POST /receipt-ocr (simulado) · GET /salud`

**Asistente bancario (`back/app`)** — `POST /asistente/mensaje · GET /salud`

**Forma de la respuesta del enjambre** (`_formatear_respuesta_orquestacion`): `{status: completed|pending_approval|approved_and_resumed|rejected_and_resumed, thread_id, next_agent, next_nodes, reply, messages[], requires_approval, pending_approval, db_evidence, strategic_report, promo_assets, iteration_count}`.

---

## 7. Variables de entorno (solo nombres)

- **Enjambre** (`enjambre_agentes/.env`): `NVIDIA_API_KEY, NVIDIA_BASE_URL, DATABASE_URL, TAVILY_API_KEY, HF_TOKEN, GEMINI_API_KEY, GROQ_API_KEY, COHERE_API_KEY, OLLAMA_BASE_URL, API_HOST, API_PORT, TIENDITA_API_KEY, SSH_VPS_TARGET, LANGSMITH_*`.
- **Back** (`back/.env`): `LLM_PROVIDER, LLM_FALLBACK, NVIDIA_API_KEY, NIM_BASE_URL, NIM_MODEL, OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TIMEOUT_S, LLM_MAX_TOKENS, CORS_ORIGINS, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT, CARGAR_SEMILLA, DATABASE_URL`.
- **Visión:** `VISION_MODELO, VISION_UMBRAL`.
- **App** (`front/.env`): `EXPO_PUBLIC_API_URL, EXPO_PUBLIC_USE_MOCKS, EXPO_PUBLIC_VISION_REAL, EXPO_PUBLIC_ASISTENTE_REAL, EXPO_PUBLIC_ASISTENTE_ENJAMBRE, EXPO_PUBLIC_MOCK_VISION, EXPO_PUBLIC_MOCK_PAGO, EXPO_PUBLIC_MOCK_ASISTENTE`.

---

## 8. Cómo levantarlo

```bash
# Base de datos (Docker Desktop encendido)
cd back && cp .env.example .env     # definir DB_PASSWORD
docker compose up -d db

# Servidor unido: enjambre + visión + asistente bancario (puerto 8000)
cd ../enjambre_agentes && cp .env.example .env   # definir NVIDIA_API_KEY y DATABASE_URL
uv sync
uv run uvicorn api:app --host 0.0.0.0 --port 8000

# App (en otra terminal)
cd ../front && cp .env.example .env
#   EXPO_PUBLIC_API_URL=http://<IP-de-la-laptop>:8000
#   EXPO_PUBLIC_ASISTENTE_ENJAMBRE=1   (Asistente → enjambre)
npx expo start -c
```
Hay que ejecutar `uvicorn` **desde `enjambre_agentes/`**: `api.py` importa `config`, `schemas`, `tools` y `agents` como paquetes de primer nivel y agrega `back/` al **final** del `sys.path` para que `app` y `vision` (de `back/`) no tapen a los del enjambre. Sin `onnxruntime`/`pillow` el servidor arranca pero la visión queda desactivada (aviso en consola). Requisito previo no versionado: `vision/artefactos/v1/best.onnx`.

---

## 9. Lo que la documentación dice y el código NO respalda (omitido de este documento)

| Afirmación en la documentación | Realidad verificada |
|---|---|
| "**NeMo Guardrails**: reglas Colang en `rails.co`" | Existen `config/guardrails/rails.co` y `config.yml`, pero **ningún código los carga** (no hay `LLMRails` ni `RailsConfig`). Solo corren las 3 funciones de `tools/guards.py`. |
| "**NeMo Customizer** (SFT/LoRA)" | `scripts/export_nemo_sft.py` solo **exporta un JSONL**; no llama a ningún servicio. El LoRa real se entrena en local con PEFT. |
| "**NeMo Retriever**" / `health.capabilities.nemo_retriever: true` | Es una bandera fija en `/health`. La consulta del RAG usa `all-MiniLM-L6-v2` local; el reranker NVIDIA es condicional. |
| "969 fragmentos oficiales" en FAISS | El código habla de **934 fragmentos** (`conocimiento.jsonl`), que están en `back/app/datos/`. Los archivos que el RAG del enjambre espera (`enjambre_agentes/data/Embeddings/datos/*`, `data/vectorstores/faiss/`) **no están versionados**. |
| "Memoria persistente" | El checkpointer es `MemorySaver` (RAM): se pierde al reiniciar. |
| "Orquestación: salida a `END` para baja latencia" | Existe, pero el supervisor reenvía entre agentes hasta 6 iteraciones; el tiempo de respuesta puede ser largo (la app usa 90 s). |
| La app tiene backend de ventas/inventario | **No**: `/productos`, `/ventas`, `/inventario/altas` no los sirve ningún módulo. |
| El enjambre usa el modelo de visión entrenado | **No**: sus herramientas llaman a NIM Vision (nube). El ONNX solo lo sirven las rutas `/vision/*`. |
| "Pagos digitales / OCR de tickets" reales | `POST /vision/receipt-ocr` devuelve datos **simulados** (`simulacion: true`). |

---

## 10. Guía rápida para otros agentes de IA

1. **Antes de proponer algo**, confirma la ruta o función en el código; no asumas lo que diga un README.
2. **No mezcles visiones:** la foto de un producto para vender/dar de alta va a `/vision/*` (ONNX); la foto que se le muestra al agente del Asistente va a `/imagen` (NIM).
3. **Contratos de la app:** toda respuesta se valida con `zod` en `front/src/api/esquemas.ts`; cambia ahí primero si extiendes un contrato.
4. **No rompas el original:** las integraciones nuevas van detrás de flags (`EXPO_PUBLIC_*`) y en archivos nuevos o con ramas `if (flag)`.
5. **Seguridad de datos:** no envíes tarjeta, CLABE, NIP ni claves al servidor; el cliente ya los bloquea y el back/enjambre también los filtra.
6. **Archivos clave:** `enjambre_agentes/api.py` (API), `agents/graph.py` (grafo + HITL), `config/models.py` (modelos), `tools/vision_nim.py`, `back/vision/{modelo,router}.py`, `back/app/main.py`, `front/src/api/{cliente,esquemas,enjambre,asistente,vision}.ts`.
