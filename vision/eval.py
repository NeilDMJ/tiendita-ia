"""Evaluación con el conjunto de PRUEBA reservado (bases §7 y §13).

Produce en artefactos/<nombre>/eval/:
    metricas.json    exactitud top-1/top-5, precisión y exhaustividad por clase, matriz de confusión,
                     efecto del umbral de confianza y comparación con el modelo base
    val_test/        matriz de confusión (imagen) de Ultralytics
    aciertos/        ejemplos bien clasificados
    errores/         ejemplos mal clasificados (el nombre dice real -> predicho)

Cómo se calcula (para explicarlo al jurado):
  - Exactitud top-1 = fotos de test cuya clase más probable es la correcta / total de fotos de test.
  - Precisión de una clase = de las fotos que el modelo dijo "X", cuántas eran X.
  - Exhaustividad de una clase = de las fotos que eran X, cuántas reconoció como X.
  - Umbral de confianza: si la probabilidad es menor, la app pide al usuario confirmar el producto.

Uso:
    python eval.py --nombre v1
"""
import argparse
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from comun import AQUI, ARTEFACTOS, ahora, guardar_json

EXT_IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def imagenes_test(data: Path) -> list[tuple[Path, str]]:
    return [
        (img, d.name)
        for d in sorted((data / "test").iterdir()) if d.is_dir()
        for img in sorted(d.iterdir()) if img.suffix.lower() in EXT_IMG
    ]


def predecir(modelo, muestras, lote: int = 32):
    """Predice en lotes: pasar la lista completa a predict() la mete en UN solo batch (sin memoria en GPU)."""
    for i in range(0, len(muestras), lote):
        yield from modelo.predict([str(p) for p, _ in muestras[i:i + lote]], imgsz=224, verbose=False)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--data", type=Path, default=AQUI / "dataset")
    ap.add_argument("--umbral", type=float, default=0.6, help="confianza mínima para aceptar sin pedir confirmación")
    ap.add_argument("--ejemplos", type=int, default=12, help="máx. imágenes por carpeta aciertos/errores")
    args = ap.parse_args()

    from ultralytics import YOLO

    base = ARTEFACTOS / args.nombre
    salida = base / "eval"
    if salida.exists():
        shutil.rmtree(salida)
    modelo = YOLO(str(base / "best.pt"))
    nombres = modelo.names

    # 1) Métrica oficial de Ultralytics sobre test (+ imagen de la matriz de confusión)
    r = modelo.val(data=str(args.data), split="test", project=str(salida), name="val_test", plots=True)

    # 2) Predicción foto por foto: matriz de confusión, métricas por clase, ejemplos
    muestras = imagenes_test(args.data)
    (salida / "aciertos").mkdir(parents=True, exist_ok=True)
    (salida / "errores").mkdir(parents=True, exist_ok=True)
    matriz: dict[str, Counter] = defaultdict(Counter)
    confianzas = []  # (confianza, acierto)
    n_ok = n_err = 0
    for (img, real), res in zip(muestras, predecir(modelo, muestras)):
        pred = nombres[int(res.probs.top1)]
        conf = float(res.probs.top1conf)
        matriz[real][pred] += 1
        confianzas.append((conf, pred == real))
        if pred == real:
            n_ok += 1
            if n_ok <= args.ejemplos:
                res.save(filename=str(salida / "aciertos" / img.name))
        else:
            n_err += 1
            if n_err <= args.ejemplos:
                res.save(filename=str(salida / "errores" / f"{real}__como__{pred}__{conf:.2f}__{img.name}"))

    clases = list(nombres.values())
    por_clase = {}
    for c in clases:
        tp = matriz[c][c]
        reales = sum(matriz[c].values())
        predichas = sum(matriz[x][c] for x in clases)
        por_clase[c] = {
            "fotos_test": reales,
            "precision": round(tp / predichas, 4) if predichas else None,
            "exhaustividad": round(tp / reales, 4) if reales else None,
        }
    confusiones = Counter({f"{r_} -> {p}": n for r_ in clases for p, n in matriz[r_].items() if p != r_})

    seguras = [ok for conf, ok in confianzas if conf >= args.umbral]
    umbral = {
        "umbral": args.umbral,
        "fotos_aceptadas_sin_confirmar": f"{len(seguras)}/{len(confianzas)}",
        "exactitud_en_aceptadas": round(sum(seguras) / len(seguras), 4) if seguras else None,
        "fotos_que_piden_confirmacion": len(confianzas) - len(seguras),
    }

    # 3) Comparación con el modelo base (bases §13): ImageNet no tiene estos productos
    base_in = YOLO("yolo11n-cls.pt")
    vistas: dict[str, Counter] = defaultdict(Counter)
    for (img, real), res in zip(muestras, predecir(base_in, muestras)):
        vistas[real][base_in.names[int(res.probs.top1)]] += 1

    guardar_json(salida / "metricas.json", {
        "fecha": ahora(),
        "conjunto": "test (sesiones reservadas, no usadas en entrenamiento ni validación)",
        "fotos_test": len(muestras),
        "global": {"exactitud_top1": round(float(r.top1), 4), "exactitud_top5": round(float(r.top5), 4)},
        "por_clase": por_clase,
        "matriz_confusion": {c: dict(matriz[c]) for c in clases},
        "confusiones_mas_frecuentes": dict(confusiones.most_common(10)),
        "umbral_de_confianza": umbral,
        "comparacion_modelo_base": {
            "modelo": "yolo11n-cls.pt (ImageNet-1k, sin ajustar)",
            "comparable": False,
            "motivo": (
                "El modelo base clasifica en 1000 categorías genéricas de ImageNet (p. ej. 'pop bottle', "
                "'water bottle', 'packet'); no tiene nuestros productos, así que su exactitud sobre nuestras "
                "clases es 0 por definición. Se reporta qué categoría genérica asigna a cada producto para "
                "mostrar que, sin ajuste fino, no distingue productos con distinto precio."
            ),
            "prediccion_base_por_producto": {c: dict(vistas[c].most_common(3)) for c in clases},
        },
    })
    print(f"\nExactitud top-1 = {r.top1:.3f}   top-5 = {r.top5:.3f}")
    print(f"Con umbral {args.umbral}: {umbral['fotos_aceptadas_sin_confirmar']} aceptadas, "
          f"exactitud en ellas = {umbral['exactitud_en_aceptadas']}")
    if confusiones:
        print("Confusiones más frecuentes:", dict(confusiones.most_common(3)))
    print(f"Siguiente: python export_trt.py --nombre {args.nombre}")


if __name__ == "__main__":
    main()
