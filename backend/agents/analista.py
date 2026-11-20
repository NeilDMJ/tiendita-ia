"""Agente Analista: ventas, márgenes, productos top/lentos y reportes (idea.md §2.4).
Cada sección del reporte indica su fuente: bd | externa | hipotesis."""
import json
import re

from .. import db
from . import control, investigador
from .base import Agente
from .registro import tool
from .util import PERIODOS, detectar_periodo, dinero, norm


def _periodo(args) -> str:
    p = args.get("periodo") or "hoy"
    if p not in PERIODOS:
        raise ValueError("periodo debe ser hoy, semana o mes")
    return p


@tool("analista", False, {"periodo": (str, type(None))})
def consultar_ventas(args, ctx):
    p = _periodo(args)
    cond = PERIODOS[p]
    with db.conn() as c:
        n, total = c.execute(f"SELECT COUNT(*), COALESCE(SUM(total),0) FROM ventas WHERE {cond}").fetchone()
        met = {r[0]: r[1] for r in c.execute(
            f"SELECT metodo_pago, SUM(total) FROM ventas WHERE {cond} GROUP BY metodo_pago")}
        pico = c.execute(f"SELECT strftime('%H', fecha, 'localtime') h, COUNT(*) n FROM ventas WHERE {cond} "
                         f"GROUP BY h ORDER BY n DESC LIMIT 1").fetchone()
    if not n:
        return {"ok": True, "periodo": p, "ventas": 0, "total": 0, "texto": f"Sin ventas registradas ({p}).",
                "fuentes": ["bd"]}
    ticket = total / n
    texto = (f"Ventas ({p}): {n} por {dinero(total)}. Ticket promedio {dinero(ticket)}. "
             + ", ".join(f"{k} {dinero(v)}" for k, v in met.items()) + "."
             + (f" Hora pico: {pico[0]}:00." if pico else ""))
    return {"ok": True, "periodo": p, "ventas": n, "total": total, "ticket_promedio": ticket,
            "por_metodo": met, "hora_pico": pico[0] if pico else None, "texto": texto, "fuentes": ["bd"]}


@tool("analista", False, {"periodo": (str, type(None))})
def calcular_margenes(args, ctx):
    p = _periodo(args)
    with db.conn() as c:
        rows = [dict(r) for r in c.execute(
            f"SELECT p.nombre, SUM(d.cantidad) cant, SUM(d.cantidad*d.precio) ingreso, "
            f"SUM(d.cantidad*(d.precio-p.costo)) utilidad FROM venta_detalle d "
            f"JOIN ventas v ON v.id=d.venta_id JOIN productos p ON p.id=d.producto_id "
            f"WHERE {PERIODOS[p]} AND p.costo IS NOT NULL GROUP BY p.id ORDER BY utilidad DESC")]
        sin_costo = [r[0] for r in c.execute("SELECT nombre FROM productos WHERE costo IS NULL")]
    for r in rows:
        r["margen_pct"] = round(100 * r["utilidad"] / r["ingreso"], 1) if r["ingreso"] else 0
    texto = ("\n".join(f"- {r['nombre']}: utilidad {dinero(r['utilidad'])} ({r['margen_pct']}%)" for r in rows)
             or "No hay ventas con costo registrado en el periodo.")
    if sin_costo:
        texto += f"\nSin costo capturado (no calculable): {', '.join(sin_costo)}."
    return {"ok": True, "periodo": p, "margenes": rows, "sin_costo": sin_costo, "texto": texto, "fuentes": ["bd"]}


@tool("analista", False, {"periodo": (str, type(None)), "limite": (int, type(None))})
def top_productos(args, ctx):
    p, lim = _periodo(args), args.get("limite") or 5
    with db.conn() as c:
        top = [dict(r) for r in c.execute(
            f"SELECT p.nombre, SUM(d.cantidad) cant FROM venta_detalle d JOIN ventas v ON v.id=d.venta_id "
            f"JOIN productos p ON p.id=d.producto_id WHERE {PERIODOS[p]} GROUP BY p.id "
            f"ORDER BY cant DESC LIMIT ?", (lim,))]
        lentos = [r[0] for r in c.execute(
            f"SELECT nombre FROM productos WHERE stock>0 AND id NOT IN (SELECT d.producto_id FROM venta_detalle d "
            f"JOIN ventas v ON v.id=d.venta_id WHERE {PERIODOS[p]}) ORDER BY nombre LIMIT ?", (lim,))]
    texto = "Más vendidos: " + (", ".join(f"{t['nombre']} ({t['cant']})" for t in top) or "ninguno") + "."
    if lentos:
        texto += " Sin movimiento: " + ", ".join(lentos) + "."
    return {"ok": True, "periodo": p, "top": top, "lentos": lentos, "texto": texto, "fuentes": ["bd"]}


@tool("analista", False, {"periodo": (str, type(None))})
def generar_reporte(args, ctx):
    """Arma el reporte delegando en Control (problemas) e Investigador (mercado) y lo guarda en `reportes`."""
    p = _periodo(args)
    ven = consultar_ventas({"periodo": p}, ctx)
    mar = calcular_margenes({"periodo": p}, ctx)
    top = top_productos({"periodo": p}, ctx)
    bajo = control.stock_bajo({}, ctx)
    cad = control.productos_por_caducar({}, ctx)
    mer = investigador.resumen_mercado({}, ctx)
    hipotesis, soluciones = [], []
    if bajo["productos"]:
        hipotesis.append("Los productos con poco stock pueden estar perdiendo ventas por quedarse sin existencias.")
        soluciones.append("Reabastecer: " + ", ".join(x["nombre"] for x in bajo["productos"]))
    if cad["productos"]:
        hipotesis.append("Hay mercancía que podría convertirse en merma si no rota antes de caducar.")
        soluciones.append("Pedir al Publicista una promoción para: " + ", ".join(x["nombre"] for x in cad["productos"]))
    if top["lentos"]:
        soluciones.append("Revisar precio o exhibición de productos sin movimiento: " + ", ".join(top["lentos"]))
    secciones = {
        "Identificación": {"contenido": f"Tiendita, periodo: {p}", "fuente": "bd"},
        "Sector": {"contenido": mer["texto"], "fuente": "externa"},
        "Tendencias": {"contenido": top["texto"] + " " + (f"Hora pico: {ven['hora_pico']}:00." if ven.get("hora_pico") else ""), "fuente": "bd"},
        "Clientes": {"contenido": ven["texto"], "fuente": "bd"},
        "Problemas": {"contenido": "Stock bajo: " + bajo["texto"] + "\nPor caducar: " + cad["texto"], "fuente": "bd"},
        "Hallazgos": {"contenido": mar["texto"], "fuente": "bd"},
        "Hipótesis": {"contenido": " ".join(hipotesis) or "Sin hipótesis relevantes.", "fuente": "hipotesis"},
        "Soluciones": {"contenido": "\n".join(soluciones) or "Sin acciones urgentes.", "fuente": "hipotesis"},
    }
    reporte = {"periodo": p, "secciones": secciones}
    with db.conn() as c:
        rid = c.execute("INSERT INTO reportes(periodo,contenido,generado_por) VALUES(?,?,?)",
                        (p, json.dumps(reporte, ensure_ascii=False), "analista")).lastrowid
    texto = "\n".join(f"{k} [{v['fuente']}]: {v['contenido']}" for k, v in secciones.items())
    return {"ok": True, "reporte_id": rid, "reporte": reporte, "texto": texto,
            "fuentes": ["bd", "externa"], "delegaciones": ["control", "investigador"]}


def reglas(texto: str, ctx: dict):
    t = norm(texto)
    p = detectar_periodo(t)
    if re.search(r"reporte|informe", t):
        return {"tool": "generar_reporte", "args": {"periodo": p}, "respuesta": ""}
    if re.search(r"margen|ganancia|utilidad", t):
        return {"tool": "calcular_margenes", "args": {"periodo": p}, "respuesta": ""}
    if re.search(r"mas vendid|top|menos vendid|rotacion|lentos|que se vende", t):
        return {"tool": "top_productos", "args": {"periodo": p}, "respuesta": ""}
    return {"tool": "consultar_ventas", "args": {"periodo": p}, "respuesta": ""}


ANALISTA = Agente("analista", "Interpretas los datos del negocio: ventas, márgenes, productos top y reportes. "
                  "Indica siempre si un dato viene de la BD o es una hipótesis.",
                  ["consultar_ventas", "calcular_margenes", "top_productos", "generar_reporte"], reglas)
