"""Agente Publicista: promociones para productos por caducar o de baja rotación (texto listo para WhatsApp)."""
import json
import re

from .. import db
from . import control
from .base import Agente
from .registro import tool
from .util import dinero, norm, resolver_producto


@tool("publicista", False, {"nombre": (str, type(None)), "descuento": (int, type(None))})
def generar_promocion(args, ctx):
    desc = args.get("descuento") if args.get("descuento") is not None else 20
    if not 5 <= desc <= 70:
        raise ValueError("el descuento debe estar entre 5% y 70%")
    delegaciones = []
    with db.conn() as c:
        if args.get("nombre"):
            p = resolver_producto(c, args["nombre"])
            if not p:
                raise ValueError(f"No encontré '{args['nombre']}' en el catálogo.")
        else:  # el Publicista le pide a Control lo más urgente
            cad = control.productos_por_caducar({"dias": 14}, ctx)["productos"]
            delegaciones.append("control")
            if cad:
                p = c.execute("SELECT * FROM productos WHERE nombre=?", (cad[0]["nombre"],)).fetchone()
            else:
                p = c.execute("SELECT * FROM productos WHERE stock>0 ORDER BY stock DESC LIMIT 1").fetchone()
            if not p:
                raise ValueError("No hay productos con existencias para promocionar.")
    nuevo = round(p["precio"] * (1 - desc / 100))
    aviso = ""
    if p["costo"] is not None and nuevo < p["costo"]:
        aviso = f" Ojo: {dinero(nuevo)} queda por debajo de tu costo ({dinero(p['costo'])})."
    motivo = f" Caduca el {p['caducidad']}." if p["caducidad"] else ""
    mensaje = (f"¡Oferta en la tiendita! {p['nombre']} de {dinero(p['precio'])} a solo {dinero(nuevo)} "
               f"({desc}% menos). Quedan {p['stock']} piezas.{motivo} ¡Pásate por el tuyo!")
    with db.conn() as c:
        c.execute("INSERT INTO reportes(periodo,contenido,generado_por) VALUES(?,?,?)",
                  ("promocion", json.dumps({"producto": p["nombre"], "precio_promo": nuevo, "mensaje": mensaje},
                                           ensure_ascii=False), "publicista"))
    return {"ok": True, "producto": p["nombre"], "precio_promo": nuevo, "mensaje": mensaje,
            "texto": mensaje + aviso, "fuentes": ["bd"], "delegaciones": delegaciones}


def reglas(texto: str, ctx: dict):
    t = norm(texto)
    d = re.search(r"(\d{1,2})\s*%", t)
    nombre = None
    with db.conn() as c:
        p = resolver_producto(c, re.sub(r"promo\w*|oferta|descuento|anuncio|publicidad|whatsapp|arma\w*|haz\w*|crea\w*", " ", t))
        if p:
            nombre = p["nombre"]
    return {"tool": "generar_promocion", "args": {"nombre": nombre, "descuento": int(d.group(1)) if d else None},
            "respuesta": ""}


PUBLICISTA = Agente("publicista", "Creas promociones y textos para WhatsApp o redes para productos por caducar "
                    "o de baja rotación. Cuida que el precio promocional no quede bajo el costo.",
                    ["generar_promocion"], reglas)
