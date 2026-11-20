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
def generate_promo_copy(
    product_name: str,
    trigger: Literal["caducidad", "sobrestock", "general"],
    precio_actual: Optional[float] = None,
    descuento_pct: Optional[float] = 20.0,
) -> str:
    """
    Prepara el brief estructurado y cálculo de precio promocional para que el agente redacte
    un copy publicitario original (no genérico) adaptado a WhatsApp, redes sociales y mostrador.
    """
    precio_promo = (
        round(float(precio_actual) * (1.0 - (float(descuento_pct or 0.0) / 100.0)), 2)
        if precio_actual is not None and precio_actual > 0
        else None
    )
    return json.dumps({
        "status": "brief_ready",
        "producto": product_name,
        "trigger": trigger,
        "precio_actual": precio_actual,
        "descuento_pct": descuento_pct,
        "precio_promo_calculado": precio_promo,
        "instruccion_redaccion": (
            "Redacta un copy original, cercano y específico para este producto en español de México, "
            "destacando el ahorro real y urgencia sin usar frases genéricas repetitivas."
        ),
    }, ensure_ascii=False)


@tool
def generate_video_prompt(
    product_name: str,
    trigger: Literal["caducidad", "sobrestock", "general"],
    precio_promo: Optional[float] = None,
) -> str:
    """
    Devuelve la especificación técnica vertical 9:16 (5s) para que el agente redacte
    la dirección visual original y locución adaptada al producto real.
    """
    return json.dumps({
        "status": "spec_ready",
        "aspect_ratio": "9:16",
        "duration_seconds": 5,
        "trigger": trigger,
        "producto": product_name,
        "precio_promo": precio_promo,
        "requisitos_escena": [
            "Formato vertical 9:16, duración exacta 5 segundos",
            "Plano macro inicial del producto real sobre mostrador de tiendita mexicana",
            "Mostrar etiqueta clara con precio promocional y cierre con llamado a la acción",
        ],
    }, ensure_ascii=False)


@tool
def generate_cta(product_name: str, discount_pct: Optional[float] = 20.0) -> str:
    """
    Devuelve parámetros estructurados de descuento y urgencia para formular un CTA único para el producto.
    """
    return json.dumps({
        "status": "brief_ready",
        "producto": product_name,
        "descuento_pct": discount_pct,
        "objetivo": "Llamado a la acción breve (máx. 1 oración) enfocado en visita hoy mismo al mostrador.",
    }, ensure_ascii=False)
