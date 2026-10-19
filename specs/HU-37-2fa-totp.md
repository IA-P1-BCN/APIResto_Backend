# HU-37 · Verificación en dos pasos (TOTP)

> Issue: #80 · Prioridad Could (R-12) · Nivel Experto · Escribe: Anna · Revisa: pareja de
> revisión del sprint · Aprueba: Levi (PO). Vocabulario: `specs/ontology.md`. Usa
> `specs/HU-TEMPLATE.md`. Incluye la parte de frontend (login y página "Seguridad").

## Problem Statement
Hoy basta con el email y la contraseña (o una cuenta de Google o GitHub) para entrar. Si
alguien consigue la contraseña de un admin, tiene acceso a todo. La issue pide verificación
en dos pasos con TOTP; la ontología define `totp_secret` (cifrado) y `totp_enabled` en
`User` y la regla R-12, y deja a esta spec cómo recuperar el acceso.

## Solution
Cada usuario puede activar la verificación en dos pasos desde la web: escanea un QR con una
app de autenticación (Google Authenticator, Authy…), confirma con un primer código y recibe
8 códigos de recuperación. Desde entonces, tras la contraseña o el login social el backend
no devuelve el JWT, sino un token temporal; la web pide el código de 6 dígitos (o uno de
recuperación) y lo canjea por el JWT. Las cuentas sin 2FA no cambian.

## User Stories
1. Como usuario, quiero activar la verificación en dos pasos con una app del móvil, para
   que no baste con mi contraseña para entrar.
2. Como usuario con 2FA, quiero que el login me pida el código después de la contraseña o
   de Google/GitHub, para que nadie entre solo con ellos.
3. Como usuario que ha perdido el móvil, quiero entrar con un código de recuperación, para
   no quedarme fuera de mi cuenta.
4. Como usuario, quiero desactivar la 2FA cuando lo necesite, confirmándolo con un código.
5. Como equipo, queremos que el secreto TOTP no se guarde en claro ni salga en ningún
   schema o log (como R-02).

## Implementation Decisions
- **Modelo**: en `users`, `totp_secret` (texto, cifrado con Fernet), `totp_enabled` (bool,
  por defecto `false`) y `totp_recovery_codes` (texto con los SHA-256 de los códigos sin
  usar, separados por comas). Migración `0010`.
- **Cifrado**: Fernet (`cryptography`) con la clave `TOTP_ENCRYPTION_KEY`; si está vacía, se
  deriva de `JWT_SECRET_KEY` (SHA-256). Ningún schema de salida incluye el secreto, salvo
  `POST /users/me/2fa/setup`, que lo devuelve una vez para añadirlo a la app.
- **TOTP**: `pyotp`, códigos de 6 dígitos cada 30 s, se acepta ±1 intervalo. Emisor
  `APIResto`. QR en SVG con `segno` (sin dependencias).
- **Login en dos pasos**: `POST /auth/login` y `POST /auth/social/{provider}` devuelven
  `{"mfa_required": true, "mfa_token": "…"}` si el usuario tiene `totp_enabled`. El
  `mfa_token` es un JWT con `aud: "2fa"` que caduca en 5 min; como lleva `aud`, la
  validación del access token lo rechaza y no sirve para llamar a la API.
- **`POST /auth/2fa/verify`** (público): `{mfa_token, code}`. `code` es el TOTP o un código
  de recuperación (este se gasta). Respuesta igual que `/auth/login` (`TokenOut`).
  `mfa_token` inválido o caducado → 401 `invalid_mfa_token`; código incorrecto → 401
  `invalid_totp_code`; usuario desactivado o borrado → 401.
- **Gestión desde el perfil** (cualquier usuario autenticado, prefijo `/users/me/2fa`):
  - `GET` → `{enabled, recovery_codes_left}`.
  - `POST /setup` → genera un secreto nuevo (aún sin activar) y devuelve `{secret,
    otpauth_uri, qr_svg}`. Con la 2FA ya activa → 409 `totp_already_enabled`.
  - `POST /enable` `{code}` → con un código válido activa la 2FA y devuelve
    `{recovery_codes}` (8 códigos, se muestran una sola vez). Sin `setup` previo → 409
    `totp_not_set_up`; código incorrecto → 400 `invalid_totp_code`.
  - `POST /disable` `{code}` → con un TOTP o un código de recuperación válido la desactiva
    y borra secreto y códigos. Sin 2FA → 409 `totp_not_enabled`; código incorrecto → 400
    `invalid_totp_code`.
- **Errores**: formato estándar `{"detail", "code"}`. **Logs**: se registra activar,
  desactivar y los fallos con el `user_id`; nunca el secreto ni los códigos.
- **Capas**: `routers/router_2fa.py` → `services/totp_service.py` →
  `user_repository`; esquemas en `schemas/schema_2fa.py`. En `routers/auth.py` solo se
  añade la comprobación de `totp_enabled` antes de emitir el JWT en el login y en el login
  social.
- **Frontend**: tras el login (también el social), si llega `mfa_required`, la web pide el
  código de 6 dígitos (con la opción de usar uno de recuperación). Página **"Seguridad"**
  para todos los roles: estado, activar (QR, secreto para teclearlo a mano y confirmar con
  un código), mostrar los códigos de recuperación una vez y desactivar. El modo simulado
  imita el flujo (código de prueba `123456`).

## Testing Decisions
- Activar: `setup` → `enable` con un código válido (generado con el secreto en el test) →
  `enabled: true` y 8 códigos; `enable` con código malo → 400; `enable` sin `setup` → 409;
  `setup` con la 2FA activa → 409.
- Login con 2FA: contraseña correcta → `mfa_required`; `verify` con TOTP → JWT válido;
  código malo → 401; `mfa_token` caducado o manipulado → 401; el `mfa_token` no sirve
  como access token (401 en `/auth/me`).
- Códigos de recuperación: sirven una vez; el segundo uso → 401.
- Login social con 2FA → `mfa_required`.
- Desactivar con código → login normal otra vez; código malo → 400.
- Usuarios sin 2FA: login y login social igual que antes (todos los tests actuales pasan).
- El secreto se guarda cifrado (no coincide con el valor en claro) y no sale en `UserOut`.
- Frontend: paso del código tras el login (simulado y contra la API), página Seguridad
  (activar, códigos, desactivar).

## Criterios de aceptación
- [ ] Un usuario activa la 2FA escaneando un QR y confirmando con un código.
- [ ] Con 2FA, el login (contraseña o social) pide el código y sin él no hay JWT.
- [ ] Un código de recuperación permite entrar una sola vez.
- [ ] Se puede desactivar con un código válido.
- [ ] El secreto se guarda cifrado y solo sale en la respuesta de `setup`; nunca en los logs.
- [ ] Sin 2FA, todo funciona como antes.
- [ ] Migración `0010`; `docs/api.md`, `.env.example` y `docs/deploy.md` actualizados;
  nuevas dependencias (`pyotp`, `cryptography`, `segno`) indicadas en la PR.

## Out of Scope
- Límite de intentos en `/auth/2fa/verify` (lo cubre la HU de rate limiting, R-10).
- Que un admin desactive la 2FA de otro usuario.
- Recordar el dispositivo ("no volver a pedir el código en 30 días").
- Otros segundos factores (SMS, email, llaves de seguridad).
- Regenerar los códigos de recuperación sin desactivar y volver a activar.

## Preguntas abiertas
Ninguna.

## Decisiones de la sesión
Sesión del 16/10/2026 (Anna):
- **Login en dos pasos con token temporal** → la web solo pide el código si hace falta y
  el formulario OAuth2 de `/auth/login` no cambia. Rechazado: un campo de código opcional
  en el login.
- **Códigos de recuperación** (8, de un solo uso, guardados con hash) → el usuario no
  depende de nadie si pierde el móvil. Rechazado: que lo desactive un admin; dejarlo fuera.
- **El login social también pide el código** → la 2FA protege la cuenta entre por donde
  entre. Rechazado: confiar en la verificación del proveedor.
- **Backend y frontend en esta HU** → la funcionalidad no sirve sin la web. Rechazado:
  solo backend.
- **`aud: "2fa"` en el token temporal** → la validación actual del access token ya rechaza
  los tokens con audiencia, así que no hace falta tocar `core/security.py`.
