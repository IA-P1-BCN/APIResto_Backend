# agent-tests · HU-25

> Equipo: [líder](lead.md) · Depende de: [`agent-router`](agent-router.md) · En paralelo
> con: [`agent-docs`](agent-docs.md)

## Tarea
Escribir los tests de la HU-25 (sección "Testing Decisions" de la spec): caso feliz y todos
los 4xx de cada endpoint.

## Archivos
Solo `tests/test_users.py`, añadiendo al final. Los tests existentes no se tocan ni se
debilitan.

## Lecturas
`AGENTS.md` → `specs/ontology.md` → la spec de HU-25 → `tests/conftest.py` (fixtures
`client`, `db`, `make_user`, `auth_headers`; contraseña `secreto123`) →
`tests/test_users.py` → el código ya terminado (router, servicio y schemas).

## Casos mínimos
`PATCH /users/me`
- `name` y `phone` → 200, sin `password_hash`.
- Funciona para `customer`, `waiter` y `admin`.
- Email en mayúsculas/espacios → minúsculas; email de otro → 409 `conflict`; el propio → 200.
- `role` / `is_active` en el body → 422 y no cambian.
- `name: ""` o `null` → 422; `phone: null` lo borra.
- Sin token → 401; `updated_by` = propio id.

`POST /users/me/password`
- Cambio correcto → 204 vacío; login con la nueva funciona y con la vieja da 401.
- Actual incorrecta → 403 `invalid_current_password`.
- Nueva < 8 → 422 `validation_error`; igual a la actual → 422 `same_password`.
- Sin contraseña (`password_hash=None`) → 400 `password_not_set`.
- Campo extra → 422; sin token → 401.

## Reglas
Si un test falla porque el código no cumple la spec, no se debilita: se reporta al líder.
Sin comentarios `#`. No hace commit ni push. No toca `docs/ai-log.md`.

## Verificación
Con `DATABASE_URL=sqlite:///./test_hu25.db` (y borrar el `.db` al terminar):
`ruff check tests/test_users.py`, `pytest tests/test_users.py` y `pytest` completo.

## Resultado
Entregado y aceptado: 33 tests nuevos (20 de perfil, 13 de contraseña), además de dos casos
extra: el email de un usuario borrado sigue reservado y solo cambian los campos enviados.
`test_users.py`: 62 passed; suite completa: 599 passed. El código cumplió la spec en todos
los casos.
