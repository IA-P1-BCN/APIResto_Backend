"""Búsqueda de texto sin distinguir acentos ni mayúsculas (HU-24).

Postgres trae `translate()` de serie; SQLite no, así que se registra una función
equivalente en cada conexión SQLite (tests y entorno local).
"""

import sqlite3

from sqlalchemy import event, func
from sqlalchemy.engine import Engine

ACCENTED = "áàäâãÁÀÄÂÃéèëêÉÈËÊíìïîÍÌÏÎóòöôõÓÒÖÔÕúùüûÚÙÜÛñÑçÇ"
PLAIN = "aaaaaaaaaaeeeeeeeeiiiiiiiioooooooooouuuuuuuunncc"
UNACCENT_TABLE = str.maketrans(ACCENTED, PLAIN)


def normalize_text(text: str) -> str:
    """Quita acentos y pasa a minúsculas, igual que `normalized_column` en SQL."""
    return text.translate(UNACCENT_TABLE).lower()


def normalized_column(column):
    """Expresión SQL de la columna sin acentos y en minúsculas."""
    return func.lower(func.translate(column, ACCENTED, PLAIN))


def _sqlite_translate(value: str | None, source: str, target: str) -> str | None:
    if value is None:
        return None
    return value.translate(str.maketrans(source, target))


@event.listens_for(Engine, "connect")
def _register_sqlite_translate(dbapi_connection, _connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.create_function(
            "translate", 3, _sqlite_translate, deterministic=True
        )
