# HU-38 · Inicio de sesión con Google o GitHub

> Issue: #81 · Prioridad Could (R-13) · Nivel Experto · Escribe: Manon · Revisa: Rita ·
> Aprueba: Levi (PO). Vocabulario: `specs/ontology.md`. Usa `specs/HU-TEMPLATE.md`.
> Parte de frontend: `Resto-API_Frontend#31` (bloqueada por esta HU).

## Problem Statement
Hoy solo se puede entrar con email y contraseña. La issue pide iniciar sesión con Google
o GitHub, sin criterios de aceptación, y la ontología solo define la entidad
`SocialAccount` (C) y la regla R-13.

## Solution
Un endpoint `POST /auth/social/{provider}` al que el frontend envía el `code` OAuth que
recibió del proveedor. El backend lo intercambia, obtiene el email verificado del
usuario, busca o crea el `User` (rol `customer`), registra un `SocialAccount` y devuelve
nuestro JWT, igual que `/auth/login`.

## User Stories
1. Como cliente, quiero entrar con mi cuenta de Google, para no crear otra contraseña.
2. Como cliente, quiero entrar con mi cuenta de GitHub, para lo mismo.
3. Como usuario que ya tiene cuenta, quiero que el login social se vincule a ella si mi
   email está verificado, para no acabar con dos cuentas.
4. Como admin, quiero que un usuario desactivado o borrado no pueda entrar por el
   proveedor, para que el bloqueo valga en todos los accesos.
5. Como equipo, quiero que un email sin verificar no sirva para vincular cuentas, para
   evitar el robo de cuentas.

## Implementation Decisions
- **Flujo**: el frontend redirige al proveedor y recibe `?code` en su propia página de
  callback; lo envía a `POST /auth/social/{provider}` con `{code, redirect_uri}`. El
  backend lo intercambia con `httpx`. Sin cookies ni sesión de servidor.
- **Endpoint**: `POST /auth/social/{provider}` (`provider` = `google` | `github`),
  público. Respuesta `{access_token, token_type}`, igual que `/auth/login`.
- **Modelo**: tabla `social_accounts` (`id`, `user_id` FK, `provider`,
  `provider_user_id`, `created_at`), única por (`provider`, `provider_user_id`).
  `users.password_hash` pasa a ser nulo. Migración Alembic con el siguiente número libre
  al implementar (HU-32 usa `0004`).
- **Email por proveedor**: Google (`openid email profile`): solo si `email_verified`.
  GitHub (`user:email`): `GET /user/emails`, el `primary` con `verified`. Sin email
  verificado → 401. El `name` sale del perfil (si falta, la parte local del email).
- **Vinculación** (R-13): `SocialAccount` existente → entra. Si no, un `User` con ese
  email (normalizado, R-01) → se vincula, sin cambiar su rol. Si no existe → se crea un
  `customer` sin contraseña.
- **Estado del usuario**: inactivo (`is_active=false`) o borrado (`deleted_at`) → 401. El
  login por contraseña rechaza (401) a quien no tiene `password_hash`; `authenticate` lo
  comprueba antes de llamar a `verify_password`.
- **Configuración**: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_ID`,
  `GITHUB_CLIENT_SECRET` (vacías por defecto; proveedor sin configurar → 503).
  `redirect_uri` debe estar en una lista permitida derivada de `ALLOWED_ORIGINS`
  (si no, 422). Se documentan en `.env.example` y `docs/deploy.md`; los secretos nunca
  entran al repo.
- **Errores**: `provider` desconocido → 422; `code` inválido o caducado → 401; proveedor
  no disponible → 502; formato estándar `{"detail", "code"}`.
- **Logging**: se registra el proveedor y el resultado; nunca el `code`, los tokens del
  proveedor ni el secreto.
- Capas: `routers/auth.py` → `services/social_auth_service.py` (reglas) →
  `repositories/social_account_repository.py` y `user_repository`; las llamadas HTTP al
  proveedor van en un cliente aislado, fácil de mockear.

## Testing Decisions
- `httpx` se mockea; sin red en los tests.
- Casos: usuario nuevo (se crea `customer` y `SocialAccount`); `SocialAccount` existente;
  vinculación a un `User` existente con email verificado; email sin verificar → 401;
  GitHub sin email primario verificado → 401; usuario inactivo o borrado → 401; `code`
  inválido → 401; proveedor caído → 502; proveedor sin configurar → 503; `redirect_uri`
  no permitida → 422; usuario sin contraseña no entra por `/auth/login`.
- Una cuenta de personal vinculada conserva su rol.

## Criterios de aceptación
- [ ] `POST /auth/social/google` y `/github` devuelven un JWT válido para un usuario nuevo.
- [ ] El `User` nuevo es `customer` y tiene un `SocialAccount`.
- [ ] Un email verificado coincidente se vincula; uno sin verificar → 401.
- [ ] Usuario inactivo o borrado → 401.
- [ ] Un usuario sin contraseña no puede usar `/auth/login`.
- [ ] Sin secretos en el repo; variables en `.env.example` y `docs/deploy.md`.
- [ ] Migración Alembic; `docs/api.md` actualizado; tests sin red.

## Out of Scope
- La UI (botones y página de callback): `Resto-API_Frontend#31`.
- Refresh tokens, 2FA y verificación de email propia (otras HU).
- Desvincular una cuenta social, o vincular una desde un perfil ya iniciado.
- Más proveedores que Google y GitHub.
- Registrar las apps OAuth en Google y GitHub y poner los secretos en Render: tarea
  externa de quien tenga acceso a esas plataformas (Anna para Render).

## Preguntas abiertas
Ninguna.

## Decisiones de la sesión
Sesión de 14/10/2026 (Manon, con Claude Code):
- **El frontend envía el `code`** → backend como API pura y mockeable. Rechazado:
  redirección en el backend (necesita `state` y deja el token en la URL); solo ID token
  de Google (GitHub no lo tiene).
- **Vincular solo con email verificado** → evita el robo de cuentas. Rechazado: no
  vincular nunca; vincular siempre.
- **`password_hash` nulo** → modela "solo entra por proveedor" y deja paso a HU-52.
  Rechazado: hash aleatorio inservible.
- **Email primario verificado de GitHub** → muchos perfiles ocultan el email. Rechazado:
  solo el email del perfil.
- **Respuesta igual a `/auth/login` y variables de entorno por proveedor** → no se amplía
  el contrato. Rechazado: devolver también el usuario y `is_new`.
- **HU de solo backend; issue de frontend abierta ya** (`Resto-API_Frontend#31`).
