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
_(Rellénalo al terminar: qué hiciste, archivos, comandos y resultados, errores que
cometiste y cómo los solucionaste, dudas abiertas.)_
