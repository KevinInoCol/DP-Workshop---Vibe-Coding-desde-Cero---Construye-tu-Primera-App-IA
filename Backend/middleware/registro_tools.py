"""
Middleware que registra en la terminal cada uso de una tool.

Usa @wrap_tool_call de LangChain v1: envuelve la ejecución de TODAS las tools
del agente, así que una tool nueva queda registrada sin tocar este archivo.
Por cada llamada deja dos líneas: qué tool y con qué argumentos, y cuánto tardó
y cuánto devolvió (o el error, si falló).
"""

import logging
import time

from langchain.agents.middleware import wrap_tool_call

logger = logging.getLogger("agente.tools")

MAX_CARACTERES_ARGS = 200


@wrap_tool_call
def registrar_tools(request, handler):
    nombre = request.tool_call["name"]
    args = str(request.tool_call.get("args", {}))[:MAX_CARACTERES_ARGS]
    logger.info("🔧 %s ← %s", nombre, args)

    inicio = time.perf_counter()
    try:
        resultado = handler(request)
    except Exception as exc:
        logger.error("❌ %s falló en %.2fs: %s", nombre, time.perf_counter() - inicio, type(exc).__name__)
        raise

    contenido = getattr(resultado, "content", "")
    logger.info("✅ %s → %d caracteres en %.2fs", nombre, len(str(contenido)), time.perf_counter() - inicio)
    return resultado
