# HU-27 · Colección Bruno para pruebas de la API

> Issue: #70 · Prioridad Must · Nivel Entregable · Escribe: Levi ·
> Revisa: quien la vea primero · Aprueba: Levi (PO). Vocabulario: `specs/ontology.md`.
> Reglas del repo: `AGENTS.md`.

## Problem Statement
La API de RestoAPI expone 48 endpoints HTTP sobre FastAPI, con roles
(`admin`, `waiter`, `kitchen`, `bartender`, `customer`), JWT, refresh tokens,
permisos por estación, facturación, stats y export CSV. No existe una forma
**versionada, reproducible y compartida** de probar la API de punta a punta:
cada persona del equipo prueba a mano con `curl` o Swagger, y cada PR depende
de que quien revisa sepa qué flujo ejercitar.

Sin una colección de pruebas común:
- Los PR de otras HUs se revisan sin un contrato ejecutable previo.
- El frontend adivina payloads y códigos de error.
- El onboarding de nuevas personas (Manon, futuras incorporaciones) es lento.
- No hay una verificación end-to-end reproducible antes del merge.

## Solution
Una **colección Bruno** versionada en `bruno/` (formato abierto, basado en
archivos `.bru` de texto plano) que:

1. Cubre los endpoints HTTP que hoy existen en `app/routers/*.py` (44 de 48),
   salvo los que quedan fuera según "Alcance acotado a lo existente".
2. Documenta el flujo completo por roles: login admin → alta de usuarios por
   rol → login por rol → CRUD de menú/mesas/reservas/pedidos → factura →
   stats/export → limpieza → desactivación.
3. Incluye **casos de error y seguridad** por endpoint: 401, 403, 404, 409, 422.
4. Tiene entornos `Local` y `Production` con `baseUrl` y credenciales como
   variables secretas (nunca hardcodeadas en `.bru`).
5. Se ejecuta de dos formas:
   - **Bruno app**: manual, explorable por dominio.
   - **Bruno CLI** (`npx @usebruno/cli`): Collection Runner automatizado para
     verificación end-to-end antes del merge.
6. Documenta los **WebSocket** (cocina/barra) como request manual fuera del
   runner: Bruno no es una herramienta WS de primera clase y la verificación
   real de WS ya vive en `tests/integration/test_kitchen_websocket.py`.

La colección **solo documenta lo que existe hoy**. Los endpoints futuros se
añadirán en la PR de su propia HU.

## Desarrollo Agéntico con Agent Teams

Esta HU se desarrolla siguiendo el flujo SDD definido en `AGENTS.md` y el
briefing del proyecto: **spec → agente → PR → revisión**. Para esta tarea
concreta, se utiliza **Agent Teams** de Claude Code, con un **agente líder**
que orquesta y **agentes especialistas** que ejecutan tareas únicas y
bien delimitadas.

### Cómo se activa el equipo

1. Se habilita el flag experimental de agent teams en Claude Code.
2. Se invoca al agente líder con la instrucción de crear el equipo.
3. El líder lee `docs/agents/HU-27/lead.md` y reparte las tareas según los
   archivos `agent-*.md`.
4. Los agentes especialistas trabajan **en paralelo**, cada uno en su
   carpeta de dominio dentro de `bruno/`, sin solapamiento de archivos.
5. El líder verifica que cada especialista entrega lo pactado y consolida.

### Agentes y tareas

| Agente | Archivo de directriz | Tarea única | Archivos que posee |
|---|---|---|---|
| **Lead** | `docs/agents/HU-27/lead.md` | Orquestar, verificar, consolidar, abrir PR | Ninguno (solo lectura + coordinación) |
| **Auth & Users** | `docs/agents/HU-27/agent-auth.md` | Revisar/crear `.bru` de `01-auth/` y `02-users/` | `bruno/01-auth/`, `bruno/02-users/` |
| **Menus & Tables** | `docs/agents/HU-27/agent-menus.md` | Revisar/crear `.bru` de `03-categories/`, `04-dishes/`, `05-tables/` | `bruno/03-categories/`, `bruno/04-dishes/`, `bruno/05-tables/` |
| **Orders & Invoices** | `docs/agents/HU-27/agent-orders.md` | Revisar/crear `.bru` de `07-orders/` y `08-invoices/` | `bruno/07-orders/`, `bruno/08-invoices/` |
| **Reservations** | `docs/agents/HU-27/agent-reservations.md` | Revisar/crear `.bru` de `06-reservations/` | `bruno/06-reservations/` |
| **Stats, Export & Cleanup** | `docs/agents/HU-27/agent-cleanup.md` | Revisar/crear `.bru` de `09-stats/`, `10-exports/`, `11-cleanup/` | `bruno/09-stats/`, `bruno/10-exports/`, `bruno/11-cleanup/` |

*Nota: El agente Lead no escribe archivos `.bru`; solo coordina, verifica y
consolida. Los especialistas escriben únicamente en las carpetas que
poseen.*

### Reglas para los agentes especialistas

Cada agente especialista debe:
1. Leer primero `AGENTS.md`, luego `specs/ontology.md`, luego su archivo
   `docs/agents/HU-27/agent-*.md`.
2. Trabajar **únicamente** en las carpetas de `bruno/` que se le asignan.
3. No tocar código de `app/`, `tests/`, migraciones, CI ni configuración de
   despliegue.
4. No inventar endpoints ni campos que no existan en los schemas reales.
5. Seguir el estilo de los `.bru` existentes (meta, request, body,
   script:post-response, tests).
6. Reportar al líder al terminar, indicando archivos modificados y cualquier
   duda.

### Reglas para el agente líder

El agente líder debe:
1. Leer `docs/agents/HU-27/lead.md` antes de hacer nada.
2. Crear el equipo de agentes especialistas.
3. Asignar tareas según la tabla de arriba.
4. Verificar que cada especialista entrega lo pactado.
5. Si hay conflictos o dudas, resolverlos o escalar a Levi.
6. Consolidar los cambios y preparar la rama para la PR.
7. No escribir archivos `.bru` directamente; solo coordinar.

## User Stories
1. Como desarrolladora, quiero probar cualquier endpoint sin escribir `curl`,
   para iterar rápido con una interfaz gráfica (Bruno app).
2. Como revisora de PR, quiero ejecutar la colección completa con un comando,
   para verificar que la API sigue funcionando antes de aprobar.
3. Como frontend, quiero ver en cada request el body real y la respuesta
   esperada, para integrarme sin leer el código del backend.
4. Como Tech Lead, quiero que los casos de error (401, 403, 404, 409, 422)
   estén cubiertos, para que el contrato de la API quede documentado.
5. Como equipo, quiero que la colección viva en Git junto al código, para
   que las PR puedan modificarla cuando cambie el contrato.
6. Como agente de IA en futuras HUs, quiero leer `bruno/README.md` y la
   estructura de `bruno/`, para no inventar endpoints ni campos.
7. Como PO, quiero que la colección no toque `app/` ni tests ni CI, para
   no arriesgar el trabajo de otras HUs.
8. Como equipo, quiero que las credenciales del admin viajen como variables
   secretas, para no commitear secretos.
9. Como agente líder, quiero directrices claras sobre cómo orquestar el
   equipo, para no solaparme con los especialistas ni generar conflictos.
10. Como agente especialista, quiero una tarea única y acotada a un conjunto
    de carpetas, para no pisar el trabajo de otro agente.

## Implementation Decisions
- **Formato**: Bruno (no Postman) porque:
  - Los `.bru` son archivos de texto plano versionables en Git con diffs
    legibles (frente al JSON monolítico de Postman).
  - No requiere cuenta ni licencia para uso individual o de equipo pequeño.
  - Coherente con `AGENTS.md` ("no subir secretos; solo `.env.example`") y
    con la filosofía del repo (`specs/`, `docs/` versionados).
- **Estructura**: `bruno/<NN-dominio>/<NN-nombre>.bru`. Los prefijos numéricos
  indican el orden de ejecución. Dominios según `app/routers/*.py`:
  - `00-health`, `01-auth`, `02-users`, `03-categories`, `04-dishes`,
    `05-tables`, `06-reservations`, `07-orders`, `08-invoices`, `09-stats`,
    `10-exports`, `11-cleanup`.
- **Entornos**: `environments/Local.bru` (`http://localhost:8000`) y
  `environments/Production.bru` (`https://restoapi-47sp.onrender.com`).
  `adminEmail` y `adminPassword` son variables secretas, definidas por quien
  ejecuta (nunca en el repo). Se documenta en `bruno/README.md`.
- **Variables encadenadas**: cada request protegido usa `{{token}}`. Los
  `script:post-response` guardan `token`, `refreshToken` (si aplica) e IDs
  creados (`userId`, `orderId`, `dishId`, `tableId`, `reservationId`,
  `invoiceId`) para el siguiente request del flujo.
- **Tests en cada request**: al menos un assert de status y uno de shape del
  response (campos obligatorios del schema). Se verifica también que
  `password` / `password_hash` **no aparecen nunca** en las respuestas de
  usuario (`R-02` de `specs/ontology.md`).
- **Alcance acotado a lo existente**:
  - Existen en `app/routers/` pero quedan fuera (se añadirán en la PR de su
    HU), decidido por Levi (PO) el 15/10/2026:
    - `POST /auth/register` (HU-22).
    - `POST /auth/social/{provider}` (HU-38): necesita un `code` OAuth real de
      Google o GitHub y no se puede automatizar en el runner tal cual.
    - `DELETE /users/{user_id}` (soft delete) y `POST /users/{user_id}/restore`
      (HU-32).
  - Llegaron a `dev` después de la verificación del 15/10 y entran en esta
    PR por decisión de Levi (PO) del 16/10/2026: `PATCH /users/me` y
    `POST /users/me/password` (HU-25).
  - También llegaron después y ya están cubiertos: la paginación `Page` de
    `GET /users` (HU-24; los filtros `role`, `is_active` y `q` no se prueban)
    y el filtro por estación de HU-40 (R-14: el pedido lleva una línea de
    cocina y otra de barra, y `kitchen` y `bartender` solo ven la suya).
  - Aún no existen: refresh/logout (HU-30).
  - Comportamiento actual documentado, aunque no sea el ideal:
    - HU-43: un `customer` puede crear reservas para sí mismo (201); el 403
      solo salta si apunta a otro `user_id`.
    - HU-08: el 409 de factura es **por pedido** (`invoice_already_exists`,
      `order_not_served`), no por mesa.
- **WebSocket**: `/ws/kitchen` no tiene `.bru` y queda fuera del runner. La
  sección 8 de `bruno/README.md` explica cómo probarlo a mano (`websocat`,
  `wscat` o Bruno) y enlaza a los tests de WS existentes.
- **No toca código ni configuración**: ni `app/`, ni `tests/`, ni
  `migrations/`, ni `.github/workflows/`, ni `requirements.txt`, ni
  `Dockerfile`, ni `render.yaml`, ni `.env`. Fuera de `bruno/` solo se
  permiten los ficheros de la excepción de los criterios de aceptación.

## Testing Decisions
- La colección **es el propio test**: su valor se mide por lo que se ejecuta,
  no por lo que documenta.
- **Punto de prueba único (seam)**: el Collection Runner de Bruno CLI
  (`npx @usebruno/cli run -r --env Local ...`).
- **Criterio de verde**: 141/141 requests en local con la API levantada y el
  admin creado vía `python -m app.scripts.create_admin`.
- **Orden de preparación en local**: primero levantar la API (`docker compose
  up -d --build db api`) para que Alembic cree el esquema y después crear el
  admin (`docker compose exec api python -m app.scripts.create_admin ...`).
  `create_admin` llama a `Base.metadata.create_all`: si se ejecuta antes con la
  BD vacía, crea las tablas sin `alembic_version` y el contenedor `api` cae
  con `DuplicateTable` al arrancar.
- No se ejecuta la colección en CI en esta HU (no hay GH Action que ejecute
  Bruno en este momento). Si en el futuro se añade, será en una PR aparte
  (HU-36 es de otro tipo).
- La colección **no duplica** los tests de `tests/`: los complementa. Los
  tests de pytest siguen siendo el contrato automatizado; Bruno es la
  verificación manual reproducible end-to-end.

## Criterios de aceptación
- [x] `bruno/bruno.json` válido y la colección se importa en Bruno sin errores.
- [x] Entornos `Local` y `Production` con `baseUrl` correcto.
- [x] Todos los endpoints HTTP actuales de `app/routers/*.py` cubiertos por
      al menos un request, salvo los 4 sin cubrir de "Alcance acotado a lo
      existente" (44 de 48).
- [x] Flujo `login admin → alta usuarios por rol → login por rol → CRUD →
      factura → stats → cleanup → desactivación (401)` completo.
- [x] Casos de error 401, 403, 404, 409 y 422 presentes donde la API los
      devuelva.
- [ ] Tests en cada request: status, shape del schema y ausencia de
      `password` / `password_hash` en respuestas de usuario.
- [ ] `bruno/README.md` explica instalación de Bruno, importar, elegir
      entorno, configurar `adminEmail`/`adminPassword` como secretos, orden
      de ejecución, Collection Runner (app y CLI), WebSocket manual y tabla
      de cobertura.
- [x] **141/141 requests en verde** en local con la API levantada y el admin
      creado.
  > Verificado el 15/10/2026 con Docker Compose y la BD migrada con Alembic
  > hasta `0006`: 130/130 requests y 332/332 tests, antes y después de
  > integrar `dev` (HU-32, HU-38).
  >
  > Verificado de nuevo el 16/10/2026 tras rebasar sobre `dev` (HU-24, HU-25,
  > HU-40; BD migrada hasta `0007`): 132/132 requests y 339/339 tests. Con los
  > requests de `/users/me` (HU-25): 141/141 requests y 361/361 tests.
- [x] Ninguna credencial real ni token hardcodeado en el repo.
- [ ] El diff de la PR contra `dev` solo muestra cambios dentro de `bruno/`,
      `docs/agents/HU-27/`, `scripts/generate_agent_diagrams.py`,
      `docs/agents/HU-27/`, este fichero y la sección HU-27 de
      `docs/ai-log.md`.
  > Excepción aprobada por Levi (PO) el 14/10/2026 para incluir
  > la documentación visual y las directrices de agentes de esta HU.
  > `docs/ai-log.md` va en la misma PR porque lo exige `AGENTS.md`
  > ("Registro de IA").
  > Excepción pedida por Levi (PO) el 16/10/2026 tras la revisión de Ana:
  > `.dockerignore` excluye `bruno/` y `scripts/generate_agent_diagrams.py`
  > de la imagen Docker (solo añade dos líneas; no cambia el código que corre).
- [ ] PR revisada por otra persona y aprobada por Levi (PO).
- [ ] Los archivos `docs/agents/HU-27/*.md` existen y describen las tareas
      de cada agente de forma clara y sin solapamiento.

## Out of Scope
- Modificar `app/`, `tests/`, migraciones, CI ni configuración de despliegue.
- Añadir endpoints que no existen hoy (se añaden en la PR de su HU).
- Colección Postman (se elige Bruno; Postman se descarta según la
  justificación de `Implementation Decisions`).
- Integración de Bruno en GitHub Actions (queda para otra PR).
- Pruebas de rendimiento o carga (fuera del alcance de HU-27).
- Swagger enriquecido (tags, ejemplos, Authorize): es HU-26 (Rita), no HU-27.

> Actualización 14/10: HU-06 mergeó station en categorías, así
> que la colección Bruno lo cubre. HU-40 (estación de barra en
> pedidos) sigue fuera de alcance.
>
> Actualización 15/10: al integrar `dev` llegan HU-32 (`DELETE
> /users/{id}` y `POST /users/{id}/restore`) y HU-38 (`POST
> /auth/social/{provider}`). Quedan fuera de HU-27 por decisión de
> Levi (PO); la colección sigue en 130/130 sin cambios en los `.bru`.
>
> Actualización 16/10: tras rebasar sobre `dev` (HU-24, HU-25, HU-40) la
> colección daba 128/130. Se adapta `02-users/09-list-users` a `Page[UserOut]`
> y el pedido de `07-orders` lleva una línea de barra (categoría y plato
> nuevos en `03-categories/11` y `04-dishes/12`) para probar R-14: 132/132.
> Después, por decisión de Levi (PO), se añaden `PATCH /users/me` y
> `POST /users/me/password` (HU-25): 9 requests en `02-users/17` a `25`.
> Colección final: 141/141.

## Further Notes
- Referencias:
  - `AGENTS.md` — reglas del repo, stack, estructura, "no hagas".
  - `specs/ontology.md` — vocabulario, roles, reglas `R-01`…`R-13`.
  - `docs/api.md` — documentación funcional de la API.
  - `docs/deploy.md` — despliegue y entornos (Local, Production).
  - Swagger: https://restoapi-47sp.onrender.com/docs
  - `docs/agents/HU-27/lead.md` — directriz del agente líder.
  - `docs/agents/HU-27/agent-*.md` — directrices de los agentes especialistas.
- Alineado con `R-02` (no exponer `password_hash`), `R-03` (roles y creación
  de cuentas), `R-04` (desactivación lógica) y `R-05`/`R-06`/`R-07` (par de
  tokens) en la medida en que el código actual los implementa.
- Este fichero **no sustituye** a `AGENTS.md`: lo complementa para la HU-27.
  Cualquier agente que trabaje en esta rama debe leer primero `AGENTS.md` y
  luego este fichero.
- Cuando una HU añada o ya tenga endpoints sin cubrir (HU-22, HU-24, HU-25,
  HU-30, HU-32, HU-38, HU-40, etc.), su PR deberá:
  1. Añadir el `.bru` correspondiente en la carpeta del dominio.
  2. Actualizar la tabla de cobertura de `bruno/README.md`.
  3. Actualizar este fichero si la lista de "Out of Scope" cambia.
- Mantenedor de este fichero: Levi (PO / Dev QA).