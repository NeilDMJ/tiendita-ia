"""Utilidades compartidas por los agentes: normalización de texto y resolución de productos."""
import re
import unicodedata

STOP = {"los", "las", "del", "una", "uno", "por", "para", "con", "que", "cuantos", "cuantas", "quedan",
        "dame", "cobrame", "agrega", "pesos", "piezas", "pieza", "mas", "como", "esta", "estan", "hay",
        "tengo", "precio", "sube", "baja", "cambia", "mis", "mi", "ahora", "cuesta", "stock"}

NUM = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
       "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "docena": 12, "media docena": 6}

METODOS = ("efectivo", "transferencia", "qr", "tarjeta")

# Filtros de periodo sobre la columna `fecha` (hora local del servidor)
PERIODOS = {
    "hoy": "date(fecha,'localtime')=date('now','localtime')",
    "semana": "date(fecha,'localtime')>=date('now','localtime','-6 days')",
    "mes": "date(fecha,'localtime')>=date('now','localtime','-29 days')",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").lower()


def toks(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", norm(s)) if len(t) >= 3 and t not in STOP]


def _coincide(a: str, b: str) -> bool:
    a, b = a.rstrip("s"), b.rstrip("s")
    return a == b or (min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)))


def resolver_producto(c, frag: str):
    """Busca un producto por nombre exacto o por coincidencia de palabras (tolera plurales y alias)."""
    if not frag:
        return None
    exacto = c.execute("SELECT * FROM productos WHERE nombre=? COLLATE NOCASE", (frag.strip(),)).fetchone()
    if exacto:
        return exacto
    t = toks(frag)
    if not t:
        return None
    mejor, puntos = None, 0
    for r in c.execute("SELECT * FROM productos"):
        nt = toks(r["nombre"])
        p = sum(any(_coincide(x, y) for y in nt) for x in t)
        if p > puntos or (p == puntos and p and mejor is not None and len(r["nombre"]) < len(mejor["nombre"])):
            mejor, puntos = r, p
    return mejor if puntos else None


def detectar_metodo(t: str):
    for m in METODOS:
        if re.search(rf"\b{m}\b", t):
            return m
    return None


def detectar_periodo(t: str) -> str:
    if re.search(r"\bsemana", t):
        return "semana"
    if re.search(r"\bmes\b", t):
        return "mes"
    return "hoy"


def parsear_items(c, texto: str):
    """'2 cocas y 3 gansitos' -> ([{'nombre','cantidad'}], [no_encontrados])."""
    t = norm(texto)
    t = re.sub(r"\b(?:(?:pago|paga|pagan|pagara)\s+)?(?:con|en|por)\s+(?:efectivo|transferencia|qr|tarjeta)\b", "", t)
    t = re.sub(r"\b(efectivo|transferencia|qr|tarjeta)\b", "", t)
    t = re.sub(r"\b(cobrame|cobrale|cobra|cobrar|agregame|agregale|agrega|anademe|anade|ponme|vendi|vendo|"
               r"vende|dame|llevo|lleva|llevame|quiero|el total|al carrito|por favor|porfa|me)\b", " ", t)
    items, faltan = [], []
    for parte in re.split(r",|\by\b|\be\b", t):
        parte = parte.strip(" .")
        m = re.match(r"^(\d+|media docena|docena|" + "|".join(k for k in NUM if " " not in k) + r")\s+(.*)$", parte)
        n, resto = (NUM.get(m.group(1)) or int(m.group(1)), m.group(2)) if m else (1, parte)
        resto = re.sub(r"^de\s+", "", resto).strip()
        if not toks(resto):
            continue
        p = resolver_producto(c, resto)
        if p:
            items.append({"nombre": p["nombre"], "cantidad": max(n, 1)})
        else:
            faltan.append(resto)
    return items, faltan


def dinero(x) -> str:
    return f"${x:,.0f}" if float(x).is_integer() else f"${x:,.2f}"
