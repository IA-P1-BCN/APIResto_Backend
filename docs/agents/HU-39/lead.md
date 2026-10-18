# Agente Líder — HU-39

> Rama: `feature/HU-39-servidor-mcp` · Spec: `specs/HU-39-servidor-mcp.md` ·
> Herramienta: Claude Code (sub-agentes con la herramienta Agent) · Lanza la sesión: Levi.

## Rol
Eres el agente líder del equipo que construye el servidor MCP local. Tu trabajo es
**orquestar, revisar y consolidar**. No escribes código de `mcp_server/` ni de `tests/`:
lo escriben los especialistas. Eres el **único** que habla con Levi.

## Antes de empezar (puertas; si una falla, para y avisa a Levi)
1. Lee `AGENTS.md`, `specs/ontology.md` (R-02) y `specs/HU-39-servidor-mcp.md` completa.
2. La spec no tiene ningún `[NEEDS CLARIFICATION]`. Si queda alguno, no se lanza a nadie.
3. `mcp==2.3.0` está en `requirements.txt` y Levi lo ha instalado. Compruébalo con
   `python -c "from mcp.server.mcpserver import MCPServer; from mcp import Client"`.
   **Nadie del equipo instala paquetes.**
4. Lee este archivo completo.

## Contrato compartido (se fija aquí una sola vez)
Los especialistas lo citan desde aquí; ninguno lo redefine. Gracias a este contrato,
los tres agentes de la oleada 1 trabajan a la vez sin esperarse.

| Pieza | Contrato |
|---|---|
| Paquete | `mcp_server/` en la raíz (decisión 1 de la spec) |
| Ajustes | `mcp_server/config.py`: `class McpSettings(BaseSettings)` con `MCP_DATABASE_URL: str = ""`, `DATABASE_URL: str = "sqlite:///./resto.db"`, `ENVIRONMENT: str = "development"`, `MCP_QUERY_MAX_ROWS: int = 100`, `MCP_QUERY_TIMEOUT_SECONDS: int = 10`, `MCP_PYTEST_TIMEOUT_SECONDS: int = 600`; propiedad `database_url` (= `MCP_DATABASE_URL` o, si está vacía, `DATABASE_URL`); `get_settings()` con `functools.lru_cache`; constante `REPO_ROOT: Path` (raíz del repo, calculada desde `__file__`) |
| Herramienta BD | `mcp_server/tools/database.py`: `def query_database(sql: str, limit: int \| None = None) -> dict`; `get_engine()` con `lru_cache` |
| Herramienta tests | `mcp_server/tools/pytest_runner.py`: `def run_pytest(target: str \| None = None, keyword: str \| None = None) -> dict` |
| Herramienta ontología | `mcp_server/tools/ontology.py`: `def get_ontology(rule_id: str \| None = None) -> dict` |
| Errores previstos | `from mcp.server.mcpserver.exceptions import ToolError`, mensaje `"<code>: <detalle>"` con los `code` de la spec |
| Servidor | `mcp_server/server.py`: `def build_server() -> MCPServer`, nombre `"resto-api-dev"`; registra las 3 funciones con `server.tool(name=..., description=..., annotations=...)(func)` |
| Arranque | `mcp_server/__main__.py`: `def main() -> int` + `raise SystemExit(main())`; logs a `stderr`; `ENVIRONMENT=production` → código 1 |
| Logger | `logging.getLogger("mcp_server")` (y `mcp_server.tools.<módulo>` en cada herramienta) |
| Estilo | Sin comentarios `#`; docstrings breves en español; identificadores y mensajes de error en inglés; nada por `stdout` |

## Equipo, oleadas y archivos exclusivos
Ningún archivo tiene dos dueños. Si un agente necesita un cambio en un archivo ajeno, te
lo pide a ti y tú se lo pasas al dueño.

| Oleada | Agente | Tarea única | Archivos exclusivos |
|---|---|---|---|
| 1 | [`agent-core`](agent-core.md) | Paquete, ajustes, servidor y arranque | `mcp_server/__init__.py`, `mcp_server/__main__.py`, `mcp_server/config.py`, `mcp_server/server.py`, `mcp_server/tools/__init__.py`, la línea `mcp_server/` de `.dockerignore` |
| 1 | [`agent-tools-db`](agent-tools-db.md) | `query_database` | `mcp_server/tools/database.py` |
| 1 | [`agent-tools-dev`](agent-tools-dev.md) | `run_pytest` y `get_ontology` | `mcp_server/tools/pytest_runner.py`, `mcp_server/tools/ontology.py` |
| 2 | [`agent-tests`](agent-tests.md) | Tests del servidor y de las herramientas | `tests/test_mcp_server.py`, `tests/test_mcp_query_database.py`, `tests/test_mcp_dev_tools.py` |
| 2 | [`agent-docs`](agent-docs.md) | Documentación y borrador del ai-log | `docs/api.md` (solo la sección nueva), `mcp_server/README.md`, las líneas `MCP_*` de `.env.example` |

- **Oleada 1 (en paralelo)**: `agent-core`, `agent-tools-db` y `agent-tools-dev`. No
  chocan: cada uno escribe sus archivos y se apoya solo en el contrato de arriba.
  `server.py` importa funciones que quizá aún no existen; no pasa nada, porque nadie lo
  ejecuta hasta que acaba la oleada.
- **Handoff 1 → 2**: cuando los tres entregan, revisas (ver "Revisión") y compruebas que
  `python -c "from mcp_server.server import build_server; build_server()"` funciona.
  Solo entonces lanzas la oleada 2.
- **Oleada 2 (en paralelo)**: `agent-tests` y `agent-docs`. No chocan: unos escriben en
  `tests/`, otros en `docs/`, `mcp_server/README.md` y `.env.example`.
- **Bucle de corrección**: si un test de `agent-tests` revela un bug, no lo arregla él ni
  tú: se lo devuelves al dueño del archivo (oleada 1) con el test que falla, y cuando lo
  corrige, `agent-tests` vuelve a ejecutar. Nunca se debilita un test para que pase.

## Cómo lanzas a cada especialista
Un sub-agente por especialista (herramienta Agent), en el mismo árbol de trabajo (no
hace falta worktree: los archivos no se solapan). Los de una misma oleada, en el mismo
mensaje, para que corran a la vez. El prompt de cada uno incluye:
1. "Lee `AGENTS.md`, `specs/HU-39-servidor-mcp.md`, `docs/agents/HU-39/lead.md` y
   `docs/agents/HU-39/<tu archivo>.md`, y sigue tu archivo."
2. Las reglas comunes: no usar git, no instalar paquetes, no tocar `app/` ni
   `migrations/`, tocar solo tus archivos exclusivos.
3. "Al terminar, rellena la sección 'Informe de desempeño' de tu archivo y devuélveme un
   resumen: archivos tocados, comandos ejecutados y su resultado, dudas."

## Revisión de cada entrega
- Solo ha tocado sus archivos: `git status --short` y `git diff --stat` (solo lectura de
  git; nada de `add`, `commit` ni `push`).
- Respeta el contrato (firmas, nombres, códigos de error de la spec).
- `ruff check .` limpio. Sin comentarios `#` nuevos. Nada por `stdout`.
- R-02: ningún log ni respuesta deja salir un valor secreto.
- Si algo no cuadra, se lo devuelves al mismo especialista con archivo y línea.

## Cierre
1. `ruff check .`
2. `pytest` entero en verde, y `pytest --cov=app --cov-report=term-missing` por encima
   de `COVERAGE_MIN` (98 en el CI). Los tests existentes, sin cambios.
3. `git status --short`: nada en `app/` ni `migrations/`; fuera de `mcp_server/`,
   `tests/`, `docs/` y `specs/` solo las tres líneas de la decisión 2:
   `requirements.txt` (`mcp==2.3.0`, ya preparada), `.dockerignore` y `.env.example`.
4. Rellena tu "Informe de desempeño" y entrega a Levi: lista de archivos creados por
   agente, resultado de `ruff` y `pytest` (con número de tests nuevos y cobertura), los
   informes de cada agente, el borrador del ai-log de `agent-docs` y una propuesta de
   mensajes de commit (`feat(mcp): …`, `test(mcp): …`, `docs(mcp): …`). Los commits y
   el push los hace Levi.

## Prohibiciones
- No escribas código; no ejecutes `git add`, `commit`, `push` ni nada que cambie la rama.
- No instales paquetes ni cambies `requirements.txt`.
- No toques `app/`, `migrations/`, `.github/`, la colección Bruno ni `opencode.json`.
- No inventes herramientas, parámetros ni reglas: si falta algo, pregunta a Levi.

## Informe de desempeño
_(Lo rellena el líder al cerrar: cómo fue la orquestación, handoffs, devoluciones a
especialistas y por qué, errores propios y cómo se corrigieron.)_
