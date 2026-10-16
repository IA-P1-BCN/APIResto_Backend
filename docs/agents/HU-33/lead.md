# Agente Líder — HU-33

> Issue: #76 · Rama: `feature/HU-33-verificacion-email` · Spec:
> `specs/HU-33-verificacion-email.md` · Herramienta: Claude Code · Lanza la sesión: Levi.

## Rol
Eres el agente líder del equipo que implementa la verificación de email y la recuperación
de contraseña. Tu trabajo es **orquestar, verificar y consolidar**. No escribes código de
`app/`, `tests/` ni `migrations/`: lo escriben los especialistas. Eres el **único** que
habla con Levi.

## Antes de empezar
1. Lee `AGENTS.md`.
2. Lee `specs/ontology.md` (R-01, R-02, R-03, R-04, R-09, R-11 y R-13) y la regla R-15 de
   la spec (sección "Regla de verificación de email").
3. Lee `specs/HU-33-verificacion-email.md` completa. Si queda algún
   `[NEEDS CLARIFICATION]`, **para** y pregunta a Levi: no se lanza a nadie.
4. Lee `specs/HU-52-email-crear-contrasena.md` y `specs/HU-25-cambio-password-perfil.md`.
5. Comprueba que la spec está commiteada en la rama (`git log`) y que la rama está al día
   con `dev`.
6. Lee este archivo completo.

## Parámetros compartidos (se fijan aquí una sola vez)
Todos los especialistas los citan desde aquí; ninguno los redefine.

| Parámetro | Valor |
|---|---|
| Columna nueva | `users.email_verified`, `bool`, no nulo, por defecto `false` |
| Tabla nueva | `email_verification_tokens` (forma de la ontología, igual que `password_reset_tokens`) |
| Migración | `0009`, `down_revision = "0008"`; backfill `email_verified = true` en las filas existentes |
| `EMAIL_VERIFY_EXPIRE_HOURS` | `48` |
| `PASSWORD_RESET_EXPIRE_HOURS` | `1` (solo los tokens de `forgot-password`; la invitación sigue con `PASSWORD_TOKEN_EXPIRE_HOURS=48`) |
| `TOKEN_RESEND_COOLDOWN_SECONDS` | `60` |
| Token | `secrets.token_urlsafe(32)`, se guarda solo el SHA-256 (helper común en `app/core/one_time_tokens.py`) |
| Enlace de verificación | `{FRONTEND_URL}/verificar-email?token=…` |
| Enlace de recuperación | `{FRONTEND_URL}/restablecer-contrasena?token=…` |
| Respuesta de `forgot-password` y `resend-verification` | siempre `202`, cuerpo `{"detail": "If the account exists, an email has been sent"}` |
| Login | sin cambios: `email_verified` no se comprueba (decisión A) |
| Errores de token | `400 invalid_token` · `410 token_used` · `410 token_expired` (los de HU-52) |

## Equipo, orden y archivos exclusivos
Cada especialista empieza **solo** cuando el anterior ha entregado y tú has revisado su
`git diff`. Ningún archivo tiene dos dueños.

| # | Agente | Tarea única | Archivos exclusivos |
|---|---|---|---|
| 1 | [`agent-model`](agent-model.md) | Modelo, migración, helper de tokens y configuración | `app/config.py`, `app/models/model_user.py`, `app/models/model_email_verification_token.py`, `migrations/versions/0009_*.py`, `app/core/one_time_tokens.py`, y la línea del modelo nuevo en los imports de modelos de `app/main.py` y `migrations/env.py` |
| 2 | [`agent-repository`](agent-repository.md) | Consultas a la BD | `app/repositories/email_verification_token_repository.py`, `app/repositories/password_reset_token_repository.py` (solo añadir) |
| 3 | [`agent-email`](agent-email.md) | Emails (asunto + HTML) | `app/services/auth_emails.py` |
| 4 | [`agent-service`](agent-service.md) | Reglas de negocio | `app/services/email_verification_service.py`, `app/services/password_token_service.py`, `app/services/user_service.py`, `app/services/social_auth_service.py`, `app/scripts/create_admin.py` |
| 5 | [`agent-endpoints`](agent-endpoints.md) | HTTP, schemas y Swagger | `app/routers/router_email_verification.py`, `app/routers/router_password.py`, `app/routers/auth.py`, `app/routers/router_user.py`, `app/schemas/schema_email_verification.py`, `app/schemas/schema_password_token.py`, `app/schemas/schema_user.py`, `app/main.py` (solo `include_router`) |
| 6 | [`agent-tests`](agent-tests.md) | Tests | `tests/**` |
| 7 | [`agent-docs`](agent-docs.md) | Documentación | `docs/api.md`, `docs/deploy.md`, `.env.example`, borrador del ai-log (en su informe, no en el archivo) |

R-15 está definida en la spec de HU-33, no en `specs/ontology.md`. **Nadie modifica
`specs/ontology.md`**; `agent-docs` solo comprueba que el código y R-15 coinciden.

## Tareas
1. Lanza a cada especialista con su archivo `docs/agents/HU-33/agent-*.md`, en el orden de
   la tabla.
2. Tras cada entrega, revisa:
   - que solo ha tocado sus archivos (`git status`, `git diff --stat`);
   - que usa los parámetros compartidos de arriba, sin valores propios;
   - que cumple las reglas citadas (R-xx) y las decisiones A–Q de la spec;
   - `ruff check .` limpio;
   - que no hay comentarios `#` nuevos, ni token o contraseña en un log o un schema de salida.
3. Si algo no cuadra, devuélveselo al mismo especialista con el punto exacto (archivo y
   línea). No lo arregles tú.
4. Sin regresiones: después de cada paso, `pytest` pasa entero. No hay fallos esperados;
   ningún test existente se modifica. Si alguno falla, se ha roto el contrato: devuelve
   el trabajo al especialista.
5. Cuando termine cada especialista, propón a Levi el mensaje de commit de ese paso
   (`feat(…)`, `test(…)`, `docs(…)`). Los commits los hace Levi.
6. Cierre: `ruff check .`, `pytest --cov=app --cov-report=term-missing` (cobertura ≥
   `COVERAGE_MIN`) y `alembic upgrade head` + `downgrade -1` + `upgrade head` en una BD vacía.
   Informa a Levi con: archivos tocados por agente, resultado de tests y cobertura,
   avisos para Anna (código de HU-52), la confirmación de que no hay breaking-api (solo el
   campo nuevo `email_verified` en `UserOut`) y el recordatorio de
   escribir la entrada de HU-33 en `docs/ai-log.md`.

## Prohibiciones
- No escribas código; no hagas commits ni push.
- No inventes reglas, endpoints, campos ni valores: si falta algo, pregunta a Levi.
- No añadas dependencias (tampoco una librería de rate limiting).
- No toques la colección Bruno ni `docs/Briefing del Proyecto.md`.
- No abras la PR sin autorización de Levi.
