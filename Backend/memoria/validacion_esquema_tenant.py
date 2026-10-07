"""
Validación de nombres de ESQUEMA de tenant para Postgres / Supabase.

La convención del repo es que cada inquilino viva en su propio esquema, y que el
nombre del esquema salga de UNA variable de entorno (`DB_SCHEMA`). Este validador
es la guardia que se pone antes de usarlo, por dos razones:

  1. El nombre se interpola en DDL (`CREATE SCHEMA {x}`), donde NO se pueden usar
     parámetros de consulta: sin validar, es una vía de inyección SQL.
  2. Postgres corta los identificadores a 63 BYTES en silencio. Un nombre más
     largo no falla: se trunca, y de pronto dos tenants comparten esquema.
     Ojo: son bytes, no caracteres — una 'ñ' o un acento en UTF-8 ocupan 2.

Reglas aplicadas (deliberadamente más estrictas que Postgres):

    - solo minúsculas, dígitos y guiones bajos
    - empieza por letra o '_' (nunca por dígito)
    - 1 a 63 bytes en UTF-8
    - no puede empezar por 'pg_' (reservado por Postgres)
    - no puede ser una palabra reservada obvia ni un esquema del sistema

Se rechazan mayúsculas y guiones a propósito: Postgres los aceptaría CITANDO el
identificador (`"Campana-Madeline"`), pero entonces hay que citarlo en todas
partes y cualquier consulta que se olvide falla con "relation does not exist".
Minúsculas y guiones bajos evitan esa clase entera de bugs.

Uso como script:

    python validacion_esquema_tenant.py                      # ejemplos
    python validacion_esquema_tenant.py campana_madeline     # exit 1 si no vale

Uso como módulo:

    from validacion_esquema_tenant import validar_esquema

    v = validar_esquema(os.getenv("DB_SCHEMA", ""))
    if not v.ok:
        raise ValueError(f"DB_SCHEMA inválido: {v.motivos}")
"""

import re
import sys
import unicodedata
from dataclasses import dataclass, field

MAX_BYTES_IDENTIFICADOR = 63          # límite duro de Postgres (NAMEDATALEN - 1)
PATRON_ESQUEMA = re.compile(r"^[a-z_][a-z0-9_]*$")

# Esquemas que ya existen o están reservados: usarlos mezcla los datos del tenant
# con los del sistema o con los de otro inquilino.
ESQUEMAS_RESERVADOS = frozenset({
    "public", "information_schema",
    # Supabase
    "auth", "storage", "realtime", "supabase_functions", "supabase_migrations",
    "graphql", "graphql_public", "extensions", "vault", "pgsodium", "cron", "net",
})


@dataclass
class Resultado:
    """Resultado de una validación: válido o no, y por qué no."""

    nombre: str
    motivos: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.motivos

    def __str__(self) -> str:
        if self.ok:
            return f"OK    [postgres] esquema {self.nombre!r}"
        return f"FALLA [postgres] esquema {self.nombre!r}: " + "; ".join(self.motivos)


def validar_esquema(nombre: str, *, permitir_public: bool = False) -> Resultado:
    """Valida un nombre de esquema de tenant.

    `permitir_public=True` acepta 'public' como valor legítimo, para el caso en que
    la app use el esquema por defecto (proyecto de un solo tenant).
    """
    r = Resultado(nombre=nombre)

    if not nombre or not nombre.strip():
        r.motivos.append("está vacío")
        return r
    if nombre != nombre.strip():
        r.motivos.append("tiene espacios al inicio o al final")

    n = nombre.strip()

    if not PATRON_ESQUEMA.match(n):
        r.motivos.append(
            "solo se admiten minúsculas, dígitos y guiones bajos, empezando por "
            "letra o '_' (nada de mayúsculas, guiones, puntos, espacios ni acentos)"
        )

    largo = len(n.encode("utf-8"))
    if largo > MAX_BYTES_IDENTIFICADOR:
        r.motivos.append(
            f"ocupa {largo} bytes y Postgres corta en {MAX_BYTES_IDENTIFICADOR} "
            "(el truncado es SILENCIOSO: dos tenants podrían acabar en el mismo esquema)"
        )
    if any(unicodedata.combining(c) or ord(c) > 127 for c in n):
        r.motivos.append("contiene caracteres no ASCII: usá el nombre sin acentos ni 'ñ'")

    if n.startswith("pg_"):
        r.motivos.append("empieza por 'pg_', prefijo reservado por Postgres")
    if n in ESQUEMAS_RESERVADOS and not (permitir_public and n == "public"):
        r.motivos.append(
            f"'{n}' es un esquema reservado o del sistema: elegí uno propio del tenant"
        )
    return r


def a_nombre_esquema(texto: str, prefijo: str = "") -> str:
    """Convierte un texto libre en un nombre de esquema válido.

    'Campaña Madeline Cañizares' + prefijo 'campana_' -> 'campana_madeline_canizares'
    Quita acentos, pasa a minúsculas, colapsa lo no alfanumérico en '_' y recorta a
    63 bytes sin cortar a mitad de una palabra si se puede evitar.
    """
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)
    )
    base = re.sub(r"[^a-z0-9]+", "_", sin_acentos.lower()).strip("_")
    # Si el texto ya empieza por el prefijo, no lo dupliques: 'Campaña Madeline' con
    # prefijo 'campana_' debe dar 'campana_madeline', no 'campana_campana_madeline'.
    raiz = prefijo.strip("_")
    if raiz and base.startswith(f"{raiz}_"):
        base = base[len(raiz) + 1:]
    elif raiz and base == raiz:
        base = ""
    candidato = f"{prefijo}{base}".strip("_")
    if not candidato or candidato[0].isdigit():
        candidato = f"t_{candidato}"
    while len(candidato.encode("utf-8")) > MAX_BYTES_IDENTIFICADOR:
        if "_" in candidato:
            candidato = candidato.rsplit("_", 1)[0]
        else:
            candidato = candidato.encode("utf-8")[:MAX_BYTES_IDENTIFICADOR].decode(
                "utf-8", errors="ignore"
            )
    return candidato


def _ejemplos() -> None:
    print("Convención: un ESQUEMA por tenant en Postgres/Supabase.\n")
    casos = [
        "campana_madeline",
        "campana_madeline_2026",
        "public",
        "Campana-Madeline",
        "1campana",
        "campana_ñoño",
        'campana"; drop schema public cascade; --',
        "pg_temp_1",
        "auth",
        "c" * 64,
    ]
    for c in casos:
        print("  " + str(validar_esquema(c)))
    print("\nNormalización de texto libre:")
    for t in ["Campaña Madeline Cañizares", "Ibarra Avanza Contigo"]:
        print(f"  {t!r} -> {a_nombre_esquema(t, 'campana_')!r}")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        _ejemplos()
        return 0
    salida = 0
    for nombre in args:
        r = validar_esquema(nombre, permitir_public="--permitir-public" in sys.argv)
        print(str(r))
        if not r.ok:
            salida = 1
    return salida


if __name__ == "__main__":
    raise SystemExit(main())
