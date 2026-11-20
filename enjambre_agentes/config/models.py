"""
Fábrica unificada de LLMs y Embeddings para Tiendita IA.

Política de Cerebros:
  - Por defecto (100% NVIDIA NIM):
      * supervisor, analista, investigador -> nvidia/nemotron-3-super-120b-a12b
      * control, vendedor, publicista, tutor_ui -> nvidia/llama-3.1-nemotron-nano-8b-v1
  - Rescate silencioso automático mediante `.with_fallbacks()` (`ResilientChatModel`)
    encadenando los demás proveedores activos en caso de caída de red o cuota (HTTP 429).
  - Overrides individuales en tiempo de ejecución por subagente mediante `ACTIVE_AGENT_BRAINS`:
      * `set_agent_brain(role, provider, model_name)`
      * `reset_brains_to_nvidia_default()`
      * `get_active_brains()`
"""
from __future__ import annotations

import concurrent.futures
import contextlib
import contextvars
import os
import threading
import time
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple
import yaml

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables.fallbacks import RunnableWithFallbacks

from config.keys import (
    COHERE_API_KEY,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    HF_TOKEN,
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    OLLAMA_BASE_URL,
)

# ---------------------------------------------------------------------------
# Constantes globales, perfiles 100% NVIDIA por defecto y overrides en runtime
# ---------------------------------------------------------------------------

_CONFIG_YAML_PATH = os.path.join(os.path.dirname(__file__), "agentes.yaml")

PROVIDERS = ["NVIDIA", "Gemini", "Groq", "Cohere", "Ollama", "HuggingFace"]
ACTIVE_PROBE_ORDER = ["NVIDIA", "Groq", "Cohere", "Gemini", "Ollama"]
FALLBACK_PRIORITY_ORDER = ["NVIDIA", "Groq", "Cohere", "Gemini", "Ollama"]

AGENT_ROLES = [
    "supervisor",
    "control",
    "vendedor",
    "analista",
    "investigador",
    "publicista",
    "tutor_ui",
]

# Perfil 100% NVIDIA exclusivo por defecto
DEFAULT_NVIDIA_BRAINS: Dict[str, Tuple[str, str]] = {
    "supervisor": ("NVIDIA", "nvidia/nemotron-3-super-120b-a12b"),
    "analista": ("NVIDIA", "nvidia/nemotron-3-super-120b-a12b"),
    "investigador": ("NVIDIA", "nvidia/nemotron-3-super-120b-a12b"),
    "control": ("NVIDIA", "nvidia/llama-3.1-nemotron-nano-8b-v1"),
    "vendedor": ("NVIDIA", "nvidia/llama-3.1-nemotron-nano-8b-v1"),
    "publicista": ("NVIDIA", "nvidia/llama-3.1-nemotron-nano-8b-v1"),
    "tutor_ui": ("NVIDIA", "nvidia/llama-3.1-nemotron-nano-8b-v1"),
}

# Estado mutable en tiempo de ejecución: rol -> (proveedor, modelo)
ACTIVE_AGENT_BRAINS: Dict[str, Tuple[str, str]] = dict(DEFAULT_NVIDIA_BRAINS)

DEFAULT_ROLE_TEMPERATURES: Dict[str, float] = {
    "supervisor": 0.1,
    "control": 0.1,
    "vendedor": 0.2,
    "analista": 0.1,
    "investigador": 0.2,
    "publicista": 0.4,
    "tutor_ui": 0.0,
}

# Caché de detección de proveedores activos (TTL en segundos)
_STATE_LOCK = threading.RLock()
_CACHE_TTL_SECONDS = 120.0
_cached_active_providers: Optional[Dict[str, List[str]]] = None
_cached_provider_status: Dict[str, Dict[str, Any]] = {}
_cached_timestamp: float = 0.0

# Circuit Breaker por proveedor (evita repetir esperas de red/410/403/504/429 entre dispositivos)
_CIRCUIT_COOLDOWN_SECONDS = 300.0
_tripped_providers: Dict[str, float] = {}

# Override global opcional y override acotado por petición (FastAPI / CLI)
_manual_override: Tuple[Optional[str], Optional[str]] = (None, None)
_request_override_var: contextvars.ContextVar[Tuple[Optional[str], Optional[str]]] = (
    contextvars.ContextVar("tiendita_model_override", default=(None, None))
)


def _marcar_proveedor_caido(provider: str) -> None:
    """Marca temporalmente un proveedor en cooldown tras error de red/timeout/cuota."""
    prov = _normalizar_proveedor(provider)
    if prov:
        with _STATE_LOCK:
            _tripped_providers[prov] = time.time() + _CIRCUIT_COOLDOWN_SECONDS


def _proveedor_en_cooldown(provider: str) -> bool:
    """Indica si un proveedor falló recientemente y está temporalmente en cooldown."""
    prov = _normalizar_proveedor(provider)
    if not prov:
        return False
    with _STATE_LOCK:
        expira = _tripped_providers.get(prov)
        if expira is None:
            return False
        if time.time() >= expira:
            _tripped_providers.pop(prov, None)
            return False
        return True


def _limpiar_cooldown_proveedor(provider: Optional[str] = None) -> None:
    with _STATE_LOCK:
        if provider:
            prov = _normalizar_proveedor(provider)
            if prov:
                _tripped_providers.pop(prov, None)
        else:
            _tripped_providers.clear()


# ---------------------------------------------------------------------------
# Utilidades de texto y gestión de cerebros por agente en runtime
# ---------------------------------------------------------------------------

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


def _normalizar_proveedor(provider: Optional[str]) -> Optional[str]:
    """Normaliza el nombre de proveedor a su forma canónica."""
    if not provider:
        return None
    p = provider.strip().lower()
    mapa = {
        "nvidia": "NVIDIA",
        "nim": "NVIDIA",
        "gemini": "Gemini",
        "google": "Gemini",
        "groq": "Groq",
        "cohere": "Cohere",
        "ollama": "Ollama",
        "huggingface": "HuggingFace",
        "hf": "HuggingFace",
    }
    return mapa.get(p, provider.strip())


def set_agent_brain(role: str, provider: str, model_name: str) -> Tuple[str, str]:
    """
    Cambia en tiempo de ejecución el proveedor y modelo de un subagente específico
    sin necesidad de reiniciar el programa.
    """
    role_norm = role.strip().lower()
    if role_norm not in AGENT_ROLES:
        raise ValueError(
            f"Rol de agente inválido '{role}'. Roles válidos: {', '.join(AGENT_ROLES)}"
        )
    prov_norm = _normalizar_proveedor(provider)
    if not prov_norm or prov_norm not in PROVIDERS:
        raise ValueError(
            f"Proveedor inválido '{provider}'. Proveedores válidos: {', '.join(PROVIDERS)}"
        )
    mod_clean = model_name.strip()
    if not mod_clean:
        raise ValueError("El nombre del modelo no puede estar vacío.")

    ACTIVE_AGENT_BRAINS[role_norm] = (prov_norm, mod_clean)
    _limpiar_cooldown_proveedor(prov_norm)
    return ACTIVE_AGENT_BRAINS[role_norm]


def reset_brains_to_nvidia_default() -> Dict[str, Tuple[str, str]]:
    """Devuelve todos los 7 agentes al perfil exclusivo 100% NVIDIA NIM."""
    global _manual_override
    _manual_override = (None, None)
    _limpiar_cooldown_proveedor()
    ACTIVE_AGENT_BRAINS.clear()
    ACTIVE_AGENT_BRAINS.update(DEFAULT_NVIDIA_BRAINS)
    return dict(ACTIVE_AGENT_BRAINS)


def set_manual_override(provider: Optional[str], model_name: Optional[str] = None) -> None:
    """Fija un proveedor/modelo global a nivel de sesión."""
    global _manual_override
    prov_norm = _normalizar_proveedor(provider)
    _manual_override = (prov_norm, model_name.strip() if model_name else None)


def clear_manual_override() -> None:
    """Limpia el override global de sesión."""
    global _manual_override
    _manual_override = (None, None)


def get_manual_override() -> Tuple[Optional[str], Optional[str]]:
    """Devuelve el override global o por petición si existe."""
    req_prov, req_mod = _request_override_var.get()
    if req_prov or req_mod:
        return (req_prov, req_mod)
    return _manual_override


@contextlib.contextmanager
def override_model_context(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Iterator[None]:
    """Context manager seguro para concurrencia que aplica override temporal por petición."""
    prov_norm = _normalizar_proveedor(provider)
    mod_norm = model_name.strip() if model_name else None
    if not prov_norm and not mod_norm:
        yield
        return
    token = _request_override_var.set((prov_norm, mod_norm))
    try:
        yield
    finally:
        _request_override_var.reset(token)


# ---------------------------------------------------------------------------
# Wrapper Resiliente compatible con .with_fallbacks(), bind_tools y structured_output
# ---------------------------------------------------------------------------

def _detectar_proveedor_de_runnable(runnable: Any) -> Optional[str]:
    """Identifica el nombre canónico del proveedor de un runnable, binding o secuencia LangChain."""
    obj = runnable
    for _ in range(4):
        if hasattr(obj, "steps") and getattr(obj, "steps"):
            obj = obj.steps[0]
        elif hasattr(obj, "first"):
            obj = obj.first
        elif hasattr(obj, "bound"):
            obj = obj.bound
        else:
            break
    cls_name = type(obj).__name__.lower()
    if "nvidia" in cls_name:
        return "NVIDIA"
    if "google" in cls_name or "gemini" in cls_name:
        return "Gemini"
    if "groq" in cls_name:
        return "Groq"
    if "cohere" in cls_name:
        return "Cohere"
    if "ollama" in cls_name:
        return "Ollama"
    if "huggingface" in cls_name:
        return "HuggingFace"
    return None


class ResilientChatModel(RunnableWithFallbacks):
    """
    Subclase de `RunnableWithFallbacks` que preserva `.with_fallbacks()` nativo de LangChain,
    propaga `.bind_tools()` y `.with_structured_output()`, y registra automáticamente en el
    circuit breaker cualquier proveedor primario que falle por red/timeout/cuota para evitar
    esperas repetidas en el resto de la ejecución del grafo.
    """

    def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
        try:
            return self.runnable.invoke(input, config=config, **kwargs)
        except Exception:
            prov_primario = _detectar_proveedor_de_runnable(self.runnable)
            if prov_primario:
                _marcar_proveedor_caido(prov_primario)
            ultimo_err: Optional[Exception] = None
            for fb in self.fallbacks:
                prov_fb = _detectar_proveedor_de_runnable(fb)
                if prov_fb and _proveedor_en_cooldown(prov_fb):
                    continue
                try:
                    return fb.invoke(input, config=config, **kwargs)
                except Exception as exc:
                    ultimo_err = exc
                    if prov_fb:
                        _marcar_proveedor_caido(prov_fb)
            if ultimo_err:
                raise ultimo_err
            raise

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Any:
        primary_bound = self.runnable.bind_tools(tools, **kwargs)
        bound_fallbacks = []
        for fb in self.fallbacks:
            try:
                bound_fallbacks.append(fb.bind_tools(tools, **kwargs))
            except Exception:
                continue
        if not bound_fallbacks:
            return primary_bound
        wrapped = primary_bound.with_fallbacks(bound_fallbacks)
        return ResilientChatModel(
            runnable=wrapped.runnable,
            fallbacks=wrapped.fallbacks,
            exceptions_to_handle=wrapped.exceptions_to_handle,
            exception_key=wrapped.exception_key,
        )

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        primary_struct = self.runnable.with_structured_output(schema, **kwargs)
        struct_fallbacks = []
        for fb in self.fallbacks:
            try:
                struct_fallbacks.append(fb.with_structured_output(schema, **kwargs))
            except Exception:
                continue
        if not struct_fallbacks:
            return primary_struct
        wrapped = primary_struct.with_fallbacks(struct_fallbacks)
        return ResilientChatModel(
            runnable=wrapped.runnable,
            fallbacks=wrapped.fallbacks,
            exceptions_to_handle=wrapped.exceptions_to_handle,
            exception_key=wrapped.exception_key,
        )


def _envolver_con_rescate(primary: BaseChatModel, fallbacks: List[BaseChatModel]) -> Any:
    """Envuelve el modelo primario con `.with_fallbacks()` en un `ResilientChatModel`."""
    if not fallbacks:
        return primary
    wrapped = primary.with_fallbacks(fallbacks)
    return ResilientChatModel(
        runnable=wrapped.runnable,
        fallbacks=wrapped.fallbacks,
        exceptions_to_handle=wrapped.exceptions_to_handle,
        exception_key=wrapped.exception_key,
    )


# ---------------------------------------------------------------------------
# Detección de Proveedores Activos en Tiempo Real (timeout <= 4s)
# ---------------------------------------------------------------------------

def _credencial_valida(api_key: Optional[str]) -> bool:
    return bool(api_key and api_key.strip() and not api_key.strip().startswith("tu_"))


def _sondear_proveedor(provider: str, timeout: float = 4.0) -> Tuple[str, List[str], Dict[str, Any]]:
    """Sondea un proveedor individual reutilizando su módulo `config/models_*.py`."""
    t = min(max(timeout, 0.5), 4.0)
    inicio = time.perf_counter()

    try:
        if provider == "NVIDIA":
            if not _credencial_valida(NVIDIA_API_KEY):
                return provider, [], {"activo": False, "motivo": "Sin NVIDIA_API_KEY válida", "latencia_ms": 0}
            from config.models_nvidia import obtener_modelos_nvidia
            modelos = obtener_modelos_nvidia(timeout=t, strict=True)

        elif provider == "Gemini":
            if not _credencial_valida(GEMINI_API_KEY):
                return provider, [], {"activo": False, "motivo": "Sin GEMINI_API_KEY válida", "latencia_ms": 0}
            from config.models_gemini import obtener_modelos_gemini
            modelos = obtener_modelos_gemini(tipo="chat", timeout=t, strict=True)

        elif provider == "Groq":
            if not _credencial_valida(GROQ_API_KEY):
                return provider, [], {"activo": False, "motivo": "Sin GROQ_API_KEY válida", "latencia_ms": 0}
            from config.models_groq import obtener_modelos_groq
            modelos = obtener_modelos_groq(timeout=t, strict=True)

        elif provider == "Cohere":
            if not _credencial_valida(COHERE_API_KEY):
                return provider, [], {"activo": False, "motivo": "Sin COHERE_API_KEY válida", "latencia_ms": 0}
            from config.models_cohere import obtener_modelos_cohere
            modelos = obtener_modelos_cohere(tipo="chat", timeout=t, strict=True)

        elif provider == "Ollama":
            from config.models_ollama import obtener_modelos_ollama
            modelos = obtener_modelos_ollama(timeout=t, strict=True)

        else:
            return provider, [], {"activo": False, "motivo": "Proveedor no soportado", "latencia_ms": 0}

        latencia_ms = int((time.perf_counter() - inicio) * 1000)
        if modelos:
            return provider, modelos, {
                "activo": True,
                "motivo": f"{len(modelos)} modelos en vivo",
                "latencia_ms": latencia_ms,
                "total_modelos": len(modelos),
            }
        return provider, [], {
            "activo": False,
            "motivo": "Sin respuesta en vivo o bloqueado por red (timeout <= 4s)",
            "latencia_ms": latencia_ms,
            "total_modelos": 0,
        }
    except Exception as exc:
        latencia_ms = int((time.perf_counter() - inicio) * 1000)
        return provider, [], {
            "activo": False,
            "motivo": f"Error de conexión: {type(exc).__name__}",
            "latencia_ms": latencia_ms,
            "total_modelos": 0,
        }


def detectar_proveedores_activos(
    force_refresh: bool = False,
    timeout: float = 4.0,
) -> Dict[str, List[str]]:
    """
    Consulta en paralelo qué proveedores tienen credenciales válidas y responden en tiempo real
    (NVIDIA, Gemini, Groq, Cohere, Ollama local) con timeout <= 4s.
    """
    global _cached_active_providers, _cached_provider_status, _cached_timestamp

    ahora = time.time()
    if (
        not force_refresh
        and _cached_active_providers is not None
        and (ahora - _cached_timestamp) < _CACHE_TTL_SECONDS
    ):
        return {k: list(v) for k, v in _cached_active_providers.items()}

    t = min(max(timeout, 0.5), 4.0)
    activos_temp: Dict[str, List[str]] = {}
    estados_temp: Dict[str, Dict[str, Any]] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ACTIVE_PROBE_ORDER)) as executor:
        futuros = {executor.submit(_sondear_proveedor, prov, t): prov for prov in ACTIVE_PROBE_ORDER}
        for futuro in concurrent.futures.as_completed(futuros):
            prov, modelos, info = futuro.result()
            estados_temp[prov] = info
            if modelos:
                activos_temp[prov] = modelos

    activos_ordenados = {
        prov: activos_temp[prov]
        for prov in ACTIVE_PROBE_ORDER
        if prov in activos_temp
    }

    _cached_active_providers = activos_ordenados
    _cached_provider_status = {
        prov: estados_temp.get(prov, {"activo": False, "motivo": "No sondeado", "latencia_ms": 0})
        for prov in ACTIVE_PROBE_ORDER
    }
    _cached_timestamp = ahora

    return {k: list(v) for k, v in activos_ordenados.items()}


def obtener_estado_proveedores(force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    """Retorna el diagnóstico detallado (activo/inactivo, latencia y motivo) de cada proveedor."""
    detectar_proveedores_activos(force_refresh=force_refresh)
    return {k: dict(v) for k, v in _cached_provider_status.items()}


# ---------------------------------------------------------------------------
# Selección de modelos de respaldo y estado activo de los 7 cerebros
# ---------------------------------------------------------------------------

_MODEL_PREFERENCES: Dict[str, Dict[str, List[str]]] = {
    "NVIDIA": {
        "razonamiento": [
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3-ultra-550b-a55b",
            "meta/llama-3.1-70b-instruct",
        ],
        "velocidad_contexto": [
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3.5-lightning-30b-a3b",
        ],
        "baja_latencia": [
            "nvidia/llama-3.1-nemotron-nano-8b-v1",
            "nvidia/nemotron-3.5-bolt-e4b",
        ],
        "balanceado": [
            "nvidia/llama-3.1-nemotron-nano-8b-v1",
            "nvidia/nemotron-3-super-120b-a12b",
        ],
    },
    "Gemini": {
        "razonamiento": ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.5-flash-lite"],
        "velocidad_contexto": ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.5-flash-lite"],
        "baja_latencia": ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
        "balanceado": ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.5-flash-lite"],
    },
    "Groq": {
        "razonamiento": ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"],
        "velocidad_contexto": ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"],
        "baja_latencia": ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"],
        "balanceado": ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"],
    },
    "Cohere": {
        "razonamiento": ["command-a-03-2025", "command-r-plus-08-2024", "command-r-08-2024", "command-r7b-12-2024"],
        "velocidad_contexto": ["command-r-08-2024", "command-r-plus-08-2024", "command-r7b-12-2024"],
        "baja_latencia": ["command-r7b-12-2024", "command-r-08-2024"],
        "balanceado": ["command-r-08-2024", "command-r7b-12-2024", "command-r-plus-08-2024"],
    },
    "Ollama": {
        "razonamiento": ["llama3.1:latest", "qwen2.5", "llama3.2", "mistral", "gemma2"],
        "velocidad_contexto": ["llama3.2", "qwen2.5", "llama3.1:latest", "mistral"],
        "baja_latencia": ["llama3.2", "gemma2", "qwen2.5", "mistral"],
        "balanceado": ["llama3.2", "mistral", "gemma2", "llama3.1:latest"],
    },
}

_ROLE_PROFILES: Dict[str, str] = {
    "supervisor": "razonamiento",
    "analista": "razonamiento",
    "investigador": "velocidad_contexto",
    "control": "balanceado",
    "vendedor": "baja_latencia",
    "publicista": "balanceado",
    "tutor_ui": "baja_latencia",
}


def _elegir_modelo_para_perfil(
    provider: str,
    profile: str,
    modelos_disponibles: Optional[List[str]] = None,
) -> str:
    """Selecciona el mejor modelo disponible en `provider` para el perfil cognitivo dado."""
    preferencias = _MODEL_PREFERENCES.get(provider, {}).get(profile, [])
    disponibles = modelos_disponibles or []

    if disponibles:
        for cand in preferencias:
            if cand in disponibles:
                return cand
        for cand in preferencias:
            for disp in disponibles:
                if disp.startswith(cand):
                    return disp
        return disponibles[0]

    if preferencias:
        return preferencias[0]

    defaults = {
        "NVIDIA": "nvidia/nemotron-3-super-120b-a12b",
        "Gemini": "gemini-flash-lite-latest",
        "Groq": "llama-3.3-70b-versatile",
        "Cohere": "command-r7b-12-2024",
        "Ollama": "llama3.2",
        "HuggingFace": "mistralai/Mistral-7B-Instruct-v0.3",
    }
    return defaults.get(provider, "nvidia/nemotron-3-super-120b-a12b")


def _construir_lista_rescate_specs(
    primary_provider: str,
    profile: str,
    activos: Dict[str, List[str]],
) -> List[Dict[str, str]]:
    """Calcula la cadena silenciosa de respaldo (.with_fallbacks) excluyendo al proveedor primario."""
    specs: List[Dict[str, str]] = []

    for prov in FALLBACK_PRIORITY_ORDER:
        if prov == primary_provider:
            continue
        if prov in activos:
            specs.append({
                "provider": prov,
                "model": _elegir_modelo_para_perfil(prov, profile, activos[prov]),
            })

    if not specs:
        for prov in FALLBACK_PRIORITY_ORDER:
            if prov == primary_provider:
                continue
            if prov == "NVIDIA" and _credencial_valida(NVIDIA_API_KEY):
                specs.append({"provider": prov, "model": _elegir_modelo_para_perfil(prov, profile)})
            elif prov == "Gemini" and _credencial_valida(GEMINI_API_KEY):
                specs.append({"provider": prov, "model": _elegir_modelo_para_perfil(prov, profile)})
            elif prov == "Groq" and _credencial_valida(GROQ_API_KEY):
                specs.append({"provider": prov, "model": _elegir_modelo_para_perfil(prov, profile)})
            elif prov == "Cohere" and _credencial_valida(COHERE_API_KEY):
                specs.append({"provider": prov, "model": _elegir_modelo_para_perfil(prov, profile)})
            elif prov == "Ollama":
                specs.append({"provider": prov, "model": _elegir_modelo_para_perfil(prov, profile)})

    return specs


def get_active_brains(
    proveedores_activos: Optional[Dict[str, List[str]]] = None,
    force_refresh: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """
    Devuelve el mapa completo de cerebros activos para los 7 agentes en tiempo de ejecución.

    - Por defecto todos los roles apuntan 100% a NVIDIA NIM (según `DEFAULT_NVIDIA_BRAINS` / `agentes.yaml`).
    - Cualquier cambio realizado con `set_agent_brain(role, provider, model_name)` se refleja de inmediato.
    - Incluye la cadena silenciosa de rescate (`fallbacks`) calculada desde los proveedores activos.
    """
    activos = (
        proveedores_activos
        if proveedores_activos is not None
        else detectar_proveedores_activos(force_refresh=force_refresh)
    )
    yaml_modelos = cargar_config_agentes().get("modelos", {})
    manual_prov, manual_model = get_manual_override()

    resultado: Dict[str, Dict[str, Any]] = {}
    for role in AGENT_ROLES:
        profile = _ROLE_PROFILES.get(role, "razonamiento")
        yaml_role = yaml_modelos.get(role, {})
        temp = float(yaml_role.get("temperatura", DEFAULT_ROLE_TEMPERATURES.get(role, 0.2)))

        default_pair = DEFAULT_NVIDIA_BRAINS[role]
        active_prov, active_mod = ACTIVE_AGENT_BRAINS.get(role, default_pair)

        if manual_prov:
            prov_elegido = manual_prov
            mod_elegido = manual_model or _elegir_modelo_para_perfil(prov_elegido, profile, activos.get(prov_elegido))
            fuente = "override_global"
            is_custom = True
        else:
            prov_elegido = active_prov
            mod_elegido = active_mod
            is_custom = (prov_elegido, mod_elegido) != default_pair
            fuente = "personalizado" if is_custom else "nvidia_default"

        fallbacks_specs = _construir_lista_rescate_specs(prov_elegido, profile, activos)

        resultado[role] = {
            "provider": prov_elegido,
            "model": mod_elegido,
            "temperature": temp,
            "profile": profile,
            "is_custom": is_custom,
            "source": fuente,
            "fallbacks": fallbacks_specs,
        }

    return resultado


def asignar_cerebros_por_agente(
    proveedores_activos: Optional[Dict[str, List[str]]] = None,
    force_refresh: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Alias compatible con API/herramientas que devuelve `get_active_brains()`."""
    return get_active_brains(proveedores_activos=proveedores_activos, force_refresh=force_refresh)


# ---------------------------------------------------------------------------
# Instanciación de Modelos con Rescate Silencioso (.with_fallbacks)
# ---------------------------------------------------------------------------

def _instanciar_chat_model(
    provider: str,
    model_name: str,
    temperature: float,
    es_fallback: bool = False,
) -> Optional[BaseChatModel]:
    """Instancia un `BaseChatModel` concreto con timeouts cortos para evitar bloqueos de 30-60s."""
    prov_norm = (_normalizar_proveedor(provider) or "NVIDIA").upper()
    retries = 0
    req_timeout = 10.0 if es_fallback else 12.0

    try:
        if prov_norm == "NVIDIA":
            if not _credencial_valida(NVIDIA_API_KEY):
                return None
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            llm_nv = ChatNVIDIA(
                model=model_name,
                nvidia_api_key=NVIDIA_API_KEY,
                base_url=NVIDIA_BASE_URL,
                temperature=temperature,
            )
            if hasattr(llm_nv, "_client") and hasattr(llm_nv._client, "timeout"):
                llm_nv._client.timeout = (4.0, req_timeout)
            return llm_nv

        if prov_norm == "GEMINI":
            if not _credencial_valida(GEMINI_API_KEY):
                return None
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                google_api_key=GEMINI_API_KEY,
                timeout=req_timeout,
                max_retries=retries,
            )

        if prov_norm == "GROQ":
            if not _credencial_valida(GROQ_API_KEY):
                return None
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=model_name,
                temperature=temperature,
                api_key=GROQ_API_KEY,
                timeout=req_timeout,
                max_retries=retries,
            )

        if prov_norm == "COHERE":
            if not _credencial_valida(COHERE_API_KEY):
                return None
            from langchain_cohere import ChatCohere
            return ChatCohere(
                model=model_name,
                temperature=temperature,
                cohere_api_key=COHERE_API_KEY,
                timeout=req_timeout,
            )

        if prov_norm == "HUGGINGFACE":
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
            endpoint = HuggingFaceEndpoint(
                repo_id=model_name,
                huggingfacehub_api_token=HF_TOKEN,
                temperature=max(temperature, 0.01),
            )
            return ChatHuggingFace(llm=endpoint)

        if prov_norm == "OLLAMA":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=model_name,
                base_url=OLLAMA_BASE_URL,
                temperature=temperature,
                client_kwargs={"timeout": 20.0},
            )
    except Exception:
        return None

    return None


def get_llm(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    role: Optional[str] = None,
) -> Any:
    """
    Resuelve e instancia el LLM en tiempo de ejecución para el agente indicado:
      1. Si se pasan `provider`/`model_name` explícitos, se usan como modelo primario.
      2. Si hay un override por petición (`override_model_context`) o global, se respeta.
      3. Si se indica `role`, resuelve desde `ACTIVE_AGENT_BRAINS[role]` (100% NVIDIA por
         defecto, o el proveedor/modelo personalizado vía `set_agent_brain`).
      4. Siempre envuelve con `.with_fallbacks()` silencioso (`ResilientChatModel`) usando
         los demás proveedores activos ante caídas de red o errores de cuota.
    """
    activos = detectar_proveedores_activos()
    role_key = role.strip().lower() if role else None
    profile = _ROLE_PROFILES.get(role_key or "", "razonamiento")

    if temperature is None:
        yaml_role = cargar_config_agentes().get("modelos", {}).get(role_key or "", {})
        temp = float(yaml_role.get("temperatura", DEFAULT_ROLE_TEMPERATURES.get(role_key or "", 0.2)))
    else:
        temp = float(temperature)

    manual_prov, manual_model = get_manual_override()

    if provider:
        primary_provider = _normalizar_proveedor(provider) or "NVIDIA"
        primary_model = model_name or _elegir_modelo_para_perfil(
            primary_provider, profile, activos.get(primary_provider)
        )
    elif manual_prov:
        primary_provider = manual_prov
        primary_model = model_name or manual_model or _elegir_modelo_para_perfil(
            primary_provider, profile, activos.get(primary_provider)
        )
    elif role_key and role_key in AGENT_ROLES:
        primary_provider, assigned_model = ACTIVE_AGENT_BRAINS.get(role_key, DEFAULT_NVIDIA_BRAINS[role_key])
        primary_model = model_name or assigned_model
    else:
        primary_provider = "NVIDIA"
        primary_model = model_name or "nvidia/nemotron-3-super-120b-a12b"

    fallback_specs = _construir_lista_rescate_specs(primary_provider, profile, activos)

    # Si el proveedor primario está en cooldown por fallo reciente, promover un respaldo saludable
    # para evitar esperar timeouts repetidos en cada nodo del grafo.
    primary_llm = None
    if not _proveedor_en_cooldown(primary_provider):
        primary_llm = _instanciar_chat_model(primary_provider, primary_model, temp, es_fallback=False)

    fallbacks_list: List[BaseChatModel] = []
    for fb_spec in fallback_specs:
        if _proveedor_en_cooldown(fb_spec["provider"]):
            continue
        fb_llm = _instanciar_chat_model(fb_spec["provider"], fb_spec["model"], temp, es_fallback=True)
        if fb_llm is not None:
            fallbacks_list.append(fb_llm)

    if primary_llm is None:
        if fallbacks_list:
            primary_llm = fallbacks_list.pop(0)
        else:
            # Si todos estuvieron en cooldown, intentar instanciar el primario configurado de nuevo
            primary_llm = _instanciar_chat_model(primary_provider, primary_model, temp, es_fallback=False)
            if primary_llm is None:
                from langchain_ollama import ChatOllama
                primary_llm = ChatOllama(model="llama3.2", base_url=OLLAMA_BASE_URL, temperature=temp)

    return _envolver_con_rescate(primary_llm, fallbacks_list)


def get_llm_para_agente(nombre_agente: str) -> Any:
    """Alias retrocompatible que delega en `get_llm(role=nombre_agente)`."""
    return get_llm(role=nombre_agente)


# ---------------------------------------------------------------------------
# Embeddings, Configuración YAML y Listado de Modelos
# ---------------------------------------------------------------------------

def get_embeddings_model(provider: str = "HuggingFace", model_name: Optional[str] = None) -> Embeddings:
    """
    Fábrica unificada de modelos de embeddings:
    Soporta NVIDIA NIM (nv-embedqa-e5-v5), HuggingFace (all-MiniLM-L6-v2), Gemini y Ollama.
    """
    prov_norm = provider.strip().upper()

    if prov_norm == "NVIDIA" and _credencial_valida(NVIDIA_API_KEY):
        try:
            from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
            return NVIDIAEmbeddings(model=model_name or "nvidia/nv-embedqa-e5-v5", nvidia_api_key=NVIDIA_API_KEY)
        except Exception:
            pass

    if prov_norm == "GEMINI" and _credencial_valida(GEMINI_API_KEY):
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


def listar_modelos_disponibles(provider: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Descubre y devuelve la lista de modelos disponibles para cada proveedor
    reutilizando sus módulos especializados `models_*.py`.
    """
    resultado: Dict[str, List[str]] = {}
    prov_filter = (_normalizar_proveedor(provider) or "").upper() if provider else None

    if not prov_filter or prov_filter == "NVIDIA":
        from config.models_nvidia import obtener_modelos_nvidia
        resultado["NVIDIA"] = obtener_modelos_nvidia()

    if not prov_filter or prov_filter == "GEMINI":
        try:
            from config.models_gemini import obtener_modelos_gemini
            resultado["Gemini"] = obtener_modelos_gemini(tipo="chat")
        except Exception:
            resultado["Gemini"] = ["gemini-3.6-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]

    if not prov_filter or prov_filter == "GROQ":
        try:
            from config.models_groq import obtener_modelos_groq
            resultado["Groq"] = obtener_modelos_groq()
        except Exception:
            resultado["Groq"] = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

    if not prov_filter or prov_filter == "COHERE":
        try:
            from config.models_cohere import obtener_modelos_cohere
            resultado["Cohere"] = obtener_modelos_cohere(tipo="chat")
        except Exception:
            resultado["Cohere"] = ["command-r7b-12-2024", "command-r-08-2024", "command-r-plus-08-2024"]

    if not prov_filter or prov_filter == "OLLAMA":
        from config.models_ollama import obtener_modelos_ollama
        resultado["Ollama"] = obtener_modelos_ollama()

    if not prov_filter or prov_filter == "HUGGINGFACE":
        resultado["HuggingFace"] = [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "sentence-transformers/all-MiniLM-L6-v2",
        ]

    return resultado
