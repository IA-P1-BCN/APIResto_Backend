# Agente Especialista — Tests · HU-39

## Rol
Eres el especialista en los tests del servidor MCP. Oleada 2: empiezas cuando el líder
ha aceptado la oleada 1. Trabajas en paralelo con `agent-docs`.

## Antes de empezar
1. Lee `AGENTS.md`, "Los tests son el contrato".
2. Lee `specs/HU-39-servidor-mcp.md`, "Testing Decisions" y "Criterios de aceptación".
3. Lee `docs/agents/HU-39/lead.md` y los informes de `agent-core`, `agent-tools-db` y
   `agent-tools-dev` (nombres de funciones internas, casos límite).
4. Lee `tests/conftest.py`: sus fixtures `autouse` también se aplican a tus tests; no
   los cambies.

## Archivos exclusivos
`tests/test_mcp_server.py`, `tests/test_mcp_query_database.py`,
`tests/test_mcp_dev_tools.py`.

## Tareas
1. Escribe todos los casos de "Testing Decisions" de la spec, en los tres archivos.
2. **Sin Postgres ni red**: BD SQLite en `tmp_path`; la rama de Postgres de
   `query_database`, con una conexión falsa (`unittest.mock`) que registre las
   sentencias. `MCP_DATABASE_URL` con `monkeypatch.setenv` y `get_settings.cache_clear()`
   + `get_engine.cache_clear()` antes y después (fixture propio).
3. **Nunca** lances pytest de verdad desde `run_pytest`: sustituye `subprocess.run`.
4. Servidor:
   - en proceso: `async with Client(build_server()) as client:` (`from mcp import
     Client`), ejecutado con `anyio.run(...)` dentro de un test síncrono, para no
     depender de plugins de pytest;
   - por stdio: `Client(StdioServerParameters(command=sys.executable, args=["-m",
     "mcp_server"], cwd=str(REPO_ROOT)))` con un tiempo máximo (`anyio.fail_after`).
   - `ENVIRONMENT=production`: `subprocess.run([sys.executable, "-m", "mcp_server"],
     env=...)` devuelve `1`.
5. Comprueba con `caplog` que ningún log contiene valores de filas ni hashes.
6. Ejecuta `pytest tests/test_mcp_*.py` y después `pytest` entero.

## Si un test falla
Si el fallo es del código (no del test), **no lo arregles tú**: avisa al líder con el
test, el error y el archivo responsable. No debilites el test ni uses `skip`.

## Handoff
- `ruff check tests` limpio.
- `pytest` entero en verde; los tests existentes, sin cambios.
- Informe al líder: número de tests nuevos por archivo, tiempo de los tests de stdio y
  fallos encontrados en el código (si los hubo).

## Prohibiciones
- No toques `mcp_server/`, `app/`, `migrations/` ni `tests/conftest.py`.
- No uses git ni instales paquetes. Sin comentarios `#`.

## Informe de desempeño
**Qué hice.** Antes de escribir, probé el SDK con un script en la scratchpad
(`Client(build_server())` en proceso y `Client(StdioServerParameters(...))`) para confirmar
cómo llegan los datos: `result.content[0].text` trae el JSON, `is_error` marca el
`ToolError`, `tool.annotations.read_only_hint` lleva la anotación y `client.server_info.name`
el nombre. Después escribí los casos de "Testing Decisions", más algunos límites que
contaban los informes de la oleada 1. Lo async corre con `anyio.run` + `anyio.fail_after(60)`
dentro de tests síncronos, sin plugins. Cada archivo tiene su propio fixture, que fija
`MCP_DATABASE_URL`/`MCP_*` con `monkeypatch` y llama a `get_settings.cache_clear()` y
`get_engine.cache_clear()` antes y después; al terminar hace además `dispose()` del motor,
para no dejar la SQLite abierta en Windows.

**Archivos y número de tests** (93 nuevos, contando cada caso parametrizado):
- `tests/test_mcp_server.py`: 11. Las 3 herramientas exactas con descripción;
  `readOnlyHint` en `query_database`/`get_ontology` y no en `run_pytest`; nombre
  `resto-api-dev` e instrucciones. Ida y vuelta en proceso: `get_ontology R-02`,
  `ToolError` como `is_error`, `query_database` con SQLite y un rechazo. Arranque real
  por stdio (`list_tools` + `get_ontology`). `ENVIRONMENT=production` → código 1, stdout
  vacío y el mensaje en stderr.
- `tests/test_mcp_query_database.py`: 49. Usa una SQLite en `tmp_path` con `users`
  (`password_hash`, `note`) y `refresh_tokens`. Caso feliz; `WITH` y `;` final; fechas
  ISO, `Decimal` y `bytes` (con `_serialize`/`redact_rows`, porque SQLite devuelve el
  TIMESTAMP como texto); `limit`/`truncated`, el recorte a `MCP_QUERY_MAX_ROWS` y
  `limit` 0 y -1. 19 rechazos con su `code`, entre ellos `U&"…"`, `"PASSWORD_HASH"` y el
  falso positivo `'drop'`. La BD sigue igual tras los rechazos. Capa 2: cuatro escrituras
  pasadas a `_execute_read_only` fallan por `query_only`. Redacción: `SELECT *`; bcrypt,
  Fernet y SHA-256 en `note`; JSON guardado en `note` con `totp_recovery_codes`, anidado y
  en mayúsculas; `_redact_json`/`_redact_value` directos. `query_failed` sin la URL ni la
  ruta. Con `caplog`, los logs no llevan valores, hashes, emails ni la ruta, y el SQL del
  log tapa un SHA-256. Postgres con una conexión falsa: el orden de las sentencias, el
  `rollback` también si falla y `fetchmany(max_rows + 1)`; además, `query_database`
  completo con un `get_engine` falso (timeout 7 s → `7000`) y su `query_failed`.
- `tests/test_mcp_dev_tools.py`: 33. Sustituye `subprocess.run` en todos los casos (nunca
  lanza pytest). Comprueba el comando exacto y los argumentos de `subprocess.run`
  (`cwd`, `shell=False`, `timeout`, `capture_output`, `text`, `check=False`,
  `stdin=DEVNULL`), `-k` como un solo argumento, la suite entera y `::nodo`, que pase y
  que falle, el recorte de `output_tail` a 200 líneas y el `TimeoutExpired` →
  `timed_out`. Rechaza 9 `target` y 3 `keyword`, y en ninguno se llama a `subprocess`.
  También prueba `find_summary`/`tail_output`, `get_ontology` sin argumentos, `R-02` y
  `r-02`, `R-99`, 5 formatos inválidos y `parse_rules` solo con la §4.

**Comandos y resultados** (pytest siempre con `DATABASE_URL=sqlite:///<scratchpad>/tests_run.db`):
- `.venv/Scripts/python -m ruff check tests` → `All checks passed!`
- `pytest tests/test_mcp_server.py tests/test_mcp_query_database.py tests/test_mcp_dev_tools.py`
  → `93 passed` en ~2,6 s.
- `pytest --cov=app --cov-report=term-missing -q` (suite entera) → `996 passed`, 0
  skipped, `TOTAL 100%` en ~66 s.
- Tiempo de los tests de subproceso: stdio ~0,8 s, `production` ~0,2 s.

**Errores que cometí y cómo los solucioné.**
- En la primera pasada, ruff marcó `DTZ001` (dos `datetime` sin `tzinfo`) y `SIM117`
  (`with` anidados). Pasé las fechas a `tzinfo=datetime.UTC`, que esperan
  `…T12:30:00+00:00`, y junté los `with`.
- Para contar los tests por archivo lancé `pytest --collect-only` con
  `DATABASE_URL=sqlite:///x.db` relativo, y al importar `app` se creó `x.db` en la raíz
  del repo. Lo borré enseguida (no estaba versionado; `git status` limpio de él).

**Bugs del código encontrados.** Ninguno: todos los casos de la spec pasaron a la primera
contra el código de la oleada 1.

**Dudas abiertas.** Ninguna que bloquee. Nota para el CI: los tests de stdio y de
`production` heredan `os.environ` y fijan `ENVIRONMENT`, `MCP_DATABASE_URL` y
`PYTHONIOENCODING`, así que no dependen de rutas de Windows ni del Postgres del servicio.
