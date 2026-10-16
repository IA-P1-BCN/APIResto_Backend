# Agente Especialista — CI y documentación · HU-34

## Rol
Eres el especialista que sube el umbral de cobertura del CI y lo documenta. Paso 2:
empiezas cuando el líder ha aceptado a `agent-tests` con la cobertura al 100 %.

## Antes de empezar
1. Lee `AGENTS.md` ("Comandos", "Registro de IA").
2. Lee `specs/HU-34-cobertura-tests.md`, "Solution" y "Decisiones de la sesión".
3. Lee `docs/agents/HU-34/lead.md` (parámetros compartidos).
4. Lee `.github/workflows/ci.yml` y la sección 3 de `docs/deploy.md`.

## Archivos exclusivos
`.github/workflows/ci.yml` (solo la línea de `--cov-fail-under`) y `docs/deploy.md` (solo
la fila de `COVERAGE_MIN`).

## Tareas
1. `ci.yml`: cambia `${{ vars.COVERAGE_MIN || 0 }}` por `${{ vars.COVERAGE_MIN || 98 }}`.
   Nada más del workflow.
2. `docs/deploy.md`: la fila de `COVERAGE_MIN` pasa a decir que el umbral es `98` desde
   HU-34 y que, si la variable existe, manda sobre el valor por defecto de `ci.yml`.
3. Comprueba que `pytest --cov=app --cov-fail-under=98` pasa en local.
4. Prepara en tu informe (no en el archivo) un **borrador** de la entrada de HU-34 para
   `docs/ai-log.md` con la plantilla de la bitácora. Inclúyelo: cobertura antes/después,
   tests nuevos, que no hubo pragmas y los avisos de la spec (assert de
   `test_keep_awake.py:74`, tests siempre en SQLite). La entrada final la escribe Levi.

## Handoff
- `ruff check .` limpio y `pytest` sin cambios respecto al paso 1.
- Informe al líder: el diff de las dos líneas, el borrador del ai-log y el recordatorio
  para Levi de poner la variable `COVERAGE_MIN` de GitHub a 98 o borrarla.

## Prohibiciones
- No toques `app/`, `tests/`, `specs/`, `README.md` ni otros workflows.
- No cambies variables ni secretos de GitHub: eso lo hace Levi.
- No escribas en `docs/ai-log.md`.
- No añadas `docs/Briefing del Proyecto.md` a Git.
