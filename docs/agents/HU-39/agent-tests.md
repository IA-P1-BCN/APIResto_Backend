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
_(Rellénalo al terminar: qué hiciste, archivos, comandos y resultados, errores que
cometiste y cómo los solucionaste, dudas abiertas.)_
