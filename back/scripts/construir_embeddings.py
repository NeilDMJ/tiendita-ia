"""Calcula los embeddings de los fragmentos (una sola vez) y los guarda en app/datos/embeddings.npz.

Uso (desde back/):  .venv/Scripts/python -X utf8 scripts/construir_embeddings.py [modelo]
Requiere NVIDIA_API_KEY en back/.env. El servicio de NVIDIA a veces responde 503: se reintenta.
Solo se envían textos públicos de Banco de México (nada de usuarios).
"""
import json
import sys
import time
from pathlib import Path

import httpx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import get_settings  # noqa: E402
from app.conocimiento import RUTA, SALIDA_EMBEDDINGS  # noqa: E402

LOTE = 16


def embeber(cliente: httpx.Client, s, modelo: str, textos: list[str], tipo: str) -> list[list[float]]:
    for intento in range(8):
        try:
            r = cliente.post(
                f"{s.nim_base_url}/embeddings",
                headers={"Authorization": f"Bearer {s.nvidia_api_key}"},
                json={"model": modelo, "input": textos, "input_type": tipo, "encoding_format": "float", "truncate": "END"},
            )
            if r.status_code == 200:
                return [d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"])]
            print(f"  HTTP {r.status_code}, reintento {intento + 1}", flush=True)
        except httpx.HTTPError as e:
            print(f"  {type(e).__name__}, reintento {intento + 1}", flush=True)
        time.sleep(2 + intento * 2)
    raise SystemExit("El servicio de embeddings no respondió; prueba más tarde o con otro modelo.")


def main() -> None:
    s = get_settings()
    modelo = sys.argv[1] if len(sys.argv) > 1 else s.embed_model
    filas = [json.loads(linea) for linea in RUTA.open(encoding="utf-8")]
    textos = [f"{f['titulo']}. {f['seccion']}. {f['texto']}"[:3000] for f in filas]
    vectores: list[list[float]] = []
    with httpx.Client(timeout=60) as cliente:
        for i in range(0, len(textos), LOTE):
            vectores += embeber(cliente, s, modelo, textos[i : i + LOTE], "passage")
            print(f"{len(vectores)}/{len(textos)}", flush=True)
    m = np.asarray(vectores, dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    np.savez_compressed(SALIDA_EMBEDDINGS, v=m.astype(np.float16), ids=np.array([f["id"] for f in filas]), modelo=modelo)
    print("Guardado", SALIDA_EMBEDDINGS, m.shape)


if __name__ == "__main__":
    main()
