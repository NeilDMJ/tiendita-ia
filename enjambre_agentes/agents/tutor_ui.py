"""
Agente Especialista en Asistencia de Pagos Digitales en Punto de Venta (Tutor UI).
Razonamiento puro sin tools: lee ui_state y responde en MÁXIMO 2 ORACIONES accionables.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config.models import get_llm_para_agente, extraer_texto_mensaje
from schemas.state import OrchestratorState
from schemas.ui_copilot import TutorResponse, UIState
from tools.guards import enforce_max_sentences

TUTOR_UI_SYSTEM_PROMPT = """Eres el Copiloto y Tutor de Pantalla para Pagos Digitales de Tiendita IA.
Tu única labor es asistir al cajero o al cliente frente a la terminal de cobro.

REGLAS DE ORO OBLIGATORIAS:
1. Responde de forma ULTRA-CONCISA en un MÁXIMO ABSOLUTO DE 2 ORACIONES.
2. Cada oración debe ser directamente accionable (indicar claramente qué presionar, insertar o esperar).
3. PROHIBIDO dar rodeos, explicaciones técnicas innecesarias o saludos largos.
4. Razonamiento puro: analiza 'screen', 'step', 'payment_method' y 'error_code' provistos en el estado.
"""


def tutor_ui_node(state: OrchestratorState) -> Dict[str, Any]:
    """Nodo ejecutor para el Tutor UI con estricto límite de 2 oraciones."""
    llm = get_llm_para_agente("tutor_ui")
    ui_state = state.get("ui_state") or {
        "screen": "seleccion_pago",
        "step": 1,
        "payment_method": "tarjeta",
        "error_code": None
    }
    
    prompt_usuario = (
        f"Estado actual de la terminal de pago:\n"
        f"- Pantalla: {ui_state.get('screen')}\n"
        f"- Paso: {ui_state.get('step')}\n"
        f"- Método seleccionado: {ui_state.get('payment_method')}\n"
        f"- Error visible: {ui_state.get('error_code') or 'Ninguno'}\n\n"
        f"Instruye al usuario en máximo 2 oraciones accionables."
    )
    
    tutor_salida: TutorResponse | None = None
    try:
        # Intentar estructurado con Pydantic
        structured_llm = llm.with_structured_output(TutorResponse)
        tutor_salida = structured_llm.invoke([
            SystemMessage(content=TUTOR_UI_SYSTEM_PROMPT),
            HumanMessage(content=prompt_usuario)
        ])
    except Exception:
        pass
        
    if tutor_salida and tutor_salida.mensaje_unificado:
        texto_final = tutor_salida.mensaje_unificado
    else:
        # Fallback analítico puro con guardia estricta de 2 oraciones
        resp = llm.invoke([
            SystemMessage(content=TUTOR_UI_SYSTEM_PROMPT),
            HumanMessage(content=prompt_usuario)
        ])
        texto_crudo = extraer_texto_mensaje(resp.content).strip().replace("\n", " ")
        texto_final = enforce_max_sentences(texto_crudo, max_sentences=2)
        if not texto_final:
            texto_final = "Inserte la tarjeta con el chip hacia el frente en la ranura inferior. Ingrese su NIP de cuatro dígitos y presione la tecla verde para confirmar."
            
    texto_final = enforce_max_sentences(texto_final, max_sentences=2)
    
    return {
        "messages": [AIMessage(content=f"[TUTOR_UI]: {texto_final}")],
        "iteration_count": state.get("iteration_count", 0) + 1
    }
