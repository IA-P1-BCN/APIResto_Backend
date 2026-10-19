# Agente Especialista — Documentación · HU-39

## Rol
Eres el especialista en la documentación del servidor MCP. Oleada 2: empiezas cuando el
líder ha aceptado la oleada 1. Trabajas en paralelo con `agent-tests`.

## Antes de empezar
1. Lee `AGENTS.md` ("Convenciones" y "Registro de IA").
2. Lee `specs/HU-39-servidor-mcp.md` completa.
3. Lee `docs/agents/HU-39/lead.md` y el código de `mcp_server/` (solo lectura).
4. Lee `docs/api.md` (estilo y orden de secciones) y el final de `docs/ai-log.md`
   (plantilla de las entradas).

## Archivos exclusivos
- `docs/api.md`: **solo una sección nueva** al final, "Servidor MCP para agentes (local)
  · HU-39". No cambies las demás.
- `mcp_server/README.md` (nuevo).
- `.env.example`: solo añadir las líneas `MCP_*` comentadas, sin valores reales.

## Tareas
1. `docs/api.md`: qué es, que no es un endpoint HTTP ni se despliega, las tres
   herramientas con parámetros, respuesta y tabla de `code` de error, y el enlace a
   `mcp_server/README.md`.
2. `mcp_server/README.md`:
   - requisitos (`mcp==2.3.0` en `requirements.txt`) y arranque (`python -m mcp_server`);
   - registro en Claude Code (`claude mcp add resto-api-dev -- python -m mcp_server` o
     `.mcp.json`) y en OpenCode (`opencode.json`, clave `mcp`), como ejemplo para copiar,
     sin tocar `opencode.json`;
   - variables `MCP_*` y sus valores por defecto;
   - seguridad: capas de solo lectura, secretos de R-02, solo local, no en producción;
   - cómo crear un usuario de Postgres con solo `SELECT` para `MCP_DATABASE_URL`.
3. Comprueba que lo que documentas coincide con el código. Si no coincide, avisa al
   líder; no lo cambies tú.
4. Prepara en tu informe (no en el archivo) un **borrador** de la entrada de HU-39 para
   `docs/ai-log.md`, con la plantilla de la bitácora (herramienta y modelo, prompt
   clave, qué se aceptó y qué se rechazó, alucinaciones y cómo se corrigieron; por
   ejemplo, el cambio de `FastMCP` a `MCPServer` en el SDK 2.x y el nombre de la
   carpeta). La entrada final la escribe Levi.

## Handoff
- `ruff check .` sigue limpio.
- Informe al líder: secciones tocadas, borrador del ai-log y una línea para el PR: "sin
  breaking-api; no cambia ningún endpoint".

## Prohibiciones
- No escribas en `docs/ai-log.md` ni en `specs/`.
- No toques código (`mcp_server/*.py`, `app/`, `tests/`) ni `opencode.json`.
- No añadas `docs/Briefing del Proyecto.md` a Git. No uses git.

## Informe de desempeño
**Qué hice.** Leí `AGENTS.md`, la spec (decisiones 1–5), `lead.md`, este archivo, los
informes de la oleada 1, todo `mcp_server/` (solo lectura), `docs/api.md`, `.env.example`,
el principio y el final de `docs/ai-log.md`, `app/models/` (para el ejemplo de permisos por
columna), `docker-compose.yml` y `opencode.json` (solo lectura). Documenté a partir del
código, no de la spec, y comprobé las respuestas reales con un cliente en proceso.

**Archivos.**
- `mcp_server/README.md` (nuevo): requisitos (API 2.x, `MCPServer`, por qué `mcp_server/`),
  arranque por stdio, registro en Claude Code (`claude mcp add`, `.mcp.json` de ejemplo sin
  commitear) y en OpenCode (bloque `mcp`, tipo `local`, `command` como lista, con enlace a
  su documentación), variables `MCP_*`, las tres herramientas con respuesta y `code` de
  error, las capas de `query_database` (incluida la decisión 5), el riesgo residual, el SQL
  de ejemplo del usuario de solo lectura con permisos por columna y el aviso del `.env` con
  Postgres apagado en `run_pytest`.
- `docs/api.md`: solo la sección nueva al final, "Servidor MCP para agentes (local) ·
  HU-39". `docs/api.md` no tiene índice, así que no hubo que añadir ninguna entrada.
- `.env.example`: solo el bloque `MCP_*` comentado al final, con los valores por defecto.

**Comandos y resultados.**
- Script en la scratchpad con `mcp.Client(build_server())` y un SQLite temporal:
  `list_tools` da las tres herramientas con sus parámetros y `read_only_hint=True` en
  `query_database` y `get_ontology`; `get_ontology("r-02")` devuelve la fila de R-02;
  `query_database("select 1 as a, 'x' as b")` devuelve el JSON documentado. Un `ToolError`
  llega con `isError: true` y el texto `Error executing tool get_ontology: invalid_rule_id:
  ...` (el prefijo lo pone el SDK; está documentado así).
- `.venv/Scripts/python -m ruff check .` → `All checks passed!`.

**Errores y cómo los solucioné.**
- Primer borrador del ejemplo de respuesta de `query_database` con `password_hash` en las
  columnas sin decir de qué consulta salía: nombrar esa columna se rechaza. Lo cambié a "por
  ejemplo, para `SELECT * FROM users LIMIT 1`".
- Había escrito que con SQLite sin archivo "la consulta falla"; `SELECT 1` funciona. Lo
  precisé: fallan las consultas a tablas.

**Dudas abiertas (para el líder; no he cambiado código ni spec).**
- `.mcp.json` no está en `.gitignore`: con `claude mcp add --scope project` alguien podría
  commitearlo. El README lo advierte.
- Un error imprevisto de una herramienta (por ejemplo, que falte `specs/ontology.md`) llega
  al cliente solo como `Error executing tool <nombre>`, sin detalle.
- El docstring de `_contains_secret_value` en `database.py` aún dice "bcrypt o Fernet",
  aunque también comprueba SHA-256.
