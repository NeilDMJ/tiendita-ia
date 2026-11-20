"""
Descubrimiento e introspección dinámica de modelos NVIDIA NIM en vivo.
Compatible tanto con endpoints cloud (integrate.api.nvidia.com) como DGX Spark on-premise.
"""
from __future__ import annotations

import os
from typing import List
import requests

from config.keys import NVIDIA_API_KEY, NVIDIA_BASE_URL

# Modelos oficiales estipulados para Tiendita IA
FALLBACK_MODELS_NVIDIA = [
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/llama-3.1-nemotron-nano-8b-v1",
    "meta/llama-3.1-70b-instruct",
    "mistralai/mistral-large-2-instruct",
    "nvidia/neva-22b"
]


def obtener_modelos_nvidia() -> List[str]:
    """
    Consulta en vivo GET {NVIDIA_BASE_URL}/models para listar los microservicios NIM disponibles.
    Si la red no está disponible o falta la llave, retorna la lista de fallbacks oficiales.
    """
    if not NVIDIA_API_KEY or NVIDIA_API_KEY.startswith("tu_"):
        return list(FALLBACK_MODELS_NVIDIA)
    
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json"
    }
    url = f"{NVIDIA_BASE_URL.rstrip('/')}/models"
    
    try:
        resp = requests.get(url, headers=headers, timeout=5.0)
        if resp.status_code == 200:
            datos = resp.json()
            modelos = [m["id"] for m in datos.get("data", []) if "id" in m]
            if modelos:
                # Asegurar que los modelos prioritarios de Tiendita IA estén presentes
                for prio in ["nvidia/nemotron-3-super-120b-a12b", "nvidia/llama-3.1-nemotron-nano-8b-v1"]:
                    if prio not in modelos:
                        modelos.insert(0, prio)
                return modelos
    except Exception:
        pass
        
    return list(FALLBACK_MODELS_NVIDIA)
