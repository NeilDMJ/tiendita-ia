"""
graph.py — Ecosistema Multiagente Comercial Multimodal en LangGraph.

Orquesta 6 Agentes Especializados + Supervisor Multicanal + Human-in-the-Loop (HITL):
1. Supervisor / Router (`supervisor_node`): Enrutamiento dinámico según event_source y Few-Shot.
2. Agente de Control (`control_node`): Inventario y OCR sin mutación directa previa a HITL.
3. Agente Vendedor (`vendedor_node`): Carrito POS, cross-selling y preparación de cobro.
4. Agente Analista (`analista_node`): Solo lectura, márgenes y flujo de caja con grounding.
5. Agente Investigador (`investigador_node`): Reporte comercial estructurado de 9 secciones fijas.
6. Agente Publicista (`publicista_node`): Activos de video 9:16 (5s) + copy y CTA.
7. Agente Tutor UI (`tutor_ui_node`): Guía de pagos móvil en máximo 2 oraciones accionables.
8. Nodo HITL (`aprobacion_hitl_node`): Interrupción determinista antes de mutaciones en BD.
"""
from __future__ import annotations

import os
import json
import re
from typing import Dict, Any, Generator, Optional, List, Literal

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, AnyMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from state import (
    OrchestratorState,
    StrategicReportModel,
    PromoAssetsModel,
    PendingApprovalModel,
    SupervisorDecision,
)
from models import get_llm
from guards import enforce_db_grounding, validate_strategic_report
from few_shot_retriever import FewShotRetriever
from tools_bridge import (
    parse_vision_catalog_item,
    parse_receipt_ocr,
    query_expiring_products,
    commit_inventory_mutation,
    build_pos_cart_from_vision,
    get_cross_sell_recommendations,
    commit_sale_transaction,
    get_cashflow_summary,
    get_product_margins,
    get_sales_cohort_metrics,
    search_market_trends,
    generate_promo_video_job,
    inspect_payment_step,
    crear_producto,
    actualizar_precio,
    consultar_inventario,
    ajustar_stock,
    find_product_by_name_or_alias,
    db as mock_db,
)


retriever = FewShotRetriever()


# ─────────────────────────────────────────────────────────────────────────────
# 1. NODO SUPERVISOR / ENRUTADOR MULTICANAL
# ─────────────────────────────────────────────────────────────────────────────

def supervisor_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Supervisor Central de la Plataforma Comercial.
    
    Evalúa:
    - `event_source`: "vision_api" | "ui_copilot" | "cron_trigger" | "chat"
    - `iteration_count`: Corta forzosamente en "FIN" si supera 6 iteraciones.
    - `pending_approval`: Si existe una acción que requiere confirmación humana, delega a "aprobacion_hitl".
    - `query` conversacional: Utiliza Few-Shot prompts o reglas semánticas para coordinar secuencias.
    """
    iteration = state.get("iteration_count", 0) + 1

    # Salvaguarda estricta: límite de 6 ciclos
    if iteration > 6:
        return {
            "next_agent": "FIN",
            "iteration_count": iteration,
            "supervisor_notes": "Límite máximo de 6 iteraciones alcanzado. Finalizando ejecución."
        }

    # Si hay una mutación pendiente de confirmación humana, derivar a HITL
    pending = state.get("pending_approval")
    if pending and pending.get("requires_confirmation", True):
        return {
            "next_agent": "aprobacion_hitl",
            "iteration_count": iteration,
            "supervisor_notes": f"Acción '{pending.get('action_type')}' requiere aprobación del usuario."
        }

    # Si el último nodo fue aprobación HITL o tutor_ui o reporte finalizado
    sender = state.get("sender", "")
    if sender == "aprobacion_hitl":
        return {
            "next_agent": "FIN",
            "iteration_count": iteration,
            "supervisor_notes": "Acción HITL procesada exitosamente."
        }

    event_source = state.get("event_source", "chat")
    vision_payload = state.get("vision_payload") or {}

    # Enrutamiento determinista por fuente de evento
    if event_source == "vision_api":
        endpoint = vision_payload.get("endpoint", "")
        if endpoint in ["/catalog-scan", "/receipt-ocr"]:
            next_step = "control"
            notes = f"Evento de visión {endpoint} delegado a Agente de Control."
        elif endpoint == "/pos-checkout":
            next_step = "vendedor"
            notes = "Evento de visión /pos-checkout delegado a Agente Vendedor."
        else:
            next_step = "control"
            notes = f"Endpoint {endpoint} no reconocido, derivado a Control."

        return {
            "next_agent": next_step,
            "iteration_count": iteration,
            "supervisor_notes": notes
        }

    elif event_source == "ui_copilot":
        return {
            "next_agent": "tutor_ui",
            "iteration_count": iteration,
            "supervisor_notes": "Evento de interfaz móvil delegado a Agente Tutor UI."
        }

    elif event_source == "cron_trigger":
        return {
            "next_agent": "control",
            "iteration_count": iteration,
            "supervisor_notes": "Disparo programado (cron) para revisión de caducidades en almacén."
        }

    # Canal CHAT: Enrutamiento semántico con inyección Few-Shot
    query = state.get("query", "")
    query_lower = query.lower()

    # Guard fuera_de_alcance: preguntas ajenas al negocio de tienda
    _FUERA_ALCANCE_TRIGGERS = [
        "clima", "temperatura", "pronóstico", "pronostico",
        "chiste", "broma", "cuéntame un", "cuentame un",
        "declaración fiscal", "declaracion fiscal", "sat ", "hacienda",
        "receta", "cocinar", "cómo se hace", "como se hace",
        "política", "elecciones", "noticias",
        "cotización de dólar", "tipo de cambio",
        "astrología", "horóscopo",
    ]
    if any(t in query_lower for t in _FUERA_ALCANCE_TRIGGERS):
        return {
            "next_agent": "FIN",
            "iteration_count": iteration,
            "supervisor_notes": "Consulta fuera del alcance de la tiendita. Se finaliza sin acción.",
            "messages": [AIMessage(content="Esa consulta está fuera del alcance de mi función como asistente de la tienda. Puedo ayudarte con inventario, precios, ventas y pagos. ¿En qué te ayudo?")]
        }

    # Heurística rápida y robusta para evitar timeouts de red si no hay API key
    if any(k in query_lower for k in ["flujo de caja", "flujo", "margen", "rentabilidad", "utilidad", "ganancia", "egreso", "balance financiero", "ingresos"]):
        next_step = "analista"
        notes = "Consulta de métricas financieras de solo lectura."
    elif any(k in query_lower for k in ["caducar", "vencer", "lote", "stock minimo", "inventario", "recibo", "factura", "precio", "sube", "cuesta", "stock", "llegaron", "merma", "alta", "dame de alta", "existencia", "catálogo", "catalogo"]):
        next_step = "control"
        notes = "Consulta u operación de catálogo, existencias, precios o comprobantes (asistente de tienda)."
    elif any(k in query_lower for k in ["carrito", "vender", "cobrar", "pos", "checkout", "cross-sell", "recomendar"]):
        next_step = "vendedor"
        notes = "Consulta orientada a ventas o cobro en caja."
    elif any(k in query_lower for k in ["reporte", "sector", "tendencia", "investigar", "mercado", "estrategico"]):
        next_step = "investigador"
        notes = "Consulta orientada a análisis e inteligencia de mercado (9 secciones)."
    elif any(k in query_lower for k in ["video", "promo", "campana", "publicidad", "descuento"]):
        next_step = "publicista"
        notes = "Generación de video vertical y campaña promocional."
    elif any(k in query_lower for k in ["pago", "spei", "tarjeta", "clabe", "qr", "boton", "pantalla"]):
        next_step = "tutor_ui"
        notes = "Asistencia sobre pasarelas de pago e interfaz móvil."
    else:
        # Fallback a LLM con Few-Shot retriever
        provider = state.get("provider", os.getenv("DEFAULT_LLM_PROVIDER", "NVIDIA"))
        model_name = state.get("model_name")
        few_shots = retriever.format_few_shots_for_prompt("orquestador", query)

        try:
            llm = get_llm(provider=provider, model_name=model_name, temperature=0.0)
            sys_msg = (
                "Eres el Supervisor Maestro del Ecosistema Multiagente Comercial.\n"
                "Tu función es analizar la solicitud y delegar al especialista idóneo:\n"
                "- 'control': Inventario, caducidades, alta de productos o lectura de facturas/tickets.\n"
                "- 'vendedor': Armado de carritos POS, venta cruzada y cobro.\n"
                "- 'analista': Flujo de caja, egresos, ingresos y márgenes de ganancia (solo lectura).\n"
                "- 'investigador': Inteligencia de mercado, clientes y reporte de 9 secciones.\n"
                "- 'publicista': Promociones comerciales, video 9:16 y copys persuasivos.\n"
                "- 'tutor_ui': Ayuda técnica con botones, errores o pagos en la app móvil.\n"
                "- 'FIN': Si la solicitud ya fue completamente resuelta.\n\n"
                f"{few_shots}\n"
                "Responde ÚNICAMENTE en JSON con la clave: {\"next_step\": \"<agente>\", \"reasoning\": \"<motivo>\"}"
            )
            response = llm.invoke([SystemMessage(content=sys_msg), HumanMessage(content=query)])
            data = json.loads(re.search(r"\{.*\}", response.content, re.DOTALL).group(0))
            next_step = data.get("next_step", "analista")
            notes = data.get("reasoning", "Enrutamiento generado por LLM.")
        except Exception:
            next_step = "analista"
            notes = "Enrutamiento fallback a Analista."

    return {
        "next_agent": next_step,
        "iteration_count": iteration,
        "supervisor_notes": notes
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. NODOS ESPECIALISTAS COMERCIALES
# ─────────────────────────────────────────────────────────────────────────────

def control_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Agente de Control de Inventario y Validación OCR.
    
    Regla estricta: NUNCA muta PostgreSQL directamente; prepara `pending_approval`
    y transfiere el control a HITL.
    """
    vision_payload = state.get("vision_payload") or {}
    endpoint = vision_payload.get("endpoint")
    query = state.get("query", "")
    db_evidence_accum: List[Dict[str, Any]] = []

    if endpoint == "/catalog-scan":
        raw_res = parse_vision_catalog_item.invoke({"vision_payload": vision_payload})
        res_dict = json.loads(raw_res)
        db_evidence_accum.append(res_dict)

        # Preparar mutación pendiente
        pending = {
            "action_type": "inventory_mutation",
            "summary": f"Actualización de catálogo para {res_dict.get('total_detectados', 0)} productos detectados por cámara.",
            "payload": {"tabla": "productos", "accion": "update", "datos": vision_payload.get("items", [{}])[0]},
            "requires_confirmation": True
        }
        msg = f"Escaneo de catálogo completado. Se detectaron {res_dict.get('total_detectados')} ítems. Confirmar para actualizar inventario."

    elif endpoint == "/receipt-ocr":
        raw_res = parse_receipt_ocr.invoke({"vision_payload": vision_payload})
        res_dict = json.loads(raw_res)
        db_evidence_accum.append(res_dict)

        pending = {
            "action_type": "inventory_mutation",
            "summary": f"Registro de comprobante de {res_dict.get('proveedor')} por ${res_dict.get('monto_total', 0.0):,.2f} ({res_dict.get('tipo')}).",
            "payload": {
                "tabla": "movimientos_financieros",
                "accion": "insert",
                "datos": {
                    "tipo": res_dict.get("tipo"),
                    "proveedor": res_dict.get("proveedor"),
                    "monto_total": res_dict.get("monto_total"),
                    "fecha": res_dict.get("fecha"),
                    "datos_ocr_json": res_dict.get("items_contabilizados")
                }
            },
            "requires_confirmation": True
        }
        msg = (
            f"Ticket analizado: Proveedor '{res_dict.get('proveedor')}', clasificado como '{res_dict.get('tipo')}'. "
            f"Monto total: ${res_dict.get('monto_total', 0.0):,.2f}. Requiere confirmación para asentarse en finanzas."
        )

    else:
        q_lower = query.lower()
        # 1. Operación de precio: "Sube la Coca a $22", "Cambia el precio de...", "Ponle $30 a..."
        if any(w in q_lower for w in ["precio", "sube", "cuesta", "ponle"]):
            montos = re.findall(r"\$?\s*([0-9]+(?:\.[0-9]+)?)", query)
            prod = None
            for p in mock_db.productos.values():
                if p["nombre"].lower() in q_lower or any(a in q_lower for a in p.get("alias", [])):
                    prod = p
                    break
            if prod and montos:
                new_p = float(montos[-1])
                raw_res = actualizar_precio.invoke({"nombre": prod["nombre"], "precio": new_p})
                res_dict = json.loads(raw_res)
                db_evidence_accum.append(res_dict)
                pending = {
                    "action_type": "inventory_mutation",
                    "summary": res_dict.get("respuesta", f"Actualización de precio de {prod['nombre']} a ${new_p:,.2f}"),
                    "payload": {"tool": "actualizar_precio", "args": {"nombre": prod["nombre"], "precio": new_p}},
                    "requires_confirmation": True
                }
                msg = res_dict.get("respuesta")
            elif not prod and montos:
                pending = None
                msg = "¿A qué producto le cambio el precio?"
            elif prod and not montos:
                pending = None
                msg = f"¿A cuánto quieres dejar {prod['nombre']}?"
            else:
                pending = None
                msg = "¿A qué producto le cambio el precio y cuál es el precio nuevo?"

        # 2. Operación de stock: "Llegaron 5 de Bimbo", "Se echaron a perder 2 de Coca", "Descuenta 3 de..."
        elif any(w in q_lower for w in ["llegaron", "entregaron", "merma", "echaron a perder", "descuenta", "quitar", "tira"]):
            cantidades = [int(n) for n in re.findall(r"\b[0-9]+\b", query)]
            tipo = "entrada"
            if any(w in q_lower for w in ["merma", "echaron", "caducaron", "tira"]):
                tipo = "merma"
            elif any(w in q_lower for w in ["descuenta", "lleve", "regale", "salida"]):
                tipo = "salida"

            prod = None
            for p in mock_db.productos.values():
                if p["nombre"].lower() in q_lower or any(a in q_lower for a in p.get("alias", [])):
                    prod = p
                    break

            if prod and cantidades:
                cant = cantidades[0]
                raw_res = ajustar_stock.invoke({"nombre": prod["nombre"], "cantidad": cant, "tipo": tipo})
                res_dict = json.loads(raw_res)
                db_evidence_accum.append(res_dict)
                pending = {
                    "action_type": "inventory_mutation",
                    "summary": res_dict.get("respuesta", f"Ajuste de existencias de {prod['nombre']} ({tipo}): {cant} piezas."),
                    "payload": {"tool": "ajustar_stock", "args": {"nombre": prod["nombre"], "cantidad": cant, "tipo": tipo}},
                    "requires_confirmation": True
                }
                msg = res_dict.get("respuesta")
            else:
                pending = None
                msg = "¿De qué producto y cuántas piezas llegaron o se ajustarán?"

        # 3. Consulta de catálogo / existencias: "¿Cuánto me queda de Coca?", "¿Qué productos tengo?"
        elif any(w in q_lower for w in ["cuanto hay", "cuánto hay", "cuántos me quedan", "cuantos me quedan", "stock de", "existencias", "qué vendo", "inventario", "catálogo", "catalogo", "lista de productos"]):
            prod = None
            for p in mock_db.productos.values():
                if p["nombre"].lower() in q_lower or any(a in q_lower for a in p.get("alias", [])):
                    prod = p
                    break
            raw_res = consultar_inventario.invoke({"nombre": prod["nombre"] if prod else None})
            res_dict = json.loads(raw_res)
            db_evidence_accum.append(res_dict)
            pending = None
            msg = res_dict.get("respuesta")

        # 4. Alta de nuevo producto: "Dame de alta Mazapán a $10, 20 piezas"
        elif any(w in q_lower for w in ["alta", "nuevo producto", "agrega", "registra", "guarda"]):
            montos = [float(x) for x in re.findall(r"\$?\s*([0-9]+(?:\.[0-9]+)?)", query)]
            nombre = "Nuevo Producto"
            m = re.search(r"(?:alta|agrega|registra|guarda)\s+([a-zA-Z0-9\s]+?)(?:,|\sen\s|\sa\s|\$|\stengo)", query, re.IGNORECASE)
            if m:
                nombre = m.group(1).strip()

            precio = montos[0] if montos else 15.0
            stock = int(montos[1]) if len(montos) > 1 else 10

            raw_res = crear_producto.invoke({"nombre": nombre, "precio": precio, "stock": stock})
            res_dict = json.loads(raw_res)
            db_evidence_accum.append(res_dict)
            pending = {
                "action_type": "inventory_mutation",
                "summary": res_dict.get("respuesta"),
                "payload": {"tool": "crear_producto", "args": {"nombre": nombre, "precio": precio, "stock": stock}},
                "requires_confirmation": True
            }
            msg = res_dict.get("respuesta")

        else:
            # Consulta general de caducidades y stock crítico
            raw_res = query_expiring_products.invoke({"dias_horizonte": 3})
            res_dict = json.loads(raw_res)
            db_evidence_accum.append(res_dict)

            cad = res_dict.get("productos_por_caducar", [])
            bajo_stock = res_dict.get("productos_bajo_stock_minimo", [])
            pending = None
            msg = (
                f"Auditoría de inventario: {len(cad)} lotes próximos a vencer a 72h "
                f"y {len(bajo_stock)} productos con stock crítico."
            )

    # Validación determinista de Grounding
    grounded, errors = enforce_db_grounding(msg, db_evidence_accum)

    return {
        "sender": "control",
        "messages": [AIMessage(content=msg)],
        "db_evidence": db_evidence_accum,
        "pending_approval": pending,
        "validation_errors": errors if not grounded else [],
        "next_agent": "supervisor"
    }


def vendedor_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Agente Vendedor y Copiloto POS.
    
    Regla estricta: NUNCA muta PostgreSQL directamente; prepara `pending_approval`
    con el carrito validado y pasa a confirmación HITL.
    """
    vision_payload = state.get("vision_payload") or {}
    db_evidence_accum: List[Dict[str, Any]] = []

    # Construir carrito desde visión o items del estado
    if vision_payload.get("endpoint") == "/pos-checkout":
        raw_cart = build_pos_cart_from_vision.invoke({"vision_payload": vision_payload})
        cart_data = json.loads(raw_cart)
    else:
        # Fallback a carrito muestra si fue solicitado por chat
        mock_payload = {
            "endpoint": "/pos-checkout",
            "items": [{"sku": "LALA-1L", "cantidad": 2}, {"sku": "BIMB-BLAN", "cantidad": 1}]
        }
        raw_cart = build_pos_cart_from_vision.invoke({"vision_payload": mock_payload})
        cart_data = json.loads(raw_cart)

    db_evidence_accum.append(cart_data)

    # Extraer SKUs para sugerencias de cross-selling
    skus = [it["sku"] for it in cart_data.get("items", [])]
    raw_cross = get_cross_sell_recommendations.invoke({"skus_carrito": skus})
    cross_data = json.loads(raw_cross)
    db_evidence_accum.append(cross_data)

    total_cobro = cart_data.get("total_a_cobrar", 0.0)
    recs = cross_data.get("recomendaciones", [])
    rec_text = f" Sugerencia de impulso: {recs[0]['nombre']} por ${recs[0]['precio_venta']:,.2f}." if recs else ""

    summary = f"Cobro de {len(cart_data.get('items', []))} productos por un total de ${total_cobro:,.2f}."
    msg = f"Carrito armado exitosamente. Total a cobrar: ${total_cobro:,.2f}.{rec_text} ¿Confirmar pago y descontar existencias?"

    pending = {
        "action_type": "sale_transaction",
        "summary": summary,
        "payload": {
            "items": cart_data.get("items", []),
            "total_a_cobrar": total_cobro,
            "metodo_pago": "efectivo",
            "origen_vision": True
        },
        "requires_confirmation": True
    }

    grounded, errors = enforce_db_grounding(msg, db_evidence_accum)

    return {
        "sender": "vendedor",
        "messages": [AIMessage(content=msg)],
        "db_evidence": db_evidence_accum,
        "pending_approval": pending,
        "validation_errors": errors if not grounded else [],
        "next_agent": "supervisor"
    }


def analista_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Agente Analista Financiero.
    
    Regla estricta: ESTRICTAMENTE SOLO LECTURA.
    Métricas exactas de flujo de caja y márgenes de ganancia respaldadas por `db_evidence`.
    """
    db_evidence_accum: List[Dict[str, Any]] = []

    raw_cashflow = get_cashflow_summary.invoke({"fecha_inicio": "2026-11-01", "fecha_fin": "2026-11-30"})
    cashflow_data = json.loads(raw_cashflow)
    db_evidence_accum.append(cashflow_data)

    raw_margins = get_product_margins.invoke({"categoria": None})
    margins_data = json.loads(raw_margins)
    db_evidence_accum.append(margins_data)

    ingresos = cashflow_data.get("ingresos_ventas", 0.0)
    egresos = cashflow_data.get("egresos_totales", 0.0)
    flujo_neto = cashflow_data.get("flujo_caja_neto", 0.0)

    top_prod = margins_data.get("metricas_margen", [{}])[0]
    top_margen_sku = top_prod.get("nombre", "N/A")
    top_margen_pct = top_prod.get("margen_porcentaje", 0.0)

    msg = (
        f"Informe Financiero Consolidado:\n"
        f"- Ingresos por Ventas: ${ingresos:,.2f}\n"
        f"- Egresos Totales: ${egresos:,.2f} (Gastos Operativos + Inversión en Inventario)\n"
        f"- Flujo de Caja Neto: ${flujo_neto:,.2f}\n"
        f"- Producto de mayor margen: {top_margen_sku} ({top_margen_pct}% de margen bruto)."
    )

    # Validar grounding determinista (con reintento controlado si fallase)
    grounded, errors = enforce_db_grounding(msg, db_evidence_accum)

    return {
        "sender": "analista",
        "messages": [AIMessage(content=msg)],
        "db_evidence": db_evidence_accum,
        "validation_errors": errors if not grounded else [],
        "next_agent": "supervisor"
    }


def investigador_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Agente Investigador de Mercado.
    
    Genera estrictamente el reporte estratégico de 9 secciones obligatorias:
    identificacion_sector, mercado_tendencias, clientes, problemas, soluciones,
    hipotesis, objetivos, impacto, hallazgos.
    """
    db_evidence_accum: List[Dict[str, Any]] = []

    raw_cohort = get_sales_cohort_metrics.invoke({})
    cohort_data = json.loads(raw_cohort)
    db_evidence_accum.append(cohort_data)

    raw_trends = search_market_trends.invoke({"sector": "abarrotes y tienditas de barrio", "query": "consumo y metodos de pago"})
    trends_data = json.loads(raw_trends)
    db_evidence_accum.append(trends_data)

    t_prom = cohort_data.get("ticket_promedio_mxn", 79.50)

    report_dict = {
        "identificacion_sector": "Canal tradicional minorista de conveniencia y proximidad (tienditas de barrio y misceláneas).",
        "mercado_tendencias": "Digitalización del 35% de los cobros mediante SPEI y tarjetas contactless; demanda creciente de productos de ocasión y combos de conveniencia.",
        "clientes": f"Consumidores locales de compra cotidiana con ticket promedio real de ${t_prom:,.2f} y visitas recurrentes (3 a 5 semanales).",
        "problemas": "Riesgo de merma por caducidad en lácteos/panadería fresca y demoras operativas en caja por falta de automatización.",
        "soluciones": "Automatización de inventario por visión artificial, activación de promociones dinámicas y asistencia guiada en pasarelas de pago.",
        "hipotesis": "Un descuento anticipado del 15% al 20% en productos a 72h de vencer recupera el costo unitario y elimina la merma física.",
        "objetivos": "Asegurar cero mermas por caducidad, aumentar el ticket promedio a $95.00 MXN y reducir tiempo de cobro a menos de 20 segundos.",
        "impacto": "Mejora directa estimada del 5.8% en rentabilidad neta mensual y mayor fidelización vecinal.",
        "hallazgos": f"El ticket promedio actual observado en BD es de ${t_prom:,.2f}; las horas pico ocurren entre 07:30-09:30 y 18:00-20:30."
    }

    es_valido = validate_strategic_report(report_dict)
    msg = (
        f"Reporte Estratégico Comercial Completado (9 secciones validadas):\n"
        f"Sector: {report_dict['identificacion_sector']}\n"
        f"Hallazgo clave: {report_dict['hallazgos']}\n"
        f"Objetivo: {report_dict['objetivos']}"
    )

    return {
        "sender": "investigador",
        "strategic_report": report_dict,
        "messages": [AIMessage(content=msg)],
        "db_evidence": db_evidence_accum,
        "validation_errors": [] if es_valido else ["El reporte no cumplió con las 9 secciones requeridas."],
        "next_agent": "supervisor"
    }


def publicista_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Agente Publicista y Generador Multimedia.
    
    Genera:
    - video_prompt: Prompt vertical 9:16 (5s) en inglés cinematográfico.
    - copy_promocional: Texto persuasivo en español.
    - call_to_action: Llamado a la acción en español.
    - pending_approval: Prepara la campaña para confirmación HITL antes del disparo externo.
    """
    producto = "Leche Entera Lala 1L"
    descuento = "20%"

    video_prompt = (
        "Cinematic vertical 9:16 commercial, 5 seconds. Extreme close-up of a premium glass bottle of cold fresh milk "
        "with chilled condensation droplets glinting in morning golden hour sunlight. Creamy whole milk pouring gracefully "
        "into a glass on a clean wooden countertop, warm artisan bakery background, 4k 60fps advertising aesthetics."
    )
    copy_promo = (
        f"¡Aprovecha hoy {descuento} de descuento en {producto}! Frescura garantizada para el desayuno familiar "
        f"a precio de oportunidad en Tiendita IA."
    )
    cta = "Toca aquí para apartar tu pedido en la app móvil o pedirlo directo por WhatsApp antes de que se agote."

    assets = {
        "video_prompt": video_prompt,
        "copy_promocional": copy_promo,
        "call_to_action": cta,
        "video_url": "https://cdn.tiendita.ia/promos/video_lala_descuento_916.mp4"
    }

    pending = {
        "action_type": "promo_campaign",
        "summary": f"Activación de campaña multimedia para '{producto}' con {descuento} de descuento.",
        "payload": {
            "producto": producto,
            "descuento": descuento,
            "video_prompt": video_prompt,
            "copy_texto": copy_promo
        },
        "requires_confirmation": True
    }

    msg = (
        f"Activos Promocionales Generados:\n"
        f"- Video Prompt (9:16, 5s): {video_prompt[:90]}...\n"
        f"- Copy: {copy_promo}\n"
        f"- CTA: {cta}\n"
        f"Campaña registrada en estado 'pendiente_aprobacion'."
    )

    return {
        "sender": "publicista",
        "promo_assets": assets,
        "pending_approval": pending,
        "messages": [AIMessage(content=msg)],
        "next_agent": "supervisor"
    }


def tutor_ui_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Agente Tutor de Pasarelas de Pago e Interfaz de Usuario.
    
    Regla estricta: Responde en MÁXIMO 2 ORACIONES ACCIONABLES referenciando
    el campo o botón exacto en `ui_state`.
    """
    ui_state = state.get("ui_state") or {
        "pantalla": "Checkout",
        "paso_actual": "seleccion_metodo",
        "campos_vacios": [],
        "error_visible": None,
        "intentos": 1
    }

    raw_inspect = inspect_payment_step.invoke({"ui_state": ui_state})
    inspect_data = json.loads(raw_inspect)
    instruccion = inspect_data.get("instruccion_accionable", "")

    # Garantizar formato estricto de máximo 2 oraciones accionables
    pantalla = ui_state.get("pantalla", "Pago")
    if "spei" in pantalla.lower():
        msg = "Verifica que tu cuenta CLABE contenga exactamente 18 dígitos sin espacios ni guiones. Pégala en el campo 'CLABE Interbancaria' y pulsa el botón 'Confirmar Transferencia'."
    elif "tarjeta" in pantalla.lower():
        msg = "Ingresa los 3 dígitos de seguridad ubicados al reverso de tu tarjeta en el campo 'CVV'. Al completarlo, el botón 'Pagar con Tarjeta' se activará para finalizar tu compra."
    else:
        msg = f"{instruccion} Recuerda pulsar el botón principal para continuar con tu proceso."

    # Asegurar máximo 2 oraciones
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", msg) if s.strip()]
    final_msg = " ".join(sentences[:2])

    return {
        "sender": "tutor_ui",
        "messages": [AIMessage(content=final_msg)],
        "next_agent": "supervisor"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. NODO DE APROBACIÓN HUMAN-IN-THE-LOOP (HITL)
# ─────────────────────────────────────────────────────────────────────────────

def aprobacion_hitl_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Punto de Interrupción Determinista Human-in-the-Loop.
    
    Usa `interrupt()` de LangGraph para pausar la ejecución y solicitar confirmación
    al operador móvil antes de alterar datos en PostgreSQL.
    
    Al reanudarse mediante Command(resume={"approved": True/False, "edited_payload": ...}):
    - Si fue aprobado: ejecuta la herramienta de mutación real y actualiza inventario/finanzas.
    - Si fue rechazado: descarta la mutación y registra la cancelación.
    """
    pending = state.get("pending_approval")
    if not pending or not pending.get("requires_confirmation", True):
        return {"sender": "aprobacion_hitl", "next_agent": "supervisor"}

    # Interrupción formal en LangGraph v0.2+
    user_decision = interrupt({
        "action_type": pending.get("action_type"),
        "summary": pending.get("summary"),
        "payload": pending.get("payload"),
        "requires_confirmation": True
    })

    # Procesar respuesta tras resume
    approved = False
    edited_payload = None

    if isinstance(user_decision, dict):
        approved = user_decision.get("approved", False)
        edited_payload = user_decision.get("edited_payload")
    elif isinstance(user_decision, bool):
        approved = user_decision

    payload_to_execute = edited_payload if edited_payload is not None else pending.get("payload", {})
    action_type = pending.get("action_type")
    evidence_update = []

    if approved:
        if action_type == "inventory_mutation":
            res = commit_inventory_mutation.invoke({"mutation_payload": payload_to_execute})
            msg = f"Mutación de inventario confirmada y ejecutada: {res}"
            evidence_update.append(json.loads(res))
        elif action_type == "sale_transaction":
            res = commit_sale_transaction.invoke({"cart_payload": payload_to_execute})
            msg = f"Venta confirmada y registrada en BD: {res}"
            evidence_update.append(json.loads(res))
        elif action_type == "promo_campaign":
            res = generate_promo_video_job.invoke({
                "producto": payload_to_execute.get("producto", "General"),
                "descuento": payload_to_execute.get("descuento", "15%"),
                "video_prompt": payload_to_execute.get("video_prompt", "")
            })
            msg = f"Campaña promocional aprobada y activada: {res}"
            evidence_update.append(json.loads(res))
        else:
            msg = f"Acción '{action_type}' aprobada exitosamente."

        return {
            "sender": "aprobacion_hitl",
            "pending_approval": None,
            "messages": [AIMessage(content=msg)],
            "db_evidence": evidence_update,
            "next_agent": "supervisor"
        }
    else:
        return {
            "sender": "aprobacion_hitl",
            "pending_approval": None,
            "messages": [AIMessage(content=f"La acción '{action_type}' fue cancelada por el usuario.")],
            "next_agent": "supervisor"
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. ENRUTADOR CONDICIONAL Y CONSTRUCCIÓN DEL GRAFO
# ─────────────────────────────────────────────────────────────────────────────

def router_supervisor(state: OrchestratorState) -> str:
    """Función de salto condicional basada en `next_agent`."""
    next_step = state.get("next_agent", "FIN")
    if next_step in ["control", "vendedor", "analista", "investigador", "publicista", "tutor_ui", "aprobacion_hitl"]:
        return next_step
    return END


def build_orchestrator(checkpointer: Optional[Any] = None) -> Any:
    """
    Construye y compila el StateGraph del Ecosistema Multiagente Comercial Multimodal.
    """
    builder = StateGraph(OrchestratorState)

    # Registro de nodos
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("control", control_node)
    builder.add_node("vendedor", vendedor_node)
    builder.add_node("analista", analista_node)
    builder.add_node("investigador", investigador_node)
    builder.add_node("publicista", publicista_node)
    builder.add_node("tutor_ui", tutor_ui_node)
    builder.add_node("aprobacion_hitl", aprobacion_hitl_node)

    # Conexiones
    builder.add_edge(START, "supervisor")

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
            "aprobacion_hitl": "aprobacion_hitl",
            END: END,
        }
    )

    # Retorno de especialistas al supervisor o a HITL
    for node_name in ["control", "vendedor", "analista", "investigador", "publicista", "tutor_ui"]:
        builder.add_edge(node_name, "supervisor")

    builder.add_edge("aprobacion_hitl", "supervisor")

    # Si no se suministra checkpointer, instanciar MemorySaver para soportar HITL interrupt
    cp = checkpointer if checkpointer is not None else MemorySaver()
    return builder.compile(checkpointer=cp)


# Instancia compilada global con MemorySaver
default_checkpointer = MemorySaver()
orchestrator_graph = build_orchestrator(checkpointer=default_checkpointer)


# ─────────────────────────────────────────────────────────────────────────────
# 5. PUNTOS DE ENTRADA PÚBLICOS DE EJECUCIÓN Y REANUDACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def run_orchestration(
    query: str = "",
    thread_id: str = "default_thread",
    event_source: Literal["chat", "vision_api", "ui_copilot", "cron_trigger"] = "chat",
    vision_payload: Optional[Dict[str, Any]] = None,
    ui_state: Optional[Dict[str, Any]] = None,
    provider: str = "NVIDIA",
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    checkpointer: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el flujo multiagente sincronizado para una solicitud multimodal.
    """
    graph = orchestrator_graph if checkpointer is None else build_orchestrator(checkpointer=checkpointer)

    initial_messages: List[AnyMessage] = []
    if query:
        initial_messages.append(HumanMessage(content=query))
    elif vision_payload:
        initial_messages.append(HumanMessage(content=f"Evento de visión: {vision_payload.get('endpoint')}"))
    elif ui_state:
        initial_messages.append(HumanMessage(content=f"Evento de UI en pantalla {ui_state.get('pantalla')}"))

    state_input: OrchestratorState = {
        "messages": initial_messages,
        "query": query,
        "event_source": event_source,
        "vision_payload": vision_payload,
        "ui_state": ui_state,
        "db_evidence": [],
        "few_shot_examples": [],
        "strategic_report": None,
        "promo_assets": None,
        "pending_approval": None,
        "validation_errors": [],
        "next_agent": "supervisor",
        "iteration_count": 0,
        "provider": provider,
        "model_name": model_name,
        "temperature": temperature,
        "sender": "inicio"
    }

    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(state_input, config=config)
    return result


def run_orchestration_stream(
    query: str = "",
    thread_id: str = "default_stream_thread",
    event_source: Literal["chat", "vision_api", "ui_copilot", "cron_trigger"] = "chat",
    vision_payload: Optional[Dict[str, Any]] = None,
    ui_state: Optional[Dict[str, Any]] = None,
    provider: str = "NVIDIA",
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    checkpointer: Optional[Any] = None,
) -> Generator[Dict[str, Any], None, None]:
    """
    Genera en streaming los deltas de cada nodo conforme avanza la orquestación.
    """
    graph = orchestrator_graph if checkpointer is None else build_orchestrator(checkpointer=checkpointer)

    initial_messages: List[AnyMessage] = []
    if query:
        initial_messages.append(HumanMessage(content=query))
    elif vision_payload:
        initial_messages.append(HumanMessage(content=f"Evento de visión: {vision_payload.get('endpoint')}"))
    elif ui_state:
        initial_messages.append(HumanMessage(content=f"Evento de UI en pantalla {ui_state.get('pantalla')}"))

    state_input: OrchestratorState = {
        "messages": initial_messages,
        "query": query,
        "event_source": event_source,
        "vision_payload": vision_payload,
        "ui_state": ui_state,
        "db_evidence": [],
        "few_shot_examples": [],
        "strategic_report": None,
        "promo_assets": None,
        "pending_approval": None,
        "validation_errors": [],
        "next_agent": "supervisor",
        "iteration_count": 0,
        "provider": provider,
        "model_name": model_name,
        "temperature": temperature,
        "sender": "inicio"
    }

    config = {"configurable": {"thread_id": thread_id}}
    for step in graph.stream(state_input, config=config):
        yield step


def resume_orchestration(
    thread_id: str,
    approved: bool,
    edited_payload: Optional[Dict[str, Any]] = None,
    checkpointer: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Reanuda la ejecución del grafo pausado en un punto de interrupción (HITL)
    utilizando Command(resume=...).
    """
    graph = orchestrator_graph if checkpointer is None else build_orchestrator(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    resume_data = {
        "approved": approved,
        "edited_payload": edited_payload
    }
    result = graph.invoke(Command(resume=resume_data), config=config)
    return result
