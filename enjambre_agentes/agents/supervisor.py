"""
Agente Supervisor Central (Director de Orquesta de Tiendita IA).
Razonamiento puro sobre event_source y estado global: enrutamiento estructurado,
soporte para encadenamiento compuesto y límite estricto iteration_count <= 6.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config.models import get_llm, extraer_texto_mensaje
from schemas.state import OrchestratorState


class SupervisorDecision(BaseModel):
    """Esquema de salida estructurada para la decisión de orquestación del Supervisor."""
    next_agent: Literal[
        "control",
        "vendedor",
        "analista",
        "investigador",
        "publicista",
        "tutor_ui",
        "FINISH"
    ] = Field(..., description="Agente especialista elegido para ejecutar la siguiente acción.")
    reasoning: str = Field(..., description="Justificación analítica pura de la asignación del flujo.")
    compound_chain: Optional[List[str]] = Field(
        default=None,
        description="Secuencia de agentes a invocar sucesivamente si la solicitud lo amerita (ej. ['control', 'vendedor'])."
    )


SUPERVISOR_SYSTEM_PROMPT = """Eres el Supervisor Maestro y Orquestador Principal de Tiendita IA.
Tu función es coordinar el flujo de trabajo entre los 6 agentes especialistas mediante RAZONAMIENTO PURO:

ESPECIALISTAS DISPONIBLES:
1. 'control': Escaneo de catálogo (/catalog-scan), auditoría de comprobantes/facturas (/receipt-ocr), registro de productos, conteo de inventario y alertas de caducidad.
2. 'vendedor': Atención de mostrador (/pos-checkout), cotización contra inventario, cobro de carritos y upselling al cliente.
3. 'analista': Flujo de caja, cálculo de márgenes por SKU, rotación de mercancía y balance financiero (SOLO LECTURA).
4. 'investigador': Estrategia comercial completa estructurada en 9 secciones obligatorias y análisis de mercado.
5. 'publicista': Creación de copys comerciales, llamados a la acción y prompts de video vertical 9:16 ante caducidad o sobrestock.
6. 'tutor_ui': Copiloto de pantalla y asistencia en terminales de cobro digital (máximo 2 oraciones accionables).
7. 'FINISH': Seleccionar cuando la solicitud del usuario ha sido satisfecha por completo.

REGLAS ESTRICTAS DE ORQUESTACIÓN:
- PROHIBIDO utilizar palabras clave o reglas rígidas de texto (if 'pos' in query). Evalúa la intención semántica global, el evento detonante (event_source) y los datos disponibles.
- Para consultas directas que resuelve un solo especialista, deja 'compound_chain' vacío (null o []). NUNCA repitas el agente elegido en 'next_agent' dentro de 'compound_chain'.
- Usa 'compound_chain' ÚNICAMENTE para los agentes ADICIONALES posteriores a 'next_agent' cuando la tarea realmente requiera dos o más especialistas distintos (ej. next_agent='control', compound_chain=['publicista']).
- Si la tarea ya está concluida o se alcanzó el objetivo, emite 'FINISH'.
"""


def supervisor_node(state: OrchestratorState) -> Dict[str, Any]:
    """Nodo central del Supervisor en LangGraph."""
    llm = get_llm(role="supervisor")
    iteration_count = state.get("iteration_count", 0)
    
    # Límite estricto: iteration_count <= 6
    if iteration_count >= 6:
        return {
            "next_agent": "FINISH",
            "messages": [AIMessage(content="(˘_˘) [SUPERVISOR] Límite de 6 iteraciones alcanzado. Cerrando ciclo de orquestación con resumen consolidado.")],
            "iteration_count": iteration_count + 1
        }
        
    # Verificar si hay una cadena compuesta en ejecución
    compound_chain = state.get("compound_chain") or []
    if compound_chain:
        siguiente = compound_chain.pop(0)
        return {
            "next_agent": siguiente,
            "compound_chain": compound_chain,
            "iteration_count": iteration_count + 1
        }
        
    mensajes = list(state.get("messages", []))
    event_source = state.get("event_source", "chat")
    vision_payload = state.get("vision_payload")
    ui_state = state.get("ui_state")
    
    contexto_evaluacion = (
        f"Estado actual de la orquestación:\n"
        f"- Fuente del evento: {event_source}\n"
        f"- Carga visual disponible: {'Sí (' + str(vision_payload.get('mode') or vision_payload.get('endpoint') or 'imagen') + ')' if vision_payload else 'No'}\n"
        f"- Estado de interfaz UI: {'Sí' if ui_state else 'No'}\n"
        f"- Evidencia BD previa: {'Sí' if state.get('db_evidence') else 'No'}\n"
        f"- Iteraciones consumidas: {iteration_count} / 6\n"
        f"- Último mensaje registrado: {extraer_texto_mensaje(mensajes[-1].content) if mensajes else 'Sin mensajes previos.'}\n"
    )
    
    decision: SupervisorDecision | None = None
    try:
        structured_llm = llm.with_structured_output(SupervisorDecision)
        decision = structured_llm.invoke([
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=contexto_evaluacion)
        ])
    except Exception:
        # Fallback de razonamiento estructurado por prompting si with_structured_output no responde
        fallback_prompt = (
            f"{SUPERVISOR_SYSTEM_PROMPT}\n\n"
            f"Devuelve un JSON con 'next_agent' (uno de: control, vendedor, analista, investigador, publicista, tutor_ui, FINISH), "
            f"'reasoning' y 'compound_chain'.\n\n{contexto_evaluacion}"
        )
        resp = llm.invoke([HumanMessage(content=fallback_prompt)])
        contenido = extraer_texto_mensaje(resp.content).strip()
        try:
            ini = contenido.find("{")
            fin = contenido.rfind("}") + 1
            if ini != -1 and fin != 0:
                data = json.loads(contenido[ini:fin])
                decision = SupervisorDecision(**data)
        except Exception:
            pass
            
    if not decision:
        # Asignación semántica de emergencia basada en event_source / metadata si fallan las llamadas
        vision_mode = str((vision_payload or {}).get("mode") or (vision_payload or {}).get("endpoint") or "").lower()
        if event_source == "vision_api":
            if "pos" in vision_mode:
                decision = SupervisorDecision(next_agent="vendedor", reasoning="Imagen real de mostrador POS recibida vía vision_api.")
            else:
                decision = SupervisorDecision(next_agent="control", reasoning="Imagen real de catálogo o comprobante recibida vía vision_api.")
        elif event_source in ("catalog-scan", "receipt-ocr"):
            decision = SupervisorDecision(next_agent="control", reasoning="Evento directo de inspección documental o anaquel.")
        elif event_source == "pos-checkout":
            decision = SupervisorDecision(next_agent="vendedor", reasoning="Evento directo de mostrador para cobro.")
        elif event_source == "cron":
            decision = SupervisorDecision(
                next_agent="control",
                reasoning="Barrido programado de caducidades y stock crítico en PostgreSQL.",
                compound_chain=["publicista"],
            )
        elif ui_state:
            decision = SupervisorDecision(next_agent="tutor_ui", reasoning="Interacción activa en pantalla de terminal.")
        else:
            decision = SupervisorDecision(next_agent="vendedor", reasoning="Canal general de atención comercial.")
            
    # Sanitizar compound_chain: nunca repetir next_agent ni encadenar duplicados consecutivos
    valid_specialists = {"control", "vendedor", "analista", "investigador", "publicista", "tutor_ui"}
    cadena_limpia: List[str] = []
    prev_ag = decision.next_agent
    for ag in (decision.compound_chain or []):
        if ag in valid_specialists and ag != prev_ag:
            cadena_limpia.append(ag)
            prev_ag = ag

    return {
        "next_agent": decision.next_agent,
        "compound_chain": cadena_limpia,
        "messages": [AIMessage(content=f"(・_・)? [SUPERVISOR] Enrutando a '{decision.next_agent}'. Motivo: {decision.reasoning}")],
        "iteration_count": iteration_count + 1
    }
