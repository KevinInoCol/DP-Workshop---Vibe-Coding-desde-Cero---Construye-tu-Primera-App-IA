"""
API REST (FastAPI) que expone el agente de la Alcaldía de Girardota al Frontend.

El Frontend envía cada mensaje con un session_id propio; ese id se usa como
thread_id del checkpointer, así cada pestaña del chat conserva su conversación.
La memoria es volátil: se pierde al reiniciar el servidor.

Ejecutar:
    .venv/bin/uvicorn api:app --reload --port 8000
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import crear_agente, responder, verificar_configuracion

load_dotenv()

FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")

verificar_configuracion()
agente = crear_agente()

app = FastAPI(title="Agente Alcaldía de Girardota")
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
