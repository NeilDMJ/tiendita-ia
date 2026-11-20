"""Divide las fotos en train/val/test POR SESIÓN (clasificación: una carpeta por clase).

Entrada (lo que genera preparar_videos.py):
    raw/<sesion>/<clase>/*.jpg

Salida (formato de clasificación de Ultralytics):
    dataset/{train,val,test}/<clase>/*.jpg
    dataset/estadisticas.json     (cantidad y distribución -> entregable C y sección 13)

Bases §7: "No deberán colocarse imágenes duplicadas ni versiones de la misma imagen en
conjuntos distintos". Por eso una sesión completa va a un solo conjunto, y además se buscan
fotos casi idénticas entre conjuntos (hash perceptual).

Uso:
    python split.py --train s1,s2 --val s3 --test s4   # 4 sesiones: cada conjunto con las suyas
    python split.py --train s1 --test s2                # 2 sesiones: val sale de train (ver abajo)

Sin --val, la validación se toma del FINAL de cada video de las sesiones de train
(--val-frac, 20 % por defecto) y se descartan --hueco cuadros entre ambos tramos para que no
queden fotos casi iguales a los dos lados. Val solo se usa para elegir la mejor época; la
métrica que se reporta sale de test, que sigue siendo una sesión completa que el modelo no vio.
"""
import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).resolve().parent
EXT_IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SPLITS = ("train", "val", "test")
FONDO = "fondo"


def leer_clases(ruta: Path) -> list[str]:
    return [l.strip() for l in ruta.read_text().splitlines() if l.strip() and not l.startswith("#")]


def dhash(ruta: Path) -> int:
    """Hash perceptual de 64 bits: resiste cambios de tamaño, compresión y brillo leve."""
    with Image.open(ruta) as im:
        px = im.convert("L").resize((9, 8), Image.Resampling.LANCZOS).tobytes()
    bits = 0
    for fila in range(8):
        for col in range(8):
            bits = (bits << 1) | (px[fila * 9 + col] > px[fila * 9 + col + 1])
    return bits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=AQUI / "raw")
    ap.add_argument("--out", type=Path, default=AQUI / "dataset")
    ap.add_argument("--clases", type=Path, default=AQUI / "clases.txt")
    ap.add_argument("--train", required=True, help="sesiones separadas por coma, ej. s1,s2")
    ap.add_argument("--val", default="", help="sesiones de val; vacío = tramo final de cada video de train")
    ap.add_argument("--test", required=True)
    ap.add_argument("--val-frac", type=float, default=0.2, help="sin --val: fracción final de cada video que va a val")
    ap.add_argument("--hueco", type=int, default=4, help="sin --val: cuadros descartados entre el tramo de train y el de val")
    ap.add_argument("--umbral-dup", type=int, default=4, help="distancia de Hamming máx. para considerar duplicado")
    ap.add_argument("--permitir-dup", action="store_true", help="solo avisar de duplicados entre conjuntos")
    args = ap.parse_args()

    clases = leer_clases(args.clases) + [FONDO]
    asignacion: dict[str, str] = {}
    for split in SPLITS:
        for s in filter(None, getattr(args, split).split(",")):
            if s in asignacion:
                sys.exit(f"ERROR: la sesión {s} está en '{asignacion[s]}' y en '{split}'. Debe ir a un solo conjunto.")
            asignacion[s] = split

    if args.out.exists():
        shutil.rmtree(args.out)
    for split in SPLITS:
        for c in clases:
            (args.out / split / c).mkdir(parents=True)

    val_de_train = not args.val.strip()
    conteo = {s: Counter() for s in SPLITS}
    hashes: dict[str, list[tuple[int, Path]]] = {s: [] for s in SPLITS}
    descartadas_hueco = 0

    def copiar(img: Path, split: str, sesion: str, c: str) -> None:
        shutil.copy2(img, args.out / split / c / f"{sesion}__{img.name}")
        conteo[split][c] += 1
        hashes[split].append((dhash(img), img))

    for sesion, split in asignacion.items():
        dir_ses = args.raw / sesion
        if not dir_ses.is_dir():
            sys.exit(f"ERROR: no existe {dir_ses}")
        extranas = [d.name for d in dir_ses.iterdir() if d.is_dir() and d.name not in clases]
        if extranas:
            sys.exit(f"ERROR: carpetas que no son clases en {dir_ses}: {extranas}. Clases válidas: {clases}")
        for c in clases:
            dir_c = dir_ses / c
            if not dir_c.is_dir():
                continue
            imgs = sorted(p for p in dir_c.iterdir() if p.suffix.lower() in EXT_IMG)
            if not (val_de_train and split == "train"):
                for img in imgs:
                    copiar(img, split, sesion, c)
                continue
            # Agrupar por video (nombre antes de "_fNNNNN") y cortar cada uno en el tiempo.
            por_video: dict[str, list[Path]] = {}
            for img in imgs:
                por_video.setdefault(img.stem.rsplit("_f", 1)[0], []).append(img)
            for cuadros in por_video.values():
                n_val = round(len(cuadros) * args.val_frac)
                corte = len(cuadros) - n_val
                for img in cuadros[:max(0, corte - args.hueco)]:
                    copiar(img, "train", sesion, c)
                for img in cuadros[corte:]:
                    copiar(img, "val", sesion, c)
                descartadas_hueco += min(args.hueco, corte)

    # Sin --val, val y train salen del mismo video: si el producto estuvo quieto, hay cuadros
    # casi iguales a los dos lados. Esos se quitan de val (no se aborta: es esperable).
    quitadas_val = 0
    if val_de_train:
        h_train = [h for h, _ in hashes["train"]]
        quedan = []
        for hv, pv in hashes["val"]:
            if any(bin(hv ^ ht).count("1") <= args.umbral_dup for ht in h_train):
                (args.out / "val" / pv.parent.name / f"{pv.parent.parent.name}__{pv.name}").unlink()
                conteo["val"][pv.parent.name] -= 1
                quitadas_val += 1
            else:
                quedan.append((hv, pv))
        hashes["val"] = quedan
        if quitadas_val:
            print(f"Quitadas {quitadas_val} fotos de val casi iguales a otras de train (mismo video).")

    # Duplicados casi idénticos entre conjuntos distintos
    dups = []
    for a_i, a in enumerate(SPLITS):
        for b in SPLITS[a_i + 1:]:
            for ha, pa in hashes[a]:
                for hb, pb in hashes[b]:
                    if bin(ha ^ hb).count("1") <= args.umbral_dup:
                        dups.append((a, pa, b, pb))
    if dups:
        print(f"\n⚠ {len(dups)} posibles duplicados entre conjuntos distintos:")
        for a, pa, b, pb in dups[:30]:
            print(f"  [{a}] {pa}  ~  [{b}] {pb}")
        if not args.permitir_dup:
            shutil.rmtree(args.out)  # no dejar un dataset a medias que train.py pueda usar por error
            sys.exit("Quita esas fotos de una de las sesiones (o revísalas a mano y usa --permitir-dup).")

    stats = {
        "tarea": "clasificación de imágenes (un producto por foto)",
        "sesiones": asignacion,
        "validacion": (
            f"último {args.val_frac:.0%} de cada video de las sesiones de train; "
            f"{descartadas_hueco} cuadros descartados como hueco ({args.hueco} por video); "
            f"{quitadas_val} fotos de val quitadas por ser casi iguales a una de train"
            if val_de_train else "sesiones propias"
        ),
        "imagenes_por_conjunto": {s: sum(conteo[s].values()) for s in SPLITS},
        "imagenes_por_clase": {s: {c: conteo[s].get(c, 0) for c in clases} for s in SPLITS},
        "duplicados_entre_conjuntos": len(dups),
        "origen": "cuadros extraídos de videos grabados por el equipo (preparar_videos.py)",
    }
    (args.out / "estadisticas.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))

    print(f"\n{'clase':<22}{'train':>7}{'val':>7}{'test':>7}")
    for c in clases:
        fila = [conteo[s].get(c, 0) for s in SPLITS]
        aviso = "  ⚠ sin fotos en algún conjunto" if 0 in fila else ""
        print(f"{c:<22}{fila[0]:>7}{fila[1]:>7}{fila[2]:>7}{aviso}")
    print(f"{'TOTAL':<22}" + "".join(f"{sum(conteo[s].values()):>7}" for s in SPLITS))
    print(f"\nListo: {args.out}")


if __name__ == "__main__":
    main()
