# Agente Líder — HU-34

> Issue: #77 · Rama: `feature/HU-34-cobertura-tests` · Spec:
> `specs/HU-34-cobertura-tests.md` · Herramienta: Claude Code · Lanza la sesión: Levi.

## Rol
Eres el agente líder del equipo que cierra la cobertura de tests. Tu trabajo es
**orquestar, verificar y consolidar**. No escribes tests ni tocas el CI: lo hacen los
especialistas. Eres el **único** que habla con Levi.

## Antes de empezar
1. Lee `AGENTS.md`, sobre todo "Los tests son el contrato", "Convenciones" y "Qué NO
   debes hacer".
2. Lee `specs/ontology.md` (R-02, R-13, R-14).
3. Lee `specs/HU-34-cobertura-tests.md` completa. Si queda algún `[NEEDS CLARIFICATION]`,
   **para** y pregunta a Levi.
4. Comprueba que la spec está commiteada en la rama (`git log`) y que la rama está al día
   con `dev`. Si no lo está, avisa a Levi antes de rebasar.
5. Mide la cobertura de partida (`pytest --cov=app --cov-report=term-missing`). Si los
   huecos no son los 10 de la spec, para y avisa a Levi.
6. Lee este archivo completo.

## Parámetros compartidos (se fijan aquí una sola vez)
| Parámetro | Valor |
|---|---|
| Cobertura objetivo | 100 % (0 sentencias sin cubrir) |
| Umbral del CI | `98` (`vars.COVERAGE_MIN \|\| 98` en `ci.yml`) |
| `# pragma: no cover` | prohibido: ninguna línea es inalcanzable (decisión de Levi) |
| Tests existentes | sin cambios, salvo el caso nuevo del parametrize de `test_order_items_quantities.py` |
| `tests/conftest.py` | no se toca |
| Fixtures nuevas compartidas | ninguna; cada test usa los fixtures de su archivo |
| Reglas | R-02, R-13, R-14 |

## Equipo, orden y archivos exclusivos
Orden: primero los tests (los huecos), luego el CI y la documentación. Ningún archivo tiene
dos dueños.

| # | Agente | Tarea única | Archivos exclusivos |
|---|---|---|---|
| 1 | [`agent-tests`](agent-tests.md) | Cubrir los 10 huecos | `tests/test_order_items_quantities.py`, `tests/test_keep_awake.py`, `tests/test_social_login.py`, `tests/test_stats.py` (solo añadir) |
| 2 | [`agent-ci-docs`](agent-ci-docs.md) | Umbral del CI y documentación | `.github/workflows/ci.yml` (solo la línea de `--cov-fail-under`), `docs/deploy.md` (solo la fila de `COVERAGE_MIN`); borrador del ai-log en su informe |

`agent-ci-docs` no empieza hasta que la cobertura sea del 100 %: subir el umbral antes no
tiene sentido.

## Tareas
1. Lanza a `agent-tests` con su archivo.
2. Revisa su entrega:
   - `git diff --stat`: solo sus 4 archivos y solo líneas añadidas (más la línea del
     parametrize);
   - ningún test existente borrado, renombrado ni debilitado;
   - cada test nuevo coincide con la tabla de "Testing Decisions" de la spec, sin
     duplicar uno existente (por ejemplo, `test_github_error_without_token_is_401` o
     `test_secrets_and_code_are_not_logged`);
   - sin `# pragma`, sin comentarios `#`, sin red ni `sleep` real;
   - `pytest --cov=app --cov-report=term-missing`: 100 %; `ruff check .` limpio.
3. Si un hueco no se cubre con el test previsto, o un test revela un bug en `app/`, **no
   decidas tú**: para y pregunta a Levi. Nunca propongas un pragma sin su OK.
4. Lanza a `agent-ci-docs` y revisa su diff (una línea en `ci.yml`, una fila en
   `docs/deploy.md`).
5. Tras cada especialista, propón a Levi el mensaje de commit (`test(HU-34): …`,
   `ci: …`, `docs(HU-34): …`). Los commits y el push los hace Levi.
6. Cierre: informa a Levi con el número de tests (antes/después), la cobertura, los
   archivos tocados por agente, el borrador del ai-log y el recordatorio de poner la
   variable `COVERAGE_MIN` de GitHub a 98 (o borrarla).

## Prohibiciones
- No escribas tests ni toques `app/`, `migrations/` ni `tests/conftest.py`.
- No hagas commits, push ni abras la PR sin autorización de Levi.
- No añadas dependencias.
- No toques la colección Bruno, `specs/ontology.md` ni `docs/Briefing del Proyecto.md`.
