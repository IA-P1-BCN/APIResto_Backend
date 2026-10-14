# 🚀 Guía de despliegue — RestoAPI

> **Solo Anna despliega.** Únicamente ella puede mergear en `main` y tiene acceso a Neon, Render y Vercel.

| Pieza | Plataforma | Repo | Se despliega cuando… |
|---|---|---|---|
| Base de datos | Neon (PostgreSQL 16) | — | Migraciones con `alembic upgrade head` en el arranque de Render |
| API | Render (Web Service, free) | `restochino-dev/backend` | Push a `main` → `deploy.yml` → tests en verde → deploy hook |
| Web | Vercel (Hobby) | `restochino-dev/frontend` | Push a `main` (producción) · cada PR genera una Preview URL |

El equipo trabaja en `IA-P1-BCN/Resto-API_Backend` y `IA-P1-BCN/Resto-API_Frontend`. Se despliega desde los repos de `restochino-dev`: lo que está en `main` de IA-P1-BCN se sube con una PR a `main` de `restochino-dev` (ver [sección 5](#5-paso-a-producción-d5-y-d9)).

## 1. Neon (base de datos)

> ✅ **Ya creado** (2026-10-02): proyecto `Resto-API` (`small-violet-45321750`) en la organización de Anna · AWS Frankfurt · Postgres 16 · base de datos `restoapi`.
>
> | Rama Neon | Usuario | Uso | Quién tiene la URL |
> |---|---|---|---|
> | `main` | `restoapi_owner` | Producción (Render) | Solo Anna |
> | `dev` | `restoapi_dev` | Integración compartida | Equipo |
>
> `restoapi_dev` solo existe en la rama `dev`: compartir su URL no da acceso a producción.
> **Nunca** compartas la URL de `restoapi_owner`: tiene la misma contraseña en `main` y en `dev`.

Pasos (por si hay que recrearlo):

1. [neon.tech](https://neon.tech) → **New Project** → región **AWS Europe (Frankfurt)** · Postgres 16 · base de datos `restoapi`.
2. **Branches → New branch** `dev` desde `main` (`main` = producción, `dev` = integración).
3. **Connect** → marcar *Connection pooling* → copiar la cadena y adaptarla a SQLAlchemy:
   ```
   postgresql+psycopg://USER:PASS@HOST-pooler.REGION.aws.neon.tech/restoapi?sslmode=require
   ```
4. Guardar las dos URLs (rama `main` y rama `dev`) en un gestor de secretos. Nunca en el chat ni en el repo.

## 2. Render (API)

1. Render → **New → Blueprint** → repo `restochino-dev/backend` (lee [`render.yaml`](../render.yaml)).
2. Rellenar las variables marcadas como `sync: false`:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | Neon, rama `main` (pooled), empezando por `postgresql+psycopg://` (no `postgresql://`: ver paso 3 de Neon) |
   | `ALLOWED_ORIGINS` | URL de producción de Vercel, exacta y sin `/` final (p. ej. `https://restoapi.vercel.app`). Varias, separadas por comas |
   | `BREVO_API_KEY`, `MAIL_FROM` | Vacías hasta HU-19 (D7) |

   `JWT_SECRET_KEY` la genera Render automáticamente.
3. **Settings → Deploy Hook** → copiar la URL.
4. Comprobar que **Auto-Deploy está en Off** (el deploy lo lanza GitHub Actions).
5. Cuando exista `/health` (D3): abrir `https://<servicio>.onrender.com/docs`.

> El arranque (`sh docker-entrypoint.sh`) aplica `alembic upgrade head` antes de levantar la API. Ver [sección 8](#8-migraciones-con-alembic-hu-23).

## 3. GitHub Actions (repo Backend)

En `restochino-dev/backend`, **Settings → Secrets and variables → Actions** (o en el entorno `production`, que es el que usa `deploy.yml`):

| Tipo | Nombre | Valor |
|---|---|---|
| Secret | `RENDER_DEPLOY_HOOK_URL` | URL del deploy hook de Render |
| Secret | `JWT_SECRET_KEY_TEST` | Cualquier cadena (solo tests) |
| Variable | `RENDER_URL` | `https://<servicio>.onrender.com` |
| Variable | `COVERAGE_MIN` | `0` al principio · `70` en el Sprint 2 |

| Workflow | Cuándo | Qué hace |
|---|---|---|
| `ci.yml` (job `tests`) | PR a `dev`/`main` y push a `dev` | ruff → una sola cabeza de Alembic → migraciones → pytest + cobertura → build Docker. Check obligatorio para mergear |
| `deploy.yml` | Push a `main` | Reutiliza `ci.yml` y, si pasa, dispara el deploy hook de Render y espera a que `/health` devuelva el commit desplegado (máx. 10 min) |

Mientras `RENDER_DEPLOY_HOOK_URL` no exista, `deploy.yml` ejecuta los tests y **omite** el deploy con un aviso.
Los pasos de Alembic, pytest y Docker se activan solos cuando existan `alembic.ini`, `tests/` y `Dockerfile`.

Lanzar un deploy a mano: **Actions → deploy → Run workflow** (rama `main`).

### Merge bloqueado si el CI falla

El check del CI es obligatorio en `dev` y `main` de los dos repos (ruleset **CI obligatorio**: `tests` en el backend, `build` en el frontend). Con un test fallando el botón de merge queda bloqueado.

Se configura con [`scripts/github-rulesets.sh`](../scripts/github-rulesets.sh) (Anna, permisos de admin). Se puede volver a ejecutar sin problema: actualiza el ruleset si ya existe.

```bash
sh scripts/github-rulesets.sh
```

Para comprobar que funciona: **Settings → Rules → Rulesets** en cada repo, o abrir un PR con un test roto y ver el merge bloqueado.

## 4. Vercel (web)

1. Vercel → **Add New → Project** → importar `restochino-dev/frontend`.
2. Configuración:

   | Campo | Valor |
   |---|---|
   | Root Directory | `./` (raíz del repo) |
   | Framework Preset | Vite |
   | Build Command | `npm run build` |
   | Output Directory | `dist` |
   | Install Command | `npm ci` |
   | Env var | `VITE_API_URL` = URL de Render, sin `/` final (Production y Preview) |
   | Env var | `VITE_USE_MOCK` = `false` (o no definirla) |
   | Node.js | La que permite `engines` en el `package.json` del frontend (20.19+ o 22.12+, lo que pide Vite) |

   Las variables `VITE_*` se fijan al construir: si se cambian, hay que volver a desplegar (**Deployments → Redeploy**).

3. **Settings → Git → Production Branch** = `main`.
4. Añadir la URL de producción de Vercel a `ALLOWED_ORIGINS` en Render.

`vercel.json` ya incluye el *rewrite* para que las rutas del SPA no den 404.

## 5. Paso a producción (D5 y D9)

1. En IA-P1-BCN, Anna abre el PR `dev` → `main` en cada repo; otra persona lo aprueba y Anna mergea (merge commit, no squash).
2. Se sube `main` a `restochino-dev` con una PR a su `main` (en cada repo; Anna puede mergearla sin aprobación). Los dos repos no comparten historial, así que la rama se crea desde `main` de `restochino-dev` y se le copia el contenido de `main` de IA-P1-BCN:

   ```bash
   # Una vez por copia local: remoto de despliegue
   git remote add restochino https://github.com/restochino-dev/backend.git    # frontend: .../frontend.git

   git fetch origin
   git fetch restochino
   git switch -c release/AAAA-MM-DD restochino/main
   git restore --source origin/main --staged --worktree :/
   git commit -m "Release AAAA-MM-DD"
   git push restochino release/AAAA-MM-DD
   # Abrir el PR release/AAAA-MM-DD → main en restochino-dev y mergearlo
   ```

   `git restore` deja el contenido exactamente igual que `main` de IA-P1-BCN (también borra lo que allí ya no existe).

Al entrar en `main` de `restochino-dev`:

1. Vercel despliega el frontend automáticamente (el CI del frontend ya ha pasado lint, tests y build en el PR).
2. `deploy.yml` ejecuta los tests y, si pasan, despliega la API en Render y comprueba `/health`.
3. Verificar: `<RENDER_URL>/health`, `<RENDER_URL>/docs` y la web en Vercel.

### Comprobar el despliegue

[`scripts/smoke-deploy.sh`](../scripts/smoke-deploy.sh) revisa de una vez los criterios de HU-01: `/health`, Swagger, que la API pide token, CORS desde Vercel, la web y su *rewrite*, y que el frontend apunta a la API de Render.

```bash
sh scripts/smoke-deploy.sh https://<servicio>.onrender.com https://<proyecto>.vercel.app
```

### Primer admin en producción

El plan free de Render no tiene *Shell*, así que el primer admin se crea **desde tu equipo** contra la BD de producción (Neon `main`). La URL solo se pone en la variable de entorno de ese comando, nunca en el `.env` ni en el repo:

```bash
# PowerShell
$env:DATABASE_URL = "postgresql+psycopg://restoapi_owner:...@...-pooler...neon.tech/restoapi?sslmode=require"
python -m app.scripts.create_admin EMAIL PASSWORD "Nombre"
Remove-Item Env:DATABASE_URL
```

Con ese admin se crean el resto de usuarios desde Swagger (`POST /users/`).

### Si algo falla

| Síntoma | Causa | Solución |
|---|---|---|
| Render: `No module named 'psycopg2'` | `DATABASE_URL` empieza por `postgresql://` | Cambiarla a `postgresql+psycopg://` |
| Render: `No config file 'alembic.ini' found` | El *Start Command* del servicio no es el de `render.yaml` | Poner `sh docker-entrypoint.sh` en **Settings → Start Command** de Render |
| Navegador: error de CORS | `ALLOWED_ORIGINS` no contiene la URL exacta de Vercel | Corregirla en Render (sin `/` final) y reiniciar el servicio |
| La web llama a `localhost:8000` | Falta `VITE_API_URL` en Vercel | Añadirla y hacer *Redeploy* |
| `500` con `SSL connection has been closed unexpectedly` tras un rato sin uso | Neon suspende la BD a los 5 min y el *pool* de SQLAlchemy guardaba conexiones cerradas | Resuelto con `pool_pre_ping=True` en `create_engine` (`app/database.py`): comprobar que el deploy incluye ese cambio |
| Cocina en "Sin conexión" | Render dormido o reiniciando | Se reconecta sola; mientras tanto actualiza cada 10 s |

## 6. Checklist antes de la demo (D10)

- [ ] `sh scripts/smoke-deploy.sh <RENDER_URL> <VERCEL_URL>` en verde
- [ ] Abrir `<RENDER_URL>/health` 5-10 min antes (cold start del free tier ≈ 50 s)
- [ ] Datos de demo cargados en Neon `main`
- [ ] Usuarios demo por rol funcionando
- [ ] Vídeo de respaldo grabado (D9) y `docker-compose up` listo como plan B

## 7. Docker en local (HU-02)

Levanta todo el stack con un solo comando: API + PostgreSQL 16 + frontend. Sirve también como **plan B de la demo** si Render o Vercel fallan.

**Requisitos:** Docker Desktop arrancado y los dos repos clonados en la misma carpeta:

```text
P2_Resto/
├── Resto-API_Backend/    ← docker-compose.yml
└── Resto-API_Frontend/
```

Si el frontend está en otra ruta, añadir `FRONTEND_PATH=/ruta/al/frontend` en el `.env` del backend.

```bash
cd Resto-API_Backend
docker compose up --build        # primera vez o tras cambiar dependencias
docker compose up -d             # en segundo plano
docker compose logs -f api       # ver logs de la API
docker compose down              # parar
docker compose down -v           # parar y BORRAR los datos de la BD
```

| Servicio | URL | Imagen |
|---|---|---|
| `frontend` | http://localhost:5173 | `Resto-API_Frontend/Dockerfile` (Node 22 → nginx) |
| `api` | http://localhost:8000 · `/docs` | `Resto-API_Backend/Dockerfile` (Python 3.12) |
| `db` | `localhost:5432` (usuario, contraseña y BD: `restoapi`) | `postgres:16` |

- Al arrancar, la API aplica las migraciones (`alembic upgrade head`) si ya existe `alembic.ini`.
- `VITE_API_URL` se fija en el build del frontend: si cambia, hay que reconstruir con `docker compose up --build`.
- Si el puerto 5432 está ocupado (otro Postgres instalado en el equipo), añadir `DB_PORT=5433` al `.env`: la BD queda en `localhost:5433`.
- Login: `POST /auth/login` como formulario OAuth2 (`username` = email, `password`) devuelve `{access_token, token_type}`. En Swagger (`/docs`), el botón **Authorize** hace el login y añade el token a las peticiones.
- Para levantar el frontend sin API se puede usar datos simulados: `VITE_USE_MOCK=true` en el `.env` y `docker compose up --build`.
- Primer admin (sin él nadie puede usar `/users`): `docker compose exec api python -m app.scripts.create_admin EMAIL PASSWORD [NOMBRE]`. Si el email ya existe, lo convierte en admin.
- Si el volumen de la BD de Docker se creó antes de Alembic, el arranque falla porque las tablas ya existen: marcarla una vez con `docker compose exec api alembic stamp 0001` y luego `docker compose exec api alembic upgrade head` (o recrearla con `docker compose down -v`).

## 8. Migraciones con Alembic (HU-23)

Los cambios en el modelo de datos se hacen con migraciones de Alembic (`migrations/versions/`), nunca a mano en la BD. La primera migración (`0001_esquema_inicial`) crea las 8 tablas tal como están en P2; la `0002_platos_preparados_y_servidos` añade las columnas `prepared` y `served` a `order_items`.

```bash
alembic upgrade head        # aplicar las migraciones pendientes
alembic current             # en qué migración está la BD
alembic check               # ¿hay cambios en los modelos sin migración?

# Después de cambiar un modelo:
alembic revision --autogenerate -m "descripción corta"
# Revisar el fichero generado en migrations/versions/ y probarlo con upgrade y downgrade
```

- La URL de la BD sale de `DATABASE_URL` (variable de entorno o `.env`), igual que en la app.
- El CI comprueba que hay una sola cabeza de migraciones, aplica `alembic upgrade head` sobre PostgreSQL y falla si los modelos no coinciden con las migraciones (`tests/test_migrations.py`).
- Si dos PRs crean migraciones a la vez, la segunda tiene que cambiar su `down_revision` para colgar de la primera (o crear una migración de `merge`).

### BD que ya existían antes de Alembic

Las BD creadas con `create_all` ya tienen las tablas: en ellas **no** se ejecuta la migración inicial, solo se marca como aplicada **una vez** (riesgo R18 del plan) y después se aplican las siguientes. Se ha comprobado que el esquema de Neon `main` y de la BD local coincide con `0001_esquema_inicial` (aún sin `prepared` ni `served`).

| BD | Qué hacer (una vez) |
|---|---|
| Neon `main` (producción) | `alembic stamp 0001` **antes** de desplegar la versión con Alembic (si no, el arranque intenta crear tablas que ya existen y falla); el arranque de Render aplica después la `0002` |
| Neon `dev` | Está vacía: `alembic upgrade head` |
| BD local (SQLite) creada antes de Alembic | `alembic stamp 0001` y `alembic upgrade head` |
| Volumen de Docker creado antes de Alembic | `docker compose exec api alembic stamp 0001` y `docker compose exec api alembic upgrade head`, o `docker compose down -v` |
| BD creada con `create_all` que ya tiene `prepared` y `served` | `alembic stamp head` |

Para lanzarlo contra Neon desde el equipo, igual que el primer admin: la URL solo en la variable de entorno de ese comando.

```bash
# PowerShell
$env:DATABASE_URL = "postgresql+psycopg://...neon.tech/restoapi?sslmode=require"
alembic stamp 0001
alembic upgrade head
Remove-Item Env:DATABASE_URL
```
