"""Tests de la herramienta query_database del servidor MCP (HU-39, R-02)."""

import datetime
import decimal
import json
import logging
import sqlite3
from contextlib import contextmanager

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.exc import OperationalError

from mcp_server.config import get_settings
from mcp_server.tools import database
from mcp_server.tools.database import (
    REDACTED,
    _execute_read_only,
    _redact_json,
    _redact_value,
    _serialize,
    get_engine,
    query_database,
    redact_rows,
)

BCRYPT_HASH = "$2b$12$" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXY01"
FERNET_TOKEN = "gAAAAABk" + "Zx9_aQwErTyUiOpAsDfGhJkLzXcVbNm-1234567890="
SHA256_HEX = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
CREATED_AT = "2026-10-18 12:30:00"

USERS = [
    (1, "Ana", "ana@test.com", BCRYPT_HASH, CREATED_AT, "nota normal"),
    (2, "Bruno", "bruno@test.com", BCRYPT_HASH, CREATED_AT, f"bcrypt {BCRYPT_HASH}"),
    (3, "Carla", "carla@test.com", BCRYPT_HASH, CREATED_AT, FERNET_TOKEN),
    (4, "Dani", "dani@test.com", BCRYPT_HASH, CREATED_AT, f"{SHA256_HEX},{SHA256_HEX}"),
    (
        5,
        "Eva",
        "eva@test.com",
        BCRYPT_HASH,
        CREATED_AT,
        json.dumps(
            {
                "name": "x",
                "totp_recovery_codes": ["abc", "def"],
                "nested": {"items": [{"TOTP_RECOVERY_CODES": "ghi", "k": 1}]},
            }
        ),
    ),
]


@pytest.fixture
def sqlite_db(monkeypatch, tmp_path):
    """SQLite temporal con users (con password_hash) y refresh_tokens; limpia las cachés."""
    path = tmp_path / "mcp_query.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, "
            "password_hash TEXT, created_at TIMESTAMP, note TEXT)"
        )
        conn.execute(
            "CREATE TABLE refresh_tokens (id INTEGER PRIMARY KEY, user_id INTEGER, token_hash TEXT)"
        )
        conn.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", USERS)
        conn.execute("INSERT INTO refresh_tokens VALUES (1, 1, ?)", (SHA256_HEX,))
    conn.close()
    monkeypatch.setenv("MCP_DATABASE_URL", f"sqlite:///{path.as_posix()}")
    monkeypatch.setenv("MCP_QUERY_MAX_ROWS", "100")
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield path
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_settings.cache_clear()
    get_engine.cache_clear()


def _snapshot(path) -> list[tuple]:
    """Contenido de las dos tablas, leído con una conexión aparte."""
    conn = sqlite3.connect(path)
    try:
        users = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        tokens = conn.execute("SELECT * FROM refresh_tokens ORDER BY id").fetchall()
    finally:
        conn.close()
    return users + tokens


def _error_code(exc_info) -> str:
    """Código del ToolError (lo que va antes de ':')."""
    return str(exc_info.value).split(":", 1)[0]


def test_caso_feliz_devuelve_columnas_filas_y_row_count(sqlite_db):
    result = query_database("SELECT id, name, email FROM users WHERE id <= 2 ORDER BY id")
    assert result["columns"] == ["id", "name", "email"]
    assert result["rows"] == [[1, "Ana", "ana@test.com"], [2, "Bruno", "bruno@test.com"]]
    assert result["row_count"] == 2
    assert result["truncated"] is False
    assert result["redacted_columns"] == []


def test_consulta_with_y_punto_y_coma_final_se_aceptan(sqlite_db):
    result = query_database("WITH u AS (SELECT id FROM users) SELECT count(*) AS n FROM u;")
    assert result["columns"] == ["n"]
    assert result["rows"] == [[5]]


def test_fechas_se_devuelven_en_iso_8601():
    moment = datetime.datetime(2026, 10, 18, 12, 30, 0, tzinfo=datetime.UTC)
    assert _serialize(moment) == "2026-10-18T12:30:00+00:00"
    assert _serialize(datetime.date(2026, 10, 18)) == "2026-10-18"
    rows, _ = redact_rows(["created_at"], [(moment,)])
    assert rows == [["2026-10-18T12:30:00+00:00"]]


def test_decimal_y_bytes_se_serializan():
    assert _serialize(decimal.Decimal("12.50")) == "12.50"
    assert _serialize(b"\x00\x01") == "<bytes>"


def test_limit_trunca_y_marca_truncated(sqlite_db):
    result = query_database("SELECT id FROM users ORDER BY id", limit=2)
    assert result["rows"] == [[1], [2]]
    assert result["row_count"] == 2
    assert result["truncated"] is True


def test_limit_igual_al_numero_de_filas_no_trunca(sqlite_db):
    result = query_database("SELECT id FROM users ORDER BY id", limit=5)
    assert result["row_count"] == 5
    assert result["truncated"] is False


def test_limit_mayor_que_el_maximo_se_recorta(sqlite_db, monkeypatch):
    monkeypatch.setenv("MCP_QUERY_MAX_ROWS", "3")
    get_settings.cache_clear()
    result = query_database("SELECT id FROM users ORDER BY id", limit=1000)
    assert result["row_count"] == 3
    assert result["truncated"] is True


def test_sin_limit_se_usa_el_maximo(sqlite_db, monkeypatch):
    monkeypatch.setenv("MCP_QUERY_MAX_ROWS", "4")
    get_settings.cache_clear()
    result = query_database("SELECT id FROM users ORDER BY id")
    assert result["row_count"] == 4
    assert result["truncated"] is True


@pytest.mark.parametrize("limit", [0, -1])
def test_limit_menor_que_uno_es_invalid_limit(sqlite_db, limit):
    with pytest.raises(ToolError) as exc_info:
        query_database("SELECT id FROM users", limit=limit)
    assert _error_code(exc_info) == "invalid_limit"


@pytest.mark.parametrize(
    ("sql", "code"),
    [
        ("", "empty_query"),
        ("   ", "empty_query"),
        (";", "empty_query"),
        ("SELECT 1; SELECT 2", "multiple_statements"),
        ("SELECT 1; DELETE FROM users", "multiple_statements"),
        ("INSERT INTO users (id) VALUES (99)", "read_only"),
        ("UPDATE users SET name = 'x'", "read_only"),
        ("DELETE FROM users", "read_only"),
        ("DROP TABLE users", "read_only"),
        ("WITH x AS (SELECT id FROM users) DELETE FROM users", "read_only"),
        ("SELECT * INTO users_copy FROM users", "read_only"),
        ("PRAGMA query_only = OFF", "read_only"),
        ("SELECT 1 FROM users WHERE name = 'drop'", "read_only"),
        ("SELECT password_hash FROM users", "secret_not_allowed"),
        ('SELECT "PASSWORD_HASH" FROM users', "secret_not_allowed"),
        ("SELECT * FROM refresh_tokens", "secret_not_allowed"),
        ("SELECT token_hash FROM sessions", "secret_not_allowed"),
        ('SELECT U&"d\\0061ta" FROM users', "secret_not_allowed"),
        ('SELECT u& "x" FROM users', "secret_not_allowed"),
    ],
)
def test_rechazos_con_su_code(sqlite_db, sql, code):
    with pytest.raises(ToolError) as exc_info:
        query_database(sql)
    assert _error_code(exc_info) == code


def test_tras_los_rechazos_la_bd_sigue_igual(sqlite_db):
    before = _snapshot(sqlite_db)
    for sql in (
        "INSERT INTO users (id) VALUES (99)",
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "DROP TABLE users",
        "WITH x AS (SELECT 1) DELETE FROM users",
        "SELECT * INTO users_copy FROM users",
        "SELECT 1; DELETE FROM users",
        "PRAGMA query_only = OFF",
    ):
        with pytest.raises(ToolError):
            query_database(sql)
    assert _snapshot(sqlite_db) == before


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM users",
        "INSERT INTO users (id, name) VALUES (99, 'x')",
        "UPDATE users SET name = 'x'",
        "DROP TABLE users",
    ],
)
def test_capa_2_escritura_falla_por_query_only_aunque_se_salte_la_validacion(sqlite_db, sql):
    before = _snapshot(sqlite_db)
    with get_engine().connect() as conn, pytest.raises(OperationalError):
        _execute_read_only(conn, sql, 10)
    assert _snapshot(sqlite_db) == before


def test_select_asterisco_tapa_password_hash_y_lo_lista(sqlite_db):
    result = query_database("SELECT * FROM users ORDER BY id")
    index = result["columns"].index("password_hash")
    assert all(row[index] == REDACTED for row in result["rows"])
    assert result["redacted_columns"] == ["password_hash"]
    assert BCRYPT_HASH not in json.dumps(result)


@pytest.mark.parametrize("user_id", [2, 3, 4])
def test_valores_con_forma_de_secreto_en_otra_columna_se_tapan(sqlite_db, user_id):
    result = query_database(f"SELECT name, note FROM users WHERE id = {user_id}")
    assert result["rows"][0][1] == REDACTED
    assert result["redacted_columns"] == []
    dumped = json.dumps(result)
    assert BCRYPT_HASH not in dumped
    assert FERNET_TOKEN not in dumped
    assert SHA256_HEX not in dumped


def test_json_con_clave_totp_recovery_codes_tapa_solo_su_valor(sqlite_db):
    result = query_database("SELECT note FROM users WHERE id = 5")
    value = json.loads(result["rows"][0][0])
    assert value["name"] == "x"
    assert value["totp_recovery_codes"] == REDACTED
    assert value["nested"]["items"][0]["TOTP_RECOVERY_CODES"] == REDACTED
    assert value["nested"]["items"][0]["k"] == 1


def test_json_sin_secretos_se_devuelve_igual(sqlite_db):
    result = query_database("SELECT json_object('id', id, 'name', name) AS j FROM users WHERE id = 1")
    assert json.loads(result["rows"][0][0]) == {"id": 1, "name": "Ana"}


def test_redact_json_tapa_claves_secretas_a_cualquier_profundidad():
    value = {
        "a": {"b": [{"totp_secret": "JBSWY3DP", "ok": "si"}]},
        "password_hash": "x",
        "list": [BCRYPT_HASH, "normal"],
    }
    assert _redact_json(value) == {
        "a": {"b": [{"totp_secret": REDACTED, "ok": "si"}]},
        "password_hash": REDACTED,
        "list": [REDACTED, "normal"],
    }


def test_redact_value_texto_y_json_en_texto():
    assert _redact_value("hola") == "hola"
    assert _redact_value(f"hash={BCRYPT_HASH}") == REDACTED
    text = json.dumps({"token_hash": "abc", "n": 1})
    assert json.loads(_redact_value(text)) == {"token_hash": REDACTED, "n": 1}
    assert _redact_value(42) == 42


def test_error_de_la_bd_es_query_failed_sin_cadena_de_conexion(sqlite_db):
    with pytest.raises(ToolError) as exc_info:
        query_database("SELECT * FROM missing_table")
    message = str(exc_info.value)
    assert _error_code(exc_info) == "query_failed"
    assert "missing_table" in message
    assert "sqlite:///" not in message
    assert sqlite_db.as_posix() not in message
    assert str(sqlite_db) not in message


def test_logs_no_contienen_valores_de_filas_ni_hashes(sqlite_db, caplog):
    caplog.set_level(logging.DEBUG, logger="mcp_server")
    query_database("SELECT * FROM users ORDER BY id")
    query_database("SELECT name, note FROM users")
    with pytest.raises(ToolError):
        query_database("SELECT password_hash FROM users")
    with pytest.raises(ToolError):
        query_database("SELECT * FROM missing_table")
    assert caplog.records
    text = caplog.text
    for secret in (BCRYPT_HASH, FERNET_TOKEN, SHA256_HEX, "ana@test.com", "nota normal", "Bruno"):
        assert secret not in text
    assert sqlite_db.as_posix() not in text


def test_log_del_sql_tapa_valores_con_forma_de_secreto(sqlite_db, caplog):
    caplog.set_level(logging.DEBUG, logger="mcp_server")
    query_database(f"SELECT id FROM users WHERE note = '{SHA256_HEX}'")
    assert SHA256_HEX not in caplog.text


class FakeResult:
    """Resultado falso de exec_driver_sql con filas fijas."""

    def __init__(self, columns, rows):
        self.returns_rows = True
        self._columns = columns
        self._rows = rows
        self.fetch_sizes = []

    def keys(self):
        return list(self._columns)

    def fetchmany(self, size):
        self.fetch_sizes.append(size)
        return self._rows[:size]

    def close(self):
        pass


class FakeDialect:
    """Dialecto falso: solo tiene name."""

    def __init__(self, name):
        self.name = name


class FakePostgresConnection:
    """Conexión falsa de Postgres que registra las sentencias y los rollback."""

    def __init__(self, rows=None, columns=("id",), fail_on_query=False):
        self.dialect = FakeDialect("postgresql")
        self.statements = []
        self.rollbacks = 0
        self.fail_on_query = fail_on_query
        self.result = FakeResult(list(columns), rows if rows is not None else [(1,)])

    def exec_driver_sql(self, sql):
        self.statements.append(sql)
        if sql.startswith("SET "):
            return None
        if self.fail_on_query:
            raise OperationalError(sql, {}, Exception("boom"))
        return self.result

    def rollback(self):
        self.rollbacks += 1


def test_postgres_pone_la_transaccion_en_solo_lectura_y_hace_rollback():
    conn = FakePostgresConnection(rows=[(1,), (2,), (3,)])
    columns, rows, truncated = _execute_read_only(conn, "SELECT id FROM users", 2, 5)
    assert conn.statements == [
        "SET TRANSACTION READ ONLY",
        "SET LOCAL statement_timeout = 5000",
        "SELECT id FROM users",
    ]
    assert conn.rollbacks == 1
    assert conn.result.fetch_sizes == [3]
    assert columns == ["id"]
    assert rows == [(1,), (2,)]
    assert truncated is True


def test_postgres_hace_rollback_aunque_falle_la_consulta():
    conn = FakePostgresConnection(fail_on_query=True)
    with pytest.raises(OperationalError):
        _execute_read_only(conn, "SELECT id FROM users", 10, 5)
    assert conn.statements[:2] == [
        "SET TRANSACTION READ ONLY",
        "SET LOCAL statement_timeout = 5000",
    ]
    assert conn.rollbacks == 1


@pytest.fixture
def fake_postgres(monkeypatch):
    """Sustituye get_engine por un motor falso de Postgres; devuelve la conexión."""
    conn = FakePostgresConnection(
        columns=("id", "created_at", "amount", "photo", "password_hash"),
        rows=[
            (
                1,
                datetime.datetime(2026, 10, 18, 12, 30, tzinfo=datetime.UTC),
                decimal.Decimal("9.90"),
                b"\x89PNG",
                BCRYPT_HASH,
            )
        ],
    )

    class FakeEngine:
        @contextmanager
        def connect(self):
            yield conn

    monkeypatch.setenv("MCP_QUERY_TIMEOUT_SECONDS", "7")
    get_settings.cache_clear()
    monkeypatch.setattr(database, "get_engine", lambda: FakeEngine())
    yield conn
    get_settings.cache_clear()


def test_query_database_por_la_rama_de_postgres(fake_postgres):
    result = query_database("SELECT * FROM users")
    assert fake_postgres.statements == [
        "SET TRANSACTION READ ONLY",
        "SET LOCAL statement_timeout = 7000",
        "SELECT * FROM users",
    ]
    assert fake_postgres.rollbacks == 1
    assert result["rows"] == [[1, "2026-10-18T12:30:00+00:00", "9.90", "<bytes>", REDACTED]]
    assert result["redacted_columns"] == ["password_hash"]


def test_query_database_postgres_error_es_query_failed(fake_postgres):
    fake_postgres.fail_on_query = True
    with pytest.raises(ToolError) as exc_info:
        query_database("SELECT * FROM users")
    assert _error_code(exc_info) == "query_failed"
    assert fake_postgres.rollbacks == 1
