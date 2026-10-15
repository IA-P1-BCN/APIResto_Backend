# AGENTS.md — Resto-API_Backend

Instrucciones para agentes de código (Claude Code, OpenCode…) y para quien los
use en este repo. Prosa en español, identificadores en inglés.

## Qué es esto
API REST de gestión de un restaurante (FastAPI + PostgreSQL). La "parte 2" (P3) añade
gestión de usuarios y autenticación sobre este mismo código: login JWT, refresh,
roles, etc. Producción: restoapi-47sp.onrender.com (`/docs`, `/health`).

## Antes de escribir código (obligatorio)
1. Lee `specs/ontology.md`: es el vocabulario. Usa esos nombres exactos
   (`User`, `Role`, `RefreshToken`, `RevokedToken`…); no inventes sinónimos.
2. Lee la issue de la HU que te piden (historia y criterios de aceptación). **Al empezar
   cada sesión de una HU, la persona que la lleva establece primero su spec**: copia
   `specs/HU-TEMPLATE.md` a `specs/HU-XX-descripcion.md`, resuelve las preguntas
   abiertas (una a una, con el equipo o con el agente) y commitéala antes de escribir
   código. La guía de cómo hacerlo está al principio de la plantilla.
3. **Si la HU aún no tiene spec propia** (HU anteriores a esta regla), trabaja con la
   ontología (reglas `R-xx`) y los criterios de la issue. Si una regla falta o es
   ambigua, **para y pregunta a una persona; no la inventes**. Cuando una persona
   decida algo así, apúntalo en la sección de esa HU de `docs/ai-log.md`.
4. Una tarea = una tarjeta Kanban = una sesión = una rama = un PR. Mantenla pequeña.

## Stack
Python 3.12 · FastAPI + Uvicorn · SQLAlchemy 2.x + Alembic · Pydantic v2 +
pydantic-settings · PyJWT + bcrypt · PostgreSQL 16 · pytest + httpx · ruff.

## Estructura
```
app/{main.py, config.py, database.py, core/, models/, schemas/, routers/,
     services/, repositories/, websocket/, scripts/}
tests/{conftest.py, unit/, integration/, test_*.py}   docs/   scripts/
```
Capas: `routers` (solo HTTP) → `services` (reglas de negocio, errores de dominio,
transacciones) → `repositories` (solo consultas a la BD, sin HTTP ni reglas) →
`models`. Los `schemas` definen la entrada y salida. Una consulta nueva va en
`repositories/<entidad>_repository.py`; una regla nueva, en `services/`. El primer admin
se crea con
`python -m app.scripts.create_admin EMAIL PASSWORD [NOMBRE]`.
Los schemas de entrada y salida van separados; `password_hash` nunca sale en un schema.

## Comandos
```
ruff check .                     # lint (arreglar: ruff check . --fix)
pytest                           # tests
pytest --cov=app --cov-report=term-missing   # el CI exige la cobertura mínima (COVERAGE_MIN)
```
Migraciones con Alembic (`alembic.ini`, `migrations/versions/`; ver `docs/deploy.md`):
`alembic upgrade head` y `alembic revision --autogenerate -m "descripcion"`. Un cambio
de modelo sin migración rompe `tests/test_migrations.py`.
Ojo: con SQLite local, los tests de mesas/reservas se saltan; el CI usa Postgres y
puede fallar donde tú no viste nada.

## Convenciones
- Código (tablas, campos, enums, endpoints, variables, funciones) en **inglés**.
  Commits, issues y documentación en **español**.
- Errores: `{"detail": "...", "code": "..."}` con el código HTTP correcto
  (400/401/403/404/409/422/429).
- Sin comentarios `#` en el código (el equipo los quitó en #58): nombres claros y
  docstrings breves.
- Cada endpoint: `summary`, `tags` y ejemplos en Swagger. Registra en el log las
  operaciones relevantes y los errores (nunca secretos ni contraseñas).
- Si cambia el modelo: migración de Alembic. Si cambia el contrato: actualiza
  `docs/api.md` y avisa de `breaking-api`.
- Commits: `feat(ámbito): …`, `fix(ámbito): …`, `test(ámbito): …`, `docs(ámbito): …`,
  `ci: …`, `chore(deps): …`.
- Rama: `feature/HU-XX-descripcion` desde `dev`. PR: `[HU-XX] Descripción`.

## Los tests son el contrato
Escribe tests (caso feliz + al menos un 4xx por endpoint). Si un test falla, **arregla
el código; nunca borres ni debilites el test** salvo que la spec haya cambiado.

## Qué NO debes hacer
- No subir secretos, claves ni `.env`; solo `.env.example` sin valores reales.
- No hacer push a `main` ni a `dev`; todo va por PR con otra persona revisando.
- No saltarte tests ni lint, ni usar `--no-verify`.
- No guardar contraseñas ni tokens en claro; no loguearlos.
- No inventar roles, campos ni endpoints que no estén en la ontología o la spec.
- No tocar el módulo de otra persona sin avisar.
- No añadir dependencias sin necesidad ni sin mencionarlo en el PR.

## Seguridad (revisión humana especial)
Todo código generado se revisa a mano, sobre todo: hash de contraseñas, validación de
JWT (firma, `exp`, `jti` revocado), permisos por rol y manejo de secretos.

## Registro de IA
Tras cada sesión relevante, añade una entrada en `docs/ai-log.md`: herramienta y
modelo, prompt clave, qué se aceptó y qué se rechazó (y por qué), alucinaciones y
cómo se corrigieron. Lo escribe quien lanzó la sesión, no el agente.

## Definition of Done (resumen)
Criterios de aceptación cumplidos · lint limpio · tests pasando · errores con
formato estándar · Swagger actualizado · migración si hay cambio de modelo · PR
aprobado por otra persona · aceptada por Levi (PO).
