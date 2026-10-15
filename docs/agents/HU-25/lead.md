# Agente líder · HU-25

> Issue: #68 · Rama: `feature/HU-25-cambio-password-perfil` · Spec:
> `specs/HU-25-cambio-password-perfil.md` · Sesión: 2026-10-15 · Herramienta: Claude Code ·
> Opus 5.5 · Lanzó la sesión: Levi.

## Rol
Orquestar el equipo de agentes de la HU-25: verificar el estado del repo, cerrar las
decisiones técnicas con Levi, redactar la spec, lanzar a los especialistas respetando las
dependencias, revisar el trabajo de cada uno y consolidar.

## Lecturas previas
`AGENTS.md`, `specs/ontology.md` (R-01 a R-04, R-11), `docs/Briefing del Proyecto.md`,
el Plan de Proyecto v3 (página 4, fila HU-25), `docs/api.md`, `docs/ai-log.md` y el código
de usuarios (`schema_user.py`, `router_user.py`, `auth.py`, `user_service.py`,
`user_repository.py`, `security.py`, `permissions.py`, `model_user.py`) con sus tests.

## Qué hizo
1. Verificó la rama y los archivos. Detectó que `app/crud/` solo tenía restos de
   `__pycache__`, que no existen `specs/HU-27-*.md` ni `bruno/` en `dev`, y que el router
   `/users` exige `admin` a nivel de router.
2. Propuso las decisiones técnicas y esperó el OK de Levi (ver la spec, "Decisiones de la
   sesión").
3. Redactó `specs/HU-25-cambio-password-perfil.md`, como exige `AGENTS.md`.
4. Lanzó a los especialistas en orden y revisó cada entrega con `git diff` antes de lanzar
   al siguiente.
5. Consolidó: `ruff check .` y `pytest --cov=app` completos.
6. Hizo los commits por encargo de Levi y le recordó la entrada de `docs/ai-log.md`.

## Equipo y dependencias

| Agente | Tarea | Archivos exclusivos | Depende de |
|---|---|---|---|
| [`agent-schema`](agent-schema.md) | Schemas de entrada | `app/schemas/schema_user.py` | la spec |
| [`agent-service`](agent-service.md) | Reglas de negocio | `app/services/user_service.py` | `agent-schema` |
| [`agent-router`](agent-router.md) | Endpoints y Swagger | `app/routers/router_user.py`, 1 línea de `app/main.py` | `agent-service` |
| [`agent-tests`](agent-tests.md) | Tests | `tests/test_users.py` | `agent-router` |
| [`agent-docs`](agent-docs.md) | Documentación | `docs/api.md` | `agent-router` |

`agent-tests` y `agent-docs` trabajaron en paralelo. El líder propuso 3 agentes (la cadena
es secuencial); Levi eligió 5.

## Checklist de revisión de cada entrega
- Solo se tocaron los archivos asignados (`git diff --stat`).
- Vocabulario de `specs/ontology.md`.
- Errores con `{"detail", "code"}` y el HTTP correcto.
- `password_hash` no aparece en respuestas ni en logs.
- Sin cambio de modelo, así que sin migración 0007.
- Los tests existentes no se borran ni se debilitan.

## Resultado
`ruff check .` limpio · `pytest`: 599 passed, 0 failed, 0 skipped · cobertura 100 % en
`router_user.py`, `schema_user.py` y `user_service.py` (99 % en `app/`).
Commits: 95fc335 (spec), 97222c7 (feat), be56010 (test), f601792 (docs).

## Reglas para el líder
- No toca `docs/ai-log.md`: lo escribe la persona que lanzó la sesión.
- No hace commit ni push salvo que Levi lo pida.
- No inventa reglas: si falta una, pregunta a Levi y la anota en la spec.
- En local, `pytest` necesita `DATABASE_URL=sqlite:///...`; si no, intenta conectar al
  Postgres de `.env` y da timeout.
