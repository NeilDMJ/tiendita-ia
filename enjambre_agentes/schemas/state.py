"""
Estado maestro compartido de Tiendita IA (OrchestratorState).
Estructura TypedDict para la orquestación multimodal en LangGraph.
"""
from __future__ import annotations

from typing import Annotated, Optional, TypedDict
from langgraph.graph.message import add_messages


class OrchestratorState(TypedDict, total=False):
    """
    Estado multimodal central compartido entre el Supervisor y los 6 agentes especialistas.
    """
    # Historial de conversación / traza de mensajes de LangGraph
    messages: Annotated[list, add_messages]

    # Fuente del evento: 'chat', 'catalog-scan', 'pos-checkout', 'receipt-ocr', 'cron'
    event_source: str

    # Carga útil multimodal (imagen en base64, mime_type, metadata de cámara/archivo)
    vision_payload: Optional[dict]

    # Estado de la interfaz de usuario en cajas / terminales punto de venta
    ui_state: Optional[dict]

    # Evidencia recuperada de la base de datos o NeMo Retriever
    db_evidence: Optional[str]

    # Ejemplos dinámicos Few-Shot recuperados para guiar al modelo
    few_shot_examples: Optional[list[dict]]

    # Reporte estratégico estructurado (Investigador)
    strategic_report: Optional[dict]

    # Activos publicitarios generados (copy, CTA, prompt de video 9:16)
    promo_assets: Optional[dict]

    # Carga pendiente de aprobación humana (HITL)
    pending_approval: Optional[dict]

    # Siguiente agente designado por el Supervisor
    next_agent: Optional[str]

    # Contador de iteraciones del ciclo de orquestación (máximo 6)
    iteration_count: int

    # Cadena compuesta pendiente de ejecución secuencial
    compound_chain: Optional[list[str]]

    # Registro de errores no fatales durante la ejecución
    errores: list[str]
