"""
Cliente multimodal real para NVIDIA NIM Vision en Tiendita IA.
Procesa imágenes reales desde disco o API (base64) sin datos simulados:
  - Escaneo de catálogo (/catalog-scan / catalog)
  - Identificación en mostrador POS (/pos-checkout / pos)
  - OCR y clasificación contable de comprobantes (/receipt-ocr / ticket)
"""
from __future__ import annotations

import json
from typing import Optional, Tuple

import httpx
from langchain_core.tools import tool

from config.keys import NVIDIA_API_KEY, NVIDIA_BASE_URL

# Modelos Vision-Language reales disponibles en NVIDIA NIM (en orden de preferencia)
VISION_NIM_MODELS = [
    "nvidia/nemotron-3.5-super-vl-120b-a12b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "google/gemma-3-12b-it",
]

# Buffer en memoria de la imagen activa del turno actual (evita truncar base64 largo en prompts)
_ACTIVE_VISION_IMAGE: Tuple[Optional[str], str] = (None, "image/jpeg")


def set_active_vision_image(image_b64: Optional[str], mime_type: str = "image/jpeg") -> None:
    """Registra la imagen real en base64 para que las herramientas NIM Vision la consuman directamente."""
    global _ACTIVE_VISION_IMAGE
    _ACTIVE_VISION_IMAGE = (image_b64, mime_type or "image/jpeg")


def clear_active_vision_image() -> None:
    """Limpia la imagen activa al concluir la operación multimodal."""
    global _ACTIVE_VISION_IMAGE
    _ACTIVE_VISION_IMAGE = (None, "image/jpeg")


def _resolver_imagen(image_b64: Optional[str]) -> Tuple[Optional[str], str]:
    """Usa la imagen activa cargada desde disco si el LLM pasa un marcador o cadena corta."""
    active_b64, active_mime = _ACTIVE_VISION_IMAGE
    if active_b64 and (not image_b64 or len(image_b64.strip()) < 64):
        return active_b64, active_mime
    if image_b64 and len(image_b64.strip()) >= 64:
        return image_b64.strip(), active_mime
    return None, active_mime


def _call_nim_vision_endpoint(prompt: str, image_b64: str, mime_type: str = "image/jpeg") -> str:
    """Llama en vivo a la API de NVIDIA NIM Vision con reintento entre modelos VL activos."""
    if not NVIDIA_API_KEY or NVIDIA_API_KEY.startswith("tu_"):
        return json.dumps({
            "status": "error",
            "message": "NVIDIA_API_KEY no está configurada para ejecutar NIM Vision.",
        }, ensure_ascii=False)

    real_b64, real_mime = _resolver_imagen(image_b64)
    if not real_b64:
        return json.dumps({
            "status": "error",
            "message": "No se recibió una imagen real válida en base64 para analizar.",
        }, ensure_ascii=False)

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
    ultimo_error = "Sin respuesta de NIM Vision."

    with httpx.Client(timeout=45.0) as client:
        for model_id in VISION_NIM_MODELS:
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{real_mime};base64,{real_b64}"},
                            },
                        ],
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1024,
            }
            try:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return json.dumps({
                        "status": "success",
                        "modelo_vision": model_id,
                        "analisis": content,
                    }, ensure_ascii=False)
                ultimo_error = f"{model_id} devolvió HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as exc:
                ultimo_error = f"{model_id} falló: {exc}"

    return json.dumps({"status": "error", "message": ultimo_error}, ensure_ascii=False)


@tool
def analyze_catalog_photo(image_b64: str = "ACTIVE_IMAGE", categoria_sugerida: Optional[str] = None) -> str:
    """
    Analiza una fotografía real de catálogo o anaquel usando NVIDIA NIM Vision.
    Detecta productos visibles, infiere precios en empaque y propone SKUs normalizados.
    """
    cat_hint = f" Categoría sugerida: {categoria_sugerida}." if categoria_sugerida else ""
    prompt = (
        "Analiza esta imagen real comercial de productos o anaquel de una tienda de abarrotes."
        f"{cat_hint} Extrae cada producto visible en formato JSON con campos: "
        "sku_sugerido, nombre, categoria, precio_estimado, confianza_deteccion (0.0 a 1.0) y observaciones."
    )
    return _call_nim_vision_endpoint(prompt, image_b64)


@tool
def analyze_receipt(image_b64: str = "ACTIVE_IMAGE") -> str:
    """
    Ejecuta OCR real sobre un ticket o factura de compra mediante NVIDIA NIM Vision y clasifica
    el importe en 'inversion_inventario' (mercancía para reventa) o 'gasto_operativo'.
    """
    prompt = (
        "Extrae todo el texto real de este comprobante o factura. Devuelve un JSON con: "
        "proveedor, folio_o_numero, fecha_emision, total_importe, partidas (descripcion, cantidad, "
        "precio_unitario, subtotal), clasificacion_contable ('inversion_inventario' o 'gasto_operativo') "
        "y justificacion_clasificacion."
    )
    return _call_nim_vision_endpoint(prompt, image_b64)


@tool
def analyze_pos_items(image_b64: str = "ACTIVE_IMAGE") -> str:
    """
    Examina visualmente mediante NVIDIA NIM Vision los artículos colocados sobre la barra de caja POS.
    Devuelve la lista real de productos y cantidades detectadas para cotizar contra PostgreSQL.
    """
    prompt = (
        "Identifica los productos reales y la cantidad exacta de unidades visibles en esta foto de mostrador POS. "
        "Devuelve un JSON con 'items': lista de objetos con nombre, marca, presentacion, cantidad_detectada y confianza."
    )
    return _call_nim_vision_endpoint(prompt, image_b64)
