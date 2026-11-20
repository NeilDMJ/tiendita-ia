# Tiendita IA

Ecosistema móvil y multiagente para digitalizar **tiendas de abarrotes y microcomercios en México**: cobra y registra productos con la cámara del celular, controla inventario y caducidades, consulta finanzas reales, genera promociones y acompaña cobros digitales (**CoDi, SPEI y DiMo**).

---

## ¿Qué hace?

- **Cobro y alta por cámara (`vision/` + `back/vision/`):** clasificador **YOLO11n-cls** (95.26 % exactitud top-1, optimizado con **NVIDIA TensorRT** y servido en ONNX a ~5–8 ms/foto) sin necesidad de lector de códigos.
- **Enjambre de 7 agentes (`enjambre_agentes/`):** orquestado con **LangGraph** y **Modo Thinking** visible en la app móvil y CLI:
  - `supervisor` (enruta por intención), `control` (inventario/caducidades), `vendedor` (mostrador POS), `analista` (finanzas solo lectura), `investigador` (mercado), `publicista` (promociones y video 9:16) y `tutor_ui` (pagos CoDi/SPEI/DiMo en ≤ 2 oraciones).
- **Control Humano (HITL) y privacidad:** las acciones críticas (promociones, ventas, altas) piden aprobación antes de escribir en PostgreSQL; el teléfono bloquea NIP/claves/tarjetas antes de enviarlas.
- **Pagos digitales MX + LoRA local:** RAG dual (**FAISS + `pgvector`**) sobre guías oficiales de Banxico y adaptador LoRA propio (**`tiendita-lora-v1`** en Ollama, entrenado en GPU NVIDIA RTX 5060).
- **App móvil accesible (`front/`):** React Native + Expo con modo claro/oscuro, accesibilidad y cola offline.

---

## Arquitectura

```text
App Móvil (Expo / React Native — front/)
   │  Cámara (/vision/*)  │  Chat Enjambre (/orchestrate, /pago)  │  Guía Bancaria (/asistente/mensaje)
   ▼
Servidor Unificado FastAPI — Puerto 8000 (enjambre_agentes/api.py)
   ├── Enjambre LangGraph (7 agentes + HITL + Modo Thinking + WebSockets)
   │     └── LLMs: NVIDIA NIM (default) con rescate automático (Groq → Cohere → Gemini → Ollama LoRA)
   ├── Visión ONNX Runtime (back/vision → vision/artefactos/v1/best.onnx)
   └── Asistente Bancario (back/app → RAG Banxico)
   ▼
Datos: PostgreSQL 16 + pgvector (tiendita-db) · FAISS · Ollama local (tiendita-lora-v1)
```

### Estructura del repositorio

| Carpeta | Responsabilidad |
|---|---|
| `front/` | App móvil Expo (Cobrar, Inventario, Historial, Asistente con Modo Thinking). |
| `enjambre_agentes/` | Orquestador LangGraph, API unificada (puerto `8000`), CLI, RAG dual y scripts de entrenamiento LoRA. |
| `back/` | Base de datos PostgreSQL + `pgvector` (`docker-compose.yml`), servicio `/vision/*` y asistente bancario `/asistente/mensaje`. |
| `vision/` | Entrenamiento, evaluación y exportación ONNX / NVIDIA TensorRT de YOLO11n-cls (`artefactos/v1/`). |
| `docs/` | Catálogo demo, documentación UI/UX y diseño de orquestación. |

---

## Cómo correr el proyecto en local

### Requisitos previos
- **Docker** (PostgreSQL 16 + `pgvector`), **Python 3.12 + `uv`**, **Node.js 20+**.
- Llaves de API en `enjambre_agentes/.env` (`NVIDIA_API_KEY`, `DATABASE_URL` y respaldos opcionales `GROQ_API_KEY`, `COHERE_API_KEY`, `GEMINI_API_KEY`).
- *(Opcional)* **Ollama** local para ejecutar el modelo LoRA (`tiendita-lora-v1`).

### 1. Levantar la base de datos (`tiendita-db`)
```bash
cd back
cp .env.example .env   # ajustar DB_PASSWORD si aplica
docker compose up -d
```

### 2. Levantar el servidor unificado (Agentes + Visión + Asistente Bancario en puerto `8000`)
```bash
cd enjambre_agentes
cp .env.example .env   # configurar API keys y DATABASE_URL
uv sync

# Modo local / Wi-Fi LAN (http://<TU_IP>:8000):
uv run python main.py --serve

# O con túnel público HTTPS (para celulares en otra red):
uv run python main.py --serve --tunnel
```
Verificación rápida:
- Salud general y BD: `http://localhost:8000/health`
- Salud de visión ONNX: `http://localhost:8000/vision/salud`
- Swagger interactivo: `http://localhost:8000/docs`

### 3. Correr la app móvil (`front/`)
```bash
cd front
npm install
cp .env.example .env
```
Configura `front/.env`:
```env
EXPO_PUBLIC_API_URL=http://<TU_IP_LOCAL>:8000   # o URL https:// del túnel
EXPO_PUBLIC_USE_MOCKS=1
EXPO_PUBLIC_VISION_REAL=1
EXPO_PUBLIC_ASISTENTE_REAL=1
EXPO_PUBLIC_ASISTENTE_ENJAMBRE=1
```
Arranca Expo:
```bash
npx expo start -c                # misma red Wi-Fi o web (presiona 'w')
npx expo start -c --tunnel ngrok # celulares fuera de tu Wi-Fi
```

### 4. *(Opcional)* CLI interactivo y LoRA local
```bash
# Probar los 7 agentes directo en consola:
cd enjambre_agentes
uv run python main.py

# Activar el modelo LoRA entrenado en Ollama para pagos (tutor_ui):
uv run python main.py --agent-brain tutor_ui=Ollama:tiendita-lora-v1
```

---

## Documentación detallada

- **Enjambre, API, CLI y replicación LoRA:** [`enjambre_agentes/README.md`](./enjambre_agentes/README.md) y [`enjambre_agentes/docs/README.md`](./enjambre_agentes/docs/README.md)
- **Explicación sin tecnicismos (negocio + NVIDIA + LoRA):** [`enjambre_agentes/docs/10_GUIA_EXPLICACION_SIMPLE.md`](./enjambre_agentes/docs/10_GUIA_EXPLICACION_SIMPLE.md)
- **Reporte técnico LoRA (GPU RTX 5060):** [`enjambre_agentes/docs/09_REPORTE_TECNICO_LORA.md`](./enjambre_agentes/docs/09_REPORTE_TECNICO_LORA.md)
- **Modelo de visión (YOLO11n-cls + TensorRT):** [`vision/README.md`](./vision/README.md) y [`back/vision/README.md`](./back/vision/README.md)
