"""
Descubrimiento dinámico de modelos locales mediante la API de Ollama.
Consulta en vivo GET {OLLAMA_BASE_URL}/api/tags.
"""
from __future__ import annotations

import os
from typing import List
import requests

from config.keys import OLLAMA_BASE_URL

FALLBACK_MODELS_OLLAMA = [
    "llama3.2",
    "llama3.1:latest",
    "mistral",
    "gemma2",
    "qwen2.5-coder",
    "deepseek-r1"
]


def obtener_modelos_ollama() -> List[str]:
    """
    Descubre dinámicamente los modelos instalados en la instancia local de Ollama.
    """
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    try:
        resp = requests.get(url, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            modelos = [m["name"] for m in data.get("models", []) if "name" in m]
            if modelos:
                return modelos
    except Exception:
        pass
    return list(FALLBACK_MODELS_OLLAMA)
