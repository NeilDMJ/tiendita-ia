"""
Herramientas de Medios y Publicidad para el Agente Publicista:
Generación de copys comerciales, llamados a la acción (CTAs) y prompts de video vertical 9:16 de 5s.
"""
from __future__ import annotations

import json
from typing import Literal, Optional
from langchain_core.tools import tool


@tool
def generate_promo_copy(product_name: str, trigger: Literal["caducidad", "sobrestock", "general"]) -> str:
    """
    Genera un texto publicitario altamente persuasivo y localizado para WhatsApp o redes sociales.
    """
    if trigger == "caducidad":
        copy = (
            f"¡OFERTA RELÁMPAGO EN TIENDITA! Hoy tenemos {product_name} con descuento especial de remate "
            f"fresco para disfrutar hoy mismo en familia. ¡Pocas piezas en mostrador!"
        )
    elif trigger == "sobrestock":
        copy = (
            f"¡Surtido en grande! Llévate tu {product_name} favorito a precio de paquete de temporada. "
            f"Ven a tu tiendita de confianza y ahorra en tu canasta semanal."
        )
    else:
        copy = (
            f"Encuentra siempre fresco y al mejor precio tu {product_name} en Tiendita IA. "
            f"¡Abierto todos los días con atención rápida y pago digital disponible!"
        )
    
    return json.dumps({
        "status": "success",
        "producto": product_name,
        "trigger": trigger,
        "copy_text": copy
    }, ensure_ascii=False)


@tool
def generate_video_prompt(product_name: str, trigger: Literal["caducidad", "sobrestock", "general"]) -> str:
    """
    Crea un prompt cinematográfico vertical en formato 9:16 con duración de 5 segundos
    para modelos generativos de video (NVIDIA / Runway / Pika) ante sobrestock o caducidad.
    """
    prompt_visual = (
        f"Vertical commercial video 9:16 aspect ratio, 5 seconds duration. Close-up cinematic macro shot of {product_name} "
        f"on a clean modern Mexican grocery counter. Crisp studio lighting, vibrant warm colors, shallow depth of field. "
        f"Dynamic camera tilt-down revealing fresh texture and premium packaging, with a subtle golden hour glow. "
        f"High production value, 4K resolution, hyperrealistic commercial aesthetic."
    )
    guion_off = f"¡Aprovecha hoy {product_name} al mejor precio en tu tiendita vecina!"
    
    return json.dumps({
        "status": "success",
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
        "trigger": trigger,
        "producto": product_name,
        "video_prompt": prompt_visual,
        "guion_locucion": guion_off
    }, ensure_ascii=False)


@tool
def generate_cta(product_name: str, discount_pct: Optional[float] = 20.0) -> str:
    """
    Produce un llamado a la acción (CTA) directo y apremiante para incentivar la visita o compra inmediata.
    """
    pct_text = f" con {int(discount_pct)}% de descuento" if discount_pct else ""
    cta = f"¡Corre por tu {product_name}{pct_text}! Disponible hasta agotar existencias en mostrador."
    return json.dumps({"status": "success", "cta": cta}, ensure_ascii=False)
