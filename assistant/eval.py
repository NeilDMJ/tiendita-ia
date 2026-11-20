"""Evalúa un modelo (OpenAI-compatible) contra assistant/data/test.jsonl.

Métricas por ejemplo:
  json_valido   -> la salida contiene un JSON con las llaves tool/args/respuesta
  tool_correcta -> tool igual a la esperada (incluye null cuando falta info / fuera de alcance)
  args_correctos-> tool correcta Y argumentos equivalentes (None ignorado, números por valor,
                   textos sin mayúsculas/espacios extra)
La 'respuesta' en texto no se puntúa automáticamente (revisar a mano unos ejemplos).

Ejemplos:
  # Baseline (modelo base hospedado). Llave por variable de entorno, nunca en el código:
  set NVIDIA_API_KEY=...        (PowerShell: $env:NVIDIA_API_KEY="...")
  python -I assistant/eval.py --model nvidia/nemotron-3-nano-omni-30b-a3b-reasoning --out assistant/results/base.json
  # Modelo ajustado servido en el servidor del concurso:
  python -I assistant/eval.py --base-url http://SERVIDOR:8000/v1 --model mi-lora --out assistant/results/lora.json
  # Comparar:
  python -I assistant/eval.py --compare assistant/results/base.json assistant/results/lora.json
  # Probar el evaluador sin red (modelo "oráculo"):
  python -I assistant/eval.py --selftest
"""
import argparse
import json
import os
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).parent


def cargar(split="test", limit=None):
    rows = [json.loads(l) for l in open(AQUI / "data" / f"{split}.jsonl", encoding="utf-8")]
    return rows[:limit] if limit else rows


def parsear(texto):
    m = re.search(r"\{.*\}", texto or "", re.S)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) and {"tool", "args", "respuesta"} <= o.keys() else None


def norm(v):
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        return " ".join(v.lower().split())
    return v


def args_iguales(a, b):
    a = {k: norm(v) for k, v in (a or {}).items() if v is not None}
    b = {k: norm(v) for k, v in (b or {}).items() if v is not None}
    return a == b


def puntuar(esperado, salida_texto):
    o = parsear(salida_texto)
    if o is None:
        return {"json_valido": 0, "tool_correcta": 0, "args_correctos": 0}
    tool_ok = o.get("tool") == esperado["tool"]
    args_ok = tool_ok and isinstance(o.get("args") or {}, dict) and args_iguales(o.get("args"), esperado["args"])
    return {"json_valido": 1, "tool_correcta": int(tool_ok), "args_correctos": int(args_ok)}


def llamar(base_url, key, model, messages, reintentos=3):
    import httpx
    payload = {"model": model, "messages": messages, "max_tokens": 2048, "temperature": 0.0}
    if "integrate.api.nvidia.com" in base_url:
        payload["reasoning_budget"] = 512  # mismo valor que backend/main.py
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    for i in range(reintentos):
        try:
            r = httpx.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120)
            r.raise_for_status()
            return r.json()["choices"][0]["message"].get("content") or ""
        except Exception as e:  # red, 429, 5xx
            err = str(e)
            time.sleep(2 * (i + 1))
    return f"__ERROR__ {err}"


def evaluar(rows, generar, workers=4):
    def uno(r):
        msgs, gold = r["messages"][:2], json.loads(r["messages"][2]["content"])
        salida = generar(msgs)
        return {"categoria": r["categoria"], "usuario": msgs[1]["content"], "esperado": gold,
                "salida": salida, **puntuar(gold, salida)}
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(uno, rows))


def resumen(res):
    n = len(res)
    tot = {m: sum(r[m] for r in res) / n for m in ("json_valido", "tool_correcta", "args_correctos")}
    por_cat = defaultdict(list)
    for r in res:
        por_cat[r["categoria"]].append(r["args_correctos"])
    return {"n": n, **tot, "por_categoria": {c: sum(v) / len(v) for c, v in sorted(por_cat.items())}}


def mostrar(nombre, s):
    print(f"\n== {nombre} (n={s['n']}) ==")
    print(f"JSON válido {s['json_valido']:.1%} | tool correcta {s['tool_correcta']:.1%} | "
          f"args correctos {s['args_correctos']:.1%}")
    for c, v in s["por_categoria"].items():
        print(f"  {c:22s} {v:.0%}")


def comparar(a, b):
    sa, sb = (json.load(open(p, encoding="utf-8"))["resumen"] for p in (a, b))
    print(f"{'métrica':22s} {'base':>8s} {'ajustado':>9s}")
    for m in ("json_valido", "tool_correcta", "args_correctos"):
        print(f"{m:22s} {sa[m]:8.1%} {sb[m]:9.1%}")
    for c in sa["por_categoria"]:
        print(f"  {c:20s} {sa['por_categoria'][c]:8.0%} {sb['por_categoria'].get(c, 0):9.0%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://integrate.api.nvidia.com/v1")
    ap.add_argument("--model", default="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out")
    ap.add_argument("--compare", nargs=2, metavar=("BASE", "AJUSTADO"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.compare:
        return comparar(*a.compare)
    rows = cargar(a.split, a.limit)

    if a.selftest:  # el oráculo debe sacar 100 %; una salida rota, 0 %
        gold = {r["messages"][1]["content"]: r["messages"][2]["content"] for r in rows}
        mostrar("oráculo", resumen(evaluar(rows, lambda m: gold[m[1]["content"]])))
        mostrar("salida inválida", resumen(evaluar(rows, lambda m: "no sé")))
        return

    key = os.getenv("NVIDIA_API_KEY")
    if "integrate.api.nvidia.com" in a.base_url and not key:
        raise SystemExit("Define NVIDIA_API_KEY en el entorno (no la pongas en el código).")
    res = evaluar(rows, lambda m: llamar(a.base_url, key, a.model, m), a.workers)
    s = resumen(res)
    mostrar(a.model, s)
    errores = sum(r["salida"].startswith("__ERROR__") for r in res)
    if errores:
        print(f"\nAVISO: {errores} llamadas fallaron (cuentan como fallos); revisa red/cuota.")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        json.dump({"modelo": a.model, "base_url": a.base_url, "split": a.split, "resumen": s,
                   "ejemplos": res}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Guardado en", a.out)


if __name__ == "__main__":
    main()
