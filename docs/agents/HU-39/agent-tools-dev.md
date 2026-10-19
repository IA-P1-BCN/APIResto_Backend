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
**Qué hice.** Implementé `run_pytest` y `get_ontology` como funciones normales que
devuelven un `dict`, según la spec y el contrato del líder. Los errores previstos son
`ToolError("<code>: <detalle>")`. Cada rechazo deja un `warning` con su `code`, y cada
llamada que sale bien deja un `info`.

**Archivos** (solo los míos): `mcp_server/tools/pytest_runner.py` y
`mcp_server/tools/ontology.py`. Cuando empecé, `mcp_server/` no existía: creé solo la
carpeta `tools/`, sin `__init__.py`, que es de `agent-core`. Cuando hice las pruebas, el
`config.py` de `agent-core` ya existía y lo usé tal cual, sin stub.

**Firmas y funciones internas** (sirven a `agent-tests`):
- `run_pytest(target: str | None = None, keyword: str | None = None) -> dict`.
  Funciones internas: `validate_target`, `validate_keyword`, `build_command`,
  `find_summary(stdout, stderr="")`, `tail_output(stdout, stderr, max_lines=200)`.
  Constantes: `BASE_COMMAND`, `OUTPUT_TAIL_LINES` y `SUMMARY_PATTERN`.
- `get_ontology(rule_id: str | None = None) -> dict`. Funciones internas:
  `read_ontology()` y `parse_rules(content) -> {rule_id: (prioridad, texto)}`.
  Constante: `ONTOLOGY_RELATIVE_PATH`.

**Detalles de diseño.**
- `target`: rechazo cualquier valor que empiece por `-`, también tras espacios. Quito
  el `::nodo`. Rechazo las rutas absolutas, en estilo POSIX o Windows, las que llevan
  unidad (`C:`) y las que empiezan por `/` o `\`. El resto lo resuelvo contra `REPO_ROOT`:
  debe quedar dentro de `REPO_ROOT/tests` (`is_relative_to`) y existir. Un `target`
  vacío o `None` lanza la suite entera.
- `summary`: recorro las líneas de stdout de abajo arriba (después, las de stderr) y le
  quito los `=` decorativos a cada una. Devuelvo la primera que encaja con
  `\d+ (passed|failed|errors?|skipped|deselected|xfailed|xpassed)` o `no tests ran`.
  Exijo el número delante para no tomar como resumen una línea como `AssertionError`. Si
  no encuentro ninguna, devuelvo `""`. En un timeout sin resumen, devuelvo
  `"timed out after N seconds"`.
- `subprocess.run(..., cwd=REPO_ROOT, shell=False, check=False, capture_output=True,
  text=True, timeout=..., stdin=subprocess.DEVNULL)`. Añadí `check=False` porque lo pide
  ruff (PLW1510). Añadí `stdin=DEVNULL` para que el pytest hijo no herede el stdin del
  servidor, que es el canal del protocolo MCP. En un `TimeoutExpired` convierto a texto
  la salida parcial (puede llegar en `bytes`).
- `get_ontology`: `fullmatch` de `R-\d{2}` sin distinguir mayúsculas y con `re.ASCII`,
  así que `"R-02\n"` y los dígitos no ASCII no pasan. Solo leo las filas de la tabla de
  la sección `## 4.`. El texto es todo lo que hay hasta el último `|` de la fila.

**Comandos y resultados.**
- `ruff check mcp_server/tools/pytest_runner.py mcp_server/tools/ontology.py`: limpio.
- `get_ontology("R-02")` devuelve `R-02 · M · "Contraseña ≥ 8 caracteres…"`;
  `get_ontology("r-15")` devuelve `R-15 · S · "Verificación de email (HU-33)…"`. Las
  llamadas con `R-99` dan `rule_not_found`. Las que llevan `X-1`, `R-2` o `"R-02\n"` dan
  `invalid_rule_id`. Sin argumentos devuelve el archivo entero.
- Estos `target` se rechazan con `invalid_target`: `../app`, `--cov`, `C:/Windows`,
  `/etc`, `tests/nope.py`, `app/main.py`, `tests/../app` y `tests\..\..`. El `keyword`
  `-p x` da `invalid_keyword`.
- `run_pytest("tests/test_health.py")` devuelve `exit_code=0`, `passed=True` y el
  summary `"3 passed, 3 warnings in 0.09s"`, en unos 1,2 s. Con `::test_health`, el
  summary es `"1 passed, …"`. Con un `-k` que deselecciona todo: `exit_code=5` y summary
  `"3 deselected, 3 warnings in 0.01s"`. No lancé la suite entera.

**Errores y cómo los solucioné.**
1. La primera pasada de ruff marcó el orden de los imports (I001) y la falta de `check`
   en `subprocess.run` (PLW1510). Corregí los dos.
2. La primera vez, `run_pytest("tests/test_health.py")` devolvió `exit_code=4` tras
   132 s. Llamé a pytest directamente y pasó lo mismo: `tests/conftest.py` importa
   `app.main`, y el `.env` local apunta a un Postgres que no estaba arrancado. El fallo es
   del entorno, no de la herramienta. Repetí la prueba con
   `DATABASE_URL=sqlite:///<scratchpad>/manual.db`: el hijo hereda el entorno, y pasó.
3. Con un `-k` que no seleccionaba nada, el summary salía vacío porque el patrón no
   incluía `deselected`. Amplié el patrón con `deselected`, `xfailed` y `xpassed`.

**Dudas abiertas.**
- Para `agent-tests`: si comprueba los argumentos exactos de `subprocess.run`, tiene que
  contar con `check=False` y `stdin=subprocess.DEVNULL`, que no aparecen en la lista del
  archivo del agente.
- Cuando pytest falla antes de imprimir el resumen (por ejemplo, un error al cargar el
  conftest), `summary` es `""` y el detalle queda en `output_tail`. ¿Basta así?
- Si `specs/ontology.md` no existe, el `OSError` no se convierte en `ToolError`, porque
  la spec no define un `code` para ese caso. El cliente lo recibe igualmente como un
  error de la herramienta.
- Con el `.env` local apuntando a un Postgres apagado, `run_pytest` tarda unos 2 min en
  devolver `exit_code=4`. Conviene decirlo en el README (`agent-docs`).
