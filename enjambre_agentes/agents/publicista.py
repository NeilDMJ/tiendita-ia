"""
Agente Especialista en Marketing y Medios Comerciales (Publicista).
Genera copys comerciales, llamados a la acción y prompts de video vertical 9:16 de 5 segundos.
Conectado a approval_gate (HITL) para autorización previa a publicación.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from config.models import get_llm, extraer_texto_mensaje
from schemas.state import OrchestratorState
from schemas.reports import PromoAssets, VideoPrompt
from tools.media_tools import generate_promo_copy, generate_video_prompt, generate_cta
from tools.db_client import query_expiring_soon, query_inventory
from tools.few_shot_retriever import retrieve_few_shots

PUBLICISTA_SYSTEM_PROMPT = """Eres el Agente Publicista y Creador de Campañas de Tiendita IA.
Tu responsabilidad es:
1. Detectar productos con riesgo de merma o sobrestock para detonar campañas de impulso inmediato.
2. Escribir copys comerciales persuasivos y atractivos para WhatsApp Status, redes sociales y carteles de mostrador.
3. Formular llamados a la acción (CTAs) contundentes y promociones claras.
4. Generar especificaciones técnicas de video vertical en formato 9:16 con duración de 5 segundos para plataformas móviles.

REGLAS:
- Emplea Tool Calling nativo para consultar productos en caducidad y generar los activos publicitarios.
- Toda campaña creada debe quedar empaquetada como propuesta para revisión del operador humano (HITL) antes de publicarse.
"""


def get_publicista_agent():
    """Instancia el agente ReAct del Publicista."""
    llm = get_llm(role="publicista")
    tools = [
        generate_promo_copy,
        generate_video_prompt,
        generate_cta,
        query_expiring_soon,
        query_inventory,
        retrieve_few_shots,
    ]
    return create_react_agent(llm, tools=tools, prompt=PUBLICISTA_SYSTEM_PROMPT)


def publicista_node(state: OrchestratorState) -> Dict[str, Any]:
    """Nodo ejecutor para el Publicista en LangGraph. Pasa por approval_gate antes de publicar."""
    agent = get_publicista_agent()
    mensajes = [
        m for m in state.get("messages", [])
        if not extraer_texto_mensaje(getattr(m, "content", m)).startswith("(・_・)? [SUPERVISOR]")
    ]

    resultado = agent.invoke({"messages": mensajes})
    mensajes_nuevos = resultado.get("messages", [])
    ultimo_mensaje = extraer_texto_mensaje(mensajes_nuevos[-1].content).strip() if mensajes_nuevos else ""

    # Consultar productos reales próximos a caducar en PostgreSQL (sin datos simulados)
    producto_real = None
    try:
        exp_data = json.loads(query_expiring_soon.invoke({"days_ahead": 7}))
        items_exp = exp_data.get("items") or []
        if items_exp:
            producto_real = items_exp[0]
    except Exception:
        producto_real = None

    nombre_prod = producto_real["nombre"] if producto_real else "Selección destacada en tienda"
    sku_prod = producto_real["sku"] if producto_real else None
    precio_base = float(producto_real["precio_venta"]) if producto_real else 0.0
    precio_promo = round(precio_base * 0.80, 2) if precio_base > 0 else None

    if not ultimo_mensaje:
        precio_txt = f" a ${precio_promo:.2f} (20% de descuento)" if precio_promo else " con 20% de descuento"
        ultimo_mensaje = (
            f"Propuesta de promoción lista para {nombre_prod}{precio_txt}. "
            "Revisa la tarjeta de confirmación para aprobarla o descartarla."
        )

    promo_assets = {
        "sku": sku_prod,
        "producto_promocionado": nombre_prod,
        "copy_text": ultimo_mensaje[:400],
        "cta": f"¡Aprovecha hoy en mostrador: {nombre_prod}!",
        "descuento_sugerido_pct": 20.0,
        "precio_promo": precio_promo,
        "video_prompt": {
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            "trigger": "caducidad" if producto_real else "promocion_general",
            "producto_promocionado": nombre_prod,
            "prompt_text": f"Cinematic 9:16 vertical commercial shot, 5 seconds. Close-up of {nombre_prod} on a vibrant neighborhood store counter with clear promotional price tag.",
            "guion_voz_superpuesta": f"¡Hoy llévate {nombre_prod} con 20% de descuento en tu tiendita!"
        }
    }

    # Carga de aprobación humana (HITL) real para COMMIT en tabla promocion de PostgreSQL
    pending_approval = {
        "action_type": "publicar_campana",
        "description": f"Publicar campaña y registrar promoción en PostgreSQL para '{nombre_prod}'.",
        "proposed_data": {
            "op": "publicar_campana",
            "sku": sku_prod,
            "motivo": "caducidad" if producto_real else "impulso_comercial",
            "descuento": "20%",
            "precio_promo": precio_promo,
            "copy": promo_assets["copy_text"],
            "cta": promo_assets["cta"],
            "video_prompt": promo_assets["video_prompt"],
        },
        "reason": "La publicación de promociones y su registro en PostgreSQL requieren confirmación del dueño del negocio.",
        "requires_human": True,
        "status": "pending",
    }
    
    return {
        "messages": [AIMessage(content=f"[PUBLICISTA]: {ultimo_mensaje}")],
        "promo_assets": promo_assets,
        "pending_approval": pending_approval,
        "iteration_count": state.get("iteration_count", 0) + 1
    }
