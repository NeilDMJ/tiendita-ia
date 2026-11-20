"""Optimización con NVIDIA TensorRT (bases §9: herramienta NVIDIA para optimizar/desplegar).

Exporta best.pt -> best.onnx -> best.engine (FP16) y compara PyTorch vs TensorRT con las MISMAS
fotos de test: latencia, FPS y exactitud. Demuestra que la optimización acelera sin perder precisión.

Produce en artefactos/<nombre>/:
    best.onnx        formato intermedio (también sirve de respaldo en CPU con onnxruntime)
    best.engine      motor TensorRT FP16 — es el que carga el backend en la demo
    benchmark.json   tabla comparativa + SHA-256 de cada artefacto

IMPORTANTE: un .engine solo corre en el mismo modelo de GPU y la misma versión de TensorRT con
que se construyó (aquí: Tesla T4 del entorno DLI). Si cambian de GPU, regenerarlo desde best.onnx.

Uso:
    python export_trt.py --nombre v1
"""
import argparse
import shutil
import statistics
from pathlib import Path

from comun import AQUI, ARTEFACTOS, ahora, entorno, guardar_json, sha256

EXT_IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def medir(modelo, muestras: list[tuple[str, str]], imgsz: int, calentamiento: int = 10) -> dict:
    """Latencia y exactitud foto por foto (una a la vez, como llega desde la cámara del celular)."""
    for p, _ in muestras[:calentamiento]:
        modelo.predict(p, imgsz=imgsz, verbose=False)
    inf, total, aciertos = [], [], 0
    for p, real in muestras:
        res = modelo.predict(p, imgsz=imgsz, verbose=False)[0]
        s = res.speed
        inf.append(s["inference"])
        total.append(s["preprocess"] + s["inference"] + s["postprocess"])
        aciertos += modelo.names[int(res.probs.top1)] == real
    inf_ord = sorted(inf)
    return {
        "inferencia_ms_media": round(statistics.mean(inf), 2),
        "inferencia_ms_p95": round(inf_ord[max(0, int(len(inf_ord) * 0.95) - 1)], 2),
        "total_ms_media": round(statistics.mean(total), 2),
        "fps_inferencia": round(1000 / statistics.mean(inf), 1),
        "exactitud_top1": round(aciertos / len(muestras), 4),
        "fotos": len(muestras),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--data", type=Path, default=AQUI / "dataset")
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--max-fotos", type=int, default=400)
    args = ap.parse_args()

    from ultralytics import YOLO

    base = ARTEFACTOS / args.nombre
    pt = base / "best.pt"

    onnx = Path(YOLO(str(pt)).export(format="onnx", imgsz=args.imgsz, simplify=True))
    engine = Path(YOLO(str(pt)).export(format="engine", imgsz=args.imgsz, half=True, device=0))
    for f in (onnx, engine):
        if f.parent != base:
            shutil.move(f, base / f.name)
    onnx, engine = base / onnx.name, base / engine.name

    muestras = [
        (str(img), d.name)
        for d in sorted((args.data / "test").iterdir()) if d.is_dir()
        for img in sorted(d.iterdir()) if img.suffix.lower() in EXT_IMG
    ]
    # Submuestra repartida entre clases para no tardar de más
    paso = max(1, len(muestras) // args.max_fotos)
    muestras = muestras[::paso]

    filas = {}
    for etiqueta, ruta in (("PyTorch FP32 (best.pt)", pt), ("TensorRT FP16 (best.engine)", engine)):
        filas[etiqueta] = medir(YOLO(str(ruta), task="classify"), muestras, args.imgsz)

    a, b = filas.values()
    aceleracion = round(a["inferencia_ms_media"] / b["inferencia_ms_media"], 2)

    guardar_json(base / "benchmark.json", {
        "fecha": ahora(),
        "herramienta_nvidia": "TensorRT — compila el grafo ONNX a un motor optimizado para la GPU "
                              "(fusión de capas, precisión FP16 con Tensor Cores, selección de kernels)",
        "entorno": entorno(),
        "resultados": filas,
        "aceleracion_inferencia_x": aceleracion,
        "artefactos": {f.name: sha256(f) for f in (pt, onnx, engine)},
    })

    print("\n| Modelo | Inferencia (ms) | FPS | Exactitud top-1 |\n|---|---|---|---|")
    for k, v in filas.items():
        print(f"| {k} | {v['inferencia_ms_media']} | {v['fps_inferencia']} | {v['exactitud_top1']} |")
    print(f"\nTensorRT es {aceleracion}x más rápido en inferencia.")


if __name__ == "__main__":
    main()
