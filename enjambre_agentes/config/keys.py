"""
Gestión centralizada de variables de entorno y API keys para Tiendita IA.
Lectura segura mediante os.getenv(...) sin llaves hardcodeadas.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

# --- NVIDIA NIM & NeMo ---
NVIDIA_API_KEY: str | None = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# --- Base de Datos PostgreSQL Vectorial ---
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://tiendita_user:tiendita_pass@localhost:5432/tiendita_db"
)

# --- Búsqueda Web Tavily (Investigador) ---
TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")
TAVILY_MAX_RESULTS: int = int(os.getenv("TAVILY_MAX_RESULTS", "5"))

# --- HuggingFace (Embeddings y Modelos Open Source) ---
HF_TOKEN: str | None = os.getenv("HF_TOKEN")

# --- Proveedores Nube Alternativos ---
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
COHERE_API_KEY: str | None = os.getenv("COHERE_API_KEY")

# --- Modelo Local (Ollama) ---
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_API_KEY: str | None = os.getenv("OLLAMA_API_KEY")

# --- Observabilidad LangSmith ---
LANGSMITH_TRACING: str = os.getenv("LANGSMITH_TRACING", "false")
LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_API_KEY: str | None = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "tiendita-ia")

# --- Servidor API, Autenticación Opcional y Túnel SSH Nativo ---
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
TIENDITA_API_KEY: str = os.getenv("TIENDITA_API_KEY", "").strip()
SSH_VPS_TARGET: str = os.getenv("SSH_VPS_TARGET", "").strip()


def get_tiendita_api_key() -> str:
    """Lee dinámicamente TIENDITA_API_KEY desde el entorno (vacía = acceso abierto LAN)."""
    return os.getenv("TIENDITA_API_KEY", "").strip()


def validate_keys(*required_keys: str) -> None:
    """Valida que las credenciales obligatorias para una operación específica estén presentes."""
    key_map = {
        "NVIDIA_API_KEY": NVIDIA_API_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "GROQ_API_KEY": GROQ_API_KEY,
        "COHERE_API_KEY": COHERE_API_KEY,
        "TAVILY_API_KEY": TAVILY_API_KEY,
        "HF_TOKEN": HF_TOKEN,
        "DATABASE_URL": DATABASE_URL,
    }
    faltantes = [k for k in required_keys if not key_map.get(k) or str(key_map.get(k)).startswith("tu_")]
    if faltantes:
        raise ValueError(
            f"Faltan las siguientes variables de entorno requeridas en .env: {', '.join(faltantes)}. "
            f"Por favor configúralas para continuar."
        )
