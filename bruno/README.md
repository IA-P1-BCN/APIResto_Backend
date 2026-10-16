# Colección Bruno de RestoAPI (HU-27)

Colección de pruebas de la API REST de RestoAPI para [Bruno](https://www.usebruno.com/).
Cubre **44 de los 48 endpoints HTTP** de `app/routers/*.py` (más `/` y `/health` de `app/main.py`)
con **141 requests**: el flujo completo de punta a punta y los casos de error y seguridad
(401, 403, 404, 409 y 422).

> Quedan fuera 4 endpoints (ver sección 9): `POST /auth/register` (HU-22),
> `POST /auth/social/{provider}` (HU-38), `DELETE /users/{user_id}` y
> `POST /users/{user_id}/restore` (HU-32).
> El WebSocket de cocina (`/ws/kitchen`) tampoco está en el runner (sección 8).

- Documentación de la API: [`docs/api.md`](../docs/api.md)
- Swagger: <https://restoapi-47sp.onrender.com/docs> (en local: <http://localhost:8000/docs>)

---

## 1. Qué es Bruno y por qué Bruno y no Postman

Bruno es un cliente de APIs de código abierto, como Postman o Insomnia. Lo hemos elegido porque:

| | Bruno | Postman |
|---|---|---|
| Formato | Archivos de texto `.bru`, uno por request, dentro del repo | JSON exportado o colección en la nube |
| Git | Diffs legibles: cada cambio de un request se revisa en la PR como el código | Un JSON enorme que cambia entero al exportar |
| Cuenta | No hace falta | Hace falta para sincronizar y colaborar |
| Precio | Gratis y open source (MIT) | Gratis con límites; colaboración de pago |
| Secretos | Variables secretas guardadas solo en tu equipo | Se sincronizan con la nube si no tienes cuidado |

Encaja con nuestro flujo: la colección vive en `bruno/`, se versiona con la API y se revisa en cada PR.

## 2. Instalar Bruno

- **App de escritorio:** descárgala en <https://www.usebruno.com/downloads> (Windows, macOS y Linux),
  o con `winget install Bruno.Bruno` / `brew install bruno`.
- **CLI** (para el runner desde la terminal; necesita Node.js 18 o superior): no hace falta instalarlo,
  se usa con `npx @usebruno/cli`.

## 3. Pre-requisitos

1. **API levantada en local** (desde la raíz del repo, con el `.venv` activo y el `.env` configurado
   según el README principal):

   ```bash
   uvicorn app.main:app --reload
   ```

   O con Docker: `docker compose up`.

2. **Crear el admin una vez.** Sin un admin no se puede usar `/users` y el flujo no arranca:

   ```bash
   python -m app.scripts.create_admin EMAIL PASSWORD "Nombre"
   # con Docker:
   docker compose exec api python -m app.scripts.create_admin EMAIL PASSWORD "Nombre"
   ```

   Si el email ya existe, el script lo convierte en admin.

   Usa un email con dominio normal (p. ej. `@example.com`). Los dominios reservados (`.test`,
   `.local`, `.localhost`…) no pasan la validación `EmailStr`: `GET /auth/me` del admin daría 500 y
   el alta de usuarios, 422. Por eso los usuarios de prueba usan `@restoapi.example.com`.

3. **Guardar las credenciales del admin en Bruno**, nunca en un `.bru` commiteado. En la app:
   selector de entorno (arriba a la derecha) → **Configure** → entorno **Local** → rellena
   `adminEmail` y `adminPassword` → **Save**. Las dos son variables **secretas** (`vars:secret`):
   Bruno guarda su valor en tu equipo y en el archivo del entorno solo queda el nombre. Con el CLI se
   pasan con `--env-var` (ver sección 7).

4. **Production es de solo lectura:** el flujo crearía datos reales en la BD de Neon y algunos
   (mesas en uso, pedidos, facturas, usuarios desactivados) **no se pueden borrar**. Por eso el
   pre-request de `collection.bru` cancela en Production cualquier request que no sea `GET` o
   `POST /auth/login`, con el error `Production es de solo lectura: usa Local para el flujo completo.`
   Usa siempre **Local** para el Collection Runner de punta a punta; en Production limítate a
   `00-health` y `01-auth/01-login-admin` + `01-auth/02-me`. El primer request puede tardar unos
   50 s si Render está dormido (plan free).

## 4. Abrir la colección

1. Abre Bruno → **Open Collection**.
2. Selecciona la carpeta `bruno/` de este repo (la que contiene `bruno.json`).
3. Aparece la colección **RestoAPI** con las carpetas `00-health` … `11-cleanup`.

## 5. Elegir entorno

En el selector de entorno elige:

| Entorno | `baseUrl` | Uso |
|---|---|---|
| `Local` | `http://localhost:8000` | Flujo completo (Collection Runner) |
| `Production` | `https://restoapi-47sp.onrender.com` | Solo lectura: `GET` y `POST /auth/login`; el resto se cancela antes de enviarse |

## 6. Orden de ejecución (flujo de punta a punta)

Las carpetas y los requests están numerados y se ejecutan en ese orden. Cada request guarda en
variables de ejecución lo que necesitan los siguientes, así que **empieza siempre por
`01-auth/01-login-admin`**: su pre-request genera un `runId` nuevo (emails, nombres y números de mesa
únicos) y las fechas de las reservas. Si lanzas un request suelto sin haber ejecutado antes los que
crean sus datos, fallará.

| Carpeta | Qué hace | Requests |
|---|---|---|
| `00-health` | `GET /` y `GET /health` | 2 |
| `01-auth` | Login admin (guarda `token`), `/auth/me` y errores 401/422 | 6 |
| `02-users` | Crea un usuario waiter, kitchen, bartender y customer, login con cada uno (guarda `tokenWaiter`, `tokenKitchen`, `tokenBartender`, `tokenCustomer`), lista (paginado, `Page[UserOut]`), ve y edita. El customer edita su perfil (`PATCH /users/me`) y el bartender cambia su contraseña (`POST /users/me/password`) y entra con la nueva. Errores 401/403/404/409/422 | 25 |
| `03-categories` | CRUD, incluido el borrado de una categoría temporal, y una categoría de barra (`station: "bar"`). Errores 401/403/404/409 | 11 |
| `04-dishes` | CRUD, listado paginado con filtros, borrado de un plato temporal y un plato de barra. Errores 403/404/422 | 12 |
| `05-tables` | CRUD, mesas disponibles, cambio de estado como waiter. Errores 403/404/409/422 | 14 |
| `06-reservations` | Reserva del admin para el customer, reserva del propio customer, edición, cancelación y borrado. Errores 401/403/404/409/422 | 18 |
| `07-orders` | Pedido del waiter con una línea de cocina y otra de barra; kitchen y bartender solo ven la suya (R-14) → `in_kitchen` (kitchen) → línea preparada (kitchen) → línea servida (waiter) → `served`. Errores 401/403/404/409/422 | 18 |
| `08-invoices` | Factura del pedido servido, listado, detalle, pedido → `paid`. Errores 403/404/409/422 | 13 |
| `09-stats` | Ventas y platos más vendidos. Errores 403/422 | 6 |
| `10-exports` | CSV de facturas y pedidos. Errores 403/422 | 5 |
| `11-cleanup` | Borrados que dan 409 (recursos en uso), borrado del plato no usado, desactivación de los usuarios de prueba y comprobación de que ya no pueden entrar (401) | 11 |

Resumen del flujo: **login admin → crear usuarios (`POST /users/`) → login por rol → CRUD de menú,
mesas, reservas y pedidos → factura → estadísticas y CSV → limpieza → desactivar usuarios → login y
token de un usuario desactivado = 401** (equivale al logout, que todavía no existe).

### Variables

| Variable | Origen | Uso |
|---|---|---|
| `baseUrl` | entorno | URL de la API |
| `adminEmail`, `adminPassword` | entorno (secretas) | Login del admin |
| `runId`, `testPassword`, `tableNumber`, `tempTableNumber`, `today`, `reservedAt*` | pre-request de `01-login-admin` | Datos únicos de la ejecución |
| `newBartenderPassword` | pre-request de `02-users/18-change-password-bartender` | Contraseña nueva aleatoria del bartender |
| `token` | `01-auth/01-login-admin` | Bearer del admin |
| `tokenWaiter`, `tokenKitchen`, `tokenBartender`, `tokenCustomer` | `02-users/05..08-login-*` | Casos por rol (403) |
| `adminId`, `waiterId`, `kitchenId`, `bartenderId`, `customerId` y sus `*Email` | `01-auth/02-me`, `02-users/01..04-create-*` | Path params y bodies |
| `categoryId`, `barCategoryId`, `dishId`, `barDishId`, `unavailableDishId`, `tableId`, `reservationId`, `customerReservationId`, `orderId`, `orderItemId` (línea de cocina), `orderBarItemId` (línea de barra), `orderTotal`, `pendingOrderId`, `invoiceId` | Requests de alta | Encadenar el flujo |

Ningún `.bru` contiene credenciales ni tokens: los tokens salen del login y los usuarios de prueba
usan una contraseña aleatoria generada en cada ejecución (`testPassword = "Bp-" + uuid v4`), que no
se puede deducir de su email.

## 7. Ejecutar toda la colección (Collection Runner)

### Desde la app

Clic derecho en la colección **RestoAPI** → **Run** → **Run Collection**, con el entorno **Local**
seleccionado y las variables secretas ya rellenas.

### Desde la terminal (CLI)

El CLI de Bruno se ejecuta **dentro de la carpeta de la colección** (la que tiene `bruno.json`).
Si lo lanzas desde la raíz del repo con `run bruno/`, falla. Con la API levantada en otra terminal:

```bash
cd bruno
npx @usebruno/cli run -r --env Local --env-var adminEmail=TU_EMAIL_ADMIN --env-var adminPassword=TU_PASSWORD_ADMIN
```

- `-r` ejecuta todas las carpetas de forma recursiva.
- Para guardar un informe: añade `--output reports/resultado.json` (la carpeta `reports/` ya existe con un `.gitkeep` y su contenido está en el `.gitignore`).
- Para no dejar la contraseña en el historial de la shell, usa variables de tu terminal:
  `--env-var adminPassword="$RESTO_ADMIN_PASSWORD"` (bash) o `--env-var adminPassword=$env:RESTO_ADMIN_PASSWORD` (PowerShell).

**Resultado esperado:** los 141 requests en verde, con todas sus aserciones pasando. Los casos de
error **también salen en verde**, porque sus tests comprueban que la API devuelve el código de error
esperado. Cada ejecución crea datos nuevos (sufijo `runId`), así que se puede repetir sin limpiar la BD.

### Qué comprueba cada request

- **Status** esperado.
- **Shape:** los campos obligatorios del schema de respuesta (`UserOut`, `DishOut`, `OrderOut`,
  `Page[...]`…).
- **Seguridad:** en todas las respuestas con usuarios, que **no aparecen `password` ni `password_hash`**.
- **Errores:** el formato común `{"detail": str, "code": str}` y el `code` concreto (`unauthorized`,
  `forbidden`, `not_found`, `conflict`, `reservation_conflict`, `invoice_already_exists`,
  `table_in_use`, `validation_error`…).
- **Reglas de negocio:** total del pedido (2 × 13,00 + 1 × 3,00 = 29,00), base + IVA = total de la
  factura, transiciones de estado, que kitchen y bartender solo ven las líneas de su estación con el
  total del pedido completo (R-14), que un customer solo ve sus reservas, etc.

Cada request tiene en la pestaña **Docs** su endpoint, los roles permitidos, el token que usa y las
respuestas posibles.

## 8. WebSocket (cocina/barra)

`/ws/kitchen` no es HTTP: no tiene `.bru` y no forma parte del runner (los 141 requests son HTTP).
Lo usan la cocina y la barra. Para probarlo a mano:

1. Ejecuta `01-auth/01-login-admin` (o `02-users/06-login-kitchen` / `02-users/07-login-bartender`)
   y copia el valor de `token` (o `tokenKitchen` / `tokenBartender`) desde las variables de ejecución.
2. Conéctate con un cliente WebSocket:
   - **websocat:** `websocat "ws://localhost:8000/ws/kitchen?token=<TOKEN>"`
   - **wscat:** `npx wscat -c "ws://localhost:8000/ws/kitchen?token=<TOKEN>"`
   - **Bruno** (versiones recientes): **New Request → WebSocket** con la misma URL.
   - En Production: `wss://restoapi-47sp.onrender.com/ws/kitchen?token=<TOKEN>`.
3. Lanza `07-orders/01-create-waiter` o `07-orders/04-status-in-kitchen` y verás los eventos:

   ```json
   {"event": "order_created", "order": {"id": 1, "table_id": 3, "table_number": 12, "waiter_id": 2, "status": "pending", "total": "26.00", "items": [...]}}
   {"event": "order_status_changed", "order": {"id": 1, "table_id": 3, "table_number": 12, "status": "in_kitchen", "total": "26.00"}}
   ```

Solo pueden conectarse usuarios activos con rol `admin`, `kitchen` o `bartender`. Sin token, con un
token inválido o con otro rol, el servidor cierra la conexión con el código **1008**.

La verificación automática real del WebSocket vive en pytest:
[`tests/integration/test_kitchen_websocket.py`](../tests/integration/test_kitchen_websocket.py).

## 9. Comportamiento actual que conviene saber

- **Existen pero quedan fuera de esta colección:**
  - `POST /auth/register` (HU-22).
  - `POST /auth/social/{provider}` (HU-38, login con Google o GitHub): necesita un `code` OAuth real
    del proveedor, así que no se puede automatizar en el runner tal cual.
  - `DELETE /users/{user_id}` (soft delete) y `POST /users/{user_id}/restore` (HU-32).
- **Ya en `dev` y cubiertos:** la paginación `Page` de `GET /users` (HU-24; los filtros `role`,
  `is_active` y `q` no se prueban), el filtro por estación de HU-40 (`07-orders/02-list-kitchen` y
  `07-orders/03-get-bartender`) y el perfil propio de HU-25 (`02-users/17` a `25`). El cambio de
  contraseña se hace con el bartender porque `11-cleanup/10` hace login del customer con
  `testPassword` y espera 401 por estar desactivado. Cambiar la contraseña no revoca los tokens ya
  emitidos: `tokenBartender` sigue sirviendo después.
- **No existen todavía:** `/auth/refresh` y `/auth/logout` (HU-30). Los usuarios se crean con
  `POST /users/` (admin) y la colección los da de baja con `PATCH /users/{id}/deactivate` (carpeta
  `11-cleanup`).
- **Login:** es OAuth2 Password Flow, con body `application/x-www-form-urlencoded` y el email en el
  campo `username`. No acepta JSON.
- **Reservas (HU-43):** hoy un customer **sí** puede crear reservas a su nombre (201). El 403 solo
  salta si indica el `user_id` de otro usuario. El alcance "solo el personal da de alta reservas" se
  ajustará cuando se refine la HU-43, y la colección se actualizará en esa PR.
- **Facturas:** el 409 es **por pedido**: `order_not_served` (el pedido no está `served`) o
  `invoice_already_exists` (ya tiene factura). La API no tiene el concepto "facturar la misma mesa dos
  veces a la vez", así que ese caso no está cubierto.
- **Validación:** los datos mal formados devuelven **422** (`validation_error`, con la lista `errors`),
  no 400.
- **Barras finales:** `/users/`, `/categories/`, `/dishes/` y `/orders/` llevan barra al final;
  `/tables`, `/reservations` e `/invoices` no. La colección usa la forma exacta de cada router.
- **Emails de reservas:** con `EMAIL_ENABLED=false` (por defecto en local) solo se escriben en el log.

## 10. Mantener la colección

- Un endpoint nuevo o modificado se acompaña, en la misma PR, de su `.bru` (caso feliz + errores).
- Respeta la numeración `NN-...` (el orden de ejecución) y el `seq` del bloque `meta`.
- Los casos de error van en la misma carpeta que el recurso, detrás de los casos felices
  (`NN-error-4xx-...`). No se usan subcarpetas porque el CLI de Bruno ejecuta las subcarpetas antes que
  los archivos de la carpeta padre, y los errores dependen de los recursos ya creados.
- Nunca pongas credenciales ni tokens en un `.bru`: usa variables de entorno secretas o de ejecución.

## 11. Cobertura de endpoints

| Método | Path | Requests | Archivos |
|---|---|---|---|
| `GET` | `/` | 1 | `00-health/01-root.bru` |
| `GET` | `/health` | 1 | `00-health/02-health.bru` |
| `POST` | `/auth/login` | 10 | `01-auth/01-login-admin.bru`<br>`01-auth/03-error-401-login-credenciales-invalidas.bru`<br>`01-auth/06-error-422-login-sin-password.bru`<br>`02-users/05-login-waiter.bru`<br>`02-users/06-login-kitchen.bru`<br>`02-users/07-login-bartender.bru`<br>`02-users/08-login-customer.bru`<br>`11-cleanup/10-error-401-login-usuario-desactivado.bru`<br>`02-users/19-login-bartender-nueva-password.bru`<br>`02-users/20-error-401-login-password-antigua.bru` |
| `GET` | `/auth/me` | 4 | `01-auth/02-me.bru`<br>`01-auth/04-error-401-me-sin-token.bru`<br>`01-auth/05-error-401-me-token-invalido.bru`<br>`11-cleanup/11-error-401-me-token-usuario-desactivado.bru` |
| `POST` | `/users/` | 7 | `02-users/01-create-waiter.bru`<br>`02-users/02-create-kitchen.bru`<br>`02-users/03-create-bartender.bru`<br>`02-users/04-create-customer.bru`<br>`02-users/12-error-409-email-duplicado.bru`<br>`02-users/15-error-401-crear-sin-token.bru`<br>`02-users/16-error-422-email-invalido.bru` |
| `GET` | `/users/` | 2 | `02-users/09-list-users.bru`<br>`02-users/13-error-403-listar-como-waiter.bru` |
| `GET` | `/users/{user_id}` | 2 | `02-users/10-get-user.bru`<br>`02-users/14-error-404-usuario-inexistente.bru` |
| `PUT` | `/users/{user_id}` | 1 | `02-users/11-update-user.bru` |
| `PATCH` | `/users/{user_id}/deactivate` | 5 | `11-cleanup/05-desactivar-waiter.bru`<br>`11-cleanup/06-desactivar-kitchen.bru`<br>`11-cleanup/07-desactivar-bartender.bru`<br>`11-cleanup/08-desactivar-customer.bru`<br>`11-cleanup/09-error-404-desactivar-inexistente.bru` |
| `PATCH` | `/users/me` | 4 | `02-users/17-update-me-customer.bru`<br>`02-users/23-error-422-me-campo-no-editable.bru`<br>`02-users/24-error-409-me-email-ocupado.bru`<br>`02-users/25-error-401-me-sin-token.bru` |
| `POST` | `/users/me/password` | 3 | `02-users/18-change-password-bartender.bru`<br>`02-users/21-error-403-password-actual-incorrecta.bru`<br>`02-users/22-error-422-misma-password.bru` |
| `POST` | `/categories/` | 5 | `03-categories/01-create.bru`<br>`03-categories/05-create-temporal.bru`<br>`03-categories/08-error-409-nombre-duplicado.bru`<br>`03-categories/09-error-403-crear-como-customer.bru`<br>`03-categories/11-create-barra.bru` |
| `GET` | `/categories/` | 2 | `03-categories/02-list.bru`<br>`03-categories/10-error-401-listar-sin-token.bru` |
| `GET` | `/categories/{category_id}` | 2 | `03-categories/03-get.bru`<br>`03-categories/07-error-404-categoria-borrada.bru` |
| `PUT` | `/categories/{category_id}` | 1 | `03-categories/04-update.bru` |
| `DELETE` | `/categories/{category_id}` | 2 | `03-categories/06-delete-temporal.bru`<br>`11-cleanup/03-error-409-borrar-categoria-con-platos.bru` |
| `POST` | `/dishes/` | 6 | `04-dishes/01-create.bru`<br>`04-dishes/02-create-no-disponible.bru`<br>`04-dishes/03-create-temporal.bru`<br>`04-dishes/10-error-403-crear-como-waiter.bru`<br>`04-dishes/11-error-422-precio-negativo.bru`<br>`04-dishes/12-create-plato-barra.bru` |
| `GET` | `/dishes/` | 2 | `04-dishes/05-list-filtro-categoria.bru`<br>`04-dishes/06-list-disponibles.bru` |
| `GET` | `/dishes/{dish_id}` | 2 | `04-dishes/07-get.bru`<br>`04-dishes/09-error-404-plato-borrado.bru` |
| `PUT` | `/dishes/{dish_id}` | 1 | `04-dishes/08-update.bru` |
| `DELETE` | `/dishes/{dish_id}` | 3 | `04-dishes/04-delete-temporal.bru`<br>`11-cleanup/01-error-409-borrar-plato-en-uso.bru`<br>`11-cleanup/04-borrar-plato-no-disponible.bru` |
| `POST` | `/orders/` | 6 | `07-orders/01-create-waiter.bru`<br>`07-orders/08-create-pedido-pendiente.bru`<br>`07-orders/09-error-403-crear-como-kitchen.bru`<br>`07-orders/13-error-409-plato-no-disponible.bru`<br>`07-orders/14-error-404-mesa-inexistente.bru`<br>`07-orders/18-error-401-sin-token.bru` |
| `GET` | `/orders/` | 2 | `07-orders/02-list-kitchen.bru`<br>`07-orders/11-error-403-customer-lista-pedidos.bru` |
| `GET` | `/orders/{order_id}` | 2 | `07-orders/03-get-bartender.bru`<br>`07-orders/15-error-404-pedido-inexistente.bru` |
| `PATCH` | `/orders/{order_id}/status` | 5 | `07-orders/04-status-in-kitchen.bru`<br>`07-orders/07-status-served.bru`<br>`07-orders/12-error-409-transicion-invalida.bru`<br>`08-invoices/11-pedido-pagado.bru`<br>`08-invoices/13-cancelar-pedido-pendiente.bru` |
| `PATCH` | `/orders/{order_id}/items/{item_id}` | 6 | `07-orders/05-item-preparado-kitchen.bru`<br>`07-orders/06-item-servido-waiter.bru`<br>`07-orders/10-error-403-kitchen-marca-servido.bru`<br>`07-orders/16-error-404-linea-inexistente.bru`<br>`07-orders/17-error-422-linea-sin-campos.bru`<br>`08-invoices/12-error-409-linea-pedido-cerrado.bru` |
| `POST` | `/orders/{order_id}/invoice` | 4 | `08-invoices/01-create.bru`<br>`08-invoices/05-error-409-ya-facturado.bru`<br>`08-invoices/06-error-409-pedido-no-servido.bru`<br>`08-invoices/07-error-404-pedido-inexistente.bru` |
| `GET` | `/invoices` | 4 | `08-invoices/02-list.bru`<br>`08-invoices/03-list-por-fecha.bru`<br>`08-invoices/09-error-403-kitchen.bru`<br>`08-invoices/10-error-422-rango-fechas.bru` |
| `GET` | `/invoices/{invoice_id}` | 2 | `08-invoices/04-get.bru`<br>`08-invoices/08-error-404-factura-inexistente.bru` |
| `GET` | `/exports/invoices` | 2 | `10-exports/01-invoices-csv.bru`<br>`10-exports/03-error-403-waiter.bru` |
| `GET` | `/exports/orders` | 3 | `10-exports/02-orders-csv.bru`<br>`10-exports/04-error-422-rango.bru`<br>`10-exports/05-error-422-status-invalido.bru` |
| `GET` | `/stats/sales` | 4 | `09-stats/01-sales.bru`<br>`09-stats/02-sales-rango.bru`<br>`09-stats/04-error-422-rango.bru`<br>`09-stats/06-error-403-waiter.bru` |
| `GET` | `/stats/top-dishes` | 2 | `09-stats/03-top-dishes.bru`<br>`09-stats/05-error-422-limit.bru` |
| `GET` | `/tables` | 2 | `05-tables/02-list.bru`<br>`05-tables/13-error-403-listar-como-kitchen.bru` |
| `GET` | `/tables/available` | 1 | `05-tables/03-available.bru` |
| `GET` | `/tables/{table_id}` | 2 | `05-tables/04-get.bru`<br>`05-tables/10-error-404-mesa-borrada.bru` |
| `POST` | `/tables` | 5 | `05-tables/01-create.bru`<br>`05-tables/08-create-temporal.bru`<br>`05-tables/11-error-409-numero-duplicado.bru`<br>`05-tables/12-error-403-crear-como-waiter.bru`<br>`05-tables/14-error-422-campo-no-permitido.bru` |
| `PUT` | `/tables/{table_id}` | 1 | `05-tables/05-update.bru` |
| `PATCH` | `/tables/{table_id}/status` | 2 | `05-tables/06-update-status-occupied.bru`<br>`05-tables/07-update-status-available.bru` |
| `DELETE` | `/tables/{table_id}` | 2 | `05-tables/09-delete-temporal.bru`<br>`11-cleanup/02-error-409-borrar-mesa-en-uso.bru` |
| `POST` | `/reservations` | 5 | `06-reservations/01-create-admin-para-cliente.bru`<br>`06-reservations/05-create-cliente.bru`<br>`06-reservations/08-error-409-solapamiento.bru`<br>`06-reservations/09-error-403-cliente-para-otro-usuario.bru`<br>`06-reservations/15-error-422-aforo-superado.bru` |
| `GET` | `/reservations` | 5 | `06-reservations/02-list-admin.bru`<br>`06-reservations/06-list-cliente.bru`<br>`06-reservations/11-error-403-cliente-filtra-otro-usuario.bru`<br>`06-reservations/12-error-403-kitchen-sin-acceso.bru`<br>`06-reservations/13-error-401-sin-token.bru` |
| `GET` | `/reservations/{reservation_id}` | 2 | `06-reservations/03-get-cliente-dueno.bru`<br>`06-reservations/14-error-404-reserva-inexistente.bru` |
| `PATCH` | `/reservations/{reservation_id}` | 3 | `06-reservations/04-update-admin.bru`<br>`06-reservations/07-update-cliente-notas.bru`<br>`06-reservations/10-error-403-cliente-cambia-estado.bru` |
| `PATCH` | `/reservations/{reservation_id}/cancel` | 2 | `06-reservations/16-cancel-cliente.bru`<br>`06-reservations/17-error-409-cancelar-ya-cancelada.bru` |
| `DELETE` | `/reservations/{reservation_id}` | 1 | `06-reservations/18-delete-cliente.bru` |

Sin cobertura en esta colección:

| Método | Path | HU |
|---|---|---|
| `POST` | `/auth/register` | HU-22 |
| `POST` | `/auth/social/{provider}` | HU-38 |
| `DELETE` | `/users/{user_id}` | HU-32 |
| `POST` | `/users/{user_id}/restore` | HU-32 |
