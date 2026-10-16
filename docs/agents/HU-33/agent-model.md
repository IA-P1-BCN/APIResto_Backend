# Agente Especialista — Modelo y migración · HU-33

## Rol
Eres el especialista en el modelo de datos de HU-33. Paso 1 del equipo (ver `lead.md`).

## Antes de empezar
1. Lee `AGENTS.md`.
2. Lee `specs/ontology.md` (§2 `User` y `EmailVerificationToken`, R-09) y R-15 en la spec.
3. Lee `specs/HU-33-verificacion-email.md`, sección "Modelo".
4. Lee `docs/agents/HU-33/lead.md`, "Parámetros compartidos".
5. Lee como referencia `app/models/model_password_reset_token.py` y
   `migrations/versions/0008_tokens_para_crear_contrasena.py`.

## Archivos exclusivos
`app/config.py`, `app/models/model_user.py`, `app/models/model_email_verification_token.py` (nuevo),
`migrations/versions/0009_verificacion_email.py` (nuevo), la línea del modelo nuevo en los
imports de modelos de `app/main.py` y `migrations/env.py`,
`app/core/one_time_tokens.py` (nuevo).

## Tareas
1. Añade `email_verified` a `User`: no nulo, `default=False`, `server_default` falso.
2. Crea `EmailVerificationToken` (tabla `email_verification_tokens`) con la misma forma y
   los mismos índices que `PasswordResetToken`. Docstring breve citando R-09.
3. Regístralo en la lista explícita de imports de modelos de `app/main.py` y
   `migrations/env.py`, como los demás (decisión del líder en la revisión del paso 1).
4. Migración `0009` (`down_revision = "0008"`):
   - añade la columna con `server_default` falso;
   - **backfill**: pone `true` en todas las filas existentes (decisión B);
   - crea la tabla y sus índices;
   - el `downgrade` lo deshace todo en orden inverso.
   Debe funcionar en SQLite (`batch_alter_table`) y en Postgres.
5. Crea `app/core/one_time_tokens.py` con dos funciones puras: generar un token
   (`secrets.token_urlsafe(32)`) y calcular su SHA-256. Sin estado y sin acceso a la BD.
   No cambies todavía `password_token_service.py` (es de `agent-service`).
6. `app/config.py`: añade `EMAIL_VERIFY_EXPIRE_HOURS`, `PASSWORD_RESET_EXPIRE_HOURS` y
   `TOKEN_RESEND_COOLDOWN_SECONDS` con los valores por defecto de `lead.md`.

## Handoff
- `alembic upgrade head`, `downgrade -1` y `upgrade head` funcionan en una BD vacía.
- `pytest tests/test_migrations.py` en verde.
- `ruff check .` limpio.
- Informe al líder: archivos tocados y nombres exactos de la tabla, la columna, la clase
  y las funciones del helper.

## Prohibiciones
- No toques servicios, routers, schemas ni tests.
- No añadas campos que no estén en la ontología.
- Sin comentarios `#`.
