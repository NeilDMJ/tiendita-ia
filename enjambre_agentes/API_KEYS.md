# 🔑 Guía de Obtención de API Keys

Esta guía te ayudará a obtener las API keys necesarias para los diferentes proveedores LLM.

---

## 🎯 ¿Qué proveedor elegir?

| Proveedor | Velocidad | Costo | Límites Gratuitos | Recomendado Para |
|-----------|-----------|-------|-------------------|------------------|
| **NVIDIA NIM** | ⚡⚡⚡ Muy Rápido | 💰 Gratis* | Generoso | Producción, Llama 3.3 70B |
| **Google Gemini** | ⚡⚡ Rápido | 💰 Gratis* | Muy generoso | Desarrollo, multimodal |
| **Groq** | ⚡⚡⚡⚡ Ultra Rápido | 💰 Gratis* | Moderado | Demos, prototipado |
| **Cohere** | ⚡⚡ Rápido | 💰💰 Trial + Pago | Trial limitado | Enterprise |
| **Ollama** | ⚡ Depende HW | 💰 Gratis | Sin límites | 100% local, privacidad |

\* Con límites de tasa (RPM/TPM), suficientes para desarrollo y demos.

---

## 1. NVIDIA NIM (Recomendado) 🟢

### ¿Por qué NVIDIA NIM?
- Acceso a **Llama 3.3 70B** optimizado por NVIDIA
- **Inferencia ultra-rápida** (DGX Cloud)
- Límites generosos para desarrollo
- Modelos open-source de última generación

### Pasos para obtener tu API Key:

1. **Visita:** https://build.nvidia.com/

2. **Crear cuenta:**
   - Clic en "Get Started" o "Sign In"
   - Regístrate con tu correo o cuenta de Google/GitHub

3. **Generar API Key:**
   - En el dashboard, ve a "API Keys" o haz clic en tu perfil
   - Clic en "Generate API Key"
   - **Copia la key** (empieza con `nvapi-...`)

4. **Configurar en .env:**
   ```env
   DEFAULT_LLM_PROVIDER=NVIDIA
   NVIDIA_API_KEY=nvapi-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```

5. **Modelos recomendados:**
   - `meta/llama-3.3-70b-instruct` (default, óptimo)
   - `nvidia/llama-3.1-nemotron-70b-instruct` (razonamiento)
   - `meta/llama-3.1-8b-instruct` (rápido, económico)

---

## 2. Google Gemini 🔵

### ¿Por qué Gemini?
- **Gemini 2.5 Flash** es extremadamente rápido y gratuito
- Límites generosos (1500 req/día gratis)
- Excelente soporte multimodal (imágenes, video)
- Integración nativa con Google AI Studio

### Pasos:

1. **Visita:** https://aistudio.google.com/app/apikey

2. **Iniciar sesión** con tu cuenta de Google

3. **Crear API Key:**
   - Clic en "Get API key"
   - Clic en "Create API key"
   - **Copia la key** (empieza con `AIzaSy...`)

4. **Configurar en .env:**
   ```env
   DEFAULT_LLM_PROVIDER=Gemini
   GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```

5. **Modelos recomendados:**
   - `gemini-2.5-flash` (default, ultra rápido)
   - `gemini-2.0-flash` (alternativa)
   - `gemini-1.5-pro` (razonamiento complejo)

---

## 3. Groq 🟣

### ¿Por qué Groq?
- **La inferencia más rápida del mercado** (chips LPU™)
- Ideal para demos y prototipos
- API compatible con OpenAI
- Gratis con límites razonables

### Pasos:

1. **Visita:** https://console.groq.com/

2. **Crear cuenta:**
   - Clic en "Sign Up"
   - Regístrate con correo o GitHub

3. **Generar API Key:**
   - En el sidebar, ve a "API Keys"
   - Clic en "Create API Key"
   - Dale un nombre (ej: "tiendita-ia-dev")
   - **Copia la key** (empieza con `gsk_...`)

4. **Configurar en .env:**
   ```env
   DEFAULT_LLM_PROVIDER=Groq
   GROQ_API_KEY=gsk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```

5. **Modelos recomendados:**
   - `llama-3.3-70b-versatile` (default)
   - `llama-3.1-8b-instant` (ultra rápido)
   - `mixtral-8x7b-32768` (contexto largo)

---

## 4. Cohere 🟠

### ¿Por qué Cohere?
- Excelente para embeddings y RAG
- Modelos especializados en enterprise
- Trial gratuito

### Pasos:

1. **Visita:** https://dashboard.cohere.com/

2. **Crear cuenta** con tu correo o Google

3. **Dashboard → API Keys:**
   - Ve a la sección "API Keys"
   - Clic en "Create API Key"
   - **Copia la key**

4. **Configurar en .env:**
   ```env
   DEFAULT_LLM_PROVIDER=Cohere
   COHERE_API_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```

---

## 5. Ollama (100% Local) 🏠

### ¿Por qué Ollama?
- **Sin API keys**, todo en tu máquina
- **Privacidad total**, sin enviar datos a la nube
- Modelos open-source (Llama, Mistral, Qwen, etc.)
- Ideal para desarrollo offline

### Pasos:

1. **Instalar Ollama:**
   
   **Linux/macOS:**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
   
   **Windows:**
   - Descarga el instalador desde https://ollama.com/download
   - Ejecuta el .exe

2. **Descargar un modelo:**
   ```bash
   # Llama 3.2 (3B, ligero)
   ollama pull llama3.2
   
   # Qwen 2.5 (7B, multilingüe)
   ollama pull qwen2.5:7b
   
   # Nemotron Nano (30B, si tienes GPU potente)
   ollama pull nemotron-3-nano:30b
   ```

3. **Verificar que corre:**
   ```bash
   ollama list
   # Deberías ver los modelos descargados
   ```

4. **Configurar en .env:**
   ```env
   DEFAULT_LLM_PROVIDER=Ollama
   OLLAMA_HOST=http://127.0.0.1:11434
   ```

5. **No necesitas API key** ✅

---

## 🔐 Seguridad de API Keys

### ⚠️ Nunca compartas tus API keys

- **NO** las subas a Git
- **NO** las incluyas en screenshots
- **NO** las envíes por Slack/Discord sin cifrar

### ✅ Buenas Prácticas

1. **Usa .env para desarrollo:**
   ```bash
   # El archivo .env está en .gitignore por defecto
   cp .env.example .env
   ```

2. **En producción, usa secretos del sistema:**
   - Variables de entorno del OS
   - AWS Secrets Manager
   - Azure Key Vault
   - Google Secret Manager

3. **Rotar keys periódicamente:**
   - NVIDIA: Genera nuevas keys cada 90 días
   - Gemini: Rota keys si sospechas exposición

4. **Restricciones de IP/dominio:**
   - Algunos proveedores permiten whitelist de IPs
   - Úsalo en producción

---

## 🧪 Verificar que tu Key Funciona

```bash
# Después de configurar .env, ejecuta:
cd tiendita-ia/enjambre_agentes
uv run python check_setup.py
```

Si tu key está configurada correctamente, verás:
```
✓ NVIDIA NIM configurado
# o
✓ Google Gemini configurado
# o
✓ Groq Cloud configurado
```

---

## 🆘 Problemas Comunes

### Error: "API key not found"
- Verifica que tu `.env` esté en el directorio correcto
- Verifica que el nombre de la variable sea exacto: `NVIDIA_API_KEY`, no `NVIDIA_KEY`

### Error: "Authentication failed"
- Verifica que copiaste la key completa (sin espacios)
- Regenera la key en el dashboard del proveedor

### Error: "Rate limit exceeded"
- Espera unos minutos y reintenta
- Considera cambiar a otro proveedor temporalmente
- En Ollama local, no hay rate limits

### Error: "Model not found"
- Verifica el nombre exacto del modelo
- Lista modelos disponibles: `uv run python -c "from models import get_available_models; print(get_available_models('NVIDIA'))"`

---

## 💡 Tips Finales

1. **Comienza con Gemini o NVIDIA NIM** (gratis, límites generosos)
2. **Usa Groq para demos** (ultra rápido, gratis)
3. **Ollama para desarrollo offline** (sin dependencias cloud)
4. **Configura 2-3 proveedores** como fallback automático
