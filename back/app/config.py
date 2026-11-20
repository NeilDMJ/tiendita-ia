"""Configuración del backend (variables de entorno / back/.env). Nunca registrar la clave."""
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parent.parent

Proveedor = Literal["nim", "ollama"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=RAIZ / ".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: Proveedor = "nim"
    llm_fallback: str = ""  # "", "nim" u "ollama"

    nvidia_api_key: str = ""
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_model: str = "nvidia/nemotron-3.5-bolt-e4b"

    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:3b"

    embed_model: str = "nvidia/nemotron-3.5-embed-8b"
    embed_timeout_s: float = 6  # si tarda más, la búsqueda usa solo palabras clave

    llm_timeout_s: float = 25
    llm_max_tokens: int = 600
    cors_origins: str = "*"


def get_settings() -> Settings:
    return Settings()
