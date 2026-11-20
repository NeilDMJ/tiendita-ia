"""Agente Vendedor: carrito, venta, pago y acompañamiento del pago digital."""
import re

from .. import db
from .base import Agente
from .registro import tool
from .util import METODOS, detectar_metodo, dinero, norm, parsear_items, resolver_producto

ORDEN_PAGO = ["pendiente", "enviado", "recibido", "conciliado"]


def _total_carrito(c, carrito: dict) -> float:
    return sum(c.execute("SELECT precio FROM productos WHERE nombre=?", (n,)).fetchone()[0] * q
               for n, q in carrito.items())


def _texto_carrito(c, carrito: dict) -> str:
    if not carrito:
        return "El carrito está vacío."
    lineas = [f"- {q} x {n}" for n, q in carrito.items()]
    return "\n".join(lineas) + f"\nTotal: {dinero(_total_carrito(c, carrito))}"


@tool("vendedor", False, {"items": list}, ["items"])
def agregar_al_carrito(args, ctx):
    carrito = ctx.setdefault("carrito", {})
    with db.conn() as c:
        for it in args["items"]:
            p = resolver_producto(c, str(it.get("nombre", "")))
            cant = it.get("cantidad", 1)
            if not p:
                raise ValueError(f"No encontré '{it.get('nombre')}' en el catálogo.")
            if not isinstance(cant, int) or cant <= 0:
                raise ValueError("la cantidad debe ser un entero mayor a cero")
            if carrito.get(p["nombre"], 0) + cant > p["stock"]:
                raise ValueError(f"Solo te quedan {p['stock']} de {p['nombre']}.")
        for it in args["items"]:
            p = resolver_producto(c, str(it["nombre"]))
            carrito[p["nombre"]] = carrito.get(p["nombre"], 0) + it.get("cantidad", 1)
        texto = _texto_carrito(c, carrito)
    sufijo = f"\n¿Cobro con {ctx['metodo']}?" if ctx.get("metodo") else "\n¿Cómo paga: efectivo, transferencia, QR o tarjeta?"
    return {"ok": True, "carrito": dict(carrito), "texto": texto + sufijo, "fuentes": ["bd"]}


@tool("vendedor", False, {"items": list}, ["items"])
def quitar_del_carrito(args, ctx):
    carrito = ctx.setdefault("carrito", {})
    with db.conn() as c:
        for it in args["items"]:
            p = resolver_producto(c, str(it.get("nombre", "")))
            if not p or p["nombre"] not in carrito:
                raise ValueError(f"'{it.get('nombre')}' no está en el carrito.")
            q = carrito[p["nombre"]] - it.get("cantidad", 1)
            if q > 0:
                carrito[p["nombre"]] = q
            else:
                del carrito[p["nombre"]]
        texto = _texto_carrito(c, carrito)
    return {"ok": True, "carrito": dict(carrito), "texto": texto, "fuentes": ["bd"]}


@tool("vendedor", False, {})
def sugerir_complemento(args, ctx):
    carrito = list((ctx.get("carrito") or {}))
    with db.conn() as c:
        ids = [r[0] for r in c.execute(
            f"SELECT id FROM productos WHERE nombre IN ({','.join('?' * len(carrito)) or 'NULL'})", carrito)]
        rows = c.execute(
            f"SELECT p.nombre, COUNT(*) n FROM venta_detalle a JOIN venta_detalle b ON a.venta_id=b.venta_id "
            f"JOIN productos p ON p.id=b.producto_id WHERE a.producto_id IN ({','.join('?' * len(ids)) or 'NULL'}) "
            f"AND b.producto_id NOT IN ({','.join('?' * len(ids)) or 'NULL'}) AND p.stock>0 "
            f"GROUP BY p.id ORDER BY n DESC LIMIT 2", ids + ids).fetchall()
        if not rows:  # sin historial: lo que más se vende
            rows = c.execute(
                f"SELECT p.nombre FROM venta_detalle d JOIN productos p ON p.id=d.producto_id "
                f"WHERE p.stock>0 AND p.id NOT IN ({','.join('?' * len(ids)) or 'NULL'}) "
                f"GROUP BY p.id ORDER BY SUM(d.cantidad) DESC LIMIT 2", ids).fetchall()
    sug = [r["nombre"] for r in rows]
    texto = ("Ofrécele también: " + ", ".join(sug) + ".") if sug else "No tengo sugerencias todavía."
    return {"ok": True, "sugerencias": sug, "texto": texto, "fuentes": ["bd"]}


@tool("vendedor", True, {"items": list, "metodo_pago": str, "referencia": (str, type(None))},
      ["items", "metodo_pago"])
def registrar_venta(args, ctx):
    metodo = args["metodo_pago"].lower()
    if metodo not in METODOS:
        raise ValueError("método de pago debe ser efectivo, transferencia, qr o tarjeta")
    if not args["items"]:
        raise ValueError("el carrito está vacío")
    with db.conn() as c:
        acum = {}
        for it in args["items"]:
            cant = it.get("cantidad", 1) if isinstance(it, dict) else 0
            p = resolver_producto(c, str(it.get("nombre", ""))) if isinstance(it, dict) else None
            if not p:
                raise ValueError(f"producto no encontrado: {it.get('nombre') if isinstance(it, dict) else it}")
            if not isinstance(cant, int) or cant <= 0:
                raise ValueError("la cantidad debe ser un entero mayor a cero")
            prev = acum.get(p["id"], (p, 0))[1]
            acum[p["id"]] = (p, prev + cant)
        for p, cant in acum.values():
            if p["stock"] < cant:
                raise ValueError(f"stock insuficiente de {p['nombre']} (quedan {p['stock']})")
        total = sum(p["precio"] * cant for p, cant in acum.values())
        ref = args.get("referencia")
        digital = metodo != "efectivo"
        pago_estado = ("recibido" if ref else "pendiente") if digital else "conciliado"
        venta_estado = "pagada" if (not digital or ref) else "pendiente_pago"
        vid = c.execute("INSERT INTO ventas(total,metodo_pago,estado) VALUES(?,?,?)",
                        (total, metodo, venta_estado)).lastrowid
        for p, cant in acum.values():
            c.execute("INSERT INTO venta_detalle(venta_id,producto_id,cantidad,precio) VALUES(?,?,?,?)",
                      (vid, p["id"], cant, p["precio"]))
            c.execute("UPDATE productos SET stock=stock-? WHERE id=?", (cant, p["id"]))
            c.execute("INSERT INTO movimientos_inventario(producto_id,tipo,cantidad) VALUES(?,?,?)",
                      (p["id"], "salida", cant))
        c.execute("INSERT INTO pagos(venta_id,tipo,referencia,monto,estado) VALUES(?,?,?,?,?)",
                  (vid, metodo, ref, total, pago_estado))
    texto = f"Venta #{vid} registrada por {dinero(total)} ({metodo})."
    if digital and not ref:
        texto += " Pago pendiente: muéstrale el QR o tus datos al cliente y dime la referencia cuando llegue."
    return {"ok": True, "venta_id": vid, "total": total, "estado_pago": pago_estado, "texto": texto,
            "fuentes": ["bd"]}


@tool("vendedor", True, {"venta_id": int, "referencia": (str, type(None)), "estado": (str, type(None)),
                         "monto": (int, float, type(None)), "comprobante": (str, type(None))}, ["venta_id"])
def registrar_pago(args, ctx):
    with db.conn() as c:
        p = c.execute("SELECT p.*, v.total FROM pagos p JOIN ventas v ON v.id=p.venta_id WHERE p.venta_id=?",
                      (args["venta_id"],)).fetchone()
        if not p:
            raise ValueError("esa venta no tiene pago registrado")
        if p["tipo"] == "efectivo":
            raise ValueError("las ventas en efectivo no requieren registrar un pago digital")
        ref = args.get("referencia") or p["referencia"]
        comp = args.get("comprobante") or p["comprobante"]
        nuevo = args.get("estado") or ("recibido" if (ref or comp) else "enviado")
        if nuevo not in ORDEN_PAGO:
            raise ValueError("estado debe ser pendiente, enviado, recibido o conciliado")
        if ORDEN_PAGO.index(nuevo) < ORDEN_PAGO.index(p["estado"]):
            raise ValueError(f"el pago ya está en estado {p['estado']}")
        if nuevo in ("recibido", "conciliado") and not (ref or comp):
            raise ValueError("falta la referencia o el comprobante para marcar el pago como recibido")
        if args.get("monto") is not None and abs(args["monto"] - p["total"]) > 0.01:
            raise ValueError(f"el monto {dinero(args['monto'])} no coincide con el total {dinero(p['total'])}")
        c.execute("UPDATE pagos SET estado=?, referencia=?, comprobante=? WHERE id=?", (nuevo, ref, comp, p["id"]))
        if nuevo in ("recibido", "conciliado"):
            c.execute("UPDATE ventas SET estado='pagada' WHERE id=?", (args["venta_id"],))
    return {"ok": True, "venta_id": args["venta_id"], "estado": nuevo,
            "texto": f"Listo, el pago quedó {nuevo} y ligado a la venta #{args['venta_id']}.", "fuentes": ["bd"]}


def reglas(texto: str, ctx: dict):
    t = norm(texto)
    metodo = detectar_metodo(t)
    with db.conn() as c:
        if re.search(r"\b(quita|quitar|elimina|saca|borra)\b", t):
            items, _ = parsear_items(c, re.sub(r"\b(quita|quitar|elimina|saca|borra)\b", " ", t))
            if items:
                return {"tool": "quitar_del_carrito", "args": {"items": items}, "respuesta": ""}
        ref = re.search(r"referencia\s*[:#]?\s*([a-z0-9]{4,})", t)
        if ref or re.search(r"comprobante|ya (llego|pago|me transfirio)|transferencia (recibida|llego)", t):
            return {"tool": "registrar_pago", "args": {"venta_id": None, "referencia": ref.group(1) if ref else None},
                    "respuesta": "Voy a marcar el pago como recibido. ¿Confirmas?"}
        if re.search(r"complement|que mas le ofrezco|sugier|recomiend", t):
            return {"tool": "sugerir_complemento", "args": {}, "respuesta": ""}
        items, faltan = parsear_items(c, texto)
    if items:
        if metodo:
            ctx["metodo"] = metodo
        return {"tool": "agregar_al_carrito", "args": {"items": items}, "respuesta": ""}
    if faltan:
        return {"tool": None, "args": {}, "respuesta": f"No encontré '{faltan[0]}' en el catálogo. ¿Lo damos de alta?"}
    if metodo or re.search(r"\b(cobr\w*|total|pagar|listo)\b", t):
        return {"tool": "registrar_venta", "args": {"items": None, "metodo_pago": metodo},
                "respuesta": "Voy a registrar la venta. ¿Confirmas?"}
    return {"tool": None, "args": {}, "respuesta": "¿Qué productos agrego al carrito?"}


VENDEDOR = Agente("vendedor", "Armas el carrito, confirmas totales, registras ventas y guías el pago digital "
                  "(pendiente, enviado, recibido, conciliado).",
                  ["agregar_al_carrito", "quitar_del_carrito", "registrar_venta", "registrar_pago",
                   "sugerir_complemento"], reglas)
