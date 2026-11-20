"""
Agente Especialista en Ventas y Mostrador (Vendedor POS).
Gestiona el carrito de compras, cotización contra inventario en tiempo real,
detección visual de items en barra y recomendaciones estratégicas de Upselling.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from config.models import get_llm_para_agente, extraer_texto_mensaje
from schemas.state import OrchestratorState
from tools.db_client import query_inventory
from tools.vision_nim import analyze_pos_items
from tools.pos_tools import create_cart, add_to_cart, checkout_cart, suggest_upsell
from tools.few_shot_retriever import retrieve_few_shots
from tools.guards import prevent_cost_leakage

VENDEDOR_SYSTEM_PROMPT = """Eres el Agente Vendedor de Mostrador y Caja POS de Tiendita IA.
Tu misión es:
1. Atender a los clientes y registrar ventas de forma ágil y precisa.
2. Identificar productos en mostrador mediante la cámara POS (/pos-checkout).
3. Cotizar precios de venta en tiempo real contra la base de datos de inventario.
4. Aplicar técnicas de venta cruzada (Upselling) con productos complementarios de alto margen.
5. Gestionar la apertura, adición y liquidación del carrito de ventas.

REGLAS ESTRICTAS:
- NUNCA menciones ni reveles el costo de adquisición o costo unitario del producto al cliente. El precio válido es exclusivamente 'precio_venta'.
- Utiliza las herramientas oficiales para calcular subtotales y cerrar carritos.
- Sé cordial, dinámico y enfocado en la satisfacción del cliente y el incremento del ticket promedio.
"""


def get_vendedor_agent():
    """Instancia el agente ReAct de Mostrador."""
    llm = get_llm_para_agente("vendedor")
    tools = [
        analyze_pos_items,
        create_cart,
        add_to_cart,
        checkout_cart,
        suggest_upsell,
        query_inventory,
        retrieve_few_shots,
    ]
    return create_react_agent(llm, tools=tools, prompt=VENDEDOR_SYSTEM_PROMPT)


def vendedor_node(state: OrchestratorState) -> Dict[str, Any]:
    """Nodo ejecutor para el Vendedor en el grafo LangGraph."""
    agent = get_vendedor_agent()
    mensajes = list(state.get("messages", []))
    vision_payload = state.get("vision_payload")
    
    prompt_adicional = "[CANAL_VENTA: Mostrador Activo]"
    if vision_payload and vision_payload.get("image_b64"):
        prompt_adicional += "\n[IMAGEN_MOSTRADOR: Se adjuntó toma de cámara para detección de artículos]"
        
    mensajes_invocacion = mensajes + [HumanMessage(content=prompt_adicional)]
    resultado = agent.invoke({"messages": mensajes_invocacion})
    mensajes_nuevos = resultado.get("messages", [])
    ultimo_mensaje = extraer_texto_mensaje(mensajes_nuevos[-1].content) if mensajes_nuevos else "Venta atendida."
    
    # Aplicar guardia para evitar filtración de costos
    mensaje_seguro = prevent_cost_leakage(str(ultimo_mensaje))
    
    # Revisar si se propuso un descuento especial alto que amerite HITL
    pending_approval = state.get("pending_approval")
    if "descuento" in mensaje_seguro.lower() and ("%" in mensaje_seguro or "$" in mensaje_seguro):
        pending_approval = {
            "action_type": "descuento_especial",
            "description": "Descuento en caja propuesto al cliente.",
            "proposed_data": {"mensaje": mensaje_seguro[:300]},
            "reason": "Aplicación de política de descuento en mostrador.",
            "requires_human": True,
            "status": "pending"
        }
        
    return {
        "messages": [AIMessage(content=f"[VENDEDOR]: {mensaje_seguro}")],
        "db_evidence": str(mensaje_seguro)[:800],
        "pending_approval": pending_approval,
        "iteration_count": state.get("iteration_count", 0) + 1
    }
