# Agente Especialista — Emails · HU-33

## Rol
Eres el especialista en el contenido de los emails de HU-33. Paso 3: empiezas cuando el
líder ha aceptado a `agent-repository`.

## Antes de empezar
1. Lee `AGENTS.md`.
2. Lee `specs/HU-33-verificacion-email.md`, sección "Emails" (decisión O).
3. Lee `docs/agents/HU-33/lead.md`: enlaces, variables de caducidad.
4. Lee como referencia `invitation_email` y `set_password_link` en
   `app/services/password_token_service.py`, y `app/services/notifications.py`.

## Archivos exclusivos
`app/services/auth_emails.py` (nuevo).

## Tareas
1. Dos funciones puras que devuelvan `(to, subject, html)`, como `invitation_email`:
   - email de verificación: asunto "Verifica tu email de APIResto", enlace
     `{FRONTEND_URL}/verificar-email?token=…` y `EMAIL_VERIFY_EXPIRE_HOURS`;
   - email de recuperación: asunto "Restablece tu contraseña de APIResto", enlace
     `{FRONTEND_URL}/restablecer-contrasena?token=…`, `PASSWORD_RESET_EXPIRE_HOURS` y
     "si no lo has pedido tú, ignora este email".
2. Escapa el nombre y el enlace con `html.escape`, como HU-52. Quita la barra final de
   `FRONTEND_URL`.
3. No envíes nada: el envío (`send_email` en `BackgroundTasks`) lo hacen los routers.

## Handoff
- `ruff check .` limpio.
- Informe al líder: nombres de las funciones y el HTML resultante con un token de ejemplo.

## Prohibiciones
- No toques `notifications.py`, `password_token_service.py` ni ningún otro archivo.
- Nunca registres el token ni el enlace en un log.
- Sin dependencias nuevas (nada de motores de plantillas). Sin comentarios `#`.
