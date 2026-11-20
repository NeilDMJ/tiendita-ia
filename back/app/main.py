"""API del agente guía bancario. Uso: uvicorn app.main:app --port 8000 (desde back/)."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import llm
from .config import Settings, get_settings
from .conocimiento import buscar_hibrido
from .esquemas import MensajeAsistente, SolicitudMensaje
from .servicio import GeneradorTexto, responder


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    s = get_settings()
    # Ollama tarda ~1 min en cargar el modelo la primera vez: se precalienta sin bloquear el arranque.
    tareas = [asyncio.create_task(llm.precalentar(s, p)) for p in {s.llm_provider, s.llm_fallback} if p == "ollama"]
    yield
    for tarea in tareas:
        tarea.cancel()


app = FastAPI(title="Guía bancaria — backend", version="0.2.0", lifespan=ciclo_de_vida)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


def generador(s: Settings) -> GeneradorTexto:
    """Modelo principal; si falla y hay LLM_FALLBACK, prueba el de respaldo (p. ej. nube → local)."""

    async def generar(mensajes: list[dict[str, str]], **opciones: float | int | None) -> str:
        try:
            return await llm.completar(s, s.llm_provider, mensajes, **opciones)
        except llm.ErrorLLM:
            if s.llm_fallback and s.llm_fallback != s.llm_provider:
                return await llm.completar(s, s.llm_fallback, mensajes, **opciones)
            raise

    return generar


@app.get("/salud")
async def salud() -> dict:
    s = get_settings()
    try:
        _, modelo, _ = llm.config_proveedor(s, s.llm_provider)
    except llm.ErrorLLM:
        modelo = "(sin configurar)"
    return {
        "proveedor": s.llm_provider,
        "modelo": modelo,
        "respaldo": s.llm_fallback or None,
        "disponible": await llm.salud(s, s.llm_provider),
    }


@app.post("/asistente/mensaje", response_model=MensajeAsistente, response_model_exclude_none=True)
async def asistente_mensaje(solicitud: SolicitudMensaje) -> MensajeAsistente:
    # response_model_exclude_none: el zod del front usa .optional(), que rechaza null.
    cfg = get_settings()

    async def buscar(consulta: str):
        return await buscar_hibrido(cfg, consulta)

    return await responder(solicitud.texto, generador(cfg), [t.a_mensaje() for t in solicitud.historial], buscar)
