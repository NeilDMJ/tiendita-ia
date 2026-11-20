"""
API REST y Servidor de Streaming (SSE) de Tiendita IA — Paridad 100% con el CLI Interactivo.
Diseñada para consumo directo desde aplicaciones móviles (Flutter / React Native / Android / iOS)
mediante contratos JSON estrictos, sesiones persistentes (`thread_id`) y pausa/reanudación HITL.

Endpoints:
  Sistema y Salud:
    - GET  /health                   -> Salud del servicio + métricas en vivo de PostgreSQL (tiendita-db)
    - GET  /models                   -> Modelos disponibles por proveedor, estado en vivo y cerebros activos
    - GET  /tools/mcp                -> Manifiesto MCP de las 24 herramientas comerciales

  Gestión de Cerebros por Agente (Runtime, igual que /cerebro, /cerebros, /reset-cerebros):
    - GET  /brains                   -> Tabla de los 7 agentes, proveedor/modelo activo y rescate silencioso
    - PUT  /brains/{role}            -> Cambia el proveedor y modelo de un subagente en vivo
    - POST /brains/reset             -> Restaura los 7 agentes al perfil exclusivo 100% NVIDIA NIM

  Orquestación Multiagente y Estado (igual que chat libre, HITL y /estado):
    - POST /orchestrate              -> Ejecución síncrona del enjambre (JSON limpio + thread_id + HITL)
    - POST /orchestrate/stream       -> Streaming SSE (Server-Sent Events) nodo por nodo
    - POST /orchestrate/resume       -> Reanudación HITL [aprobar / rechazar / editar] con COMMIT real
    - GET  /state/{thread_id}        -> Inspección de OrchestratorState real + métricas vivas de BD

  Pagos Digitales MX (CoDi / SPEI / DiMo) y RAG (igual que /pago y /rag):
    - POST /pago                     -> Copiloto Tutor UI (máx. 2 oraciones respaldadas por RAG Banxico)
    - POST /rag/search               -> Búsqueda semántica en FAISS / pgvector con puntuación de relevancia
    - GET  /rag/search               -> Variante GET rápida (?q=...&metodo=codi|spei|dimo&top_k=5)

  Visión Multimodal, Cron y Reportes (igual que /imagen y /cron):
    - POST /imagen                   -> Endpoint unificado de imagen base64 (mode: catalog | pos | ticket)
    - POST /catalog-scan             -> Escaneo visual de catálogo y anaqueles (NIM Vision -> control)
    - POST /pos-checkout             -> Identificación visual en mostrador POS (NIM Vision -> vendedor)
    - POST /receipt-ocr              -> OCR y clasificación contable de tickets (NIM Vision -> control)
    - POST /cron                     -> Barrido real de caducidades y stock bajo (control -> publicista)
    - GET  /reports/history          -> Listado de reportes estratégicos históricos
    - GET  /reports/{report_id}      -> Detalle JSON completo (9 secciones) de un reporte histórico
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from config.keys import API_HOST, API_PORT, get_tiendita_api_key
from config.models import (
    AGENT_ROLES,
    PROVIDERS,
    extraer_texto_mensaje,
    get_active_brains,
    listar_modelos_disponibles,
    obtener_estado_proveedores,
    reset_brains_to_nvidia_default,
    set_agent_brain,
)
from agents.graph import (
    get_graph_state,
    resume_orchestration,
    run_orchestration,
    run_orchestration_stream,
    tiendita_graph,
)
from config.models import override_model_context
from schemas.vision import CatalogScanRequest, POSCheckoutRequest, ReceiptOCRRequest
from tools.db_client import close_db_pool, verify_db_connection
from tools.mcp_exporter import export_mcp_manifest
from tools.rag_nemo import buscar_rag_pagos


# ---------------------------------------------------------------------------
# Ciclo de vida FastAPI (cierre limpio del pool PostgreSQL)
# ---------------------------------------------------------------------------

@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    # Arranque: validar que existe el directorio de reportes
    REPORTES_DIR.mkdir(parents=True, exist_ok=True)
    # Asistente bancario (back/app): precalienta Ollama si está configurado
    async with (_ciclo_banco(_app) if _ciclo_banco else contextlib.nullcontext()):
        yield
    # Apagado: cerrar limpiamente todas las conexiones abiertas en el pool
    close_db_pool()


app = FastAPI(
    title="Tiendita IA API",
    description=(
        "API REST JSON y SSE del Ecosistema Comercial Multimodal Tiendita IA "
        "(LangGraph + NVIDIA NIM/NeMo + PostgreSQL/pgvector + RAG CoDi/SPEI/DiMo)."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Servicios de back/ montados en este mismo servidor (un solo puerto para la app) ──
#   back/vision → /vision/pos-checkout, /vision/catalog-scan, /vision/receipt-ocr, /vision/salud
#                 (si deseas separarlo al puerto 8001 con `python -m vision.server`, pon MOUNT_VISION_IN_API=0)
#   back/app    → /asistente/mensaje (agente guía bancario) y /salud
# back/ no es paquete (back/tests importa `app` como módulo de primer nivel): se agrega back/ al
# FINAL del path para no tapar los paquetes de enjambre_agentes (config, tools, scripts...).
import sys  # noqa: E402

_DIR_BACK = str(Path(__file__).resolve().parent.parent / "back")
if _DIR_BACK not in sys.path:
    sys.path.append(_DIR_BACK)

_MOUNT_VISION_IN_API = os.getenv("MOUNT_VISION_IN_API", "1").strip().lower() in {"1", "true", "yes"}
if _MOUNT_VISION_IN_API:
    try:
        from vision import router as vision_router  # noqa: E402

        app.include_router(vision_router)
    except ImportError as _e:  # sin onnxruntime/pillow el resto de la API sigue funcionando
        print(f"⚠ Visión deshabilitada: {_e}. Instala: uv add onnxruntime pillow numpy python-multipart")

_ciclo_banco = None
try:
    from app.main import ciclo_de_vida as _ciclo_banco, router as banco_router  # noqa: E402

    app.include_router(banco_router)
except ImportError as _e:
    print(f"⚠ Asistente bancario deshabilitado: {_e}. Instala: uv add pydantic-settings httpx")

# Rutas públicas exentas de autenticación X-API-Key cuando TIENDITA_API_KEY está activa
_PUBLIC_REST_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/docs/oauth2-redirect",
}


def _verificar_api_key(provided: Optional[str]) -> bool:
    """Valida API key con comparación en tiempo constante. Si TIENDITA_API_KEY está vacía, permite acceso abierto."""
    expected = get_tiendita_api_key()
    if not expected:
        return True
    if not provided:
        return False
    return hmac.compare_digest(provided.strip(), expected)


@app.middleware("http")
async def optional_api_key_middleware(request: Request, call_next):
    """
    Autenticación opcional por header `X-API-Key` cuando `TIENDITA_API_KEY` está definida en `.env`.
    Permite siempre `/health`, `/docs`, `/openapi.json` y preflights CORS `OPTIONS`.
    """
    if request.method == "OPTIONS" or request.url.path in _PUBLIC_REST_PATHS:
        return await call_next(request)

    if not _verificar_api_key(request.headers.get("X-API-Key")):
        return JSONResponse(
            status_code=401,
            content={"detail": "API Key inválida o faltante en el header 'X-API-Key'."},
        )

    return await call_next(request)

REPORTES_DIR = Path(__file__).resolve().parent / "data" / "reportes"
REPORTES_DIR.mkdir(parents=True, exist_ok=True)

_IMAGE_MODE_ENDPOINTS = {
    "catalog": "/catalog-scan",
    "pos": "/pos-checkout",
    "ticket": "/receipt-ocr",
}


# ---------------------------------------------------------------------------
# Esquemas Pydantic de Solicitudes JSON (Mobile-Friendly)
# ---------------------------------------------------------------------------

class OrchestrateRequest(BaseModel):
    input_text: str = Field(..., description="Mensaje, consulta o instrucción comercial del usuario.")
    thread_id: Optional[str] = Field(default=None, description="ID de sesión conversacional. Si se omite, la API genera y devuelve uno.")
    event_source: str = Field(
        default="chat",
        description="Fuente del evento: 'chat', 'vision_api', 'ui_copilot', 'cron', 'catalog-scan', 'pos-checkout', 'receipt-ocr'.",
    )
    vision_payload: Optional[Dict[str, Any]] = Field(default=None, description="Carga multimodal en base64 si aplica.")
    ui_state: Optional[Dict[str, Any]] = Field(default=None, description="Estado de pantalla de pago digital si aplica.")
    provider: Optional[str] = Field(default=None, description="Override temporal de proveedor LLM para esta petición.")
    model_name: Optional[str] = Field(default=None, description="Override temporal de modelo LLM para esta petición.")


class ResumeRequest(BaseModel):
    thread_id: str = Field(..., description="ID del hilo pausado en 'approval_gate'.")
    approved: Optional[bool] = Field(
        default=None,
        description="True para autorizar y confirmar COMMIT en BD; False para rechazar.",
    )
    action: Optional[str] = Field(
        default=None,
        description="Alias opcional compatible ('approve' / 'reject') si no se envía 'approved'.",
    )
    correction: Optional[str] = Field(default=None, description="Corrección del operador (equivalente a [e] Editar en CLI).")
    notes: Optional[str] = Field(default=None, description="Notas o motivo de auditoría humana.")

    def resolved_approved(self) -> bool:
        if self.approved is not None:
            return bool(self.approved)
        act = (self.action or "").strip().lower()
        if act in ("approve", "aprobar", "s", "si", "sí", "true"):
            return True
        if act in ("reject", "rechazar", "n", "no", "false"):
            return False
        raise ValueError("Debes enviar 'approved' (true/false) o 'action' ('approve'/'reject').")


class UpdateBrainRequest(BaseModel):
    provider: str = Field(..., description=f"Proveedor LLM ({', '.join(PROVIDERS)}).")
    model_name: str = Field(..., description="Identificador exacto del modelo a asignar al subagente.")


class PagoCopilotRequest(BaseModel):
    metodo_pago: Literal["codi", "spei", "dimo", "tarjeta"] = Field(..., description="Método de pago digital (codi, spei, dimo, tarjeta).")
    pantalla: str = Field(..., description="Pantalla actual del flujo (ej. 'cobro_qr', 'transferir', 'confirmacion', 'comprobante').")
    paso: int = Field(default=1, ge=1, description="Número de paso en pantalla.")
    error_code: Optional[str] = Field(default=None, description="Código o mensaje de error visible si existe.")
    duda: Optional[str] = Field(default=None, description="Pregunta adicional opcional del usuario/cajero.")
    monto_pendiente: Optional[float] = Field(default=None, description="Importe pendiente de cobro en MXN (opcional).")
    thread_id: Optional[str] = Field(default=None, description="ID de sesión opcional.")


class RagSearchRequest(BaseModel):
    consulta: str = Field(..., min_length=1, description="Consulta sobre CoDi, SPEI, DiMo o políticas comerciales.")
    metodo_pago: Optional[Literal["codi", "spei", "dimo"]] = Field(default=None, description="Filtro opcional por método de pago.")
    top_k: int = Field(default=5, ge=1, le=20, description="Número máximo de fragmentos a devolver.")
    preferir_pgvector: bool = Field(default=False, description="Si True, consulta directamente el índice HNSW de PostgreSQL pgvector.")


class ImageUploadRequest(BaseModel):
    image_b64: str = Field(..., min_length=16, description="Imagen codificada en Base64 capturada desde la app móvil.")
    mode: Literal["catalog", "pos", "ticket"] = Field(..., description="Modo de procesamiento: 'catalog', 'pos' o 'ticket'.")
    mime_type: str = Field(default="image/jpeg", description="Tipo MIME (image/jpeg, image/png, image/webp).")
    filename: Optional[str] = Field(default="mobile_capture.jpg", description="Nombre opcional del archivo.")
    categoria_sugerida: Optional[str] = Field(default=None, description="Categoría sugerida (solo para mode='catalog').")
    id_carrito_activo: Optional[str] = Field(default=None, description="ID de carrito activo (solo para mode='pos').")
    thread_id: Optional[str] = Field(default=None, description="ID de sesión opcional.")


class CronRequest(BaseModel):
    thread_id: Optional[str] = Field(default=None, description="ID de sesión opcional para auditar o aprobar el barrido HITL.")
    days_ahead: int = Field(default=7, ge=1, le=60, description="Ventana de días para alertar lotes próximos a caducar.")


# ---------------------------------------------------------------------------
# Serializadores JSON Limpios para Clientes Móviles
# ---------------------------------------------------------------------------

def _serializar_mensajes(messages: List[Any]) -> List[Dict[str, Any]]:
    """Convierte mensajes de LangGraph a dicts JSON limpios con texto plano garantizado."""
    salida: List[Dict[str, Any]] = []
    for m in messages or []:
        if hasattr(m, "content"):
            role = getattr(m, "type", "ai")
            texto = extraer_texto_mensaje(m.content)
            salida.append({"role": role, "content": texto})
        elif isinstance(m, dict):
            salida.append({
                "role": str(m.get("role", m.get("type", "ai"))),
                "content": extraer_texto_mensaje(m.get("content", "")),
            })
    return salida


def _extraer_respuesta_principal(mensajes_json: List[Dict[str, Any]]) -> str:
    """Extrae la respuesta final orientada al usuario (omitiendo trazas internas del supervisor si hay respuesta del especialista)."""
    for m in reversed(mensajes_json):
        if m.get("role") != "human":
            txt = (m.get("content") or "").strip()
            if txt and not txt.startswith("(・_・)? [SUPERVISOR]"):
                return txt
    for m in reversed(mensajes_json):
        if m.get("role") != "human" and (m.get("content") or "").strip():
            return m["content"].strip()
    return ""


def _formatear_respuesta_orquestacion(thread_id: str, resultado: Dict[str, Any]) -> Dict[str, Any]:
    """Construye un payload JSON uniforme, 100% serializable y listo para apps móviles."""
    mensajes_json = _serializar_mensajes(resultado.get("messages", []))
    snap = get_graph_state(thread_id)
    next_nodes = snap.get("next") or []
    pending = (snap.get("values") or {}).get("pending_approval") or resultado.get("pending_approval")
    requires_approval = bool(
        "approval_gate" in next_nodes
        or (isinstance(pending, dict) and pending.get("requires_human") and pending.get("status") == "pending")
    )

    return {
        "status": "pending_approval" if requires_approval else "completed",
        "thread_id": thread_id,
        "next_agent": resultado.get("next_agent"),
        "next_nodes": next_nodes,
        "reply": _extraer_respuesta_principal(mensajes_json),
        "messages": mensajes_json,
        "requires_approval": requires_approval,
        "pending_approval": pending,
        "db_evidence": resultado.get("db_evidence"),
        "strategic_report": resultado.get("strategic_report"),
        "promo_assets": resultado.get("promo_assets"),
        "iteration_count": resultado.get("iteration_count", 0),
    }


def _serializar_evento_sse(evento: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza un evento de LangGraph stream para emitir JSON limpio por SSE."""
    limpio: Dict[str, Any] = {}
    for nodo, datos in evento.items():
        if isinstance(datos, dict):
            item = dict(datos)
            if "messages" in item:
                item["messages"] = _serializar_mensajes(item["messages"])
            limpio[nodo] = item
        else:
            limpio[nodo] = datos
    return limpio


# ---------------------------------------------------------------------------
# 1. Salud, Modelos y Manifiesto MCP
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Verifica la salud del microservicio y la conexión real en vivo con PostgreSQL (tiendita-db)."""
    db_info = verify_db_connection()
    return {
        "status": "healthy" if db_info.get("connected") else "degraded",
        "service": "Tiendita IA",
        "version": "2.0.0",
        "auth_enabled": bool(get_tiendita_api_key()),
        "database": db_info,
        "capabilities": {
            "multimodal_vision": True,
            "nemo_retriever": True,
            "dual_rag_pagos_mx": ["codi", "spei", "dimo"],
            "hitl_enabled": True,
            "websocket_bidirectional": True,
            "runtime_brain_switching": True,
        },
        "providers_supported": PROVIDERS,
        "agent_roles": AGENT_ROLES,
    }


@app.get("/models")
def get_models(provider: Optional[str] = Query(default=None, description="Filtrar por proveedor específico.")):
    """Consulta en vivo modelos disponibles, estado de proveedores y asignación actual de cerebros."""
    return {
        "status": "success",
        "modelos": listar_modelos_disponibles(provider),
        "estado_proveedores": obtener_estado_proveedores(),
        "cerebros_por_agente": get_active_brains(),
    }


@app.get("/tools/mcp")
def get_mcp_tools():
    """Devuelve el manifiesto MCP JSON de todas las herramientas comerciales del enjambre."""
    return export_mcp_manifest()


# ---------------------------------------------------------------------------
# 2. Gestión de Cerebros por Agente en Runtime (/cerebros, /cerebro, /reset-cerebros)
# ---------------------------------------------------------------------------

@app.get("/brains")
def api_get_brains(refresh: bool = Query(default=False, description="Si True, re-sondea proveedores en vivo.")):
    """Devuelve los cerebros activos de los 7 agentes, su cadena de rescate y estado de proveedores."""
    return {
        "status": "success",
        "estado_proveedores": obtener_estado_proveedores(force_refresh=refresh),
        "brains": get_active_brains(force_refresh=False),
    }


@app.put("/brains/{role}")
def api_set_agent_brain(role: str, req: UpdateBrainRequest):
    """Cambia en vivo el proveedor y modelo de un subagente específico (equivalente a `/cerebro`)."""
    try:
        prov_ok, mod_ok = set_agent_brain(role, req.provider, req.model_name)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    return {
        "status": "updated",
        "role": role.strip().lower(),
        "provider": prov_ok,
        "model_name": mod_ok,
        "brains": get_active_brains(),
    }


@app.post("/brains/reset")
def api_reset_brains():
    """Restaura los 7 agentes al perfil exclusivo 100% NVIDIA NIM (equivalente a `/reset-cerebros`)."""
    reset_brains_to_nvidia_default()
    return {
        "status": "reset",
        "mode": "nvidia_default",
        "brains": get_active_brains(),
    }


# ---------------------------------------------------------------------------
# 3. Orquestación Principal, Streaming SSE, HITL y Estado
# ---------------------------------------------------------------------------

@app.post("/orchestrate")
def orchestrate_sync(req: OrchestrateRequest):
    """Ejecuta un ciclo síncrono de orquestación devolviendo JSON limpio y thread_id persistente."""
    tid = req.thread_id or str(uuid.uuid4())
    try:
        resultado = run_orchestration(
            input_text=req.input_text,
            thread_id=tid,
            event_source=req.event_source,
            vision_payload=req.vision_payload,
            ui_state=req.ui_state,
            provider=req.provider,
            model_name=req.model_name,
        )
        return _formatear_respuesta_orquestacion(tid, resultado)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrate/stream")
async def orchestrate_streaming(req: OrchestrateRequest):
    """Transmite eventos SSE (JSON limpio) en tiempo real conforme cada nodo termina."""
    tid = req.thread_id or str(uuid.uuid4())

    async def event_generator():
        yield f"data: {json.dumps({'event': 'session_started', 'thread_id': tid}, ensure_ascii=False)}\n\n"
        try:
            async for evento in run_orchestration_stream(
                input_text=req.input_text,
                thread_id=tid,
                event_source=req.event_source,
                vision_payload=req.vision_payload,
                ui_state=req.ui_state,
                provider=req.provider,
                model_name=req.model_name,
            ):
                limpio = _serializar_evento_sse(evento)
                payload_json = json.dumps({"thread_id": tid, "data": limpio}, default=str, ensure_ascii=False)
                yield f"data: {payload_json}\n\n"

            snap = get_graph_state(tid)
            pending = (snap.get("values") or {}).get("pending_approval")
            paused = "approval_gate" in (snap.get("next") or [])
            yield f"data: {json.dumps({'event': 'done', 'thread_id': tid, 'requires_approval': paused, 'pending_approval': pending}, default=str, ensure_ascii=False)}\n\n"
        except Exception as err:
            yield f"data: {json.dumps({'event': 'error', 'thread_id': tid, 'error': str(err)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/orchestrate/resume")
def resume_hitl(req: ResumeRequest):
    """
    Reanuda un hilo pausado en `approval_gate` (HITL):
    confirma el COMMIT real en PostgreSQL si approved=True, o cancela limpiamente si approved=False.
    """
    snap = get_graph_state(req.thread_id)
    if not snap or not snap.get("values"):
        raise HTTPException(status_code=404, detail=f"No existe estado activo para thread_id='{req.thread_id}'.")
    try:
        is_approved = req.resolved_approved()
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))
    try:
        resultado = resume_orchestration(
            thread_id=req.thread_id,
            approved=is_approved,
            correction=req.correction,
            notes=req.notes,
        )
        respuesta = _formatear_respuesta_orquestacion(req.thread_id, resultado)
        respuesta["status"] = "approved_and_resumed" if is_approved else "rejected_and_resumed"
        respuesta["approved"] = is_approved
        return respuesta
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state/{thread_id}")
def api_get_state(thread_id: str):
    """Inspecciona el OrchestratorState real del checkpointer y métricas vivas de BD (equivalente a `/estado`)."""
    snap = get_graph_state(thread_id)
    vals = snap.get("values") or {}
    next_nodes = snap.get("next") or []
    mensajes_json = _serializar_mensajes(vals.get("messages", []))

    return {
        "status": "found" if vals else "empty",
        "thread_id": thread_id,
        "state": {
            "event_source": vals.get("event_source"),
            "next_agent": vals.get("next_agent"),
            "next_nodes": next_nodes,
            "iteration_count": vals.get("iteration_count", 0),
            "total_messages": len(mensajes_json),
            "db_evidence": vals.get("db_evidence"),
            "strategic_report": vals.get("strategic_report"),
            "promo_assets": vals.get("promo_assets"),
            "pending_approval": vals.get("pending_approval"),
        },
        "database": verify_db_connection(),
    }


# ---------------------------------------------------------------------------
# 4. Pagos Digitales MX (CoDi / SPEI / DiMo) y RAG (/pago y /rag)
# ---------------------------------------------------------------------------

@app.post("/pago")
@app.post("/ui-copilot")
def api_pago_copilot(req: PagoCopilotRequest):
    """
    Copiloto de pantalla Tutor UI para CoDi, SPEI y DiMo (equivalente a `/pago`).
    Devuelve máximo 2 oraciones accionables respaldadas por el RAG de Banxico (`guias.json` + `conocimiento.jsonl`).
    """
    tid = req.thread_id or str(uuid.uuid4())
    ui_state = {
        "payment_method": req.metodo_pago,
        "screen": req.pantalla,
        "step": req.paso,
        "error_code": req.error_code,
        "monto_pendiente": req.monto_pendiente,
    }
    texto = (
        req.duda.strip()
        if req.duda and req.duda.strip()
        else (
            f"Asistencia de pago digital {req.metodo_pago.upper()} en pantalla '{req.pantalla}' (paso {req.paso})"
            + (f" con error '{req.error_code}'." if req.error_code else ".")
        )
    )
    try:
        resultado = run_orchestration(
            input_text=texto,
            thread_id=tid,
            event_source="ui_copilot",
            ui_state=ui_state,
        )
        resp = _formatear_respuesta_orquestacion(tid, resultado)
        resp["ui_state"] = ui_state
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/search")
def api_rag_search_post(req: RagSearchRequest):
    """Consulta el índice RAG de pagos digitales CoDi/SPEI/DiMo en FAISS o pgvector (equivalente a `/rag`)."""
    try:
        data = buscar_rag_pagos(
            consulta=req.consulta,
            top_k=req.top_k,
            metodo_pago=req.metodo_pago,
            preferir_pgvector=req.preferir_pgvector,
        )
        return {"status": "success", **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/search")
def api_rag_search_get(
    q: str = Query(..., min_length=1, description="Consulta semántica sobre CoDi, SPEI o DiMo."),
    metodo: Optional[Literal["codi", "spei", "dimo"]] = Query(default=None, description="Filtro opcional por método."),
    top_k: int = Query(default=5, ge=1, le=20),
    preferir_pgvector: bool = Query(default=False),
):
    """Variante GET de `/rag/search` para consultas rápidas desde móvil o navegador."""
    try:
        data = buscar_rag_pagos(
            consulta=q,
            top_k=top_k,
            metodo_pago=metodo,
            preferir_pgvector=preferir_pgvector,
        )
        return {"status": "success", **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 5. Visión Multimodal (/imagen, /catalog-scan, /pos-checkout, /receipt-ocr) y /cron
# ---------------------------------------------------------------------------

@app.post("/imagen")
def api_imagen_unificada(req: ImageUploadRequest):
    """
    Endpoint multimodal unificado (equivalente a `/imagen <archivo> <catalog|pos|ticket>`).
    Recibe una foto real en Base64 desde la cámara de la app móvil y la procesa vía NIM Vision.
    """
    tid = req.thread_id or str(uuid.uuid4())
    prompts = {
        "catalog": f"Analiza esta fotografía real de anaquel/catálogo ({req.filename}) con NIM Vision y contrasta con el inventario en PostgreSQL.",
        "pos": f"Identifica los artículos reales en mostrador POS en esta foto ({req.filename}) con NIM Vision y cotízalos contra PostgreSQL.",
        "ticket": f"Ejecuta OCR real sobre este comprobante/ticket ({req.filename}) con NIM Vision y clasifica contablemente el gasto.",
    }
    vision_payload: Dict[str, Any] = {
        "mode": req.mode,
        "endpoint": _IMAGE_MODE_ENDPOINTS[req.mode],
        "file_path": req.filename,
        "mime_type": req.mime_type,
        "image_b64": req.image_b64,
    }
    if req.categoria_sugerida:
        vision_payload["categoria_sugerida"] = req.categoria_sugerida
    if req.id_carrito_activo:
        vision_payload["id_carrito_activo"] = req.id_carrito_activo

    try:
        resultado = run_orchestration(
            input_text=prompts[req.mode],
            thread_id=tid,
            event_source="vision_api",
            vision_payload=vision_payload,
        )
        resp = _formatear_respuesta_orquestacion(tid, resultado)
        resp["mode"] = req.mode
        resp["endpoint"] = _IMAGE_MODE_ENDPOINTS[req.mode]
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/catalog-scan")
def api_catalog_scan(req: CatalogScanRequest):
    """Procesa una fotografía real de catálogo o anaquel para altas e inventario."""
    tid = str(uuid.uuid4())
    payload = {
        "mode": "catalog",
        "endpoint": "/catalog-scan",
        "image_b64": req.image_b64,
        "mime_type": req.mime_type,
        "categoria_sugerida": req.categoria_sugerida,
    }
    resultado = run_orchestration(
        input_text="Escaneo de catálogo o anaquel recibido para procesar inventario.",
        thread_id=tid,
        event_source="catalog-scan",
        vision_payload=payload,
    )
    resp = _formatear_respuesta_orquestacion(tid, resultado)
    resp["endpoint"] = "/catalog-scan"
    resp["resultado"] = resp["reply"]
    return resp


@app.post("/pos-checkout")
def api_pos_checkout(req: POSCheckoutRequest):
    """Identifica visualmente artículos en mostrador de caja y genera cotización."""
    tid = str(uuid.uuid4())
    payload = {
        "mode": "pos",
        "endpoint": "/pos-checkout",
        "image_b64": req.image_b64,
        "mime_type": req.mime_type,
        "id_carrito_activo": req.id_carrito_activo,
    }
    resultado = run_orchestration(
        input_text="Artículos detectados en mostrador POS para cotizar y agregar al carrito.",
        thread_id=tid,
        event_source="pos-checkout",
        vision_payload=payload,
    )
    resp = _formatear_respuesta_orquestacion(tid, resultado)
    resp["endpoint"] = "/pos-checkout"
    resp["resultado"] = resp["reply"]
    return resp


@app.post("/receipt-ocr")
def api_receipt_ocr(req: ReceiptOCRRequest):
    """Extrae texto de un ticket y clasifica en 'inversion_inventario' vs 'gasto_operativo'."""
    tid = str(uuid.uuid4())
    payload = {
        "mode": "ticket",
        "endpoint": "/receipt-ocr",
        "image_b64": req.image_b64,
        "mime_type": req.mime_type,
    }
    resultado = run_orchestration(
        input_text="Comprobante de compra recibido para auditoría y clasificación contable.",
        thread_id=tid,
        event_source="receipt-ocr",
        vision_payload=payload,
    )
    resp = _formatear_respuesta_orquestacion(tid, resultado)
    resp["endpoint"] = "/receipt-ocr"
    resp["resultado"] = resp["reply"]
    return resp


@app.post("/cron")
def api_cron_sweep(req: Optional[CronRequest] = None):
    """
    Ejecuta el barrido real de lotes próximos a caducar y stock crítico en PostgreSQL
    (equivalente a `/cron`: control -> publicista con pausa HITL si se genera campaña).
    """
    cfg = req or CronRequest()
    tid = cfg.thread_id or str(uuid.uuid4())
    try:
        resultado = run_orchestration(
            input_text=(
                f"Ejecuta el barrido programado real sobre PostgreSQL (ventana {cfg.days_ahead} días): "
                "revisa lotes próximos a caducar (v_por_caducar) y alertas de stock crítico (v_stock_bajo). "
                "Si detectas alertas reales, encadena al publicista para proponer campaña de rescate."
            ),
            thread_id=tid,
            event_source="cron",
        )
        return _formatear_respuesta_orquestacion(tid, resultado)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 6. Reportes Estratégicos Históricos
# ---------------------------------------------------------------------------

@app.get("/reports/history")
def get_reports_history():
    """Lista los reportes estratégicos de 9 secciones guardados históricamente."""
    archivos = list(REPORTES_DIR.glob("*.json"))
    reportes_lista = []
    for arc in sorted(archivos, reverse=True)[:20]:
        try:
            with open(arc, "r", encoding="utf-8") as f:
                datos = json.load(f)
                reportes_lista.append({
                    "id": arc.stem,
                    "sector": datos.get("identificacion_sector", "Sector no especificado")[:100],
                    "archivo": arc.name,
                })
        except Exception:
            pass
    return {
        "status": "success",
        "total_reportes": len(reportes_lista),
        "reportes": reportes_lista,
    }


@app.get("/reports/{report_id}")
def get_report_detail(report_id: str):
    """Devuelve el JSON completo (9 secciones) de un reporte estratégico por su ID."""
    # Prevenir path traversal
    safe_id = Path(report_id).name
    target = REPORTES_DIR / f"{safe_id}.json"
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"Reporte '{safe_id}' no encontrado.")
    try:
        datos = json.loads(target.read_text(encoding="utf-8"))
        return {"status": "success", "id": safe_id, "reporte": datos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 7. WebSocket Bidireccional en Tiempo Real + HITL en el Mismo Socket
# ---------------------------------------------------------------------------

def _normalizar_event_source_ws(raw_source: Optional[str]) -> str:
    src = (raw_source or "chat").strip().lower()
    if src == "cron_trigger":
        return "cron"
    return src


@app.websocket("/ws/orchestrate")
async def websocket_orchestrate(websocket: WebSocket):
    """
    Canal WebSocket bidireccional para apps móviles, clientes LAN y túneles remotos (`ws://` / `wss://`).

    Autenticación opcional (si `TIENDITA_API_KEY` está configurada en `.env`):
      - Query param `?api_key=<clave>` o header `X-API-Key: <clave>`.

    Protocolo JSON cliente -> servidor:
      {
        "message": "texto de la consulta",
        "event_source": "chat" | "vision_api" | "ui_copilot" | "cron_trigger",
        "thread_id": "opcional",
        "vision_payload": {...},
        "ui_state": {...},
        "provider": "opcional",
        "model_name": "opcional"
      }

    Protocolo JSON servidor -> cliente:
      - {"type": "connected", "thread_id": "...", "auth_enabled": bool}
      - {"type": "session_started", "thread_id": "...", "event_source": "..."}
      - {"type": "node_update", "thread_id": "...", "node": "supervisor|control|...", "data": {...}}
      - {"type": "hitl_required", "thread_id": "...", "approval": {...}}
          -> el servidor espera en el MISMO socket:
             {"action": "approve" | "reject", "edits": "...", "notes": "..."}
      - {"type": "hitl_resolved", "thread_id": "...", "approved": bool, "result": {...}}
      - {"type": "completed", "thread_id": "...", "result": {...}}
      - {"type": "error", "thread_id": "...", "detail": "..."}
    """
    api_key_candidata = websocket.query_params.get("api_key") or websocket.headers.get("x-api-key")
    if not _verificar_api_key(api_key_candidata):
        await websocket.close(code=1008, reason="API Key inválida o faltante (?api_key=... o X-API-Key).")
        return

    await websocket.accept()
    default_thread_id = str(uuid.uuid4())
    await websocket.send_json({
        "type": "connected",
        "thread_id": default_thread_id,
        "auth_enabled": bool(get_tiendita_api_key()),
    })

    try:
        while True:
            raw_payload = await websocket.receive_json()
            if not isinstance(raw_payload, dict):
                await websocket.send_json({"type": "error", "detail": "El mensaje debe ser un objeto JSON."})
                continue

            # Soporte keepalive para apps móviles
            if raw_payload.get("type") == "ping":
                await websocket.send_json({"type": "pong", "thread_id": default_thread_id})
                continue

            tid = str(raw_payload.get("thread_id") or default_thread_id)
            default_thread_id = tid
            raw_source = raw_payload.get("event_source", "chat")
            event_source = _normalizar_event_source_ws(raw_source)
            mensaje = str(raw_payload.get("message") or raw_payload.get("input_text") or "").strip()

            if not mensaje and event_source == "cron":
                mensaje = (
                    "Ejecuta el barrido programado real sobre PostgreSQL: revisa lotes próximos a caducar "
                    "(v_por_caducar) y alertas de stock crítico (v_stock_bajo). Si detectas alertas reales, "
                    "encadena al publicista para proponer campaña de rescate."
                )
            elif not mensaje:
                await websocket.send_json({
                    "type": "error",
                    "thread_id": tid,
                    "detail": "Falta el campo 'message' (o 'input_text') en el payload JSON.",
                })
                continue

            vision_payload = raw_payload.get("vision_payload")
            ui_state = raw_payload.get("ui_state")
            provider = raw_payload.get("provider")
            model_name = raw_payload.get("model_name")

            await websocket.send_json({
                "type": "session_started",
                "thread_id": tid,
                "event_source": raw_source,
            })

            # Ejecutar stream del grafo en hilo separado para no bloquear el event loop de WebSockets
            loop = asyncio.get_running_loop()
            cola: asyncio.Queue[Tuple[str, Any]] = asyncio.Queue()
            _sentinel = ("__done__", None)

            def _worker_stream():
                try:
                    config = {"configurable": {"thread_id": tid}}
                    initial_state = {
                        "messages": [{"role": "user", "content": mensaje}],
                        "event_source": event_source,
                        "vision_payload": vision_payload,
                        "ui_state": ui_state,
                        "next_agent": None,
                        "compound_chain": [],
                        "pending_approval": None,
                        "promo_assets": None,
                        "iteration_count": 0,
                        "errores": [],
                    }
                    with override_model_context(provider=provider, model_name=model_name):
                        for ev in tiendita_graph.stream(initial_state, config=config):
                            loop.call_soon_threadsafe(cola.put_nowait, ("event", ev))
                except Exception as exc:
                    loop.call_soon_threadsafe(cola.put_nowait, ("error", exc))
                finally:
                    loop.call_soon_threadsafe(cola.put_nowait, _sentinel)

            hilo = threading.Thread(target=_worker_stream, daemon=True)
            hilo.start()

            error_flujo: Optional[Exception] = None
            while True:
                kind, item = await cola.get()
                if kind == "__done__":
                    break
                if kind == "error":
                    error_flujo = item
                    continue
                limpio = _serializar_evento_sse(item)
                for nodo, datos in limpio.items():
                    await websocket.send_json({
                        "type": "node_update",
                        "thread_id": tid,
                        "node": nodo,
                        "data": datos,
                    })

            if error_flujo is not None:
                await websocket.send_json({
                    "type": "error",
                    "thread_id": tid,
                    "detail": str(error_flujo),
                })
                continue

            # Revisar si el grafo se pausó en approval_gate (HITL)
            snap = get_graph_state(tid)
            vals = snap.get("values") or {}
            next_nodes = snap.get("next") or []
            pending = vals.get("pending_approval")
            paused_hitl = bool(
                "approval_gate" in next_nodes
                or (isinstance(pending, dict) and pending.get("requires_human") and pending.get("status") == "pending")
            )

            if paused_hitl:
                await websocket.send_json({
                    "type": "hitl_required",
                    "thread_id": tid,
                    "approval": pending,
                })

                # Esperar decisión humana en el MISMO socket sin cerrar la conexión
                while True:
                    decision_msg = await websocket.receive_json()
                    if isinstance(decision_msg, dict) and decision_msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong", "thread_id": tid})
                        continue
                    break

                if not isinstance(decision_msg, dict):
                    decision_msg = {}

                action_raw = str(decision_msg.get("action") or "").strip().lower()
                if action_raw in ("approve", "aprobar", "s", "si", "sí", "true"):
                    is_approved = True
                elif action_raw in ("reject", "rechazar", "n", "no", "false"):
                    is_approved = False
                elif "approved" in decision_msg:
                    is_approved = bool(decision_msg["approved"])
                else:
                    is_approved = False

                edits = decision_msg.get("edits") if decision_msg.get("edits") is not None else decision_msg.get("correction")
                edits_str = json.dumps(edits, ensure_ascii=False) if isinstance(edits, (dict, list)) else (str(edits) if edits else None)
                notes_str = decision_msg.get("notes") or (f"Decisión WebSocket: {action_raw or is_approved}")

                res_resume = await asyncio.to_thread(
                    resume_orchestration,
                    thread_id=tid,
                    approved=is_approved,
                    correction=edits_str,
                    notes=str(notes_str),
                )
                formatted_resume = _formatear_respuesta_orquestacion(tid, res_resume)
                await websocket.send_json({
                    "type": "hitl_resolved",
                    "thread_id": tid,
                    "approved": is_approved,
                    "result": formatted_resume,
                })
            else:
                formatted_final = _formatear_respuesta_orquestacion(tid, vals)
                await websocket.send_json({
                    "type": "completed",
                    "thread_id": tid,
                    "result": formatted_final,
                })

    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "thread_id": default_thread_id, "detail": str(exc)})
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host=API_HOST, port=API_PORT, reload=True)
