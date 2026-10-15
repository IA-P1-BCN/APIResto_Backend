# agent-service · HU-25

> Equipo: [líder](lead.md) · Depende de: [`agent-schema`](agent-schema.md) · Bloquea a:
> [`agent-router`](agent-router.md)

## Tarea
Implementar las reglas de negocio de la HU-25 (sección "Reglas" de la spec).

## Archivos
Solo `app/services/user_service.py`. Las funciones existentes no se cambian.

## Lecturas
`AGENTS.md` → `specs/ontology.md` → la spec de HU-25 → `user_service.py`,
`user_repository.py`, `app/core/exceptions.py`, `app/core/security.py`, los schemas nuevos
y `social_auth_service.py` como precedente de errores con `code` y de logs.

## Contrato
`update_profile(db, user, data: UserProfileUpdate) -> User`
- Aplica solo los campos enviados (`exclude_unset`).
- `email`: `normalize_email`; si pertenece a otro usuario (también borrado) →
  `ConflictError("Email already registered")`, 409 `conflict` (R-01).
- `updated_by = user.id` (R-11) y guarda con `user_repository.save`.

`change_password(db, user, data: PasswordChange) -> None`, en este orden:
1. `password_hash` nulo → `AppError`, 400 `password_not_set`.
2. Contraseña actual incorrecta → `ForbiddenError`, 403 `invalid_current_password`.
3. Nueva igual a la actual → `UnprocessableError`, 422 `same_password`.
4. `hash_password` (bcrypt), `updated_by = user.id` y guardar.

Logs: solo `user_id`, nombres de campos y `code`. Nunca contraseñas, hashes ni valores.

## Reglas
Sin comentarios `#`. Sin dependencias nuevas. No hace commit ni push. No toca
`docs/ai-log.md`.

## Verificación
- `ruff check app/services/user_service.py`.
- Prueba rápida con SQLite en memoria de las 4 ramas de `change_password` y del 409.
- `pytest tests/test_users.py tests/test_auth.py` (con `DATABASE_URL=sqlite:///...`).

## Resultado
Entregado y aceptado. Añadido aceptado por el líder: el 409 descarta que la cuenta
encontrada sea la propia (`existing.id != user.id`), porque `get_by_email` ignora
mayúsculas y una cuenta antigua guardada con mayúsculas recibiría 409 con su propio email.
