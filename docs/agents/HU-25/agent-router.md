# agent-router · HU-25

> Equipo: [líder](lead.md) · Depende de: [`agent-service`](agent-service.md) · Bloquea a:
> [`agent-tests`](agent-tests.md) y [`agent-docs`](agent-docs.md)

## Tarea
Exponer los endpoints de la HU-25 (sección "Endpoints" de la spec) con Swagger completo.

## Archivos
`app/routers/router_user.py` y una sola línea de `app/main.py`. El `router` de admin y sus
endpoints no se tocan.

## Lecturas
`AGENTS.md` → `specs/ontology.md` → la spec de HU-25 → `router_user.py`, `main.py`,
`app/core/permissions.py`, `app/core/exceptions.py` (`ErrorResponse`) y
`app/routers/reservations.py` como precedente de `responses`.

## Contrato
- `me_router = APIRouter(prefix="/users", tags=["users"])`, **sin** la dependencia de
  admin; cada endpoint recibe `CurrentUser`.
- `PATCH /users/me` → 200 `UserOut`, `summary="Editar mi perfil"`; errores 401, 409, 422.
- `POST /users/me/password` → 204 sin cuerpo, `summary="Cambiar mi contraseña"`; errores
  400, 401, 403, 422.
- Errores documentados con `ErrorResponse`. El router solo hace HTTP y delega en el servicio.
- En `main.py`, `app.include_router(router_user.me_router)` justo antes de
  `app.include_router(router_user.router)`, para que `/users/me` no se confunda con
  `/users/{user_id}`.

## Por qué un router aparte
El router `/users` aplica `require_role(admin)` a todos sus endpoints. Colgar `/users/me`
de él daría 403 a cualquier rol que no sea admin. Quitar la dependencia y ponerla endpoint
a endpoint se descartó por el riesgo de olvidarla en alguno.

## Reglas
Sin comentarios `#`. No toca tests ni docs. No hace commit ni push. No toca
`docs/ai-log.md`.

## Verificación
- `ruff check app/routers/router_user.py app/main.py`.
- `pytest tests/test_users.py tests/test_auth.py tests/test_permissions.py` (con
  `DATABASE_URL=sqlite:///...`).
- Prueba rápida con `TestClient` (script en el scratchpad, no en `tests/`) con un
  `customer`, y comprobación de `/openapi.json`.

## Resultado
Entregado y aceptado sin cambios: 114 passed. Un `customer` obtiene 200 / 204, sin token
401, contraseña actual mala 403 `invalid_current_password`, y el 204 sale con cuerpo vacío.
