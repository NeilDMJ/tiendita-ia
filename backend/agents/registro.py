"""Registro común de herramientas: TOOL -> (agente, lectura/escritura, esquema, función)."""
from dataclasses import dataclass
from typing import Callable


@dataclass
class Tool:
    nombre: str
    agente: str
    escribe: bool          # True = requiere confirmación del vendedor antes de ejecutar
    esquema: dict
    requeridos: list
    fn: Callable           # fn(args: dict, ctx: dict) -> dict con al menos {"ok": True, "texto": str}


TOOLS: dict[str, Tool] = {}


def tool(agente: str, escribe: bool, esquema: dict, requeridos=()):
    def deco(fn):
        TOOLS[fn.__name__] = Tool(fn.__name__, agente, escribe, esquema, list(requeridos), fn)
        return fn
    return deco


def validar(nombre: str, args: dict) -> list[str]:
    """Lista de errores/faltantes (vacía si la llamada es válida)."""
    t = TOOLS.get(nombre)
    if not t:
        return [f"herramienta desconocida: {nombre}"]
    errs = [f"falta {k}" for k in t.requeridos if args.get(k) is None]
    for k, v in args.items():
        if k not in t.esquema:
            errs.append(f"argumento no permitido: {k}")
        elif v is not None and not isinstance(v, t.esquema[k]):
            errs.append(f"tipo inválido en {k}")
    return errs


def ejecutar(nombre: str, args: dict, ctx: dict | None = None) -> dict:
    errs = validar(nombre, args)
    if errs:
        raise ValueError("; ".join(errs))
    return TOOLS[nombre].fn(args, ctx if ctx is not None else {})


def firma(nombre: str) -> str:
    t = TOOLS[nombre]
    return f"{nombre}(" + ", ".join(k if k in t.requeridos else k + "?" for k in t.esquema) + ")"
