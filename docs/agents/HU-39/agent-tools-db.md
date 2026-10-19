# Agente Especialista — Herramienta de BD · HU-39

## Rol
Eres el especialista de `query_database`, la consulta de solo lectura. Oleada 1, en
paralelo con `agent-core` y `agent-tools-dev`. Es la pieza más sensible de la HU: el
líder y Levi la revisarán a mano (AGENTS.md, "Seguridad").

## Antes de empezar
1. Lee `AGENTS.md` ("Seguridad" y "Qué NO debes hacer").
2. Lee `specs/ontology.md`, R-02, y las entidades con secretos (`User`, `RefreshToken`,
   `RevokedToken`, `EmailVerificationToken`, `PasswordResetToken`).
3. Lee `specs/HU-39-servidor-mcp.md`, sección `query_database` entera (las 8 capas y los
   `code` de error).
4. Lee `docs/agents/HU-39/lead.md` (contrato: `get_settings()`, `ToolError`, logger).

## Archivo exclusivo
`mcp_server/tools/database.py`.

## Tareas
1. `query_database(sql, limit=None) -> dict` con este orden: validar el texto → abrir
   conexión → modo solo lectura según el dialecto → ejecutar → leer como máximo `limit`
   filas (+1 para saber si hay `truncated`) → `rollback` siempre (`finally`) → redactar
   → serializar.
2. Validación del texto: una función propia y pequeña por regla (vacía, varias
   sentencias, primera palabra, palabras prohibidas con límite de palabra, secretos).
   Las listas de palabras prohibidas y de secretos, como constantes del módulo
   (`frozenset`), exactamente las de la spec.
3. Solo lectura en la BD:
   - Postgres: `SET TRANSACTION READ ONLY` y `SET LOCAL statement_timeout = <ms>` (de
     `MCP_QUERY_TIMEOUT_SECONDS`) dentro de la transacción, antes de la consulta.
   - SQLite: `PRAGMA query_only = ON` en la conexión.
   - Separa la ejecución en una función interna (por ejemplo `_execute_read_only(conn,
     sql, max_rows)`) para que `agent-tests` pueda probar esta capa sola.
4. `get_engine()` con `lru_cache`, creado con `get_settings().database_url` la primera
   vez que se llama. Nunca al importar el módulo.
5. Redacción: columnas secretas → `"***"` y en `redacted_columns`; valores de texto con
   bcrypt (`\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}`) o Fernet (`gAAAAA[A-Za-z0-9_\-=]{20,}`)
   → `"***"`.
6. Serialización: `datetime`/`date`/`time` → ISO, `Decimal` → `str`, `bytes` →
   `"<bytes>"`, el resto tal cual si es JSON.
7. Errores con `ToolError("<code>: <detalle>")`. Un error de SQLAlchemy se convierte en
   `query_failed` con solo el nombre de la clase de error y su mensaje corto, nunca la
   URL de conexión.
8. Logs (`mcp_server.tools.database`): `info` con número de filas y duración; `warning`
   con el `code` en cada rechazo. Nunca valores de filas ni la URL.

## Handoff
- `ruff check mcp_server/tools/database.py` limpio.
- Prueba manual rápida (sin escribir tests en `tests/`): con un SQLite temporal en la
  scratchpad, un `SELECT 1` funciona y un `DELETE` se rechaza.
- Informe al líder: firma final, nombre de la función interna para `agent-tests`, y los
  casos límite que has visto.

## Prohibiciones
- Nada de `pip install` ni librerías nuevas (ni `sqlparse` ni `sqlglot`).
- No toques otros archivos de `mcp_server/`, ni `app/`, ni `migrations/`. No uses git.
- No escribas en ninguna BD real. Sin comentarios `#`.

## Informe de desempeño
**Qué hice.** Implementé `query_database(sql: str, limit: int | None = None) -> dict` en
`mcp_server/tools/database.py`, en el orden de la spec: `validate_sql` (una función por
regla: `_check_not_empty`, `_check_single_statement`, `_check_first_keyword`,
`_check_forbidden_keywords`, `_check_no_secrets`) → `_resolve_limit` → `get_engine()`
(`lru_cache`, perezoso) → `_execute_read_only(conn, sql, max_rows, timeout_seconds=None)`
(Postgres: `SET TRANSACTION READ ONLY` + `SET LOCAL statement_timeout = <ms>`; SQLite:
`PRAGMA query_only = ON`; `rollback` en `finally`; lee `max_rows + 1` filas) →
`redact_rows` (columnas secretas → `"***"`, valores bcrypt/Fernet → `"***"`, también
dentro de JSON anidado) → serialización. Constantes `frozenset`: `ALLOWED_FIRST_KEYWORDS`,
`FORBIDDEN_KEYWORDS`, `SECRET_COLUMNS`, `SECRET_TABLES`, `SECRET_IDENTIFIERS`; regex
`BCRYPT_PATTERN` y `FERNET_PATTERN`. Los errores de SQLAlchemy salen como
`query_failed: <Clase>: <primera línea>`, sin la URL, sin su contraseña y con los valores
con forma de secreto redactados. Logs: `info` con filas, `truncated`, duración y el SQL;
`warning` solo con el `code` (y la clase de error en `query_failed`).

**Archivos.** Solo `mcp_server/tools/database.py` (y esta sección).

**Comandos y resultados.**
- `.venv/Scripts/python -m ruff check mcp_server/tools/database.py` → `All checks passed!`
  (también `ruff format`, solo sobre mi archivo).
- Script manual en la scratchpad con un SQLite temporal (nunca `resto.db` ni `test.db`):
  `SELECT 1` funciona; `DELETE`, `INSERT`, `UPDATE`, `DROP`, `PRAGMA`, `WITH … DELETE`,
  `SELECT … INTO`, dos sentencias, vacía, `;`, `password_hash`, `"PASSWORD_HASH"` y
  `refresh_tokens` se rechazan con su `code`; `limit=0/-1` → `invalid_limit`;
  `limit=1000` se recorta; `SELECT * FROM users` → `password_hash` = `"***"` y en
  `redacted_columns`; un bcrypt y un Fernet en otra columna y dentro de `json_object(...)`
  → `"***"`; `DELETE`/`INSERT` pasados a `_execute_read_only` fallan con
  `OperationalError: attempt to write a readonly database` y la BD sigue igual; conexión
  falsa de Postgres: `SET TRANSACTION READ ONLY`, `SET LOCAL statement_timeout = 10000`,
  consulta y `rollback`; los logs no contienen hashes, emails ni la URL. URLs erróneas
  (`postgresql+psycopg://u:secretpw@…`, dialecto inexistente, texto sin formato) → el
  mensaje no incluye la URL ni la contraseña.

**Errores que cometí y cómo los solucioné.**
- Dejé una línea absurda (`… if False else …`) en la ejecución; la vi al repasar y la
  quité.
- Ruff marcó `SIM118` (`result.keys()` en un bucle) y `BLE001` (`except Exception`):
  cambié a `list(map(str, result.keys()))` y a `except (SQLAlchemyError, ValueError)`.
- El script manual falló por `ModuleNotFoundError: mcp_server` (lanzado desde la
  scratchpad): lo ejecuté con `PYTHONPATH=.`.
- Una URL de Postgres a un puerto cerrado tardaba más de 2 minutos en fallar: añadí
  `connect_timeout = MCP_QUERY_TIMEOUT_SECONDS` en `get_engine()` para Postgres (ahora
  falla en ~2 s con `MCP_QUERY_TIMEOUT_SECONDS=2`).

**Decisiones de implementación (para revisar).**
- Ejecuto con `conn.exec_driver_sql(sql)` y no con `text(sql)`: `text()` trataría
  `':foo'` como parámetro y fallaría.
- Un dialecto que no sea `postgresql` ni `sqlite` se rechaza con `query_failed`.
- `limit` que no sea `int` (o un `bool`) → `invalid_limit`.

**Dudas abiertas (no las he resuelto porque no están en la spec).**
- Postgres, nombres con escapes Unicode (`U&"password\005fhash"`): se saltan la capa de
  texto; con alias, también la de columnas, y `token_hash` (SHA-256, sin forma de bcrypt
  ni Fernet) saldría. ¿Rechazamos `U&"`?
- Postgres, trucos sobre la fila entera (`encode(convert_to(u::text,'UTF8'),'base64')`,
  `substr(u::text, …)` por trozos): saltan la regex. La spec acepta este riesgo en local;
  el usuario de Postgres de solo lectura con permisos por columna lo cerraría.
- SQLite: si el archivo de `DATABASE_URL` no existe, conectar crea un archivo vacío.
- SQLite devuelve `TIMESTAMP` como texto (tal cual); solo los `datetime` reales se pasan a
  ISO.

### Corrección tras la revisión del líder
Decisión 5 de la spec (aprobada por Levi). Cambios, solo en `mcp_server/tools/database.py`:
- `SHA256_HEX_PATTERN = re.compile(r"\b[0-9a-fA-F]{64}\b")` añadido a
  `SECRET_VALUE_PATTERNS`. Afecta a los valores del resultado, a los mensajes de error y
  al SQL del log.
- Claves secretas en JSON: `_redact_json` recorre dicts y listas a cualquier
  profundidad. Si una clave (en minúsculas) está en `SECRET_COLUMNS`, su valor pasa a
  `"***"`, tenga la forma que tenga. Las hojas de texto pasan por los patrones.
  **Elegí redacción parcial**: se devuelve la estructura con solo esas partes tapadas, no
  el valor entero. Un texto que es un JSON de objeto o de lista (SQLite devuelve
  `json_object` como `str`) se parsea, se redacta y se vuelve a serializar compacto. Si no
  cambia nada, se devuelve el texto original. Un texto que no es JSON sigue tapándose
  entero si contiene un secreto. Cambio visible: `json_object('id', id, 'n', note)` con un
  bcrypt en `note` ahora da `{"id":1,"n":"***"}` en vez de `"***"`.
- `_check_no_unicode_escapes` (patrón `UNICODE_ESCAPE_IDENTIFIER_PATTERN =
  re.compile(r"\bU&\s*\"", re.IGNORECASE)`), llamada desde `validate_sql` antes de
  `_check_no_secrets`. Lanza `secret_not_allowed: unicode escaped identifiers (U&"...")
  are not allowed`. Cierra la primera duda abierta de arriba.

Resultados: `ruff check` limpio. Script ampliado
(`scratchpad/manual_db_v2.py`, que ejecuta también el anterior): todo verde.
- Dos SHA-256 hex separados por coma en otra columna → `"***"`.
- JSON con `totp_recovery_codes` en una columna, en una lista anidada (y en mayúsculas)
  y envuelto con `json_object('wrap', json(note))` → solo esa clave a `"***"`; `name`,
  `k` y `id` intactos.
- `U&"d\0061ta"`, `u& "x"` y `U&` + salto de línea + `"` → `secret_not_allowed`.
  `'u&x'` sigue funcionando.
- Los casos anteriores siguen pasando.

Errores que cometí:
- Generé el cambio con un script de Python en un heredoc y los `\b` de las regex se
  escribieron como el carácter de retroceso (ruff `PLE2510`). Un segundo intento con
  `replace` tampoco funcionó. Lo arreglé sustituyendo `chr(8)` por `chr(92) + "b"` y
  comprobé los patrones importando el módulo.
- El caso del líder `SELECT json_object('totp_recovery_codes', 'abc', 'name', 'x')` no
  llega a la BD: la capa 1 lo rechaza con `secret_not_allowed`, porque el texto nombra
  la columna secreta. Es correcto. Para probar la capa de JSON, guardé ese JSON en una
  columna normal y lo leí por la consulta.
- Segunda indicación del líder (solo docstrings, sin cambiar lógica ni nombres): los de
  `_contains_secret_value` (ahora incluye SHA-256 en hexadecimal) y `redact_rows` (ahora
  incluye las claves secretas en JSON) estaban desfasados y los actualicé. `ruff check`
  limpio.
