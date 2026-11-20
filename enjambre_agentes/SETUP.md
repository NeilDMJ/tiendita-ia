# 🚀 Guía de Instalación y Configuración Rápida

Esta guía te llevará paso a paso desde cero hasta tener el sistema funcionando.

---

## ✅ Prerequisitos

1. **Python 3.11+** instalado
   ```bash
   python --version  # Debe ser >= 3.11
   ```

2. **uv** (gestor de paquetes ultrarrápido)
   ```bash
   # Instalar uv si no lo tienes
   pip install uv
   
   # O en Linux/macOS con curl
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **API Key** de al menos uno de estos proveedores:
   - [NVIDIA NIM](https://build.nvidia.com/) (recomendado, gratis con límites generosos)
   - [Google Gemini](https://aistudio.google.com/app/apikey) (gratis)
   - [Groq](https://console.groq.com/keys) (gratis, muy rápido)
   - [Cohere](https://dashboard.cohere.com/api-keys)
   - Ollama Local (no requiere API key, instalar desde [ollama.com](https://ollama.com))

---

## 📦 Paso 1: Instalar Dependencias

```bash
# Navegar al directorio del proyecto
cd tiendita-ia/enjambre_agentes

# Sincronizar dependencias con uv (crea .venv automáticamente)
uv sync

# O si prefieres usar pip tradicional
uv pip install -r requirements.txt
```

**Tiempo estimado:** 30-60 segundos (uv es muy rápido)

---

## 🔑 Paso 2: Configurar Variables de Entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar con tu editor favorito
nano .env
# o
code .env
# o
vim .env
```

**Configuración mínima requerida:**

```env
# Proveedor LLM por defecto
DEFAULT_LLM_PROVIDER=NVIDIA

# API Key del proveedor (elige uno)
NVIDIA_API_KEY=nvapi-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# o
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# o
GROQ_API_KEY=gsk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

> 💡 **Tip:** Si usas Ollama local, no necesitas API key. Solo ajusta `DEFAULT_LLM_PROVIDER=Ollama`

---

## ✨ Paso 3: Verificar Instalación

```bash
# Ejecutar el script de verificación
uv run python check_setup.py
```

**Deberías ver:**
```
✓ Python >= 3.11 (detectado: 3.11.x)
✓ Módulo 'state.py' importado correctamente
✓ Módulo 'models.py' importado correctamente
✓ Módulo 'guards.py' importado correctamente
✓ Módulo 'few_shot_retriever.py' importado correctamente
✓ Módulo 'tools_bridge.py' importado correctamente
✓ Módulo 'graph.py' importado correctamente

── Proveedores LLM Configurados ──
✓ NVIDIA NIM configurado
...

✓ Todos los chequeos pasaron. El entorno está listo.
```

Si algo falla, el script te dirá exactamente qué corregir.

---

## 🎮 Paso 4A: Ejecutar CLI Interactivo (Recomendado para comenzar)

```bash
# Usando el script auxiliar (más fácil)
./start_cli.sh

# O directamente con uv
uv run python cli_tester.py
```

**Comandos dentro del CLI:**
- Escribe tu consulta en español: `"¿Cuánto me queda de Coca-Cola?"`
- `/pos` → Simula cobro en punto de venta con cámara
- `/ticket` → Simula lectura OCR de factura
- `/pago` → Simula error en pantalla de pago móvil
- `/estado` → Ver estado interno de la sesión
- `/ayuda` → Lista todos los comandos
- `/salir` → Cerrar

---

## 🌐 Paso 4B: Ejecutar API REST

```bash
# Usando el script auxiliar
./start_api.sh

# O directamente con uvicorn
uv run uvicorn api:app --reload --port 8000
```

Luego abre en tu navegador:
- 📄 **Documentación interactiva (Swagger):** http://localhost:8000/docs
- 📗 **Documentación alternativa (ReDoc):** http://localhost:8000/redoc
- 🔍 **Health check:** http://localhost:8000/health

**Endpoints principales:**
- `POST /orchestrate` → Ejecutar flujo multiagente (batch)
- `POST /orchestrate/stream` → Streaming en tiempo real (SSE)
- `POST /orchestrate/resume` → Reanudar tras confirmación HITL
- `GET /mcp/tools` → Exportar herramientas en formato MCP

---

## 🧪 Paso 5: Ejecutar Tests (Opcional)

```bash
# Suite completa de tests
uv run python test_suite.py
```

Valida:
- ✓ Tipado Pydantic v2
- ✓ 17 herramientas MCP
- ✓ Validación de grounding (guards)
- ✓ Inyección few-shot
- ✓ Flujo POS con HITL
- ✓ Clasificación OCR
- ✓ Tutor UI (máx 2 oraciones)
- ✓ Reporte estratégico (9 secciones)
- ✓ Integración con asistente de catálogo

---

## 🎯 Ejemplos de Uso Rápido

### Consulta Simple (CLI)
```bash
$ uv run python cli_tester.py

🤖 Tiendita IA > ¿Cuánto tengo de leche?
🤖 Respuesta: Tienes 12 piezas de Leche Lala 1L en stock (mínimo: 6).
```

### Cobro POS (API)
```bash
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "event_source": "vision_api",
    "vision_payload": {
      "endpoint": "/pos-checkout",
      "items": [
        {"sku": "COCA-600", "cantidad": 2},
        {"sku": "LALA-1L", "cantidad": 1}
      ]
    }
  }'
```

---

## 🔧 Solución de Problemas Comunes

### Error: `ModuleNotFoundError: No module named 'langgraph'`
```bash
# Reinstalar dependencias
uv sync --reinstall
```

### Error: `ValueError: No se encontró NVIDIA_API_KEY`
```bash
# Verificar que .env esté en el directorio correcto
ls -la .env

# Verificar que las variables se carguen
source .env  # Linux/macOS
# o editar directamente .env y relanzar
```

### Error: `ImportError: langchain_nvidia_ai_endpoints`
```bash
# Instalar dependencia específica
uv pip install langchain-nvidia-ai-endpoints
```

### CLI no tiene colores (Rich)
```bash
# Instalar rich
uv pip install rich
```

---

## 📚 Siguiente Paso

Lee el [README.md](README.md) completo para:
- Arquitectura detallada del grafo
- Esquema de base de datos PostgreSQL
- Catálogo completo de las 17 herramientas
- Ejemplos avanzados de uso
- Integración con el asistente de catálogo

---

## 🆘 Soporte

Si encuentras problemas:
1. Ejecuta `uv run python check_setup.py` y revisa el output
2. Verifica que tu `.env` tenga al menos un proveedor configurado
3. Revisa los logs en la terminal
4. Consulta la documentación interactiva en `/docs` si usas la API
