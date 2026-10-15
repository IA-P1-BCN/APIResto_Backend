# 🍽️ RestoAPI — Backend

API REST para la gestión de un restaurante: usuarios y roles, mesas, reservas, menú, pedidos, cocina en tiempo real, facturación, estadísticas y notificaciones por email.

> 🌐 **App en producción:** [apiresto-f5.vercel.app](https://apiresto-f5.vercel.app) · API: [restoapi-47sp.onrender.com](https://restoapi-47sp.onrender.com) ([Swagger](https://restoapi-47sp.onrender.com/docs))

> Frontend: [IA-P1-BCN/Resto-API_Frontend](https://github.com/IA-P1-BCN/Resto-API_Frontend) · Despliegue: [docs/deploy.md](docs/deploy.md) (solo Anna despliega) · Modelo de datos: [docs/er.md](docs/er.md) ([imagen](docs/er-diagram.png)) · Bitácora de IA: [docs/ai-log.md](docs/ai-log.md)

## Stack

| Capa | Tecnología |
|---|---|
| API | FastAPI + Uvicorn |
| ORM y migraciones | SQLAlchemy 2 + Alembic |
| Base de datos | PostgreSQL (Neon en producción, Docker en local) |
| Validación y config | Pydantic v2 + pydantic-settings |
| Auth | JWT (PyJWT) + bcrypt |
| Email | Brevo (vía httpx) |
| Caché | cachetools |
| Tests y calidad | pytest + pytest-cov + httpx · ruff |

## Puesta en marcha

Requisitos: **Python 3.12** y **Git**.

```bash
# 1. Clonar y situarse en dev
git clone https://github.com/IA-P1-BCN/Resto-API_Backend.git
cd Resto-API_Backend
git switch dev

# 2. Entorno virtual
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Windows (Git Bash):    source .venv/Scripts/activate
# macOS / Linux:         source .venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
cp .env.example .env    # y rellenar los valores
```

## Flujo de trabajo (Gitflow)

| Rama | Uso | Commits directos |
|---|---|---|
| `main` | Producción (Render + Neon `main`) | ❌ Nunca |
| `dev` | Integración, rama por defecto | ❌ Nunca |
| `feature/HU-XX-descripcion` | Una rama por HU, sale de `dev` | ✅ Solo su dueña/o |
| `fix/HU-XX-descripcion` | Bug detectado en `dev` | ✅ Solo su dueña/o |
| `hotfix/descripcion` | Urgencia en producción, sale de `main` | ✅ Solo su dueña/o |

```bash
# Empezar una HU
git switch dev
git pull origin dev
git switch -c feature/HU-07-crear-pedido

# Antes de abrir el PR
git pull origin dev     # traer lo último de dev y resolver conflictos en TU rama
pytest
git push -u origin feature/HU-07-crear-pedido
```

1. PR **`feature/...` → `dev`** con título `[HU-XX] Descripción` y `Closes #N`.
2. Lo revisa, aprueba y mergea **otra persona** (*Squash and merge*). La rama se borra automáticamente.
3. Quien mergea avisa en el canal: `✅ Mergeado #N [HU-XX] en dev → ¡haced pull!`
4. Todo el equipo actualiza su rama: `git pull origin dev`.
5. Al cierre de cada sprint: PR `dev` → `main` (*merge commit*) → despliegue.

**Commits** — [Conventional Commits](https://www.conventionalcommits.org/es/):
`feat(pedidos): ...` · `fix(reservas): ...` · `test(auth): ...` · `docs(api): ...` · `ci: ...` · `chore(deps): ...`

## Agente de código: OpenCode con modelos gratuitos (HU-21)

El repo trae `opencode.json` con modelos gratuitos de OpenCode Zen, que funcionan sin cuenta ni clave. Al abrir una sesión, OpenCode lee `AGENTS.md`.

```bash
npm install -g opencode-ai                          # instalar (una vez)
opencode                                            # abrir en la carpeta del repo
opencode run "tu pregunta" --agent plan             # una consulta que no toca ficheros
```

| Uso | Modelo | Por qué |
|---|---|---|
| Por defecto (`model`) | `opencode/big-pickle` | El más rápido y completo en la prueba de humo (16 s) |
| Tareas cortas, como títulos (`small_model`) | `opencode/mimo-v2.6-flash-free` | Rápido y correcto en la misma prueba |
| Alternativas probadas | `opencode/longcat-2.5-preview-free`, `opencode/nemotron-3-ultra-free` | Se eligen con `/models` o con `-m` |

- **Agentes:** `plan` solo lee y propone; `build` edita y ejecuta comandos. Empieza cada HU en `plan` y pasa a `build` cuando el plan esté claro.
- **Push:** OpenCode pide confirmación antes de cualquier `git push` (`permission` en `opencode.json`). Aun así, nunca se hace push a `main` ni a `dev` (ver `AGENTS.md`).
- **Privacidad:** con Big Pickle, mientras sea gratuito, el proveedor puede usar las conversaciones para mejorar el modelo; los Nemotron son de prueba. No pegues secretos, `.env` ni datos personales. LongCat 2.5 Preview Free usa un proveedor que no guarda los datos.
- **Disponibilidad:** los modelos gratuitos cambian con el tiempo; la lista actual sale con `opencode models opencode`.
- **Proveedor propio** (por ejemplo, un router local con tus claves): elígelo con `/models` y déjalo en tu configuración personal (`~/.config/opencode/opencode.json`), nunca en el `opencode.json` del repo.
- **Prueba de humo** (HU-20): `opencode run "¿Qué roles existen y qué no debes hacer?" --agent plan` debe responder con los 5 roles (`admin`, `waiter`, `kitchen`, `bartender`, `customer`) y las prohibiciones de `AGENTS.md`.

## Reglas

- `.env` nunca se sube; solo `.env.example` sin valores reales.
- Una sola persona (Carla) mergea migraciones de Alembic en `dev`, de una en una.
- PRs pequeños (idealmente < 400 líneas).
- Si usas un agente de IA (Claude Code, OpenCode), añade tu entrada en [docs/ai-log.md](docs/ai-log.md) en la misma PR.
