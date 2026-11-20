"""Ajuste fino (transfer learning) de YOLO11n-cls preentrenado en ImageNet a los productos de la tiendita.

Guarda en artefactos/<nombre>/:
    best.pt                  pesos entrenados (los que usa la app)
    registro.json            fecha, duración, GPU, versiones, parámetros, épocas, SHA-256  -> entregable C
    estadisticas_datos.json  cantidad y distribución de las fotos
    resultados/              curvas, results.csv y args.yaml de Ultralytics

Uso:
    python train.py --nombre humo --epochs 2   # prueba rápida antes de gastar GPU
    python train.py --nombre v1                # entrenamiento completo (~5-15 min en T4)
"""
import argparse
import shutil
import time
from pathlib import Path

from comun import AQUI, ARTEFACTOS, ahora, entorno, guardar_json, sha256

MODELO_BASE = {
    "nombre": "YOLO11n-cls (clasificación)",
    "archivo": "yolo11n-cls.pt",
    "procedencia": "Ultralytics, preentrenado en ImageNet-1k (1000 clases) — https://docs.ultralytics.com/tasks/classify/",
    "licencia": "AGPL-3.0",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=AQUI / "dataset", help="carpeta con train/ val/ test/")
    ap.add_argument("--modelo", default=MODELO_BASE["archivo"])
    ap.add_argument("--nombre", required=True, help="versión del modelo, ej. v1")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--batch", type=int, default=64, help="64 cabe holgado en una T4 de 16 GB a 224 px")
    ap.add_argument("--patience", type=int, default=10, help="corta si val no mejora en N épocas")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    from ultralytics import YOLO

    destino = ARTEFACTOS / args.nombre
    if destino.exists():
        raise SystemExit(f"{destino} ya existe: usa otro --nombre para no sobrescribir evidencia.")
    if not (args.data / "estadisticas.json").exists():
        raise SystemExit(f"{args.data} está incompleto o no existe: corre split.py primero (y que termine sin errores).")

    # En clasificación, con auto_augment (RandAugment, el valor por defecto) Ultralytics IGNORA hsv_*:
    # se apaga para que el ajuste de tono/saturación/brillo sí se aplique (las sesiones difieren en
    # balance de blancos). Probado: con RandAugment los pesos salían idénticos al cambiar hsv_*.
    aumentos = {"fliplr": 0.5, "flipud": 0.0, "hsv_h": 0.04, "hsv_s": 0.7, "hsv_v": 0.5, "erasing": 0.3,
                "auto_augment": None}
    inicio, t0 = ahora(), time.time()
    modelo = YOLO(args.modelo)
    modelo.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        seed=args.seed,
        deterministic=True,
        project=str(AQUI / "runs"),
        name=args.nombre,
        plots=True,
        # La luz y que la mano tape parte del producto varían mucho en la tienda; voltear de cabeza no aporta.
        **aumentos,
    )
    fin, duracion = ahora(), time.time() - t0

    trainer = modelo.trainer
    destino.mkdir(parents=True)
    best = destino / "best.pt"
    shutil.copy2(trainer.best, best)
    shutil.copytree(trainer.save_dir, destino / "resultados")
    shutil.copy2(args.data / "estadisticas.json", destino / "estadisticas_datos.json")

    guardar_json(destino / "registro.json", {
        "tarea": "clasificación de imágenes",
        "modelo_base": MODELO_BASE | {"archivo": args.modelo},
        "datos": str(args.data),
        "clases": list(modelo.names.values()) if isinstance(modelo.names, dict) else modelo.names,
        "parametros": vars(args) | aumentos,
        "inicio": inicio,
        "fin": fin,
        "duracion_min": round(duracion / 60, 1),
        "epocas_ejecutadas": trainer.epoch + 1,
        "mejor_fitness_val": float(trainer.best_fitness) if trainer.best_fitness is not None else None,
        "entorno": entorno(),
        "artefacto": {"ruta": str(best.relative_to(AQUI)), "sha256": sha256(best)},
    })
    print(f"\nListo en {duracion / 60:.1f} min. Siguiente: python eval.py --nombre {args.nombre}")


if __name__ == "__main__":
    main()
