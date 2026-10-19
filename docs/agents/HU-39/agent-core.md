# Agente Especialista — Core · HU-39

## Rol
Eres el especialista del paquete `mcp_server/`: ajustes, construcción del servidor y
arranque. Oleada 1, en paralelo con `agent-tools-db` y `agent-tools-dev`.

## Antes de empezar
1. Lee `AGENTS.md` ("Convenciones" y "Qué NO debes hacer").
2. Lee `specs/HU-39-servidor-mcp.md`: "SDK y versión", "Ubicación y estructura",
   "Configuración", "Arranque", "Logs" y "Docker y producción".
3. Lee `docs/agents/HU-39/lead.md`, sobre todo el contrato compartido.
4. Confirma la API del SDK instalado leyendo su código (`mcp/server/mcpserver/server.py`,
   `mcp/types`): **es la 2.x**; `mcp.server.fastmcp` no existe.

## Archivos exclusivos
`mcp_server/__init__.py`, `mcp_server/__main__.py`, `mcp_server/config.py`,
`mcp_server/server.py`, `mcp_server/tools/__init__.py` y la línea `mcp_server/` de
`.dockerignore` (solo añadir esa línea).

## Tareas
1. `config.py`: `McpSettings` y `get_settings()` tal como fija el contrato, más
   `REPO_ROOT`. Lee `.env` con `extra="ignore"`. No importa nada de `app/`.
2. `server.py`: `build_server()` crea `MCPServer("resto-api-dev", instructions=...)` y
   registra `query_database`, `run_pytest` y `get_ontology` (importadas de
   `mcp_server.tools.*`) con su `description` en inglés. Anotaciones:
   `readOnlyHint=True` en `query_database` y `get_ontology`; `run_pytest` sin ella.
   No crea el motor de BD ni lee archivos al construirse.
3. `__main__.py`: `main()` configura `logging` a `stderr` (logger `mcp_server`), sale con
   `1` y un mensaje en `stderr` si `ENVIRONMENT` es `production`, y si no llama a
   `build_server().run()` (stdio). Nada por `stdout`.
4. `__init__.py` y `tools/__init__.py`: docstring de una línea, sin lógica.
5. `.dockerignore`: añade `mcp_server/`.

## Handoff
- `ruff check mcp_server` limpio en tus archivos.
- Cuando el líder confirme que las herramientas existen:
  `python -c "from mcp_server.server import build_server; build_server()"` sin errores.
- Informe al líder: archivos, firmas expuestas y cualquier diferencia con el contrato
  (si la hay, explica por qué; no la impongas).

## Prohibiciones
- No escribas las herramientas (son de `agent-tools-db` y `agent-tools-dev`) ni tests.
- No toques `app/`, `migrations/`, `requirements.txt` ni otras líneas de `.dockerignore`.
- No uses git ni instales paquetes. Sin comentarios `#`.

## Informe de desempeño
**Qué hice.** Leí `AGENTS.md`, la spec, `lead.md` y este archivo, y comprobé la API del
SDK instalado (`mcp/server/mcpserver/server.py`, `mcp_types._types.ToolAnnotations`)
antes de escribir: `MCPServer(name, instructions=...)`, `server.tool(name, description,
annotations)` devuelve un decorador que llama a `add_tool`, `run()` usa stdio por defecto y
`ToolAnnotations` acepta `read_only_hint` o el alias `readOnlyHint` (en el cable sale como
`readOnlyHint`).

**Archivos.**
- `mcp_server/__init__.py`, `mcp_server/tools/__init__.py`: solo docstring.
- `mcp_server/config.py`: `REPO_ROOT: Path`, `class McpSettings(BaseSettings)` con los seis
  campos del contrato, propiedad `database_url` y `get_settings()` con `lru_cache`.
- `mcp_server/server.py`: `build_server() -> MCPServer` con nombre `"resto-api-dev"`,
  `instructions` en inglés y las tres herramientas registradas con
  `server.tool(name=..., description=..., annotations=...)(func)`;
  `ToolAnnotations(read_only_hint=True)` en `query_database` y `get_ontology`, ninguna en
  `run_pytest`. No crea el motor ni lee archivos.
- `mcp_server/__main__.py`: `main() -> int` y `raise SystemExit(main())` bajo
  `if __name__ == "__main__"`; `logging.basicConfig(stream=sys.stderr)`; con
  `ENVIRONMENT=production` escribe un mensaje en `stderr` y devuelve 1.
- `.dockerignore`: añadida solo la línea `mcp_server/` al final.

**Diferencias con el contrato (pequeñas, para que el líder decida).**
- `env_file` es `REPO_ROOT / ".env"` y no `".env"`: así se lee el mismo `.env` de la API
  aunque el cliente MCP lance el servidor desde otra carpeta.
- En `main()`, `build_server` se importa dentro de la función, después de la comprobación
  de `production`: así esa comprobación funciona aunque falle una herramienta o el SDK.
- La comparación con `production` ignora mayúsculas y espacios.

**Comandos y resultados.**
- `ruff check` de mis cinco archivos: `All checks passed!`.
- Script en la scratchpad que carga `get_settings()` (devuelve `development`, 100 y URL no
  vacía) y llama a `build_server()` con un stub para `tools/database.py`, que aún no
  existía; `ontology.py` y `pytest_runner.py` eran los reales. Con
  `mcp.Client(build_server())`: `list_tools` da las tres herramientas con descripción y
  `read_only_hint=True` donde toca; `call_tool("get_ontology", {"rule_id": "R-02"})`
  devuelve la fila de R-02 sin error.
- `ENVIRONMENT=production python -m mcp_server`: sale con 1, stdout vacío y el mensaje en
  stderr.

**Errores míos.** En la prueba, el `print` del resultado falló por la codificación cp1252 de
la consola de Windows (caracteres `≥` y `→` de R-02). Lo arreglé con
`PYTHONIOENCODING=utf-8`; era un fallo del script de prueba, no del servidor.

**Dudas abiertas.**
- Las herramientas devuelven `dict` sin tipo concreto, así que el SDK las registra como
  no estructuradas: el resultado llega como `TextContent` con el JSON y
  `structured_content=None`. Cumple la spec; los tests deben leer `content[0].text`.
- Falta probar el arranque real por stdio con `tools/database.py` real. Queda para el
  handoff del líder.
