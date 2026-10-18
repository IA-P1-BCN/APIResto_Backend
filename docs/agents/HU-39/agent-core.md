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
_(Rellénalo al terminar: qué hiciste, archivos, comandos y resultados, errores que
cometiste y cómo los solucionaste, dudas abiertas.)_
