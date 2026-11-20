"""Servicio de visión: expone el clasificador de productos (vision/artefactos/v1/best.onnx) a la app."""
from .router import router

__all__ = ["router"]
