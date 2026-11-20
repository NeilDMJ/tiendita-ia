"""
Herramientas analíticas, financieras e investigativas para Tiendita IA.
Incluye:
  - Búsqueda web con Tavily
  - Scraping limpio con HTTPX + BeautifulSoup
  - Búsqueda e indexación vectorial de reportes estratégicos pasados
  - Métricas de flujo de caja, márgenes y rotación por SKU (Solo Lectura)
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
import httpx
from bs4 import BeautifulSoup

from config.keys import TAVILY_API_KEY, TAVILY_MAX_RESULTS
from tools.db_client import _MOCK_INVENTORY, _MOCK_SALES, _get_connection, _serializar_dato
from schemas.reports import StrategicReport


# ==============================================================================
# Herramientas de Investigación Web y Memoria Histórica (Agente Investigador)
# ==============================================================================

@tool
def search_web_tavily(query: str, max_results: int = 5) -> str:
    """
    Realiza una búsqueda web en tiempo real de tendencias comerciales, precios de mercado,
    competencia y proveedores utilizando la API de Tavily.
    """
    if not TAVILY_API_KEY or TAVILY_API_KEY.startswith("tu_"):
        # Fallback estructurado de contingencia para pruebas offline
        return json.dumps({
            "status": "mock_results",
            "query": query,
            "results": [
                {
                    "title": "Tendencias del comercio minorista y abarrotes en México 2026",
                    "url": "https://comercio-mexico.org/tendencias-abarrotes-2026",
                    "content": "El ticket promedio en tiendas de barrio creció un 14% impulsado por pagos digitales con CoDi y tarjetas. Los perecederos y lácteos frescos representan el 38% del margen bruto de la tienda."
                },
                {
                    "title": "Estrategias de fidelización y reducción de mermas en tiendas locales",
                    "url": "https://retail-estrategico.mx/reduccion-mermas-tienditas",
                    "content": "La aplicación de remates programados 48 horas antes de la caducidad reduce las pérdidas por desecho en más de un 40% y aumenta la rotación de inventarios estancados."
                }
            ]
        }, ensure_ascii=False)

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        k = max_results or TAVILY_MAX_RESULTS
        response = client.search(query=query, max_results=k, search_depth="basic")
        resultados = []
        for r in response.get("results", []):
            resultados.append({
                "title": r.get("title"),
                "url": r.get("url"),
                "content": r.get("content")
            })
        return json.dumps({"status": "success", "query": query, "results": resultados}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Fallo al consultar Tavily: {str(e)}"}, ensure_ascii=False)


@tool
def scrape_webpage_clean(url: str) -> str:
    """
    Descarga y extrae el contenido textual limpio de una página web o artículo comercial
    eliminando etiquetas irrelevantes (scripts, estilos, navegación y anuncios).
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return f"Error HTTP {resp.status_code} al acceder a la URL: {url}"

            soup = BeautifulSoup(resp.text, "lxml")
            for elemento in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "aside"]):
                elemento.decompose()

            texto = soup.get_text(separator="\n", strip=True)
            # Limpiar líneas vacías excesivas
            lineas = [l for l in texto.split("\n") if len(l.strip()) > 30]
            texto_limpio = "\n".join(lineas[:40])  # Retener los primeros párrafos informativos
            return texto_limpio[:3000] if texto_limpio else "No se pudo extraer texto relevante de la página."
    except Exception as e:
        return f"Error extrayendo contenido de {url}: {str(e)}"


@tool
def search_past_reports(query: str) -> str:
    """
    Consulta en la memoria vectorial (RAG Dual / FAISS) los reportes estratégicos previos
    generados para el negocio antes de realizar una nueva investigación desde cero.
    """
    from tools.rag_nemo import buscar_reportes_vectoriales
    docs = buscar_reportes_vectoriales(query, top_k=3)
    if not docs:
        return "No hay reportes estratégicos previos almacenados que coincidan con la consulta."

    salida = []
    for d in docs:
        ts = d.metadata.get("timestamp", "Fecha no especificada")
        salida.append(f"--- REPORTE PREVIO ({ts}) ---\n{d.page_content}")
    return "\n\n".join(salida)


@tool
def save_and_index_report(
    identificacion_sector: str,
    mercado_tendencias: str,
    clientes: str,
    problemas: str,
    soluciones: str,
    hipotesis: str,
    objetivos: str,
    impacto: str,
    hallazgos: str
) -> str:
    """
    Persiste un reporte estratégico completo de 9 secciones en formato JSON y Markdown en disco
    y lo indexa en la base de datos vectorial para consultas futuras.
    """
    from tools.rag_nemo import index_strategic_report
    report_dict = {
        "identificacion_sector": identificacion_sector,
        "mercado_tendencias": mercado_tendencias,
        "clientes": clientes,
        "problemas": problemas,
        "soluciones": soluciones,
        "hipotesis": hipotesis,
        "objetivos": objetivos,
        "impacto": impacto,
        "hallazgos": hallazgos,
    }
    return index_strategic_report(report_dict)


# ==============================================================================
# Herramientas Financieras y Operativas (Solo Lectura - Analista)
# ==============================================================================

@tool
def get_cash_flow(date_from: Optional[str] = None, date_to: Optional[str] = None) -> str:
    """
    Calcula el flujo de caja neto del negocio consultando v_flujo_caja en PostgreSQL.
    Incluye ingresos por ventas, gastos operativos e inversión en inventario por periodo.

    Args:
        date_from: Fecha inicio en formato YYYY-MM-DD (opcional).
        date_to: Fecha fin en formato YYYY-MM-DD (opcional; default: hoy).
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT dia, ingresos, gasto_operativo, inversion, neto
                      FROM v_flujo_caja
                """
                params = []
                if date_from:
                    query += " WHERE dia >= %s"
                    params.append(date_from)
                if date_to:
                    query += (" AND" if date_from else " WHERE") + " dia <= %s"
                    params.append(date_to)
                query += " ORDER BY dia DESC LIMIT 30"

                cur.execute(query, tuple(params))
                filas = cur.fetchall()

                dias = [
                    {
                        "dia": _serializar_dato(r[0]),
                        "ingresos": float(r[1] or 0),
                        "gasto_operativo": float(r[2] or 0),
                        "inversion": float(r[3] or 0),
                        "neto": float(r[4] or 0),
                    }
                    for r in filas
                ]
                total_ingresos = sum(d["ingresos"] for d in dias)
                total_gasto = sum(d["gasto_operativo"] for d in dias)
                total_inversion = sum(d["inversion"] for d in dias)
                flujo_neto = sum(d["neto"] for d in dias)

        return json.dumps({
            "status": "success",
            "fuente": "postgresql",
            "periodo": f"{date_from or 'inicio'} a {date_to or 'hoy'}",
            "ingresos_totales": round(total_ingresos, 2),
            "gastos_operativos": round(total_gasto, 2),
            "inversion_inventario": round(total_inversion, 2),
            "egresos_totales": round(total_gasto + total_inversion, 2),
            "flujo_caja_neto": round(flujo_neto, 2),
            "detalle_diario": dias,
        }, ensure_ascii=False)

    except Exception as e:
        # Fallback con _MOCK_SALES
        ingresos = sum(v["total"] for v in _MOCK_SALES)
        return json.dumps({
            "status": "success",
            "fuente": "fallback_memoria",
            "nota": str(e),
            "periodo": f"{date_from or 'inicio'} a {date_to or 'hoy'}",
            "ingresos_totales": ingresos,
            "gastos_operativos": 280.00,
            "inversion_inventario": 1450.00,
            "egresos_totales": 1730.00,
            "flujo_caja_neto": round(ingresos - 1730.00, 2),
        }, ensure_ascii=False)


@tool
def get_margins_by_sku(sku: Optional[str] = None) -> str:
    """
    Analiza el margen de ganancia bruto por producto consultando v_margen_producto en PostgreSQL.
    Uso exclusivo para auditoría interna; no exponer costo_unitario en mostrador.

    Args:
        sku: SKU específico para filtrar (opcional; si se omite, devuelve todos).
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT sku, nombre, categoria, unidades, ingresos, margen, margen_pct
                      FROM v_margen_producto
                """
                params = []
                if sku:
                    query += " WHERE sku = %s"
                    params.append(sku.strip().upper())
                query += " ORDER BY margen_pct DESC NULLS LAST LIMIT 25"
                cur.execute(query, tuple(params))
                filas = cur.fetchall()
                margenes = [
                    {
                        "sku": r[0],
                        "nombre": r[1],
                        "categoria": r[2],
                        "unidades_vendidas": float(r[3] or 0),
                        "ingresos": float(r[4] or 0),
                        "margen_bruto": float(r[5] or 0),
                        "margen_porcentaje": float(r[6] or 0),
                    }
                    for r in filas
                ]
        return json.dumps({"status": "success", "fuente": "postgresql", "margenes": margenes}, ensure_ascii=False)

    except Exception as e:
        # Fallback en memoria
        items = _MOCK_INVENTORY if not sku else [p for p in _MOCK_INVENTORY if p["sku"] == sku.strip().upper()]
        margenes = []
        for it in items:
            precio = it.get("precio_venta", 0)
            costo = it.get("costo_unitario", 0)
            ganancia = precio - costo
            margen_pct = round((ganancia / precio) * 100, 2) if precio > 0 else 0.0
            margenes.append({
                "sku": it["sku"], "nombre": it["nombre"],
                "precio_venta": precio, "costo_unitario": costo,
                "margen_bruto": round(ganancia, 2), "margen_porcentaje": margen_pct,
            })
        margenes.sort(key=lambda x: x["margen_porcentaje"], reverse=True)
        return json.dumps({
            "status": "success", "fuente": "fallback_memoria", "nota": str(e), "margenes": margenes
        }, ensure_ascii=False)


@tool
def get_rotation_by_sku(days: int = 30) -> str:
    """
    Evalúa la velocidad de rotación de productos consultando v_margen_producto y v_inventario.
    Identifica artículos estrella (alta rotación) vs. estancados (sin salida).

    Args:
        days: Número de días a analizar (referencial; la vista no filtra por periodo).
    """
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT m.sku, m.nombre, m.unidades, i.existencia,
                           CASE WHEN m.unidades >= 10 THEN 'alta'
                                WHEN m.unidades > 0 THEN 'media'
                                ELSE 'lenta' END AS rotacion
                      FROM v_margen_producto m
                      JOIN v_inventario i USING (sku)
                     ORDER BY m.unidades DESC NULLS LAST
                     LIMIT 25
                """)
                filas = cur.fetchall()
                rotacion = [
                    {
                        "sku": r[0], "nombre": r[1],
                        "unidades_vendidas": float(r[2] or 0),
                        "stock_actual": float(r[3] or 0),
                        "rotacion": r[4],
                    }
                    for r in filas
                ]
        return json.dumps({
            "status": "success", "fuente": "postgresql",
            "dias_analizados": days, "analisis_rotacion": rotacion,
        }, ensure_ascii=False)

    except Exception as e:
        # Fallback en memoria con _MOCK_SALES
        conteo: dict[str, float] = {}
        for v in _MOCK_SALES:
            for it in v.get("items", []):
                conteo[it["sku"]] = conteo.get(it["sku"], 0) + it.get("cantidad", 0)

        rotacion = []
        for prod in _MOCK_INVENTORY:
            s = prod["sku"]
            u = conteo.get(s, 0)
            rotacion.append({
                "sku": s, "nombre": prod["nombre"],
                "unidades_vendidas": u, "stock_actual": prod.get("stock_actual", 0),
                "rotacion": "alta" if u >= 3 else ("media" if u > 0 else "lenta"),
            })
        return json.dumps({
            "status": "success", "fuente": "fallback_memoria", "nota": str(e),
            "dias_analizados": days, "analisis_rotacion": rotacion,
        }, ensure_ascii=False)


@tool
def get_sales_summary(period: str = "week") -> str:
    """
    Entrega un resumen consolidado de ventas desde v_ventas_dia en PostgreSQL:
    total, ticket promedio, transacciones y top de horas pico.

    Args:
        period: 'day' (hoy), 'week' (últimos 7 días), 'month' (últimos 30 días).
    """
    limit_map = {"day": 1, "week": 7, "month": 30}
    limit = limit_map.get(period, 7)

    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT dia, ventas, ingresos, ticket_promedio
                      FROM v_ventas_dia
                     ORDER BY dia DESC
                     LIMIT %s
                """, (limit,))
                filas = cur.fetchall()
                dias = [
                    {
                        "dia": _serializar_dato(r[0]),
                        "transacciones": r[1],
                        "ingresos": float(r[2]),
                        "ticket_promedio": float(r[3]),
                    }
                    for r in filas
                ]
                total = sum(d["ingresos"] for d in dias)
                n = sum(d["transacciones"] for d in dias)
                ticket = round(total / n, 2) if n > 0 else 0.0

        return json.dumps({
            "status": "success",
            "fuente": "postgresql",
            "periodo": period,
            "total_ventas": round(total, 2),
            "transacciones": n,
            "ticket_promedio": ticket,
            "detalle_diario": dias,
        }, ensure_ascii=False)

    except Exception as e:
        total = sum(v["total"] for v in _MOCK_SALES)
        n = len(_MOCK_SALES)
        ticket = round(total / n, 2) if n > 0 else 0.0
        por_metodo: dict[str, float] = {}
        for v in _MOCK_SALES:
            m = v.get("metodo_pago", "efectivo")
            por_metodo[m] = por_metodo.get(m, 0.0) + v["total"]
        return json.dumps({
            "status": "success", "fuente": "fallback_memoria", "nota": str(e),
            "periodo": period, "total_ventas": total, "transacciones": n,
            "ticket_promedio": ticket, "ventas_por_metodo": por_metodo,
        }, ensure_ascii=False)
