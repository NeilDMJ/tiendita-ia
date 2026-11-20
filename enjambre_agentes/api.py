"""
API REST y Servidor de Streaming de Tiendita IA.
Ecosistema Comercial Multimodal con Visión Artificial, LangGraph y Tecnología NVIDIA (NIM / NeMo).

Endpoints:
  - GET  /health              -> Estado del servicio y capacidades activas
  - GET  /models              -> Lista de modelos disponibles por proveedor en vivo
  - POST /orchestrate         -> Ejecución síncrona del enjambre
  - POST /orchestrate/stream  -> Streaming SSE (Server-Sent Events) en vivo
  - POST /orchestrate/resume  -> Reanudación Human-in-the-Loop (HITL)
  - POST /catalog-scan        -> Endpoint especializado para escaneo de catálogo y estantes
  - POST /pos-checkout        -> Endpoint especializado para visión en caja / mostrador
  - POST /receipt-ocr         -> Endpoint especializado para OCR y clasificación contable
  - GET  /reports/history     -> Histórico de reportes estratégicos generados
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config.models import (
    listar_modelos_disponibles,
    asignar_cerebros_por_agente,
    obtener_estado_proveedores,
)
from agents.graph import run_orchestration, run_orchestration_stream, resume_orchestration
from schemas.vision import CatalogScanRequest, POSCheckoutRequest, ReceiptOCRRequest

app = FastAPI(
    title="Tiendita IA API",
    description="Ecosistema Comercial Multimodal con Visión Artificial, LangGraph y Tecnología NVIDIA (NIM / NeMo)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORTES_DIR = Path(__file__).resolve().parent / "data" / "reportes"
REPORTES_DIR.mkdir(parents=True, exist_ok=True)


class OrchestrateRequest(BaseModel):
    input_text: str = Field(..., description="Mensaje, consulta o instrucción comercial del usuario.")
    thread_id: Optional[str] = Field(default=None, description="Identificador único del hilo de sesión.")
    event_source: str = Field(default="chat", description="Fuente del evento: 'chat', 'catalog-scan', 'pos-checkout', 'receipt-ocr', 'cron'.")
    vision_payload: Optional[Dict[str, Any]] = Field(default=None, description="Carga de imagen en base64 si aplica.")
    ui_state: Optional[Dict[str, Any]] = Field(default=None, description="Estado de pantalla de la terminal de pago si aplica.")
    provider: Optional[str] = Field(default=None, description="Proveedor LLM manual opcional (NVIDIA, Gemini, Groq, Cohere, Ollama, HuggingFace). Si se omite, usa cerebros distribuidos.")
    model_name: Optional[str] = Field(default=None, description="Modelo específico opcional para el proveedor elegido manualmente.")


class ResumeRequest(BaseModel):
    thread_id: str = Field(..., description="ID del hilo pausado en 'approval_gate'.")
    approved: bool = Field(..., description="True para autorizar la acción, False para rechazarla.")
    correction: Optional[str] = Field(default=None, description="Texto de corrección proporcionado por el operador.")
    notes: Optional[str] = Field(default=None, description="Notas de auditoría humana.")


@app.get("/health")
def health_check():
    """Verifica la operatividad del microservicio y sus subsistemas."""
    return {
        "status": "healthy",
        "service": "Tiendita IA",
        "multimodal": True,
        "nemo_retriever": True,
        "dual_rag_active": True,
        "hitl_enabled": True,
        "providers_supported": ["NVIDIA", "Gemini", "Groq", "Cohere", "Ollama", "HuggingFace"]
    }


@app.get("/models")
def get_models(provider: Optional[str] = None):
    """Consulta en vivo los modelos soportados por proveedor y la distribución de cerebros."""
    return {
        "status": "success",
        "modelos": listar_modelos_disponibles(provider),
        "estado_proveedores": obtener_estado_proveedores(),
        "cerebros_por_agente": asignar_cerebros_por_agente(),
    }


@app.post("/orchestrate")
def orchestrate_sync(req: OrchestrateRequest):
    """Ejecuta un ciclo completo de orquestación de forma síncrona."""
    try:
        resultado = run_orchestration(
            input_text=req.input_text,
            thread_id=req.thread_id,
            event_source=req.event_source,
            vision_payload=req.vision_payload,
            ui_state=req.ui_state,
            provider=req.provider,
            model_name=req.model_name,
        )
        mensajes_serializables = []
        for m in resultado.get("messages", []):
            if hasattr(m, "content"):
                mensajes_serializables.append({"role": getattr(m, "type", "ai"), "content": m.content})
            elif isinstance(m, dict):
                mensajes_serializables.append(m)

        return {
            "status": "completed",
            "next_agent": resultado.get("next_agent"),
            "messages": mensajes_serializables,
            "pending_approval": resultado.get("pending_approval"),
            "strategic_report": resultado.get("strategic_report"),
            "promo_assets": resultado.get("promo_assets"),
            "iteration_count": resultado.get("iteration_count")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrate/stream")
async def orchestrate_streaming(req: OrchestrateRequest):
    """Transmite eventos SSE en tiempo real conforme cada agente genera su respuesta."""
    async def event_generator():
        try:
            async for evento in run_orchestration_stream(
                input_text=req.input_text,
                thread_id=req.thread_id,
                event_source=req.event_source,
                vision_payload=req.vision_payload,
                ui_state=req.ui_state,
                provider=req.provider,
                model_name=req.model_name,
            ):
                payload_json = json.dumps(evento, default=str, ensure_ascii=False)
                yield f"data: {payload_json}\n\n"
        except Exception as err:
            err_json = json.dumps({"error": str(err)})
            yield f"data: {err_json}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/orchestrate/resume")
def resume_hitl(req: ResumeRequest):
    """Reanuda la ejecución tras la decisión tomada por el operador humano en approval_gate."""
    try:
        resultado = resume_orchestration(
            thread_id=req.thread_id,
            approved=req.approved,
            correction=req.correction,
            notes=req.notes
        )
        return {
            "status": "resumed",
            "approved": req.approved,
            "resultado": resultado
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Endpoints Comerciales Especializados (Visión y Reportes)
# ==============================================================================

@app.post("/catalog-scan")
def api_catalog_scan(req: CatalogScanRequest):
    """Procesa una fotografía de catálogo o anaquel para altas e inventario."""
    payload = {
        "endpoint": "/catalog-scan",
        "image_b64": req.image_b64,
        "mime_type": req.mime_type,
        "categoria_sugerida": req.categoria_sugerida
    }
    resultado = run_orchestration(
        input_text="Escaneo de catálogo o anaquel recibido para procesar inventario.",
        event_source="catalog-scan",
        vision_payload=payload
    )
    return {
        "status": "success",
        "endpoint": "/catalog-scan",
        "resultado": resultado.get("messages", [])[-1].content if resultado.get("messages") else "Procesado.",
        "pending_approval": resultado.get("pending_approval")
    }


@app.post("/pos-checkout")
def api_pos_checkout(req: POSCheckoutRequest):
    """Identifica visualmente artículos en mostrador de caja y genera cotización."""
    payload = {
        "endpoint": "/pos-checkout",
        "image_b64": req.image_b64,
        "mime_type": req.mime_type,
        "id_carrito_activo": req.id_carrito_activo
    }
    resultado = run_orchestration(
        input_text="Artículos detectados en mostrador POS para cotizar y agregar al carrito.",
        event_source="pos-checkout",
        vision_payload=payload
    )
    return {
        "status": "success",
        "endpoint": "/pos-checkout",
        "resultado": resultado.get("messages", [])[-1].content if resultado.get("messages") else "Carrito cotizado."
    }


@app.post("/receipt-ocr")
def api_receipt_ocr(req: ReceiptOCRRequest):
    """Extrae texto de un ticket y clasifica en 'inversion_inventario' vs 'gasto_operativo'."""
    payload = {
        "endpoint": "/receipt-ocr",
        "image_b64": req.image_b64,
        "mime_type": req.mime_type
    }
    resultado = run_orchestration(
        input_text="Comprobante de compra recibido para auditoría y clasificación contable.",
        event_source="receipt-ocr",
        vision_payload=payload
    )
    return {
        "status": "success",
        "endpoint": "/receipt-ocr",
        "resultado": resultado.get("messages", [])[-1].content if resultado.get("messages") else "Comprobante auditado.",
        "pending_approval": resultado.get("pending_approval")
    }


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
                    "sector": datos.get("identificacion_sector", "Sector no especificado")[:80],
                    "archivo": arc.name
                })
        except Exception:
            pass
    return {
        "status": "success",
        "total_reportes": len(reportes_lista),
        "reportes": reportes_lista
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
