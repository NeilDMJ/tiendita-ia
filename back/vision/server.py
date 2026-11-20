"""Servidor FastAPI independiente para el módulo de visión (puerto 8001 por defecto).

Permite ejecutar el servicio de visión separado del enjambre de agentes (puerto 8000)
para evitar interferencias mientras se integra/configura el modelo `best.onnx`.

Uso:
    cd /home/m4r10/Documents/tiendita-ia/back
    ../enjambre_agentes/.venv/bin/python -m vision.server
    # o con puerto personalizado:
    VISION_PORT=8002 ../enjambre_agentes/.venv/bin/python -m vision.server
"""
from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router

VISION_HOST = os.environ.get("VISION_HOST", "0.0.0.0")
VISION_PORT = int(os.environ.get("VISION_PORT", "8001"))

app = FastAPI(
    title="Tiendita IA — Servicio de Visión",
    description="Clasificador de productos YOLO11n-cls (ONNX Runtime) en puerto dedicado.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app, host=VISION_HOST, port=VISION_PORT)
