# HU-32 · Soft delete y auditoría de usuarios

> Issue: #75 · Prioridad Should (R-11) · Escribe: Manon · Revisa: Rita ·
> Aprueba: Levi (PO). Vocabulario: `specs/ontology.md`. Primera spec que usa
> `specs/HU-TEMPLATE.md`.

## Problem Statement
Un admin solo puede desactivar usuarios (`PATCH /users/{id}/deactivate`): no hay forma de
darlos de baja ocultándolos de los listados ni de saber quién creó o modificó una
cuenta y cuándo. La issue pide "softdelete y auditoría" sin criterios de aceptación.

## Solution
Añadir a `users` las columnas `deleted_at`, `created_by`, `updated_by` y `updated_at`
(ya definidas en la ontología). Un admin puede borrar (soft delete) y restaurar
usuarios, y listar los borrados; cada creación o cambio queda registrado con su autor y
fecha. No hay borrado físico (R-04).

## User Stories
1. Como admin, quiero borrar un usuario sin perder su historial, para que no aparezca en
   los listados pero sus pedidos y reservas sigan siendo válidos.
2. Como admin, quiero restaurar un usuario borrado, para deshacer un borrado por error.
3. Como admin, quiero ver los usuarios borrados cuando lo pida, para localizar uno que
   restaurar.
4. Como admin, quiero saber quién creó o modificó un usuario y cuándo, para tener
   trazabilidad.
5. Como admin, quiero no poder borrarme ni desactivarme a mí mismo, para no dejar el
   sistema sin administrador.

## Implementation Decisions
- **Modelo**: `users` gana `deleted_at` (datetime, nulo), `created_by` y `updated_by`
  (FK `users.id`, nulos, `ON DELETE SET NULL`) y `updated_at` (datetime). Migración
  Alembic `0004`: columnas nulas; rellena `updated_at = created_at` en filas
  existentes; `created_by`/`updated_by` quedan en NULL para los usuarios previos.
- **Dos estados**: desactivar (`is_active=false`) = suspensión temporal, el usuario sigue
  en los listados y no puede iniciar sesión. Borrar = `deleted_at` + `is_active=false`,
  desaparece de los listados. Ambos reversibles por un admin.
- **Endpoints** (todos solo `admin`, como el resto de `/users`):
  - `DELETE /users/{id}` → soft delete; devuelve el `UserOut` actualizado (200).
  - `POST /users/{id}/restore` → `deleted_at=NULL`, `is_active=true`.
  - `GET /users/` acepta `include_deleted` (por defecto `false`); `GET /users/{id}` de
    un borrado → 404 salvo `include_deleted=true`. El nombre lo fija esta spec; HU-24
    (filtros admin) se adapta.
  - `UserOut` expone `deleted_at`, `created_by`, `updated_by`, `updated_at`.
- **Auditoría a nivel de servicio**: `user_service` recibe el admin que actúa y rellena
  `created_by` al crear; `updated_by` y `updated_at` al editar, desactivar, borrar o
  restaurar. El auto-registro (HU-22) deja `created_by` en NULL. Sin tabla `audit_log`.
- **Email**: sigue reservado tras borrar; crear otro usuario con ese email → 409 (R-01).
- **Casos límite**: un admin no puede borrarse ni desactivarse a sí mismo (403);
  `DELETE` sobre un borrado → 404; `restore` sobre un no borrado → 409. Un borrado no
  inicia sesión y sus tokens se rechazan (R-08) porque `is_active=false`.
- Errores con el formato estándar `{"detail", "code"}`; logging de borrar y restaurar.
- Capas: `router_user` → `user_service` → `user_repository` (filtro por `deleted_at`
  en el repository).

## Testing Decisions
- Feliz + 4xx por endpoint: borrar (200 / 404 / 403 a sí mismo), restaurar (200 / 409),
  listado con y sin `include_deleted`, 403 a roles no admin.
- Auditoría: `created_by` al crear, `updated_by`/`updated_at` tras editar y borrar.
- Un borrado no puede iniciar sesión; su email sigue dando 409 al crear.
- La migración se comprueba sobre Postgres en el CI (SQLite local puede no ser fiel).

## Criterios de aceptación
- [ ] `DELETE /users/{id}` marca `deleted_at` y `is_active=false`; el usuario deja de salir en `GET /users/`.
- [ ] `GET /users/?include_deleted=true` incluye los borrados.
- [ ] `POST /users/{id}/restore` lo deja activo y visible.
- [ ] Un admin no puede borrarse ni desactivarse a sí mismo (403).
- [ ] Crear, editar, desactivar, borrar y restaurar rellenan `created_by` / `updated_by` / `updated_at`.
- [ ] Un usuario borrado no puede iniciar sesión y su email no se puede reutilizar (409).
- [ ] Migración Alembic aplicada sobre datos existentes; `docs/api.md` actualizado.

## Out of Scope
- Tabla `audit_log` con historial completo de cambios (solo "último cambio").
- Borrado físico y purga de usuarios borrados.
- Soft delete de otras entidades (mesas, platos…).
- Endpoint de reactivación tras desactivar (hoy no existe; se puede editar `is_active` con `PUT`).

## Preguntas abiertas
Ninguna.

## Decisiones de la sesión
Sesión de 14/10/2026 (Manon, con Claude Code). Cada decisión, con su porqué y las
alternativas rechazadas:
- **Desactivar y borrar son dos estados** → cubre suspender y dar de baja sin romper
  `/deactivate`. Rechazado: sustituir `/deactivate` por `DELETE` (cambio de contrato).
- **Email reservado tras borrar** → un usuario = una identidad; sin índice único
  parcial (difiere entre Postgres y SQLite). Rechazado: índice parcial, anonimizar email.
- **Restaurar deja al usuario activo; `include_deleted` para listar** → reversible sin
  endpoint nuevo de reactivación. Rechazado: sin restore; restaurar inactivo.
- **Auditoría en el servicio** → explícito y testable. Rechazado: listener SQLAlchemy,
  tabla `audit_log`.
- **Barandillas** (no autoborrado, 404/409) → evita dejar el sistema sin admin.
- **Migración con NULL para filas previas** → no afirma una autoría falsa. Rechazado:
  asignar el admin más antiguo.
- **Parámetro `include_deleted`** → lo fija esta HU; Rita adapta los filtros de HU-24.
