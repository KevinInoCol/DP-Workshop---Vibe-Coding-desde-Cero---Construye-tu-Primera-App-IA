"""
Tool de fecha y hora actual en Colombia.

Se calcula en cada llamada (no al arrancar el servidor) y siempre en la zona
horaria America/Bogota, sin importar dónde corra el Backend. Los nombres de
días y meses van en español sin depender del locale del sistema.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from langchain.tools import tool

ZONA_HORARIA = ZoneInfo("America/Bogota")
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


@tool
def obtener_fecha_hora_actual() -> str:
    """Devuelve la fecha, el día de la semana y la hora actuales en Girardota, Colombia.

    Úsala siempre que necesites saber qué día u hora es: cuando el ciudadano
    pregunte por la fecha o la hora, o use expresiones como "hoy", "mañana",
    "esta semana", "este mes" o "este año", o cuando haya que razonar sobre
    plazos o si una oficina podría estar abierta en este momento.
    """
    ahora = datetime.now(ZONA_HORARIA)
    return (
        f"Hoy es {DIAS[ahora.weekday()]} {ahora.day} de {MESES[ahora.month - 1]} "
        f"de {ahora.year}. Son las {ahora:%H:%M} (hora de Colombia, UTC-5). "
        f"Fecha ISO: {ahora:%Y-%m-%d}."
    )
