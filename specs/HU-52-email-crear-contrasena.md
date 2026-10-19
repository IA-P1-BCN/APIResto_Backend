# HU-52 · Email para que el usuario cree su propia contraseña

> Issue: #107 · Prioridad Could (sugerencia de la profe) · Escribe: Anna · Revisa: pareja
> de revisión del sprint · Aprueba: Levi (PO). Vocabulario: `specs/ontology.md` (R-02,
> R-09). Usa `specs/HU-TEMPLATE.md`. Parte de frontend: página "Crea tu contraseña" (Anna).

## Problem Statement
Cuando el admin da de alta a alguien con `POST /users/`, tiene que inventarse su
contraseña y comunicársela por otro canal. La contraseña viaja en claro fuera de la app y
la persona no la elige. Desde la HU-38 un `User` puede no tener contraseña
(`password_hash` nulo), pero no hay forma de que la cree él mismo.

## Solution
El admin invita a un usuario sin contraseña con `POST /users/invite`. El backend crea el
`User` con `password_hash` nulo, genera un `PasswordResetToken` de un solo uso que caduca
y envía un email (Brevo, igual que las reservas de la HU-19) con un enlace a la página
"Crea tu contraseña" del frontend. Esa página llama a `POST /auth/set-password` con el
token y la contraseña nueva; a partir de ahí el usuario entra con `POST /auth/login`.

## User Stories
1. Como admin, quiero dar de alta a un usuario sin inventarme su contraseña, para no
   tener que enviársela por otro canal.
2. Como usuario invitado, quiero recibir un email con un enlace para elegir mi
   contraseña, para entrar en la app con una clave que solo yo conozco.
3. Como usuario invitado, quiero un mensaje claro si el enlace ha caducado o ya lo usé,
   para saber que tengo que pedir otro al restaurante.
4. Como equipo, queremos que el token no se guarde en claro y que solo sirva una vez,
   para que un enlace filtrado no dé acceso permanente (R-09).

## Implementation Decisions
- **Modelo**: entidad `PasswordResetToken` de la ontología, tabla
  `password_reset_tokens`: `id`, `user_id` (FK a `users`, `ON DELETE CASCADE`),
  `token_hash` (único), `expires_at`, `used_at` (nulo = sin usar), `created_at`.
  Migración de Alembic `0008`.
- **Token**: `secrets.token_urlsafe(32)`. Se guarda solo su SHA-256 (`token_hash`); el
  valor en claro solo va en el email y nunca se registra en el log. Caduca a las
  `PASSWORD_TOKEN_EXPIRE_HOURS` horas (por defecto 48).
- **`POST /users/invite`** (solo `admin`, igual que el resto de `/users`): cuerpo
  `{name, email, phone?, role?}` (rol por defecto `customer`). Crea el `User` con
  `password_hash` nulo, `created_by`/`updated_by` = el admin, y el token. Envía el email
  en segundo plano. Respuesta `201` con `UserOut`. Email repetido → `409` (R-01, mismo
  mensaje que `POST /users/`).
- **`POST /auth/set-password`** (público): cuerpo `{token, new_password}`;
  `new_password` con al menos 8 caracteres (R-02, si no `422`). Respuesta `204`.
  - Token desconocido, o usuario desactivado o borrado → `400` `invalid_token`.
  - Token ya usado → `410` `token_used`. Token caducado → `410` `token_expired` (R-09).
  - Al usarlo: se guarda el hash bcrypt de la contraseña, se marca `used_at` y se marcan
    también como usados los demás tokens pendientes de ese usuario.
- **Email**: asunto "Crea tu contraseña de APIResto"; enlace
  `{FRONTEND_URL}/crear-contrasena?token=…` y aviso de las horas de validez. Con
  `EMAIL_ENABLED=false` solo se registra que se ha "enviado" (sin el enlace).
- **Configuración nueva**: `FRONTEND_URL` (por defecto `http://localhost:5173`) y
  `PASSWORD_TOKEN_EXPIRE_HOURS` (por defecto `48`), en `.env.example` y `docs/deploy.md`.
- **Capas**: `routers/router_password.py` (los dos endpoints) →
  `services/password_token_service.py` (reglas, errores, email) →
  `repositories/password_reset_token_repository.py` y `user_repository` →
  `models/model_password_reset_token.py`. Esquemas en `schemas/schema_password_token.py`.
  No se cambia ninguna línea existente de `POST /users/`, `user_service` ni `auth.py`.
- **Errores**: formato estándar `{"detail", "code"}`. El `410` usa una subclase de
  `AppError` propia del servicio.

## Testing Decisions
- `POST /users/invite`: crea el usuario sin contraseña, guarda `created_by`, crea un
  token con hash (no en claro) y caducidad, y llama a `send_email` con el enlace; email
  repetido → 409; sin token → 401; rol no admin → 403; email no válido → 422.
- `POST /auth/set-password`: caso feliz (después el login funciona y el token queda
  usado); token desconocido → 400; reutilizar → 410 `token_used`; caducado → 410
  `token_expired`; contraseña corta → 422; usuario desactivado → 400; usar un token
  invalida los demás del mismo usuario.
- Un usuario invitado no puede iniciar sesión antes de crear su contraseña (401).
- El email se prueba sustituyendo `send_email`; sin red ni Brevo en los tests.
- Migración: los tests de `tests/test_migrations.py` siguen pasando (una sola cabeza, los
  modelos coinciden con las migraciones, se puede deshacer).

## Criterios de aceptación
- [ ] Un admin invita a un usuario con `POST /users/invite` y este recibe un email con un
  enlace para crear su contraseña.
- [ ] El usuario crea su contraseña en la página del enlace y después inicia sesión.
- [ ] El enlace sirve una sola vez y caduca a las 48 h (configurable).
- [ ] El token nunca se guarda ni se registra en claro.
- [ ] Errores `400 invalid_token`, `410 token_used`, `410 token_expired` y `422` con el
  formato estándar.
- [ ] Migración `0008`; `docs/api.md`, `.env.example` y `docs/deploy.md` actualizados.
- [ ] Frontend: página pública `/crear-contrasena` con contraseña y repetición, y
  mensajes para cada error.

## Out of Scope
- "He olvidado mi contraseña" (pedir el email desde el login): reutilizará
  `PasswordResetToken` y `POST /auth/set-password`, pero es otra HU.
- Reenviar la invitación. Mientras tanto, si el enlace caduca, el admin puede fijar una
  contraseña con `PUT /users/{id}`.
- Cambiar `POST /users/` para que la contraseña sea opcional.
- Pantalla de gestión de usuarios en el frontend.

## Preguntas abiertas
Ninguna.

## Decisiones de la sesión
Sesión del 15/10/2026 (Anna):
- **Endpoint nuevo `POST /users/invite` en lugar de hacer opcional la contraseña de
  `POST /users/`** → no cambia el contrato actual ni el código de HU-32 y deja clara la
  intención. Rechazado: `password` opcional en `UserCreate` (cambio de contrato).
- **Invitar sirve para cualquier rol** (por defecto `customer`) → el personal también se
  beneficia de elegir su contraseña. Rechazado: solo clientes.
- **`PasswordResetToken` también para la invitación** → la ontología ya lo define con la
  forma que hace falta (R-09) y lo reutilizará "he olvidado mi contraseña". Rechazado:
  una entidad nueva solo para invitaciones.
- **SHA-256 para el token y bcrypt para la contraseña** → el token es aleatorio y largo,
  así que basta un hash rápido que permita buscarlo. Rechazado: bcrypt para el token
  (obliga a recorrer todos los tokens).
- **400 para token desconocido y 410 para usado o caducado** → R-09 permite los dos; 410
  le dice al frontend que el enlace existió pero ya no sirve.
- **48 h de validez por defecto** → margen para quien no mira el correo a diario sin
  dejar enlaces abiertos mucho tiempo.
