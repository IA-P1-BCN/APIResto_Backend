# HU-40 · Estación de barra en los pedidos (bebidas y postres)

> Issue: #83 · Prioridad Must · Nivel Medio · Escribe e implementa: Manon · Revisa: Rita ·
> Aprueba: Levi (PO). Vocabulario: `specs/ontology.md`. Usa `specs/HU-TEMPLATE.md`. Parte de
> frontend ya hecha: HU-41 (pantalla de barra, Anna), que hoy filtra en el cliente.

## Problem Statement
El equipo decidió separar los pedidos por estación: cocina recibe entrantes y principales;
barra, bebidas y postres (plan v3, §5.1 y §5.2). La base ya existe: `categories.station`
(`kitchen` / `bar`, migración 0003), el rol `bartender` y la pantalla de barra. Pero **el
backend no aplica la separación**:

- `GET /orders` y `GET /orders/{id}` devuelven todas las líneas a `kitchen` y a `bartender`.
- `/ws/kitchen` difunde cada pedido a todos los conectados, sin distinguir estación.
- `PATCH /orders/{id}/items/{item_id}` deja a `kitchen` marcar como preparada una bebida, y a
  `bartender` un plato de cocina.
- La estación de una línea solo se puede saber cruzando `dishes` y `categories` en el cliente
  (`StationBoard` + `stationOf`), por lo que el filtro es solo visual.

Para la profe, "cocina solo recibe entrantes y principales" no se cumple: el dato llega a
cocina y solo se oculta en pantalla.

## Solution
Aplicar la estación en el backend. La estación de una línea es la de la categoría de su
plato. `kitchen` solo ve y marca líneas de estación `kitchen`; `bartender`, las de `bar`;
`admin` y `waiter` lo ven todo. Lo mismo para el WebSocket. Cada línea del pedido expone su
`station`. "CRUD de bebidas y postres" no necesita endpoints nuevos: se hace con los CRUD
actuales de `/categories` y `/dishes` usando categorías de estación `bar`.

## User Stories
1. Como barra, quiero ver solo las bebidas y postres de cada pedido, para no distraerme con
   lo que prepara cocina.
2. Como cocina, quiero ver solo entrantes y principales, para que las bebidas no me llenen
   la pantalla.
3. Como barra o cocina, quiero que solo me lleguen en directo (WebSocket) los pedidos con
   líneas de mi estación.
4. Como admin, quiero crear categorías y platos de barra (bebidas, postres), para que se
   enruten a barra sin tocar código.
5. Como camarero, quiero seguir viendo el pedido completo de la mesa, con la estación de
   cada línea, para saber qué falta.

## Implementation Decisions
- **Modelo**: sin tablas ni columnas nuevas. La estación se deriva en vivo de
  `OrderItem.dish → Dish.category → Category.station`; si el admin cambia la estación de una
  categoría, las líneas ya creadas la siguen.
- **Migración de datos `0007`** (Alembic, solo datos): pone `station = 'bar'` en las categorías
  cuyo nombre, sin distinguir mayúsculas ni espacios sobrantes, es `Bebidas` o `Postres`
  (los nombres de la carta del equipo). Idempotente; no toca las demás ni crea categorías.
  `downgrade` no hace nada (no se puede saber qué estación tenía cada una). Es la única
  forma automática de ajustar Neon, así que el PR lo dice y se revisa en `dev` antes de `main`.
- **Endpoints afectados** (sin rutas nuevas):
  - `GET /orders`, `GET /orders/{id}`: para `kitchen` y `bartender` devuelven solo las
    líneas de su estación y omiten los pedidos sin ninguna. `admin` y `waiter`, todo. `total`
    es siempre el del pedido completo. Sin parámetro `?station=`: el filtro depende del rol.
  - `PATCH /orders/{id}/items/{item_id}`: `kitchen`/`bartender` solo sobre líneas de su
    estación; otra estación → 403. `admin` sin restricción.
  - `PATCH /orders/{id}/status`: `kitchen`/`bartender` solo sobre pedidos con líneas de su
    estación (si no, 404) y la respuesta trae solo esas líneas. Las transiciones no cambian.
  - `OrderItemOut` añade `station` (`kitchen` | `bar`).
  - `/ws/kitchen`: cada conexión guarda el rol del usuario y el evento le llega con las
    líneas de su estación; si no tiene ninguna, no se le envía. `admin` recibe todo.
- **Capas**: `schemas/schema_order.py` (campo `station`) → `routers/router_order.py` (pasa el
  usuario) → `services/order_service.py` (filtro y comprobación de estación) →
  `repositories/order_repository.py` (consulta con join a categoría) y
  `websocket/kitchen.py` (conexiones con su rol).
- **Regla nueva `R-14` (M)** en `specs/ontology.md`, en el mismo PR, con visto bueno de
  Levi: "La estación de una línea de pedido es la `station` de la categoría de su plato.
  `kitchen` ve y marca solo líneas `kitchen`; `bartender`, solo `bar`; `admin` y `waiter`,
  todas. Marcar una línea de otra estación → 403". `Station` entra en el glosario como valor
  de `Category.station`, no como entidad.
- **Errores**: 403 `{"detail", "code"}` al marcar una línea de otra estación; un pedido sin
  líneas de la estación del usuario → 404 en `GET /orders/{id}` (no se revela que existe).

## Testing Decisions
- Pedido mixto (plato de `kitchen` + bebida de `bar`): `kitchen` ve 1 línea, `bartender` ve 1
  línea, `waiter` y `admin` ven 2.
- Pedido solo de bebidas: no aparece en el listado de `kitchen`.
- `kitchen` marca una bebida → 403; `bartender` marca una bebida → 200.
- WebSocket: `bartender` recibe solo líneas `bar`; `kitchen`, solo `kitchen`.
- `total` de un pedido filtrado = total del pedido completo.
- Cambiar la `station` de una categoría con un pedido abierto cambia la estación de sus líneas.
- Migración `0007`: marca `Bebidas` y `postres ` (otra caja, con espacios), deja `Entrantes`
  y una categoría ya `bar`; segunda ejecución sin cambios (`tests/test_migrations.py`).
- Los tests actuales de pedidos, marcas y `test_bartender_role.py` siguen pasando.

## Criterios de aceptación
- [ ] `kitchen` solo recibe líneas de estación `kitchen`; `bartender`, solo `bar`.
- [ ] `admin` y `waiter` ven el pedido completo, con `station` en cada línea.
- [ ] Marcar preparada una línea de otra estación → 403 `{"detail", "code"}`.
- [ ] `/ws/kitchen` difunde a cada rol solo sus líneas.
- [ ] Una categoría `bar` nueva enruta sus platos a barra sin cambios de código.
- [ ] La migración `0007` deja `Bebidas` y `Postres` en `bar` y es idempotente.
- [ ] `R-14` añadida a `specs/ontology.md`.
- [ ] Tests (caso feliz + 4xx), lint limpio, `docs/api.md` actualizado (`station` en las
  líneas, filtro por rol, 403 nuevo, migración `0007`) y `docs/deploy.md` (lista de
  migraciones).

## Out of Scope
- UI de barra (HU-41, hecha) y gestión de la carta en la web.
- Estado por producto individual y por estación (HU-45, #89, Rita): el `status` del pedido
  sigue siendo único y lo mueven los mismos roles que hoy. Se avisa a Rita porque HU-45 toca
  el mismo router.
- Tabla `stations`, estación por plato o estación congelada en `order_items`: descartado.
- Un parámetro `?station=` y totales por estación.
- Crear categorías que no existan: la migración solo marca las que ya hay.

## Preguntas abiertas
Ninguna.

## Decisiones de la sesión
### Alcance: el backend aplica la estación
- **Decisión**: `kitchen` y `bartender` solo ven y marcan líneas de su estación en
  `GET /orders`, `GET /orders/{id}`, `PATCH .../items/{item_id}` y `/ws/kitchen`.
- **Por qué**: "cocina solo recibe entrantes y principales" (issue #83) y plan v3 §5.2; hoy
  solo se cumple visualmente en `StationBoard`.
- **Alternativas rechazadas**: solo carta y datos (el requisito sería solo visual);
  `?station=` opcional (sin garantía de que cocina no reciba bebidas).

### El `status` del pedido no cambia
- **Decisión**: se mantiene el estado único y sus transiciones y roles actuales.
- **Por qué**: el estado por producto/estación es HU-45 (#89, Rita) y toca el mismo router;
  mezclarlo aquí aumenta el PR y el riesgo de conflicto.
- **Alternativas rechazadas**: estado derivado por estación (modelo y migración nuevos);
  que solo cocina mueva el estado (cambia permisos ya cubiertos por tests).

### El filtro depende del rol, no de un parámetro
- **Decisión**: sin `?station=`; el rol del token fija la estación. `total` queda como el del
  pedido completo.
- **Por qué**: es la garantía que pide la issue y no cambia el contrato de lectura.
- **Alternativas rechazadas**: `total` parcial o `null` (totales distintos para un mismo
  pedido o cambio de schema).

### La estación se deriva en vivo
- **Decisión**: la estación de una línea sale siempre de la categoría actual del plato.
- **Por qué**: sin columna ni migración; coherente con la decisión del 13/10 (valor en la
  categoría, no en la línea).
- **Alternativas rechazadas**: congelarla al pedir (columna, migración y backfill en Neon).

### Producción: migración de datos `0007`
- **Decisión**: una migración Alembic marca `bar` las categorías `Bebidas` y `Postres`.
- **Por qué**: lo decide Manon: deja Neon listo en el deploy sin pasos manuales.
- **Riesgo aceptado**: si en Neon los nombres difieren, no marca nada y el admin lo corrige
  con `PUT /categories/{id}`; por eso es idempotente y por nombre exacto.
- **Alternativas rechazadas**: que el admin lo marque a mano; script manual en `app/scripts`.

### Regla R-14 en la ontología
- **Decisión**: se añade `R-14` (M) a `specs/ontology.md` en este PR.
- **Por qué**: las HU y el ai-log citan las reglas por id y la estación no estaba cubierta.
