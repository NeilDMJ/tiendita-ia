"""Base común: llamada al LLM (NIM/vLLM/API NVIDIA) y clase Agente.
Todos los agentes comparten el mismo modelo; cambian el prompt de rol y las herramientas."""
import json
import os
import re

import httpx

from . import registro


def llm_disponible() -> bool:
    return bool(os.getenv("LLM_URL") or os.getenv("NVIDIA_API_KEY"))


async def llamar_llm(system: str, user: str, max_tokens: int = 2048) -> tuple[str, str]:
    key = os.getenv("NVIDIA_API_KEY")  # nunca en el código ni en el repo
    base = os.getenv("LLM_URL") or "https://integrate.api.nvidia.com/v1"
    modelo = os.getenv("LLM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
    payload = {"model": modelo,
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
               "max_tokens": max_tokens, "reasoning_budget": 512, "temperature": 0.2}
    async with httpx.AsyncClient(timeout=60) as cli:
        r = await cli.post(f"{base}/chat/completions", json=payload,
                           headers={"Authorization": f"Bearer {key}"} if key else {})
        r.raise_for_status()
    return r.json()["choices"][0]["message"].get("content") or "", modelo


def extraer_json(texto: str):
    m = re.search(r"\{.*\}", texto or "", re.S)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


class Agente:
    def __init__(self, nombre: str, rol: str, tools: list[str], reglas):
        self.nombre, self.rol, self.tools, self.reglas = nombre, rol, tools, reglas

    def prompt(self, ctx: dict) -> str:
        herramientas = "\n".join("- " + registro.firma(t) for t in self.tools)
        carrito = ctx.get("carrito") or {}
        return (f"Eres el agente {self.nombre} de una tiendita en México. {self.rol}\n"
                'Responde SOLO con un JSON: {"tool": <nombre o null>, "args": {...}, '
                '"respuesta": "<texto breve en español>"}\n'
                f"Herramientas:\n{herramientas}\n"
                "Si faltan datos, tool=null y pídelos en \"respuesta\". "
                "Si piden algo que no es de tu rol, tool=null y explícalo.\n"
                f"Carrito actual: {json.dumps(carrito, ensure_ascii=False)}")

    async def proponer(self, texto: str, ctx: dict) -> dict:
        """Devuelve {tool, args, respuesta, motor}. Con LLM usa el modelo; si no hay o falla, reglas."""
        if llm_disponible():
            try:
                txt, modelo = await llamar_llm(self.prompt(ctx), texto)
                o = extraer_json(txt)
                if o is not None and (o.get("tool") is None or o["tool"] in registro.TOOLS):
                    return {"tool": o.get("tool"), "args": o.get("args") or {},
                            "respuesta": o.get("respuesta", ""), "motor": "llm", "modelo": modelo}
            except Exception:
                pass  # cae a reglas
        r = self.reglas(texto, ctx) or {"tool": None, "args": {}, "respuesta": "¿Me das más detalle?"}
        return {"motor": "reglas", "simulado": not llm_disponible(), **r}
