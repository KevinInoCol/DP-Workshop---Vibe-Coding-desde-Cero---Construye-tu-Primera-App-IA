"""Middleware del agente (hooks de LangChain v1 alrededor del modelo y de las tools)."""

from middleware.registro_tools import registrar_tools

MIDDLEWARE = [registrar_tools]
