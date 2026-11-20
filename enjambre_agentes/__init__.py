"""
multiagent_template — Plantilla unificada de orquestación multiagente en LangGraph.

Integra los aprendizajes y componentes de:
- OptiAgent (herramientas analíticas, fábrica de modelos, redacción científica)
- Research-Knowledge-Backend (búsqueda SQLite FTS5/BM25, evidencia documental canónica, NVIDIA Nemotron Grounded RAG)
- AgriPoli (arquitectura jerárquica con supervisor, bucles de retroalimentación y estados tipados)
"""
from state import OrchestratorState, EvidencePackage, DomainToolResult, SupervisorDecision
from models import get_llm, get_embeddings_model, get_available_models
from tools_bridge import (
    buscar_conocimiento_backend,
    consultar_nemotron_grounded,
    sintetizar_paquete_evidencia,
    reconstruir_indice_busqueda,
    optimizador_ecuaciones,
    diccionario_optica,
    traductor_didactico,
    buscador_patentes,
    buscador_arxiv,
    buscador_semantic_scholar,
    buscador_wikipedia,
    lector_web_profundo,
    formateador_citas_ieee,
    enviar_email_reporte,
    RESEARCHER_TOOLS,
    SPECIALIST_TOOLS,
    REPORTER_TOOLS,
    ALL_TOOLS,
    to_mcp_tool_definitions,
)
from graph import (
    build_orchestrator,
    orchestrator_graph,
    run_orchestration,
    run_orchestration_stream,
)

__all__ = [
    "OrchestratorState",
    "EvidencePackage",
    "DomainToolResult",
    "SupervisorDecision",
    "get_llm",
    "get_embeddings_model",
    "get_available_models",
    "buscar_conocimiento_backend",
    "consultar_nemotron_grounded",
    "sintetizar_paquete_evidencia",
    "reconstruir_indice_busqueda",
    "optimizador_ecuaciones",
    "diccionario_optica",
    "traductor_didactico",
    "buscador_patentes",
    "buscador_arxiv",
    "buscador_semantic_scholar",
    "buscador_wikipedia",
    "lector_web_profundo",
    "formateador_citas_ieee",
    "enviar_email_reporte",
    "RESEARCHER_TOOLS",
    "SPECIALIST_TOOLS",
    "REPORTER_TOOLS",
    "ALL_TOOLS",
    "to_mcp_tool_definitions",
    "build_orchestrator",
    "orchestrator_graph",
    "run_orchestration",
    "run_orchestration_stream",
]
