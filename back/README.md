# Backend — agente guía bancario

FastAPI que recibe el mensaje del chat, lo anonimiza, busca la guía verificada y usa un modelo
**solo para redactar el texto**. Los pasos salen de `app/datos/guias.json`, nunca del modelo
(los LLM inventan nombres de botones). Diseño completo: `../front/docs/DISENO-agente-bancario.md`.

## Qué hace el modelo y qué no

| Lo hace el modelo | Lo hace el código (sin modelo) |
|---|---|
| Entender la intención cuando las palabras clave no alcanzan ("mandarle lana a mi proveedor") | Bloquear datos sensibles y temas fuera de alcance |
| Redactar la introducción y contestar seguimientos con el historial ("¿y si no me deja agregar al contacto?") | Los pasos, botones y avisos: salen de `app/datos/guias.json` |
| | Descartar lo que el modelo invente (`app/filtro.py`: botones entre comillas que no estén en la guía, listas, petición de claves, filtrar sus reglas, hablar de otro banco) |

Si el modelo falla o su texto no pasa el filtro, se usa un texto de respaldo y la guía se muestra igual.
El front envía el historial (últimos 8 turnos, anonimizado) y el back devuelve `banco`/`operacion` para
mantener el contexto entre mensajes.

Con Ollama el modelo se precalienta al arrancar (la primera carga tarda ~1 min); después responde en 2-4 s.
Los modelos pequeños (`qwen2.5:3b`) obedecen peor que NIM: el filtro descarta sus invenciones, pero
verás más textos de respaldo.

## Puesta en marcha

```bash
cd back
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Linux/macOS: .venv/bin/pip
cp .env.example .env                                # y editar (ver abajo)
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

Comprobar: `GET http://localhost:8000/salud` → proveedor, modelo y si responde.

## Elegir el modelo (`LLM_PROVIDER` en `.env`)

| Proveedor | `LLM_PROVIDER` | Qué necesita | Privacidad |
|---|---|---|---|
| NVIDIA NIM (nube) | `nim` | `NVIDIA_API_KEY` de build.nvidia.com. Modelo por defecto `nvidia/nemotron-3.5-bolt-e4b` | El texto, ya anonimizado, sale hacia NVIDIA |
| Ollama (local) | `ollama` | [Ollama](https://ollama.com) instalado y `ollama pull qwen2.5:3b` | **Nada sale del equipo** |

`LLM_FALLBACK=ollama` hace que, si NIM falla, se pruebe el modelo local. Si ambos fallan, el chat
sigue funcionando con un texto fijo y la guía.

Los dos hablan el mismo protocolo (`POST /v1/chat/completions`), por eso hay un solo cliente (`app/llm.py`).
Modelos con razonamiento (p. ej. `nemotron-3.5-lightning`) necesitan `LLM_MAX_TOKENS` ≥ 3000.

## Privacidad

- `app/anonimizar.py` revalida en el servidor: tarjeta, CLABE, NIP/CVV/token **bloquean** el mensaje
  (no llega al modelo); montos y celulares se enmascaran.
- No se registra el contenido de los mensajes. La clave vive solo en `back/.env` (ignorado por Git).
- No uses `EXPO_PUBLIC_*` para la clave: esas variables viajan dentro de la app.

## Pruebas

```bash
.venv/Scripts/python -m pytest -q
```

Al probar con `curl` en Windows, envía el cuerpo desde un archivo UTF-8 (`--data-binary @archivo.json`):
los acentos escritos en la línea de comandos pueden romper el JSON.

## Pendiente

- Los textos de botones de BBVA son supuestos: verificarlos en la app vigente (`app/datos/guias.json`).
- Más bancos y operaciones verificadas; endpoint `/asistente/tutor`.
