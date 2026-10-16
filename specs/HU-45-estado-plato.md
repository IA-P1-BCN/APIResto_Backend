# HU-45 · Estado de plato

> Issue: #89 · Prioridad Must · Escribe: Rita · Revisa: la primera persona que la vea ·
> Aprueba: quien revisa (acuerdo del 14/10). Vocabulario: `specs/ontology.md`. Usa
> `specs/HU-TEMPLATE.md`.

## Problem Statement
La issue dice: "Como camarero quiero marcar cada plato como servido y ver estados más
detallados del pedido para saber qué falta en cada mesa". No traía criterios de aceptación.

La primera mitad ya existe. La tarea #117 (Anna) añadió `prepared_quantity` y
`served_quantity` a `order_items` (migración `0006`) y `PATCH /orders/{id}/items/{item_id}`
permite al camarero marcar unidades servidas. HU-40 (Manon) añadió `station` a cada línea y
el filtro por estación (R-14).

Lo que falta es la segunda mitad. El pedido solo tiene su `status` (`pending`, `in_kitchen`,
`served`, `paid`, `cancelled`), que se mueve a mano y no dice qué hay listo para llevar a la
mesa. Para saberlo, el camarero tiene que recorrer las líneas y restar unidades una a una, y
no ve de un vistazo si lo que falta es de cocina o de barra.

## Solution
Añadir a la respuesta de los pedidos un resumen calculado, sin tocar el modelo:

- Cada línea trae `ready_to_serve`: unidades preparadas que aún no se han servido.
- Cada pedido trae `progress`: unidades totales, preparadas, servidas y listas para servir,
  un `stage` que resume en qué punto está y `by_station` con lo mismo para cocina y barra.

## User Stories
1. Como camarero, quiero ver qué unidades están listas para llevar a cada mesa, para no
   tener que preguntar a cocina ni a barra.
2. Como camarero, quiero ver el progreso de cocina y de barra por separado en cada pedido,
   para saber de dónde viene lo que falta.
3. Como camarero, quiero un estado resumido del pedido (esperando, en preparación, listo
   para servir, todo servido), para priorizar mesas.
4. Como cocina o barra, quiero ver el progreso de mis líneas, sin las de la otra estación.
5. Como admin, quiero ver lo mismo que el camarero.

## Implementation Decisions
- **Modelo**: sin tablas ni columnas nuevas y sin migración. Todo se calcula al responder a
  partir de `quantity`, `prepared_quantity` y `served_quantity` de cada línea.
- **Línea** (`OrderItemOut`): campo nuevo `ready_to_serve = max(prepared_quantity -
  served_quantity, 0)`. Nunca es negativo, aunque hoy se puede servir sin haber preparado
  (ver decisión "Servir sin preparar").
- **Pedido** (`OrderOut`): campo nuevo `progress` (schema `OrderProgress`):

  | Campo | Valor |
  |---|---|
  | `quantity` | suma de `quantity` de las líneas |
  | `prepared_quantity` | suma de `prepared_quantity` |
  | `served_quantity` | suma de `served_quantity` |
  | `ready_to_serve` | suma de `ready_to_serve` de las líneas (no la resta de los totales) |
  | `stage` | ver tabla siguiente |
  | `by_station` | objeto con una entrada por estación presente (`kitchen`, `bar`), cada una con los cinco campos anteriores (schema `StationProgress`) |

- **`stage`**, evaluado en este orden (gana la primera condición que se cumpla):

  | `stage` | Condición |
  |---|---|
  | `all_served` | `quantity > 0` y `served_quantity == quantity` (un pedido sin líneas queda `waiting`) |
  | `ready_to_serve` | `ready_to_serve > 0` |
  | `waiting` | `prepared_quantity == 0` y `served_quantity == 0` |
  | `preparing` | cualquier otro caso (algo hecho, nada pendiente de llevar) |

- **Estación (R-14)**: `progress` se calcula sobre las líneas que trae la respuesta. `admin`
  y `waiter` reciben el pedido completo, así que ven el total y `by_station` con `kitchen` y
  `bar`. `kitchen` y `bartender` solo reciben sus líneas, así que ven su progreso y una sola
  entrada en `by_station`. No hace falta código nuevo para esto: `_view` ya filtra las
  líneas antes de serializar.
- **Endpoints afectados** (sin rutas, códigos ni permisos nuevos): todas las respuestas con
  `OrderOut`: `POST /orders/`, `GET /orders/`, `GET /orders/{id}`,
  `PATCH /orders/{id}/status` y `PATCH /orders/{id}/items/{item_id}`.
- **Pedidos cerrados**: `paid` y `cancelled` traen `progress` igual que los demás.
- **`status` del pedido**: no cambia. Sus transiciones, quién lo mueve, las facturas y el
  CSV siguen igual.
- **Capas**: solo `schemas/schema_order.py` (`StationProgress`, `OrderProgress`, campos
  calculados). Sin cambios en routers, services, repositories ni models.
- **Regla nueva `R-16` (M)** en `specs/ontology.md`, en el mismo PR.
- **Contrato**: solo se añaden campos de salida; no es `breaking-api`. Se documenta en
  `docs/api.md`.

## Testing Decisions
- Línea: `ready_to_serve` con 0 preparadas, con preparadas sin servir, con todo servido y
  con más servidas que preparadas (da 0).
- Pedido: un caso por cada `stage`, incluido el empate de orden (algo servido y algo listo
  → `ready_to_serve`).
- Pedido mixto (plato de `kitchen` + bebida de `bar`): `waiter` y `admin` ven el total y las
  dos entradas de `by_station`; `kitchen` ve solo `kitchen` y `bartender` solo `bar`, con
  sus sumas.
- `progress` aparece en `POST /orders/`, `GET /orders/`, `GET /orders/{id}` y en los dos
  `PATCH`, y cambia tras marcar unidades.
- Los 401, 403 y 404 actuales de pedidos siguen igual (no se tocan permisos).
- Los tests actuales de pedidos, marcas, unidades, estaciones y facturas siguen pasando sin
  cambios.

## Criterios de aceptación
- [ ] El camarero marca como servida cada línea o cada unidad con
  `PATCH /orders/{id}/items/{item_id}` (ya existe; se cubre con tests).
- [ ] Cada línea trae `ready_to_serve`, que nunca es negativo.
- [ ] Cada pedido trae `progress` con `quantity`, `prepared_quantity`, `served_quantity`,
  `ready_to_serve`, `stage` y `by_station`, en todas las respuestas con `OrderOut`.
- [ ] `stage` vale `waiting`, `preparing`, `ready_to_serve` o `all_served` según la tabla de
  esta spec.
- [ ] `by_station` desglosa el progreso por estación (`kitchen`, `bar`) con su propio
  `stage`; solo aparecen las estaciones que tiene el pedido.
- [ ] `admin` y `waiter` ven el total y las dos estaciones; `kitchen` y `bartender` solo la
  suya (R-14).
- [ ] Sin cambios de modelo ni migración.
- [ ] El `status` del pedido, sus transiciones, las facturas y el CSV no cambian.
- [ ] `R-16` añadida a `specs/ontology.md`.
- [ ] Tests (caso feliz + 4xx), ruff limpio, `docs/api.md` actualizado y entrada en
  `docs/ai-log.md`.

## Out of Scope
- Impedir servir más unidades de las preparadas (acordado con Anna el 16/10; ver
  decisiones).
- Cambiar el `status` del pedido automáticamente cuando todo está servido.
- Avisos en directo al camarero: `/ws/kitchen` solo admite `admin`, `kitchen` y
  `bartender`, y `PATCH .../items/{item_id}` no emite eventos.
- Filtro `?stage=` en `GET /orders/`.
- Pantalla de sala en el frontend (issue aparte en Resto-API_Frontend).

## Preguntas abiertas
Ninguna.

## Decisiones de la sesión
### Alcance: resumen calculado, sin modelo
- **Decisión**: `ready_to_serve` por línea y `progress` por pedido, calculados al
  responder.
- **Por qué**: marcar unidades servidas ya existe (#117); lo que falta es leer el estado.
  Sin migración, la PR es pequeña y no choca con nadie a 3 días de la entrega.
- **Alternativas rechazadas**: columna `status` por línea (modelo, migración y backfill en
  Neon); nuevos valores del `status` del pedido (cambia transiciones y tests ya cubiertos).

### Servir sin preparar
- **Decisión**: se sigue permitiendo marcar unidades servidas sin haberlas preparado.
  `ready_to_serve` se queda en 0 en ese caso.
- **Por qué**: prohibirlo cambiaría el código y los tests de Anna
  (`test_order_items_marks.py`) y quizá el frontend. Anna dio el visto bueno en Discord el
  16/10.
- **Alternativas rechazadas**: 409 si `served_quantity > prepared_quantity`.

### Progreso por estación para sala
- **Decisión**: `progress.by_station` con `kitchen` y `bar`; `admin` y `waiter` ven las dos.
- **Por qué**: lo pide Rita, para que sala sepa si lo que falta es de cocina o de barra.
- **Alternativas rechazadas**: solo el total del pedido.

### El progreso sigue a R-14
- **Decisión**: `progress` se calcula sobre las líneas de la respuesta, así que cocina y
  barra ven el suyo.
- **Por qué**: coherente con R-14 (no ven las líneas de la otra estación) y sin código
  extra.
- **Alternativas rechazadas**: progreso del pedido completo para todos (le daría a cocina
  datos de barra que R-14 le oculta).

### El `status` del pedido no cambia
- **Decisión**: ni transición automática ni bloqueo al marcar `served` con unidades
  pendientes.
- **Por qué**: cambia comportamiento que usan facturas (solo pedidos `served`) y tests
  actuales.
- **Alternativas rechazadas**: pasar a `served` solo cuando `stage` sea `all_served`.

### Regla R-16 en la ontología
- **Decisión**: se añade `R-16` (M) a `specs/ontology.md` en este PR.
- **Por qué**: las HU y el ai-log citan las reglas por id y el progreso no estaba cubierto.

### La regla pasa de R-15 a R-16
- **Decisión** (Rita, 16/10): la regla del progreso del pedido es `R-16`.
- **Por qué**: HU-33 (Levi, #145, ya en `dev`) usa `R-15` para la verificación de email en su
  spec, en el código y en `docs/api.md`. Su PR ya está integrada; renumerar la de HU-45 toca
  menos archivos y no cambia código ajeno.
- **Alternativas rechazadas**: que HU-33 pase a `R-16` (cambiaría el código de Levi ya
  integrado).
