# HU-26 · Swagger y auth

> Issue: #69 · Prioridad Must · Escribe: Rita · Revisa: la primera persona que la vea ·
> Aprueba: quien revisa (acuerdo del 14/10). Vocabulario: `specs/ontology.md`. Usa
> `specs/HU-TEMPLATE.md`.

## Problem Statement
La issue dice: "Como equipo de otra app quiero Swagger con tags, ejemplos, respuestas de
error y Authorize en auth y users para integrarme sin leer el código". No trae criterios de
aceptación. Auditado el `/openapi.json` de `dev` (commit `d8302f1`) en los 13 endpoints de
`/auth` y `/users`:

- **Authorize**: el botón existe (esquema `OAuth2PasswordBearer`, `tokenUrl=/auth/login`),
  pero nada explica cómo usarlo.
- **Tags**: `auth` y `users` existen sin descripción. No hay `openapi_tags` ni descripción
  general de la API.
- **Respuesta de login**: `POST /auth/login` y `POST /auth/social/{provider}` devuelven
  `{access_token, token_type}`, pero Swagger muestra la respuesta `{}` (sin `response_model`).
- **422 mal documentado**: Swagger declara el `HTTPValidationError` de FastAPI
  (`{"detail": [...]}`), pero el cuerpo real es `{"detail", "code", "errors"}`
  (`validation_error_handler`).
- **Errores sin declarar**: solo `/users/me` y `/users/me/password` declaran errores. Los
  otros 11 endpoints no declaran 401, 403, 404 ni 409.
- **Ejemplos**: `UserRegister`, `UserCreate`, `UserUpdate`, `SocialLoginRequest` y `UserOut`
  no tienen ejemplo. Los parámetros `provider` y `user_id` no tienen descripción.
- **Descripciones y roles**: 6 endpoints de `/users` no tienen `description`, y ninguno
  indica qué rol puede llamarlo.

## Solution
Completar la documentación OpenAPI de `/auth` y `/users` sin cambiar el comportamiento:
tags con descripción, descripción general de la API con los pasos para autenticarse,
respuesta de login tipada, errores por endpoint con su cuerpo real, ejemplos de petición y
respuesta, y el rol permitido en cada endpoint. Un test sobre `/openapi.json` impide que un
endpoint nuevo de `/auth` o `/users` llegue sin esa documentación.

## User Stories
1. Como equipo de otra app, quiero ver en Swagger una descripción de cada grupo (`auth`,
   `users`), para ubicarme sin leer el código.
2. Como equipo de otra app, quiero pulsar Authorize, iniciar sesión con email y contraseña y
   que el token se añada solo a las peticiones, para probar los endpoints protegidos.
3. Como equipo de otra app, quiero ver qué devuelve el login (`access_token`, `token_type`),
   para saber qué guardar.
4. Como equipo de otra app, quiero ejemplos de petición y de respuesta en registro,
   creación y edición de usuarios, para copiarlos.
5. Como equipo de otra app, quiero ver por endpoint qué errores puede devolver, con su
   `code` y su cuerpo real, para manejarlos en mi cliente.
6. Como equipo de otra app, quiero saber qué rol puede llamar a cada endpoint, para no
   probar con el rol equivocado.
7. Como equipo, quiero que un test falle si alguien añade un endpoint de `auth` o `users`
   sin esta documentación, para que no se vuelva a desfasar.

## Implementation Decisions
- **Alcance**: solo `/auth/*` y `/users/*`, incluidos `/users/me` y `/users/me/password`
  (lo dice la issue). Los demás routers quedan fuera.
- **Solo documentación**: sin cambios de modelo ni migración de Alembic, y sin cambios de
  rutas, códigos HTTP, mensajes `detail` ni `code`. Lo único que cambia en runtime es
  `/openapi.json`. `response_model=TokenOut` devuelve las mismas dos claves que hoy.
- **Módulo nuevo `app/core/openapi.py`** (no toca código de nadie): `ValidationErrorResponse`
  (hereda de `ErrorResponse` y añade `errors: list[dict]`, con ejemplo) y un helper
  `error_responses(...)` que devuelve el dict `responses` de FastAPI con
  `model=ErrorResponse` (y `ValidationErrorResponse` para el 422) y una descripción en
  español por código de estado.
- **`TokenOut`** (`access_token`, `token_type`, con ejemplo) en `schemas/schema_auth.py`,
  usado como `response_model` en `POST /auth/login` y `POST /auth/social/{provider}`.
- **Authorize**: se mantiene `OAuth2PasswordBearer(tokenUrl="/auth/login")` en
  `permissions.py`, sin cambios. Se explica en la descripción general y en el `description`
  de `POST /auth/login`: pulsar Authorize, `username` = email, `password`, y dejar vacíos
  `client_id` y `client_secret`.
- **Tags y descripción general** en `main.py`: `FastAPI(description=...)` con los 3 pasos
  para autenticarse (registrar, login o Authorize, llamar), el formato de error
  `{"detail", "code"}` y la lista de roles; `openapi_tags` con la descripción de `auth` y
  `users`.
- **Ejemplos**: `json_schema_extra={"examples": [...]}` en `UserRegister`, `UserCreate`,
  `UserUpdate` y `SocialLoginRequest`, y de respuesta en `UserOut`, con el patrón de
  `UserProfileUpdate`. `Path(description=..., examples=[...])` para `provider` y `user_id`.
- **Roles**: cada `description` de `/users/*` termina con "Rol: admin."; `/users/me*` y
  `/auth/me` con "Cualquier usuario autenticado."; `register`, `login` y `social` con
  "Público."
- **Errores por endpoint** (`code` tal como responde hoy la API; los 404, 409 y 403 de
  `user_service` usan los genéricos `not_found`, `conflict` y `forbidden`):

| Endpoint | Éxito | Errores a declarar |
|---|---|---|
| `POST /auth/register` | 201 `UserOut` | 409 `conflict`, 422 `validation_error` |
| `POST /auth/login` | 200 `TokenOut` | 401 `unauthorized`, 422 `validation_error` |
| `POST /auth/social/{provider}` | 200 `TokenOut` | 401 (`invalid_code`, `email_not_verified`, `inactive_account`), 422 (`redirect_uri_not_allowed`, `validation_error`), 502 `provider_unavailable`, 503 `provider_not_configured` |
| `GET /auth/me` | 200 `UserOut` | 401 `unauthorized` |
| `POST /users/` | 201 `UserOut` | 401, 403, 409, 422 |
| `GET /users/` | 200 `Page[UserOut]` | 401, 403, 422 |
| `GET /users/{user_id}` | 200 `UserOut` | 401, 403, 404, 422 |
| `PUT /users/{user_id}` | 200 `UserOut` | 401, 403, 404, 409, 422 |
| `PATCH /users/{user_id}/deactivate` | 200 `UserOut` | 401, 403 (no es admin, o es uno mismo), 404, 422 |
| `DELETE /users/{user_id}` | 200 `UserOut` | 401, 403 (no es admin, o es uno mismo), 404, 422 |
| `POST /users/{user_id}/restore` | 200 `UserOut` | 401, 403, 404, 409 (no está borrado), 422 |
| `PATCH /users/me` | 200 `UserOut` | los de HU-25: 401, 409, 422 |
| `POST /users/me/password` | 204 | los de HU-25: 400, 401, 403, 422 |

- **Capas afectadas**: `routers/auth.py`, `routers/router_user.py`, `schemas/` y
  `core/openapi.py`, más dos argumentos en `main.py`. Sin tocar services ni repositories.
- **Idioma**: el texto de Swagger va en español (es documentación); los identificadores,
  en inglés. Los `detail` de runtime siguen en inglés.
- **Documentación**: `docs/api.md` gana una sección corta sobre cómo usar Authorize y el
  formato de error, con enlace a `/docs`.

## Testing Decisions
- Nuevo `tests/test_openapi.py` sobre `/openapi.json` (no necesita datos), parametrizado
  por cada operación de `/auth` y `/users`:
  - tiene `tags`, `summary` y `description`;
  - los protegidos declaran `security` y la respuesta 401; los de `/users` salvo `/users/me*`
    declaran también 403;
  - cada respuesta 4xx o 5xx referencia `ErrorResponse` o `ValidationErrorResponse`, nunca
    `HTTPValidationError`;
  - cada parámetro tiene `description`;
  - los cuerpos JSON tienen ejemplo;
  - login y social devuelven `TokenOut` en el 200;
  - el esquema de seguridad es `OAuth2PasswordBearer` con `tokenUrl` `/auth/login`;
  - `auth` y `users` tienen descripción de tag.
- Test de contrato: un `POST /auth/register` sin cuerpo devuelve un 422 cuyo JSON valida
  contra `ValidationErrorResponse`, para que la documentación no se desvíe del cuerpo real.
- Los tests existentes (`test_auth.py`, `test_users.py`, `test_profile.py`,
  `test_social_login.py`, `test_errors.py`) pasan sin tocarlos: es la prueba de que nada
  cambia en runtime.
- No se prueba el render de Swagger UI. La comprobación de Authorize se hace a mano en
  `/docs` en local y se anota en la PR.

## Criterios de aceptación
- [ ] `/docs` muestra los tags `auth` y `users` con descripción, y la API tiene una
  descripción general con los pasos para autenticarse y el formato de error `{"detail", "code"}`.
- [ ] En `/docs`, **Authorize** con el email y la contraseña de un usuario real permite
  llamar a `GET /auth/me` desde Swagger sin copiar el token a mano (comprobado a mano en
  local; el esquema `OAuth2PasswordBearer` con `tokenUrl=/auth/login` está cubierto por test).
- [ ] Los 13 endpoints de `/auth` y `/users` tienen `tags`, `summary` y `description`, y la
  descripción indica el rol permitido.
- [ ] `POST /auth/login` y `POST /auth/social/{provider}` documentan el 200 como `TokenOut`
  (`access_token`, `token_type`) y el JSON real no cambia.
- [ ] Cada endpoint declara todos los errores de la tabla, con `ErrorResponse` (`detail`,
  `code`) y una descripción que dice cuándo ocurre y con qué `code`.
- [ ] El 422 de los endpoints de `/auth` y de `/users` (salvo `/users/me*`) se documenta con
  `ValidationErrorResponse` (`detail`, `code`, `errors`), igual que el cuerpo real. Ningún
  endpoint de `/auth` o `/users` referencia `HTTPValidationError`.
- [ ] Los cuerpos de `POST /auth/register`, `POST /auth/social/{provider}`, `POST /users/`,
  `PUT /users/{user_id}`, `PATCH /users/me` y `POST /users/me/password` tienen ejemplo, y
  `UserOut` y `TokenOut` tienen ejemplo de respuesta.
- [ ] Todos los parámetros de ruta y de query de `/auth` y `/users` tienen descripción;
  `provider` y `user_id` tienen además ejemplo.
- [ ] `tests/test_openapi.py` comprueba todo lo anterior y falla si se añade un endpoint de
  `/auth` o `/users` sin esa documentación.
- [ ] Ninguna ruta, código HTTP ni cuerpo cambia: los tests existentes pasan sin modificarse.
- [ ] `docs/api.md` explica cómo usar Authorize y enlaza a `/docs`.
- [ ] Lint limpio, CI en verde con la cobertura mínima, entrada en `docs/ai-log.md` y PR
  `[HU-26] ...` de menos de 400 líneas (si no cabe, se divide en pasos).

## Out of Scope
- Swagger del resto de routers (categorías, platos, pedidos, facturas, exportaciones,
  estadísticas, mesas, reservas, WebSocket). Sus tags seguirán sin descripción.
- Cambiar los mensajes `detail` o poner `code` propios a los 403, 404 y 409 de `users`: sería
  un cambio de contrato (`breaking-api`) para el frontend.
- Scopes OAuth2 por rol, refresh tokens y logout (otras HU de auth).
- `persistAuthorization` y otros ajustes de Swagger UI: guardaría el token en el navegador
  de quien use la documentación de producción.
- Alinear el 422 de `/users/me` y `/users/me/password` (HU-25, de Levi) con
  `ValidationErrorResponse`, sustituyendo su `_me_errors` por el helper compartido con las
  mismas descripciones. Aplazado a un último paso aparte, que solo se hace si Levi está de
  acuerdo (consultado el 15/10, pendiente de respuesta). Si no, esos dos endpoints conservan
  su `_me_errors` y su 422 como `ErrorResponse`, y la HU se cierra sin tocar su código.

## Preguntas abiertas
Ninguna.

## Decisiones de la sesión
Sesión de 15/10/2026 (Rita, con Claude). Decidido al partir de la issue:
- **Alcance solo `auth` y `users`** → es lo que pide la issue. Rechazado: documentar todos
  los routers en esta HU (PR enorme y fuera del texto de la historia).
- **Solo documentación, sin cambios de comportamiento** → la historia pide poder integrarse
  sin leer el código, no cambiar el contrato. Rechazado: unificar los `code` de `users`
  (rompe al frontend).
- **422 documentado como `ValidationErrorResponse`** → refleja el cuerpo real. Rechazado:
  dejar el `HTTPValidationError` de FastAPI (describe un cuerpo que la API no devuelve).
- **Módulo compartido `app/core/openapi.py`** (decidido por Rita) → un solo sitio para el
  modelo del 422 y las descripciones de error, reutilizable por los otros routers más
  adelante. Rechazado: dicts `responses` locales en cada router (11 endpoints repetidos).
- **Tocar `main.py` para `description` y `openapi_tags`** (decidido por Rita) → la
  descripción general es donde se explica cómo autenticarse. Son dos argumentos de
  `FastAPI(...)`; se avisa en la PR.
- **Prioridad Must; revisa la primera persona que la vea** (decidido por Rita) → es el
  acuerdo del 14/10: quien revisa aprueba y hace el squash.
- **El cambio en el código de Levi (`_me_errors`) se aplaza a un último paso y queda
  condicionado a su respuesta** (Rita le escribió el 15/10) → no bloquea el resto de la HU y
  no se toca código ajeno sin aviso (`AGENTS.md`). Rechazado: esperar su respuesta antes de
  empezar.
