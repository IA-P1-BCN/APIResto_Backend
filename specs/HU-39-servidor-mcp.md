# HU-39 · Servidor MCP propio con herramientas para agentes

> Issue: #82 · Prioridad Could (nivel experto del brief P3: "Servidor MCP propio o
> integración de herramientas MCP en el flujo del agente") · Escribe: Levi · Revisa: Rita, Anna, Carla, Manon
> equipo · Aprueba: Levi (PO). Vocabulario: `specs/ontology.md` (R-02). Usa
> `specs/HU-TEMPLATE.md`. Equipo de agentes: `docs/agents/HU-39/`.
> Sin breaking-api: no se toca `app/` ni ningún endpoint. No hay migración.

## Problem Statement
Los agentes de código (Claude Code, OpenCode) trabajan en este repo a ciegas en tres
cosas que piden a menudo:
- **Datos**: para comprobar una hipótesis ("¿qué roles hay en la BD local?") la persona
  tiene que abrir un cliente SQL y pegar el resultado en el chat.
- **Tests**: el agente lanza `pytest` por la shell, con permisos amplios, y recibe la
  salida entera, sin un resumen fiable.
- **Vocabulario**: `AGENTS.md` obliga a usar la ontología, pero el agente tiene que
  encontrar y leer `specs/ontology.md` entero para citar una regla R-xx.

## Solution
Un **servidor MCP propio**, en Python con el SDK oficial (`mcp`), que vive en el repo y se
ejecuta **solo en local** por stdio. Expone tres herramientas:

| Herramienta | Qué hace |
|---|---|
| `query_database` | Ejecuta **una** consulta `SELECT`/`WITH` de solo lectura contra la BD local y devuelve columnas y filas, sin datos secretos (R-02) |
| `run_pytest` | Lanza `pytest` (todo o una ruta de `tests/`) y devuelve el código de salida, el resumen y el final de la salida |
| `get_ontology` | Devuelve `specs/ontology.md` entero o solo la fila de una regla (`R-02`) |

El servidor no se despliega: queda fuera de la imagen Docker y se niega a arrancar con
`ENVIRONMENT=production`.

## User Stories
1. Como agente de código, quiero consultar la BD local en solo lectura, para comprobar
   datos sin pedírselos a la persona.
2. Como persona del equipo, quiero que el agente no pueda escribir en la BD ni leer
   hashes de contraseñas o tokens, para darle la herramienta sin miedo (R-02).
3. Como agente de código, quiero lanzar los tests y recibir un resumen corto, para saber
   si he roto algo sin leer cientos de líneas.
4. Como agente de código, quiero leer una regla R-xx concreta, para citarla con su texto
   exacto y no inventar vocabulario.
5. Como PO, quiero que nada de esto llegue a producción ni cambie la API.

## Implementation Decisions

### SDK y versión
- SDK oficial `mcp`, versión **2.3.0** (la que resuelve pip hoy; `pip install --dry-run`
  sin conflictos con las versiones fijadas en `requirements.txt`). Añade `httpx2`,
  `sse-starlette`, `jsonschema`, `mcp-types`, `pywin32` (solo Windows) y poco más.
- **Ojo, es la 2.x**: `FastMCP` ya no existe. La clase es
  `from mcp.server.mcpserver import MCPServer`; los errores previstos se lanzan con
  `from mcp.server.mcpserver.exceptions import ToolError`; los tests usan
  `from mcp import Client` (acepta la instancia de `MCPServer` en proceso, o
  `StdioServerParameters` para lanzar el servidor como subproceso). Cualquier ejemplo de
  internet con `mcp.server.fastmcp` es de la 1.x y no sirve.

### Dependencia (decisión 2)
`requirements.txt` gana una sección nueva (la línea ya está preparada en la rama):
```
# --- Servidor MCP local para agentes (HU-39) ---
mcp==2.3.0
```
Levi ejecuta `pip install -r requirements.txt` antes de la fase de código; ningún agente
instala paquetes. Va en `requirements.txt` (y no en un fichero aparte) porque el CI solo
instala ese fichero y los tests del servidor MCP deben correr en el CI.

### Ubicación y estructura
Carpeta propia en la raíz, **`mcp_server/`** (decisión 1: `mcp/` choca con el paquete
del SDK).
```
mcp_server/
  __init__.py
  __main__.py          python -m mcp_server  →  arranca por stdio
  config.py            McpSettings y get_settings()
  server.py            build_server() → MCPServer con las 3 herramientas registradas
  tools/
    __init__.py
    database.py        query_database
    pytest_runner.py   run_pytest
    ontology.py        get_ontology
```
- Las herramientas son **funciones normales** (sin decoradores) que reciben parámetros
  simples y devuelven un `dict`. `server.py` las registra con `server.tool(...)(func)`.
  Así se prueban sin MCP y cada agente trabaja en su archivo.
- No importa nada de `app/` (ni `app.config` ni `app.database`): el servidor es
  independiente de la API y no la arranca.
- Transporte: **solo stdio**. Nada de HTTP ni puertos abiertos.
- `stdout` es del protocolo MCP: nada se imprime por `stdout`. Los logs van a `stderr`.

### Configuración (`mcp_server/config.py`)
`McpSettings(BaseSettings)`, lee el mismo `.env` que la API (`extra="ignore"`):

| Variable | Por defecto | Uso |
|---|---|---|
| `MCP_DATABASE_URL` | vacío → usa `DATABASE_URL` | BD de `query_database`. Permite apuntar a un usuario de Postgres de solo lectura |
| `DATABASE_URL` | `sqlite:///./resto.db` | El mismo valor por defecto que `app/config.py` |
| `ENVIRONMENT` | `development` | Con `production`, el servidor no arranca |
| `MCP_QUERY_MAX_ROWS` | `100` | Tope de filas de `query_database` |
| `MCP_QUERY_TIMEOUT_SECONDS` | `10` | Tiempo máximo de una consulta (Postgres) |
| `MCP_PYTEST_TIMEOUT_SECONDS` | `600` | Tiempo máximo de `run_pytest` |

`get_settings()` va con `lru_cache` para que los tests puedan limpiarla.
Las variables se documentan en `.env.example` (sin valores reales; decisión 2) y en
`mcp_server/README.md`.

### `query_database(sql: str, limit: int | None = None) -> dict`
Solo lectura con **varias capas**: si una falla, la siguiente sigue protegiendo.

1. **Validación del texto** (antes de tocar la BD). Se rechaza con `ToolError` si:
   - está vacía o tiene un `;` que no sea el último carácter (una sola sentencia);
   - no empieza por `SELECT` o `WITH` (sin distinguir mayúsculas);
   - contiene como palabra completa `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `DROP`,
     `ALTER`, `CREATE`, `TRUNCATE`, `GRANT`, `REVOKE`, `COPY`, `CALL`, `DO`, `SET`,
     `LOCK`, `VACUUM`, `REINDEX`, `ATTACH`, `DETACH`, `PRAGMA`, `COMMENT` o `INTO`
     (cubre `WITH … DELETE` y `SELECT … INTO` de Postgres). Un falso positivo, por
     ejemplo esa palabra dentro de un literal, se rechaza también: rechazar es lo seguro;
   - menciona una columna o tabla secreta (lista de abajo).
2. **Transacción de solo lectura en la BD**: en Postgres, `SET TRANSACTION READ ONLY` y
   `SET LOCAL statement_timeout`; en SQLite, `PRAGMA query_only = ON` en la conexión.
   Siempre se hace `rollback` al terminar, haya ido bien o mal.
3. **Tope de filas**: se leen como máximo `limit` filas (por defecto y como máximo
   `MCP_QUERY_MAX_ROWS`; `limit < 1` → `ToolError`). Si había más, `truncated: true`.
4. **Datos secretos (R-02, decisión 4: tres capas)**:
   - Columnas secretas: `password_hash`, `token_hash`, `totp_secret`,
     `totp_recovery_codes`. Tablas secretas: `refresh_tokens`, `revoked_tokens`,
     `email_verification_tokens`, `password_reset_tokens`. Mencionarlas en el texto →
     `ToolError` (`secret_not_allowed`).
   - Un identificador con escapes Unicode de Postgres (`U&"…"`, sin distinguir
     mayúsculas ni espacios entre `U&` y la comilla) también → `secret_not_allowed`:
     permitiría escribir `password_hash` sin que aparezca en el texto (decisión 5).
   - Aun así, si el resultado trae una columna con uno de esos nombres (por ejemplo con
     `SELECT * FROM users`), su valor se sustituye por `"***"` y la columna se lista en
     `redacted_columns`.
   - Dentro de un valor JSON del resultado (dict o lista, a cualquier profundidad), el
     valor de una clave con nombre de columna secreta se sustituye por `"***"`. Cubre
     `SELECT row_to_json(u) FROM users u` en Postgres (decisión 5).
   - Por último, cualquier texto del resultado que contenga un hash bcrypt
     (`$2a$`/`$2b$`/`$2y$` + 53 caracteres), un token Fernet (`gAAAAA…`) o un SHA-256 en
     hexadecimal (64 caracteres `[0-9a-fA-F]` seguidos, como palabra completa) se
     sustituye por `"***"`. Cubre `totp_recovery_codes` y `token_hash` aunque salgan
     dentro de la fila entera (`SELECT u::text FROM users u`) (decisión 5).
   - Riesgo residual aceptado: trucos que transforman la fila (por ejemplo, pasarla a
     base64 o cortarla en trozos con `substr`) se saltan las regex. Lo cierra un usuario
     de Postgres con solo `SELECT` y permisos por columna; se explica en
     `mcp_server/README.md`.
5. **Respuesta**:
   `{"columns": [...], "rows": [[...]], "row_count": n, "truncated": bool,
   "redacted_columns": [...]}`. Fechas en ISO 8601, `Decimal` como texto, `bytes` como
   `"<bytes>"`.
6. **Errores** (`ToolError`, mensaje `"<code>: <detalle>"` en inglés, como los `code` de
   la API): `empty_query`, `multiple_statements`, `read_only` (no empieza por
   `SELECT`/`WITH` o lleva una palabra prohibida), `secret_not_allowed`,
   `invalid_limit`, `query_failed` (error de la BD; se devuelve el tipo de error, no la
   cadena de conexión).
7. El motor de SQLAlchemy se crea **la primera vez que se usa** (`get_engine()` con
   `lru_cache`), no al arrancar: el servidor arranca aunque no haya BD.
8. Se anota como herramienta de solo lectura (`ToolAnnotations(readOnlyHint=True)`).

Recomendación para quien use Postgres local: apuntar `MCP_DATABASE_URL` a un usuario con
solo `SELECT` (se explica en `mcp_server/README.md`). Es opcional: las capas 1–4 bastan.

### `run_pytest(target: str | None = None, keyword: str | None = None) -> dict`
- Ejecuta `[sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"]`
  más `target` y `-k keyword`, con `cwd` en la raíz del repo y **sin shell**
  (`subprocess.run(..., shell=False)`).
- `target`: ruta relativa **dentro de `tests/`** (admite `::nodo`). Se rechaza
  (`ToolError invalid_target`) si sale de `tests/` (`..`, ruta absoluta), si no existe o
  si empieza por `-`.
- `keyword`: expresión de `-k`; se pasa como un solo argumento. Si empieza por `-` →
  `ToolError invalid_keyword`.
- No acepta otros argumentos de pytest (ni `--cov`, ni plugins): menos superficie.
- Tiempo máximo `MCP_PYTEST_TIMEOUT_SECONDS`; si se pasa → `timed_out: true`, sin error.
- Respuesta: `{"exit_code": int | None, "passed": bool, "timed_out": bool, "summary":
  "<última línea de resumen de pytest>", "output_tail": "<últimas 200 líneas>",
  "duration_seconds": float, "command": [...]}`. `passed` = `exit_code == 0`.
- **No** se anota como solo lectura (crea BD SQLite temporales y escribe cachés de
  Python).

### `get_ontology(rule_id: str | None = None) -> dict`
- Sin argumentos: `{"path": "specs/ontology.md", "content": "<texto completo>"}`.
- Con `rule_id` (formato `R-` + dos dígitos, sin distinguir mayúsculas: `"R-02"` y
  `"r-02"` valen, `"R-2"` no): devuelve `{"rule_id", "priority", "text"}` leídos de la tabla de
  reglas de la §4. Formato inválido → `ToolError invalid_rule_id`; regla que no existe →
  `ToolError rule_not_found`.
- Lee el archivo en cada llamada (sin caché): siempre devuelve la versión actual.
- Solo lectura (`readOnlyHint=True`).

### Arranque (`mcp_server/__main__.py` y `server.py`)
- `build_server() -> MCPServer`: nombre `"resto-api-dev"`, `instructions` breves en
  inglés (para qué es cada herramienta), registra las tres herramientas con su
  `description` y sus anotaciones.
- `python -m mcp_server`: configura el log a `stderr`, comprueba `ENVIRONMENT` (con
  `production` sale con código 1 y un mensaje en `stderr`) y llama a
  `build_server().run()` (stdio).

### Logs
`logging` a `stderr`, logger `mcp_server`. `info`: herramienta llamada, duración, número
de filas o código de salida. `warning`: cada rechazo con su `code`. **Nunca**: los valores
de las filas, la cadena de conexión ni nada de la lista de secretos (R-02). El texto de la
consulta sí se registra (ya se ha comprobado que no menciona secretos).

### Integración en el flujo del agente
`mcp_server/README.md` explica cómo registrarlo en Claude Code (`claude mcp add
resto-api-dev -- python -m mcp_server`, o `.mcp.json`) y en OpenCode (`opencode.json`,
clave `mcp`) como ejemplos para copiar. **No** se versiona `.mcp.json` y `opencode.json`
no se toca (decisión 3): cada persona activa el servidor a mano.

### Docker y producción
- `.dockerignore` gana la línea `mcp_server/`: el código del servidor no entra en la
  imagen (decisión 2). El paquete `mcp` sí se instala en la imagen, porque va en
  `requirements.txt`, pero nada lo importa.
- Doble cierre: el código no está en la imagen y, aunque estuviera, no arranca con
  `ENVIRONMENT=production`.

### Lo que no cambia
`app/`, `migrations/`, la colección Bruno, `.github/workflows/`, `opencode.json` y los
tests existentes. Fuera de `mcp_server/`, `tests/`, `docs/` y `specs/`, solo cambian las
tres líneas aprobadas: `requirements.txt`, `.dockerignore` y `.env.example`.
La cobertura del CI se mide sobre `app` (`--cov=app`), así que `mcp_server/` no la cambia.

## Testing Decisions
Sin Postgres ni red. Tres archivos nuevos en `tests/`:

- `tests/test_mcp_server.py`
  - `build_server()` registra exactamente `query_database`, `run_pytest` y
    `get_ontology`, con descripción, y `query_database`/`get_ontology` con
    `readOnlyHint=True`.
  - Ida y vuelta en proceso con `mcp.Client(build_server())`: `list_tools` y
    `call_tool("get_ontology", {"rule_id": "R-02"})` devuelven el texto de R-02; un
    `ToolError` llega como resultado con error, no como excepción del cliente.
  - Arranque real por stdio: `Client(StdioServerParameters(command=sys.executable,
    args=["-m", "mcp_server"], cwd=<raíz>))` → `list_tools` responde (con tiempo
    máximo, para que no se cuelgue el CI).
  - Con `ENVIRONMENT=production`, `python -m mcp_server` sale con código 1.
- `tests/test_mcp_query_database.py` (SQLite temporal en `tmp_path` con tablas `users`
  con `password_hash` y `refresh_tokens`; `MCP_DATABASE_URL` por `monkeypatch` y
  `cache_clear()`):
  - Caso feliz: columnas, filas, `row_count`; fechas en ISO.
  - `limit` y `truncated`; `limit` mayor que `MCP_QUERY_MAX_ROWS` se recorta; `limit=0`
    → `invalid_limit`.
  - Rechazos: vacía, dos sentencias, `INSERT`/`UPDATE`/`DELETE`/`DROP`, `WITH … DELETE`,
    `SELECT … INTO`, `PRAGMA`; mencionar `password_hash` o `refresh_tokens` → cada uno
    con su `code`. Tras los rechazos, la BD sigue igual.
  - Capa 2: aunque se salte la validación del texto (llamando a la función interna de
    ejecución), una escritura en SQLite falla por `query_only`.
  - Redacción: `SELECT * FROM users` → `password_hash` = `"***"` y en
    `redacted_columns`; un valor con formato bcrypt, Fernet o SHA-256 hex en otra
    columna → `"***"`; un JSON con la clave `totp_recovery_codes` (también anidada) →
    su valor `"***"`; `U&"…"` → `secret_not_allowed`.
  - Rama de Postgres: con una conexión falsa (mock), se ejecutan `SET TRANSACTION READ
    ONLY` y `SET LOCAL statement_timeout` antes de la consulta y siempre `rollback`.
  - Error de la BD (tabla inexistente) → `query_failed` sin la cadena de conexión.
  - `caplog`: ningún log contiene valores de filas ni hashes.
- `tests/test_mcp_dev_tools.py`:
  - `run_pytest` con `subprocess.run` sustituido (mock; **nunca** lanza pytest de
    verdad dentro de pytest): comando exacto, `cwd`, `shell=False`, `-k` como un solo
    argumento, `passed`, `summary`, `output_tail` recortado, `timeout` → `timed_out`.
  - Rechazos de `target` (`../app`, ruta absoluta, inexistente, `--cov`) y de `keyword`
    (`-p x`).
  - `get_ontology`: sin argumentos devuelve el archivo; `R-02` y `r-02` devuelven su
    fila y prioridad; `R-99` → `rule_not_found`; `X-1` → `invalid_rule_id`.
- Los tests existentes no se tocan y siguen pasando.

## Criterios de aceptación
- [ ] `python -m mcp_server` arranca por stdio y un cliente MCP lista las 3 herramientas.
- [ ] `query_database` solo lee: rechaza escrituras, varias sentencias y secretos; la
  transacción es de solo lectura; nunca devuelve `password_hash`, `token_hash`,
  `totp_secret` ni `totp_recovery_codes` (R-02).
- [ ] `run_pytest` lanza pytest sin shell, solo sobre `tests/`, y devuelve un resumen.
- [ ] `get_ontology` devuelve la ontología entera o una regla R-xx.
- [ ] El servidor no arranca con `ENVIRONMENT=production` y `mcp_server/` no entra en la
  imagen Docker.
- [ ] Ningún archivo de `app/` ni `migrations/` cambia; sin breaking-api.
- [ ] Tests nuevos sin Postgres ni red; `ruff check .` limpio y `pytest` en verde con la
  cobertura mínima.
- [ ] `docs/api.md` y `mcp_server/README.md` explican el servidor y cómo registrarlo;
  `mcp==2.3.0` en `requirements.txt`.
- [ ] Informes de cada agente en `docs/agents/HU-39/`; entrada de HU-39 en
  `docs/ai-log.md` (la escribe Levi).

## Out of Scope
- Transporte HTTP/SSE, autenticación del servidor MCP o desplegarlo.
- Herramientas que escriban (en la BD, en el repo o en git) o que llamen a la API HTTP.
- Recursos (`resources`) y prompts MCP: solo herramientas.
- Ejecutar el servidor MCP en el CI más allá de los tests.
- Crear el usuario de Postgres de solo lectura (solo se documenta cómo).
- Un parser SQL completo (`sqlglot`, `sqlparse`): sería una dependencia más; las capas
  1–4 se consideran suficientes para un servidor local.

## Preguntas abiertas
(vacío: spec lista para implementar)

## Decisiones de la sesión
Votación del equipo (18/10/2026), traída por Levi. Las decisiones 1–4 y la del SDK las
propuso el agente y Levi las aprobó el mismo día.

### Alcance: servidor MCP propio
- **Decisión**: servidor propio en Python con el SDK oficial `mcp`, dentro del repo.
- **Por qué**: cumple el punto del nivel experto del brief y el equipo controla qué
  puede hacer el agente.
- **Alternativas rechazadas**: solo integrar servidores MCP de terceros.

### Herramientas
- **Decisión**: `query_database` (solo lectura), `run_pytest`, `get_ontology`.
- **Por qué**: son las tres cosas que los agentes piden más en este repo (datos, tests,
  vocabulario).

### Seguridad
- **Decisión**: solo local (stdio, sin puertos), nunca en producción, BD en solo lectura.

### SDK 2.3.0
- **Decisión**: fijar `mcp==2.3.0` y usar la API 2.x (`MCPServer`, `ToolError`,
  `Client`).
- **Por qué**: es la versión actual y no tiene conflictos con lo fijado (comprobado con
  `pip install --dry-run`, sin instalar).
- **Alternativas rechazadas**: `mcp<2` con `FastMCP` (versión anterior, muchos ejemplos
  de internet pero API ya sustituida).

### 1 · Carpeta `mcp_server/`
- **Decisión**: el servidor vive en `mcp_server/` en la raíz.
- **Por qué**: el equipo votó `mcp/`, pero choca con el SDK, que es el paquete `mcp` y
  tiene un subpaquete `mcp.server`. Una carpeta `mcp/` en la raíz (que está en
  `sys.path` con pytest y con `python -m`) taparía al SDK, y `mcp/server.py` chocaría
  con `mcp.server`: `from mcp.server.mcpserver import MCPServer` dejaría de funcionar.
- **Alternativas rechazadas**: `mcp/` (choque de nombres); `tools_mcp/`, `resto_mcp/`.

### 2 · Tres líneas fuera de `mcp_server/` y `tests/`
- **Decisión**: se permiten `mcp==2.3.0` en `requirements.txt` (preparada en la rama;
  `pip install` lo ejecuta Levi), `mcp_server/` en `.dockerignore` (la añade
  `agent-core`) y las variables `MCP_*` comentadas en `.env.example` (las añade
  `agent-docs`). `app/` no se toca.
- **Por qué**: el CI solo instala `requirements.txt`, y el código del servidor no debe
  entrar en la imagen. Es el mismo tipo de excepción que en HU-27.
- **Alternativas rechazadas**: un `requirements-mcp.txt` aparte (obligaría a cambiar el
  CI).

### 3 · Sin `.mcp.json` versionado
- **Decisión**: el registro del servidor en Claude Code y OpenCode solo se documenta en
  `mcp_server/README.md`; no se versiona `.mcp.json` y `opencode.json` no se toca.
- **Por qué**: cada persona decide si lo activa, y la configuración compartida del equipo
  no cambia.
- **Alternativas rechazadas**: `.mcp.json` en la raíz; añadir la clave `mcp` a
  `opencode.json`.

### 4 · Secretos de `query_database` en tres capas (R-02)
- **Decisión**: rechazar las consultas que mencionan columnas o tablas secretas,
  enmascarar las columnas secretas del resultado y ocultar con regex los valores con
  forma de hash bcrypt o token Fernet.
- **Por qué**: cada capa tapa los huecos de la anterior (por ejemplo, `SELECT *` o
  `row_to_json(u)`), sin añadir dependencias.
- **Alternativas rechazadas**: prohibir la tabla `users` entera (demasiado estricto);
  solo enmascarar columnas (demasiado laxo).

### 5 · Refuerzo de la decisión 4 tras la revisión de la oleada 1
- **Decisión** (Levi, 18/10/2026): tres capas más en `query_database`: patrón de
  SHA-256 en hexadecimal en los valores, enmascarar las claves secretas dentro de los
  valores JSON y rechazar los identificadores `U&"…"` con `secret_not_allowed`.
- **Por qué**: en Postgres, `row_to_json(u)` o `u::text` devuelven la fila entera sin
  nombrar ninguna columna. bcrypt y Fernet ya se tapaban, pero `totp_recovery_codes`
  (SHA-256 en hex) salía. Lo detectó el líder al revisar `database.py`; `U&"…"` lo
  detectó `agent-tools-db`.
- **Alternativas rechazadas**: aceptar el riesgo y solo documentarlo; un parser SQL
  (dependencia nueva).
