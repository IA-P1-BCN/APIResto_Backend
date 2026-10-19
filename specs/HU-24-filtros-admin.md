# HU-24 · Filtros admin de usuarios

> Issue: #67 · Prioridad Must · Escribe: Rita · Revisa y aprueba: Manon.
> Vocabulario: `specs/ontology.md`.

## Problem Statement

Un admin solo puede listar usuarios con `GET /users/` usando `skip`/`limit` (hasta 500)
y recibe una lista simple, sin total y sin forma de filtrar ni buscar. Con muchos
usuarios no hay manera rápida de encontrar a uno concreto. Es además el único listado
de la API que no sigue el contrato de paginación común de HU-11. La issue solo tiene la
historia, sin criterios de aceptación.

## Solution

`GET /users/` pasa a devolver `Page[UserOut]` con `page`/`size` y acepta filtros por
rol y estado, una búsqueda por texto en nombre o email y el `include_deleted` que ya
existe (HU-32). Todos los parámetros se combinan entre sí.

## User Stories

1. Como admin, quiero buscar un usuario escribiendo parte de su nombre o email, para
   encontrarlo sin recorrer toda la lista.
2. Como admin, quiero filtrar por rol, para ver por ejemplo todo el personal de barra.
3. Como admin, quiero filtrar por activos o desactivados, para revisar las cuentas
   suspendidas.
4. Como admin, quiero el listado paginado con el total, para moverme por páginas y saber
   cuántos usuarios cumplen el filtro.

## Implementation Decisions

- **Modelo**: sin cambios. No hace falta migración.
- **Endpoint**: `GET /users/`, solo `admin` (como el resto de `/users`).
  - Paginación con el contrato de HU-11: `PageParamsDep` (`page` ≥ 1 por defecto 1,
    `size` de 1 a 100 por defecto 20) y respuesta `Page[UserOut]`
    (`items`, `total`, `page`, `size`). Se eliminan `skip` y `limit`.
  - `role`: valor del enum `Role`. Un valor que no existe da 422 (validación de FastAPI).
  - `is_active`: bool. Sin el parámetro salen activos e inactivos.
  - `q`: texto; coincidencia parcial sin distinguir mayúsculas en `name` o en `email`.
    Se quitan los espacios de los extremos; si queda vacío, no filtra. Los caracteres
    `%` y `_` se buscan como texto literal, no como comodines.
  - `include_deleted`: igual que en HU-32 (por defecto `false`, R-11).
  - `total` cuenta los usuarios que cumplen todos los filtros, no todos los usuarios.
  - Orden fijo por `id` ascendente (`paginate` exige `order_by`).
  - Una página más allá de la última devuelve `items` vacío (contrato de HU-11).
- **Contrato**: cambio `breaking-api` (la respuesta pasa de lista a `Page`). El
  frontend no usa `/users`. Se actualiza `docs/api.md` (sección de usuarios).
- **Capas**: `router_user` (query params y `PageParamsDep`) → `user_service`
  (pasa los filtros) → `user_repository` (construye el `select` filtrado y ordenado)
  → `paginate(...)`.
- Sin cambios en `GET /users/{id}` ni en el resto de endpoints de usuarios.

## Testing Decisions

- Paginación: `items`, `total`, `page`, `size` correctos; segunda página; página vacía
  más allá del final; `size` > 100 → 422.
- Cada filtro por separado y combinados (p. ej. `role` + `q`), con `total` coherente.
- `q`: parcial, sin distinguir mayúsculas, en nombre y en email; `q` con solo espacios
  no filtra; `%` no actúa como comodín.
- `role` inválido → 422. Rol no admin → 403 (ya cubierto en `test_permissions.py`).
- `include_deleted` sigue funcionando con la respuesta paginada.
- Se adaptan a `r.json()["items"]` las aserciones de `tests/test_users.py` que leían la
  respuesta como lista (HU-32). No se debilita ninguna.

## Criterios de aceptación

- [x] `GET /users/` devuelve `Page[UserOut]` y acepta `page`/`size` con los límites de HU-11.
- [x] `?role=` filtra por rol; un rol inexistente da 422.
- [x] `?is_active=` filtra activos o desactivados.
- [x] `?q=` busca de forma parcial y sin distinguir mayúsculas en nombre o email.
- [x] `?q=` no distingue acentos y admite como máximo 100 caracteres (más → 422). Añadido tras la revisión de Manon.
- [x] Los filtros se combinan entre sí y con `include_deleted`; `total` refleja el filtro.
- [x] El orden es estable por `id` ascendente entre páginas.
- [x] Tests nuevos en verde, tests de HU-32 adaptados, lint limpio y `docs/api.md` actualizado.

## Out of Scope

- Filtro por rango de `created_at`.
- Ordenación configurable (`?sort=`).
- Búsqueda por teléfono.
- Paginar otros listados que aún no usen `Page` (no se ha revisado en esta HU).

## Preguntas abiertas

Ninguna.

## Decisiones de la sesión

Sesión de 14/10/2026 (Rita, con Claude claude.ai · Opus 5.5). La issue no tiene
criterios de aceptación; esta spec los fija.

### Formato de la respuesta

- **Decisión**: `Page[UserOut]` con `page`/`size`; se quitan `skip`/`limit`.
- **Por qué**: es el contrato común de HU-11 que ya usan los demás listados, da el
  `total` y la HU pide paginar. El coste para el resto es bajo: el frontend no llama a
  `/users` y solo cambian unas pocas aserciones de los tests de HU-32.
- **Alternativas rechazadas**: lista simple con `skip`/`limit` (sin total, distinta al
  resto de la API); aceptar las dos formas a la vez (más código y tests sin necesidad).

### Filtros

- **Decisión**: `role` e `is_active`, además del `include_deleted` de HU-32.
- **Por qué**: son los que sirven para "encontrar a cualquiera" sin añadir validación
  extra.
- **Alternativas rechazadas**: rango de `created_at` (no lo pide la HU; a Out of Scope).

### Búsqueda

- **Decisión**: un único parámetro `q` en `name` o `email`, parcial y sin distinguir
  mayúsculas.
- **Por qué**: el admin no tiene que saber en qué campo buscar.
- **Alternativas rechazadas**: parámetros separados `name` y `email`; incluir `phone`
  (opcional y sin formato fijo).

### Orden

- **Decisión**: fijo por `id` ascendente.
- **Por qué**: es el orden actual, estable entre páginas y sin parámetros nuevos.
- **Alternativas rechazadas**: alfabético por `name`; `?sort=` configurable.

### Revisión de Manon tras integrar la PR #126 (15/10/2026)
- **Acentos**: `q` no encontraba "José" con `jose`, ni "ÁNGELA" con `ángela` (el `lower()`
  de SQLite y el de Postgres con la configuración del CI no pasan a minúsculas las letras
  acentuadas). **Decisión**: `translate()` a letras sin acento antes de `lower()`
  (`app/core/text_search.py`); Postgres lo trae de serie y en SQLite se registra una
  función igual al conectar. Sin migración. **Rechazado**: extensión `unaccent` (migración,
  `CREATE EXTENSION` en Neon y no existe en SQLite).
- **Longitud de `q`**: máximo 100 caracteres; más → 422.
- **`skip`/`limit` ignorados**: se mantiene el contrato. Comprobado que nadie más llama a
  `/users` (frontend y `scripts/`); la PR #126 lleva la etiqueta `breaking-api`.
  **Rechazado**: devolver 422 si llegan (código para un caso que hoy no existe).
