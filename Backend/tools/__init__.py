"""Tools disponibles para el agente de la Alcaldía de Girardota."""

from tools.base_conocimiento import buscar_en_base_de_conocimiento
from tools.busqueda_web import buscar_en_internet
from tools.fecha_hora import obtener_fecha_hora_actual

TOOLS = [buscar_en_base_de_conocimiento, buscar_en_internet, obtener_fecha_hora_actual]
