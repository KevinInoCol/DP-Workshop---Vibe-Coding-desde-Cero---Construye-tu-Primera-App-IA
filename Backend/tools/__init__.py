"""Tools disponibles para el agente de la Alcaldía de Girardota."""

from tools.busqueda_web import buscar_en_internet
from tools.fecha_hora import obtener_fecha_hora_actual

TOOLS = [obtener_fecha_hora_actual, buscar_en_internet]
