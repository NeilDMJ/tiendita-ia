"""Agente Control: catálogo, inventario, caducidades, gastos, cierre de caja y conciliación."""
import re

from .. import db, tools
from . import registro
from .base import Agente, extraer_json, llamar_llm, llm_disponible
from .registro import Tool, tool
from .util import PERIODOS, dinero, norm, resolver_producto

# Mantener sincronizado con assistant/gen_data.py (el LoRA se entrena con este prompt exacto)
SYSTEM_PROMPT = """Eres el asistente de catálogo de una tiendita en México. Responde SOLO con un JSON:
{"tool": <nombre o null>, "args": {...}, "respuesta": "<texto breve en español>"}
Herramientas: crear_producto(nombre, precio, costo?, stock, caducidad?), actualizar_precio(nombre, precio),
consultar_inventario(nombre?), ajustar_stock(nombre, cantidad, tipo: entrada|salida|merma).
Si faltan datos, tool=null y pídelos en "respuesta". Si piden algo fuera del catálogo, tool=null y explícalo."""


# ---- herramientas originales del catálogo (backend/tools.py) ---------------------------------
def _legacy(nombre):
    def fn(args, ctx):
        r = tools.ejecutar(nombre, args)
        if nombre == "consultar_inventario":
            ps = r["productos"]
            r["texto"] = ("\n".join(f"- {p['nombre']}: {p['stock']} pzas, {dinero(p['precio'])}" for p in ps)
                          or "No encontré productos.")
        else:
            r["texto"] = "Listo, ya quedó guardado."
        r["fuentes"] = ["bd"]
        return r
    return fn


for _n in tools.ESQUEMAS:
    registro.TOOLS[_n] = Tool(_n, "control", _n != "consultar_inventario",
                              tools.ESQUEMAS[_n], tools.REQUERIDOS[_n], _legacy(_n))


# ---- herramientas nuevas ----------------------------------------------------------------------
@tool("control", False, {"umbral": (int, type(None))})
def stock_bajo(args, ctx):
    umbral = args.get("umbral") if args.get("umbral") is not None else 5
    with db.conn() as c:
        ps = [dict(r) for r in c.execute(
            "SELECT nombre, stock FROM productos WHERE stock<=? ORDER BY stock, nombre", (umbral,))]
    texto = ("\n".join(f"- {p['nombre']}: te quedan {p['stock']}" for p in ps)
             or f"Nada con {umbral} piezas o menos.")
    return {"ok": True, "productos": ps, "texto": texto, "fuentes": ["bd"]}


@tool("control", False, {"dias": (int, type(None))})
def productos_por_caducar(args, ctx):
    dias = args.get("dias") if args.get("dias") is not None else 7
    with db.conn() as c:
        ps = [dict(r) for r in c.execute(
            "SELECT nombre, stock, precio, costo, caducidad, "
            "CAST(julianday(caducidad)-julianday(date('now','localtime')) AS INTEGER) AS dias "
            "FROM productos WHERE caducidad IS NOT NULL AND stock>0 "
            "AND date(caducidad)<=date('now','localtime',?) ORDER BY caducidad",
            (f"+{int(dias)} days",))]
    texto = ("\n".join(f"- {p['nombre']}: caduca {p['caducidad']} ({p['dias']} días), {p['stock']} pzas"
                       for p in ps) or f"Nada caduca en los próximos {dias} días.")
    return {"ok": True, "productos": ps, "texto": texto, "fuentes": ["bd"]}


@tool("control", False, {"fecha": (str, type(None))})
def cierre_de_caja(args, ctx):
    fecha = args.get("fecha")
    with db.conn() as c:
        por_metodo = {r["metodo_pago"]: r["t"] for r in c.execute(
            "SELECT metodo_pago, SUM(total) t FROM ventas "
            "WHERE date(fecha,'localtime')=COALESCE(?, date('now','localtime')) GROUP BY metodo_pago", (fecha,))}
        n = c.execute("SELECT COUNT(*) FROM ventas WHERE date(fecha,'localtime')="
                      "COALESCE(?, date('now','localtime'))", (fecha,)).fetchone()[0]
        gastos = c.execute("SELECT COALESCE(SUM(monto),0) FROM gastos WHERE date(fecha,'localtime')="
                           "COALESCE(?, date('now','localtime'))", (fecha,)).fetchone()[0]
        sin_cobrar = [dict(r) for r in c.execute(
            "SELECT v.id venta_id, v.total, p.estado FROM pagos p JOIN ventas v ON v.id=p.venta_id "
            "WHERE p.tipo!='efectivo' AND p.estado IN ('pendiente','enviado') "
            "AND date(v.fecha,'localtime')=COALESCE(?, date('now','localtime'))", (fecha,))]
        por_conciliar = c.execute(
            "SELECT COUNT(*) FROM pagos p JOIN ventas v ON v.id=p.venta_id WHERE p.estado='recibido' "
            "AND date(v.fecha,'localtime')=COALESCE(?, date('now','localtime'))", (fecha,)).fetchone()[0]
    total = sum(por_metodo.values())
    efectivo = por_metodo.get("efectivo", 0)
    lineas = [f"{n} ventas por {dinero(total)}: efectivo {dinero(efectivo)}, digital {dinero(total - efectivo)}.",
              f"Gastos del día: {dinero(gastos)}. Neto: {dinero(total - gastos)}."]
    if sin_cobrar:
        lineas.append("Diferencias: " + ", ".join(f"venta #{s['venta_id']} ({dinero(s['total'])}, {s['estado']})"
                                                  for s in sin_cobrar) + " sin pago recibido.")
    if por_conciliar:
        lineas.append(f"{por_conciliar} pagos recibidos listos para conciliar.")
    return {"ok": True, "ventas": n, "total": total, "efectivo": efectivo, "digital": total - efectivo,
            "gastos": gastos, "neto": total - gastos, "diferencias": sin_cobrar,
            "por_conciliar": por_conciliar, "texto": "\n".join(lineas), "fuentes": ["bd"]}


@tool("control", True, {"concepto": str, "monto": (int, float), "tipo": (str, type(None)),
                        "ticket": (str, type(None))}, ["concepto", "monto"])
def registrar_gasto(args, ctx):
    tipo = args.get("tipo") or "gasto"
    if tipo not in ("gasto", "compra", "inversion"):
        raise ValueError("tipo debe ser gasto, compra o inversion")
    if args["monto"] <= 0:
        raise ValueError("el monto debe ser mayor a cero")
    with db.conn() as c:
        cur = c.execute("INSERT INTO gastos(concepto,monto,tipo,ticket) VALUES(?,?,?,?)",
                        (args["concepto"], args["monto"], tipo, args.get("ticket")))
    return {"ok": True, "id": cur.lastrowid, "texto": f"Registré {tipo}: {args['concepto']} por {dinero(args['monto'])}."}


@tool("control", True, {})
def conciliar_pagos(args, ctx):
    with db.conn() as c:
        n = c.execute("UPDATE pagos SET estado='conciliado' WHERE estado='recibido'").rowcount
        pend = c.execute("SELECT COUNT(*) FROM pagos WHERE estado IN ('pendiente','enviado') "
                         "AND tipo!='efectivo'").fetchone()[0]
    return {"ok": True, "conciliados": n, "pendientes": pend,
            "texto": f"Concilié {n} pagos. Quedan {pend} sin recibir."}


# ---- agente ----------------------------------------------------------------------------------
NUEVAS = ["consultar_inventario", "stock_bajo", "productos_por_caducar", "cierre_de_caja",
          "registrar_gasto", "conciliar_pagos"]


def reglas(texto: str, ctx: dict):
    """Atajos deterministas. Devuelve None si no aplica (entonces decide el LLM del catálogo)."""
    t = norm(texto)
    alta = re.search(r"\b(alta|nuevo producto|registra|guarda)\b|\$", t)
    m = re.search(r"\b(gaste|gasto|compre|pague|inverti|invierto)\b\s*(?:de\s*)?\$?\s*(\d+(?:\.\d+)?)"
                  r"\s*(?:pesos)?\s*(?:en|de|por)?\s*(.*)", t)
    if m:
        tipo = "compra" if m.group(1) == "compre" else "gasto"
        if re.search(r"inver", t):
            tipo = "inversion"
        return {"tool": "registrar_gasto", "args": {"concepto": m.group(3).strip() or "gasto",
                                                    "monto": float(m.group(2)), "tipo": tipo},
                "respuesta": f"Voy a registrar un {tipo} de ${m.group(2)}. ¿Confirmas?"}
    if re.search(r"\b(cierre|corte)\b", t):
        return {"tool": "cierre_de_caja", "args": {}, "respuesta": ""}
    if re.search(r"\bconcilia", t):
        return {"tool": "conciliar_pagos", "args": {}, "respuesta": "Voy a conciliar los pagos recibidos. ¿Confirmas?"}
    if re.search(r"stock bajo|por agotar|se acaba|poco inventario|me falta|que reabastec", t):
        return {"tool": "stock_bajo", "args": {}, "respuesta": ""}
    if re.search(r"caduc|vence|vencer", t) and not alta:
        return {"tool": "productos_por_caducar", "args": {}, "respuesta": ""}
    m = re.search(r"\b(?:sube|baja|cambia|pon\w*|actualiza)\s+(?:el precio de\s+)?(.+?)\s+(?:a|en)\s+\$?(\d+(?:\.\d+)?)", t)
    if m:
        with db.conn() as c:
            p = resolver_producto(c, m.group(1))
        if p:
            return {"tool": "actualizar_precio", "args": {"nombre": p["nombre"], "precio": float(m.group(2))},
                    "respuesta": f"Voy a poner {p['nombre']} en ${m.group(2)}. ¿Confirmas?"}
    if re.search(r"cuant\w+|inventario|existencias|me quedan|\bstock\b", t) and not alta:
        with db.conn() as c:
            p = resolver_producto(c, re.sub(r"cuant\w+|me quedan|quedan|hay|tengo", " ", t))
        if p:
            return {"tool": "consultar_inventario", "args": {"nombre": p["nombre"]}, "respuesta": ""}
        if re.search(r"inventario|catalogo|existencias", t):
            return {"tool": "consultar_inventario", "args": {}, "respuesta": ""}
        return {"tool": None, "args": {}, "respuesta": "No identifiqué ese producto. ¿Cómo se llama exactamente?"}
    return None


async def interpretar_catalogo(mensaje: str) -> dict:
    """Interpretación del catálogo con el LLM/LoRA (prompt original). Sin LLM: respuesta simulada."""
    if not llm_disponible():
        return {"tool": None, "args": {}, "respuesta": "Asistente simulado: aún sin modelo.",
                "simulado": True, "motor": "reglas"}
    texto, modelo = await llamar_llm(SYSTEM_PROMPT, mensaje)
    out = extraer_json(texto)
    if out is None:
        raise ValueError("el asistente no devolvió JSON válido")
    return {"tool": out.get("tool"), "args": out.get("args") or {}, "respuesta": out.get("respuesta", ""),
            "modelo": modelo, "motor": "llm"}


class AgenteControl(Agente):
    async def proponer(self, texto: str, ctx: dict) -> dict:
        r = self.reglas(texto, ctx)
        if r is not None:
            return {"motor": "reglas", "simulado": not llm_disponible(), **r}
        return await interpretar_catalogo(texto)


CONTROL = AgenteControl(
    "control", "Administras catálogo, inventario, caducidades, gastos, cierre de caja y conciliación de pagos.",
    list(tools.ESQUEMAS) + NUEVAS[1:], reglas)
