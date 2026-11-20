"""Orquesta una respuesta.

Seguridad primero (determinista, sin modelo): datos sensibles y fuera de alcance.
Después el modelo ayuda a entender la intención y a conversar, pero los pasos de una operación
salen SIEMPRE de las guías, y todo texto del modelo pasa por `filtro.texto_valido`.
"""
import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

from .anonimizar import anonimizar
from .conocimiento import TEMA_CONSULTA, indice
from .deteccion import (
    BANCOS,
    FRASE_OP,
    FUERA_DE_ALCANCE,
    NOMBRE_OP,
    PANTALLA_DISTINTA,
    detectar_banco,
    detectar_operacion,
)
from .esquemas import MensajeAsistente
from .filtro import texto_valido
from .guias import Guia, obtener_guia
from .llm import REGLAS, SISTEMA_CLASIFICAR, SISTEMA_CONSULTA, SISTEMA_INTRO, ErrorLLM

# generar(mensajes, max_tokens=..., temperature=...) -> texto del modelo (puede lanzar ErrorLLM)
GeneradorTexto = Callable[..., Awaitable[str]]

TURNOS_DE_CONTEXTO = 8
NOMBRES_BANCOS = {nombre for _, nombre in BANCOS}
OPERACIONES_VALIDAS = set(NOMBRE_OP)

AVISO_BLOQUEO = (
    "No usé tu mensaje porque parece traer datos privados (tarjeta, CLABE, NIP o clave). "
    "Por tu seguridad, no los escribas aquí. Cuéntame lo que quieres hacer sin esos datos y te guío."
)
FUERA_DE_ALCANCE_TEXTO = (
    "Eso no lo puedo resolver desde aquí. Para eso lo mejor es contactar a tu banco por sus "
    "canales oficiales. ¿Te ayudo con alguna operación paso a paso?"
)
NO_ENTENDI = "No entendí bien. ¿Quieres hacer una transferencia, pagar un servicio, ver tu saldo o revisar un cobro?"
PANTALLA_SIN_CONTEXTO = (
    "Los bancos cambian su app seguido. Cuéntame qué opciones ves en la pantalla (sin escribir "
    "números de cuenta ni claves) y buscamos el camino juntos."
)
SEGUIMIENTO_RESPALDO = (
    "Ahora mismo no pude pensar bien esa respuesta. Revisa los pasos de arriba o cuéntame qué opciones "
    "ves en tu pantalla (sin números de cuenta ni claves) y lo vemos."
)


def _banco(texto: str, **extra: Any) -> MensajeAsistente:
    return MensajeAsistente(rol="banco", texto=texto, **extra)


# ---------- contexto ----------

def _turnos(historial: list[MensajeAsistente]) -> list[MensajeAsistente]:
    """Últimos turnos, con texto anonimizado; se omiten los del usuario con datos sensibles."""
    salida: list[MensajeAsistente] = []
    for m in historial[-TURNOS_DE_CONTEXTO:]:
        a = anonimizar(m.texto)
        if m.rol == "usuario" and a.bloquear:
            continue
        salida.append(m.model_copy(update={"texto": a.texto}))
    return salida


def _contexto(turnos: list[MensajeAsistente]) -> tuple[str | None, str | None]:
    """Banco y operación más recientes de la conversación."""
    banco = operacion = None
    for m in reversed(turnos):
        if banco is None:
            banco = m.banco if m.banco in NOMBRES_BANCOS else (detectar_banco(m.texto) if m.rol == "usuario" else None)
        if operacion is None:
            operacion = (
                m.operacion if m.operacion in OPERACIONES_VALIDAS
                else (detectar_operacion(m.texto) if m.rol == "usuario" else None)
            )
        if banco and operacion:
            break
    return banco, operacion


def _permitido(guia: Guia) -> str:
    return " ".join(f"{p.texto} {p.pantalla or ''}" for p in guia.pasos)


# ---------- modelo ----------

async def _clasificar(t: str, generar: GeneradorTexto) -> tuple[str | None, str | None, str] | None:
    """El modelo interpreta la intención cuando las palabras clave no alcanzan. None si falla."""
    try:
        crudo = await generar(
            [{"role": "system", "content": SISTEMA_CLASIFICAR}, {"role": "user", "content": t}],
            max_tokens=80,
            temperature=0.0,
        )
        datos = json.loads(re.search(r"\{.*\}", crudo, re.S).group(0))  # type: ignore[union-attr]
    except (ErrorLLM, AttributeError, ValueError):
        return None
    banco = datos.get("banco") if datos.get("banco") in NOMBRES_BANCOS else None
    operacion = datos.get("operacion") if datos.get("operacion") in OPERACIONES_VALIDAS else None
    tema = datos.get("tema") if datos.get("tema") in {"banca", "fuera_de_alcance", "otro"} else "otro"
    return banco, operacion, tema


async def _conversar(
    t: str, turnos: list[MensajeAsistente], banco: str, operacion: str, generar: GeneradorTexto
) -> MensajeAsistente:
    """Seguimiento libre ("¿y si no me deja agregar al contacto?") con la guía como referencia."""
    guia = obtener_guia(banco, operacion)
    referencia = "\n".join(f"{p.n}. {p.texto}" for p in guia.pasos)
    sistema = (
        f"{REGLAS}\nEl usuario usa {banco} y está con {NOMBRE_OP[operacion]}. Referencia "
        f"({'verificada' if guia.verificada else 'general, sin verificar: avisa que su app puede verse distinta'}):\n"
        f"{referencia}\nSi lo que pregunta no tiene que ver con operaciones bancarias, dilo con amabilidad."
    )
    conversacion = [
        {"role": "user" if m.rol == "usuario" else "assistant", "content": m.texto} for m in turnos if m.texto
    ]
    try:
        texto = await generar(
            [{"role": "system", "content": sistema}, *conversacion, {"role": "user", "content": t}],
            max_tokens=220,
        )
        if not texto_valido(texto, _permitido(guia), banco):
            texto = SEGUIMIENTO_RESPALDO
    except ErrorLLM:
        texto = SEGUIMIENTO_RESPALDO
    return _banco(texto, banco=banco, operacion=operacion, respuestas_rapidas=["Mi pantalla se ve distinta"])


async def _guiar(t: str, banco: str, operacion: str, generar: GeneradorTexto) -> MensajeAsistente:
    guia = obtener_guia(banco, operacion)
    respaldo = (
        f"¡Claro! Te guío paso a paso en tu app de {banco}."
        if guia.verificada
        else f"Estos son los pasos generales para {NOMBRE_OP[operacion]}. En {banco} los nombres de los botones pueden variar."
    )
    estado = (
        "Tenemos una guía verificada."
        if guia.verificada
        else "Solo hay pasos generales sin verificar: dilo y avisa que su app puede verse distinta."
    )
    contexto = f"El usuario usa {banco} y quiere {NOMBRE_OP[operacion]}. {estado} Mensaje del usuario: {t}"
    try:
        intro = await generar(
            [{"role": "system", "content": SISTEMA_INTRO}, {"role": "user", "content": contexto}], max_tokens=120
        )
        if not texto_valido(intro, _permitido(guia), banco):
            intro = respaldo
    except ErrorLLM:
        intro = respaldo  # el flujo no se rompe si el modelo falla
    return _banco(
        intro,
        pasos=guia.pasos,
        advertencias=guia.advertencias,
        guia_verificada=guia.verificada,
        respuestas_rapidas=["Mi pantalla se ve distinta"],
        banco=banco,
        operacion=operacion,
    )


# ---------- consulta de conocimiento (DiMo, CoDi, SPEI) ----------

SIN_INFORMACION = (
    "Eso no lo encuentro en los documentos de Banco de México que tengo. Te recomiendo preguntarlo en tu banco "
    "o en banxico.org.mx. ¿Te ayudo con una transferencia, un pago o un cobro?"
)
SALTO = chr(10)
RAPIDAS_CONSULTA = ["¿Qué es CoDi?", "¿Qué es DiMo?", "¿Cómo cobro con CoDi?"]


async def _consultar(t: str, turnos: list[MensajeAsistente], generar: GeneradorTexto) -> MensajeAsistente:
    """Responde sobre DiMo/CoDi/SPEI solo con fragmentos de los documentos de Banxico."""
    previas = " ".join(m.texto for m in turnos[-2:] if m.rol == "usuario")  # contexto de un seguimiento
    fragmentos = indice().buscar(f"{previas} {t}", k=4)
    if not fragmentos:
        return _banco(SIN_INFORMACION, operacion="consulta", respuestas_rapidas=RAPIDAS_CONSULTA)
    fuentes = SALTO.join(f"- {f.texto}" for f in fragmentos)
    conversacion = [
        {"role": "user" if m.rol == "usuario" else "assistant", "content": m.texto} for m in turnos[-4:] if m.texto
    ]
    permitido = " ".join(f.texto for f in fragmentos)
    try:
        texto = await generar(
            [{"role": "system", "content": f"{SISTEMA_CONSULTA}{SALTO}{SALTO}Fragmentos:{SALTO}{fuentes}"}, *conversacion, {"role": "user", "content": t}],
            max_tokens=300,
        )
        if not texto_valido(texto, permitido, None, revisar_bancos=False):
            texto = None
    except ErrorLLM:
        texto = None
    if texto is None:  # respaldo: el pasaje más relevante, tal cual
        texto = "Esto dice la documentación de Banco de México: " + fragmentos[0].texto[:450].rsplit(" ", 1)[0] + "…"
    origen = fragmentos[0].titulo
    if origen and "no tengo esa informaci" not in texto.lower():
        texto += f"{SALTO}{SALTO}Fuente: {origen} (Banco de México)"
    return _banco(texto, operacion="consulta", respuestas_rapidas=RAPIDAS_CONSULTA)


# ---------- punto de entrada ----------

async def responder(
    texto: str, generar: GeneradorTexto, historial: list[MensajeAsistente] | None = None
) -> MensajeAsistente:
    seguro = anonimizar(texto)
    if seguro.bloquear:  # nunca llega al modelo
        return _banco(AVISO_BLOQUEO)
    t = seguro.texto

    if FUERA_DE_ALCANCE.search(t):
        return _banco(FUERA_DE_ALCANCE_TEXTO, respuestas_rapidas=["Quiero hacer una transferencia", "Quiero ver mi saldo"])

    turnos = _turnos(historial or [])
    banco_ctx, operacion_ctx = _contexto(turnos)
    banco_msg, operacion_msg = detectar_banco(t), detectar_operacion(t)
    banco, operacion = banco_msg or banco_ctx, operacion_msg or operacion_ctx

    en_consulta = bool(turnos) and turnos[-1].rol == "banco" and turnos[-1].operacion == "consulta"
    if TEMA_CONSULTA.search(t) or (en_consulta and not (banco_msg or operacion_msg)):
        return await _consultar(t, turnos, generar)

    if not (banco_msg or operacion_msg):  # el mensaje no trae pistas por sí solo
        if banco and operacion:  # seguimiento dentro de una operación en curso
            return await _conversar(t, turnos, banco, operacion, generar)
        if PANTALLA_DISTINTA.search(t):
            return _banco(PANTALLA_SIN_CONTEXTO)

    if not operacion:  # el modelo interpreta lo que las reglas no ven ("mandarle lana a mi proveedor")
        clasificado = await _clasificar(t, generar)
        if clasificado:
            c_banco, c_operacion, tema = clasificado
            if tema == "fuera_de_alcance":
                return _banco(FUERA_DE_ALCANCE_TEXTO, respuestas_rapidas=["Quiero hacer una transferencia", "Quiero ver mi saldo"])
            banco, operacion = banco or c_banco, operacion or c_operacion

    if not banco and not operacion:
        return MensajeAsistente(rol="general", texto=NO_ENTENDI, no_resuelto=True, respuestas_rapidas=list(FRASE_OP.values()))
    if not operacion:
        return _banco(
            f"Con gusto. ¿Qué quieres hacer en {banco}?",
            respuestas_rapidas=[f"{f} en {banco}" for f in FRASE_OP.values()],
            no_resuelto=True,
            banco=banco,
        )
    if not banco:
        return _banco(
            f"Te guío con {NOMBRE_OP[operacion]}. ¿Qué banco usas?",
            respuestas_rapidas=[f"{FRASE_OP[operacion]} en {b}" for b in ("BBVA", "Banorte", "Santander", "Otro banco")],
            no_resuelto=True,
            operacion=operacion,
        )
    return await _guiar(t, banco, operacion, generar)
