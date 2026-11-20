# 📚 Índice de Documentación - Enjambre Agentes

Guía rápida para navegar toda la documentación del sistema.

---

## 🚀 Para Comenzar AHORA

| Documento | Para Qué | Tiempo |
|-----------|----------|--------|
| **[QUICKSTART.md](QUICKSTART.md)** | ⚡ Sistema funcionando en 5 minutos | 5 min |
| **[SETUP.md](SETUP.md)** | 📖 Instalación paso a paso desde cero | 10 min |
| **[API_KEYS.md](API_KEYS.md)** | 🔑 Cómo obtener API keys de cada proveedor | 5 min |

---

## 📖 Documentación Principal

### [README.md](README.md) - Referencia Técnica Completa
**Contenido:**
- ✅ Visión general y arquitectura
- ✅ Diagrama del grafo multiagente (Mermaid)
- ✅ Esquema de base de datos PostgreSQL
- ✅ Catálogo de las 17 herramientas tipadas
- ✅ Integración del asistente de catálogo
- ✅ Ejemplos funcionales de uso
- ✅ Suite de pruebas y validación

**Lee esto cuando:** Necesites entender cómo funciona el sistema internamente.

---

## 🎯 Guías de Instalación

### [SETUP.md](SETUP.md) - Guía Completa de Instalación
**Contenido:**
- ✅ Prerequisitos detallados
- ✅ Instalación de dependencias con `uv`
- ✅ Configuración de variables de entorno
- ✅ Verificación de instalación
- ✅ Tres formas de ejecución (CLI, API, Programática)
- ✅ Solución de problemas comunes

**Lee esto cuando:** Es tu primera vez instalando el sistema.

---

### [QUICKSTART.md](QUICKSTART.md) - Inicio Rápido
**Contenido:**
- ✅ Sistema funcionando en 5 minutos
- ✅ Pasos mínimos esenciales
- ✅ Configuración mínima de `.env`
- ✅ Test rápido

**Lee esto cuando:** Quieres probar el sistema lo más rápido posible.

---

## 🔑 Configuración de API Keys

### [API_KEYS.md](API_KEYS.md) - Guía de Proveedores LLM
**Contenido:**
- ✅ Comparativa de proveedores (velocidad, costo, límites)
- ✅ Instrucciones paso a paso para:
  - NVIDIA NIM (Llama 3.3 70B)
  - Google Gemini (Gemini 2.5 Flash)
  - Groq (inferencia ultra-rápida)
  - Cohere (enterprise)
  - Ollama (100% local)
- ✅ Buenas prácticas de seguridad
- ✅ Solución de problemas de autenticación

**Lee esto cuando:** Necesites configurar o cambiar tu proveedor LLM.

---

## 🔧 Referencia de Cambios

### [CHANGELOG.md](CHANGELOG.md) - Historial de Cambios
**Contenido:**
- ✅ Resumen de archivos corregidos
- ✅ Nuevos archivos creados
- ✅ Dependencias añadidas
- ✅ Estado final del sistema
- ✅ Instrucciones de ejecución

**Lee esto cuando:** Quieras saber qué se cambió exactamente en esta revisión.

---

## 🛠️ Herramientas Auxiliares

### Scripts de Shell

| Script | Función | Uso |
|--------|---------|-----|
| **start_cli.sh** | Inicia el CLI interactivo | `./start_cli.sh` |
| **start_api.sh** | Inicia la API REST | `./start_api.sh` |
| **check_setup.py** | Verifica el entorno | `uv run python check_setup.py` |

### Archivos de Configuración

| Archivo | Propósito |
|---------|-----------|
| `.env.example` | Plantilla de variables de entorno |
| `pyproject.toml` | Dependencias para `uv` |
| `requirements.txt` | Dependencias para `pip` |

---

## 📂 Estructura del Código Fuente

### Núcleo del Sistema

| Archivo | Responsabilidad |
|---------|-----------------|
| **state.py** | Estado multimodal (`OrchestratorState`) y contratos Pydantic |
| **models.py** | Fábrica de LLMs (NVIDIA, Gemini, Groq, Cohere, Ollama) |
| **guards.py** | Validación anti-alucinaciones (`enforce_db_grounding`) |
| **few_shot_retriever.py** | Inyección dinámica de ejemplos por rol |
| **tools_bridge.py** | 17 herramientas tipadas + exportación MCP |
| **graph.py** | Grafo LangGraph (6 agentes + Supervisor + HITL) |

### Interfaces Externas

| Archivo | Responsabilidad |
|---------|-----------------|
| **api.py** | API REST FastAPI (6 endpoints) |
| **cli_tester.py** | CLI interactivo con comandos slash |
| **test_suite.py** | Suite de tests unitarios e integración |

---

## 🎓 Flujo de Lectura Sugerido

### Si eres nuevo:
1. **[QUICKSTART.md](QUICKSTART.md)** → Instala y ejecuta en 5 min
2. **[README.md](README.md)** → Entiende la arquitectura
3. **[API_KEYS.md](API_KEYS.md)** → Configura otros proveedores

### Si eres desarrollador:
1. **[README.md](README.md)** → Arquitectura completa
2. **[SETUP.md](SETUP.md)** → Instalación detallada
3. **Código fuente** → `state.py`, `graph.py`, `tools_bridge.py`
4. **[test_suite.py](test_suite.py)** → Ejemplos de uso y validación

### Si vas a producción:
1. **[SETUP.md](SETUP.md)** → Configuración completa
2. **[API_KEYS.md](API_KEYS.md)** → Seguridad y buenas prácticas
3. **[README.md](README.md)** → Sección de despliegue
4. **[api.py](api.py)** → Endpoints y contratos

---

## 🔍 Búsqueda Rápida

### "¿Cómo hago X?"

| Pregunta | Dónde Buscar |
|----------|--------------|
| ¿Cómo instalo el sistema? | [SETUP.md](SETUP.md) |
| ¿Cómo obtengo una API key? | [API_KEYS.md](API_KEYS.md) |
| ¿Cómo ejecuto el CLI? | [QUICKSTART.md](QUICKSTART.md) |
| ¿Cómo funciona el grafo? | [README.md](README.md) → Sección 2 |
| ¿Qué herramientas hay? | [README.md](README.md) → Sección 4 |
| ¿Cómo funciona HITL? | [README.md](README.md) → Sección 1 + `graph.py` |
| ¿Cómo añado un agente? | [graph.py](graph.py) + [state.py](state.py) |
| ¿Cómo añado una herramienta? | [tools_bridge.py](tools_bridge.py) |
| ¿Cómo cambio el LLM? | [models.py](models.py) + `.env` |
| ¿Cómo funciona el grounding? | [guards.py](guards.py) |

---

## 🆘 Soporte

Si tienes problemas:

1. **Verifica tu instalación:**
   ```bash
   uv run python check_setup.py
   ```

2. **Revisa la solución de problemas:**
   - [SETUP.md](SETUP.md) → Sección "Solución de Problemas"
   - [API_KEYS.md](API_KEYS.md) → Sección "Problemas Comunes"

3. **Consulta los logs:**
   - CLI: Error se muestra directamente en terminal
   - API: Logs en la consola de `uvicorn`

4. **Ejecuta los tests:**
   ```bash
   uv run python test_suite.py
   ```

---

## 📊 Métricas del Sistema

- **Módulos Core:** 6 archivos Python
- **Agentes Especializados:** 6 + 1 Supervisor
- **Herramientas Tipadas:** 17 (8 Control + 3 Vendedor + 2 Analista + 2 Investigador + 1 Publicista + 1 Tutor UI)
- **Endpoints API:** 6 (orchestrate, stream, resume, state, tools, health)
- **Proveedores LLM:** 5 (NVIDIA, Gemini, Groq, Cohere, Ollama)
- **Líneas de Código:** ~3,000 (sin contar tests)
- **Tests Unitarios:** Suite completa en `test_suite.py`

---

## 🎯 Siguiente Paso

**Comienza aquí:** [QUICKSTART.md](QUICKSTART.md)

¡Que disfrutes el sistema! 🚀
