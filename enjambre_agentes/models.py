"""
models.py — Fábrica centralizada de modelos LLM y Embeddings.

Unifica soporte para:
1. NVIDIA NIM (ChatNVIDIA) — Inferencia de alta velocidad local o en la nube (DGX Spark / API).
2. Google Gemini (ChatGoogleGenerativeAI).
3. Groq Cloud (ChatGroq).
4. Cohere (ChatCohere).
5. Ollama Local (ChatOllama) para ejecución 100% offline.

NeMo Microservices (NVIDIA_BASE_URL apunta a la nube o a un NIM local / DGX Spark):
- `get_llm(..., role=...)`: mapeo por rol a modelo base o adaptador LoRA entrenado con
  SFT en NeMo Customizer (`NEMO_MODEL_<ROL>`).
- `get_nemo_embeddings_client()`: NeMo Retriever Embedding (`nv-embedqa-e5-v5`, 1024 dims).
- `get_nemo_reranker_client()`: NeMo Retriever Reranking (`nv-rerankqa-mistral-4b-v3`).
- Clientes `httpx` asíncronos con wrappers síncronos (`run_sync`) para los nodos del grafo.

Regla estricta: NO se leen archivos .env ni my_keys.py; todas las credenciales
se resuelven exclusivamente mediante variables de entorno estándar (os.getenv).
"""
from __future__ import annotations

import os
import json
import asyncio
import logging
import concurrent.futures
import urllib.request
from typing import List, Dict, Any, Optional, Sequence, Literal, Coroutine, TypeVar
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)
_T = TypeVar("_T")


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

# NeMo Microservices
NVIDIA_CLOUD_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_CLOUD_RERANK_URL = "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking"
NVIDIA_REASONING_FALLBACK = "nvidia/nemotron-3.5-super-vl-120b-a12b"
NEMO_EMBED_DEFAULT_MODEL = "nvidia/nv-embedqa-e5-v5"
NEMO_EMBED_DEFAULT_DIMS = 1024
NEMO_RERANK_DEFAULT_MODEL = "nvidia/nv-rerankqa-mistral-4b-v3"

# Rol del grafo -> sufijo de la variable NEMO_MODEL_<SUFIJO>
_ROLE_ENV_SUFFIX: Dict[str, str] = {
    "supervisor": "SUPERVISOR",
    "orquestador": "SUPERVISOR",
    "vendedor": "VENDEDOR",
    "control": "CONTROL",
    "tutor": "TUTOR",
    "tutor_ui": "TUTOR",
}

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

def resolve_role_model(role: Optional[str]) -> Optional[str]:
    """
    Resuelve el modelo NIM (base o adaptador LoRA de NeMo Customizer) para un rol.

    Orden: `NEMO_MODEL_<ROL>` -> `NVIDIA_REASONING_MODEL` -> `nvidia/nemotron-3.5-super-vl-120b-a12b`.
    Retorna None si no se indica rol (el llamador usa entonces su modelo por defecto).
    """
    if not role:
        return None
    key = role.strip().lower()
    suffix = _ROLE_ENV_SUFFIX.get(key, key.upper())
    return (
        os.getenv(f"NEMO_MODEL_{suffix}")
        or os.getenv("NVIDIA_REASONING_MODEL")
        or NVIDIA_REASONING_FALLBACK
    )


def get_llm(
    provider: str = "NVIDIA",
    model_name: Optional[str] = None,
    temperature: float = 0.2,
    streaming: bool = False,
    role: Optional[str] = None,
    **kwargs: Any
) -> BaseChatModel:
    """
    Fábrica universal de modelos de lenguaje agnóstica al proveedor.
    
    Args:
        provider: Proveedor LLM ('NVIDIA', 'Gemini', 'Groq', 'Cohere', 'Ollama').
        model_name: Nombre específico del modelo (None utiliza el predeterminado del proveedor).
        temperature: Temperatura de muestreo (0.0 = determinista, 1.0 = creativo).
        streaming: Si True, habilita generación en streaming.
        role: Rol del agente ('supervisor', 'vendedor', 'control', 'tutor_ui'). Solo aplica a
            NVIDIA/NIM: selecciona el modelo base o adaptador LoRA vía `NEMO_MODEL_<ROL>`.
            Un `model_name` explícito siempre tiene prioridad.
        kwargs: Parámetros adicionales para el cliente subyacente.
        
    Returns:
        Instancia compatible con BaseChatModel de LangChain.
    """
    prov = (provider or "NVIDIA").strip().lower()

    # ── 1. NVIDIA NIM (ChatNVIDIA) ──
    if prov in ("nvidia", "nim"):
        nvidia_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        final_model = model_name or resolve_role_model(role) or NVIDIA_DEFAULT_MODEL
        
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            # ChatNVIDIA no tiene parámetro `streaming` (acabaría en model_kwargs y se enviaría a la API):
            # el streaming se solicita al invocar con `.stream()`.
            return ChatNVIDIA(
                model=final_model,
                api_key=nvidia_key,
                base_url=base_url,
                temperature=temperature,
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
        from langchain_ollama import ChatOllama
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
# 3b. FÁBRICA CON FALLO AUTOMÁTICO ENTRE PROVEEDORES (get_llm_auto)
# ─────────────────────────────────────────────────────────────────────────────

_FALLBACK_PROVIDER_ORDER: List[str] = ["NVIDIA", "Gemini", "Cohere", "Ollama"]


def get_llm_auto(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    streaming: bool = False,
    role: Optional[str] = None,
    provider_order: Optional[List[str]] = None,
    **kwargs: Any
) -> BaseChatModel:
    """
    Intenta obtener un LLM probando proveedores en orden hasta que uno funcione.

    Orden por defecto: NVIDIA → Gemini → Cohere → Ollama.

    Args:
        model_name: Nombre del modelo (None usa el predeterminado de cada proveedor).
        temperature: Temperatura de muestreo.
        streaming: Habilitar streaming.
        role: Rol del agente (solo aplica a NVIDIA/NIM para NEMO_MODEL_<ROL>).
        provider_order: Lista personalizada de proveedores a probar.
        kwargs: Parámetros adicionales pasados a get_llm.

    Returns:
        Instancia compatible con BaseChatModel del primer proveedor disponible.

    Raises:
        RuntimeError: Si ningún proveedor puede inicializarse.
    """
    order = provider_order or _FALLBACK_PROVIDER_ORDER
    last_error: Optional[Exception] = None
    for prov in order:
        try:
            return get_llm(
                provider=prov,
                model_name=model_name,
                temperature=temperature,
                streaming=streaming,
                role=role,
                **kwargs,
            )
        except Exception as exc:
            last_error = exc
            logger.warning(f"Proveedor LLM '{prov}' no disponible ({exc}); probando siguiente...")
    raise RuntimeError(
        f"Ningún proveedor LLM disponible ({order}). Último error: {last_error}"
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


# ────────────────────────────────────────────────────────────────────────────────
# 5. NEMO RETRIEVER: CLIENTES HTTPX ASÍNCRONOS (EMBEDDING + RERANKING)
# ────────────────────────────────────────────────────────────────────────────────

class NemoServiceError(RuntimeError):
    """Fallo al invocar un microservicio NeMo / NIM (red, HTTP o contrato)."""


def run_sync(coro: Coroutine[Any, Any, _T]) -> _T:
    """
    Ejecuta una corrutina desde código síncrono (nodos de LangGraph).
    Si ya hay un event loop activo en el hilo actual (p. ej. endpoint async de FastAPI),
    la corrutina corre en un hilo auxiliar con su propio loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def nvidia_api_key() -> Optional[str]:
    return os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY")


def nvidia_base_url() -> str:
    return os.getenv("NVIDIA_BASE_URL", NVIDIA_CLOUD_BASE_URL).rstrip("/")


def _is_cloud_url(url: str) -> bool:
    return (urlparse(url).hostname or "") in {"integrate.api.nvidia.com", "ai.api.nvidia.com"}


def _embed_base_url(explicit: Optional[str] = None) -> str:
    return (explicit or os.getenv("NEMO_EMBED_BASE_URL") or nvidia_base_url()).rstrip("/")


def _rerank_endpoint(explicit: Optional[str] = None) -> str:
    """
    Nube: el reranker hospedado vive en ai.api.nvidia.com/v1/retrieval/nvidia/reranking.
    NIM local: `POST {base}/ranking` (p. ej. http://localhost:8002/v1/ranking).
    """
    url = explicit or os.getenv("NEMO_RERANK_URL")
    if url:
        return url.rstrip("/")
    base = (os.getenv("NEMO_RERANK_BASE_URL") or nvidia_base_url()).rstrip("/")
    return NVIDIA_CLOUD_RERANK_URL if _is_cloud_url(base) else f"{base}/ranking"


def nemo_is_configured() -> bool:
    """
    True si los servicios NeMo Retriever son alcanzables por configuración:
    hay API key (nube) o ambos endpoints apuntan a un NIM local.
    Evita intentos de red inútiles cuando no hay credenciales.
    """
    if nvidia_api_key():
        return True
    return not _is_cloud_url(_embed_base_url()) and not _is_cloud_url(_rerank_endpoint())


async def post_json_async(
    url: str,
    payload: Dict[str, Any],
    *,
    api_key: Optional[str] = None,
    timeout: float = 30.0,
    retries: int = 2,
) -> Dict[str, Any]:
    """POST JSON con httpx asíncrono y reintentos con backoff ante 429/5xx/red."""
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    last_exc: Optional[Exception] = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(retries + 1):
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                    await asyncio.sleep(0.5 * 2 ** attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                raise NemoServiceError(
                    f"{url} -> HTTP {exc.response.status_code}: {exc.response.text[:300]}"
                ) from exc
            except (httpx.HTTPError, ValueError) as exc:
                last_exc = exc
                if attempt < retries:
                    await asyncio.sleep(0.5 * 2 ** attempt)
    raise NemoServiceError(f"{url} no disponible: {last_exc}") from last_exc


class _EmbeddingItem(BaseModel):
    index: int
    embedding: List[float]


class _EmbeddingResponse(BaseModel):
    data: List[_EmbeddingItem]


class RerankHit(BaseModel):
    """Índice original del pasaje y logit de relevancia devuelto por el reranker."""
    index: int
    logit: float


class _RerankResponse(BaseModel):
    rankings: List[RerankHit]


class NemoEmbeddingsClient(Embeddings):
    """
    NeMo Retriever Embedding NIM (`nvidia/nv-embedqa-e5-v5`, 1024 dims).

    Modelo asimétrico: usar `input_type="query"` para consultas y `"passage"` para
    documentos indexados. Compatible con la interfaz `Embeddings` de LangChain.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        dims: Optional[int] = None,
        timeout: float = 30.0,
        batch_size: int = 32,
    ) -> None:
        self.model = model or os.getenv("NEMO_EMBED_MODEL", NEMO_EMBED_DEFAULT_MODEL)
        self.base_url = _embed_base_url(base_url)
        self.api_key = api_key if api_key is not None else nvidia_api_key()
        self.dims = dims or int(os.getenv("NEMO_EMBED_DIMS", NEMO_EMBED_DEFAULT_DIMS))
        self.timeout = timeout
        self.batch_size = max(1, batch_size)

    async def aembed(
        self, texts: Sequence[str], input_type: Literal["query", "passage"]
    ) -> List[List[float]]:
        vectors: List[List[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = [t if t.strip() else " " for t in texts[start:start + self.batch_size]]
            raw = await post_json_async(
                f"{self.base_url}/embeddings",
                {
                    "model": self.model,
                    "input": batch,
                    "input_type": input_type,
                    "encoding_format": "float",
                    "truncate": "END",
                },
                api_key=self.api_key,
                timeout=self.timeout,
            )
            items = sorted(_EmbeddingResponse.model_validate(raw).data, key=lambda d: d.index)
            if len(items) != len(batch):
                raise NemoServiceError(
                    f"Embedding devolvió {len(items)} vectores para {len(batch)} textos."
                )
            for item in items:
                if len(item.embedding) != self.dims:
                    raise NemoServiceError(
                        f"Dimensión inesperada {len(item.embedding)} (esperada {self.dims}) "
                        f"para el modelo '{self.model}'. Ajusta NEMO_EMBED_DIMS y la columna vector()."
                    )
                vectors.append(item.embedding)
        return vectors

    async def aembed_query(self, text: str) -> List[float]:
        return (await self.aembed([text], "query"))[0]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return await self.aembed(texts, "passage")

    def embed_query(self, text: str) -> List[float]:
        return run_sync(self.aembed_query(text))

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return run_sync(self.aembed_documents(texts))


class NemoRerankerClient:
    """NeMo Retriever Reranking NIM (`nvidia/nv-rerankqa-mistral-4b-v3`)."""

    def __init__(
        self,
        model: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.model = model or os.getenv("NEMO_RERANK_MODEL", NEMO_RERANK_DEFAULT_MODEL)
        self.endpoint = _rerank_endpoint(endpoint)
        self.api_key = api_key if api_key is not None else nvidia_api_key()
        self.timeout = timeout

    async def arerank(
        self, query: str, passages: Sequence[str], top_n: Optional[int] = None
    ) -> List[RerankHit]:
        """Devuelve los pasajes ordenados por relevancia descendente (máx. 512 por petición)."""
        if not passages:
            return []
        raw = await post_json_async(
            self.endpoint,
            {
                "model": self.model,
                "query": {"text": query},
                "passages": [{"text": p if p.strip() else " "} for p in passages],
                "truncate": "END",
            },
            api_key=self.api_key,
            timeout=self.timeout,
        )
        hits = _RerankResponse.model_validate(raw).rankings
        if any(not 0 <= h.index < len(passages) for h in hits):
            raise NemoServiceError("El reranker devolvió índices fuera de rango.")
        hits.sort(key=lambda h: h.logit, reverse=True)
        return hits[:top_n] if top_n else hits

    def rerank(
        self, query: str, passages: Sequence[str], top_n: Optional[int] = None
    ) -> List[RerankHit]:
        return run_sync(self.arerank(query, passages, top_n))


def get_nemo_embeddings_client(
    model_name: Optional[str] = None, base_url: Optional[str] = None
) -> NemoEmbeddingsClient:
    """Cliente de embeddings NeMo Retriever (nube o NIM local vía NVIDIA_BASE_URL / NEMO_EMBED_BASE_URL)."""
    return NemoEmbeddingsClient(model=model_name, base_url=base_url)


def get_nemo_reranker_client(
    model_name: Optional[str] = None, endpoint: Optional[str] = None
) -> NemoRerankerClient:
    """Cliente de reranking NeMo Retriever (nube o NIM local vía NVIDIA_BASE_URL / NEMO_RERANK_URL)."""
    return NemoRerankerClient(model=model_name, endpoint=endpoint)
