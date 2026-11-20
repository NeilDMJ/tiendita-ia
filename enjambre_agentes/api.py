"""
api.py — API REST del Ecosistema Multiagente Comercial Multimodal (FastAPI).

Levanta el servidor:
    uvicorn api:app --reload --port 8000

Endpoints:
    POST /orchestrate            — Ejecución síncrona (batch)
    POST /orchestrate/stream     — Streaming SSE en tiempo real
    POST /orchestrate/resume     — Reanudación HITL
    GET  /threads/{thread_id}/state  — Inspección de estado del checkpointer
    GET  /mcp/tools              — Herramientas en formato JSON Schema MCP
    GET  /health                 — Healthcheck del grafo y proveedor LLM
"""
from __future__ import annotations

import sys
import os
import json
import asyncio
from typing import Any, Dict, Generator, Literal, Optional

# ─── Añadir el directorio actual al path si es necesario ────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from graph import (
    run_orchestration,
    run_orchestration_stream,
    resume_orchestration,
    orchestrator_graph,
)
from models import NemoServiceError
from tools_bridge import to_mcp_tool_definitions, vision_payload_from_image
from response_formatter import formatear_respuesta, respuesta_json


# ─────────────────────────────────────────────────────────────────────────────
# ESQUEMAS PYDANTIC v2 DE ENTRADA / SALIDA
# ─────────────────────────────────────────────────────────────────────────────

class OrchestrationRequest(BaseModel):
    """Cuerpo de la solicitud para /orchestrate y /orchestrate/stream."""
    query:          str                                                      = Field(default="", description="Mensaje en lenguaje natural del usuario o vacío si se usa vision_payload/ui_state")
    thread_id:      str                                                      = Field(default="default_thread", description="Identificador único de la sesión de conversación")
    event_source:   Literal["chat", "vision_api", "ui_copilot", "cron_trigger"] = Field(default="chat")
    vision_payload: Optional[Dict[str, Any]]                                = Field(default=None, description="Payload de la API de Visión Artificial (/catalog-scan, /pos-checkout, /receipt-ocr)")
    ui_state:       Optional[Dict[str, Any]]                                = Field(default=None, description="Estado de la pantalla de la app móvil para el Tutor UI")
    image_base64:   Optional[str]                                           = Field(default=None, description="Imagen cruda (base64, data URI o URL). Se convierte a vision_payload con NIM Vision antes de entrar al grafo; requiere image_endpoint y se ignora si ya viene vision_payload")
    image_endpoint: Optional[Literal["/catalog-scan", "/pos-checkout", "/receipt-ocr"]] = Field(default=None, description="Flujo de visión al que pertenece image_base64")
    image_mime_type: str                                                    = Field(default="image/jpeg", description="MIME de image_base64 cuando no es data URI")
    provider:       Optional[str]                                           = Field(default=None, description="Proveedor LLM: NVIDIA, Gemini, Groq, Ollama (usa variable de entorno si es None)")
    model_name:     Optional[str]                                           = Field(default=None, description="Nombre del modelo específico del proveedor")


class ResumeRequest(BaseModel):
    """Cuerpo de la solicitud para /orchestrate/resume (HITL)."""
    thread_id:      str                       = Field(description="Thread ID de la sesión pausada en HITL")
    approved:       bool                      = Field(description="True para ejecutar la mutación, False para cancelarla")
    edited_payload: Optional[Dict[str, Any]] = Field(default=None, description="Payload editado por el operador (opcional)")


class OrchestrationResponse(BaseModel):
    """Respuesta de /orchestrate."""
    thread_id:        str
    status:           Literal["completed", "awaiting_approval"]
    response:         str                       = Field(description="Último mensaje del agente en lenguaje natural")
    pending_approval: Optional[Dict[str, Any]] = None
    strategic_report: Optional[Dict[str, Any]] = None
    promo_assets:     Optional[Dict[str, Any]] = None
    db_evidence:      list                      = Field(default_factory=list)
    iteration_count:  int                       = 0
    validation_errors: list                    = Field(default_factory=list)


class ResumeResponse(BaseModel):
    """Respuesta de /orchestrate/resume."""
    thread_id:        str
    approved:         bool
    status:           Literal["executed", "cancelled"]
    response:         str
    db_evidence:      list = Field(default_factory=list)
    pending_approval: Optional[Dict[str, Any]] = None


class ThreadStateResponse(BaseModel):
    """Respuesta de /threads/{thread_id}/state."""
    thread_id:        str
    has_pending:      bool
    pending_approval: Optional[Dict[str, Any]] = None
    iteration_count:  int                       = 0
    db_evidence_len:  int                       = 0
    last_sender:      Optional[str]             = None


class MCPToolsResponse(BaseModel):
    """Respuesta de /mcp/tools."""
    total:  int
    tools:  list


class HealthResponse(BaseModel):
    """Respuesta de /health."""
    status:          str
    provider:        str
    graph_compiled:  bool
    tools_count:     int
    version:         str = "0.3.0"


# ─────────────────────────────────────────────────────────────────────────────
# INSTANCIA FASTAPI + CORS
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Tiendita IA — API Multiagente Comercial",
    description=(
        "API REST del Ecosistema Multiagente Comercial Multimodal en LangGraph.\n\n"
        "Expone 6 agentes especializados (Control, Vendedor, Analista, Investigador, "
        "Publicista, Tutor UI) + Human-in-the-Loop (HITL) + Visión Artificial + MCP."
    ),
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # En producción: lista de orígenes autorizados
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_last_message(result: Dict[str, Any]) -> str:
    """Extrae el contenido del último AIMessage del estado del grafo."""
    messages = result.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    return getattr(last, "content", str(last))


def _resolve_provider(requested: Optional[str]) -> str:
    return requested or os.getenv("DEFAULT_LLM_PROVIDER", "NVIDIA")


def _resolve_vision_input(req: OrchestrationRequest) -> tuple[Optional[Dict[str, Any]], str]:
    """
    Si la app envió una imagen cruda en lugar de un vision_payload, la convierte con NIM Vision.
    Devuelve (vision_payload, event_source). La percepción ocurre aquí; el grafo nunca ve píxeles.
    """
    if req.vision_payload is not None or not req.image_base64:
        return req.vision_payload, req.event_source
    if not req.image_endpoint:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 requiere image_endpoint (/catalog-scan, /pos-checkout o /receipt-ocr).",
        )
    try:
        payload = vision_payload_from_image(req.image_base64, req.image_endpoint, req.image_mime_type)
    except (NemoServiceError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NIM Vision no pudo procesar la imagen: {exc}",
        ) from exc
    return payload, "vision_api"


def _make_serializable(obj: Any) -> Any:
    """Convierte objetos no serializables (como AnyMessage) a dict/str."""
    if hasattr(obj, "content"):
        return {"role": type(obj).__name__, "content": obj.content}
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(i) for i in obj]
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.post(
    "/orchestrate",
    response_model=OrchestrationResponse,
    summary="Ejecución síncrona del orquestador multiagente",
    tags=["Orquestación"],
)
def orchestrate(req: OrchestrationRequest) -> OrchestrationResponse:
    """
    Ejecuta el flujo multiagente completo de forma sincronizada.

    - Si el grafo pausa en HITL, `status` será `"awaiting_approval"` y
      `pending_approval` contendrá los detalles de la mutación a confirmar.
    - Llama luego a `POST /orchestrate/resume` con el `thread_id` para aprobar o rechazar.
    """
    provider = _resolve_provider(req.provider)
    vision_payload, event_source = _resolve_vision_input(req)
    try:
        result = run_orchestration(
            query=req.query,
            thread_id=req.thread_id,
            event_source=event_source,
            vision_payload=vision_payload,
            ui_state=req.ui_state,
            provider=provider,
            model_name=req.model_name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la orquestación: {exc}",
        ) from exc

    formateada = formatear_respuesta(result)
    pending = result.get("pending_approval")
    return OrchestrationResponse(
        thread_id=req.thread_id,
        status="awaiting_approval" if pending else "completed",
        response=formateada["respuesta"],
        pending_approval=formateada.get("pendiente_aprobacion"),
        strategic_report=result.get("strategic_report"),
        promo_assets=result.get("promo_assets"),
        db_evidence=_make_serializable(result.get("db_evidence", [])),
        iteration_count=result.get("iteration_count", 0),
        validation_errors=result.get("validation_errors", []),
    )


@app.post(
    "/orchestrate/stream",
    summary="Ejecución del orquestador con streaming SSE en tiempo real",
    tags=["Orquestación"],
    response_class=StreamingResponse,
)
def orchestrate_stream(req: OrchestrationRequest) -> StreamingResponse:
    """
    Emite eventos SSE (`text/event-stream`) por cada transición de nodo del grafo.

    Cada evento tiene formato:
    ```
    data: {"node": "<nombre>", "next_agent": "...", "iteration_count": N,
           "pending_approval": null, "final_response": null}\\n\\n
    ```

    El evento final con `final_response` contiene el mensaje completo del agente.

    **Uso con `curl`:**
    ```bash
    curl -X POST http://localhost:8000/orchestrate/stream \\
      -H "Content-Type: application/json" \\
      -d '{"query": "¿Cuánto me queda de la Coca?", "thread_id": "stream01"}' \\
      --no-buffer
    ```
    """
    provider = _resolve_provider(req.provider)
    vision_payload, event_source = _resolve_vision_input(req)

    def _event_generator() -> Generator[str, None, None]:
        final_state: Dict[str, Any] = {}
        try:
            for step in run_orchestration_stream(
                query=req.query,
                thread_id=req.thread_id,
                event_source=event_source,
                vision_payload=vision_payload,
                ui_state=req.ui_state,
                provider=provider,
                model_name=req.model_name,
            ):
                node_name = list(step.keys())[0] if step else None
                if not node_name:
                    continue
                node_state = step[node_name]
                final_state.update(node_state)

                event_data = {
                    "node":           node_name,
                    "next_agent":     node_state.get("next_agent"),
                    "iteration_count": node_state.get("iteration_count"),
                    "pending_approval": node_state.get("pending_approval"),
                    "db_evidence_delta": len(node_state.get("db_evidence", [])),
                    "validation_errors": node_state.get("validation_errors", []),
                    "final_response": None,
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False, default=str)}\n\n"

            # Evento final con la respuesta completa
            final_event = {
                "node":            "_final",
                "next_agent":      "FIN",
                "iteration_count": final_state.get("iteration_count", 0),
                "pending_approval": final_state.get("pending_approval"),
                "db_evidence_delta": 0,
                "validation_errors": final_state.get("validation_errors", []),
                "final_response":  _extract_last_message(final_state),
                "strategic_report": final_state.get("strategic_report"),
                "promo_assets":     final_state.get("promo_assets"),
            }
            yield f"data: {json.dumps(final_event, ensure_ascii=False, default=str)}\n\n"

        except Exception as exc:
            error_event = {"error": str(exc), "node": "_error"}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post(
    "/orchestrate/resume",
    response_model=ResumeResponse,
    summary="Reanudación del flujo Human-in-the-Loop (HITL)",
    tags=["Orquestación"],
)
def orchestrate_resume(req: ResumeRequest) -> ResumeResponse:
    """
    Reanuda un grafo pausado en un punto de interrupción HITL.

    - `approved=true`: Ejecuta la mutación de inventario, venta o campaña pendiente.
    - `approved=false`: Cancela la acción sin alterar la base de datos.
    - `edited_payload`: Permite modificar el payload antes de confirmar (ej. ajustar cantidad).

    **Ejemplo `curl`:**
    ```bash
    curl -X POST http://localhost:8000/orchestrate/resume \\
      -H "Content-Type: application/json" \\
      -d '{"thread_id": "mi_sesion", "approved": true}'
    ```
    """
    try:
        result = resume_orchestration(
            thread_id=req.thread_id,
            approved=req.approved,
            edited_payload=req.edited_payload,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al reanudar la sesión '{req.thread_id}': {exc}",
        ) from exc

    return ResumeResponse(
        thread_id=req.thread_id,
        approved=req.approved,
        status="executed" if req.approved else "cancelled",
        response=formatear_respuesta(result)["respuesta"],
        db_evidence=_make_serializable(result.get("db_evidence", [])),
        pending_approval=result.get("pending_approval"),
    )


@app.get(
    "/threads/{thread_id}/state",
    response_model=ThreadStateResponse,
    summary="Inspección del estado interno de una sesión",
    tags=["Estado"],
)
def get_thread_state(thread_id: str) -> ThreadStateResponse:
    """
    Consulta el checkpointer activo del grafo para leer el estado guardado
    de una sesión (historial de mensajes, db_evidence, aprobaciones pendientes).

    Útil para depuración, dashboards de operador y recuperación de sesiones interrumpidas.
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = orchestrator_graph.get_state(config)
        if checkpoint is None or checkpoint.values is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró estado para el thread_id '{thread_id}'.",
            )
        vals = checkpoint.values
        pending = vals.get("pending_approval")
        return ThreadStateResponse(
            thread_id=thread_id,
            has_pending=bool(pending and pending.get("requires_confirmation")),
            pending_approval=pending,
            iteration_count=vals.get("iteration_count", 0),
            db_evidence_len=len(vals.get("db_evidence", [])),
            last_sender=vals.get("sender"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer el estado del thread '{thread_id}': {exc}",
        ) from exc


@app.get(
    "/mcp/tools",
    response_model=MCPToolsResponse,
    summary="Exportación de herramientas en formato JSON Schema MCP",
    tags=["MCP"],
)
def get_mcp_tools() -> MCPToolsResponse:
    """
    Devuelve las 17 herramientas del ecosistema en el formato estándar del
    **Model Context Protocol (MCP)** para integración con clientes compatibles
    (Claude, OpenAI Tools, LangChain ToolNode, etc.).
    """
    tools = to_mcp_tool_definitions()
    return MCPToolsResponse(total=len(tools), tools=tools)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Healthcheck del servicio y el grafo LangGraph",
    tags=["Infraestructura"],
)
def health_check() -> HealthResponse:
    """
    Verifica que el grafo esté compilado correctamente y reporta el proveedor LLM activo.
    Útil para sondas de Kubernetes, CI/CD y monitoreo de la app móvil.
    """
    try:
        is_compiled = orchestrator_graph is not None
        tools_count = len(to_mcp_tool_definitions())
        provider = os.getenv("DEFAULT_LLM_PROVIDER", "NVIDIA")
        return HealthResponse(
            status="ok" if is_compiled else "degraded",
            provider=provider,
            graph_compiled=is_compiled,
            tools_count=tools_count,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Servicio degradado: {exc}",
        ) from exc
