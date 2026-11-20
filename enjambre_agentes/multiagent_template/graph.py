"""
graph.py — Plantilla unificada de orquestación multiagente en LangGraph.

Implementa un Grafo Jerárquico Supervisor-Especialistas compuesto por:
1. Nodo Supervisor / Router:
   Evalúa el estado global y delega dinámicamente según la necesidad del flujo.
2. Agente Investigador (RAG):
   Recupera y sintetiza evidencia documental desde Research-Knowledge-Backend y fuentes académicas.
3. Agente Especialista (Dominio):
   Ejecuta cálculos analíticos, validaciones matemáticas (SymPy), patentes y definiciones.
4. Agente Reportador:
   Fusiona los hallazgos en un reporte final estructurado, aplica norma IEEE y despacha notificaciones.
"""
from __future__ import annotations

import os
import json
import re
from typing import Dict, Any, Generator, Optional, List

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from state import OrchestratorState, SupervisorDecision
from models import get_llm
from tools_bridge import (
    RESEARCHER_TOOLS,
    SPECIALIST_TOOLS,
    REPORTER_TOOLS,
    enviar_email_reporte,
    formateador_citas_ieee
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. NODO SUPERVISOR / ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def supervisor_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Nodo Supervisor / Director de Orquesta.
    
    Analiza la consulta original, el historial conversacional y el estado actual
    para delegar de forma autónoma al especialista correspondiente o finalizar.
    """
    iteration = state.get("iteration_count", 0) + 1
    
    # Salvaguarda contra bucles infinitos
    if iteration > 6:
        print("[Supervisor] Límite de iteraciones alcanzado. Enrutando a Reportador.")
        return {
            "next_agent": "reportador",
            "iteration_count": iteration,
            "supervisor_notes": "Límite de ciclos alcanzado; forzando cierre y reporte."
        }
    
    # Si el reportador ya entregó el informe final, terminamos
    if state.get("final_report") and state.get("sender") == "reportador":
        return {
            "next_agent": "FIN",
            "iteration_count": iteration,
            "supervisor_notes": "El reporte final ha sido generado y entregado exitosamente."
        }
    
    # Respetar modos de flujo forzados por el usuario si aplican
    flow = state.get("flow_type", "Híbrido")
    has_rag = bool(state.get("rag_context"))
    has_domain = bool(state.get("domain_context") or state.get("domain_results"))
    
    provider = state.get("provider", os.getenv("DEFAULT_LLM_PROVIDER", "NVIDIA"))
    model_name = state.get("model_name")
    llm = get_llm(provider=provider, model_name=model_name, temperature=0.0)

    system_prompt = (
        "Eres el Supervisor Maestro de un Sistema de Orquestación Multiagente.\n"
        "Tu misión es analizar la consulta y delegar el trabajo al sub-agente especializado adecuado:\n"
        "1. 'investigador': Si se necesita consultar documentos locales, papers en PDF, arXiv o antecedentes bibliográficos.\n"
        "2. 'especialista': Si la tarea requiere cálculos matemáticos (SymPy), definiciones ontológicas, patentes o explicaciones didácticas.\n"
        "3. 'reportador': Si ya se cuenta con la información necesaria para redactar el reporte final estructurado y generar citas.\n"
        "4. 'FIN': Si la tarea está 100% completada y el reporte final ya fue emitido.\n\n"
        "REGLAS DE DECISIÓN:\n"
        f"- Modo de Flujo actual: {flow}\n"
        f"- ¿Existe evidencia documental (RAG)?: {'SÍ' if has_rag else 'NO'}\n"
        f"- ¿Existen cálculos/análisis de dominio?: {'SÍ' if has_domain else 'NO'}\n"
        "- Si el flujo es 'Solo RAG' y aún no se consulta la evidencia -> 'investigador'.\n"
        "- Si el flujo es 'Solo Dominio' y aún no se calcula -> 'especialista'.\n"
        "- En flujo 'Híbrido' o 'Completo', primero investiga ('investigador') y luego calcula/profundiza ('especialista'), o viceversa según la consulta.\n"
        "- Una vez reunida la información requerida -> delega a 'reportador'.\n\n"
        "Devuelve tu decisión en formato JSON estricto con las claves exactas:\n"
        '{"next_step": "investigador" | "especialista" | "reportador" | "FIN", "reasoning": "...", "instructions_for_agent": "..."}'
    )

    human_content = (
        f"Consulta del usuario: {state.get('query', '')}\n"
        f"Último agente que actuó: {state.get('sender', 'Ninguno (Inicio)')}\n"
        f"Iteración actual: {iteration}\n"
        f"Resumen de RAG: {state.get('rag_context', '')[:300]}...\n"
        f"Resumen de Dominio: {state.get('domain_context', '')[:300]}..."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content)
    ]

    try:
        response = llm.invoke(messages)
        text = response.content if isinstance(response.content, str) else str(response.content)
        # Extraer JSON de la respuesta
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            decision = parsed.get("next_step", "reportador")
            reasoning = parsed.get("reasoning", "")
        else:
            decision = "reportador" if (has_rag or has_domain) else "investigador"
            reasoning = "Fallback por heurística directa"
    except Exception as e:
        print(f"[Supervisor] Falló estructuración de decisión ({e}). Usando fallback heurístico.")
        if not has_rag and flow != "Solo Dominio":
            decision = "investigador"
        elif not has_domain and flow != "Solo RAG":
            decision = "especialista"
        else:
            decision = "reportador"
        reasoning = f"Heurística de contingencia por error: {e}"

    print(f"\n[Supervisor] -> Decisión: '{decision}'. Razón: {reasoning}")
    return {
        "next_agent": decision,
        "iteration_count": iteration,
        "supervisor_notes": reasoning,
    }


def router_supervisor(state: OrchestratorState) -> str:
    """Función de enrutamiento condicional posterior al Supervisor."""
    next_step = state.get("next_agent", "reportador")
    if next_step == "investigador":
        return "investigador"
    elif next_step == "especialista":
        return "especialista"
    elif next_step == "reportador":
        return "reportador"
    return END


# ─────────────────────────────────────────────────────────────────────────────
# 2. SUB-AGENTE 1: INVESTIGADOR (RAG & KNOWLEDGE BASE)
# ─────────────────────────────────────────────────────────────────────────────

def investigador_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Sub-agente especializado en recuperación documental.
    
    Consulta el índice FTS5/BM25 de Research-Knowledge-Backend, recupera
    paquetes canónicos de investigación y consulta literatura académica externa.
    """
    print("\n🔍 [Agente Investigador] Iniciando recuperación documental...")
    provider = state.get("provider", os.getenv("DEFAULT_LLM_PROVIDER", "NVIDIA"))
    model_name = state.get("model_name")
    llm = get_llm(provider=provider, model_name=model_name, temperature=0.1)

    system_prompt = (
        "Eres el Agente Investigador Científico del enjambre.\n"
        "Tu misión es buscar evidencia técnica fundamentada en la base documental indexada y repositorios científicos.\n"
        "HERRAMIENTAS:\n"
        "- `buscar_conocimiento_backend`: Consulta la base local de paquetes de investigación (knowledge.db FTS5).\n"
        "- `sintetizar_paquete_evidencia`: Consolida múltiples evidencias en una estructura canónica.\n"
        "- `buscador_arxiv`: Busca preprints teóricos en arXiv.\n"
        "- `buscador_semantic_scholar`: Busca artículos interdisciplinarios y citas.\n\n"
        "INSTRUCCIONES:\n"
        "1. Realiza búsquedas precisas usando las herramientas disponibles.\n"
        "2. Sintetiza los hallazgos indicando claramente las fuentes y paquetes consultados.\n"
        "3. Sé conciso pero riguroso."
    )

    agent = create_react_agent(
        model=llm,
        tools=RESEARCHER_TOOLS,
        prompt=system_prompt
    )

    query = state.get("query", "")
    history = state.get("messages", [])
    result = agent.invoke({"messages": history + [HumanMessage(content=query)]})
    
    last_message = result["messages"][-1]
    resumen_investigador = last_message.content if isinstance(last_message.content, str) else str(last_message.content)

    # Identificar fuentes citadas
    fuentes_encontradas = re.findall(r"\[Package\s+\d+\]|https?://[^\s\)]+|arXiv:\d+\.\d+", resumen_investigador)

    return {
        "rag_context": resumen_investigador,
        "rag_sources": list(set(fuentes_encontradas)),
        "sender": "investigador",
        "messages": [AIMessage(content=f"[Investigador RAG]:\n{resumen_investigador}")]
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. SUB-AGENTE 2: ESPECIALISTA (CÁLCULOS, DOMINIO Y PATENTES)
# ─────────────────────────────────────────────────────────────────────────────

def especialista_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Sub-agente especializado en cálculos analíticos y herramientas de dominio.
    
    Aplica SymPy para validación de ecuaciones, ontologías formales, patentes
    y traducciones didácticas basadas en herramientas_optica.py.
    """
    print("\n⚙️ [Agente Especialista] Iniciando análisis analítico y de dominio...")
    provider = state.get("provider", os.getenv("DEFAULT_LLM_PROVIDER", "NVIDIA"))
    model_name = state.get("model_name")
    llm = get_llm(provider=provider, model_name=model_name, temperature=0.1)

    system_prompt = (
        "Eres el Agente Especialista de Dominio Técnico.\n"
        "Tu misión es resolver la dimensión matemática, conceptual profunda y tecnológica de la consulta.\n"
        "HERRAMIENTAS:\n"
        "- `optimizador_ecuaciones`: Valida y simplifica expresiones matemáticas usando SymPy y genera formato LaTeX estricto.\n"
        "- `diccionario_optica`: Obtiene la definición formal y ontológica de términos científicos.\n"
        "- `traductor_didactico`: Explica conceptos complejos mediante modelos intuitivos y analogías.\n"
        "- `buscador_patentes`: Investiga patentes registradas en Google Patents.\n"
        "- `buscador_wikipedia`: Consulta antecedentes históricos o biografías.\n"
        "- `lector_web_profundo`: Extrae texto limpio de URLs relevantes.\n\n"
        "INSTRUCCIONES:\n"
        "1. Si la consulta involucra fórmulas o matemáticas, utiliza obligatoriamente `optimizador_ecuaciones`.\n"
        "2. Si involucra conceptos teóricos nuevos, define con precisión su significado físico.\n"
        "3. Presenta los resultados claramente estructurados."
    )

    agent = create_react_agent(
        model=llm,
        tools=SPECIALIST_TOOLS,
        prompt=system_prompt
    )

    query = state.get("query", "")
    history = state.get("messages", [])
    rag_info = state.get("rag_context", "")
    
    prompt_usuario = f"Consulta: {query}\n\nContexto previo recuperado:\n{rag_info[:1500]}"
    result = agent.invoke({"messages": history + [HumanMessage(content=prompt_usuario)]})

    last_message = result["messages"][-1]
    resumen_especialista = last_message.content if isinstance(last_message.content, str) else str(last_message.content)

    return {
        "domain_context": resumen_especialista,
        "domain_results": {"raw_analysis": resumen_especialista},
        "sender": "especialista",
        "messages": [AIMessage(content=f"[Especialista Dominio]:\n{resumen_especialista}")]
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. SUB-AGENTE 3: REPORTADOR (SÍNTESIS, IEEE Y DESPACHO DE ACCIONES)
# ─────────────────────────────────────────────────────────────────────────────

def reportador_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Sub-agente Reportador.
    
    Consolida la evidencia de RAG y los cálculos de Dominio en un informe técnico
    estructurado (Resumen o Científico), aplica formato de citas IEEE y despacha
    acciones externas como notificaciones por correo electrónico (SMTP).
    """
    print("\n📝 [Agente Reportador] Redactando reporte final y evaluando acciones...")
    provider = state.get("provider", os.getenv("DEFAULT_LLM_PROVIDER", "NVIDIA"))
    model_name = state.get("model_name")
    llm = get_llm(provider=provider, model_name=model_name, temperature=0.2)

    query = state.get("query", "")
    rag_context = state.get("rag_context", "Sin evidencia documental disponible.")
    domain_context = state.get("domain_context", "Sin análisis de dominio disponible.")
    mode = state.get("response_mode", "Científico")

    if mode == "Resumen":
        prompt_redaccion = (
            "Eres un sintetizador ultra-conciso.\n"
            "Elabora una respuesta directa y precisa de A LO SUMO UN PÁRRAFO a la consulta del usuario.\n"
            "Sé técnico, riguroso y responde al grano.\n\n"
            f"Consulta: {query}\n"
            f"Evidencia RAG:\n{rag_context}\n"
            f"Análisis Especialista:\n{domain_context}"
        )
    else:
        # Modo Científico / Dossier estructurado
        prompt_redaccion = (
            "Eres un Doctor e Investigador Principal altamente calificado.\n"
            "Tu tarea es fusionar la evidencia documental y los cálculos técnicos en un artículo/reporte riguroso en Markdown.\n\n"
            "ESTRUCTURA OBLIGATORIA:\n"
            "1. **Resumen Ejecutivo**: Planteamiento y hallazgos centrales.\n"
            "2. **Evidencia Documental y Estado del Arte**: Síntesis de la literatura citando fuentes explícitamente.\n"
            "3. **Desarrollo Técnico y Fundamentación**: Ecuaciones validadas (formato LaTeX $$...$$) y análisis físico.\n"
            "4. **Conclusión**: Síntesis de implicaciones prácticas o científicas.\n"
            "5. **Referencias Bibliográficas**: Lista de fuentes bajo formato estándar IEEE.\n\n"
            f"Consulta del Usuario: {query}\n\n"
            f"--- EVIDENCIA DE INVESTIGACIÓN (RAG) ---\n{rag_context}\n\n"
            f"--- ANÁLISIS TÉCNICO Y CÁLCULOS (ESPECIALISTA) ---\n{domain_context}\n"
        )

    response = llm.invoke([
        SystemMessage(content="Actúa como redactor científico y consolidador técnico."),
        HumanMessage(content=prompt_redaccion)
    ])
    
    final_report = response.content if isinstance(response.content, str) else str(response.content)

    # Evaluar si se solicitó despacho por correo electrónico
    email_dest = state.get("email_recipient")
    email_enviado = False
    email_status = None

    if email_dest:
        asunto = state.get("email_subject") or f"Reporte Técnico Multiagente: {query[:40]}"
        print(f"[Reportador] Despachando reporte por email a '{email_dest}'...")
        status_msg = enviar_email_reporte.invoke({
            "destinatario": email_dest,
            "asunto": asunto,
            "contenido_markdown": final_report
        })
        email_status = status_msg
        email_enviado = "exitosamente" in status_msg.lower()

    return {
        "final_report": final_report,
        "fused_context": f"RAG:\n{rag_context}\n\nDOMINIO:\n{domain_context}",
        "email_sent": email_enviado,
        "email_status": email_status,
        "sender": "reportador",
        "next_agent": "FIN",
        "messages": [AIMessage(content=final_report)]
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. CONSTRUCCIÓN Y COMPILACIÓN DEL GRAFO
# ─────────────────────────────────────────────────────────────────────────────

def build_orchestrator(checkpointer: Optional[MemorySaver] = None):
    """
    Ensambla el grafo StateGraph conectando el Supervisor con los tres sub-agentes.
    
    Topología:
      START -> supervisor
      supervisor -> [investigador | especialista | reportador | END]
      investigador -> supervisor
      especialista -> supervisor
      reportador -> supervisor (-> END)
    """
    builder = StateGraph(OrchestratorState)

    # 1. Registrar Nodos
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("investigador", investigador_node)
    builder.add_node("especialista", especialista_node)
    builder.add_node("reportador", reportador_node)

    # 2. Configurar Flujo de Entrada
    builder.add_edge(START, "supervisor")

    # 3. Enrutamiento Condicional desde Supervisor
    builder.add_conditional_edges(
        "supervisor",
        router_supervisor,
        {
            "investigador": "investigador",
            "especialista": "especialista",
            "reportador": "reportador",
            END: END
        }
    )

    # 4. Retorno de Sub-Agentes al Supervisor (bucle de orquestación reactivo)
    builder.add_edge("investigador", "supervisor")
    builder.add_edge("especialista", "supervisor")
    builder.add_edge("reportador", "supervisor")

    # 5. Compilación con memoria
    memory = checkpointer or MemorySaver()
    return builder.compile(checkpointer=memory)


# Instancia compilada global por defecto
orchestrator_graph = build_orchestrator()


# ─────────────────────────────────────────────────────────────────────────────
# 6. MÉTODOS DE EJECUCIÓN (INVKOKE Y STREAM)
# ─────────────────────────────────────────────────────────────────────────────

def run_orchestration(
    query: str,
    thread_id: str = "default_thread",
    provider: str = "NVIDIA",
    model_name: Optional[str] = None,
    flow_type: str = "Híbrido",
    response_mode: str = "Científico",
    email_recipient: Optional[str] = None,
    checkpointer: Optional[MemorySaver] = None
) -> Dict[str, Any]:
    """
    Ejecuta el grafo multiagente de forma sincrónica completa.
    
    Returns:
        Estado final con 'final_report', 'rag_context', 'domain_results', etc.
    """
    graph = build_orchestrator(checkpointer=checkpointer) if checkpointer else orchestrator_graph
    
    initial_state: OrchestratorState = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "provider": provider,
        "model_name": model_name,
        "temperature": 0.2,
        "flow_type": flow_type,
        "response_mode": response_mode,
        "email_recipient": email_recipient,
        "iteration_count": 0,
        "evidence_packages": [],
        "rag_sources": [],
        "errors": []
    }

    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(initial_state, config=config)


def run_orchestration_stream(
    query: str,
    thread_id: str = "stream_thread",
    provider: str = "NVIDIA",
    model_name: Optional[str] = None,
    flow_type: str = "Híbrido",
    response_mode: str = "Científico",
    email_recipient: Optional[str] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Ejecuta el grafo en streaming emitiendo eventos nodo por nodo para interfaces de usuario.
    """
    initial_state: OrchestratorState = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "provider": provider,
        "model_name": model_name,
        "temperature": 0.2,
        "flow_type": flow_type,
        "response_mode": response_mode,
        "email_recipient": email_recipient,
        "iteration_count": 0,
        "evidence_packages": [],
        "rag_sources": [],
        "errors": []
    }

    config = {"configurable": {"thread_id": thread_id}}
    for event in orchestrator_graph.stream(initial_state, config=config):
        yield event
