"""
API REST (FastAPI) que expone el agente de la Alcaldía de Girardota al Frontend.

El Frontend envía cada mensaje con un session_id propio; ese id se usa como
thread_id del checkpointer, así cada pestaña del chat conserva su conversación.
Las conversaciones se guardan en Postgres (memoria/): sobreviven a reinicios.
El pool de conexiones se abre al arrancar y se cierra al apagar el servidor.

Ejecutar:
    .venv/bin/uvicorn api:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import crear_agente, obtener_historial, responder, verificar_configuracion
from memoria import crear_checkpointer

load_dotenv()

FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")

verificar_configuracion()
checkpointer, pool = crear_checkpointer()
agente = crear_agente(checkpointer)


@asynccontextmanager
async def ciclo_de_vida(app):
    yield
    if pool:
        pool.close()


app = FastAPI(title="Agente Alcaldía de Girardota", lifespan=ciclo_de_vida)
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str


class Mensaje(BaseModel):
    role: str
    content: str


class HistorialResponse(BaseModel):
    session_id: str
    messages: list[Mensaje]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        reply = await run_in_threadpool(responder, agente, req.session_id, req.message)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="El agente no pudo responder.") from exc
    return ChatResponse(reply=reply)


@app.get("/api/historial/{session_id}", response_model=HistorialResponse)
async def historial(session_id: str):
    """Devuelve la conversación guardada para que el Frontend la retome al recargar."""
    if not 0 < len(session_id) <= 100:
        raise HTTPException(status_code=422, detail="session_id inválido.")
    try:
        mensajes = await run_in_threadpool(obtener_historial, agente, session_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="No se pudo leer el historial.") from exc
    return HistorialResponse(session_id=session_id, messages=mensajes)
