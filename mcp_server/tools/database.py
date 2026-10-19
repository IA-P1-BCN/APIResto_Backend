"""Herramienta query_database: una consulta SQL de solo lectura contra la BD local (R-02)."""

import datetime
import decimal
import json
import logging
import re
import time
import uuid
from functools import lru_cache
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.exc import SQLAlchemyError

from mcp_server.config import get_settings

logger = logging.getLogger("mcp_server.tools.database")

ALLOWED_FIRST_KEYWORDS = frozenset({"SELECT", "WITH"})

FORBIDDEN_KEYWORDS = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
        "COPY",
        "CALL",
        "DO",
        "SET",
        "LOCK",
        "VACUUM",
        "REINDEX",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "COMMENT",
        "INTO",
    }
)

SECRET_COLUMNS = frozenset(
    {"password_hash", "token_hash", "totp_secret", "totp_recovery_codes"}
)

SECRET_TABLES = frozenset(
    {
        "refresh_tokens",
        "revoked_tokens",
        "email_verification_tokens",
        "password_reset_tokens",
    }
)

SECRET_IDENTIFIERS = SECRET_COLUMNS | SECRET_TABLES

REDACTED = "***"
BYTES_PLACEHOLDER = "<bytes>"
MAX_ERROR_DETAIL_LENGTH = 200

BCRYPT_PATTERN = re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}")
FERNET_PATTERN = re.compile(r"gAAAAA[A-Za-z0-9_\-=]{20,}")
SHA256_HEX_PATTERN = re.compile(r"\b[0-9a-fA-F]{64}\b")
SECRET_VALUE_PATTERNS = (BCRYPT_PATTERN, FERNET_PATTERN, SHA256_HEX_PATTERN)
UNICODE_ESCAPE_IDENTIFIER_PATTERN = re.compile(r"\bU&\s*\"", re.IGNORECASE)

_WORD_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_FIRST_WORD_PATTERN = re.compile(r"[A-Za-z_]+")


def _reject(code: str, detail: str) -> ToolError:
    """Registra el rechazo (solo el code) y devuelve el ToolError para lanzarlo."""
    logger.warning("query_database rejected code=%s", code)
    return ToolError(f"{code}: {detail}")


def _words(sql: str) -> list[str]:
    """Palabras (identificadores y palabras clave) del texto, en el orden en que aparecen."""
    return _WORD_PATTERN.findall(sql)


def _check_not_empty(sql: str) -> None:
    """Rechaza una consulta vacía o solo con espacios."""
    if (
        not isinstance(sql, str)
        or not sql.strip()
        or not sql.strip().rstrip(";").strip()
    ):
        raise _reject("empty_query", "the query is empty")


def _check_single_statement(sql: str) -> None:
    """Rechaza un ';' que no sea el último carácter (una sola sentencia)."""
    if ";" in sql.strip()[:-1]:
        raise _reject("multiple_statements", "only one statement is allowed")


def _check_first_keyword(sql: str) -> None:
    """Exige que la consulta empiece por SELECT o WITH."""
    match = _FIRST_WORD_PATTERN.match(sql.strip())
    if match is None or match.group(0).upper() not in ALLOWED_FIRST_KEYWORDS:
        raise _reject("read_only", "the query must start with SELECT or WITH")


def _check_forbidden_keywords(sql: str) -> None:
    """Rechaza cualquier palabra prohibida como palabra completa, incluso dentro de un literal."""
    for word in _words(sql):
        if word.upper() in FORBIDDEN_KEYWORDS:
            raise _reject("read_only", f"keyword '{word.upper()}' is not allowed")


def _check_no_secrets(sql: str) -> None:
    """Rechaza la consulta si menciona una columna o tabla secreta (R-02)."""
    for word in _words(sql):
        if word.lower() in SECRET_IDENTIFIERS:
            raise _reject(
                "secret_not_allowed",
                f"secret column or table '{word.lower()}' is not allowed",
            )


def _check_no_unicode_escapes(sql: str) -> None:
    """Rechaza identificadores U&"..." de Postgres: ocultarían un nombre secreto."""
    if UNICODE_ESCAPE_IDENTIFIER_PATTERN.search(sql):
        raise _reject(
            "secret_not_allowed",
            'unicode escaped identifiers (U&"...") are not allowed',
        )


def validate_sql(sql: str) -> str:
    """Valida el texto de la consulta y la devuelve sin espacios ni ';' final."""
    _check_not_empty(sql)
    _check_single_statement(sql)
    _check_first_keyword(sql)
    _check_forbidden_keywords(sql)
    _check_no_unicode_escapes(sql)
    _check_no_secrets(sql)
    return sql.strip().rstrip(";").strip()


def _resolve_limit(limit: int | None, max_rows: int) -> int:
    """Devuelve el tope de filas: limit recortado a max_rows; limit < 1 es un error."""
    if limit is None:
        return max_rows
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise _reject("invalid_limit", "limit must be an integer greater than 0")
    return min(limit, max_rows)


@lru_cache
def get_engine() -> Engine:
    """Crea el motor de SQLAlchemy la primera vez que se usa (no al importar)."""
    settings = get_settings()
    url = settings.database_url
    connect_args: dict[str, Any] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif url.startswith("postgresql"):
        connect_args["connect_timeout"] = settings.MCP_QUERY_TIMEOUT_SECONDS
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def _enter_read_only(conn: Connection, timeout_seconds: int | None) -> None:
    """Pone la conexión o la transacción en solo lectura según el dialecto."""
    dialect = conn.dialect.name
    if dialect == "postgresql":
        if timeout_seconds is None:
            timeout_seconds = get_settings().MCP_QUERY_TIMEOUT_SECONDS
        timeout_ms = int(timeout_seconds) * 1000
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        conn.exec_driver_sql(f"SET LOCAL statement_timeout = {timeout_ms}")
    elif dialect == "sqlite":
        conn.exec_driver_sql("PRAGMA query_only = ON")
    else:
        raise _reject("query_failed", f"unsupported database dialect '{dialect}'")


def _execute_read_only(
    conn: Connection,
    sql: str,
    max_rows: int,
    timeout_seconds: int | None = None,
) -> tuple[list[str], list[tuple], bool]:
    """Ejecuta sql en solo lectura y devuelve (columnas, filas, truncated); rollback siempre.

    No valida el texto: esa es la capa 1. Los errores de la BD salen como SQLAlchemyError.
    """
    try:
        _enter_read_only(conn, timeout_seconds)
        result = conn.exec_driver_sql(sql)
        if not result.returns_rows:
            return [], [], False
        columns = list(map(str, result.keys()))
        fetched = result.fetchmany(max_rows + 1)
        result.close()
    finally:
        conn.rollback()
    truncated = len(fetched) > max_rows
    return columns, [tuple(row) for row in fetched[:max_rows]], truncated


def _serialize(value: Any) -> Any:
    """Convierte un valor de la BD en algo que se puede enviar como JSON."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return BYTES_PLACEHOLDER
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_serialize(item) for item in value]
    return str(value)


def _contains_secret_value(text: str) -> bool:
    """Indica si el texto contiene un hash bcrypt, un token Fernet o un SHA-256 en hexadecimal."""
    return any(pattern.search(text) for pattern in SECRET_VALUE_PATTERNS)


def _redact_json(value: Any) -> Any:
    """Recorre un JSON: tapa las claves secretas y las hojas de texto con forma de secreto."""
    if isinstance(value, dict):
        return {
            key: REDACTED if key.lower() in SECRET_COLUMNS else _redact_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    if isinstance(value, str):
        return REDACTED if _contains_secret_value(value) else value
    return value


def _parse_json_container(text: str) -> Any:
    """Devuelve el dict o la lista si el texto es un JSON de ese tipo; si no, None."""
    if not text.lstrip().startswith(("{", "[")):
        return None
    try:
        parsed = json.loads(text)
    except ValueError:
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def _redact_value(value: Any) -> Any:
    """Tapa con '***' solo las partes secretas de un valor ya serializado.

    Texto sin estructura: entero a '***' si contiene un secreto. JSON (dict, lista o
    texto con JSON): solo las claves secretas y las hojas con forma de secreto.
    """
    if isinstance(value, (dict, list)):
        return _redact_json(value)
    if isinstance(value, str):
        parsed = _parse_json_container(value)
        if parsed is not None:
            redacted = _redact_json(parsed)
            if redacted == parsed:
                return value
            return json.dumps(redacted, ensure_ascii=False, separators=(",", ":"))
        return REDACTED if _contains_secret_value(value) else value
    return value


def _is_secret_column(name: str) -> bool:
    """Indica si el nombre de columna del resultado es una columna secreta."""
    return name.lower().rsplit(".", 1)[-1].strip('"`[]') in SECRET_COLUMNS


def redact_rows(
    columns: list[str], rows: list[tuple]
) -> tuple[list[list[Any]], list[str]]:
    """Serializa y redacta las filas: columnas secretas, claves secretas en JSON y valores con forma de secreto."""
    secret_indexes = [i for i, name in enumerate(columns) if _is_secret_column(name)]
    redacted_columns = list(dict.fromkeys(columns[i] for i in secret_indexes))
    clean_rows = []
    for row in rows:
        clean = [_redact_value(_serialize(value)) for value in row]
        for index in secret_indexes:
            clean[index] = REDACTED
        clean_rows.append(clean)
    return clean_rows, redacted_columns


def _scrub_error_text(text: str) -> str:
    """Quita de un mensaje de error la URL de conexión, su contraseña y valores secretos."""
    url = get_settings().database_url
    if url:
        text = text.replace(url, "<database_url>")
        try:
            password = make_url(url).password
        except (SQLAlchemyError, ValueError):
            password = None
        if password:
            text = text.replace(str(password), "***")
    for pattern in SECRET_VALUE_PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text


def _error_detail(exc: SQLAlchemyError) -> str:
    """Nombre de la clase del error y su primera línea, sin URL ni secretos."""
    source = getattr(exc, "orig", None) or exc
    name = type(source).__name__
    lines = str(source).strip().splitlines()
    message = (
        _scrub_error_text(lines[0].strip())[:MAX_ERROR_DETAIL_LENGTH] if lines else ""
    )
    return f"{name}: {message}" if message else name


def _redact_for_log(sql: str) -> str:
    """Texto de la consulta apto para el log (sin valores con forma de secreto)."""
    for pattern in SECRET_VALUE_PATTERNS:
        sql = pattern.sub(REDACTED, sql)
    return " ".join(sql.split())[:500]


def query_database(sql: str, limit: int | None = None) -> dict:
    """Ejecuta una sola consulta SELECT/WITH de solo lectura y devuelve columnas y filas sin secretos."""
    started = time.perf_counter()
    statement = validate_sql(sql)
    settings = get_settings()
    max_rows = _resolve_limit(limit, settings.MCP_QUERY_MAX_ROWS)
    try:
        with get_engine().connect() as conn:
            columns, rows, truncated = _execute_read_only(
                conn, statement, max_rows, settings.MCP_QUERY_TIMEOUT_SECONDS
            )
    except SQLAlchemyError as exc:
        logger.warning(
            "query_database rejected code=query_failed error=%s",
            type(getattr(exc, "orig", None) or exc).__name__,
        )
        raise ToolError(f"query_failed: {_error_detail(exc)}") from None
    clean_rows, redacted_columns = redact_rows(columns, rows)
    duration_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "query_database rows=%d truncated=%s redacted_columns=%d duration_ms=%.1f sql=%s",
        len(clean_rows),
        truncated,
        len(redacted_columns),
        duration_ms,
        _redact_for_log(statement),
    )
    return {
        "columns": columns,
        "rows": clean_rows,
        "row_count": len(clean_rows),
        "truncated": truncated,
        "redacted_columns": redacted_columns,
    }
