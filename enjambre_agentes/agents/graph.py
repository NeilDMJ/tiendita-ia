"""
Grafo LangGraph con memoria Checkpointer e interrupciones Human-in-the-Loop (HITL).
Orquesta al Supervisor y los 6 agentes especialistas conectando control, vendedor y publicista hacia approval_gate.
Exporta exactamente: run_orchestration, run_orchestration_stream y resume_orchestration.
"""
from __future__ import annotations

import uuid
from typing import Any, AsyncGenerator, Dict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from schemas.state import OrchestratorState
from agents.supervisor import supervisor_node
from agents.control import control_node
from agents.vendedor import vendedor_node
from agents.analista import analista_node
from agents.investigador import investigador_node
from agents.publicista import publicista_node
from agents.tutor_ui import tutor_ui_node


def approval_gate_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Nodo de verificación para Human-in-the-Loop.
    Si hay una propuesta que requiere intervención humana y aún no ha sido aprobada,
    se mantiene en pending para ser resuelta antes de volver al supervisor.
    """
    pending = state.get("pending_approval")
    if pending and pending.get("status") == "approved":
        # Limpiar aprobación una vez consumida
        return {
            "pending_approval": None,
            "messages": [state.get("messages", [])[-1]] if state.get("messages") else []
        }
    return {}


def router_supervisor(state: OrchestratorState) -> str:
    """Enrutador condicional basado en la decisión estructurada del Supervisor."""
    siguiente = state.get("next_agent", "FINISH")
    if siguiente in ["control", "vendedor", "analista", "investigador", "publicista", "tutor_ui"]:
        return siguiente
    return END


def router_approval(state: OrchestratorState) -> str:
    """Evalúa si una acción de control, vendedor o publicista debe pasar por el gate de aprobación."""
    pending = state.get("pending_approval")
    if pending and pending.get("requires_human") and pending.get("status") == "pending":
        return "approval_gate"
    return "supervisor"


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
    builder.add_conditional_edges("control", router_approval, {"approval_gate": "approval_gate", "supervisor": "supervisor"})
    builder.add_conditional_edges("vendedor", router_approval, {"approval_gate": "approval_gate", "supervisor": "supervisor"})
    builder.add_conditional_edges("publicista", router_approval, {"approval_gate": "approval_gate", "supervisor": "supervisor"})

    # 5. Agentes analíticos o de pantalla regresan directo al supervisor
    builder.add_edge("analista", "supervisor")
    builder.add_edge("investigador", "supervisor")
    builder.add_edge("tutor_ui", "supervisor")
    builder.add_edge("approval_gate", "supervisor")

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
    provider: str = "NVIDIA"
) -> Dict[str, Any]:
    """
    Ejecuta el ciclo de orquestación de Tiendita IA de forma síncrona.
    Nombre exacto estipulado para compatibilidad con api.py y cli_tester.py.
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
    
    return tiendita_graph.invoke(initial_state, config=config)


async def run_orchestration_stream(
    input_text: str,
    thread_id: Optional[str] = None,
    event_source: str = "chat",
    vision_payload: Optional[dict] = None,
    ui_state: Optional[dict] = None,
    provider: str = "NVIDIA"
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
