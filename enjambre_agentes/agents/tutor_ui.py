"""
Agente Especialista en Asistencia de Pagos Digitales en México (Tutor UI: CoDi, SPEI, DiMo).
Consulta primero la guía oficial en el índice RAG (`guias.json` + `conocimiento.jsonl` de Banxico)
mediante `consultar_guia_pago_digital` y responde en MÁXIMO 2 ORACIONES accionables.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config.models import get_llm, extraer_texto_mensaje
from schemas.state import OrchestratorState
from schemas.ui_copilot import TutorResponse
from tools.guards import enforce_max_sentences
from tools.media_tools import consultar_guia_pago_digital

TUTOR_UI_SYSTEM_PROMPT = """Eres el Copiloto y Tutor de Pantalla para Pagos Digitales en México (CoDi, SPEI y DiMo) de Tiendita IA.
Tu única labor es guiar al cajero o cliente frente a la app bancaria o terminal de cobro.

REGLAS DE ORO OBLIGATORIAS:
1. Basa tu respuesta ESTRICTAMENTE en la evidencia recuperada de `guias.json` y `conocimiento.jsonl` (Banxico) adjunta en el contexto. No inventes pasos, montos ni botones fuera de la guía oficial.
2. Responde de forma ULTRA-CONCISA en un MÁXIMO ABSOLUTO DE 2 ORACIONES.
3. Cada oración debe ser directamente accionable (qué verificar, tocar o corregir en la pantalla actual).
4. Nunca pidas NIP, contraseñas, CVV ni tokens de seguridad.
5. PROHIBIDO dar rodeos, saludos largos o explicaciones técnicas innecesarias.
"""


def tutor_ui_node(state: OrchestratorState) -> Dict[str, Any]:
    """Nodo ejecutor para el Tutor UI respaldado por el RAG oficial de CoDi/SPEI/DiMo."""
    llm = get_llm(role="tutor_ui")
    ui_state = state.get("ui_state") or {
        "screen": "seleccion_pago",
        "step": 1,
        "payment_method": "codi",
        "error_code": None,
    }

    metodo_pago = str(ui_state.get("payment_method") or "codi").strip().lower()
    pantalla = str(ui_state.get("screen") or "seleccion_pago").strip()
    paso = ui_state.get("step", 1)
    error_code = ui_state.get("error_code")

    mensajes = list(state.get("messages", []))
    duda_usuario = extraer_texto_mensaje(mensajes[-1].content).strip() if mensajes else ""

    # 1. Consultar primero la guía oficial en el RAG (data/Embeddings/datos/ -> FAISS / pgvector)
    raw_guia = consultar_guia_pago_digital.invoke({
        "metodo_pago": metodo_pago,
        "pantalla": pantalla,
        "error_code": error_code,
        "duda": duda_usuario,
    })

    try:
        guia_data = json.loads(raw_guia)
    except Exception:
        guia_data = {"guias_recuperadas": [], "advertencias_seguridad": []}

    fragmentos: List[Dict[str, Any]] = guia_data.get("guias_recuperadas", [])
    advertencias: List[str] = guia_data.get("advertencias_seguridad", [])

    bloques_evidencia = []
    resumen_fuentes = []
    for idx, frag in enumerate(fragmentos, 1):
        fuente_tag = f"{frag.get('doc')} [{frag.get('seccion') or frag.get('metodo_pago')}] (score={frag.get('score')})"
        resumen_fuentes.append(fuente_tag)
        bloques_evidencia.append(f"({idx}) {fuente_tag}:\n{frag.get('texto', '')[:450]}")

    evidencia_rag_str = "\n\n".join(bloques_evidencia) if bloques_evidencia else "Sin fragmentos recuperados."
    advertencias_str = " | ".join(advertencias) if advertencias else "Nunca compartas tu NIP, token ni contraseñas."

    prompt_usuario = (
        f"Estado actual de la pantalla de pago digital:\n"
        f"- Método de pago: {metodo_pago.upper()}\n"
        f"- Pantalla: {pantalla}\n"
        f"- Paso: {paso}\n"
        f"- Código/Error visible: {error_code or 'Ninguno'}\n"
        f"- Consulta del usuario: {duda_usuario or 'Asistencia paso a paso'}\n\n"
        f"GUÍA OFICIAL RECUPERADA (guias.json / conocimiento.jsonl):\n"
        f"{evidencia_rag_str}\n\n"
        f"ADVERTENCIAS DE SEGURIDAD:\n{advertencias_str}\n\n"
        f"Formula la instrucción exacta para el usuario en MÁXIMO 2 ORACIONES accionables."
    )

    tutor_salida: TutorResponse | None = None
    try:
        structured_llm = llm.with_structured_output(TutorResponse)
        tutor_salida = structured_llm.invoke([
            SystemMessage(content=TUTOR_UI_SYSTEM_PROMPT),
            HumanMessage(content=prompt_usuario),
        ])
    except Exception:
        pass

    if tutor_salida and tutor_salida.mensaje_unificado:
        texto_final = tutor_salida.mensaje_unificado
    else:
        resp = llm.invoke([
            SystemMessage(content=TUTOR_UI_SYSTEM_PROMPT),
            HumanMessage(content=prompt_usuario),
        ])
        texto_crudo = extraer_texto_mensaje(resp.content).strip().replace("\n", " ")
        texto_final = enforce_max_sentences(texto_crudo, max_sentences=2)
        if not texto_final and fragmentos:
            texto_final = enforce_max_sentences(fragmentos[0].get("texto", ""), max_sentences=2)

    texto_final = enforce_max_sentences(texto_final, max_sentences=2)
    db_ev = f"RAG Pagos ({metodo_pago.upper()} / {pantalla}): " + "; ".join(resumen_fuentes)

    return {
        "messages": [AIMessage(content=f"[TUTOR_UI]: {texto_final}")],
        "db_evidence": db_ev[:1000],
        "iteration_count": state.get("iteration_count", 0) + 1,
    }
