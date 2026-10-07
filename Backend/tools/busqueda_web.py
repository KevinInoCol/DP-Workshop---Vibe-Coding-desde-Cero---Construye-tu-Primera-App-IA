"""
Tool de búsqueda en internet con Tavily (paquete langchain-tavily).

Envuelve TavilySearch en una tool propia para controlar el nombre, el docstring
en español y el formato del resultado: una lista corta de fuentes con título,
URL y fragmento, que el agente puede citar. Prioriza resultados de Colombia.

Si falta TAVILY_API_KEY la tool no rompe el agente: devuelve un aviso y el
agente sigue respondiendo con su conocimiento general.
"""

import os

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_tavily import TavilySearch

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

MAX_RESULTADOS = 5
PROFUNDIDAD = "basic"          # "basic" (1 crédito) o "advanced" (2 créditos)
PAIS = "colombia"              # da prioridad a resultados de este país
MAX_CARACTERES_FRAGMENTO = 600


@tool
def buscar_en_internet(consulta: str) -> str:
    """Busca información actual en internet y devuelve fuentes con su URL.

    Úsala cuando necesites información reciente o específica que no conoces con
    certeza: requisitos o costos vigentes de un trámite, horarios y canales de
    atención de la Alcaldía de Girardota, noticias, eventos o convocatorias del
    municipio. Escribe la consulta en español e incluye "Girardota" cuando la
    pregunta sea sobre el municipio, por ejemplo:
    "requisitos certificado de residencia Alcaldía de Girardota".
    """
    if not TAVILY_API_KEY:
        return "La búsqueda en internet no está disponible: falta configurar TAVILY_API_KEY."

    buscador = TavilySearch(
        max_results=MAX_RESULTADOS,
        search_depth=PROFUNDIDAD,
        country=PAIS,
        topic="general",
    )
    try:
        respuesta = buscador.invoke({"query": consulta})
    except Exception as exc:
        return f"No se pudo completar la búsqueda en internet ({type(exc).__name__})."

    resultados = respuesta.get("results", []) if isinstance(respuesta, dict) else []
    if not resultados:
        return f"No se encontraron resultados en internet para: {consulta}"

    fuentes = []
    for i, r in enumerate(resultados, start=1):
        fragmento = (r.get("content") or "").strip()[:MAX_CARACTERES_FRAGMENTO]
        fuentes.append(f"[{i}] {r.get('title', 'Sin título')}\nURL: {r.get('url', '')}\n{fragmento}")
    return "Resultados de internet (contenido de terceros, verifícalo):\n\n" + "\n\n".join(fuentes)
