"""
Agente Especialista en Control de Inventario y Auditoría de Comprobantes.
Encargado de procesar fotos de catálogo (/catalog-scan), tickets de compra (/receipt-ocr)
y vigilar niveles de existencias y caducidades.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from config.models import get_llm_para_agente, extraer_texto_mensaje
from schemas.state import OrchestratorState
from schemas.commerce import ApprovalPayload
from tools.db_client import query_inventory, query_expiring_soon
from tools.vision_nim import analyze_catalog_photo, analyze_receipt
from tools.inventory_tools import register_product, update_stock, check_expiry_alerts, get_low_stock_alerts
from tools.few_shot_retriever import retrieve_few_shots

CONTROL_SYSTEM_PROMPT = """Eres el Agente de Control de Inventario y Auditoría de Tiendita IA.
Tu responsabilidad es:
1. Inspeccionar fotos de anaqueles o catálogos (/catalog-scan) para identificar y dar de alta productos.
2. Procesar comprobantes de compra (/receipt-ocr) y clasificar rígidamente el gasto en 'inversion_inventario' (mercancía para reventa) o 'gasto_operativo' (insumos y servicios del local).
3. Monitorear fechas de caducidad próximas y artículos en desabasto.

REGLAS OBLIGATORIAS:
- Utiliza Tool Calling nativo para ejecutar todas las consultas e inspecciones. Prohibido asumir precios o existencias sin consultar las herramientas.
- Si una operación implica modificar inventario en lote (>10 unidades), clasificar gastos mayores a $1,000 o dar de alta productos nuevos, formula una propuesta estructurada para revisión humana (HITL).
- Mantén un tono técnico, formal y riguroso.
"""


def get_control_agent():
    """Construye el agente ReAct de Control con su LLM asignado."""
    llm = get_llm_para_agente("control")
    tools = [
        analyze_catalog_photo,
        analyze_receipt,
        register_product,
        update_stock,
        check_expiry_alerts,
        get_low_stock_alerts,
        query_inventory,
        query_expiring_soon,
        retrieve_few_shots,
    ]
    return create_react_agent(llm, tools=tools, prompt=CONTROL_SYSTEM_PROMPT)


def control_node(state: OrchestratorState) -> Dict[str, Any]:
    """Nodo ejecutor para el Agente de Control en LangGraph."""
    agent = get_control_agent()
    
    # Preparar contexto a partir del estado multimodal
    mensajes = list(state.get("messages", []))
    vision_payload = state.get("vision_payload")
    event_source = state.get("event_source", "chat")
    
    contexto_adicional = f"[EVENTO_ORIGEN: {event_source}]"
    if vision_payload and vision_payload.get("image_b64"):
        endpoint = vision_payload.get("endpoint", "")
        contexto_adicional += f"\n[CARGA_MULTIMODAL: Imagen disponible para {endpoint}]"
    
    mensajes_invocacion = mensajes + [HumanMessage(content=contexto_adicional)]
    resultado = agent.invoke({"messages": mensajes_invocacion})
    mensajes_nuevos = resultado.get("messages", [])
    ultimo_mensaje = extraer_texto_mensaje(mensajes_nuevos[-1].content) if mensajes_nuevos else "Control completado."
    
    # Evaluar si se generó propuesta que requiera HITL
    pending_approval = state.get("pending_approval")
    if "clasificacion_contable" in str(ultimo_mensaje) or "alta_catalogo" in str(ultimo_mensaje):
        pending_approval = {
            "action_type": "clasificacion_gasto_critico" if "gasto_operativo" in str(ultimo_mensaje) else "alta_catalogo",
            "description": "Revisión de auditoría y conciliación de comprobante/catálogo.",
            "proposed_data": {"detalle": ultimo_mensaje[:400]},
            "reason": "Acción con impacto financiero o en catálogo que requiere validación humana.",
            "requires_human": True,
            "status": "pending"
        }
        
    return {
        "messages": [AIMessage(content=f"[CONTROL]: {ultimo_mensaje}")],
        "db_evidence": str(ultimo_mensaje)[:1000],
        "pending_approval": pending_approval,
        "iteration_count": state.get("iteration_count", 0) + 1
    }
