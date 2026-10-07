"""
Tool de retrieval sobre la base de conocimiento (Manual de Trámites en Qdrant).

Busca los chunks más parecidos, los agrupa por trámite y devuelve el TEXTO
COMPLETO de los trámites más relevantes (con código, dependencia, páginas y
fecha del documento). Los trámites que también coinciden pero con menos
relevancia se listan solo por nombre, para que el agente pueda preguntar al
ciudadano cuál necesita. Si Qdrant no responde, devuelve un aviso en vez de
romper el agente.
"""

import logging

from langchain.tools import tool

from rag.retriever import buscar_chunks, texto_completo_del_tramite

logger = logging.getLogger("agente.rag")

NUM_CHUNKS_BUSQUEDA = 10       # chunks que se piden a Qdrant antes de agrupar
MAX_TRAMITES_COMPLETOS = 2     # trámites que se devuelven con su texto íntegro
MAX_TRAMITES_RELACIONADOS = 3  # otros candidatos que se listan solo por nombre
SCORE_MINIMO = 0.35            # similitud coseno; por debajo, no es relevante
MARGEN_EMPATE = 0.08           # un 2.º trámite va completo si está así de cerca del 1.º


def agrupar_por_tramite(resultados):
    """Mejor score por trámite (o por chunk general), de mayor a menor."""
    mejores = {}
    for doc, score in resultados:
        meta = doc.metadata
        clave = meta.get("codigo") or f"general-{meta.get('pagina_inicio')}-{hash(doc.page_content)}"
        if clave not in mejores or score > mejores[clave][1]:
            mejores[clave] = (doc, score)
    return sorted(mejores.values(), key=lambda x: x[1], reverse=True)


def formatear(doc, score, texto):
    meta = doc.metadata
    paginas = meta.get("pagina_inicio")
    if meta.get("pagina_fin") and meta.get("pagina_fin") != paginas:
        paginas = f"{paginas}-{meta['pagina_fin']}"
    detalles = f"Páginas del manual: {paginas}"
    if meta.get("fecha_documento"):
        detalles += f" · documento del {meta['fecha_documento']}"
    detalles += f" · relevancia {score:.2f}"

    if meta.get("tipo") == "tramite":
        titulo = f"=== Trámite {meta['codigo']}: {meta['tramite']} ===\nDependencia: {meta['dependencia']}"
    else:
        titulo = "=== Información general del manual ==="
    return f"{titulo}\n{detalles}\n\n{texto}"


@tool
def buscar_en_base_de_conocimiento(consulta: str) -> str:
    """Busca en el Manual de Trámites oficial del Municipio de Girardota.

    Es la fuente principal para cualquier pregunta sobre trámites municipales.
    Devuelve el texto COMPLETO de los trámites más relevantes: propósito,
    tiempo de obtención, TODOS los documentos requeridos, pasos, a quién aplica
    y pagos, con la dependencia y la página del manual. Escribe la consulta en
    español con el nombre del trámite o el tema, por ejemplo:
    "requisitos certificado de residencia" o "aprobación de piscinas".
    """
    try:
        candidatos = agrupar_por_tramite(buscar_chunks(consulta, k=NUM_CHUNKS_BUSQUEDA))
    except Exception as exc:
        logger.warning("Qdrant no disponible: %s", type(exc).__name__)
        return f"La base de conocimiento no está disponible en este momento ({type(exc).__name__})."

    candidatos = [(doc, score) for doc, score in candidatos if score >= SCORE_MINIMO]
    if not candidatos:
        logger.info("Sin resultados relevantes para %r", consulta)
        return f"El Manual de Trámites no contiene información relevante sobre: {consulta}"

    mejor = candidatos[0][1]
    completos = [c for c in candidatos[:MAX_TRAMITES_COMPLETOS] if c[1] >= mejor - MARGEN_EMPATE]
    relacionados = [c for c in candidatos if c not in completos][:MAX_TRAMITES_RELACIONADOS]

    bloques = []
    for doc, score in completos:
        meta = doc.metadata
        texto = texto_completo_del_tramite(meta["codigo"]) if meta.get("tipo") == "tramite" else doc.page_content
        bloques.append(formatear(doc, score, texto))
        logger.info("   → %s %s (%.2f, %d caracteres)",
                    meta.get("codigo", "general"), meta.get("tramite", ""), score, len(texto))

    salida = "Resultados del Manual de Trámites:\n\n" + "\n\n".join(bloques)
    nombres = [f"- {d.metadata['codigo']}: {d.metadata['tramite']} (relevancia {s:.2f})"
               for d, s in relacionados if d.metadata.get("tipo") == "tramite"]
    if nombres:
        salida += "\n\nOtros trámites que también podrían corresponder:\n" + "\n".join(nombres)
        logger.info("   · relacionados: %s", ", ".join(d.metadata["codigo"] for d, _ in relacionados
                                                       if d.metadata.get("tipo") == "tramite"))
    return salida
