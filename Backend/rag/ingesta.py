"""
Pipeline básico de RAG en 4 pasos: carga los PDF de la base de conocimiento en Qdrant.

    1. Cargar    → lee cada PDF de "Base de Conocimiento/" página por página (pypdf)
    2. Dividir   → trocea el texto en chunks con solapamiento
    3. Embeddings → convierte cada chunk en un vector (OpenAI)
    4. Guardar   → sube chunks + vectores a una colección de Qdrant

Cada ejecución RECREA la colección desde cero, así que se puede volver a correr
tras cambiar o añadir PDFs sin duplicar datos. La carga de PDF usa pypdf directo
(como la guía oficial de LangChain v1) en vez de PyPDFLoader, que vive en
langchain-community, un paquete en retirada.

Requiere Qdrant arriba (docker compose up -d, en la raíz del proyecto) y
OPENAI_API_KEY en Backend/.env.

Ejecutar (desde Backend/):
    .venv/bin/python rag/ingesta.py
"""

import os
from pathlib import Path

import pypdf
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient

from validacion_nombre_tenant_id import validar_qdrant

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "tenant_id_alcaldia_girardota")

CARPETA_CONOCIMIENTO = Path(__file__).parent / "Base de Conocimiento"
TAMANO_CHUNK = 1000
SOLAPAMIENTO_CHUNK = 200
MODELO_EMBEDDING = "text-embedding-3-small"


def verificar_configuracion():
    if not OPENAI_API_KEY:
        raise SystemExit("Falta OPENAI_API_KEY en Backend/.env")

    validacion = validar_qdrant(QDRANT_COLLECTION)
    if not validacion.ok:
        raise SystemExit(f"Nombre de colección inválido: {validacion.motivos}")

    if not sorted(CARPETA_CONOCIMIENTO.glob("*.pdf")):
        raise SystemExit(f"No hay archivos PDF en {CARPETA_CONOCIMIENTO}")

    try:
        QdrantClient(url=QDRANT_URL).get_collections()
    except Exception:
        raise SystemExit(
            f"No se pudo conectar a Qdrant en {QDRANT_URL}. "
            "¿Lo levantaste con 'docker compose up -d'?"
        )


# ── Paso 1: Cargar ────────────────────────────────────────────────────────────
def cargar_pdfs(carpeta):
    documentos = []
    for ruta in sorted(carpeta.glob("*.pdf")):
        lector = pypdf.PdfReader(ruta)
        paginas = [
            Document(
                page_content=pagina.extract_text() or "",
                metadata={"source": ruta.name, "page": numero},
            )
            for numero, pagina in enumerate(lector.pages, start=1)
        ]
        paginas = [p for p in paginas if p.page_content.strip()]
        if not paginas:
            print(f"   ⚠️  {ruta.name}: sin texto extraíble (¿PDF escaneado?), se omite")
            continue
        print(f"   {ruta.name}: {len(paginas)} páginas con texto")
        documentos.extend(paginas)
    return documentos


# ── Paso 2: Dividir ───────────────────────────────────────────────────────────
def dividir_en_chunks(documentos):
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=TAMANO_CHUNK,
        chunk_overlap=SOLAPAMIENTO_CHUNK,
        add_start_index=True,
    )
    return divisor.split_documents(documentos)


# ── Paso 3: Embeddings ────────────────────────────────────────────────────────
def crear_embeddings():
    return OpenAIEmbeddings(model=MODELO_EMBEDDING)


# ── Paso 4: Guardar en Qdrant ─────────────────────────────────────────────────
def guardar_en_qdrant(chunks, embeddings):
    return QdrantVectorStore.from_documents(
        chunks,
        embeddings,
        url=QDRANT_URL,
        collection_name=QDRANT_COLLECTION,
        force_recreate=True,
    )


def main():
    print(f"[1/4] Cargando PDFs de '{CARPETA_CONOCIMIENTO.name}'...")
    documentos = cargar_pdfs(CARPETA_CONOCIMIENTO)
    if not documentos:
        raise SystemExit("Ningún PDF tenía texto extraíble. Nada que indexar.")

    print(f"[2/4] Dividiendo en chunks de {TAMANO_CHUNK} caracteres (solapamiento {SOLAPAMIENTO_CHUNK})...")
    chunks = dividir_en_chunks(documentos)
    print(f"   {len(chunks)} chunks")

    print(f"[3/4] Preparando embeddings con {MODELO_EMBEDDING}...")
    embeddings = crear_embeddings()

    print(f"[4/4] Guardando en Qdrant ({QDRANT_URL}) → colección '{QDRANT_COLLECTION}'...")
    guardar_en_qdrant(chunks, embeddings)

    total = QdrantClient(url=QDRANT_URL).count(QDRANT_COLLECTION).count
    print(f"\n✅ Ingesta completa: {total} vectores en '{QDRANT_COLLECTION}'")
    print(f"   Dashboard: {QDRANT_URL}/dashboard")


if __name__ == "__main__":
    verificar_configuracion()
    main()
