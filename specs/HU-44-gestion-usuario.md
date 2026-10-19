# HU-44 · Gestión de usuarios en el panel y auto-perfil del usuario

> Issue: #NN · Prioridad Must · Escribe: ... · Revisa: ... · Aprueba: Levi (PO).
> Comparte rama (`feature/HU-22-register-user`) con HU-22 · Registro de usuario, por ser
> ambas del ámbito de usuarios.

## Problem Statement
Hoy `/usuarios` es un placeholder: el admin no puede gestionar usuarios desde el panel,
y el usuario no puede cambiar su perfil ni su contraseña desde la web.

## Solution
Reutilizar el CRUD de `/users` que ya existe (HU-32) sobre una pantalla de admin, y
usar el auto-servicio de perfil y contraseña de la HU-25 (`/users/me`).

## User Stories
1. Como admin, quiero crear/editar/desactivar/borrar/restaurar usuarios desde el panel.
2. Como usuario, quiero cambiar mi perfil (nombre, email, teléfono) desde la web.
3. Como usuario, quiero cambiar mi contraseña desde la web.

## Implementation Decisions
- Modelo: sin cambios ni migración (las columnas ya existen).
- Endpoints admin (ya existen, HU-32): `POST/GET /users/`, `GET/PUT /users/{id}`,
  `PATCH /users/{id}/deactivate`, `DELETE /users/{id}`, `POST /users/{id}/restore`.
- Auto-perfil: lo cubre la HU-25 (`specs/HU-25-cambio-password-perfil.md`):
  `PATCH /users/me` (200/401/409/422) y `POST /users/me/password` (204/400/401/403/422).
- Reglas: R-01 (email único en minúsculas), R-02 (≥8, bcrypt, hash nunca expuesto),
  R-03 (solo admin cambia roles), R-04 (borrar = `is_active=false`).
- El auto-perfil usa un schema propio **sin `role`** ni `is_active` (evita escalada).
- Capas: `routers/auth.py` → `services/user_service.py` → `repositories/user_repository.py`.

## Testing Decisions
- `tests/test_users.py` (admin, ya existe) + `tests/test_profile.py` (auto-perfil):
  caso feliz y 4xx por endpoint, con el contrato de la HU-25.

## Criterios de aceptación
- [ ] El admin lista, crea, edita, desactiva, borra y restaura usuarios.
- [ ] El usuario edita nombre/email/teléfono; email duplicado → 409.
- [ ] El usuario cambia su contraseña exigiendo la actual (403 si falla) y mín. 8 (422).
- [ ] `password_hash` no aparece en ninguna respuesta.
- [ ] Un usuario no puede cambiarse el rol ni desactivarse/borrarse a sí mismo.

## Out of Scope
- Verificación de email, recuperación de contraseña y 2FA (`R-09`/`R-12`), en sus HU.
- Frontend: decidir si entra aquí o va en su HU; este PR es solo backend.

## Preguntas abiertas
(vacío)

## Decisiones de la sesión
### El auto-perfil no puede cambiar el rol
- **Decisión**: schema sin `role` ni `is_active`.
- **Por qué**: R-03 reserva el cambio de rol al admin; evita escalada de privilegios.
- **Alternativas rechazadas**: reutilizar `UserUpdate` (incluye `role`) para `/auth/me`.

### Una sola rama para HU-22 y HU-44
- **Decisión**: desarrollar ambas HU de usuarios en `feature/HU-22-register-user`.
- **Por qué**: son del mismo ámbito (usuarios) y se tocan los mismos ficheros.
- **Alternativas rechazadas**: rama y PR separados por HU (`AGENTS.md` pide uno por HU).

### El auto-perfil se unifica con la HU-25
- **Decisión**: los endpoints de auto-perfil son los de la HU-25 (`/users/me`); se quitan
  `PATCH /auth/me` y `POST /auth/me/password`, y `tests/test_profile.py` pasa al contrato
  de la HU-25 (rol en el body → 422, contraseña actual incorrecta → 403, cambio → 204).
- **Por qué**: las dos HU implementaban lo mismo con contratos distintos; la HU-25 tiene
  issue (#68) y su spec cierra más casos (cuenta sin contraseña, misma contraseña).
- **Alternativas rechazadas**: mantener los dos pares de endpoints; adoptar el contrato
  de `/auth/me`.
