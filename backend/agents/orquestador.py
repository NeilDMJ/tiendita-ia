"""Orquestador: rutea el mensaje al agente adecuado (LLM + reglas de respaldo), mantiene la sesión
(carrito, propuesta pendiente) y aplica el patrón proponer -> confirmar para toda escritura."""
import re

from .. import db
from . import registro
from .analista import ANALISTA
from .base import extraer_json, llamar_llm, llm_disponible
from .control import CONTROL
from .investigador import INVESTIGADOR
from .publicista import PUBLICISTA
from .util import dinero, norm
from .vendedor import VENDEDOR

AGENTES = {a.nombre: a for a in (VENDEDOR, CONTROL, ANALISTA, PUBLICISTA, INVESTIGADOR)}
SESIONES: dict[str, dict] = {}
SI = {"si", "confirmo", "confirmado", "ok", "dale", "va", "claro", "adelante", "si confirmo"}
NO = {"no", "cancela", "cancelar", "mejor no", "cancelalo"}
PEDIR = {"items": "los productos (el carrito está vacío)", "metodo_pago": "el método de pago (efectivo, transferencia, QR o tarjeta)",
         "venta_id": "el número de venta", "nombre": "el nombre del producto", "precio": "el precio",
         "stock": "cuántas piezas hay", "cantidad": "la cantidad", "tipo": "el tipo", "concepto": "el concepto",
         "monto": "el monto"}

ROUTER_PROMPT = ("Eres el orquestador de una tiendita. Elige UN agente para el mensaje del vendedor: "
                 "vendedor (carrito, cobrar, pagos), control (inventario, catálogo, caducidades, gastos, cierre de caja), "
                 "analista (ventas, márgenes, reportes), publicista (promociones), investigador (precios de referencia, mercado). "
                 'Responde SOLO con JSON: {"agente": "<nombre>"}')


def sesion(sid: str) -> dict:
    return SESIONES.setdefault(sid, {"carrito": {}, "ultima_venta": None, "metodo": None})


def rutear_reglas(texto: str) -> str:
    t = norm(texto)
    if re.search(r"promo|oferta|anuncio|publicidad|whatsapp|descuento", t):
        return "publicista"
    if re.search(r"precio de referencia|mercado|competencia|sector|cuanto cuesta", t):
        return "investigador"
    if re.search(r"como me fue|reporte|informe|ventas|margen|ganancia|utilidad|mas vendid|menos vendid|rotacion|lentos", t):
        return "analista"
    if re.search(r"\$|precio|stock|piezas|alta|nuevo producto|registra|guarda|inventario|cuant\w+|quedan|caduc|vence|"
                 r"agotar|cierre|corte|gast|compre|pague|inverti|concilia|catalogo", t):
        # "cobrame 2 cocas por $40" sigue siendo del vendedor
        if re.search(r"concilia|cierre", t) or not re.search(r"\bcobr\w*|carrito|pago|paga\b|referencia|comprobante", t):
            return "control"
    if re.search(r"cobr\w*|carrito|vendi|vende|total|pago|paga|transferencia|efectivo|\bqr\b|tarjeta|referencia|"
                 r"comprobante|agrega|quita|complement|\d+\s+\w+", t):
        return "vendedor"
    return "control"


async def rutear(texto: str, ctx: dict, esperando: str | None):
    if esperando in AGENTES:
        return esperando, "sesion"
    if llm_disponible():
        try:
            txt, _ = await llamar_llm(ROUTER_PROMPT, texto, max_tokens=512)
            a = (extraer_json(txt) or {}).get("agente")
            if a in AGENTES:
                return a, "llm"
        except Exception:
            pass  # respaldo por reglas
    return rutear_reglas(texto), "reglas"


def _completar(tool: str, args: dict, ctx: dict) -> dict:
    """Rellena con el estado de la sesión lo que el mensaje no trae (carrito, método, venta)."""
    args = dict(args)
    if tool == "registrar_venta":
        if args.get("items") is None and ctx.get("carrito"):
            args["items"] = [{"nombre": n, "cantidad": q} for n, q in ctx["carrito"].items()]
        if args.get("metodo_pago") is None:
            args["metodo_pago"] = ctx.get("metodo")
    elif tool == "registrar_pago" and args.get("venta_id") is None:
        vid = ctx.get("ultima_venta")
        if vid is None:
            with db.conn() as c:
                r = c.execute("SELECT venta_id FROM pagos WHERE estado IN ('pendiente','enviado') "
                              "AND tipo!='efectivo' ORDER BY venta_id DESC LIMIT 1").fetchone()
            vid = r[0] if r else None
        args["venta_id"] = vid
    return args


def _resultado(ctx: dict, tool: str, r: dict):
    """Efectos de sesión tras ejecutar una escritura."""
    if tool == "registrar_venta":
        ctx["carrito"], ctx["metodo"], ctx["ultima_venta"] = {}, None, r["venta_id"]


def confirmar(tool: str, args: dict, sid: str = "default") -> dict:
    """Ejecuta una propuesta ya confirmada. ValueError = datos inválidos (422)."""
    ctx = sesion(sid)
    r = registro.ejecutar(tool, args, ctx)
    _resultado(ctx, tool, r)
    ctx.pop("pendiente", None)
    return r


def _base(agente, ruteo, **extra):
    return {"agente": agente, "ruteo": ruteo, "tool": None, "args": {}, "respuesta": "", "faltantes": [],
            "requiere_confirmacion": False, "resultado": None, "fuentes": [], "delegaciones": [], **extra}


async def atender(texto: str, sid: str = "default") -> dict:
    ctx = sesion(sid)
    t = norm(texto).strip(" .!¡¿?")
    pend = ctx.get("pendiente")
    if pend and t in SI:
        try:
            r = confirmar(pend["tool"], pend["args"], sid)
            return _base(pend["agente"], "sesion", tool=pend["tool"], args=pend["args"], respuesta=r["texto"],
                         resultado=r, fuentes=r.get("fuentes", []))
        except ValueError as e:
            ctx.pop("pendiente", None)
            return _base(pend["agente"], "sesion", tool=pend["tool"], args=pend["args"], respuesta=f"No se pudo: {e}")
    if pend and t in NO:
        ctx.pop("pendiente")
        return _base(pend["agente"], "sesion", respuesta="Cancelado, no cambié nada.")

    esperando = ctx.pop("esperando", None)
    ctx.pop("pendiente", None)
    agente, ruteo = await rutear(texto, ctx, esperando)
    prop = await AGENTES[agente].proponer(texto, ctx)
    extra = {k: v for k, v in prop.items() if k in ("motor", "simulado", "modelo")}
    tool = prop.get("tool")
    if tool and tool in registro.TOOLS and registro.TOOLS[tool].agente != agente:
        agente, ruteo = registro.TOOLS[tool].agente, ruteo + "+delegado"  # el modelo eligió una tool de otro rol
    if not tool:
        return _base(agente, ruteo, respuesta=prop.get("respuesta") or "¿Me das más detalle?", **extra)

    args = _completar(tool, prop.get("args") or {}, ctx)
    faltantes = registro.validar(tool, args)
    if faltantes:
        ctx["esperando"] = agente
        pedir = [PEDIR.get(f.removeprefix("falta "), f) for f in faltantes]
        return _base(agente, ruteo, tool=tool, args=args, faltantes=faltantes, **extra,
                     respuesta="Me falta " + ", ".join(pedir) + ".")
    t_ = registro.TOOLS[tool]
    if t_.escribe:  # propuesta: nada se escribe hasta confirmar
        ctx["pendiente"] = {"agente": agente, "tool": tool, "args": args}
        return _base(agente, ruteo, tool=tool, args=args, requiere_confirmacion=True, **extra,
                     respuesta=prop.get("respuesta") or "¿Confirmas?")
    try:
        r = registro.ejecutar(tool, args, ctx)
    except ValueError as e:
        return _base(agente, ruteo, tool=tool, args=args, respuesta=str(e), **extra)
    return _base(agente, ruteo, tool=tool, args=args, respuesta=r["texto"], resultado=r,
                 fuentes=r.get("fuentes", []), delegaciones=r.get("delegaciones", []), **extra)


def alertas() -> list[dict]:
    """Avisos proactivos: cada uno lo 'dice' el agente que corresponde."""
    from .control import productos_por_caducar, stock_bajo
    out = []
    for p in stock_bajo({}, {})["productos"]:
        out.append({"agente": "control", "tipo": "stock_bajo", "mensaje": f"Te quedan {p['stock']} de {p['nombre']}."})
    for p in productos_por_caducar({"dias": 7}, {})["productos"]:
        out.append({"agente": "publicista", "tipo": "por_caducar",
                    "mensaje": f"{p['nombre']} caduca en {p['dias']} días, ¿armo una promoción?",
                    "sugerencia": {"tool": "generar_promocion", "args": {"nombre": p["nombre"]}}})
    with db.conn() as c:
        for r in c.execute("SELECT venta_id, estado FROM pagos WHERE tipo!='efectivo' AND estado IN "
                           "('pendiente','enviado','recibido')"):
            out.append({"agente": "vendedor" if r["estado"] != "recibido" else "control", "tipo": "pago_sin_conciliar",
                        "mensaje": f"El pago de la venta #{r['venta_id']} está {r['estado']}."})
    return out
