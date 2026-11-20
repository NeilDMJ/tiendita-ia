"""
Grafo LangGraph con memoria Checkpointer e interrupciones Human-in-the-Loop (HITL).
Orquesta al Supervisor y los 6 agentes especialistas conectando control, vendedor y publicista hacia approval_gate.
Exporta exactamente: run_orchestration, run_orchestration_stream y resume_orchestration.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, AsyncGenerator, Dict, Optional
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from config.models import override_model_context
from schemas.state import OrchestratorState
from tools.db_client import _get_connection
from agents.supervisor import supervisor_node
from agents.control import control_node
from agents.vendedor import vendedor_node
from agents.analista import analista_node
from agents.investigador import investigador_node
from agents.publicista import publicista_node
from agents.tutor_ui import tutor_ui_node


def _commit_approved_db_action(pending: Dict[str, Any]) -> str:
    """Ejecuta el COMMIT real en PostgreSQL para acciones diferidas tras aprobación HITL."""
    proposed = pending.get("proposed_data") or {}
    op = proposed.get("op") or pending.get("action_type")
    correccion = pending.get("human_notes")

    try:
        if op == "publicar_campana" and proposed.get("sku"):
            with _get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM producto WHERE sku = %s", (proposed["sku"],))
                    row = cur.fetchone()
                    if row:
                        prod_id = row[0]
                        copy_final = correccion if correccion and "Aprobado por operador" not in correccion else proposed.get("copy", "")
                        video_txt = json.dumps(proposed.get("video_prompt", {}), ensure_ascii=False)
                        cur.execute(
                            """
                            INSERT INTO promocion
                                (producto_id, motivo, descuento, precio_promo, copy, video_prompt, estado, simulada)
                            VALUES (%s, %s, %s, %s, %s, %s, 'publicada', false)
                            RETURNING id
                            """,
                            (
                                prod_id,
                                proposed.get("motivo", "promocion"),
                                proposed.get("descuento", "20%"),
                                proposed.get("precio_promo"),
                                copy_final,
                                video_txt,
                            ),
                        )
                        promo_id = cur.fetchone()[0]
                conn.commit()
            return f"COMMIT confirmado en PostgreSQL: tabla promocion (id={promo_id}, sku={proposed['sku']})."
    except Exception as exc:
        return f"Acción aprobada, pero ocurrió un error al escribir en PostgreSQL: {exc}"

    return f"Acción '{pending.get('action_type')}' autorizada y confirmada por el operador."


def approval_gate_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Nodo de verificación Human-in-the-Loop (HITL).
    Cuando el operador aprueba, confirma el COMMIT real en PostgreSQL;
    si rechaza, cancela la operación sin escribir en la base de datos.
    """
    pending = state.get("pending_approval")
    if not pending:
        return {}

    status = pending.get("status")
    if status == "approved":
        detalle_commit = _commit_approved_db_action(pending)
        return {
            "pending_approval": None,
            "db_evidence": detalle_commit,
            "messages": [AIMessage(content=f"[HITL APROBADO]: {detalle_commit}")],
        }
    if status == "rejected":
        motivo = pending.get("human_notes") or "Rechazado por el operador."
        return {
            "pending_approval": None,
            "messages": [AIMessage(content=f"[HITL RECHAZADO]: Operación cancelada sin escribir en PostgreSQL. Motivo: {motivo}")],
        }
    return {}


def get_graph_state(thread_id: str) -> Dict[str, Any]:
    """Inspecciona el OrchestratorState real almacenado en el checkpointer para un thread_id."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = tiendita_graph.get_state(config)
    if not snapshot:
        return {}
    return {
        "values": dict(snapshot.values or {}),
        "next": list(snapshot.next or []),
    }


def router_supervisor(state: OrchestratorState) -> str:
    """Enrutador condicional basado en la decisión estructurada del Supervisor."""
    siguiente = state.get("next_agent", "FINISH")
    if siguiente in ["control", "vendedor", "analista", "investigador", "publicista", "tutor_ui"]:
        return siguiente
    return END


def router_approval(state: OrchestratorState) -> str:
    """Evalúa si una acción de control, vendedor o publicista requiere approval_gate, sigue cadena o termina."""
    pending = state.get("pending_approval")
    if pending and pending.get("requires_human") and pending.get("status") == "pending":
        return "approval_gate"
    if state.get("compound_chain"):
        return "supervisor"
    return END


def router_post_specialist(state: OrchestratorState) -> str:
    """Tras un especialista sin HITL: si queda cadena compuesta vuelve al supervisor; si no, termina directo."""
    if state.get("compound_chain"):
        return "supervisor"
    return END


def build_graph():
    """Construye y compila el grafo LangGraph para Tiendita IA."""
    builder = StateGraph(OrchestratorState)

    # 1. Registrar nodos
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("control", control_node)
    builder.add_node("vendedor", vendedor_node)
    builder.add_node("analista", analista_node)
    builder.add_node("investigador", investigador_node)
    builder.add_node("publicista", publicista_node)
    builder.add_node("tutor_ui", tutor_ui_node)
    builder.add_node("approval_gate", approval_gate_node)

    # 2. Conectar flujo inicial
    builder.add_edge(START, "supervisor")

    # 3. Ramificación condicional desde el Supervisor
    builder.add_conditional_edges(
        "supervisor",
        router_supervisor,
        {
            "control": "control",
            "vendedor": "vendedor",
            "analista": "analista",
            "investigador": "investigador",
            "publicista": "publicista",
            "tutor_ui": "tutor_ui",
            END: END
        }
    )

    # 4. Conexiones hacia approval_gate para los agentes con acciones sensibles (control, vendedor, publicista)
    builder.add_conditional_edges("control", router_approval, {"approval_gate": "approval_gate", "supervisor": "supervisor", END: END})
    builder.add_conditional_edges("vendedor", router_approval, {"approval_gate": "approval_gate", "supervisor": "supervisor", END: END})
    builder.add_conditional_edges("publicista", router_approval, {"approval_gate": "approval_gate", "supervisor": "supervisor", END: END})

    # 5. Especialistas de solo lectura o UI: terminan directo salvo que haya cadena compuesta pendiente
    builder.add_conditional_edges("analista", router_post_specialist, {"supervisor": "supervisor", END: END})
    builder.add_conditional_edges("investigador", router_post_specialist, {"supervisor": "supervisor", END: END})
    builder.add_conditional_edges("tutor_ui", router_post_specialist, {"supervisor": "supervisor", END: END})
    builder.add_conditional_edges("approval_gate", router_post_specialist, {"supervisor": "supervisor", END: END})

    # Checkpointer en memoria para persistencia de sesiones e interrupciones HITL
    memory = MemorySaver()
    # Interrupción programada antes de approval_gate cuando se requiera intervención humana
    graph = builder.compile(checkpointer=memory, interrupt_before=["approval_gate"])
    return graph


# Instancia compilada singleton del grafo
tiendita_graph = build_graph()


def run_orchestration(
    input_text: str,
    thread_id: Optional[str] = None,
    event_source: str = "chat",
    vision_payload: Optional[dict] = None,
    ui_state: Optional[dict] = None,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el ciclo de orquestación de Tiendita IA de forma síncrona.
    Nombre exacto estipulado para compatibilidad con api.py y cli_tester.py.
    Si provider/model_name son None, cada agente usa su cerebro distribuido automáticamente.
    Si el usuario especifica provider/model_name, se respeta como modelo primario con rescate automático.
    """
    tid = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    
    initial_state: OrchestratorState = {
        "messages": [{"role": "user", "content": input_text}],
        "event_source": event_source,
        "vision_payload": vision_payload,
        "ui_state": ui_state,
        "iteration_count": 0,
        "errores": []
    }
    
    with override_model_context(provider=provider, model_name=model_name):
        return tiendita_graph.invoke(initial_state, config=config)


async def run_orchestration_stream(
    input_text: str,
    thread_id: Optional[str] = None,
    event_source: str = "chat",
    vision_payload: Optional[dict] = None,
    ui_state: Optional[dict] = None,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Transmite en tiempo real (SSE / streaming) los eventos de cada nodo en el grafo.
    Nombre exacto estipulado para compatibilidad con api.py.
    """
    tid = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    
    initial_state: OrchestratorState = {
        "messages": [{"role": "user", "content": input_text}],
        "event_source": event_source,
        "vision_payload": vision_payload,
        "ui_state": ui_state,
        "iteration_count": 0,
        "errores": []
    }
    
    with override_model_context(provider=provider, model_name=model_name):
        for event in tiendita_graph.stream(initial_state, config=config):
            yield event


def resume_orchestration(
    thread_id: str,
    approved: bool,
    correction: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reanuda la ejecución del grafo pausado en 'approval_gate' (HITL).
    Nombre exacto estipulado para compatibilidad con api.py y cli_tester.py.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    estado_actual = tiendita_graph.get_state(config)
    pending = estado_actual.values.get("pending_approval") if estado_actual else None
    
    if pending:
        pending["status"] = "approved" if approved else "rejected"
        pending["human_notes"] = notes or correction
        # Registrar feedback para fine-tuning LoRA NeMo Customizer
        from tools.few_shot_retriever import record_hitl_feedback
        record_hitl_feedback(
            agent_role="hitl_operator",
            user_input=str(pending.get("description")),
            agent_output=pending.get("proposed_data"),
            human_approved=approved,
            correction=correction,
            notes=notes
        )
        tiendita_graph.update_state(config, {"pending_approval": pending})
        
    return tiendita_graph.invoke(None, config=config)
