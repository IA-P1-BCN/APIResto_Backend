# Agente Especialista — Herramientas de desarrollo · HU-39

## Rol
Eres el especialista de `run_pytest` y `get_ontology`. Oleada 1, en paralelo con
`agent-core` y `agent-tools-db`.

## Antes de empezar
1. Lee `AGENTS.md` ("Comandos" y "Qué NO debes hacer").
2. Lee `specs/ontology.md` entero: vas a leer su tabla de reglas (§4) con código.
3. Lee `specs/HU-39-servidor-mcp.md`, secciones `run_pytest` y `get_ontology`.
4. Lee `docs/agents/HU-39/lead.md` (contrato: `REPO_ROOT`, `get_settings()`, `ToolError`).

## Archivos exclusivos
`mcp_server/tools/pytest_runner.py`, `mcp_server/tools/ontology.py`.

## Tareas
### `run_pytest(target=None, keyword=None) -> dict`
1. Valida `target`: relativo, sin `-` inicial, que al resolverlo (quitando `::nodo`)
   quede dentro de `REPO_ROOT / "tests"` y exista. Si no → `ToolError invalid_target`.
2. Valida `keyword`: sin `-` inicial → si no, `ToolError invalid_keyword`.
3. Comando: `[sys.executable, "-m", "pytest", "-q", "--no-header", "-p",
   "no:cacheprovider", *([target] if target), *(["-k", keyword] if keyword)]`.
4. `subprocess.run(cmd, cwd=REPO_ROOT, shell=False, capture_output=True, text=True,
   timeout=MCP_PYTEST_TIMEOUT_SECONDS)`. `TimeoutExpired` → `timed_out: true`,
   `exit_code: None`, `passed: false`, con la salida parcial que haya.
5. Respuesta de la spec: `summary` = última línea no vacía que parezca el resumen de
   pytest (contiene `passed`, `failed`, `error`, `skipped` o `no tests ran`);
   `output_tail` = últimas 200 líneas de stdout + stderr.
6. Log `info` con el código de salida y la duración; `warning` en cada rechazo.

### `get_ontology(rule_id=None) -> dict`
1. Lee `REPO_ROOT / "specs" / "ontology.md"` en cada llamada (UTF-8).
2. Sin `rule_id`: `{"path": "specs/ontology.md", "content": ...}`.
3. Con `rule_id`: valida `^R-\d{2}$` sin distinguir mayúsculas (si no →
   `invalid_rule_id`), normaliza a mayúsculas y busca la fila `| R-xx | Prio | Regla |`
   de la tabla. Devuelve `{"rule_id", "priority", "text"}`. No existe → `rule_not_found`.

## Handoff
- `ruff check mcp_server/tools` limpio en tus dos archivos.
- Prueba manual: `get_ontology("R-02")` devuelve la regla real. **No** pruebes
  `run_pytest` lanzando la suite entera desde dentro de otra ejecución de pytest; basta
  con `run_pytest("tests/test_health.py")` a mano.
- Informe al líder: firmas finales y cómo detectas `summary`.

## Prohibiciones
- `shell=True` nunca. No aceptes argumentos libres de pytest.
- No toques otros archivos de `mcp_server/`, ni `app/`, ni `specs/`. No uses git ni
  instales paquetes. Sin comentarios `#`.

## Informe de desempeño
_(Rellénalo al terminar: qué hiciste, archivos, comandos y resultados, errores que
cometiste y cómo los solucionaste, dudas abiertas.)_
