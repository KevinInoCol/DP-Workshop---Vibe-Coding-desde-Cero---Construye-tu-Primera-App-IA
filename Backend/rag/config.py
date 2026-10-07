"""
Configuración compartida del RAG.

La usan tanto la ingesta (rag/ingesta.py) como la recuperación (rag/retriever.py).
Vive en un solo sitio a propósito: si la colección o el modelo de embeddings de la
ingesta y de la consulta no coinciden, la búsqueda devuelve basura o nada.
"""

import os

from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "tenant_id_alcaldia_girardota")

MODELO_EMBEDDING = "text-embedding-3-small"
