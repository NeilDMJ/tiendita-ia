"""Paso 1: convierte los videos de cada producto en fotos clasificadas por carpeta.

El NOMBRE del video es la etiqueta, así que no hay que etiquetar a mano:
    videos/s1/s1_doritos_nacho.mp4   ->  raw/s1/doritos_nacho/s1_doritos_nacho_f00015.jpg ...
    videos/s1/s1_fondo.mp4           ->  raw/s1/fondo/...
    videos/s2/s2_chokis_2.mp4        ->  (un segundo video de la misma clase y sesión)

Qué hace con cada video:
  - Toma 1 cuadro cada --cada segundos (0.5 s por defecto: ~70 fotos de un video de 35 s).
  - Respeta la rotación del celular (video vertical sale vertical).
  - Descarta cuadros borrosos (varianza del Laplaciano < --nitidez).
  - Reduce el lado mayor a --lado px (YOLO-cls entrena a 224; 640 deja margen).
  - Las fotos se escriben sin metadatos (sin GPS ni modelo del celular, bases §10).
  - Es repetible: volver a correrlo sobrescribe los mismos archivos, no duplica.

Uso (en la laptop, no gasta GPU):
    pip install opencv-python
    python preparar_videos.py ~/Descargas/videos
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import cv2

AQUI = Path(__file__).resolve().parent
EXT_VID = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".3gp", ".webm"}
PATRON = re.compile(r"^(s\d+)_(.+?)(?:_(\d+))?$")
FONDO = "fondo"


def leer_clases(ruta: Path) -> list[str]:
    return [l.strip() for l in ruta.read_text().splitlines() if l.strip() and not l.startswith("#")]


def extraer(video: Path, destino: Path, cada: float, lado: int, nitidez: float) -> tuple[int, int, tuple[int, int]]:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir {video} (¿formato HEVC? exportar como H.264 / 'Más compatible')")
    if hasattr(cv2, "CAP_PROP_ORIENTATION_AUTO"):
        cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    paso = max(1, round(fps * cada))

    destino.mkdir(parents=True, exist_ok=True)
    i = guardadas = borrosas = 0
    tam = (0, 0)
    while cap.grab():
        if i % paso == 0:
            ok, cuadro = cap.retrieve()
            if ok:
                alto, ancho = cuadro.shape[:2]
                esc = lado / max(alto, ancho)
                if esc < 1:
                    cuadro = cv2.resize(cuadro, (round(ancho * esc), round(alto * esc)), interpolation=cv2.INTER_AREA)
                tam = (cuadro.shape[1], cuadro.shape[0])
                gris = cv2.cvtColor(cuadro, cv2.COLOR_BGR2GRAY)
                if cv2.Laplacian(gris, cv2.CV_64F).var() < nitidez:
                    borrosas += 1
                else:
                    cv2.imwrite(str(destino / f"{video.stem.lower()}_f{i:05d}.jpg"), cuadro,
                                [cv2.IMWRITE_JPEG_QUALITY, 92])
                    guardadas += 1
        i += 1
    cap.release()
    return guardadas, borrosas, tam


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", type=Path, help="carpeta con los videos (puede tener subcarpetas s1/, s2/...)")
    ap.add_argument("--salida", type=Path, default=AQUI / "raw")
    ap.add_argument("--clases", type=Path, default=AQUI / "clases.txt")
    ap.add_argument("--cada", type=float, default=0.5, help="segundos entre cuadros")
    ap.add_argument("--lado", type=int, default=640, help="lado mayor de las fotos en px")
    ap.add_argument("--nitidez", type=float, default=40.0, help="umbral de borrosidad; bájalo si descarta demasiado")
    args = ap.parse_args()

    validas = set(leer_clases(args.clases)) | {FONDO}
    videos = sorted(p for p in args.videos.rglob("*") if p.suffix.lower() in EXT_VID)
    if not videos:
        sys.exit(f"No encontré videos en {args.videos}")

    plan, malos = [], []
    for v in videos:
        m = PATRON.match(v.stem.lower())
        if m and m.group(2) in validas:
            plan.append((v, m.group(1), m.group(2)))
        else:
            malos.append(v.name)
    if malos:
        print("Videos con nombre inválido (se esperaba sN_<clase>.mp4):")
        for n in malos:
            print(f"  {n}")
        print(f"Clases válidas: {', '.join(sorted(validas))}")
        sys.exit("Renómbralos y vuelve a correr. No se extrajo nada.")

    total = Counter()
    fallidos = []
    for v, sesion, clase in plan:
        try:
            guardadas, borrosas, (w, h) = extraer(v, args.salida / sesion / clase, args.cada, args.lado, args.nitidez)
        except RuntimeError as e:
            fallidos.append(str(e))
            print(f"{v.name:<36}    ✗ no se pudo abrir")
            continue
        total[(sesion, clase)] += guardadas
        avisos = []
        if w > h and clase != FONDO:
            avisos.append("horizontal: ¿se grabó vertical? revisa que no salga girado")
        if guardadas + borrosas and borrosas / (guardadas + borrosas) > 0.4:
            avisos.append(f"{borrosas} borrosas descartadas: muévete más despacio o usa --nitidez más bajo")
        print(f"{v.name:<36} {guardadas:>4} fotos  {w}x{h}  {'  ⚠ ' + '; '.join(avisos) if avisos else ''}")

    sesiones = sorted({s for s, _ in total})
    clases = sorted(validas)
    print(f"\n{'clase':<22}" + "".join(f"{s:>7}" for s in sesiones))
    for c in clases:
        fila = [total.get((s, c), 0) for s in sesiones]
        aviso = "  ⚠ falta en alguna sesión" if 0 in fila else ""
        print(f"{c:<22}" + "".join(f"{n:>7}" for n in fila) + aviso)
    if fallidos:
        print(f"\n✗ {len(fallidos)} video(s) sin procesar:")
        for f in fallidos:
            print(f"  {f}")
        print("  Convertir a H.264: ffmpeg -i entrada.mp4 -c:v libx264 -crf 18 -an salida.mp4")
    print(f"\nFotos en {args.salida}. Revisa algunas carpetas y borra las que no sirvan.")
    print("Siguiente: python split.py --train s1,s2 --val s3 --test s4")


if __name__ == "__main__":
    main()
