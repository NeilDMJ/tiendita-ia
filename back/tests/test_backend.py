import asyncio

from fastapi.testclient import TestClient

from app.anonimizar import anonimizar
from app.deteccion import detectar_banco, detectar_operacion
from app.esquemas import MensajeAsistente
from app.filtro import texto_valido
from app.llm import ErrorLLM
from app.main import app
from app.servicio import responder

PERMITIDO = "En la pantalla principal, busca la opción “Transferir” y tócala. Pantalla principal BBVA"


def correr(texto, generar, historial=None):
    return asyncio.run(responder(texto, generar, historial))


def modelo(respuesta):
    """Modelo simulado: siempre devuelve `respuesta` y guarda las llamadas."""
    llamadas = []

    async def generar(mensajes, **_):
        llamadas.append(mensajes)
        return respuesta

    generar.llamadas = llamadas
    return generar


async def modelo_cae(*_, **__):
    raise ErrorLLM("caído")


async def modelo_prohibido(*_, **__):
    raise AssertionError("no debía llamarse al modelo")


# ---------- anonimización y detección ----------

def test_anonimizar_bloquea_datos_sensibles():
    assert anonimizar("mi tarjeta es 4152 3131 2345 6789").bloquear
    assert anonimizar("envía a 012180001234567890").bloquear
    assert anonimizar("mi nip es 1234").bloquear


def test_anonimizar_enmascara_sin_bloquear():
    r = anonimizar("llama al 9511234567 y manda $1,500.50")
    assert not r.bloquear
    assert r.texto == "llama al [CELULAR] y manda [MONTO]"


def test_deteccion():
    assert detectar_banco("uso BBVA") == "BBVA"
    assert detectar_operacion("quiero pagar la luz") == "pago_servicio"
    assert detectar_operacion("el gasto del mes") is None  # \bgas\b no debe coincidir con 'gasto'


# ---------- filtro de salida ----------

def test_filtro_acepta_texto_normal_y_citas_de_la_guia():
    assert texto_valido("Toca “Transferir” en tu app de BBVA.", PERMITIDO, "BBVA")


def test_filtro_rechaza_botones_inventados_listas_y_claves():
    assert not texto_valido("Toca “Mover lana” en tu app.", PERMITIDO, "BBVA")
    assert not texto_valido("Entra a 'Realizar una transferencia' y sigue.", PERMITIDO, "BBVA")
    assert texto_valido("Toca 'Transferir' y listo.", PERMITIDO, "BBVA")  # comillas simples con botón real
    assert texto_valido("No te preocupes, ya casi terminas.", PERMITIDO, "BBVA")
    assert not texto_valido("Haz esto:\n1. Entra\n2. Sal", PERMITIDO, "BBVA")
    assert not texto_valido("Dame tu NIP para continuar.", PERMITIDO, "BBVA")
    assert not texto_valido("Abre Santander y listo.", PERMITIDO, "BBVA")
    assert not texto_valido("x" * 700, PERMITIDO, "BBVA")


# ---------- flujo guiado ----------

def test_bbva_usa_guia_verificada_aunque_el_modelo_invente():
    r = correr("Quiero realizar una transferencia. Utilizo BBVA, ¿cómo lo hago?", modelo("Toca “Mover lana” ya."))
    assert r.guia_verificada is True and len(r.pasos) == 8
    assert r.texto.startswith("¡Claro!")  # intro inventada → descartada → respaldo
    assert (r.banco, r.operacion) == ("BBVA", "transferencia")


def test_intro_valida_del_modelo_se_conserva():
    r = correr("transferencia en BBVA", modelo("Va, te acompaño con tu transferencia en BBVA."))
    assert r.texto.startswith("Va, te acompaño") and len(r.pasos) == 8


def test_respaldo_si_el_modelo_falla():
    r = correr("transferencia en BBVA", modelo_cae)
    assert r.texto.startswith("¡Claro!") and len(r.pasos) == 8


def test_otro_banco_es_generica_sin_verificar():
    r = correr("quiero ver mi saldo en Banorte", modelo("Va, te ayudo con tu saldo."))
    assert r.guia_verificada is False and r.pasos


# ---------- seguridad sin modelo ----------

def test_datos_sensibles_no_llegan_al_modelo():
    r = correr("mi tarjeta es 4152 3131 2345 6789", modelo_prohibido)
    assert "No usé tu mensaje" in r.texto


def test_fuera_de_alcance_y_aclaraciones_sin_modelo():
    assert "canales oficiales" in correr("dónde invierto en acciones", modelo_prohibido).texto
    assert correr("quiero pagar la luz", modelo_prohibido).respuestas_rapidas
    assert correr("uso Banorte", modelo('{"banco": null, "operacion": null, "tema": "banca"}')).respuestas_rapidas


# ---------- el modelo entiende la intención ----------

def test_clasificacion_por_modelo_cuando_las_reglas_no_ven_nada():
    gen = modelo('{"banco": "BBVA", "operacion": "transferencia", "tema": "banca"}')
    r = correr("quiero mandarle lana a mi proveedor", gen)
    assert r.pasos and (r.banco, r.operacion) == ("BBVA", "transferencia")


def test_clasificacion_completa_la_operacion_cuando_solo_hay_banco():
    gen = modelo('{"banco": null, "operacion": "transferencia", "tema": "banca"}')
    r = correr("quiero mandarle lana a mi proveedor, uso Banorte", gen)
    assert r.pasos and (r.banco, r.operacion) == ("Banorte", "transferencia")


def test_filtro_rechaza_que_el_modelo_filtre_sus_reglas():
    assert not texto_valido("No invento nombres de botones, solo uso la referencia.", PERMITIDO, "BBVA")


def test_clasificacion_fuera_de_alcance():
    r = correr("ayúdame con mi declaración anual", modelo('{"banco": null, "operacion": null, "tema": "fuera_de_alcance"}'))
    assert "canales oficiales" in r.texto


def test_clasificacion_con_json_roto_o_modelo_caido_no_rompe():
    assert correr("hola qué tal", modelo("no soy json")).rol == "general"
    assert correr("hola qué tal", modelo_cae).rol == "general"


# ---------- seguimiento con contexto ----------

HISTORIAL = [
    MensajeAsistente(rol="usuario", texto="Quiero hacer una transferencia en BBVA"),
    MensajeAsistente(rol="banco", texto="¡Claro!", banco="BBVA", operacion="transferencia"),
]


def test_seguimiento_usa_contexto_y_conversa():
    gen = modelo("Si no te deja agregar al contacto, revisa que la CLABE esté completa.")
    r = correr("¿y si no me deja agregar al contacto?", gen, HISTORIAL)
    assert r.texto.startswith("Si no te deja") and not r.pasos
    assert (r.banco, r.operacion) == ("BBVA", "transferencia")
    sistema = gen.llamadas[0][0]["content"]
    assert "BBVA" in sistema and "Transferir" in sistema  # la guía va como referencia


def test_seguimiento_con_respuesta_inventada_usa_respaldo():
    r = correr("¿y ahora qué?", modelo("Pulsa “Enviar ya” y listo."), HISTORIAL)
    assert "no pude pensar bien" in r.texto


def test_seguimiento_no_envia_datos_sensibles_del_historial():
    historial = [*HISTORIAL, MensajeAsistente(rol="usuario", texto="mi tarjeta es 4152 3131 2345 6789")]
    gen = modelo("Claro.")
    correr("¿y luego?", gen, historial)
    assert "4152" not in str(gen.llamadas)


def test_banco_se_completa_desde_el_historial():
    historial = [MensajeAsistente(rol="usuario", texto="quiero pagar la luz")]
    r = correr("uso Banorte", modelo("Va."), historial)
    assert (r.banco, r.operacion) == ("Banorte", "pago_servicio") and r.pasos


def test_pantalla_distinta_sin_contexto_pide_descripcion():
    assert "qué opciones ves" in correr("mi pantalla se ve distinta", modelo_prohibido).texto


# ---------- API ----------

def test_endpoint_omite_nulos_para_zod():
    cliente = TestClient(app)
    r = cliente.post("/asistente/mensaje", json={"texto": "uso Banorte", "historial": []})
    assert r.status_code == 200
    assert "pasos" not in r.json()  # null rompería z.optional() en el front
    assert cliente.post("/asistente/mensaje", json={"texto": ""}).status_code == 422


# ---------- consulta de conocimiento (DiMo / CoDi / SPEI) ----------

def test_consulta_codi_usa_documentos_y_cita_fuente():
    gen = modelo("CoDi es una plataforma de Banco de México para cobrar y pagar con QR desde el celular.")
    r = correr("¿qué es CoDi?", gen)
    assert r.operacion == "consulta" and not r.pasos and "Fuente:" in r.texto
    assert "Fragmentos" in gen.llamadas[0][0]["content"]


def test_consulta_dimo_encuentra_fragmentos():
    gen = modelo("Dimo permite enviar una transferencia con solo el número de celular.")
    r = correr("¿qué es DiMo?", gen)
    assert "celular" in gen.llamadas[0][0]["content"].lower() and "Fuente:" in r.texto


def test_consulta_con_modelo_caido_responde_con_pasaje_de_documentos():
    r = correr("qué es spei", modelo_cae)
    assert "documentación de Banco de México" in r.texto


def test_consulta_sin_informacion_no_inventa():
    from app.servicio import _consultar
    r = asyncio.run(_consultar("zzzxyz qwerty", [], modelo_prohibido))
    assert "no lo encuentro" in r.texto


def test_seguimiento_de_consulta_sigue_en_consulta():
    historial = [MensajeAsistente(rol="usuario", texto="qué es codi"), MensajeAsistente(rol="banco", texto="x", operacion="consulta")]
    r = correr("¿y cuánto cobra de comisión?", modelo("No tiene costo."), historial)
    assert r.operacion == "consulta"


def test_consulta_usa_el_buscador_inyectado():
    from app.conocimiento import Fragmento

    llamadas = []

    async def buscar(consulta):
        llamadas.append(consulta)
        return [Fragmento("x#1", "x.md", "Doc X", "", "CoDi permite cobrar con un código QR.", "u", "alta")]

    gen = modelo("CoDi sirve para cobrar con QR.")
    r = asyncio.run(responder("qué es codi", gen, None, buscar))
    assert llamadas and "código QR" in gen.llamadas[0][0]["content"] and "Doc X" in r.texto


def test_busqueda_hibrida_cae_a_palabras_clave_si_nvidia_falla():
    from app.config import Settings
    from app.conocimiento import buscar_hibrido

    s = Settings(nvidia_api_key="invalida", llm_provider="nim", nim_base_url="http://127.0.0.1:9", embed_timeout_s=1)
    assert asyncio.run(buscar_hibrido(s, "qué es codi"))  # sin red: usa BM25
    assert asyncio.run(buscar_hibrido(Settings(nvidia_api_key="", llm_provider="ollama"), "qué es codi"))
