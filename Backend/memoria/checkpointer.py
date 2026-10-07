"""
Memoria persistente de conversaciones: checkpointer de LangGraph en Postgres.

Cada conversación (thread_id = session_id del Frontend) se guarda en Postgres,
así sobrevive a reinicios del Backend y a recargas de uvicorn --reload.

Las tablas de PostgresSaver (checkpoints, checkpoint_blobs, checkpoint_writes,
checkpoint_migrations) tienen nombres fijos dentro de la librería, así que se
aíslan en un ESQUEMA propio (DB_SCHEMA) vía search_path, no con prefijos.
El esquema se crea con una conexión efímera ANTES de abrir el pool.

Se usa un ConnectionPool (no from_conn_string, que es un context manager) porque
la API es un proceso de larga duración: el pool vive mientras vive el servidor y
se cierra en el apagado (ver api.py).

Si POSTGRES_URL no está definida, cae a memoria en RAM con un aviso: el agente
funciona, pero olvida todo al reiniciar.
"""

import logging
import os

import psycopg
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from memoria.validacion_esquema_tenant import validar_esquema

load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL", "").strip()
DB_SCHEMA = os.getenv("DB_SCHEMA", "").strip()

MAX_CONEXIONES = 10

logger = logging.getLogger("agente.memoria")


def crear_checkpointer():
    """Devuelve (checkpointer, pool). El pool es None si la memoria es en RAM."""
    if not POSTGRES_URL:
        logger.warning("POSTGRES_URL no definida: memoria en RAM, se pierde al reiniciar.")
        return InMemorySaver(), None

    validacion = validar_esquema(DB_SCHEMA)
    if not validacion.ok:
        raise SystemExit(f"DB_SCHEMA inválido ({DB_SCHEMA!r}): {validacion.motivos}")

    try:
        with psycopg.connect(POSTGRES_URL, autocommit=True, connect_timeout=5) as conexion:
            conexion.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(DB_SCHEMA)))
    except psycopg.OperationalError:
        raise SystemExit(
            "No se pudo conectar a Postgres (POSTGRES_URL). "
            "¿Lo levantaste con 'docker compose up -d' en la raíz del proyecto?"
        )

    pool = ConnectionPool(
        POSTGRES_URL,
        max_size=MAX_CONEXIONES,
        kwargs={
            "autocommit": True,                         # requerido por PostgresSaver
            "prepare_threshold": 0,                     # sin prepared statements (compatible con poolers)
            "row_factory": dict_row,                    # PostgresSaver lee filas como dict
            "options": f"-c search_path={DB_SCHEMA}",   # sin "public" de respaldo, a propósito
        },
        open=True,
    )
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()      # crea las tablas la primera vez; idempotente
    logger.info("🗄️  Memoria persistente en Postgres (esquema '%s')", DB_SCHEMA)
    return checkpointer, pool
