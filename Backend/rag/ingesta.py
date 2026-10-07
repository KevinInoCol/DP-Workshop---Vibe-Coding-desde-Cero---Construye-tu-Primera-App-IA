"""
Pipeline de RAG en 4 pasos: carga los PDF de la base de conocimiento en Qdrant.

    1. Cargar     → lee cada PDF página por página (pypdf), quita el encabezado
                    repetido (su fecha queda como metadata), descarta las páginas
                    del índice y normaliza el texto (viñetas, espacios, saltos).
    2. Dividir    → chunking por ESTRUCTURA: un chunk por trámite completo
                    ("2.1.19 Trámite: ..."), con su código, nombre, dependencia y
                    páginas como metadata. Los trámites muy largos se parten en
                    partes que llevan el nombre del trámite como cabecera.
    3. Embeddings → convierte cada chunk en un vector (OpenAI).
    4. Guardar    → sube chunks + vectores a una colección de Qdrant.

Por qué por trámite y no por tamaño fijo: el manual es una lista de trámites, y
un corte cada N caracteres partía la lista de documentos requeridos de un
trámite y la mezclaba con el siguiente. Con un trámite = un chunk, la
recuperación devuelve siempre la lista completa (ver rag/retriever.py, que
reconstruye los trámites largos uniendo sus partes).

Cada ejecución RECREA la colección. La colección y el modelo de embeddings
vienen de rag/config.py, compartido con la recuperación. Requiere Qdrant arriba
(docker compose up -d, en la raíz) y OPENAI_API_KEY en Backend/.env.

Ejecutar (desde Backend/, como módulo):
    .venv/bin/python -m rag.ingesta
"""

import os
import re
from pathlib import Path

import pypdf
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient

from rag.config import MODELO_EMBEDDING, QDRANT_COLLECTION, QDRANT_URL
from rag.validacion_nombre_tenant_id import validar_qdrant

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CARPETA_CONOCIMIENTO = Path(__file__).parent / "Base de Conocimiento"

# Un trámite que quepa aquí va entero en un solo chunk; si no, se parte.
MAX_CARACTERES_TRAMITE = 3000
TAMANO_PARTE = 2000              # partes de trámites largos, sin solapamiento
TAMANO_CHUNK_GENERAL = 1000      # texto que no es un trámite (introducción, marco normativo)
SOLAPAMIENTO_GENERAL = 150
MIN_CARACTERES_GENERAL = 200     # fragmentos generales más cortos se descartan
MIN_LINEAS_INDICE = 10           # una página con tantas líneas "....... 12" es índice

# Encabezado que el manual repite en cada página ("Manual para la implementación
# de trámites · Código · Versión · Fecha · Página N de 95"). Es ruido para la
# búsqueda; se elimina del texto y su fecha se conserva como metadata.
PATRON_ENCABEZADO = re.compile(
    r"^\s*Manual para la implementación de\s+trámites\s+Código:.*?"
    r"Fecha:\s*(?P<fecha>\d{2}-\d{2}-\d{4}).*?Página \d+ de \d+\s*",
    re.DOTALL,
)
PATRON_LINEA_INDICE = re.compile(r"\.{4,}\s*\d*\s*$")
PATRON_TRAMITE = re.compile(r"^(?P<codigo>\d+\.\d+\.\d+)\s*Trámite\s*:\s*", re.M)
PATRON_SECCION = re.compile(
    r"^(?P<codigo>\d+\.\d+)\s+(?P<nombre>(?:SECRETAR[ÍI]A|ALCALD[ÍI]A)[^\n]*)$", re.M
)
PATRON_MARCA_PAGINA = re.compile(r"\n?<<P(\d+)>>\n?")


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
def limpiar_pagina(texto):
    """Quita el encabezado repetido. Devuelve (texto_limpio, fecha_o_None)."""
    coincidencia = PATRON_ENCABEZADO.match(texto)
    if not coincidencia:
        return texto, None
    return texto[coincidencia.end():], coincidencia.group("fecha")


def es_pagina_de_indice(texto):
    return sum(bool(PATRON_LINEA_INDICE.search(l)) for l in texto.split("\n")) >= MIN_LINEAS_INDICE


def normalizar_texto(texto):
    # Viñetas del PDF (caracteres de uso privado como U+F0B7) → "•"
    texto = re.sub(r"[-]", "•", texto)
    lineas = [re.sub(r"[ \t ]+", " ", linea).strip() for linea in texto.split("\n")]
    texto = "\n".join(linea for linea in lineas if linea)
    # "Tiempo de obtención: 45\ndía(s)\nhábil" → "45 día(s) hábil"
    return re.sub(r"\s*\n\s*(?=(día\(s\)|días?|hábil(es)?)\b)", " ", texto)


def cargar_pdfs(carpeta):
    documentos = []
    for ruta in sorted(carpeta.glob("*.pdf")):
        lector = pypdf.PdfReader(ruta)
        paginas, indice = [], 0
        for numero, pagina in enumerate(lector.pages, start=1):
            texto, fecha = limpiar_pagina(pagina.extract_text() or "")
            if es_pagina_de_indice(texto):
                indice += 1
                continue
            texto = normalizar_texto(texto)
            if not texto:
                continue
            metadata = {"source": ruta.name, "page": numero}
            if fecha:
                metadata["fecha_documento"] = fecha
            paginas.append(Document(page_content=texto, metadata=metadata))
        if not paginas:
            print(f"   ⚠️  {ruta.name}: sin texto extraíble (¿PDF escaneado?), se omite")
            continue
        print(f"   {ruta.name}: {len(paginas)} páginas con texto ({indice} de índice descartadas)")
        documentos.extend(paginas)
    return documentos


# ── Paso 2: Dividir por estructura ────────────────────────────────────────────
def unir_paginas(paginas):
    """Une las páginas de un PDF en un texto con marcas <<Pn>> para ubicar cada trámite."""
    return "".join(f"\n<<P{p.metadata['page']}>>\n{p.page_content}" for p in paginas)


def paginas_del_tramo(texto_completo, inicio, fin):
    previas = PATRON_MARCA_PAGINA.findall(texto_completo[:inicio])
    internas = PATRON_MARCA_PAGINA.findall(texto_completo[inicio:fin])
    numeros = [int(n) for n in previas[-1:] + internas]
    return min(numeros), max(numeros)


def nombre_del_tramite(texto):
    cuerpo = PATRON_TRAMITE.sub("", texto, count=1)
    nombre = re.split(r"Propósito\s*:", cuerpo, maxsplit=1)[0]
    if nombre == cuerpo:                       # sin "Propósito": basta la primera línea
        nombre = cuerpo.split("\n", 1)[0]
    return " ".join(nombre.split()).rstrip(" .")[:200]


def chunks_de_tramite(texto, metadata_base):
    """Un chunk si el trámite cabe; si no, partes con el nombre como cabecera."""
    cabecera = (
        f"Trámite {metadata_base['codigo']}: {metadata_base['tramite']}\n"
        f"Dependencia: {metadata_base['dependencia']}"
    )
    if len(texto) <= MAX_CARACTERES_TRAMITE:
        partes = [texto]
    else:
        divisor = RecursiveCharacterTextSplitter(chunk_size=TAMANO_PARTE, chunk_overlap=0)
        partes = divisor.split_text(texto)

    chunks = []
    for n, parte in enumerate(partes, start=1):
        encabezado = cabecera if len(partes) == 1 else f"{cabecera}\n(parte {n} de {len(partes)})"
        chunks.append(Document(
            page_content=f"{encabezado}\n\n{parte}",
            metadata={**metadata_base, "parte": n, "total_partes": len(partes)},
        ))
    return chunks


def dividir_por_tramite(paginas):
    chunks = []
    por_pdf = {}
    for p in paginas:
        por_pdf.setdefault(p.metadata["source"], []).append(p)

    for source, paginas_pdf in por_pdf.items():
        fecha = next((p.metadata.get("fecha_documento") for p in paginas_pdf
                      if p.metadata.get("fecha_documento")), None)
        texto = unir_paginas(paginas_pdf)
        secciones = {m["codigo"]: " ".join(m["nombre"].split()).rstrip(" .")
                     for m in PATRON_SECCION.finditer(texto)}
        tramites = list(PATRON_TRAMITE.finditer(texto))
        # Un trámite termina donde empieza el siguiente trámite o una nueva sección.
        cortes = sorted({m.start() for m in tramites} | {m.start() for m in PATRON_SECCION.finditer(texto)})
        cortes.append(len(texto))

        cubierto = []
        for m in tramites:
            inicio = m.start()
            fin = next(c for c in cortes if c > inicio)
            cubierto.append((inicio, fin))
            pagina_inicio, pagina_fin = paginas_del_tramo(texto, inicio, fin)
            cuerpo = PATRON_MARCA_PAGINA.sub("\n", texto[inicio:fin]).strip()
            codigo = m["codigo"]
            metadata = {
                "source": source,
                "tipo": "tramite",
                "codigo": codigo,
                "tramite": nombre_del_tramite(cuerpo),
                "dependencia": secciones.get(codigo.rsplit(".", 1)[0], "No especificada en el manual"),
                "pagina_inicio": pagina_inicio,
                "pagina_fin": pagina_fin,
            }
            if fecha:
                metadata["fecha_documento"] = fecha
            chunks.extend(chunks_de_tramite(cuerpo, metadata))

        # Texto que no pertenece a ningún trámite: introducción, objetivos, marco normativo.
        divisor = RecursiveCharacterTextSplitter(
            chunk_size=TAMANO_CHUNK_GENERAL, chunk_overlap=SOLAPAMIENTO_GENERAL
        )
        limites = [0] + [x for tramo in cubierto for x in tramo] + [len(texto)]
        for inicio, fin in zip(limites[::2], limites[1::2]):
            cuerpo = PATRON_MARCA_PAGINA.sub("\n", texto[inicio:fin]).strip()
            if len(cuerpo) < MIN_CARACTERES_GENERAL:
                continue
            pagina_inicio, pagina_fin = paginas_del_tramo(texto, inicio, fin)
            for parte in divisor.split_text(cuerpo):
                metadata = {"source": source, "tipo": "general",
                            "pagina_inicio": pagina_inicio, "pagina_fin": pagina_fin}
                if fecha:
                    metadata["fecha_documento"] = fecha
                chunks.append(Document(page_content=parte, metadata=metadata))
    return chunks


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
    paginas = cargar_pdfs(CARPETA_CONOCIMIENTO)
    if not paginas:
        raise SystemExit("Ningún PDF tenía texto extraíble. Nada que indexar.")

    print("[2/4] Dividiendo por trámite...")
    chunks = dividir_por_tramite(paginas)
    tramites = {c.metadata["codigo"] for c in chunks if c.metadata["tipo"] == "tramite"}
    partidos = {c.metadata["codigo"] for c in chunks if c.metadata.get("total_partes", 1) > 1}
    generales = sum(c.metadata["tipo"] == "general" for c in chunks)
    print(f"   {len(tramites)} trámites ({len(partidos)} largos partidos en varias partes) "
          f"+ {generales} chunks generales = {len(chunks)} chunks")

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
