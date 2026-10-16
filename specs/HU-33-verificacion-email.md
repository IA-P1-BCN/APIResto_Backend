# HU-33 · Verificación de email y recuperación de contraseña

> Issue: #76 · Prioridad Should (nivel avanzado del brief P3) · Escribe: Levi · Revisa:
> equipo · Aprueba: Levi (PO). Vocabulario: `specs/ontology.md` (R-01, R-02, R-04, R-09,
> R-11, R-13). Regla propia de esta HU: R-15 (sección "Regla de verificación de email").
> Usa `specs/HU-TEMPLATE.md`. Equipo de agentes: `docs/agents/HU-33/`.
> Sin breaking-api: ningún endpoint existente cambia su respuesta. `UserOut` gana un campo
> (`email_verified`).

## Problem Statement
Hoy nadie comprueba que el email de una cuenta pertenece a quien la usa. Además, quien
olvida su contraseña depende de un admin, porque no hay forma de pedir un enlace para
cambiarla. HU-52 ya creó `PasswordResetToken` y `POST /auth/set-password` para las
invitaciones, pero solo los usa el admin.

## Solution
- El `User` gana `email_verified`. El auto-registro nace sin verificar y recibe un email
  con un enlace de un solo uso; la página del frontend llama a `POST /auth/verify-email`.
  Se puede pedir otro enlace con `POST /auth/resend-verification`.
- La verificación es **informativa** (R-15): `email_verified` sale en `UserOut` y el login
  no cambia.
- "He olvidado mi contraseña": `POST /auth/forgot-password` envía un enlace con un
  `PasswordResetToken` y la contraseña se fija con el `POST /auth/set-password` de HU-52.
- Los dos endpoints que reciben un email responden siempre lo mismo y tienen un tiempo
  mínimo entre envíos, sin librerías nuevas.

## User Stories
1. Como cliente recién registrado, quiero recibir un email para confirmar mi dirección.
2. Como usuario sin verificar, quiero pedir otro enlace si el primero caducó o no me llegó.
3. Como usuario que ha olvidado su contraseña, quiero pedir un enlace por email y elegir
   una nueva, sin depender del restaurante.
4. Como usuario que cambia su email en el perfil, quiero confirmar la dirección nueva.
5. Como equipo, queremos que estos endpoints no revelen qué emails están registrados y no
   sirvan para inundar un buzón.
6. Como equipo, queremos que nada de lo que ya funciona cambie su respuesta.

## Regla de verificación de email (R-15)
`specs/ontology.md` no fija cómo funciona la verificación: en su §5 ("Pendientes") deja
expresamente la decisión ("¿bloquea el login?") a la spec de la HU que la implementa.
Esta es esa spec, así que la regla se define aquí y **la ontología no se modifica** en
este PR. Usa el vocabulario de la ontología (`User.email_verified`,
`EmailVerificationToken`, `PasswordResetToken`) y complementa a R-09 (tokens de un solo
uso) y R-13 (login social). El id R-15 es el siguiente libre tras R-14 y se cita así en el
código, los tests y la PR de esta HU.

| Id | Prio | Regla |
|---|---|---|
| R-15 | S | Verificación de email (HU-33), informativa: `email_verified` no impide iniciar sesión. Nace `false` en `POST /auth/register` y `true` en las cuentas creadas por un `admin`, por `create_admin` o por login social (nuevas o vinculadas); pasa a `true` al usar un `EmailVerificationToken` o al fijar la contraseña con un `PasswordResetToken`. Cambiar el propio email lo devuelve a `false` e invalida los `EmailVerificationToken` pendientes. Los endpoints que reciben un email para enviar un enlace (verificación, recuperación) responden igual exista o no la cuenta |

Con esta regla queda resuelto el pendiente de §5 sobre la verificación de email. Sigue
pendiente lo que allí se dice de los parámetros numéricos (caducidad del refresh, límite
del rate limiting) y de la recuperación de códigos 2FA, que fijará la spec de su HU.

## Implementation Decisions

### Modelo (migración `0009`)
- `users.email_verified`: `bool`, no nulo, por defecto `false` (ontología §2). La migración
  añade la columna y marca `true` todas las filas existentes (decisión B).
- Nueva entidad `EmailVerificationToken`, tabla `email_verification_tokens`, con la forma de
  la ontología: `id`, `user_id` (FK a `users`, `ON DELETE CASCADE`), `token_hash` (único),
  `expires_at`, `used_at` (nulo = sin usar), `created_at`. Igual que
  `password_reset_tokens`; se mantienen separadas para respetar el vocabulario.
- La generación del token (`secrets.token_urlsafe(32)`) y su SHA-256 se mueven de
  `password_token_service.py` a un helper común, `app/core/one_time_tokens.py`, que usan
  los dos servicios (decisión P). El comportamiento de HU-52 no cambia.

### Quién nace verificado (decisión C, R-15)
| Origen de la cuenta | `email_verified` |
|---|---|
| `POST /auth/register` | `false` y se envía el email de verificación |
| `POST /users/` (admin) | `true` |
| `POST /users/invite` (HU-52) | `false`; pasa a `true` al usar `POST /auth/set-password` |
| Login social, cuenta nueva (R-13) | `true` |
| Login social que vincula una cuenta existente | pasa a `true` (decisión P1) |
| `python -m app.scripts.create_admin` | `true`, también si promueve una cuenta existente (decisión P2) |
| Cuentas que ya existían antes de `0009` | `true` (backfill, decisión B) |

`POST /auth/set-password` marca `email_verified = true` con **cualquier**
`PasswordResetToken` (invitación o recuperación): los dos llegan por email, así que usarlo
demuestra que el buzón es del usuario. La tabla no distingue el origen del token.

### Endpoints
| Método | Ruta | Acceso | Éxito | Errores |
|---|---|---|---|---|
| `POST` | `/auth/verify-email` | público | `204` | 400 `invalid_token`, 410 `token_used` / `token_expired`, 422 |
| `POST` | `/auth/resend-verification` | público | `202` | 422 |
| `POST` | `/auth/forgot-password` | público | `202` | 422 |

Endpoints existentes. **No cambian su código de respuesta ni sus errores**:
- `POST /auth/login`: sin cambios (decisión A).
- `POST /auth/register`: mismo `201`; además encola el email de verificación.
- `PATCH /users/me`: mismo `200`; si cambia el email, `email_verified = false` y se encola
  el email (decisión E).
- `POST /auth/set-password`: mismo `204`; además marca `email_verified = true`.
- `UserOut` añade `email_verified` (campo nuevo, aditivo). Nunca sale `token_hash` ni
  `password_hash` (R-02).

Detalles:
- **Cuerpos de entrada** (`extra="forbid"`): `verify-email` → `{token}`;
  `resend-verification` y `forgot-password` → `{email}` (`EmailStr`).
- **Respuesta `202`**: siempre `{"detail": "If the account exists, an email has been sent"}`.
- **Ubicación** (decisión de Levi): `verify-email` y `resend-verification` en un router
  nuevo, `router_email_verification.py`; `forgot-password` en `router_password.py`, junto a
  `set-password` (código de Anna, hay que avisarla). Tag `auth`.

### Reglas
- **Login (decisión A, R-15)**: `email_verified` no se comprueba al iniciar sesión.
- **`verify-email` (R-09, decisión L)**: busca el token por su hash bloqueando la fila
  (como HU-52).
  - Desconocido, o usuario inactivo o borrado (R-04) → `400 invalid_token`.
  - Ya usado → `410 token_used`. Caducado → `410 token_expired`.
  - Si es válido: `email_verified = true`, `used_at` en ese token y en los demás tokens
    de verificación pendientes del usuario, y `updated_by = user.id` (R-11).
  - Si la cuenta ya estaba verificada y el token es válido: `204`, y el token se marca
    usado igualmente.
- **`resend-verification` (decisiones I, J, M)**: siempre `202` con el mismo cuerpo. Solo
  se envía si el email existe (R-01, comparado en minúsculas), la cuenta está activa y no
  borrada, no está verificada y no ha pasado el tiempo de espera. Si no, no se hace nada
  y solo queda un log sin el email.
- **`forgot-password` (decisiones F, G, I, M, N)**: siempre `202` con el mismo cuerpo.
  - Se envía si la cuenta existe, está activa y no borrada, y ha pasado el tiempo de
    espera. También a cuentas sin contraseña (solo social o invitadas): así fijan una.
  - El token es un `PasswordResetToken` que caduca a las `PASSWORD_RESET_EXPIRE_HOURS`.
  - La contraseña se fija con `POST /auth/set-password`, sin cambios en su contrato.
- **Tiempo de espera (decisión M)**: no se emite un token nuevo del mismo tipo si el último
  del usuario se creó hace menos de `TOKEN_RESEND_COOLDOWN_SECONDS`. Se mira el
  `created_at` del último token, así que no hace falta ninguna librería ni tabla nueva.
  Es **silencioso**: no devuelve `429`, porque un `429` solo aparecería con emails
  registrados y rompería la decisión I.
- **Cambio de email en `PATCH /users/me` (decisión E)**: si el email cambia de verdad,
  `email_verified = false`, se invalidan (`used_at`) los tokens de verificación pendientes,
  porque iban a la dirección anterior, y se envía un enlace nuevo a la dirección nueva.
  Este envío no espera el tiempo de espera. Mismo email o sin email en el cuerpo: nada
  cambia. El usuario no pierde el acceso.
- **Tokens (R-09)**: en claro solo van en el email. Nunca salen en un log ni en una
  respuesta. Se usan una sola vez y caducan.
- **Errores**: formato `{"detail", "code"}` con las clases de `app/core/exceptions.py` y el
  `TokenGoneError` (410) de HU-52.
- **Logs**: `info` en cada verificación y en cada envío, con el `user_id`; `warning` en
  cada rechazo, con su `code`. Nunca el token, el enlace ni la contraseña.

### Emails (decisión O)
- HTML en español, enviado con `send_email` (Brevo) en `BackgroundTasks`, igual que HU-52.
  Con `EMAIL_ENABLED=false` solo se registra el envío, sin el enlace.
- Verificación: asunto "Verifica tu email de APIResto"; enlace
  `{FRONTEND_URL}/verificar-email?token=…` y las horas de validez.
- Recuperación: asunto "Restablece tu contraseña de APIResto"; enlace
  `{FRONTEND_URL}/restablecer-contrasena?token=…`, las horas de validez y "si no lo has
  pedido tú, ignora este email".

### Configuración nueva
`EMAIL_VERIFY_EXPIRE_HOURS=48` (H), `PASSWORD_RESET_EXPIRE_HOURS=1` (G) y
`TOKEN_RESEND_COOLDOWN_SECONDS=60` (M), en `app/config.py`, `.env.example` y
`docs/deploy.md`. `PASSWORD_TOKEN_EXPIRE_HOURS` sigue siendo la de la invitación.

### Capas
`router_email_verification.py` / `router_password.py` / `auth.py` / `router_user.py` (solo
HTTP) → `email_verification_service.py` / `password_token_service.py` / `user_service.py` /
`social_auth_service.py` (reglas y transacciones) → `email_verification_token_repository.py`
/ `password_reset_token_repository.py` / `user_repository.py` (solo BD) → modelos. Los
emails se arman en `services/auth_emails.py`. El reparto de archivos entre agentes está en
`docs/agents/HU-33/lead.md`.

## Testing Decisions
- **Sin regresiones**: los tests existentes no se modifican y siguen pasando. Es la prueba
  de que no hay breaking-api.
- `verify-email`: caso feliz; token desconocido → 400; reutilizado → 410 `token_used`;
  caducado → 410 `token_expired`; usuario desactivado → 400; cuenta ya verificada → 204;
  usarlo invalida los demás tokens del usuario; cuerpo sin `token` → 422.
- `resend-verification`: cuenta sin verificar → 202 y llamada a `send_email`; email
  inexistente, cuenta verificada, inactiva o dentro del tiempo de espera → mismo 202 y
  mismo cuerpo, **sin** llamar a `send_email`; email mal formado → 422.
- `forgot-password`: cuenta existente → 202, `send_email` con el enlace y token con
  caducidad de 1 h; después `set-password` + login funcionan; email inexistente o inactivo
  → mismo 202 sin envío; tiempo de espera → sin segundo envío; cuenta sin contraseña →
  sí envía; email mal formado → 422.
- Login: una cuenta con `email_verified=false` inicia sesión igual (`200`), decisión A.
- Nacimiento (C, P1, P2): register → `false`; `POST /users/` → `true`; social nuevo y
  vinculado → `true`; invitado → `true` tras `set-password`; `create_admin` → `true`.
- `PATCH /users/me`: cambiar el email → `email_verified=false`, envío a la dirección nueva
  y tokens anteriores invalidados; mismo email → sin cambios.
- `UserOut` incluye `email_verified` y no incluye `password_hash`.
- Ningún token en claro en la BD (solo el hash) ni en los logs (`caplog`).
- Migración: `tests/test_migrations.py` sigue pasando, y un test comprueba que el backfill
  deja `true` a las filas existentes.
- `send_email` se sustituye en los tests: sin red ni Brevo.

## Criterios de aceptación
- [ ] Un cliente que se registra recibe un email de verificación; al usar el enlace, su
  cuenta queda con `email_verified=true`.
- [ ] `POST /auth/verify-email`: el token sirve una sola vez y caduca a las 48 h
  (configurable) (R-09).
- [ ] `POST /auth/resend-verification` y `POST /auth/forgot-password` responden siempre
  202 con el mismo cuerpo y respetan el tiempo de espera entre envíos.
- [ ] Un usuario que olvidó su contraseña recibe un enlace válido 1 h (configurable), fija
  una nueva con `POST /auth/set-password` y luego inicia sesión.
- [ ] Cambiar el email desde `PATCH /users/me` vuelve a pedir la verificación.
- [ ] Ningún endpoint existente cambia su código de respuesta ni sus errores; los tests
  existentes pasan sin modificarse.
- [ ] Ningún token ni contraseña se guarda en claro ni sale en los logs (R-02, R-09).
- [ ] Errores con `{detail, code}`; Swagger con `summary`, tag y ejemplos; `docs/api.md`,
  `.env.example` y `docs/deploy.md` actualizados.
- [ ] R-15 definida en esta spec; `specs/ontology.md` sin cambios.
- [ ] `ruff check .` limpio y `pytest` en verde con la cobertura mínima.

## Out of Scope
- Bloquear el login a las cuentas sin verificar (por ejemplo, tras una variable
  `EMAIL_VERIFICATION_REQUIRED`): issue aparte.
- Riesgo de robo de cuenta al vincular un login social con una cuenta registrada por otra
  persona con ese email (¿borrar la contraseña previa?): issue de seguridad aparte.
- Páginas del frontend `/verificar-email` y `/restablecer-contrasena` (issue aparte).
- Cerrar las sesiones abiertas tras un reset o un cambio de email: depende de
  refresh/logout (R-06, R-07).
- Rate limiting del login (R-10, HU propia).
- Que un cambio de email hecho por un admin (`PUT /users/{id}`) pida verificar.
- Que un admin marque a mano una cuenta como verificada.
- Distinguir en la tabla los tokens de invitación de los de recuperación.

## Preguntas abiertas
(vacío: spec lista para implementar)

## Decisiones de la sesión
Votación del equipo (16/10/2026). Levi cambió después la decisión A para no romper la API;
G–Q y P1–P2, con la recomendación del agente que Levi aceptó.

### A · La verificación es informativa
- **Decisión**: `email_verified` sale en `UserOut`; `POST /auth/login` no lo comprueba.
- **Por qué**: el equipo votó primero bloquear a todos (opción 3), pero eso cambiaba el
  contrato del login (403 nuevo), rompía tests existentes y la colección Bruno. Levi
  priorizó no romper la API y facilitar la revisión de la PR.
- **Alternativas rechazadas**: bloquear a todos (votada y revertida); bloquear solo a
  `customer`.

### B · Backfill de las cuentas existentes
- **Decisión**: la migración `0009` marca `true` las cuentas existentes.
- **Por qué**: el personal no aparece como "no verificado" y, si un día se activa el
  bloqueo, nadie se queda fuera.
- **Alternativas rechazadas**: todas en `false`.

### C · Quién nace verificado
- **Decisión**: la tabla de "Quién nace verificado". Aprobada por unanimidad.
- **Por qué**: solo el auto-registro no ofrece ninguna garantía sobre el email.

### D · Email automático al registrarse
- **Decisión**: sí, en segundo plano; `register` sigue devolviendo el mismo `201`.
- **Alternativas rechazadas**: que el usuario lo pida con "Reenviar".

### E · Cambio de email en `/users/me`
- **Decisión**: vuelve a `false` y se envía un enlace a la dirección nueva.
- **Alternativas rechazadas**: dejarlo fuera de alcance.

### F · Recuperación con `forgot-password` + `set-password`
- **Decisión**: `POST /auth/forgot-password` nuevo; se reutiliza `POST /auth/set-password`.
- **Por qué**: HU-52 ya lo previó; no se duplica el endpoint.
- **Alternativas rechazadas**: `POST /auth/reset-password` aparte.

### G · Caducidad propia del token de recuperación
- **Decisión**: `PASSWORD_RESET_EXPIRE_HOURS=1`; la invitación mantiene 48 h.
- **Por qué**: un enlace de recuperación filtrado debe durar poco. La caducidad se fija al
  emitir el token, así que el esquema no cambia.
- **Alternativas rechazadas**: reutilizar las 48 h de la invitación.

### H · Caducidad del token de verificación
- **Decisión**: `EMAIL_VERIFY_EXPIRE_HOURS=48`.

### I · No revelar qué emails existen
- **Decisión**: `forgot-password` y `resend-verification` responden siempre `202` con el
  mismo cuerpo.
- **Alternativas rechazadas**: 404/409 explícitos.

### J · `resend-verification` es público
- **Decisión**: cuerpo `{email}`, sin autenticación.
- **Por qué**: con la decisión I no filtra nada, y sirve también a quien no ha iniciado
  sesión.

### K · `verify-email` por POST desde el frontend
- **Decisión**: `POST /auth/verify-email {token}`, llamado desde la página del frontend.
- **Alternativas rechazadas**: un `GET` que abra el enlace contra la API.

### L · Errores de `verify-email`
- **Decisión**: los de HU-52 (400 / 410 / 410); cuenta ya verificada con token válido →
  204.

### M · Tiempo de espera entre envíos, silencioso
- **Decisión**: `TOKEN_RESEND_COOLDOWN_SECONDS=60`, mirando el `created_at` del último
  token; sin `429`.
- **Por qué**: no se añaden dependencias, y un `429` contradiría la decisión I.
- **Alternativas rechazadas**: librería de rate limiting; dejarlo para la HU de R-10.

### N · `forgot-password` también para cuentas sin contraseña
- **Decisión**: se envía igual.
- **Por qué**: HU-25 lo dejó para esta HU.

### O · Emails en HTML
- **Decisión**: HTML en español con `send_email`, como HU-52.

### P · Helper común de tokens
- **Decisión**: `app/core/one_time_tokens.py`, usado también por `password_token_service.py`.
- **Por qué**: no duplicar el hash ni la generación. Se avisa a Anna.
- **Alternativas rechazadas**: copiar las funciones en el servicio nuevo.

### Q · Regla R-15 en esta spec, no en la ontología
- **Decisión** (Levi): R-15 "verificación de email" se define en esta spec (sección "Regla
  de verificación de email"); `specs/ontology.md` no se modifica. Sin
  bloqueo del login.

### P1 · Vincular un login social marca la cuenta como verificada
- **Decisión**: al vincular una cuenta existente, `email_verified = true`.
- **Por qué**: el proveedor ya verificó el email (igual que C) y es lo más simple. Sin
  bloqueo del login, esta HU no empeora el riesgo que ya existe hoy.
- **Alternativas rechazadas**: borrar además la contraseña previa (queda en una issue de
  seguridad); no tocar `email_verified`.

### P2 · `create_admin` nace verificado
- **Decisión**: `true`, también al promover una cuenta existente.
- **Por qué**: lo crea quien opera el servidor; es coherente con los creados por un admin.

### Ubicación de los endpoints
- **Decisión** (Levi): `forgot-password` en `router_password.py`; `verify-email` y
  `resend-verification` en `router_email_verification.py`.
