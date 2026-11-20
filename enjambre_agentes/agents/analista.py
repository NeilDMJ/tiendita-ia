"""
Agente Especialista en Finanzas y Auditoría Comercial (Analista Financiero).
Rol de Solo Lectura: Análisis de márgenes brutos, flujo de caja y rotación de SKU.
"""
from __future__ import annotations

from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from config.models import get_llm_para_agente, extraer_texto_mensaje
from schemas.state import OrchestratorState
from tools.analytics_tools import get_cash_flow, get_margins_by_sku, get_rotation_by_sku, get_sales_summary
from tools.db_client import query_sales, query_inventory
from tools.few_shot_retriever import retrieve_few_shots

ANALISTA_SYSTEM_PROMPT = """Eres el Agente Analista Financiero y de Rendimiento de Tiendita IA.
Tu rol es estrictamente de AUDITORÍA Y SOLO LECTURA.
Tus responsabilidades son:
1. Calcular el flujo de caja neto del negocio (ingresos por ventas vs compras de inventario vs gastos operativos).
2. Determinar la rentabilidad porcentual y el margen de contribución de cada SKU.
3. Evaluar la velocidad de rotación de inventarios para identificar productos estancados y productos líderes.
4. Generar diagnósticos ejecutivos con recomendaciones concretas de liquidez y márgenes.

REGLAS INQUEBRANTABLES:
- TIENES PROHIBIDO modificar inventarios, crear carritos o ejecutar cobros. Tu rol es 100% analítico.
- Basa todos tus cálculos en las herramientas oficiales de finanzas y ventas.
- Ofrece conclusiones estructuradas y sustentadas cuantitativamente.
"""


def get_analista_agent():
    """Instancia el agente ReAct de Análisis Financiero."""
    llm = get_llm_para_agente("analista")
    tools = [
        get_cash_flow,
        get_margins_by_sku,
        get_rotation_by_sku,
        get_sales_summary,
        query_sales,
        query_inventory,
        retrieve_few_shots,
    ]
    return create_react_agent(llm, tools=tools, prompt=ANALISTA_SYSTEM_PROMPT)


def analista_node(state: OrchestratorState) -> Dict[str, Any]:
    """Nodo ejecutor para el Analista en LangGraph."""
    agent = get_analista_agent()
    mensajes = list(state.get("messages", []))
    
    prompt_adicional = "[ROL_ACTIVO: Auditor Financiero de Solo Lectura]"
    mensajes_invocacion = mensajes + [HumanMessage(content=prompt_adicional)]
    
    resultado = agent.invoke({"messages": mensajes_invocacion})
    mensajes_nuevos = resultado.get("messages", [])
    ultimo_mensaje = extraer_texto_mensaje(mensajes_nuevos[-1].content) if mensajes_nuevos else "Análisis financiero finalizado."
    
    return {
        "messages": [AIMessage(content=f"[ANALISTA]: {ultimo_mensaje}")],
        "db_evidence": str(ultimo_mensaje)[:1000],
        "iteration_count": state.get("iteration_count", 0) + 1
    }
