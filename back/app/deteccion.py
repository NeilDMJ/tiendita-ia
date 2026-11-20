"""Detección de banco, operación y temas fuera de alcance. Espejo de front/src/api/mocks/banco.ts."""
import re
from typing import Literal

Operacion = Literal["transferencia", "pago_servicio", "saldo", "cobro"]

BANCOS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"bbva", re.I), "BBVA"),
    (re.compile(r"banorte", re.I), "Banorte"),
    (re.compile(r"santander", re.I), "Santander"),
    (re.compile(r"banamex|citibanamex", re.I), "Banamex"),
    (re.compile(r"hsbc", re.I), "HSBC"),
    (re.compile(r"\bnu\b", re.I), "Nu"),
]

OPERACIONES: list[tuple[re.Pattern[str], Operacion]] = [
    (re.compile(r"transfer|enviar dinero|mandar dinero|spei", re.I), "transferencia"),
    (re.compile(r"servicio|\bluz\b|\bagua\b|\bgas\b|tel[eé]fono|recibo", re.I), "pago_servicio"),
    (re.compile(r"saldo|cu[aá]nto tengo|movimientos", re.I), "saldo"),
    (re.compile(r"cobro|dep[oó]sito|me lleg[oó]|me pagaron", re.I), "cobro"),
]

FUERA_DE_ALCANCE = re.compile(r"inversi|cr[eé]dito|pr[eé]stamo|acciones|cripto|impuestos|\bsat\b", re.I)
PANTALLA_DISTINTA = re.compile(r"distint|no coincide|no me sale|no aparece", re.I)

NOMBRE_OP: dict[Operacion, str] = {
    "transferencia": "una transferencia",
    "pago_servicio": "el pago de un servicio",
    "saldo": "tu saldo y movimientos",
    "cobro": "si te llegó un cobro",
}

FRASE_OP: dict[Operacion, str] = {
    "transferencia": "Quiero hacer una transferencia",
    "pago_servicio": "Quiero pagar un servicio",
    "saldo": "Quiero ver mi saldo",
    "cobro": "Quiero revisar si me llegó un cobro",
}


def detectar_banco(texto: str) -> str | None:
    return next((nombre for patron, nombre in BANCOS if patron.search(texto)), None)


def detectar_operacion(texto: str) -> Operacion | None:
    return next((op for patron, op in OPERACIONES if patron.search(texto)), None)

# Saludos y despedidas: se contestan sin modelo y sin citar fuentes.
SALUDO = re.compile(
    r"^\s*[¡¿]*(hola|holi|buen[oa]s(?: d[ií]as| tardes| noches)?|hey|qu[eé] tal|c[oó]mo est[aá]s)[\s!.¡¿?]*$", re.I
)
GRACIAS = re.compile(
    r"^\s*[¡¿]*(muchas )?(gracias|ok|okey|vale|listo|perfecto|entendido|adi[oó]s|hasta luego|nos vemos)[\s!.¡¿?]*$", re.I
)
