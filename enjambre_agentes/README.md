# Tiendita IA: Ecosistema Comercial Multimodal

Ecosistema comercial con visión artificial, orquestación multiagente en **LangGraph** y tecnologías **NVIDIA (NIM / NeMo)**, diseñado para modernizar y optimizar tiendas de abarrotes y comercio minorista.

---

## Características Principales

- **Orquestación Multiagente en LangGraph:** 1 Supervisor Maestro + 6 Especialistas coordinados mediante razonamiento puro sin reglas rígidas de palabras clave.
- **Microservicios NVIDIA NIM:** Inferencia con `nvidia/nemotron-3-super-120b-a12b` y `nvidia/llama-3.1-nemotron-nano-8b-v1`.
- **NeMo Retriever:** Embeddings `nvidia/nv-embedqa-e5-v5` + PostgreSQL vectorial (`pgvector`) + Reranker `nvidia/nv-rerankqa-mistral-4b-v3`.
- **NeMo Guardrails:** Reglas Colang funcionales en `config/guardrails/rails.co` para prevención de inyecciones de prompt, protección de costos confidenciales y concisión en mostrador.
- **Human-in-the-Loop (HITL):** Puerta de aprobación `approval_gate` para acciones sensibles en inventario, ventas y publicidad.
- **Soporte de Fine-Tuning:** Recolección de feedback para entrenamiento de adaptadores LoRA con NeMo Customizer (`scripts/export_nemo_sft.py`).

---

## Estructura del Proyecto

```
enjambre_agentes/
├── agents/             # 1 Supervisor + 6 Especialistas + Grafo LangGraph
├── schemas/            # Contratos Pydantic de estado, visión, finanzas y reportes
├── tools/              # Herramientas de visión, BD, RAG NeMo, POS e inventario
├── config/             # Modelos NVIDIA NIM, Ollama, keys y NeMo Guardrails
├── scripts/            # CLI interactivo, exportador NeMo SFT y generador de diagramas
├── tests/              # Banco de pruebas test_cases.json
├── api.py              # API REST FastAPI con SSE y control HITL
└── main.py             # Entrada principal por línea de comandos
```

---

## Puesta en Marcha

### 1. Variables de Entorno
Copia el archivo `.env.example` hacia `.env` y configura tus credenciales:
```bash
cp .env.example .env
```

### 2. Ejecución de la API REST
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 3. CLI Interactivo y Banco de Pruebas
```bash
python scripts/cli_tester.py
```
Comandos disponibles en el CLI:
- `/test`: Ejecuta los 5 escenarios base de `tests/test_cases.json`.
- `/modelo`: Consulta y cambia dinámicamente modelos en vivo.
- `/pos`: Simula checkout visual en caja.
- `/ticket`: Clasifica un comprobante de compra (`inversion_inventario` vs `gasto_operativo`).
- `/pago`: Asistencia rápida de pantalla en máximo 2 oraciones.
- `/cron`: Alertas de caducidad y creación de video comercial 9:16.
