# ⚡ QuickStart - 5 Minutos al Sistema Funcionando

---

## 🎯 Objetivo
Tener el sistema ejecutándose en **menos de 5 minutos**.

---

## 📋 Pre-requisitos (1 min)

✅ **Python 3.11+** instalado → `python --version`  
✅ **uv** instalado → `pip install uv`  
✅ **Al menos 1 API key** de:
   - [NVIDIA NIM](https://build.nvidia.com/) (recomendado)
   - [Gemini](https://aistudio.google.com/app/apikey)
   - [Groq](https://console.groq.com/keys)
   - O usar **Ollama local** (sin API key)

---

## 🚀 Instalación (2 min)

```bash
# 1. Navegar al directorio
cd tiendita-ia/enjambre_agentes

# 2. Instalar dependencias (uv es ultra rápido)
uv sync

# 3. Configurar API key
cp .env.example .env
nano .env  # Pegar tu API key (ver abajo)
```

### Configuración mínima en `.env`:
```env
DEFAULT_LLM_PROVIDER=NVIDIA
NVIDIA_API_KEY=nvapi-XXXX...
```

O si usas Gemini:
```env
DEFAULT_LLM_PROVIDER=Gemini
GEMINI_API_KEY=AIzaSyXXXX...
```

O si usas Ollama local:
```env
DEFAULT_LLM_PROVIDER=Ollama
# No necesita API key
```

---

## ✅ Verificar (30 seg)

```bash
uv run python check_setup.py
```

**Deberías ver:**
```
✓ Python >= 3.11
✓ Módulos importados correctamente
✓ Proveedor LLM configurado
✓ Grafo compilado con 8 nodos
✓ 17 herramientas MCP exportadas

✓ Todos los chequeos pasaron. El entorno está listo.
```

---

## 🎮 Ejecutar (30 seg)

### Opción A: CLI Interactivo
```bash
./start_cli.sh
```

**Prueba:**
```
🤖 > ¿Cuánto tengo de Coca-Cola?
🤖 > /pos
🤖 > /ayuda
```

### Opción B: API REST
```bash
./start_api.sh
```

Abre: **http://localhost:8000/docs**

---

## 🎯 Test Rápido

```bash
# Ejecutar suite de tests
uv run python test_suite.py
```

---

## 🆘 Problemas?

### "ModuleNotFoundError"
```bash
uv sync --reinstall
```

### "API key not found"
```bash
# Verifica que .env tenga la variable correcta
cat .env | grep API_KEY
```

### Sin colores en CLI
```bash
uv pip install rich
```

---

## 📚 Siguiente Paso

Lee la [**Guía Completa**](SETUP.md) para:
- Detalles de cada proveedor LLM
- Ejemplos de uso avanzados
- Integración con tu aplicación

---

## 🎉 ¡Listo!

Ya tienes el sistema funcionando. Disfruta explorando los 6 agentes especializados y el flujo HITL.
