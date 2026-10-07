"""
Validación de nombres de tenant para Qdrant y Pinecone.

La convención del repo es que toda colección/índice lleve el prefijo del tenant.
El problema es que cada motor acepta un juego de caracteres distinto, así que el
mismo tenant se escribe de dos formas:

    Qdrant   -> tenant_id_amazon_text     (guiones bajos, sin límite práctico)
    Pinecone -> tenant-id-amazon-text     (guiones, máximo 45 caracteres)

Pinecone es el estricto: el nombre del índice forma parte del hostname DNS al que
apunta el cliente, así que solo admite minúsculas alfanuméricas y '-'. Un guion
bajo o un punto hacen que la API rechace la creación.

Uso como script:

    python validacion_nombre_tenant_id.py                              # ejemplos del repo
    python validacion_nombre_tenant_id.py --qdrant tenant_id_amazon_text
    python validacion_nombre_tenant_id.py --pinecone tenant-id-ventas

Con --qdrant o --pinecone el código de salida es 1 si el nombre no vale para ese
motor, así que sirve como guardia en un script. Sin flag solo informa.

Uso como módulo:

    from validacion_nombre_tenant_id import validar_pinecone, a_nombre_pinecone

    resultado = validar_pinecone(nombre)
    if not resultado.ok:
        raise ValueError(resultado.motivos)
"""

import re
import sys
from dataclasses import dataclass, field

# Prefijos de la convención, uno por motor
PREFIJO_QDRANT = "tenant_id_"
PREFIJO_PINECONE = "tenant-id-"

# Pinecone: 1-45 caracteres, empieza y termina en alfanumérico,
# en medio solo minúsculas alfanuméricas o '-'
MAX_LONGITUD_PINECONE = 45
PATRON_PINECONE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

# Qdrant: el nombre acaba siendo una carpeta en disco y un segmento de URL,
# así que se rechazan los caracteres que romperían cualquiera de los dos.
CARACTERES_PROHIBIDOS_QDRANT = set('<>:"/\\|?*')


@dataclass
class Resultado:
    """Resultado de una validación: válido o no, y por qué no."""

    nombre: str
    motor: str
    motivos: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.motivos

    def __str__(self) -> str:
        if self.ok:
            return f"OK    [{self.motor}] {self.nombre!r}"
        detalle = "\n".join(f"        - {m}" for m in self.motivos)
        return f"ERROR [{self.motor}] {self.nombre!r}\n{detalle}"


def validar_pinecone(nombre: str, exigir_prefijo: bool = True) -> Resultado:
    """Valida un nombre de índice de Pinecone contra las reglas de la API."""
    r = Resultado(nombre=nombre, motor="pinecone")

    if not nombre:
        r.motivos.append("El nombre está vacío.")
        return r

    if len(nombre) > MAX_LONGITUD_PINECONE:
        r.motivos.append(
            f"Tiene {len(nombre)} caracteres y el máximo es {MAX_LONGITUD_PINECONE}. "
            f"Sobran {len(nombre) - MAX_LONGITUD_PINECONE}."
        )

    if "_" in nombre:
        r.motivos.append(
            "Contiene guion bajo '_', que Pinecone no admite. "
            f"Usa guion medio: {nombre.replace('_', '-')!r}"
        )

    if "." in nombre:
        r.motivos.append("Contiene punto '.', reservado para separar hosts en DNS.")

    if nombre != nombre.lower():
        r.motivos.append(f"Tiene mayúsculas. Debe ir todo en minúsculas: {nombre.lower()!r}")

    if not PATRON_PINECONE.match(nombre):
        # Solo detallamos si no lo explicó ya alguno de los casos de arriba
        if not r.motivos:
            r.motivos.append(
                "Debe empezar y terminar en alfanumérico y contener solo "
                "minúsculas alfanuméricas o '-'."
            )

    if exigir_prefijo and not nombre.startswith(PREFIJO_PINECONE):
        r.motivos.append(f"No empieza por el prefijo {PREFIJO_PINECONE!r} de la convención.")

    return r


def validar_qdrant(nombre: str, exigir_prefijo: bool = True) -> Resultado:
    """Valida un nombre de colección de Qdrant."""
    r = Resultado(nombre=nombre, motor="qdrant")

    if not nombre:
        r.motivos.append("El nombre está vacío.")
        return r

    prohibidos = sorted(set(nombre) & CARACTERES_PROHIBIDOS_QDRANT)
    if prohibidos:
        r.motivos.append(f"Contiene caracteres no permitidos: {' '.join(prohibidos)}")

    if any(ord(c) < 32 for c in nombre):
        r.motivos.append("Contiene caracteres de control.")

    if exigir_prefijo and not nombre.startswith(PREFIJO_QDRANT):
        r.motivos.append(f"No empieza por el prefijo {PREFIJO_QDRANT!r} de la convención.")

    return r


def a_nombre_pinecone(nombre: str) -> str:
    """Convierte un nombre estilo Qdrant a uno válido para Pinecone.

    tenant_id_amazon_text -> tenant-id-amazon-text

    No trunca si excede los 45 caracteres: acortar es una decisión de nombrado,
    no algo que deba pasar en silencio. Validá el resultado antes de usarlo.
    """
    convertido = re.sub(r"[^a-z0-9-]+", "-", nombre.lower().replace("_", "-"))
    return convertido.strip("-")


EJEMPLOS = [
    "tenant_id_amazon_text",
    "tenant_id_amazon_images",
    "tenant-id-asistente-de-ventas",
    "tenant-id-langchain-pinecone-asistente-de-ventas",  # 48 caracteres: se pasa
    "tenant_id_asistente",  # guion bajo: inválido en Pinecone
    "amazon-text",  # sin prefijo
]


def _demo() -> None:
    print("Sin argumentos: validando los nombres de ejemplo del repo.\n")
    for nombre in EJEMPLOS:
        print(validar_qdrant(nombre))
        print(validar_pinecone(nombre))
        equivalente = a_nombre_pinecone(nombre)
        if equivalente != nombre:
            print(f"        equivalente Pinecone -> {equivalente!r} "
                  f"({len(equivalente)} caracteres)")
        print()


def main(argv: list) -> int:
    # --qdrant / --pinecone acotan la validación a un motor, que es lo que hace
    # falta al usar esto como guardia. Sin flag, el nombre solo se considera malo
    # si no sirve para ninguno de los dos.
    motor = None
    if "--qdrant" in argv:
        motor = "qdrant"
        argv = [a for a in argv if a != "--qdrant"]
    elif "--pinecone" in argv:
        motor = "pinecone"
        argv = [a for a in argv if a != "--pinecone"]

    if not argv:
        _demo()
        return 0

    salida = 0
    for nombre in argv:
        q = validar_qdrant(nombre)
        p = validar_pinecone(nombre)

        if motor != "pinecone":
            print(q)
        if motor != "qdrant":
            print(p)
            if not p.ok:
                equivalente = a_nombre_pinecone(nombre)
                sugerencia = validar_pinecone(equivalente)
                marca = "válido" if sugerencia.ok else "sigue sin ser válido"
                print(f"        sugerencia Pinecone -> {equivalente!r} "
                      f"({len(equivalente)} caracteres, {marca})")
        print()

        if motor == "qdrant":
            fallo = not q.ok
        elif motor == "pinecone":
            fallo = not p.ok
        else:
            fallo = not q.ok and not p.ok  # no sirve para ningún motor
        if fallo:
            salida = 1
    return salida


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
