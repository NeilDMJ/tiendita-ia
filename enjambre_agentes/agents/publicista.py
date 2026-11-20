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

from config.models import get_llm_para_agente, extraer_texto_mensaje
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
    llm = get_llm_para_agente("publicista")
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
    mensajes = list(state.get("messages", []))
    
    prompt_adicional = "[ROL: Publicista de Tiendita IA - Generar Campaña y Activo 9:16]"
    mensajes_invocacion = mensajes + [HumanMessage(content=prompt_adicional)]
    
    resultado = agent.invoke({"messages": mensajes_invocacion})
    mensajes_nuevos = resultado.get("messages", [])
    ultimo_mensaje = extraer_texto_mensaje(mensajes_nuevos[-1].content) if mensajes_nuevos else "Activos promocionales generados."
    
    # Preparar el paquete de activos publicitarios
    promo_assets = {
        "copy_text": "¡Aprovecha hoy en Tiendita IA! Tenemos productos frescos con descuento especial de temporada.",
        "cta": "¡Corre antes de que se terminen en mostrador!",
        "descuento_sugerido_pct": 25.0,
        "video_prompt": {
            "aspect_ratio": "9:16",
            "duration_seconds": 5,
            "trigger": "caducidad",
            "producto_promocionado": "Pan y Lácteos del Día",
            "prompt_text": "Cinematic 9:16 vertical commercial shot, 5 seconds. Fresh milk and bakery display on clean counter.",
            "guion_voz_superpuesta": "¡Llévate lo más fresco con descuento hoy en tu tiendita vecina!"
        }
    }
    
    # Carga de aprobación humana (HITL) requerida por el usuario para campañas y videos
    pending_approval = {
        "action_type": "publicar_campana",
        "description": "Lanzamiento de campaña publicitaria y distribución de video promocional 9:16.",
        "proposed_data": {
            "copy": promo_assets["copy_text"],
            "cta": promo_assets["cta"],
            "video_prompt": promo_assets["video_prompt"]
        },
        "reason": "La difusión pública de promociones y descuentos requiere confirmación del dueño del negocio.",
        "requires_human": True,
        "status": "pending"
    }
    
    return {
        "messages": [AIMessage(content=f"[PUBLICISTA]: {ultimo_mensaje}")],
        "promo_assets": promo_assets,
        "pending_approval": pending_approval,
        "iteration_count": state.get("iteration_count", 0) + 1
    }
