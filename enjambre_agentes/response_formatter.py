"""
response_formatter.py — Formatea la salida del enjambre en JSON estructurado.

Convierte el estado interno de LangGraph en una respuesta limpia, consistente y
fácil de parsear para clientes (CLI, API REST, app móvil).

Cada respuesta tiene este esquema:
{
  "respuesta": "<texto en español para el usuario>",
  "agente": "<nombre del agente que respondió>",
  "accion": "<tipo de acción: consulta|venta|inventario|reporte|promo|pago|hits|fin|error>",
  "datos": <dict opcional con datos estructurados>,
  "pendiente_aprobacion": <dict o null>,
  "evidencia_bd": <lista o null>,
  "errores": <lista o null>,
  "iteraciones": <int>
}
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def formatear_respuesta(
    resultado: Dict[str, Any],
    incluir_evidencia: bool = False,
) -> Dict[str, Any]:
    """
    Transforma el estado del grafo en una respuesta JSON estructurada.

    Args:
        resultado: Diccionario devuelto por run_orchestration / resume_orchestration.
        incluir_evidencia: Si True, incluye db_evidence en la salida.

    Returns:
        Diccionario con claves: respuesta, agente, accion, datos, pendiente_aprobacion,
        evidencia_bd, errores, iteraciones.
    """
    messages: List[Any] = resultado.get("messages", []) or []
    ultimo_mensaje = ""
    for m in reversed(messages):
        contenido = getattr(m, "content", None)
        if contenido and isinstance(contenido, str) and contenido.strip():
            ultimo_mensaje = contenido.strip()
            break

    agente = resultado.get("sender", "supervisor")
    pending = resultado.get("pending_approval")
    iteration = resultado.get("iteration_count", 0)
    errors = resultado.get("validation_errors", []) or []
    strategic_report = resultado.get("strategic_report")
    promo_assets = resultado.get("promo_assets")

    # ── Determinar tipo de acción ──
    accion = _inferir_accion(agente, pending, strategic_report, promo_assets, ultimo_mensaje)

    # ── Construir datos estructurados según el tipo ──
    datos: Optional[Dict[str, Any]] = None

    if accion == "venta" and pending:
        datos = {
            "tipo": "venta",
            "resumen": pending.get("summary"),
            "payload": pending.get("payload"),
        }
    elif accion == "inventario" and pending:
        datos = {
            "tipo": "inventario",
            "resumen": pending.get("summary"),
            "payload": pending.get("payload"),
        }
    elif accion == "promocion" and pending:
        datos = {
            "tipo": "promocion",
            "resumen": pending.get("summary"),
            "payload": pending.get("payload"),
        }
    elif accion == "reporte" and strategic_report:
        datos = {
            "tipo": "reporte_estrategico",
            "reporte": strategic_report,
        }
    elif accion == "promo_assets" and promo_assets:
        datos = {
            "tipo": "activos_promocionales",
            "assets": promo_assets,
        }
    elif accion == "consulta_inventario":
        # Intentar extraer datos estructurados de db_evidence
        evidencia = resultado.get("db_evidence", []) or []
        if evidencia:
            datos = {"tipo": "consulta_inventario", "evidencia": evidencia[:1]}

    # ── Construir respuesta final ──
    respuesta: Dict[str, Any] = {
        "respuesta": ultimo_mensaje or "No se generó respuesta.",
        "agente": agente,
        "accion": accion,
        "datos": datos,
        "pendiente_aprobacion": pending if pending and pending.get("requires_confirmation") else None,
        "iteraciones": iteration,
    }

    if incluir_evidencia:
        respuesta["evidencia_bd"] = resultado.get("db_evidence", []) or []

    if errors:
        respuesta["errores"] = errors

    return respuesta


def _inferir_accion(
    agente: str,
    pending: Optional[Dict[str, Any]],
    strategic_report: Optional[Dict[str, Any]],
    promo_assets: Optional[Dict[str, Any]],
    mensaje: str,
) -> str:
    """Infere el tipo de acción a partir del estado del grafo."""
    if pending and pending.get("requires_confirmation"):
        at = pending.get("action_type", "")
        if at == "sale_transaction":
            return "venta"
        if at == "inventory_mutation":
            return "inventario"
        if at == "promo_campaign":
            return "promocion"
        return "hits"

    if agente == "investigador" and strategic_report:
        return "reporte"
    if agente == "publicista" and promo_assets:
        return "promo_assets"
    if agente == "analista":
        return "consulta_financiera"
    if agente == "control":
        return "consulta_inventario"
    if agente == "vendedor":
        return "consulta_venta"
    if agente == "tutor_ui":
        return "asistencia_pago"
    if agente in ("supervisor", "inicio"):
        return "fin"
    return "otro"


def formatear_para_cli(respuesta: Dict[str, Any]) -> str:
    """
    Convierte la respuesta estructurada en texto legible para el CLI.
    """
    lineas: List[str] = []

    agente = respuesta.get("agente", "agente")
    accion = respuesta.get("accion", "")
    texto = respuesta.get("respuesta", "")

    # Etiqueta del agente
    etiquetas = {
        "supervisor": "🧠 Supervisor",
        "control": "📦 Control",
        "vendedor": "💳 Vendedor",
        "analista": "📊 Analista",
        "investigador": "🔍 Investigador",
        "publicista": "🎬 Publicista",
        "tutor_ui": "📱 Tutor UI",
        "aprobacion_hitl": "⚠️ HITL",
        "inicio": "🤖 Asistente",
    }
    etiqueta = etiquetas.get(agente, f"🤖 {agente}")
    lineas.append(f"[{etiqueta}] {texto}")

    # Si hay aprobación pendiente, mostrarla
    pendiente = respuesta.get("pendiente_aprobacion")
    if pendiente:
        lineas.append("")
        lineas.append("⏸  Aprobación requerida:")
        lineas.append(f"   Acción: {pendiente.get('action_type', '')}")
        lineas.append(f"   Resumen: {pendiente.get('summary', '')}")
        payload = pendiente.get("payload", {})
        if payload:
            lineas.append(f"   Payload: {json.dumps(payload, ensure_ascii=False)}")

    # Si hay reporte estratégico, mostrar resumen
    datos = respuesta.get("datos")
    if datos and datos.get("tipo") == "reporte_estrategico":
        rep = datos.get("reporte", {})
        lineas.append("")
        lineas.append("📋 Reporte estratégico (9 secciones):")
        for clave in [
            "identificacion_sector", "mercado_tendencias", "clientes",
            "problemas", "soluciones", "hipotesis", "objetivos",
            "impacto", "hallazgos",
        ]:
            val = rep.get(clave, "")
            if val:
                lineas.append(f"   • {clave}: {val[:100]}...")

    # Si hay activos promocionales
    if datos and datos.get("tipo") == "activos_promocionales":
        assets = datos.get("assets", {})
        lineas.append("")
        lineas.append("🎬 Activos promocionales:")
        if assets.get("copy_promocional"):
            lineas.append(f"   Copy: {assets['copy_promocional']}")
        if assets.get("call_to_action"):
            lineas.append(f"   CTA: {assets['call_to_action']}")

    return "\n".join(lineas)


def respuesta_json(resultado: Dict[str, Any]) -> str:
    """
    Devuelve la respuesta del enjambre como string JSON listo para enviar por API.
    """
    formateada = formatear_respuesta(resultado, incluir_evidencia=False)
    return json.dumps(formateada, ensure_ascii=False, indent=2)
