"""
Agente de atención ciudadana de la Alcaldía de Girardota (Antioquia, Colombia).

Agente con LangChain v1 (create_agent). Las tools viven en tools/ (RAG sobre
el Manual de Trámites, búsqueda en internet y fecha/hora) y el middleware en
middleware/ (registro de cada uso de tool en la terminal). La memoria de cada
conversación vive en un checkpointer en Postgres (memoria/), separada por
thread_id, así que sobrevive a reinicios.

El system prompt vive en prompt/system_prompt.yaml (formato de tags) y la
configuración del modelo en model_config/model_config.yaml. Requiere
OPENAI_API_KEY en un archivo .env.

Ejecutar (chat por terminal):
    .venv/bin/python agent.py

La API para el Frontend está en api.py.
"""

import logging
import os
import time
import uuid
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from memoria import crear_checkpointer
from middleware import MIDDLEWARE
from tools import TOOLS

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

BASE_DIR = Path(__file__).parent
RUTA_PROMPT = BASE_DIR / "prompt" / "system_prompt.yaml"
RUTA_MODEL_CONFIG = BASE_DIR / "model_config" / "model_config.yaml"

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-7s | %(name)-13s | %(message)s",
    datefmt="%H:%M:%S",
)
# Las librerías HTTP registran cada petición a OpenAI/Qdrant: demasiado ruido.
for ruidoso in ("httpx", "httpx2", "httpcore", "openai", "urllib3"):
    logging.getLogger(ruidoso).setLevel(logging.WARNING)
logger = logging.getLogger("agente")


def verificar_configuracion():
    if not OPENAI_API_KEY:
        raise SystemExit("Falta OPENAI_API_KEY en el archivo .env")
    for ruta in (RUTA_PROMPT, RUTA_MODEL_CONFIG):
        if not ruta.exists():
            raise SystemExit(f"No se encuentra {ruta}")


def cargar_yaml(ruta):
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def construir_system_prompt(bot_name):
    prompt_cfg = cargar_yaml(RUTA_PROMPT)
    return prompt_cfg["system_prompt"].replace("{bot_name}", bot_name)


def crear_agente(checkpointer):
    cfg = cargar_yaml(RUTA_MODEL_CONFIG)
    modelo_cfg = cfg["model"]

    modelo = init_chat_model(
        f"{modelo_cfg['provider']}:{modelo_cfg['name']}",
        temperature=modelo_cfg["temperature"],
        max_tokens=modelo_cfg["max_tokens"],
        timeout=modelo_cfg["timeout"],
        max_retries=modelo_cfg["max_retries"],
    )

    return create_agent(
        modelo,
        tools=TOOLS,
        system_prompt=construir_system_prompt(cfg["agent"]["bot_name"]),
        checkpointer=checkpointer,
        middleware=MIDDLEWARE,
    )


def responder(agente, thread_id, mensaje):
    logger.info("💬 [%s] %s", thread_id[:8], mensaje[:150])
    inicio = time.perf_counter()
    resultado = agente.invoke(
        {"messages": [{"role": "user", "content": mensaje}]},
        {"configurable": {"thread_id": thread_id}},
    )
    respuesta = resultado["messages"][-1].content
    logger.info("🤖 [%s] respuesta de %d caracteres en %.2fs",
                thread_id[:8], len(respuesta), time.perf_counter() - inicio)
    return respuesta


def obtener_historial(agente, thread_id):
    """Mensajes visibles de una conversación (usuario y respuestas finales), en orden.

    Omite los mensajes internos: llamadas a tools y sus resultados.
    """
    estado = agente.get_state({"configurable": {"thread_id": thread_id}})
    historial = []
    for mensaje in estado.values.get("messages", []):
        if mensaje.type == "human":
            historial.append({"role": "user", "content": mensaje.content})
        elif mensaje.type == "ai" and isinstance(mensaje.content, str) and mensaje.content.strip():
            historial.append({"role": "assistant", "content": mensaje.content})
    return historial


def chatear():
    checkpointer, pool = crear_checkpointer()
    agente = crear_agente(checkpointer)
    thread_id = str(uuid.uuid4())
    print("Asistente de la Alcaldía de Girardota. Escriba 'salir' para terminar.\n")

    try:
        while True:
            consulta = input("Usted: ").strip()
            if consulta.lower() in {"salir", "exit", "quit"}:
                break
            if not consulta:
                continue

            print(f"\nAsistente: {responder(agente, thread_id, consulta)}\n")
    finally:
        if pool:
            pool.close()


if __name__ == "__main__":
    verificar_configuracion()
    chatear()
