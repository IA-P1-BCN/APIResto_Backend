# HU-31 · Límite de intentos de login

> Issue: #74 · Prioridad Should · Escribe: Rita · Revisa: la primera persona que la vea ·
> Aprueba: quien revisa (acuerdo del 14/10). Vocabulario: `specs/ontology.md`. Usa
> `specs/HU-TEMPLATE.md`.

## Problem Statement
La issue dice: "Como equipo quiero limitar los intentos de login para frenar ataques de fuerza
bruta". El título de la tarjeta ("Intentos de logout") es una errata: la historia es la regla
R-10 (Should). No trae criterios de aceptación. Revisado `dev` (commit `e6164f4`; vuelto a revisar con HU-33,
`8682008`, que no cambia el login):

- `POST /auth/login` (`app/routers/auth.py`) llama a `user_service.authenticate` y, si devuelve
  `None`, responde 401 `unauthorized`. No cuenta intentos: se pueden probar contraseñas sin
  límite.
- `authenticate` devuelve `None` en cuatro casos, todos con el mismo 401: el email no existe, el
  usuario está desactivado o borrado (R-04), la cuenta no tiene contraseña (solo Google o
  GitHub) o la contraseña es incorrecta.
- `app/core/exceptions.py` no tiene error 429, y `CODES_BY_STATUS` y `DEFAULT_DESCRIPTIONS`
  (`app/core/openapi.py`) no incluyen el 429. `AGENTS.md` ya lo lista entre los códigos de error.
- En Render, `request.client.host` es la IP del proxy, no la del cliente. Uvicorn 0.54 con
  `FORWARDED_ALLOW_IPS="*"` toma la primera IP de `X-Forwarded-For`, que escribe el cliente, y el
  proxy de Render no la limpia: no sirve para un límite por IP.

## Solution
Contar los 401 de `POST /auth/login` por pareja IP + email, en memoria. Tras 5 fallos en una
ventana fija de 15 minutos, esa pareja recibe 429 `too_many_attempts` con `Retry-After` hasta
que acabe la ventana, también si la contraseña es correcta. Un login correcto borra el
contador. Los números y la cabecera de la IP se leen de variables de entorno.

## User Stories
1. Como equipo, quiero que tras 5 contraseñas fallidas desde la misma IP para el mismo email
   el login responda 429, para frenar ataques de fuerza bruta.
2. Como usuario, quiero que un fallo desde otra IP no bloquee mi cuenta, para que nadie pueda
   dejarme sin entrar a propósito.
3. Como usuario, quiero que entrar bien borre mis fallos anteriores, para no arrastrarlos.
4. Como frontend, quiero saber cuántos segundos faltan (`Retry-After`), para decírselo al
   usuario.
5. Como equipo, quiero un aviso en el log cuando empieza un bloqueo, con la IP y la cuenta, para
   investigar un ataque.
6. Como equipo, quiero cambiar el límite y la ventana por variable de entorno, sin tocar código.

## Implementation Decisions
- **Modelo**: ninguno. Sin tabla, sin migración de Alembic y sin cambios en la ontología (R-10
  delega N y la ventana en esta spec).
- **Endpoint**: solo `POST /auth/login`. Misma ruta y mismo 200 y 401. Nuevo 429:
  - cuerpo `{"detail": "Too many failed login attempts. Try again later.", "code":
    "too_many_attempts"}`;
  - cabecera `Retry-After` con los segundos enteros que faltan para que acabe la ventana
    (redondeo hacia arriba, mínimo 1).
- **Regla (R-10)**:
  - clave: `(client_ip, email)`, con el email en minúsculas y sin espacios (como R-01);
  - cuenta todo 401 del login (los cuatro casos de `authenticate`); los 422 no cuentan;
  - ventana fija: empieza en el primer fallo y dura `LOGIN_WINDOW_MINUTES`; actualizar el
    contador no la alarga;
  - los fallos 1 a 5 responden 401; desde el sexto intento, 429 hasta que acabe la ventana;
  - el bloqueo se comprueba antes de verificar credenciales: durante el bloqueo, la contraseña
    correcta también recibe 429 (y no se ejecuta bcrypt);
  - un login correcto borra el contador de esa clave.
- **Configuración** (`app/config.py`, `.env.example`, `render.yaml`):
  - `LOGIN_MAX_ATTEMPTS: int = 5` (mínimo 1);
  - `LOGIN_WINDOW_MINUTES: int = 15` (mínimo 1);
  - `CLIENT_IP_HEADER: str = ""`. Vacía: se usa `request.client.host` (local y tests). En
    Render: `True-Client-IP` (la pone Cloudflare delante de Render). Si la cabecera
    configurada no llega, se usa `request.client.host`. Nunca se lee `X-Forwarded-For`.
- **Almacén**: `cachetools.TTLCache` en memoria (ya es dependencia, sin paquetes nuevos), con
  `ttl` = la ventana y un `maxsize` de 10.000 parejas (si se llena, descarta las más antiguas). Guarda el número de fallos y el momento del primero.
  Un `threading.Lock` protege la caché, porque los endpoints síncronos de FastAPI corren en
  varios hilos. El reloj se inyecta para poder probar la ventana sin esperar.
  Contrapartida aceptada: se pierde al reiniciar el servidor y no se comparte entre
  instancias (hay una sola).
- **Log**: al quinto fallo, un warning `Login blocked` con `client_ip` y el email normalizado.
  Nunca la contraseña. Los 429 ya los registra `http_error_handler`.
- **Capas**:
  - `routers/auth.py`: obtiene la IP del cliente (con `CLIENT_IP_HEADER`) y pasa IP y email al
    service; documenta el 429.
  - `services/login_rate_limit_service.py` (nuevo): comprobar el bloqueo, sumar un fallo,
    borrar el contador y calcular `Retry-After`.
  - `core/exceptions.py`: `TooManyRequestsError` (429, `too_many_attempts`) y el 429 en
    `CODES_BY_STATUS`.
  - `core/openapi.py`: el 429 en `DEFAULT_DESCRIPTIONS`.
  - Sin repository: no hay base de datos.
- **Swagger**: el login declara el 429 con `error_responses` y una descripción que cita
  `too_many_attempts` y `Retry-After`. El `description` del endpoint explica el límite.
- **Documentación**: `docs/api.md` gana un apartado corto sobre el límite de login.

## Testing Decisions
- Fixture `autouse` en `tests/conftest.py` que vacía los contadores antes de cada test: todas
  las peticiones de `TestClient` llegan desde la misma IP (`testclient`), y los tests que ya
  prueban contraseñas incorrectas se sumarían entre sí.
- Integración (`tests/test_login_rate_limit.py`, con `TestClient`):
  - 5 fallos responden 401 y el sexto, 429 con `code` `too_many_attempts` y `Retry-After`
    entre 1 y la ventana en segundos;
  - durante el bloqueo, la contraseña correcta recibe 429;
  - un login correcto tras 4 fallos borra el contador: 5 fallos más vuelven a dar 401 hasta el
    sexto;
  - otro email desde la misma IP no está bloqueado;
  - el mismo email desde otra IP (con `CLIENT_IP_HEADER` en el test) no está bloqueado;
  - `Ana@X.com` y `ana@x.com` cuentan juntos;
  - email que no existe y usuario desactivado también cuentan;
  - un 422 (sin `password`) no cuenta;
  - el 429 valida contra `ErrorResponse`.
- Unitarios del service con reloj falso: la ventana acaba a los `LOGIN_WINDOW_MINUTES` desde
  el primer fallo y no se alarga con los siguientes; `Retry-After` baja con el tiempo.
- Log: el warning `Login blocked` sale una vez, con IP y email y sin la contraseña (`caplog`).
- `tests/test_openapi.py` pasa sin tocarlo, con el 429 declarado.
- Se prueban en falso (con el límite desactivado a propósito) para comprobar que fallan.
- No se prueba en los tests la cabecera de Render: se comprueba a mano tras el deploy.

## Criterios de aceptación
- [ ] Tras 5 intentos fallidos de la misma IP para el mismo email en 15 minutos, el sexto
  `POST /auth/login` responde 429 con `{"detail", "code": "too_many_attempts"}` y
  `Retry-After`.
- [ ] Durante el bloqueo, la contraseña correcta también recibe 429.
- [ ] Al acabar la ventana de 15 minutos desde el primer fallo, se puede volver a intentar.
- [ ] Un login correcto borra los fallos de esa IP y ese email.
- [ ] Otra IP con el mismo email, u otro email con la misma IP, no se bloquean.
- [ ] Cuentan todos los 401 del login; los 422 no.
- [ ] `LOGIN_MAX_ATTEMPTS`, `LOGIN_WINDOW_MINUTES` y `CLIENT_IP_HEADER` están en
  `config.py`, `.env.example` y `render.yaml`; la IP nunca sale de `X-Forwarded-For`.
- [ ] El log registra `Login blocked` con IP y email al quinto fallo, sin la contraseña.
- [ ] Swagger documenta el 429 del login con `ErrorResponse`, `too_many_attempts` y
  `Retry-After`; `tests/test_openapi.py` pasa.
- [ ] Sin cambios de modelo ni migración; los tests existentes pasan sin modificarse (solo se
  añade el fixture de `conftest.py`).
- [ ] `docs/api.md` explica el límite.
- [ ] Tras el deploy, el log `Login blocked` de producción muestra la IP real del cliente y no
  la del proxy (se anota en la issue).
- [ ] Lint limpio, CI en verde con la cobertura mínima, entrada en `docs/ai-log.md` y PR
  `[HU-31] ...` de menos de 400 líneas (si no cabe, se divide en pasos).

## Out of Scope
- Login social (`POST /auth/social/{provider}`): el `code` lo emite el proveedor, caduca y es de
  un solo uso.
- Límite en otros endpoints (`/users/me/password`, `set-password`, registro): R-10 es solo para
  login (lo dice también HU-25).
- Logout, refresh tokens y `jti` (R-05 a R-08, Must): otra HU.
- Guardar los intentos en la base de datos o compartirlos entre instancias (Redis).
- Tope adicional por email solo, independiente de la IP.
- Avisar al usuario por email de un bloqueo.

## Preguntas abiertas
Ninguna.

## Decisiones de la sesión
Sesión de 16/10/2026 (Rita, con Claude):
- **Es R-10, no logout** → el texto de la issue habla de intentos de login y fuerza bruta.
  Rechazado: tratarla como logout (R-07) por el título.
- **Clave IP + email** (Rita) → frena la fuerza bruta contra una cuenta y nadie bloquea una
  cuenta ajena desde su IP. Rechazados: solo email (cualquiera bloquea una cuenta ajena) y solo
  IP (una red compartida se bloquea entera).
- **En memoria con `cachetools`** (Rita) → sin modelo ni migración, sin depender de Carla antes
  del 19/10, y ya es dependencia. Rechazada: tabla `login_attempts` (migración `0009` y entidad
  nueva). Contrapartida aceptada: se pierde al reiniciar.
- **5 fallos en ventana fija de 15 minutos** (Rita) → encaja con `TTLCache` y es fácil de
  explicar. Rechazado: bloqueo de duración aparte con `LOGIN_LOCKOUT_MINUTES` (dos cachés y más
  tests).
- **Un login correcto borra el contador** (Rita). Rechazado: mantenerlo hasta que caduque.
- **Durante el bloqueo, la contraseña correcta también recibe 429** (Rita) → si no, el
  atacante sabría cuándo acierta; además se ahorra bcrypt. Rechazado: dejar entrar.
- **429 con `too_many_attempts` y `Retry-After`; el 429 empieza en el sexto intento** (Rita) →
  el cliente sabe cuánto esperar y cumple "tras N intentos". Rechazados: sin `Retry-After` y
  429 en el propio quinto fallo.
- **Cuenta todo 401; los 422 no** (Rita) → contar solo la contraseña incorrecta revelaría qué
  emails están registrados. Rechazado: contar solo la contraseña incorrecta de un usuario que
  existe.
- **Login social fuera** (Rita) → no hay contraseña que adivinar. Rechazado: aplicarle el mismo
  límite.
- **Warning `Login blocked` con IP y email al quinto fallo** (Rita). Rechazados: solo IP y no
  añadir nada.
- **IP desde `CLIENT_IP_HEADER`, nunca desde `X-Forwarded-For`** (Rita) → con
  `FORWARDED_ALLOW_IPS="*"` uvicorn toma la IP que escribe el cliente, y el proxy de Render no
  la limpia. Si la cabecera no llega, se usa la IP del proxy: el límite queda como "solo email",
  que no se puede saltar. Rechazados: `FORWARDED_ALLOW_IPS="*"` (lo propuso Claude y se
  descartó al leer el código de uvicorn), tope extra por email (más variables y tests) y
  cambiar la clave a solo email.
