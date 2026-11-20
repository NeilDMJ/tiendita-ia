"""
Fábrica unificada de LLMs y Embeddings para Tiendita IA.
Soporta NVIDIA NIM, Google Gemini, Groq, Cohere, Ollama Local y HuggingFace con tolerancia cruzada a fallos.
Implementa 'listar_modelos_disponibles()', 'get_llm(..., role=...)' y 'get_embeddings_model()'.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import yaml
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from config.keys import (
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    COHERE_API_KEY,
    OLLAMA_BASE_URL,
    HF_TOKEN
)

# Configuración por defecto de modelos en Tiendita IA
_CONFIG_YAML_PATH = os.path.join(os.path.dirname(__file__), "agentes.yaml")

PROVIDERS = ["NVIDIA", "Gemini", "Groq", "Cohere", "Ollama", "HuggingFace"]


def extraer_texto_mensaje(content: Any) -> str:
    """Extrae texto limpio de la respuesta de un modelo de lenguaje.
    Maneja strings directos y listas de diccionarios [{'type': 'text', 'text': ...}].
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    partes.append(str(item["text"]))
                elif "text" in item:
                    partes.append(str(item["text"]))
            elif isinstance(item, str):
                partes.append(item)
        return "\n".join(partes) if partes else str(content)
    if isinstance(content, dict):
        return str(content.get("text", content.get("content", str(content))))
    return str(content) if content is not None else ""


def _crear_fallbacks_cruzados(provider: str, model_name: str | None, temperature: float) -> list[BaseChatModel]:
    """Crea una lista ordenada de modelos de respaldo entre proveedores para alta disponibilidad."""
    fallbacks: list[BaseChatModel] = []
    prov_lower = provider.strip().lower()

    # 1. Fallback a NVIDIA si no era el proveedor primario
    if prov_lower != "nvidia" and NVIDIA_API_KEY and not NVIDIA_API_KEY.startswith("tu_"):
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            fallbacks.append(ChatNVIDIA(
                model="nvidia/nemotron-3-super-120b-a12b",
                nvidia_api_key=NVIDIA_API_KEY,
                base_url=NVIDIA_BASE_URL,
                temperature=temperature
            ))
        except Exception:
            pass

    # 2. Fallback a Gemini
    if prov_lower not in ("gemini", "google") and GEMINI_API_KEY and not GEMINI_API_KEY.startswith("tu_"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            fallbacks.append(ChatGoogleGenerativeAI(
                model="gemini-flash-lite-latest",
                temperature=temperature,
                google_api_key=GEMINI_API_KEY
            ))
        except Exception:
            pass

    # 3. Fallback a Groq
    if prov_lower != "groq" and GROQ_API_KEY and not GROQ_API_KEY.startswith("tu_"):
        try:
            from langchain_groq import ChatGroq
            fallbacks.append(ChatGroq(model="llama-3.3-70b-versatile", temperature=temperature))
        except Exception:
            pass

    # 4. Fallback 100% Local en Ollama (sin internet ni cuotas)
    try:
        from langchain_ollama import ChatOllama
        fallbacks.append(ChatOllama(model="llama3.2", base_url=OLLAMA_BASE_URL, temperature=temperature))
    except Exception:
        pass

    return fallbacks


def get_llm(
    provider: str = "NVIDIA",
    model_name: Optional[str] = None,
    temperature: float = 0.2,
    role: Optional[str] = None
) -> BaseChatModel:
    """
    Instancia el modelo de lenguaje elegido por el usuario o asignado por rol.
    Integra soporte para NVIDIA NIM, Gemini, Groq, Cohere, Ollama y HuggingFace.
    """
    prov_norm = provider.strip().upper()

    if prov_norm == "NVIDIA":
        if NVIDIA_API_KEY and not NVIDIA_API_KEY.startswith("tu_"):
            try:
                from langchain_nvidia_ai_endpoints import ChatNVIDIA
                m = model_name or ("nvidia/llama-3.1-nemotron-nano-8b-v1" if role in ("vendedor", "control", "tutor_ui") else "nvidia/nemotron-3-super-120b-a12b")
                primary = ChatNVIDIA(
                    model=m,
                    nvidia_api_key=NVIDIA_API_KEY,
                    base_url=NVIDIA_BASE_URL,
                    temperature=temperature
                )
                fallbacks = _crear_fallbacks_cruzados("NVIDIA", m, temperature)
                return primary.with_fallbacks(fallbacks) if fallbacks else primary
            except Exception:
                pass
        # Conmutar ordenadamente a Gemini o Ollama si NVIDIA no está disponible
        if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("tu_"):
            return get_llm(provider="Gemini", model_name="gemini-flash-lite-latest", temperature=temperature, role=role)
        return get_llm(provider="Ollama", model_name="llama3.2", temperature=temperature, role=role)

    elif prov_norm == "GEMINI":
        from langchain_google_genai import ChatGoogleGenerativeAI
        m = model_name or "gemini-flash-lite-latest"
        primary = ChatGoogleGenerativeAI(model=m, temperature=temperature, google_api_key=GEMINI_API_KEY)
        fallbacks = _crear_fallbacks_cruzados("Gemini", m, temperature)
        return primary.with_fallbacks(fallbacks) if fallbacks else primary

    elif prov_norm == "GROQ":
        from langchain_groq import ChatGroq
        m = model_name or "llama-3.3-70b-versatile"
        primary = ChatGroq(model=m, temperature=temperature)
        fallbacks = _crear_fallbacks_cruzados("Groq", m, temperature)
        return primary.with_fallbacks(fallbacks) if fallbacks else primary

    elif prov_norm == "COHERE":
        from langchain_cohere import ChatCohere
        m = model_name or "command-r7b-12-2024"
        primary = ChatCohere(model=m, temperature=temperature, cohere_api_key=COHERE_API_KEY)
        fallbacks = _crear_fallbacks_cruzados("Cohere", m, temperature)
        return primary.with_fallbacks(fallbacks) if fallbacks else primary

    elif prov_norm == "HUGGINGFACE":
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        m = model_name or "mistralai/Mistral-7B-Instruct-v0.3"
        endpoint = HuggingFaceEndpoint(
            repo_id=m,
            huggingfacehub_api_token=HF_TOKEN,
            temperature=temperature
        )
        return ChatHuggingFace(llm=endpoint)

    else:
        # Proveedor por defecto: Ollama Local
        from langchain_ollama import ChatOllama
        m = model_name or "llama3.2"
        return ChatOllama(model=m, base_url=OLLAMA_BASE_URL, temperature=temperature)


def get_embeddings_model(provider: str = "HuggingFace", model_name: Optional[str] = None) -> Embeddings:
    """
    Fábrica unificada de modelos de embeddings:
    Soporta NVIDIA NIM (nv-embedqa-e5-v5), HuggingFace (all-MiniLM-L6-v2), Gemini y Ollama.
    """
    prov_norm = provider.strip().upper()

    if prov_norm == "NVIDIA" and NVIDIA_API_KEY and not NVIDIA_API_KEY.startswith("tu_"):
        try:
            from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
            return NVIDIAEmbeddings(model=model_name or "nvidia/nv-embedqa-e5-v5", nvidia_api_key=NVIDIA_API_KEY)
        except Exception:
            pass

    if prov_norm == "GEMINI" and GEMINI_API_KEY and not GEMINI_API_KEY.startswith("tu_"):
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(model=model_name or "models/embedding-001", google_api_key=GEMINI_API_KEY)
        except Exception:
            pass

    if prov_norm == "OLLAMA":
        try:
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(model=model_name or "nomic-embed-text", base_url=OLLAMA_BASE_URL)
        except Exception:
            pass

    # Fallback por defecto: HuggingFace local offline
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=model_name or "sentence-transformers/all-MiniLM-L6-v2")


def cargar_config_agentes() -> Dict[str, Any]:
    """Lee la configuración de config/agentes.yaml."""
    if os.path.exists(_CONFIG_YAML_PATH):
        try:
            with open(_CONFIG_YAML_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {"modelos": {}}


def get_llm_para_agente(nombre_agente: str) -> BaseChatModel:
    """Retorna el LLM asignado al rol del agente en config/agentes.yaml."""
    cfg = cargar_config_agentes().get("modelos", {}).get(nombre_agente, {})
    proveedor = cfg.get("proveedor", "NVIDIA")
    modelo = cfg.get("modelo")
    temperatura = float(cfg.get("temperatura", 0.1))
    return get_llm(provider=proveedor, model_name=modelo, temperature=temperatura, role=nombre_agente)


def listar_modelos_disponibles(provider: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Descubre y devuelve en vivo la lista de modelos disponibles para cada proveedor.
    """
    resultado: Dict[str, List[str]] = {}

    if not provider or provider.upper() == "NVIDIA":
        from config.models_nvidia import obtener_modelos_nvidia
        resultado["NVIDIA"] = obtener_modelos_nvidia()

    if not provider or provider.upper() in ("GEMINI", "GOOGLE"):
        try:
            from config.models_gemini import obtener_modelos_gemini
            resultado["Gemini"] = obtener_modelos_gemini(tipo="chat")
        except Exception:
            resultado["Gemini"] = ["gemini-2.5-flash", "gemini-flash-lite-latest", "gemini-1.5-pro"]

    if not provider or provider.upper() == "GROQ":
        try:
            from config.models_groq import obtener_modelos_groq
            resultado["Groq"] = obtener_modelos_groq()
        except Exception:
            resultado["Groq"] = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

    if not provider or provider.upper() == "COHERE":
        try:
            from config.models_cohere import obtener_modelos_cohere
            resultado["Cohere"] = obtener_modelos_cohere(tipo="chat")
        except Exception:
            resultado["Cohere"] = ["command-r7b-12-2024", "command-r-plus"]

    if not provider or provider.upper() == "OLLAMA":
        from config.models_ollama import obtener_modelos_ollama
        resultado["Ollama"] = obtener_modelos_ollama()

    if not provider or provider.upper() == "HUGGINGFACE":
        resultado["HuggingFace"] = [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "sentence-transformers/all-MiniLM-L6-v2"
        ]

    return resultado
