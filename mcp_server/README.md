# Servidor MCP local para agentes (`resto-api-dev`) · HU-39

Servidor [MCP](https://modelcontextprotocol.io) propio que da a los agentes de código
(Claude Code, OpenCode) tres herramientas sobre este repo. Spec:
[`specs/HU-39-servidor-mcp.md`](../specs/HU-39-servidor-mcp.md). Resumen del contrato:
[`docs/api.md`](../docs/api.md#servidor-mcp-para-agentes-local--hu-39).

| Herramienta | Qué hace | Solo lectura |
|---|---|---|
| `query_database` | Una consulta `SELECT`/`WITH` contra la BD local, sin datos secretos (R-02) | Sí (`readOnlyHint`) |
| `run_pytest` | Lanza `pytest` (toda la suite o una ruta de `tests/`) y devuelve un resumen | No |
| `get_ontology` | Devuelve `specs/ontology.md` o una sola regla `R-xx` | Sí (`readOnlyHint`) |

- **Solo local**: transporte stdio, sin HTTP ni puertos abiertos. No es un endpoint de la
  API y no cambia ninguno (sin breaking-api).
- **No se despliega**: `mcp_server/` está en `.dockerignore` y, aunque estuviera en la
  imagen, `python -m mcp_server` se niega a arrancar con `ENVIRONMENT=production` (sale
  con código 1 y un mensaje en `stderr`).
- **No depende de la API**: no importa nada de `app/` ni arranca FastAPI.

## Requisitos

- El Python del `.venv` del proyecto (3.12).
- `mcp==2.3.0`, que ya está en `requirements.txt`: `pip install -r requirements.txt`.
- **Es la API 2.x del SDK.** La clase del servidor es
  `from mcp.server.mcpserver import MCPServer` y los errores previstos son
  `from mcp.server.mcpserver.exceptions import ToolError`. `FastMCP`
  (`mcp.server.fastmcp`) es de la 1.x y ya no existe: los ejemplos de internet que lo usan
  no sirven aquí.
- La carpeta se llama `mcp_server/` y no `mcp/` porque `mcp/` taparía al paquete `mcp` del
  SDK (decisión 1 de la spec).

## Arranque

Desde la raíz del repo:

```bash
python -m mcp_server
```

En Windows, con el Python del `.venv`:

```powershell
.venv\Scripts\python.exe -m mcp_server
```

El proceso se queda esperando mensajes MCP por `stdin`. **No escribe nada por `stdout`**,
que es el canal del protocolo; los logs (logger `mcp_server`) van a `stderr`. Normalmente
no lo lanzas tú: lo lanza el cliente MCP (abajo).

Para probarlo a mano con un cliente de la 2.x:

```python
import anyio
from mcp import Client
from mcp_server.server import build_server

async def main():
    async with Client(build_server()) as client:
        print([tool.name for tool in (await client.list_tools()).tools])
        result = await client.call_tool("get_ontology", {"rule_id": "R-02"})
        print(result.content[0].text)

anyio.run(main)
```

## Registro en el agente

Cada persona lo activa a mano en su máquina. **No se versiona `.mcp.json` y no se toca
`opencode.json`** (decisión 3 de la spec): la configuración compartida del equipo no
cambia. Los bloques de abajo son ejemplos para copiar.

El servidor necesita encontrar el paquete `mcp_server`: el cliente debe lanzarlo con la
raíz del repo como carpeta de trabajo. Si tu cliente lo lanza desde otra carpeta, añade la
variable de entorno `PYTHONPATH` con la ruta de la raíz del repo.

### Claude Code

Desde la raíz del repo:

```bash
claude mcp add resto-api-dev -- python -m mcp_server
```

`python` tiene que ser el del `.venv`. En Windows puede hacer falta la ruta completa:

```powershell
claude mcp add resto-api-dev -- C:\ruta\al\repo\Resto-API_Backend\.venv\Scripts\python.exe -m mcp_server
```

Sin `--scope`, Claude Code lo guarda en tu configuración local del proyecto (fuera del
repo). Con `--scope project` crearía un `.mcp.json` en la raíz: **no lo commitees**.
Comprueba que está activo con `claude mcp list` o con `/mcp` dentro de Claude Code.

Si prefieres un `.mcp.json` propio (sin commitear), este es el formato:

```json
{
  "mcpServers": {
    "resto-api-dev": {
      "type": "stdio",
      "command": "C:\\ruta\\al\\repo\\Resto-API_Backend\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server"],
      "env": {}
    }
  }
}
```

### OpenCode

Bloque `mcp` para **tu** configuración de OpenCode (por ejemplo, la global
`~/.config/opencode/opencode.json`; no el `opencode.json` del repo). Los servidores por
stdio son de tipo `local` y `command` es una lista con el ejecutable y sus argumentos:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "resto-api-dev": {
      "type": "local",
      "command": [
        "C:\\ruta\\al\\repo\\Resto-API_Backend\\.venv\\Scripts\\python.exe",
        "-m",
        "mcp_server"
      ],
      "enabled": true,
      "environment": {
        "PYTHONPATH": "C:\\ruta\\al\\repo\\Resto-API_Backend"
      }
    }
  }
}
```

Los campos opcionales y su comportamiento pueden cambiar entre versiones de OpenCode:
compruébalos en su documentación, https://opencode.ai/docs/mcp-servers/.

## Configuración

`mcp_server/config.py` (`McpSettings`) lee el mismo `.env` que la API (el de la raíz del
repo, aunque el cliente lance el servidor desde otra carpeta) e ignora las demás
variables. Están documentadas, comentadas, en `.env.example`.

| Variable | Por defecto | Uso |
|---|---|---|
| `MCP_DATABASE_URL` | vacío → usa `DATABASE_URL` | BD de `query_database`. Permite apuntar a un usuario de Postgres de solo lectura (abajo) |
| `DATABASE_URL` | `sqlite:///./resto.db` | La misma variable y el mismo valor por defecto que la API |
| `ENVIRONMENT` | `development` | Con `production` (sin distinguir mayúsculas ni espacios) el servidor no arranca |
| `MCP_QUERY_MAX_ROWS` | `100` | Tope de filas de `query_database` (por defecto y máximo de `limit`) |
| `MCP_QUERY_TIMEOUT_SECONDS` | `10` | Tiempo máximo de una consulta en Postgres (`statement_timeout`) y de la conexión (`connect_timeout`) |
| `MCP_PYTEST_TIMEOUT_SECONDS` | `600` | Tiempo máximo de `run_pytest` |

Los ajustes se leen una vez y se guardan en caché (`get_settings()` con `lru_cache`): si
cambias el `.env`, reinicia el servidor desde tu cliente.

## Herramientas

Las tres devuelven un objeto JSON (llega al cliente como texto JSON en
`content[0].text`). Los errores previstos llegan como resultado con error
(`isError: true`), con el texto `Error executing tool <herramienta>: <code>: <detalle>`
(detalle en inglés). Un error imprevisto (por ejemplo, que falte `specs/ontology.md`)
llega solo como `Error executing tool <herramienta>`.

### `query_database(sql, limit=None)`

Ejecuta **una** consulta de solo lectura y devuelve (por ejemplo, para
`SELECT * FROM users LIMIT 1`, recortado):

```json
{"columns": ["id", "email", "password_hash"],
 "rows": [[1, "admin@resto.local", "***"]],
 "row_count": 1, "truncated": false, "redacted_columns": ["password_hash"]}
```

Fechas en ISO 8601, `Decimal` y `UUID` como texto, `bytes` como `"<bytes>"`. Se leen como
máximo `limit` filas (por defecto y como máximo `MCP_QUERY_MAX_ROWS`; un `limit` mayor se
recorta); si había más, `truncated: true`. El motor de la BD se crea en la primera
consulta, así que el servidor arranca aunque no haya BD. Solo admite Postgres y SQLite.

**Capas de protección** (si una falla, la siguiente sigue protegiendo):

1. **Validación del texto**, antes de tocar la BD:
   - vacía, o con un `;` que no sea el último carácter → rechazada (una sola sentencia);
   - tiene que empezar por `SELECT` o `WITH` (sin distinguir mayúsculas);
   - se rechaza si contiene, como palabra completa y en cualquier sitio (también dentro
     de un literal o como alias), `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `DROP`, `ALTER`,
     `CREATE`, `TRUNCATE`, `GRANT`, `REVOKE`, `COPY`, `CALL`, `DO`, `SET`, `LOCK`,
     `VACUUM`, `REINDEX`, `ATTACH`, `DETACH`, `PRAGMA`, `COMMENT` o `INTO`. Cubre
     `WITH … DELETE` y `SELECT … INTO`. Los falsos positivos (`SELECT 'set' AS x`) se
     rechazan también: rechazar es lo seguro;
   - se rechaza si menciona una columna o tabla secreta (lista de abajo), también entre
     comillas o con prefijo de tabla (`u."password_hash"`);
   - se rechaza cualquier identificador con escapes Unicode de Postgres (`U&"…"`, sin
     distinguir mayúsculas y aunque haya espacios entre `U&` y la comilla): permitiría
     escribir `password_hash` sin que aparezca en el texto.
2. **Transacción de solo lectura en la BD**: en Postgres, `SET TRANSACTION READ ONLY` y
   `SET LOCAL statement_timeout`; en SQLite, `PRAGMA query_only = ON`. Siempre termina en
   `rollback`, haya ido bien o mal.
3. **Tope de filas** (`limit` / `MCP_QUERY_MAX_ROWS`).
4. **Datos secretos (R-02)**:
   - Columnas secretas: `password_hash`, `token_hash`, `totp_secret`,
     `totp_recovery_codes`. Tablas secretas: `refresh_tokens`, `revoked_tokens`,
     `email_verification_tokens`, `password_reset_tokens`. Nombrarlas → `secret_not_allowed`.
   - Si el resultado trae una columna con uno de esos nombres (por ejemplo con
     `SELECT * FROM users`), su valor pasa a `"***"` y la columna se lista en
     `redacted_columns`.
   - Dentro de un valor JSON del resultado (objeto o lista, a cualquier profundidad, y
     también un texto que sea un JSON, como el de `json_object` en SQLite), el valor de
     una clave con nombre de columna secreta pasa a `"***"`; **solo esa clave**, el resto
     del JSON se devuelve tal cual. Cubre `SELECT row_to_json(u) FROM users u` en Postgres.
   - Por último, cualquier texto que contenga un hash bcrypt (`$2a$`/`$2b$`/`$2y$` + coste
     + 53 caracteres), un token Fernet (`gAAAAA…`) o un SHA-256 en hexadecimal
     (64 caracteres `[0-9a-fA-F]` como palabra completa) pasa entero a `"***"`. Cubre
     `totp_recovery_codes` y `token_hash` aunque salgan dentro de la fila entera
     (`SELECT u::text FROM users u`). Dentro de un JSON, solo se tapa esa hoja.
5. **Logs**: se registran el texto de la consulta (con los valores con forma de secreto
   tapados), el número de filas y la duración; nunca los valores de las filas ni la
   cadena de conexión. Los mensajes de `query_failed` no incluyen la URL de conexión ni
   su contraseña.

**Riesgo residual aceptado**: los trucos que transforman la fila antes de devolverla (por
ejemplo, pasarla a base64 con `encode(convert_to(u::text, 'UTF8'), 'base64')` o cortarla
en trozos con `substr`) se saltan las regex de la capa 4. Lo cierra un usuario de Postgres
con permisos por columna (siguiente apartado). Sin él, no apuntes `query_database` a una
BD con datos reales.

**Códigos de error**

| `code` | Cuándo |
|---|---|
| `empty_query` | La consulta está vacía (o solo tiene espacios o `;`) |
| `multiple_statements` | Hay un `;` que no es el último carácter |
| `read_only` | No empieza por `SELECT`/`WITH` o lleva una palabra prohibida |
| `secret_not_allowed` | Menciona una columna o tabla secreta, o usa un identificador `U&"…"` |
| `invalid_limit` | `limit` es menor que 1 |
| `query_failed` | Error de la BD (`query_failed: <ClaseDeError>: <primera línea>`), o dialecto distinto de Postgres y SQLite |

Con SQLite, si el archivo de `DATABASE_URL` no existe, al conectar se crea un archivo
vacío, y las consultas a tablas fallan con `query_failed` (`no such table`).

#### Usuario de Postgres de solo lectura para `MCP_DATABASE_URL`

Opcional (las capas 1–4 bastan para la BD local de desarrollo) y recomendado si usas
Postgres. Con permisos por columna, el usuario ni siquiera puede leer las columnas
secretas: `SELECT * FROM users`, `row_to_json(u)` o `u::text` fallan con
`permission denied` (`query_failed`), y hay que nombrar las columnas permitidas.

**Es un ejemplo**: revisa antes las tablas y columnas reales en `app/models/` (y en
`migrations/versions/`), porque cambian con cada HU. Ejecútalo como el dueño de la BD
(con el Postgres de Docker, el usuario `restoapi`):

```sql
CREATE ROLE resto_mcp_readonly LOGIN PASSWORD '<cambia-esto>';
GRANT CONNECT ON DATABASE restoapi TO resto_mcp_readonly;
GRANT USAGE ON SCHEMA public TO resto_mcp_readonly;

GRANT SELECT ON
    categories, dishes, dining_tables, orders, order_items,
    invoices, reservations, social_accounts, alembic_version
TO resto_mcp_readonly;

GRANT SELECT (
    id, name, email, phone, role, is_active, email_verified,
    created_at, updated_at, deleted_at, created_by, updated_by, totp_enabled
) ON users TO resto_mcp_readonly;
```

- Sin `GRANT` en las tablas de tokens (`email_verification_tokens`,
  `password_reset_tokens` y, si llegan a existir, `refresh_tokens` y `revoked_tokens`).
- En `users`, sin `password_hash`, `totp_secret` ni `totp_recovery_codes`.
- Una tabla o columna nueva no queda accesible hasta que le des permiso: es lo que se
  busca.

Después, en tu `.env` (nunca en `.env.example` ni en Git):

```dotenv
MCP_DATABASE_URL=postgresql+psycopg://resto_mcp_readonly:<cambia-esto>@localhost:5432/restoapi
```

### `run_pytest(target=None, keyword=None)`

Lanza, sin shell y con la raíz del repo como carpeta de trabajo:

```
<python del servidor> -m pytest -q --no-header -p no:cacheprovider [target] [-k keyword]
```

- `target`: ruta relativa **dentro de `tests/`**, opcionalmente con `::nodo`
  (`tests/test_health.py::test_health`). Vacío → toda la suite. Se rechaza con
  `invalid_target` si empieza por `-`, si es absoluta (o lleva unidad, `C:`), si sale de
  `tests/` (`../app`, `tests/../app`) o si no existe.
- `keyword`: expresión de `-k`, pasada como un solo argumento. Si empieza por `-` →
  `invalid_keyword`.
- No acepta otros argumentos de pytest (ni `--cov` ni plugins).

Respuesta:

```json
{"exit_code": 0, "passed": true, "timed_out": false,
 "summary": "3 passed, 3 warnings in 0.09s",
 "output_tail": "<últimas 200 líneas de stdout y stderr>",
 "duration_seconds": 1.2,
 "command": ["<python>", "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "tests/test_health.py"]}
```

- `passed` es `exit_code == 0` (un `-k` que no selecciona nada da `exit_code=5`).
- Si se pasa de `MCP_PYTEST_TIMEOUT_SECONDS`: `timed_out: true`, `exit_code: null` y, si
  no hubo resumen, `summary` = `"timed out after N seconds"`. No es un error.
- `summary` es la última línea de resumen de pytest. **Puede ir vacío** si pytest falla
  antes de imprimirlo (por ejemplo, al cargar `tests/conftest.py`); el detalle está en
  `output_tail`.
- No es de solo lectura: crea BD SQLite temporales y escribe cachés de Python.

**Ojo con el `.env` local**: `tests/conftest.py` importa `app.main`, que conecta con la BD
de `DATABASE_URL`. Si tu `.env` apunta a un Postgres apagado, la suite falla al importar
tras unos 2 minutos, con `exit_code=4` y `summary` vacío. Levanta Postgres
(`docker compose up -d db`, ver `docs/deploy.md`) o apunta `DATABASE_URL` a SQLite para el
proceso del servidor MCP (pytest hereda su entorno). Con SQLite, los tests de mesas y
reservas se saltan; el CI los ejecuta con Postgres.

### `get_ontology(rule_id=None)`

- Sin argumentos: `{"path": "specs/ontology.md", "content": "<texto completo>"}`.
- Con `rule_id`: `{"rule_id": "R-02", "priority": "M", "text": "..."}`, leído de la tabla
  de reglas de la §4 de la ontología. Formato `R-` + dos dígitos (`R-\d{2}`), sin
  distinguir mayúsculas: `"R-02"` y `"r-02"` valen; `"R-2"` no.
- Lee el archivo en cada llamada: siempre devuelve la versión actual.

| `code` | Cuándo |
|---|---|
| `invalid_rule_id` | `rule_id` no tiene el formato `R-xx` |
| `rule_not_found` | La regla no está en la tabla de la §4 (`R-99`) |

## Tests

`tests/test_mcp_server.py`, `tests/test_mcp_query_database.py` y
`tests/test_mcp_dev_tools.py`, sin Postgres ni red: `pytest tests/test_mcp_*.py`.
