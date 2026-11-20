"""
state.py — Estado unificado para la orquestación multiagente en LangGraph.

Combina:
1. Historial de mensajes y memoria conversacional.
2. Contexto recuperado de PDFs y Knowledge Hub (evidence_packages, rag_context).
3. Resultados estructurados de herramientas de dominio (domain_results, cálculos, SymPy).
4. Metadatos de control del Supervisor (next_agent, iteration_count, sender, errores).
"""
from __future__ import annotations

import operator
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


# ─────────────────────────────────────────────────────────────────────────────
# 1. MODELOS PYDANTIC AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────

class EvidencePackage(BaseModel):
    """Esquema de un paquete de evidencia documental proveniente de Research-Knowledge-Backend."""
    package_id: Optional[int] = Field(default=None, description="Identificador del paquete en knowledge.db")
    title: str = Field(default="", description="Título del documento o paquete")
    summary: str = Field(default="", description="Resumen estructurado de la evidencia")
    detected_topics: List[str] = Field(default_factory=list, description="Tópicos identificados")
    people: List[str] = Field(default_factory=list, description="Autores o investigadores citados")
    organizations: List[str] = Field(default_factory=list, description="Instituciones u organizaciones")
    projects: List[str] = Field(default_factory=list, description="Proyectos de investigación vinculados")
    concepts: List[str] = Field(default_factory=list, description="Conceptos clave")
    metrics: List[str] = Field(default_factory=list, description="Métricas experimentales o datos numéricos")
    key_points: List[str] = Field(default_factory=list, description="Puntos clave extraídos")
    links_visible: List[str] = Field(default_factory=list, description="URLs verificadas en el documento")
    uncertainties: List[str] = Field(default_factory=list, description="Incertidumbres o campos con dudas")
    source_pdf: Optional[str] = Field(default=None, description="Ruta o nombre del archivo PDF fuente")
    hybrid_score: Optional[float] = Field(default=None, description="Puntaje híbrido (léxico FTS5 + semántico)")


class DomainToolResult(BaseModel):
    """Estructura normalizada para resultados generados por herramientas especializadas de dominio."""
    tool_name: str = Field(description="Nombre de la herramienta que generó el resultado")
    status: Literal["success", "error", "warning"] = Field(default="success")
    output: Any = Field(description="Salida cruda o calculada de la herramienta")
    latex_expression: Optional[str] = Field(default=None, description="Expresión LaTeX simplificada (ej. SymPy)")
    citations: List[str] = Field(default_factory=list, description="Citas formales producidas (IEEE, DOI, URL)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Metadatos complementarios")


class SupervisorDecision(BaseModel):
    """Decisión de enrutamiento tomada por el nodo Supervisor."""
    next_step: Literal["investigador", "especialista", "reportador", "FIN"] = Field(
        description="Siguiente agente al que se delega la tarea o FIN si el flujo está completado."
    )
    reasoning: str = Field(description="Explicación técnica de la decisión de enrutamiento")
    instructions_for_agent: str = Field(
        default="", description="Instrucciones específicas enfocadas para el siguiente agente"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. ESTADO UNIFICADO DEL GRAFO (OrchestratorState)
# ─────────────────────────────────────────────────────────────────────────────

class OrchestratorState(TypedDict, total=False):
    """
    Estado global unificado para la orquestación multiagente en LangGraph.
    
    Gestiona la comunicación entre el Supervisor/Router y los tres sub-agentes:
    - Agente Investigador (RAG & Knowledge Base)
    - Agente Especialista (Dominio, cálculos, SymPy, patentes)
    - Agente Reportador (Síntesis final, IEEE, notificaciones por email)
    """
    # ── Conversación y Memoria ──
    messages: Annotated[List[BaseMessage], add_messages]
    query: str                       # Consulta u objetivo formulado por el usuario
    
    # ── Control de Enrutamiento y Supervisor ──
    next_agent: str                  # "investigador" | "especialista" | "reportador" | "FIN"
    sender: str                      # Nombre del último nodo/agente que ejecutó
    supervisor_notes: str            # Justificación de la última decisión del supervisor
    iteration_count: int             # Contador para prevenir loops infinitos (máx 5-6)
    
    # ── Parámetros de Configuración del Modelo ──
    provider: str                    # "NVIDIA", "Gemini", "Groq", "Cohere", "Ollama"
    model_name: Optional[str]        # Nombre o tag específico del modelo LLM
    temperature: float               # Temperatura de inferencia
    flow_type: str                   # "Híbrido", "Solo RAG", "Solo Dominio", "Completo"
    response_mode: str               # "Resumen", "Científico", "Dossier"
    
    # ── Contexto Recuperado de PDFs y Knowledge Hub (Investigador) ──
    evidence_packages: Annotated[List[Dict[str, Any]], operator.add]  # Paquetes JSON estructurados
    rag_context: str                 # Texto consolidado extraído de la base documental
    rag_sources: Annotated[List[str], operator.add]                   # Fuentes documentales [Package X], PDFs, páginas
    
    # ── Resultados de Herramientas de Dominio (Especialista) ──
    domain_results: Dict[str, Any]   # Cálculos matemáticos, validaciones SymPy, patentes, etc.
    domain_context: str              # Texto explicativo o cálculos redactados por el especialista
    
    # ── Fusión y Síntesis Final (Reportador) ──
    fused_context: str               # Cruce y reconciliación entre evidencia documental y cálculos
    final_report: str                # Reporte final redactado en Markdown o texto puro
    
    # ── Acciones Externas ──
    email_recipient: Optional[str]   # Correo destino si se solicita envío
    email_subject: Optional[str]     # Asunto del correo electrónico
    email_sent: bool                 # Indicador de envío exitoso
    email_status: Optional[str]      # Registro de estado o error en el envío SMTP
    
    # ── Registro de Diagnósticos y Errores ──
    errors: Annotated[List[str], operator.add]  # Errores no fatales acumulados
