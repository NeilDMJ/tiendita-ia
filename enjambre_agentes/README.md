# Tiendita IA — Enjambre Multiagente Comercial Multimodal

Ecosistema comercial con visión artificial, orquestación multiagente en **LangGraph**, base de datos **PostgreSQL (`tiendita-db` + `pgvector`)**, **RAG Dual especializado en CoDi / SPEI / DiMo** y tecnologías **NVIDIA (NIM / NeMo)**.

---

## Capacidades Principales

- **Orquestación Multiagente Optimizada (LangGraph):** 1 Supervisor Maestro + 6 Especialistas (`control`, `vendedor`, `analista`, `investigador`, `publicista`, `tutor_ui`) con razonamiento puro, encadenamiento compuesto sanitizado y salida directa a `END` para baja latencia.
- **Stack NVIDIA NIM / NeMo (100% NVIDIA por defecto):**
  - **LLMs NIM:** `nvidia/nemotron-3-super-120b-a12b` (`supervisor`, `analista`, `investigador`) y `nvidia/llama-3.1-nemotron-nano-8b-v1` (`control`, `vendedor`, `publicista`, `tutor_ui`), con cambio individual en vivo (`set_agent_brain`) y rescate silencioso `.with_fallbacks()` + Circuit Breaker (`Gemini → Groq → Cohere → Ollama`).
  - **NIM Vision (VL):** procesamiento real de imágenes desde disco o cámara móvil (`/imagen`, `/catalog-scan`, `/pos-checkout`, `/receipt-ocr`).
  - **NeMo Retriever + RAG Dual:** 969 fragmentos oficiales de **CoDi, SPEI y DiMo** (`data/Embeddings/datos/`) indexados en `FAISS` (`data/vectorstores/faiss/`) y sincronizados en PostgreSQL `pgvector`.
  - **NeMo Guardrails:** reglas Colang en `config/guardrails/rails.co` + guardias en `tools/guards.py`.
  - **NeMo Customizer (SFT / LoRA):** recolección de feedback HITL y exportación JSONL (`scripts/export_nemo_sft.py`).
- **Base de Datos Real (`tiendita-db`):** pool thread-safe sobre PostgreSQL 16 consultando vistas oficiales (`v_inventario`, `v_por_caducar`, `v_stock_bajo`, `v_margen_producto`, `v_flujo_caja`, `v_ventas_dia`, `v_coocurrencia`) y `registrar_venta(jsonb)`.
- **Human-in-the-Loop (HITL) Real:** pausa en `approval_gate` antes de confirmar `COMMIT` sensibles en PostgreSQL (disponible en CLI, REST y WebSocket bidireccional).

---

## Guía Paso a Paso para Replicar Este Proyecto

### 1. Requisitos Previos

- **Python 3.12+** y **[`uv`](https://docs.astral.sh/uv/)** para gestión de dependencias.
- **PostgreSQL 16 + `pgvector`** corriendo en `localhost:5432` (contenedor `tiendita-db` del proyecto backend).
- **Llave de API de NVIDIA** (`NVIDIA_API_KEY`) — y opcionalmente `GOOGLE_API_KEY`, `GROQ_API_KEY`, `COHERE_API_KEY` y `TAVILY_API_KEY` para respaldos automáticos e investigación web.
- **Opcional (para correr o entrenar LoRA en local):** **[Ollama](https://ollama.com/)** instalado en `localhost:11434` y una **GPU NVIDIA con CUDA** (probado en RTX 5060 de 8 GB VRAM).

---

### 2. Correr el Enjambre en Local (Base de Datos + CLI)

```bash
# 1. Ir al directorio del enjambre
cd enjambre_agentes

# 2. Configurar variables de entorno (editar .env con tus llaves y DATABASE_URL)
cp .env.example .env

# 3. Instalar dependencias reproducibles con uv
uv sync

# 4. Verificar que PostgreSQL (tiendita-db) y las herramientas respondan en vivo
uv run python scripts/test_tools.py

# 5. Lanzar el CLI interactivo en local
uv run python main.py
```

También puedes arrancar el CLI asignando modelos específicos a cualquier agente desde el inicio:
```bash
uv run python main.py \
  --agent-brain tutor_ui=Ollama:tiendita-lora-v1 \
  --agent-brain vendedor=Gemini:gemini-flash-lite-latest \
  --agent-brain investigador=Groq:openai/gpt-oss-120b
```

#### Comandos dentro del CLI Interactivo
- `<texto libre>`: consulta inventario real, ventas, finanzas o investigación de mercado.
- `/cerebro <agente> <proveedor> <modelo>` · `/cerebros` · `/reset-cerebros`: cambia modelos en caliente sin reiniciar.
- `/imagen <ruta.jpg|png> <catalog|pos|ticket>`: análisis multimodal real con NVIDIA NIM Vision.
- `/pago <codi|spei|dimo> <pantalla> <paso> [error_code]`: asistencia del `tutor_ui` en máximo 2 oraciones respaldada por el RAG oficial.
- `/rag <consulta>`: búsqueda directa con puntajes de relevancia sobre el índice CoDi/SPEI/DiMo (`FAISS` / `pgvector`).
- `/cron` · `/estado` · `/ayuda` · `/salir`.

---

### 3. Replicar y Levantar la API (Local, Wi-Fi/LAN e Internet)

#### A) En la PC servidor (donde corren `enjambre_agentes` y `tiendita-db`)
```bash
# Modo local y red Wi-Fi / LAN (escucha en 0.0.0.0:8000 y detecta tu IP local automáticamente)
uv run python main.py --serve

# Exponer también a Internet mediante túnel SSH nativo (sin instalar ngrok):
uv run python main.py --serve --tunnel               # localhost.run (recomendado)
uv run python main.py --serve --tunnel pinggy        # puerto 443 si el puerto 22 está bloqueado
uv run python main.py --serve --tunnel vps           # usa SSH_VPS_TARGET definido en .env
```

Si otra PC o celular en el mismo Wi-Fi no alcanza el puerto `8000`, abre el puerto en el firewall del servidor:
```bash
# Ubuntu / Debian (ufw):
sudo ufw allow 8000/tcp

# Fedora / RHEL (firewalld):
sudo firewall-cmd --add-port=8000/tcp --permanent && sudo firewall-cmd --reload
```
> **Si corres en Windows con WSL2:** abre PowerShell como Administrador y ejecuta:
> `New-NetFirewallRule -DisplayName "Tiendita IA API 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow`

> **Seguridad opcional:** define `TIENDITA_API_KEY=<tu_clave>` en `.env` para exigir `X-API-Key` en REST (excepto `/health` y `/docs`) y `?api_key=<tu_clave>` en WebSockets. Si queda vacía, la API opera abierta para pruebas locales.

#### B) Probar la API desde la misma PC, otra PC en LAN o por Túnel Público
Sustituye `<BASE_URL>` por `http://localhost:8000`, `http://192.168.1.64:8000` o tu URL pública `https://<subdominio>.lhr.life`:

- **Swagger interactivo (navegador):** `<BASE_URL>/docs`
- **WebSocket bidireccional con HITL:** `ws://<HOST>:8000/ws/orchestrate` (o `wss://<subdominio>.lhr.life/ws/orchestrate`)

**En Linux / macOS / Git Bash (`curl`):**
```bash
# 1. Verificar salud y conexión a PostgreSQL
curl <BASE_URL>/health

# 2. Consultar al enjambre
curl -X POST <BASE_URL>/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"input_text": "¿Cuáles son los 3 productos más vendidos?", "event_source": "chat"}'

# 3. Probar asistencia de pagos digitales (CoDi / SPEI / DiMo)
curl -X POST <BASE_URL>/pago \
  -H "Content-Type: application/json" \
  -d '{"metodo_pago": "codi", "pantalla": "cobro_qr", "paso": 2, "error_code": "QR_EXPIRADO"}'

# 4. Probar suite automatizada REST + WebSocket + HITL
uv run python -m scripts.test_client --url <BASE_URL> --mode all
```

**En Windows PowerShell (evita errores de comillas de `curl`):**
```powershell
Invoke-RestMethod -Uri "<BASE_URL>/pago" -Method Post -ContentType "application/json" `
  -Body '{"metodo_pago":"codi","pantalla":"cobro_qr","paso":2,"error_code":"QR_EXPIRADO"}'
```

---

### 4. Replicar el Entrenamiento LoRA en Local y Registrarlo en Ollama

El entrenamiento LoRA es completamente reproducible en una GPU NVIDIA local (probado en **RTX 5060 8 GB**, tiempo total ~63 s, VRAM pico ~4.2 GB).

#### Paso 1 — Instalar dependencias de entrenamiento en `.venv` (sin modificar `pyproject.toml`)
```bash
# Instala PyTorch con CUDA (si aún no está instalado) + PEFT/Accelerate + herramientas GGUF
uv pip install --python .venv/bin/python peft accelerate gguf sentencepiece
```

#### Paso 2 — Construir el dataset de entrenamiento y evaluación
Genera 118 ejemplos reales de la tiendita (guías oficiales de CoDi/SPEI/DiMo, inventario, POS, guardrails y feedback HITL):
```bash
.venv/bin/python scripts/build_lora_dataset.py
```
Produce:
- `data/hitl_feedback/tiendita_lora_train.jsonl` (entrenamiento)
- `data/hitl_feedback/tiendita_lora_eval.jsonl` (validación)
- `data/hitl_feedback/nemo_customizer_train.jsonl` (listo también para **NVIDIA NeMo Customizer**)

#### Paso 3 — Entrenar el adaptador LoRA en tu GPU NVIDIA
Entrena un adaptador LoRA (`r=16`, `alpha=32`, `bfloat16`, 4 épocas) sobre `Qwen/Qwen2.5-1.5B-Instruct` y evalúa automáticamente antes vs. después:
```bash
.venv/bin/python scripts/train_lora_local.py
```
Guarda en `data/loras/tiendita_lora_v1/`:
- `adapter_model.safetensors` y `adapter_config.json` (pesos del adaptador LoRA, ~70 MB)
- `training_metrics.json` (curva de pérdida, perplejidad, velocidad y uso de VRAM)
- `before_after_eval.json` (comparativa cualitativa antes y después del entrenamiento)

#### Paso 4 — Exportar a GGUF y registrar el modelo en Ollama local (`tiendita-lora-v1`)

**Opción A — Replicar la fusión y conversión GGUF desde cero:**
```bash
# 1. Descargar solo el conversor Python oficial de llama.cpp
git clone --depth 1 --filter=blob:none --sparse https://github.com/ggml-org/llama.cpp.git /tmp/llama_conv
git -C /tmp/llama_conv sparse-checkout set --no-cone /convert_hf_to_gguf.py /conversion/ /gguf-py/

# 2. Fusionar LoRA + modelo base, convertir a GGUF Q8_0 (1.6 GB) y registrar en Ollama
.venv/bin/python scripts/export_lora_ollama.py \
  --model-name tiendita-lora-v1 \
  --outtype q8_0 \
  --gguf-converter /tmp/llama_conv/convert_hf_to_gguf.py
```

**Opción B — Si ya tienes `data/loras/tiendita_lora_v1/tiendita-lora-v1-q8_0.gguf`:**
```bash
.venv/bin/python scripts/export_lora_ollama.py --skip-merge --model-name tiendita-lora-v1
```

Verifica que quedó registrado y responde en tu GPU:
```bash
ollama list | grep tiendita-lora-v1
ollama run tiendita-lora-v1 "El cliente dice que el QR de CoDi expiró en el paso 2, ¿qué hago?"
```

#### Paso 5 — Conectar `tiendita-lora-v1` al enjambre (CLI o API)
```bash
# Desde el CLI interactivo:
/cerebro tutor_ui Ollama tiendita-lora-v1
/pago codi cobro_qr 2 QR_EXPIRADO

# O por API REST en caliente (sin reiniciar el servidor):
curl -X PUT http://localhost:8000/brains/tutor_ui \
  -H "Content-Type: application/json" \
  -d '{"provider": "Ollama", "model_name": "tiendita-lora-v1"}'

# Restaurar todos los agentes al perfil 100% NVIDIA NIM por defecto:
curl -X POST http://localhost:8000/brains/reset
```

---

## Documentación Completa (`docs/`)

Para documentación profunda orientada a desarrolladores, presentaciones y **agentes de IA**, consulta [`docs/README.md`](./docs/README.md):

1. [`docs/01_ARQUITECTURA_Y_ORQUESTACION.md`](./docs/01_ARQUITECTURA_Y_ORQUESTACION.md) — Grafo LangGraph, `OrchestratorState`, routers y ciclo HITL.
2. [`docs/02_CATALOGO_AGENTES.md`](./docs/02_CATALOGO_AGENTES.md) — Fichas completas de los 7 agentes, prompts, tools y guardias.
3. [`docs/03_CATALOGO_TOOLS_Y_BD.md`](./docs/03_CATALOGO_TOOLS_Y_BD.md) — Todas las `@tool`, vistas/funciones PostgreSQL y manifiesto MCP.
4. [`docs/04_MEMORIA_Y_RAG_PAGOS.md`](./docs/04_MEMORIA_Y_RAG_PAGOS.md) — Las 5 capas de memoria y RAG Dual de CoDi, SPEI y DiMo.
5. [`docs/05_STACK_NVIDIA_Y_RESILIENCIA.md`](./docs/05_STACK_NVIDIA_Y_RESILIENCIA.md) — Tecnología NVIDIA (NIM/NeMo), `ResilientChatModel` y Circuit Breaker.
6. [`docs/06_OPERACION_CLI_API_Y_EXTENSION.md`](./docs/06_OPERACION_CLI_API_Y_EXTENSION.md) — Operación CLI/API y manual para extender el enjambre.
7. [`docs/07_CONSUMO_API_LAN_Y_REMOTO.md`](./docs/07_CONSUMO_API_LAN_Y_REMOTO.md) — Guía completa de consumo LAN / Wi-Fi / App Móvil / Túnel SSH (REST, SSE y WebSocket).
8. [`docs/08_DIAGRAMA_INTERACCION_AGENTES.md`](./docs/08_DIAGRAMA_INTERACCION_AGENTES.md) — Diagramas visuales de interacción de agentes y flujos ([PNG](./docs/diagrama_agentes_tiendita_ia.png)).
9. [`docs/09_REPORTE_TECNICO_LORA.md`](./docs/09_REPORTE_TECNICO_LORA.md) — Reporte técnico con métricas reales del entrenamiento LoRA y registro en Ollama.
10. [`docs/10_GUIA_EXPLICACION_SIMPLE.md`](./docs/10_GUIA_EXPLICACION_SIMPLE.md) — **Explicación en lenguaje simple y sin tecnicismos** (qué se construyó, qué hace LoRA y cómo se usó NVIDIA).
11. [`AGENTS.md`](./AGENTS.md) y [`ARCHITECTURE_GRAPH.md`](./ARCHITECTURE_GRAPH.md) — Resumen de roles y diagrama autogenerado.
