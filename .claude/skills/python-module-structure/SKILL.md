---
name: python-module-structure
description: Orden canónico de los bloques de cabecera en cualquier archivo o módulo Python — docstring, imports, load_dotenv(), variables de entorno, constantes en mayúsculas. Use whenever creating a new .py file or restructuring an existing one, including scripts, modules, agents, RAG pipelines, ingest scripts, and utilities — o cuando el usuario mencione "estructura del script", "orden de los imports", "dónde va la configuración", "buenas prácticas de Python". Apply this layout by default unless the user explicitly says otherwise.
---

# Estructura de un archivo Python

Todo archivo `.py` que escribas o reestructures sigue este orden en la cabecera,
antes de la lógica. Es la preferencia estándar del usuario.

## El orden canónico

```python
# 1. DOCSTRING de módulo
"""
Qué hace este archivo, en una línea.

Contexto, decisiones no obvias, y qué lo diferencia de archivos parecidos
del mismo repo. Configuración previa que haga falta.

Ejecutar:
    python archivo.py
"""

# 2. IMPORTS — agrupados según PEP 8, separados por línea en blanco:
#    stdlib → terceros → locales
import os

from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient

from dotenv import load_dotenv

from validacion_nombre_tenant_id import validar_qdrant

# 3. LOAD_DOTENV() — después de TODOS los imports, nunca intercalado
load_dotenv()

# 4. VARIABLES DE ENTORNO que el archivo consume
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "tenant_id_datapath")

# 5. CONSTANTES en mayúsculas a nivel de módulo
RUTA_PDF = "Base_de_Conocimiento/documento.pdf"
TAMANO_CHUNK = 500
SOLAPAMIENTO_CHUNK = 200
MODELO_EMBEDDING = "text-embedding-ada-002"
```

## Regla de aplicación

Los cinco bloques son **condicionales pero ordenados**:

- Si el archivo no necesita `.env`, se omiten los bloques 3 y 4 juntos — nunca
  uno sin el otro.
- Si no hay nada parametrizable, se omite el bloque 5.
- El docstring (1) y los imports (2) están siempre.

**Lo que nunca cambia es el orden relativo.** Omitir un bloque no autoriza a
reordenar los demás.

## Por qué

No es solo estética. La configuración arriba hace que el archivo **falle rápido
y barato**: si `QDRANT_URL` falta, el script muere en milisegundos en vez de
cargar un PDF, trocearlo y gastar una llamada de embeddings para morir después.

Y quien abre el archivo ve en las primeras 40 líneas todo lo que necesita para
ejecutarlo, sin leer la lógica.

## Complementos

Cuando el archivo tenga precondiciones (variables obligatorias, rutas que deben
existir, nombres que deban cumplir una convención), agrúpalas en una función
`verificar_configuracion()` definida tras las constantes, y llámala como
**primera sentencia** del `if __name__ == '__main__':`. Misma lógica de fallar
antes de gastar nada.

Nombres: constantes en `MAYUSCULAS_CON_GUION_BAJO`. Se acepta usar mayúsculas
para config leída de entorno aunque técnicamente no sea constante literal — es
convención asentada. Evita caracteres no ASCII en identificadores (`TAMANO`, no
`TAMAÑO`), aunque Python 3 los permita.

## Conflicto conocido con las herramientas

Si el archivo ordena los imports por criterio didáctico (comentarios tipo
`# Paso 1: Document Loader` encima de cada import), **isort y Ruff los reordenan
alfabéticamente** y dejan cada comentario apuntando al import equivocado.

Cuando detectes ese patrón y el proyecto vaya a adoptar Ruff, avisa al usuario y
propone desactivar la regla de ordenado (`I`) en `pyproject.toml` en lugar de
aplicarla en silencio.
