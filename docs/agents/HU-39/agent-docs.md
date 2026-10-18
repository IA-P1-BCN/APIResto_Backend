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
_(Rellénalo al terminar: qué hiciste, archivos, comandos y resultados, errores que
cometiste y cómo los solucionaste, dudas abiertas.)_
