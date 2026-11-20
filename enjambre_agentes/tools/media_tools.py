"""
Herramientas de Medios, Publicidad y Guías de Pagos Digitales (CoDi, SPEI, DiMo):
- Generación de copys comerciales, llamados a la acción (CTAs) y prompts de video vertical 9:16 de 5s.
- Consulta especializada al RAG de pagos digitales (`consultar_guia_pago_digital`) para Tutor UI y Vendedor.
"""
from __future__ import annotations

import json
from typing import Literal, Optional
from langchain_core.tools import tool

from tools.rag_nemo import buscar_guia_pago, obtener_advertencias_pago


@tool
def consultar_guia_pago_digital(
    metodo_pago: str,
    pantalla: str,
    error_code: Optional[str] = None,
    duda: str = "",
) -> str:
    """
    Consulta en el índice RAG oficial (guias.json + conocimiento.jsonl de Banxico) los pasos exactos,
    límites y solución de errores para pagos digitales en México: CoDi, SPEI y DiMo.

    Args:
        metodo_pago: Método de pago digital ('codi', 'spei', 'dimo').
        pantalla: Pantalla o etapa actual del flujo (ej. 'cobro_qr', 'transferir', 'confirmacion', 'comprobante').
        error_code: Código o mensaje de error visible en pantalla (opcional).
        duda: Pregunta adicional del cajero o cliente (opcional).
    """
    partes = [duda.strip()] if duda else []
    if error_code:
        partes.append(f"error {error_code}")
    consulta = " ".join(partes) or f"pasos y solucion en pantalla {pantalla} para {metodo_pago}"

    fragmentos = buscar_guia_pago(
        metodo_pago=metodo_pago,
        pantalla=pantalla,
        consulta=consulta,
        top_k=3,
    )
    tipo_adv = "cobro" if metodo_pago.strip().lower() == "codi" else "transferencia"
    advertencias = obtener_advertencias_pago(tipo_adv)

    return json.dumps(
        {
            "status": "success" if fragmentos else "no_results",
            "metodo_pago": metodo_pago.strip().lower(),
            "pantalla": pantalla,
            "error_code": error_code,
            "advertencias_seguridad": advertencias,
            "guias_recuperadas": fragmentos,
        },
        ensure_ascii=False,
    )


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
