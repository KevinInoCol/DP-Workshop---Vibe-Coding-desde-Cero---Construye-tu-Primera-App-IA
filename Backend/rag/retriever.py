"""
Recuperación (retrieval) sobre la colección de Qdrant que llena rag/ingesta.py.

Dos pasos:
  1. Búsqueda por similitud de los chunks más parecidos a la consulta.
  2. Reconstrucción: si un chunk es parte de un trámite largo, se traen TODAS
     sus partes de Qdrant (filtro por código) y se unen en orden. Así el agente
     siempre recibe el trámite completo, nunca una lista de requisitos cortada.

La conexión se crea la primera vez que se busca y se reutiliza después. Así el
agente arranca aunque Qdrant esté apagado; el error aparece solo al buscar.
"""

import re
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import models

from rag.config import MODELO_EMBEDDING, QDRANT_COLLECTION, QDRANT_URL

# Cabecera que la ingesta antepone a cada chunk de trámite ("Trámite X: ...\n
# Dependencia: ...\n(parte n de m)\n\n"). Se quita al reconstruir el texto.
PATRON_CABECERA = re.compile(r"\ATrámite .*?\n\n", re.DOTALL)


@lru_cache(maxsize=1)
def obtener_vector_store():
    return QdrantVectorStore.from_existing_collection(
        embedding=OpenAIEmbeddings(model=MODELO_EMBEDDING),
        collection_name=QDRANT_COLLECTION,
        url=QDRANT_URL,
    )


def buscar_chunks(consulta, k):
    """Devuelve [(Document, score)] ordenados del más al menos relevante."""
    return obtener_vector_store().similarity_search_with_score(consulta, k=k)


def texto_completo_del_tramite(codigo):
    """Une en orden todas las partes de un trámite, sin sus cabeceras."""
    puntos, _ = obtener_vector_store().client.scroll(
        collection_name=QDRANT_COLLECTION,
        scroll_filter=models.Filter(must=[
            models.FieldCondition(key="metadata.codigo", match=models.MatchValue(value=codigo)),
        ]),
        limit=100,
        with_payload=True,
        with_vectors=False,
    )
    partes = sorted(puntos, key=lambda p: p.payload["metadata"].get("parte", 1))
    return "\n".join(PATRON_CABECERA.sub("", p.payload["page_content"]) for p in partes)
