"""Clasificador de productos: carga best.onnx (YOLO11n-cls entrenado en NVIDIA DLI) con onnxruntime.

Se usa ONNX y no el .engine de TensorRT porque el .engine solo corre en la GPU y la versión de
TensorRT con que se construyó (Tesla T4 del DLI). ONNX corre en CPU en cualquier laptop (~5 ms/foto)
y usa CUDA si onnxruntime-gpu está instalado.

Preprocesamiento idéntico al de Ultralytics para clasificación (classify_transforms):
RGB -> lado corto a 224 (bilineal) -> recorte central 224x224 -> [0, 1] (media 0, desviación 1).
"""
from __future__ import annotations

import ast
import hashlib
import io
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps, UnidentifiedImageError

RAIZ = Path(__file__).resolve().parents[2]
RUTA_MODELO = Path(os.environ.get("VISION_MODELO", RAIZ / "vision/artefactos/v1/best.onnx"))
LADO = 224


class ImagenInvalida(ValueError):
    """La foto no se pudo abrir o está vacía."""


@dataclass(frozen=True)
class Prediccion:
    clase: str
    confianza: float
    top: list[tuple[str, float]]  # las 3 más probables, de mayor a menor


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


class Clasificador:
    def __init__(self, ruta: Path = RUTA_MODELO):
        if not ruta.exists():
            raise FileNotFoundError(f"No existe el modelo {ruta}. Descomprime artefactos_v1 en vision/artefactos/.")
        self.ruta = ruta
        proveedores = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in ort.get_available_providers()]
        self.sesion = ort.InferenceSession(str(ruta), providers=proveedores)
        self.entrada = self.sesion.get_inputs()[0].name
        meta = self.sesion.get_modelmeta().custom_metadata_map
        nombres = ast.literal_eval(meta["names"])  # "{0: 'agua_1l', ...}" escrito por Ultralytics
        self.clases = [nombres[i] for i in sorted(nombres)]
        self.meta = {
            "archivo": str(ruta.relative_to(RAIZ)) if ruta.is_relative_to(RAIZ) else str(ruta),
            "sha256_onnx": _sha256(ruta),
            "ultralytics": meta.get("version"),
            "exportado": meta.get("date"),
            "proveedor": self.sesion.get_providers()[0],
        }
        pt = ruta.with_suffix(".pt")
        if pt.exists():  # el SHA-256 de best.pt es el que aparece en registro.json (bases §6c)
            self.meta["sha256_pt"] = _sha256(pt)

    @staticmethod
    def preprocesar(datos: bytes) -> np.ndarray:
        if not datos:
            raise ImagenInvalida("archivo vacío")
        try:
            img = Image.open(io.BytesIO(datos))
            img = ImageOps.exif_transpose(img).convert("RGB")  # fotos de celular: respetar la rotación
        except (UnidentifiedImageError, OSError) as e:
            raise ImagenInvalida(str(e)) from e
        ancho, alto = img.size
        esc = LADO / min(ancho, alto)
        img = img.resize((max(LADO, round(ancho * esc)), max(LADO, round(alto * esc))), Image.Resampling.BILINEAR)
        ancho, alto = img.size
        izq, arr = (ancho - LADO) // 2, (alto - LADO) // 2
        img = img.crop((izq, arr, izq + LADO, arr + LADO))
        x = np.asarray(img, dtype=np.float32) / 255.0
        return x.transpose(2, 0, 1)[None]  # (1, 3, 224, 224)

    def predecir(self, datos: bytes) -> Prediccion:
        salida = self.sesion.run(None, {self.entrada: self.preprocesar(datos)})[0][0]
        probs = salida if abs(float(salida.sum()) - 1) < 1e-3 else np.exp(salida - salida.max()) / np.exp(salida - salida.max()).sum()
        orden = np.argsort(probs)[::-1]
        top = [(self.clases[i], round(float(probs[i]), 4)) for i in orden[:3]]
        return Prediccion(clase=top[0][0], confianza=top[0][1], top=top)


@lru_cache(maxsize=1)
def clasificador() -> Clasificador:
    """Se carga una sola vez por proceso (la primera petición o el arranque de la API)."""
    return Clasificador()
