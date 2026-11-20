"""Endpoints de visión que consume la app (contrato: front/src/api/esquemas.ts).

    POST /vision/pos-checkout   foto del producto en el cobro -> {imagen_id, items}
    POST /vision/catalog-scan   foto para dar de alta / identificar -> {items, categoria}
    POST /vision/receipt-ocr    SIMULACIÓN etiquetada (el OCR de tickets no está entrenado)
    GET  /vision/salud          modelo cargado, clases, umbral y SHA-256 de los pesos (bases §6c)

El modelo clasifica UN producto por foto (cantidad = 1, sin caja). Si la confianza es menor que
VISION_UMBRAL (0.6 por defecto), el ítem se devuelve igual, con `requiere_confirmacion: true` y las
alternativas, para que la pantalla de revisión le pida al tendero confirmar o corregir (bases §6d).
La foto no se guarda: solo se procesa en memoria (bases §10).
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from .modelo import ImagenInvalida, Prediccion, clasificador

router = APIRouter(prefix="/vision", tags=["Visión"])

UMBRAL = float(os.environ.get("VISION_UMBRAL", "0.6"))
MAX_BYTES = 15 * 1024 * 1024
FONDO = "fondo"
CATALOGO: dict[str, dict[str, Any]] = {
    k: v for k, v in json.loads((Path(__file__).parent / "catalogo_vision.json").read_text()).items() if not k.startswith("_")
}


def _producto(clase: str) -> dict[str, Any]:
    p = CATALOGO.get(clase)
    if p is None:  # clase del modelo sin producto en el catálogo: que el tendero lo capture
        return {"sku": None, "nombre": clase.replace("_", " ").capitalize(), "precio_unitario": None, "categoria": None}
    return p


def _items(pred: Prediccion) -> list[dict[str, Any]]:
    if pred.clase == FONDO:
        return []  # no hay producto en la foto: la app muestra el estado vacío
    p = _producto(pred.clase)
    return [{
        "sku": p["sku"],
        "nombre": p["nombre"],
        "cantidad": 1,
        "precio_unitario": p["precio_unitario"],
        "confianza": pred.confianza,
        "requiere_confirmacion": pred.confianza < UMBRAL,
        "alternativas": [
            {"sku": _producto(c)["sku"], "nombre": _producto(c)["nombre"], "confianza": conf}
            for c, conf in pred.top[1:] if c != FONDO and conf >= 0.01
        ],
    }]


async def _predecir(imagen: UploadFile) -> Prediccion:
    datos = await imagen.read()
    if len(datos) > MAX_BYTES:
        raise HTTPException(413, {"detalle": "La foto pesa más de 15 MB."})
    try:
        return await run_in_threadpool(clasificador().predecir, datos)
    except ImagenInvalida as e:
        raise HTTPException(422, {"detalle": f"No se pudo leer la imagen ({e})."}) from e


@router.post("/pos-checkout", summary="Identifica el producto de la foto para cobrarlo")
async def pos_checkout(imagen: UploadFile = File(..., description="Foto JPG/PNG del producto")) -> dict[str, Any]:
    pred = await _predecir(imagen)
    return {"imagen_id": uuid.uuid4().hex, "items": _items(pred), "clase_modelo": pred.clase}


@router.post("/catalog-scan", summary="Identifica el producto para darlo de alta o consultarlo")
async def catalog_scan(imagen: UploadFile = File(...)) -> dict[str, Any]:
    pred = await _predecir(imagen)
    items = _items(pred)
    categoria = _producto(pred.clase).get("categoria") if items else None
    return {"items": items, **({"categoria": categoria} if categoria else {}), "caducidad_ocr": None}


@router.post("/receipt-ocr", summary="SIMULACIÓN: lectura de tickets (no hay modelo de OCR entrenado)")
async def receipt_ocr(imagen: UploadFile = File(...)) -> dict[str, Any]:
    await imagen.read()
    return {
        "simulacion": True,
        "aviso": "Datos simulados: el OCR de tickets no forma parte del modelo entrenado.",
        "fecha": None,
        "proveedor": "Proveedor de ejemplo (simulado)",
        "total": 150.0,
        "conceptos": [{"descripcion": "Agua Bonafont 1 L x10 (simulado)", "monto": 150.0}],
        "tipo": "compra",
        "confianza": 0.0,
    }


@router.get("/salud", summary="Estado del modelo de visión y huella de los pesos")
def salud() -> dict[str, Any]:
    try:
        c = clasificador()
    except Exception as e:  # noqa: BLE001 - se reporta, no se oculta
        raise HTTPException(503, {"detalle": f"Modelo no disponible: {e}"}) from e
    return {
        "estado": "ok",
        "tarea": "clasificación de un producto por foto (YOLO11n-cls)",
        "clases": c.clases,
        "umbral_confirmacion": UMBRAL,
        "catalogo": {k: v["sku"] for k, v in CATALOGO.items()},
        "modelo": c.meta,
    }
