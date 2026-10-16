# Agente Especialista — Reglas de negocio · HU-33

## Rol
Eres el especialista en los servicios de HU-33: todas las reglas y transacciones. Paso 4:
empiezas cuando el líder ha aceptado a `agent-email`.

## Antes de empezar
1. Lee `AGENTS.md`.
2. Lee `specs/ontology.md` (R-01, R-02, R-04, R-09, R-11, R-13) y R-15 en la spec.
3. Lee `specs/HU-33-verificacion-email.md` completa, sobre todo "Reglas" y las
   decisiones A–Q.
4. Lee `docs/agents/HU-33/lead.md`, "Parámetros compartidos".
5. Lee `password_token_service.py`, `user_service.py` y `social_auth_service.py` y
   `app/scripts/create_admin.py`.

## Archivos exclusivos
`app/services/email_verification_service.py` (nuevo), `app/services/password_token_service.py`,
`app/services/user_service.py`, `app/services/social_auth_service.py`,
`app/scripts/create_admin.py`.

## Tareas
1. Las variables de configuración ya las añadió `agent-model` en `app/config.py`.
2. `email_verification_service.py`:
   - `issue_verification_token(db, user)` → valor en claro;
   - `verify_email(db, data)`, con los errores de la decisión L;
   - `resend_verification(db, email)` → el email a enviar o `None` (decisiones I, J, M).
3. `password_token_service.py` (código de Anna):
   - usa el helper de `app/core/one_time_tokens.py`;
   - añade `forgot_password(db, email)` → el email a enviar o `None` (decisiones F, G, I,
     M, N). La caducidad es `PASSWORD_RESET_EXPIRE_HOURS`;
   - `set_password` marca además `email_verified = true` (decisión C);
   - el comportamiento de HU-52 no cambia en nada más.
4. `user_service.py`:
   - `authenticate`/login: **no se toca** (decisión A);
   - `create_user` → `email_verified=True`;
   - `register_user` → `false`, y devuelve también el token para el email (D);
   - `update_profile`: si el email cambia, `false`, invalida los tokens pendientes y
     devuelve el token nuevo (E).
5. `social_auth_service.py`: cuenta nueva → `true` (C); al vincular una cuenta existente →
   `true` (P1). No cambies nada más del login social.
6. `create_admin.py`: `email_verified = true`, también al promover una cuenta existente (P2).
7. El tiempo de espera es silencioso (sin `429`) y se calcula con `get_latest_for_user`.
8. Logs: `info`/`warning` con `user_id` y `code`. Nunca el token, el enlace, el email
   consultado en `resend`/`forgot` ni la contraseña.

## Handoff
- `ruff check .` limpio.
- `pytest` entero en verde, sin tocar ningún test.
- Informe al líder: firmas de las funciones nuevas y qué devuelve cada una al router.

## Prohibiciones
- No toques routers, schemas, modelos, repositorios ni tests.
- No lances `HTTPException` nuevos: usa las clases de `app/core/exceptions.py` y
  `TokenGoneError`.
- No envíes emails desde el servicio: devuelve los datos y el router los encola.
- Sin comentarios `#`.
