"""Servicio de visión: expone el clasificador de productos (vision/artefactos/v1/best.onnx) a la app."""
from .router import router
from .server import VISION_HOST, VISION_PORT, app

__all__ = ["router", "app", "VISION_HOST", "VISION_PORT"]
