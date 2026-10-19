# Agente Especialista — Endpoints y schemas · HU-33

## Rol
Eres el especialista en la capa HTTP de HU-33: routers, schemas y Swagger. Paso 5:
empiezas cuando el líder ha aceptado a `agent-service`.

## Antes de empezar
1. Lee `AGENTS.md` (convenciones: `summary`, `tags`, ejemplos, `{detail, code}`).
2. Lee `specs/ontology.md` (R-02, R-09) y R-15 en la spec.
3. Lee `specs/HU-33-verificacion-email.md`, tabla "Endpoints".
4. Lee `docs/agents/HU-33/lead.md`: códigos, cuerpo del `202`.
5. Lee como referencia `app/routers/router_password.py` (HU-52): `_errors`,
   `BackgroundTasks`, `Response` 204.

## Archivos exclusivos
`app/routers/router_email_verification.py` (nuevo), `app/routers/router_password.py`,
`app/routers/auth.py`, `app/routers/router_user.py`,
`app/schemas/schema_email_verification.py` (nuevo), `app/schemas/schema_password_token.py`,
`app/schemas/schema_user.py`, `app/main.py`.

## Tareas
1. Schemas de entrada (`extra="forbid"`, con ejemplos):
   - `EmailVerificationRequest {token}`, `ResendVerificationRequest {email}`;
   - `ForgotPasswordRequest {email}` en `schema_password_token.py`.
   Schema de salida `EmailDispatchOut {detail}` para el `202`. Añade `email_verified` a
   `UserOut`. Nunca `token_hash` ni `password_hash`.
2. `router_email_verification.py` (prefijo `/auth`, tag `auth`):
   `POST /verify-email` (204) y `POST /resend-verification` (202).
3. `router_password.py`: `POST /auth/forgot-password` (202). No cambies `invite` ni
   `set-password`.
4. `auth.py`:
   - `register` encola el email de verificación;
   - `login` **no se toca** (decisión A).
5. `router_user.py` (`PATCH /users/me`): si el servicio devuelve un token, encola el email
   a la dirección nueva.
6. `main.py`: registra el router nuevo (`include_router`). El import del modelo ya lo añadió
   `agent-model`.
7. Cada endpoint: `summary`, tag, `responses` con `ErrorResponse` para cada 4xx, y el
   email con `background_tasks.add_task(send_email, …)`.

## Handoff
- `ruff check .` limpio; `/docs` muestra los tres endpoints nuevos con ejemplos.
- `pytest` entero en verde, sin tocar ningún test.
- Informe al líder: rutas y códigos de los endpoints nuevos, y confirmación de que
  `register`, `set-password` y `PATCH /users/me` responden igual que antes (solo
  `UserOut` gana `email_verified`).

## Prohibiciones
- Sin reglas de negocio en los routers: solo llamar al servicio y encolar el email.
- No toques servicios, repositorios, modelos ni tests.
- No crees `POST /auth/reset-password` (decisión F). Sin comentarios `#`.
