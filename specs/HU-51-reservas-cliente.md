# HU-51 · Reservas hechas por el cliente

> Issue: #106 · Prioridad: Must · Escribe: Anna · Implementa:
> Manon (backend) y Anna (frontend) · Revisa: Rita · Aprueba: Levi (PO). Vocabulario:
> `specs/ontology.md`. Usa `specs/HU-TEMPLATE.md`. Parte de frontend: pantalla de reservas
> (Anna, issue por crear).

## Problem Statement
Un `customer` ya puede ver, editar y cancelar sus reservas, y `POST /reservations` le deja
crear una a su nombre. Pero exige `table_id`, y la única forma de saber qué mesa está libre
es `GET /tables/available`, que es solo para `admin` y `waiter` (`routers/tables.py`). En
la práctica el cliente no puede reservar: tendría que adivinar un id de mesa.

## Solution
Forma simplificada, acordada por todo el equipo: el cliente pide **día y hora, número de
personas y notas**, y el restaurante le asigna la mesa. `table_id` pasa a ser opcional en
`POST /reservations`: si no llega, el backend elige la mesa libre que mejor encaja (la
primera de `/tables/available`) y crea la reserva. Si no hay ninguna → 409. Un cliente no
puede reservar para **más de 8 personas**: el backend lo bloquea con un mensaje para que
llame al restaurante, y el frontend avisa antes de enviar. El personal sigue eligiendo mesa
a mano como hasta ahora.

## User Stories
1. Como cliente, quiero reservar indicando día, hora y personas, para no tener que saber
   qué mesas tiene el restaurante.
2. Como cliente, quiero un mensaje claro si no hay sitio a esa hora, para probar otra.
3. Como cliente con un grupo de más de 8 personas, quiero saber que tengo que llamar al
   restaurante, para no intentarlo una y otra vez.
4. Como cliente, quiero ver en "Mis reservas" la mesa que me han asignado y recibir el
   email de confirmación, igual que con una reserva hecha por el personal.
5. Como camarero o admin, quiero seguir eligiendo la mesa a mano y poder cambiarla
   después, para colocar a los clientes como mejor convenga.

## Implementation Decisions
- **Contrato**: `ReservationCreate.table_id` pasa a `int | None = None`. Con `table_id`
  todo funciona igual que hoy. Sin `table_id` el backend asigna la mesa, también para
  `admin` y `waiter`. La respuesta es la misma `ReservationRead`, con el `table_id`
  asignado. Sin cambios en el modelo ni migración de Alembic.
- **Asignación**: candidatas = `dining_table_repository.list_available_page` con
  `reserved_at`, `reserved_at + duration_min` y `party_size` (mesas con capacidad
  suficiente, no `out_of_service` y sin reservas activas solapadas, ordenadas por
  capacidad y número). Se toma la primera.
- **Concurrencia**: la mesa elegida se bloquea con `_get_table_for_update` y se repite
  `_ensure_no_overlap`, como hoy. Si otra petición la ha cogido entre medias, se prueba la
  siguiente candidata; si no queda ninguna → 409.
- **Sin mesa libre** → 409, `code` `no_table_available`, mensaje "No hay mesa libre para
  N personas el DD/MM/AAAA a las HH:MM".
- **Máximo de 8 personas por reserva del cliente**: constante `MAX_CUSTOMER_PARTY_SIZE = 8`
  en `schemas/reservation.py`. Si un `customer` crea o edita una reserva con `party_size`
  mayor que 8 → 422, `code` `party_size_too_large`, mensaje "Para reservas de más de 8
  personas, llama al restaurante". Se comprueba en el servicio, antes de buscar mesa, para
  devolver ese mensaje y no el error genérico de validación. `admin` y `waiter` no tienen
  este límite: los grupos grandes los gestiona el personal.
- **Permisos**: no cambian (`RESERVATIONS` = admin, waiter, customer). `/tables` y
  `/tables/available` siguen siendo solo del personal.
- **Email**: el de confirmación ya incluye el número de mesa; no cambia.
- **Capas**: `schemas/reservation.py` (campo opcional y constante) →
  `routers/reservations.py` (pasa al servicio si el usuario es `customer`) →
  `services/reservations.py` (`_assign_table`, el límite de 8, la fecha pasada y los errores) →
  `repositories/dining_table_repository.py` (`list_available_page`, sin cambios).
- **Código de otra persona**: el de reservas y mesas es de Levi (HU-10, HU-18). El cambio
  está acordado por todo el equipo; Manon avisa a Levi al abrir el PR.

## Testing Decisions
- Cliente sin `table_id` → 201 con la mesa más ajustada (p. ej., 2 personas con mesas de 2,
  4 y 6 → la de 2).
- Si la de 2 está reservada a esa hora → se asigna la de 4.
- Mesas `out_of_service` y reservas canceladas: no cuentan como ocupadas.
- Ninguna mesa libre → 409 `no_table_available`.
- Sin `table_id` y `reserved_at` en el pasado → 422 `reservation_in_past`; con `table_id`
  y fecha pasada sigue funcionando como hoy.
- Cliente con 9 personas → 422 `party_size_too_large` al crear y al editar; con 8 → pasa.
- `admin` o `waiter` con 9 personas y una mesa con sitio → 201.
- Con `table_id` → todos los tests actuales de HU-10 siguen pasando sin cambios.
- `admin` sin `table_id` también recibe mesa asignada.
- La reserva creada aparece en `GET /reservations` del cliente.
- Se envía el email de confirmación.
- Concurrencia: se prueba la lógica de "siguiente candidata" con la mesa elegida forzada
  a ocupada; la carrera real con dos conexiones no se prueba.

## Criterios de aceptación
- [x] Un `customer` crea una reserva con `reserved_at`, `party_size` y `notes`, sin
  `table_id`, y recibe 201 con la mesa asignada.
- [x] La mesa asignada es la más pequeña con sitio que está libre en ese hueco.
- [x] Sin mesa libre → 409 `no_table_available`.
- [x] Un `customer` con más de 8 personas → 422 `party_size_too_large` con el mensaje
  "Para reservas de más de 8 personas, llama al restaurante".
- [x] Sin `table_id` y con fecha pasada → 422 `reservation_in_past`.
- [x] Los errores usan el formato estándar `{"detail", "code"}`.
- [x] Las reservas con `table_id` funcionan igual que antes y los tests de HU-10 pasan.
- [x] `/tables/available` sigue cerrado al `customer`.
- [x] `docs/api.md` documenta el `table_id` opcional, el límite de 8 y los tres errores
  nuevos.

## Out of Scope
- La UI del cliente, que hace Anna en el frontend: "+ Nueva reserva" con día, hora,
  personas y notas. Si el cliente pone más de 8 personas, aparece el aviso "Para reservas
  de más de 8 personas, llama al restaurante" y no se envía; si el backend devuelve
  `party_size_too_large`, se muestra su mensaje.
- Que el estado de la mesa (libre, ocupada, reservada) cambie solo con pedidos y reservas:
  tarea aparte. Propuesta: calcularlo en la pantalla Mesas del frontend para esta entrega
  y llevarlo al backend en el siguiente sprint.
- Juntar mesas para grupos grandes.
- Reasignar la mesa automáticamente al editar una reserva (`PATCH` sigue como hoy, salvo
  el límite de 8 para el cliente).
- Horario de apertura y antelación mínima o máxima para reservar.
- Un aforo global del restaurante: lo marcan las mesas.

## Preguntas abiertas
Ninguna: resueltas el 15/10/2026 (ver "Decisiones de la sesión").

## Decisiones de la sesión
Acordado por todo el equipo, Levi (PO) incluido, el 15/10/2026:
- **Forma simplificada: el cliente no elige mesa; el backend la asigna** → menos campos
  para el cliente, no ve datos internos y es como funciona un restaurante. Rechazado: abrir
  `/tables/available` al `customer` (expone las mesas y obliga a una pantalla de elección).
- **Reparto**: backend, Manon; frontend, Anna.
- **Ampliar `POST /reservations` en lugar de crear un endpoint nuevo** → reutiliza
  permisos, validaciones y el email de confirmación. Rechazado: `POST /reservations/request`.
- **Máximo fijo de 8 personas por reserva del cliente, bloqueado en el backend y avisado en
  el frontend** → regla simple que el cliente entiende y que no depende de las mesas que
  haya. Rechazado: límite según la mesa más grande; aforo global `MAX_CAPACITY`.
- **Mejor encaje = la mesa más pequeña con sitio** → mismo orden que `/tables/available`;
  deja libres las mesas grandes.

Resueltas con Manon el 15/10/2026 (preguntas que estaban abiertas en la spec):
- **El `customer` puede seguir enviando `table_id`** → no rompe el contrato ni los tests de
  HU-10; la web del cliente no lo envía. Con `table_id` el flujo es el de siempre.
- **Reserva en el pasado** → 422, `code` `reservation_in_past`, solo cuando la mesa se
  asigna automáticamente (sin `table_id`). El flujo del personal con `table_id` no cambia.
  Se añade a los tests y a los criterios de aceptación.
- **Prioridad: Must** → sin esto el cliente no puede reservar en la práctica.
- **Zona horaria de `reservation_in_past`** → `reserved_at` es la hora del reloj del
  restaurante (el frontend envía y muestra hora local sin zona), así que se compara con
  la hora actual en `RESTAURANT_TIMEZONE` (por defecto `Europe/Madrid`) y no con UTC.
  Propuesto por Anna el 16/10/2026. Añade la dependencia `tzdata` (la imagen
  `python:3.12-slim` no trae la base de zonas horarias).
