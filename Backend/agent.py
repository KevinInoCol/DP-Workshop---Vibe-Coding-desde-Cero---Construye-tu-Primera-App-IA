"""
Agente de atención ciudadana de la Alcaldía de Girardota (Antioquia, Colombia).

Agente básico con LangChain v1 (create_agent): sin tools ni RAG. La memoria de
cada conversación vive en un checkpointer en memoria, separada por thread_id. El system prompt
vive en prompt/system_prompt.yaml (formato de tags) y la configuración del modelo
en model_config/model_config.yaml. Requiere OPENAI_API_KEY en un archivo .env.

Ejecutar (chat por terminal):
    .venv/bin/python agent.py

La API para el Frontend está en api.py.
"""

import os
import uuid
from datetime import date
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

BASE_DIR = Path(__file__).parent
RUTA_PROMPT = BASE_DIR / "prompt" / "system_prompt.yaml"
RUTA_MODEL_CONFIG = BASE_DIR / "model_config" / "model_config.yaml"


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
    return (
        prompt_cfg["system_prompt"]
        .replace("{bot_name}", bot_name)
        .replace("{fecha_actual}", date.today().isoformat())
    )


def crear_agente():
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
        tools=[],
        system_prompt=construir_system_prompt(cfg["agent"]["bot_name"]),
        checkpointer=InMemorySaver(),
    )


def responder(agente, thread_id, mensaje):
    resultado = agente.invoke(
        {"messages": [{"role": "user", "content": mensaje}]},
        {"configurable": {"thread_id": thread_id}},
    )
    return resultado["messages"][-1].content


def chatear():
    agente = crear_agente()
    thread_id = str(uuid.uuid4())
    print("Asistente de la Alcaldía de Girardota. Escriba 'salir' para terminar.\n")

    while True:
        consulta = input("Usted: ").strip()
        if consulta.lower() in {"salir", "exit", "quit"}:
            break
        if not consulta:
            continue

        print(f"\nAsistente: {responder(agente, thread_id, consulta)}\n")


if __name__ == "__main__":
    verificar_configuracion()
    chatear()
