# HU-25 · Cambio de contraseña y edición del propio perfil

> Issue: #68 · Prioridad Must · Nivel Medio · Escribe: Levi · Revisa: Ana, Carla, Manon, Rita·
> Aprueba: Levi (PO). Vocabulario: `specs/ontology.md`. Usa `specs/HU-TEMPLATE.md`.

## Problem Statement
Hoy un usuario solo puede ver sus datos (`GET /auth/me`). Para cambiar su nombre, email,
teléfono o contraseña depende de un admin (`PUT /users/{user_id}`), porque todo el router
`/users` exige rol `admin`. La issue pide que cualquier usuario autenticado mantenga sus
propios datos al día.

## Solution
Dos endpoints para el propio usuario autenticado, de cualquier rol, bajo `/users/me`:
`PATCH /users/me` para editar el perfil y `POST /users/me/password` para cambiar la
contraseña. Van en un `APIRouter` aparte (`me_router`) dentro de `router_user.py`, que
solo exige `CurrentUser`, para no heredar la dependencia de admin del router de `/users`.

## User Stories
1. Como usuario autenticado (cualquier rol), quiero editar mi nombre, email y teléfono,
   para mantener mis datos al día.
2. Como usuario autenticado, quiero cambiar mi contraseña indicando la actual, para
   proteger mi cuenta.
3. Como admin, quiero que nadie pueda cambiarse el rol ni reactivarse desde su perfil,
   para que R-03 y R-04 sigan valiendo.

## Implementation Decisions
- **Modelo**: sin cambios. `name`, `email`, `phone`, `password_hash` y `updated_by` ya
  existen. No hay migración 0007.
- **Schemas** (`app/schemas/schema_user.py`), separados de entrada/salida:
  - `UserProfileUpdate` (entrada, `extra="forbid"`): `name: str | None` (si llega,
    `min_length=1`, `max_length=100`, no admite `null`), `email: EmailStr | None` (no
    admite `null`), `phone: str | None` (`max_length=20`; `null` lo borra). Cualquier
    otro campo (`role`, `is_active`, `password`…) → 422 `validation_error`.
  - `PasswordChange` (entrada, `extra="forbid"`): `current_password: str` (`min_length=1`),
    `new_password: str` (`min_length=MIN_PASSWORD_LENGTH`, R-02).
  - Salida: `UserOut` existente (no incluye `password_hash`).
- **Endpoints** (`me_router`, prefijo `/users`, tag `users`, registrado en `main.py`
  antes que `router_user.router`):

  | Método | Ruta | Roles | Éxito | Errores |
  |---|---|---|---|---|
  | `PATCH` | `/users/me` | todos (autenticado) | `200` `UserOut` | 401, 409, 422 |
  | `POST` | `/users/me/password` | todos (autenticado) | `204` sin cuerpo | 400, 401, 403, 422 |

- **Reglas** (`app/services/user_service.py`, funciones `update_profile(db, user, data)` y
  `change_password(db, user, data)`):
  - Perfil: solo se aplican los campos enviados (`exclude_unset`). El email se normaliza
    (`normalize_email`); si pertenece a otro usuario (incluidos borrados) → 409
    `conflict`, `"Email already registered"` (R-01). Mismo email que el actual → OK.
  - Contraseña:
    1. `password_hash` nulo (cuenta solo social) → 400 `password_not_set`.
    2. `current_password` no coincide → 403 `invalid_current_password`. No 401: el token
       es válido y un 401 haría creer al frontend que la sesión caducó.
    3. `new_password` igual a la actual → 422 `same_password`.
    4. Se guarda con `hash_password` (bcrypt). Nunca se devuelve ni se loguea.
  - Ambas registran `updated_by = user.id` (R-11); `updated_at` lo pone el modelo.
  - Errores de dominio con las clases de `app/core/exceptions.py` (`ConflictError`,
    `AppError`, `ForbiddenError`, `UnprocessableError`) y su `code`.
  - Log `info` de cada cambio con el `user_id` y los nombres de campo cambiados, nunca
    valores de contraseña.
- **Capas**: router (solo HTTP) → service (reglas) → `user_repository.save` /
  `get_by_email` (sin consultas nuevas).
- **Swagger**: `summary`, tag `users`, ejemplos en los schemas y `responses` con
  `ErrorResponse` para cada 4xx.

## Testing Decisions
Archivo `tests/test_users.py` (tests nuevos al final, sin tocar los existentes):
- Perfil: editar `name`/`phone` (200), un `customer` y un `waiter` pueden (no solo
  admin), email se guarda en minúsculas, email de otro → 409, mismo email propio → 200,
  `role`/`is_active` en el body → 422, `name` vacío → 422, sin token → 401,
  `updated_by` = propio id, la respuesta no tiene `password_hash`.
- Contraseña: cambio correcto (204) y login con la nueva funciona y con la vieja no,
  actual incorrecta → 403 `invalid_current_password`, nueva < 8 → 422, nueva = actual →
  422 `same_password`, usuario sin contraseña → 400 `password_not_set`, sin token → 401.
- Todos los errores con forma `{"detail", "code"}`.

## Criterios de aceptación
- [ ] Cualquier usuario autenticado edita su `name`, `email` y `phone` con `PATCH /users/me`.
- [ ] No puede cambiar su `role` ni `is_active` desde ese endpoint (422).
- [ ] Email duplicado → 409; se guarda en minúsculas (R-01).
- [ ] `POST /users/me/password` exige la contraseña actual y guarda la nueva con bcrypt (R-02).
- [ ] `password_hash` no aparece en ninguna respuesta ni log.
- [ ] Errores con `{detail, code}` y documentados en Swagger y `docs/api.md`.
- [ ] `ruff check .` limpio y `pytest` en verde.

## Out of Scope
- Invalidar otras sesiones al cambiar la contraseña: los tokens aún no tienen `jti` ni
  refresh (R-06/R-07); queda para la HU de refresh/logout.
- Fijar contraseña a una cuenta solo social: lo cubrirá la HU de recuperación de contraseña.
- Reverificar el email tras cambiarlo: no existe `email_verified` en el modelo todavía.
- `GET /users/me`: ya existe `GET /auth/me`.
- Rate limiting del cambio de contraseña (R-10 es solo para login).
- Colección Bruno: no existe aún en `dev`.

## Preguntas abiertas
(vacío: spec lista para implementar)

## Decisiones de la sesión
### Ubicación de los endpoints
- **Decisión**: `PATCH /users/me` y `POST /users/me/password` en un `me_router` aparte.
- **Por qué**: convención del repo (`/users/*` para usuarios, `/auth/*` para
  login/registro); el router `/users` es solo admin a nivel de router.
- **Alternativas rechazadas**: bajo `/auth/*`; quitar la dependencia de admin del router y
  ponerla endpoint a endpoint (riesgo de olvidarla en uno).

### Contraseña actual incorrecta → 403
- **Decisión**: 403 `invalid_current_password`.
- **Por qué**: el token es válido; un 401 se confundiría con sesión caducada.
- **Alternativas rechazadas**: 401; 400.

### Campos no permitidos en el perfil → 422
- **Decisión**: `extra="forbid"` en `UserProfileUpdate` y `PasswordChange`.
- **Por qué**: que el cliente sepa que `role`/`is_active` no se pueden cambiar.
- **Alternativas rechazadas**: ignorarlos en silencio como `/auth/register` con `role`.

### Cuenta sin contraseña → 400 `password_not_set`
- **Decisión**: rechazar el cambio si `password_hash` es nulo.
- **Por qué**: sin contraseña actual no se puede verificar al usuario; fijarla es cosa de
  la HU de recuperación.
- **Alternativas rechazadas**: permitir fijarla sin `current_password`.

### Nueva contraseña igual a la actual → 422 `same_password`
- **Decisión**: rechazarla.
- **Por qué**: un "cambio" que no cambia nada suele ser un error del usuario.
- **Alternativas rechazadas**: aceptarla en silencio.
