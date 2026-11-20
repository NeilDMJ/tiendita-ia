"""
models.py — Fábrica centralizada de modelos LLM y Embeddings.

Unifica soporte para:
1. NVIDIA NIM (ChatNVIDIA) — Inferencia de alta velocidad local o en la nube (DGX Spark / API).
2. Google Gemini (ChatGoogleGenerativeAI).
3. Groq Cloud (ChatGroq).
4. Cohere (ChatCohere).
5. Ollama Local (ChatOllama) para ejecución 100% offline.

Regla estricta: NO se leen archivos .env ni my_keys.py; todas las credenciales
se resuelven exclusivamente mediante variables de entorno estándar (os.getenv).
"""
from __future__ import annotations

import os
import json
import urllib.request
from typing import List, Dict, Any, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings


# ─────────────────────────────────────────────────────────────────────────────
# 1. CONSTANTES Y MODELOS POR DEFECTO
# ─────────────────────────────────────────────────────────────────────────────

# NVIDIA NIM / NGC API
NVIDIA_DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"
NVIDIA_FALLBACK_MODELS = [
    "meta/llama-3.3-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "meta/llama-3.1-8b-instruct",
    "mistralai/mixtral-8x22b-instruct-v0.1",
]

# Google Gemini
GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"
GEMINI_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

# Groq Cloud
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
]

# Cohere
COHERE_DEFAULT_MODEL = "command-r-plus"
COHERE_FALLBACK_MODELS = [
    "command-r-plus",
    "command-r7b-12-2024",
]

# Ollama Local
OLLAMA_DEFAULT_MODEL = "nemotron-3-nano:30b"
OLLAMA_FALLBACK_MODELS = [
    "nemotron-3-nano:30b",
    "llama3.2",
    "qwen2.5:7b",
]

# Diccionario de modelos de embeddings y sus dimensiones
EMBEDDING_MODELS_INFO: Dict[str, Dict[str, int]] = {
    "Gemini": {
        "models/gemini-embedding-001": 768,
        "models/embedding-001": 768,
    },
    "HuggingFace": {
        "intfloat/multilingual-e5-small": 384,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
        "BAAI/bge-m3": 1024,
        "intfloat/multilingual-e5-base": 768,
    },
    "Ollama": {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
    },
    "NVIDIA": {
        "nvidia/nv-embedqa-e5-v5": 1024,
        "nvidia/llama-3.2-nv-embedqa-1b-v2": 2048,
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. INTROSPECCIÓN DINÁMICA DE MODELOS
# ─────────────────────────────────────────────────────────────────────────────

def get_available_models(provider: str) -> List[str]:
    """
    Obtiene dinámicamente la lista de modelos de chat del proveedor especificado,
    consultando su API REST mediante urllib estándar, con fallback seguro a constantes.
    """
    prov = provider.strip().capitalize()
    
    # ── NVIDIA NIM ──
    if prov == "Nvidia":
        nvidia_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        if nvidia_key:
            try:
                req = urllib.request.Request(
                    f"{base_url.rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {nvidia_key}", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                    if models:
                        return models
            except Exception as e:
                print(f"[Models] Consulta a API NVIDIA falló ({e}). Usando catálogo por defecto.")
        return NVIDIA_FALLBACK_MODELS

    # ── Google Gemini ──
    elif prov == "Gemini":
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [
                        m["name"].replace("models/", "")
                        for m in data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    if models:
                        return models
            except Exception as e:
                print(f"[Models] Consulta a API Gemini falló ({e}). Usando catálogo por defecto.")
        return GEMINI_FALLBACK_MODELS

    # ── Groq Cloud ──
    elif prov == "Groq":
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {groq_key}", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m["id"] for m in data.get("data", []) if m.get("id")]
                    if models:
                        return models
            except Exception as e:
                print(f"[Models] Consulta a API Groq falló ({e}). Usando catálogo por defecto.")
        return GROQ_FALLBACK_MODELS

    # ── Cohere ──
    elif prov == "Cohere":
        cohere_key = os.getenv("COHERE_API_KEY") or os.getenv("CO_API_KEY")
        if cohere_key:
            try:
                req = urllib.request.Request(
                    "https://api.cohere.com/v1/models",
                    headers={"Authorization": f"Bearer {cohere_key}", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m["name"] for m in data.get("models", []) if "chat" in m.get("endpoints", [])]
                    if models:
                        return models
            except Exception as e:
                print(f"[Models] Consulta a API Cohere falló ({e}). Usando catálogo por defecto.")
        return COHERE_FALLBACK_MODELS

    # ── Ollama Local ──
    elif prov == "Ollama":
        ollama_url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        try:
            req = urllib.request.Request(f"{ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    return models
        except Exception:
            pass
        return OLLAMA_FALLBACK_MODELS

    return []


# ─────────────────────────────────────────────────────────────────────────────
# 3. FÁBRICA CENTRALIZADA DE LLMs (get_llm)
# ─────────────────────────────────────────────────────────────────────────────

def get_llm(
    provider: str = "NVIDIA",
    model_name: Optional[str] = None,
    temperature: float = 0.2,
    streaming: bool = False,
    **kwargs: Any
) -> BaseChatModel:
    """
    Fábrica universal de modelos de lenguaje agnóstica al proveedor.
    
    Args:
        provider: Proveedor LLM ('NVIDIA', 'Gemini', 'Groq', 'Cohere', 'Ollama').
        model_name: Nombre específico del modelo (None utiliza el predeterminado del proveedor).
        temperature: Temperatura de muestreo (0.0 = determinista, 1.0 = creativo).
        streaming: Si True, habilita generación en streaming.
        kwargs: Parámetros adicionales para el cliente subyacente.
        
    Returns:
        Instancia compatible con BaseChatModel de LangChain.
    """
    prov = (provider or "NVIDIA").strip().lower()

    # ── 1. NVIDIA NIM (ChatNVIDIA) ──
    if prov in ("nvidia", "nim"):
        nvidia_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        final_model = model_name or NVIDIA_DEFAULT_MODEL
        
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(
                model=final_model,
                api_key=nvidia_key,
                base_url=base_url,
                temperature=temperature,
                streaming=streaming,
                **kwargs
            )
        except ImportError:
            # Fallback a ChatOpenAI compatible con endpoints NVIDIA NIM
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=final_model,
                openai_api_key=nvidia_key or "not-needed-for-local-nim",
                openai_api_base=base_url,
                temperature=temperature,
                streaming=streaming,
                **kwargs
            )

    # ── 2. Google Gemini (ChatGoogleGenerativeAI) ──
    elif prov in ("gemini", "google"):
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not gemini_key:
            raise ValueError(
                "No se encontró GEMINI_API_KEY ni GOOGLE_API_KEY en las variables de entorno."
            )
        final_model = model_name or GEMINI_DEFAULT_MODEL
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=final_model,
            google_api_key=gemini_key,
            temperature=temperature,
            streaming=streaming,
            **kwargs
        )

    # ── 3. Groq Cloud (ChatGroq) ──
    elif prov == "groq":
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("No se encontró GROQ_API_KEY en las variables de entorno.")
        final_model = model_name or GROQ_DEFAULT_MODEL
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=final_model,
            groq_api_key=groq_key,
            temperature=temperature,
            streaming=streaming,
            **kwargs
        )

    # ── 4. Cohere (ChatCohere) ──
    elif prov == "cohere":
        cohere_key = os.getenv("COHERE_API_KEY") or os.getenv("CO_API_KEY")
        if not cohere_key:
            raise ValueError("No se encontró COHERE_API_KEY en las variables de entorno.")
        final_model = model_name or COHERE_DEFAULT_MODEL
        from langchain_cohere import ChatCohere
        return ChatCohere(
            model=final_model,
            cohere_api_key=cohere_key,
            temperature=temperature,
            streaming=streaming,
            **kwargs
        )

    # ── 5. Ollama Local (ChatOllama) ──
    elif prov == "ollama":
        ollama_url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        final_model = model_name or OLLAMA_DEFAULT_MODEL
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=final_model,
            base_url=ollama_url,
            temperature=temperature,
            **kwargs
        )

    else:
        raise ValueError(
            f"Proveedor desconocido '{provider}'. Opciones válidas: NVIDIA, Gemini, Groq, Cohere, Ollama."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. FÁBRICA CENTRALIZADA DE EMBEDDINGS (get_embeddings_model)
# ─────────────────────────────────────────────────────────────────────────────

def get_embeddings_model(
    provider: str = "Gemini",
    model_name: Optional[str] = None
) -> Embeddings:
    """
    Fábrica de modelos de embeddings vectoriales.
    
    Args:
        provider: 'Gemini', 'HuggingFace', 'Ollama', 'NVIDIA'.
        model_name: Nombre del modelo vectorial o None para usar el predeterminado.
    """
    prov = (provider or "Gemini").strip().capitalize()

    # ── Gemini Embeddings ──
    if prov == "Gemini":
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not gemini_key:
            raise ValueError("Se requiere GEMINI_API_KEY en el entorno para embeddings de Gemini.")
        model = model_name or "models/gemini-embedding-001"
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(model=model, google_api_key=gemini_key)

    # ── NVIDIA NIM Embeddings ──
    elif prov == "Nvidia":
        nvidia_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        model = model_name or "nvidia/nv-embedqa-e5-v5"
        try:
            from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
            return NVIDIAEmbeddings(model=model, api_key=nvidia_key, base_url=base_url)
        except ImportError:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=model,
                openai_api_key=nvidia_key or "not-needed",
                openai_api_base=base_url
            )

    # ── HuggingFace Local/Transformers ──
    elif prov == "Huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        model = model_name or "intfloat/multilingual-e5-small"
        return HuggingFaceEmbeddings(model_name=model)

    # ── Ollama Local Embeddings ──
    elif prov == "Ollama":
        from langchain_community.embeddings import OllamaEmbeddings
        ollama_url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        model = model_name or "nomic-embed-text"
        return OllamaEmbeddings(model=model, base_url=ollama_url)

    else:
        raise ValueError(f"Proveedor de embeddings no soportado: '{provider}'.")
