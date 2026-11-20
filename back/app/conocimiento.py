"""Base de conocimiento (DiMo, CoDi, SPEI) a partir de documentos de Banxico.

Búsqueda BM25 en memoria sobre `datos/conocimiento.jsonl` (fragmentos de ~1000 caracteres).
Sin dependencias ni red: nada del mensaje sale del servidor para buscar. Para regenerar el
archivo, ver README. El modelo solo puede responder con los fragmentos devueltos aquí.
"""
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

RUTA = Path(__file__).parent / "datos" / "conocimiento.jsonl"
STOP = set(
    "el la los las un una unos unas de del al y o u a en por para con sin que es son se su sus lo le les "
    "como cual cuales qué que cuando donde quien me mi mis te tu tus nos ya muy mas pero si no ser esta este "
    "esto estos estas hay puede puedo pueden hacer quiero necesito usar uso utilizar".split()
)
# Peso por relevancia del documento (las guías para usuarios pesan más que informes y normativa).
PESO = {"alta": 1.15, "media": 1.0, "baja": 0.8}


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def tokens(t: str) -> list[str]:
    # Raíz aproximada (6 letras) para que "transferencias"/"transferir" se encuentren.
    return [p[:6] for p in re.findall(r"[a-z0-9ñ]+", _sin_acentos(t)) if p not in STOP and len(p) > 1]


@dataclass(frozen=True)
class Fragmento:
    id: str
    doc: str
    titulo: str
    seccion: str
    texto: str
    fuente: str
    relevancia: str


class Indice:
    def __init__(self, fragmentos: list[Fragmento]):
        self.fragmentos = fragmentos
        self.tf = [Counter(tokens(f"{f.titulo} {f.seccion} {f.texto}")) for f in fragmentos]
        self.largo = [sum(c.values()) for c in self.tf]
        self.promedio = (sum(self.largo) / len(self.largo)) if self.largo else 1.0
        df: Counter[str] = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(fragmentos)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def buscar(self, consulta: str, k: int = 4, minimo: float = 0.5) -> list[Fragmento]:
        q = set(tokens(consulta))
        if not q or not self.fragmentos:
            return []
        puntajes: list[tuple[float, int]] = []
        for i, c in enumerate(self.tf):
            s = 0.0
            for t in q:
                f = c.get(t)
                if f:
                    s += self.idf[t] * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * self.largo[i] / self.promedio))
            if s:
                puntajes.append((s * PESO.get(self.fragmentos[i].relevancia, 1.0), i))
        puntajes.sort(reverse=True)
        return [self.fragmentos[i] for s, i in puntajes[:k] if s >= minimo]


@lru_cache
def indice() -> Indice:
    if not RUTA.exists():
        return Indice([])
    fr = []
    with RUTA.open(encoding="utf-8") as f:
        for linea in f:
            d = json.loads(linea)
            fr.append(Fragmento(**{k: d.get(k, "") for k in Fragmento.__dataclass_fields__}))
    return Indice(fr)


# ¿La pregunta es sobre estos productos de pago? (detección sin modelo)
TEMA_CONSULTA = re.compile(r"\b(dimo|codi|spei|cobro digital|dinero m[oó]vil|cep|comprobante electr[oó]nico de pago)\b", re.I)
