"""Agente Investigador: contexto externo. En la demo usa datos LOCALES simulados (sin internet);
toda respuesta se marca fuente "externa" y simulado=True para no presentarlos como hechos reales."""
import re

from .. import db
from .base import Agente
from .registro import tool
from .util import dinero, norm, resolver_producto

# Precios de referencia ilustrativos (NO son datos reales de mercado)
REFERENCIAS = {
    "Coca-Cola 600 ml": 19, "Agua 1 L": 14, "Jugo Boing 500 ml": 14, "Leche Lala 1 L": 28,
    "Pan de caja Bimbo": 44, "Gansito Marinela": 17, "Sabritas Original 45 g": 19, "Takis Fuego 56 g": 19,
    "Galletas Marías Gamesa": 15, "Sopa Maruchan": 16, "Atún Dolores": 23, "Frijoles La Sierra": 21,
    "Aceite 1-2-3 1 L": 43, "Papel higiénico": 9, "Jabón Zote": 19,
}
SECTOR = ("Tienda de abarrotes de barrio: la demanda se concentra en bebidas, botanas y básicos de despensa; "
          "el ticket promedio es bajo y la rotación alta; los márgenes por pieza son pequeños, por lo que "
          "conviene vigilar mermas por caducidad y precios frente a la competencia cercana.")


@tool("investigador", False, {"nombre": str}, ["nombre"])
def buscar_referencias(args, ctx):
    with db.conn() as c:
        p = resolver_producto(c, args["nombre"])
    nombre = p["nombre"] if p else args["nombre"]
    ref = REFERENCIAS.get(nombre)
    if ref is None:
        return {"ok": True, "texto": f"No tengo precio de referencia para {nombre}.", "fuentes": ["externa"],
                "simulado": True}
    texto = f"Precio de referencia de {nombre}: {dinero(ref)} (dato simulado de demostración)."
    if p:
        dif = p["precio"] - ref
        texto += (f" Tú lo vendes en {dinero(p['precio'])}: " +
                  ("igual a la referencia." if dif == 0 else f"{dinero(abs(dif))} {'arriba' if dif > 0 else 'abajo'}."))
    return {"ok": True, "producto": nombre, "referencia": ref, "texto": texto, "fuentes": ["externa", "bd"] if p else ["externa"],
            "simulado": True}


@tool("investigador", False, {})
def resumen_mercado(args, ctx):
    return {"ok": True, "texto": SECTOR + " (resumen simulado de demostración)", "fuentes": ["externa"],
            "simulado": True}


def reglas(texto: str, ctx: dict):
    t = norm(texto)
    if re.search(r"precio de referencia|cuanto cuesta|a como|compar|competencia|precio", t):
        with db.conn() as c:
            p = resolver_producto(c, re.sub(r"precio de referencia|cuanto cuesta|compar\w*|competencia|precio", " ", t))
        if p:
            return {"tool": "buscar_referencias", "args": {"nombre": p["nombre"]}, "respuesta": ""}
        return {"tool": None, "args": {}, "respuesta": "¿De qué producto quieres el precio de referencia?"}
    return {"tool": "resumen_mercado", "args": {}, "respuesta": ""}


INVESTIGADOR = Agente("investigador", "Das contexto externo: precios de referencia y estado del mercado del giro. "
                      "Marca siempre que el dato es externo.", ["buscar_referencias", "resumen_mercado"], reglas)
