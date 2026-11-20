"""
Módulo de introspección y descubrimiento dinámico de modelos de Groq.
Responsabilidad única (SRP): Consultar en vivo a la API de Groq los modelos disponibles
para la API Key configurada y proveer la lista de modelos utilizables.
"""
import os
import sys
import json
import urllib.request

# Asegurar que la raíz del proyecto esté en sys.path para ejecución directa
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from config.keys import GROQ_API_KEY
except ImportError:
    from keys import GROQ_API_KEY

FALLBACK_MODELS_GROQ = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "groq/compound",
    "groq/compound-mini",
]


def obtener_modelos_groq(timeout: float = 4.0, strict: bool = False) -> list[str]:
    """Consulta la API de Groq y retorna los IDs de los modelos disponibles.
    
    Args:
        timeout: Tiempo máximo de espera HTTP (máx. 4s).
        strict: Si True, retorna [] cuando no hay conexión en vivo o falta API Key.

    Returns:
        Lista de identificadores de modelos Groq.
    """
    if not GROQ_API_KEY or GROQ_API_KEY.startswith("tu_"):
        return [] if strict else list(FALLBACK_MODELS_GROQ)

    t = min(timeout, 4.0)

    # Intento 1: SDK oficial de Groq si está instalado
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY, timeout=t)
        lista = client.models.list()
        modelos = [m.id for m in lista.data if hasattr(m, "id")]
        # Filtrar modelos que no sean de audio/guard
        modelos_chat = [m for m in modelos if "whisper" not in m and "guard" not in m and "tts" not in m]
        if modelos_chat:
            prioritarios = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b"]
            modelos_chat.sort()
            ordenados = [m for m in prioritarios if m in modelos_chat] + [m for m in modelos_chat if m not in prioritarios]
            return ordenados
    except Exception:
        pass

    # Intento 2: Solicitud HTTP directa con User-Agent para evitar bloqueo 403 de Cloudflare
    url = "https://api.groq.com/openai/v1/models"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Accept": "application/json",
            "User-Agent": "TienditaIA/1.0 (Linux; x86_64)",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=t) as response:
            data = json.loads(response.read().decode('utf-8'))
            modelos = [
                model["id"] for model in data.get("data", [])
                if "id" in model and "whisper" not in model["id"] and "guard" not in model["id"] and "tts" not in model["id"]
            ]
            modelos.sort()
            if modelos:
                prioritarios = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b"]
                return [m for m in prioritarios if m in modelos] + [m for m in modelos if m not in prioritarios]
            return [] if strict else list(FALLBACK_MODELS_GROQ)
    except Exception as e:
        if not strict:
            print(f"[Aviso] No se pudo consultar la API de Groq en vivo ({e}). Usando lista de respaldo.")
            return list(FALLBACK_MODELS_GROQ)
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("CONSULTA DIRECTA A LA API DE GROQ")
    print("=" * 60)
    
    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY no encontrada en el entorno.")
        exit(1)

    print("\nModelos de Groq disponibles para tu cuenta:")
    modelos = obtener_modelos_groq()
    for m in modelos:
        print(f"  • {m}")
    print("=" * 60)
