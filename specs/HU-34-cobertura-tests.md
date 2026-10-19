# HU-34 · Cobertura de tests ≥ 80 %

> Issue: #77 · Prioridad: la de la issue #77 · Escribe: Levi · Revisa: otra persona del
> equipo · Aprueba: Levi (PO). Vocabulario: `specs/ontology.md`. Reglas del repo:
> `AGENTS.md`. Equipo de agentes: `docs/agents/HU-34/`.
> Sin breaking-api: no cambia ningún endpoint, modelo ni schema. Solo tests y CI.

## Problem Statement
La issue pide una cobertura de tests ≥ 80 %. Medida el 16/10/2026 sobre `dev` (`e6164f4`)
con `pytest --cov=app --cov-report=term-missing`: **746 passed, 99 % (2442 sentencias,
10 sin cubrir)**. El objetivo ya está superado.

Lo que de verdad falta:
- 10 sentencias sin cubrir en 4 módulos. Todas son código que se ejecuta en producción
  (respuestas raras de proveedores OAuth, el bucle del keep-awake, la rama de Postgres de
  las estadísticas y una validación de pedidos).
- El CI no protege la cobertura alcanzada: `ci.yml` ejecuta
  `--cov-fail-under=${{ vars.COVERAGE_MIN || 0 }}`. Si la variable de GitHub no existe,
  exige `0`; `docs/deploy.md` documenta `70` para el Sprint 2. Una HU futura podría bajar
  la cobertura 25 puntos sin que el CI lo note.

## Solution
1. Cubrir las 10 sentencias con 5 tests nuevos y 1 caso añadido a un parametrize
   existente, sin tocar `app/` ni los tests y fixtures existentes (salvo ese caso).
2. Subir el umbral a **98 %**: valor por defecto en `.github/workflows/ci.yml`
   (`vars.COVERAGE_MIN || 98`) y la variable `COVERAGE_MIN` de GitHub a `98` (o borrada),
   que la cambia Levi.
3. Documentar el umbral en `docs/deploy.md` y cerrar la HU en `docs/ai-log.md`.

## User Stories
1. Como equipo, queremos que el CI falle si una HU baja la cobertura, para no perder
   lo ganado sin enterarnos.
2. Como revisora de PR, quiero que los casos de error de los proveedores OAuth estén
   probados, para saber que un Google o un GitHub caído o raro devuelve un 401/502 limpio.
3. Como PO, quiero cerrar la issue #77 con una medición real y un umbral razonable, no
   con un número inflado con pragmas.

## Implementation Decisions

### Los 10 huecos (ninguno es inalcanzable)
| Archivo:línea | Qué hay | Por qué no se ejecuta hoy |
|---|---|---|
| `app/schemas/schema_order.py:45` | `served` y `served_quantity` a la vez → `ValueError` (422) | El parametrize de `tests/test_order_items_quantities.py` solo prueba la pareja `prepared` |
| `app/services/keep_awake.py:57` | `sleep(interval_seconds)` en el bucle de `_run` | El único test activa `stop` en el primer ping y el bucle sale antes de dormir |
| `app/services/social_providers.py:59-60` | Respuesta 200 que no es JSON → 502 `provider_unavailable` | El fixture `provider_api` siempre crea respuestas con `json=` |
| `app/services/social_providers.py:84` | Google responde 200 sin `access_token` → 401 `invalid_code` | Solo existe el caso equivalente de GitHub |
| `app/services/social_providers.py:90` | Userinfo de Google ≠ 200 → 502 | Sin caso |
| `app/services/social_providers.py:93` | Userinfo de Google sin `sub` → 502 | Sin caso |
| `app/services/social_providers.py:118` | Token de GitHub ≠ 200 → 502 | Solo se prueba GitHub 200 con `error` (401) |
| `app/services/social_providers.py:132` | Usuario de GitHub sin `id` → 502 | Sin caso |
| `app/services/stats.py:75` | `_as_date` recibe un `date` (lo que devuelve Postgres) | `tests/conftest.py` usa siempre SQLite en memoria, que devuelve texto |

No se usa `# pragma: no cover` en ninguna línea: todas son ramas que corren en producción
y un pragma ocultaría justo el camino real (sobre todo `stats.py:75`, que es el de
Postgres).

### Comportamiento que se documenta, no se cambia
- Google trata un 4xx del endpoint de token como `401 invalid_code`; GitHub trata
  cualquier respuesta ≠ 200 como `502 provider_unavailable`. Es coherente: GitHub
  responde 200 con `error` cuando el `code` es malo (eso ya da 401). Los tests nuevos
  fijan este comportamiento tal cual.
- `tests/test_keep_awake.py:74`: el `assert seconds == 10 * 60` de `fake_sleep` nunca se
  ejecuta. No se modifica; el test nuevo de `_run` comprueba el intervalo de verdad.

### Capas afectadas
Ninguna de `app/`. Si un test nuevo revela un bug real, se para y se avisa a Levi.

## Testing Decisions
Tests nuevos, archivo a archivo (10 ejecuciones nuevas en pytest: 746 → 756):

| Archivo | Test | Cubre | Assert |
|---|---|---|---|
| `tests/test_order_items_quantities.py` | Caso `{"served": True, "served_quantity": 1}` añadido al parametrize de `test_rechaza_cantidades_negativas_o_los_dos_campos_a_la_vez` | `schema_order.py:45` | `422` |
| `tests/test_keep_awake.py` | `test_run_sleeps_between_pings` | `keep_awake.py:57` | Llama a `_run` de forma síncrona (sin hilo) con un `ping` que activa `stop` en la 2.ª llamada: 2 pings a la URL y `sleeps == [600]` |
| `tests/test_social_login.py` | `test_provider_bad_responses_are_502`, parametrizado con 4 casos: userinfo de Google 500, userinfo de Google sin `sub`, token de GitHub 500, usuario de GitHub sin `id` | `social_providers.py:90, 93, 118, 132` | `502` y `code == "provider_unavailable"` |
| `tests/test_social_login.py` | `test_google_token_without_access_token_is_401` | `social_providers.py:84` | `401` y `code == "invalid_code"` |
| `tests/test_social_login.py` | `test_provider_invalid_json_is_502` | `social_providers.py:59-60` | `monkeypatch` local de `httpx.request` que devuelve `httpx.Response(200, content=b"<html>")`; `502` y `code == "provider_unavailable"` |
| `tests/test_stats.py` | `test_as_date_accepts_postgres_date_and_sqlite_text`, parametrizado con `date(2026, 10, 1)` y `"2026-10-01"` | `stats.py:75` | Devuelve `date(2026, 10, 1)` en los dos casos |

Reglas para los tests:
- No se modifica ni se borra ningún test ni fixture existente, salvo el caso añadido al
  parametrize (lo refuerza, no lo debilita). `tests/conftest.py` no se toca.
- Sin red ni proveedores reales: todo con `monkeypatch` o el fixture `provider_api`.
- Sin `sleep` real ni hilos en el test de `_run`.
- Docstrings breves y sin comentarios `#`, como el resto de `tests/`.

## Reglas R-xx aplicables
Ninguna regla de la ontología cambia. Los tests nuevos tocan código de:
- **R-13** (login social): los casos de error de `social_providers.py`.
- **R-02** (nada sensible en los logs): los tests de `social_providers.py` no deben
  registrar el `code` ni los tokens; `test_secrets_and_code_are_not_logged` ya lo
  comprueba y no se duplica.
- **R-14** (estaciones): el endpoint de líneas de pedido; el caso nuevo es solo de
  validación (422) y no prueba permisos.

## Criterios de aceptación
- [ ] `pytest` en verde: 746 tests al empezar + los nuevos, ninguno modificado salvo el
      caso añadido al parametrize.
- [ ] `pytest --cov=app --cov-report=term-missing`: **100 %** (0 sentencias sin cubrir).
- [ ] `ruff check .` limpio.
- [ ] Ningún `# pragma: no cover` ni cambio en `app/`.
- [ ] `.github/workflows/ci.yml`: `--cov-fail-under=${{ vars.COVERAGE_MIN || 98 }}`.
- [ ] Variable `COVERAGE_MIN` de GitHub a `98` o borrada (la cambia Levi; si sigue en
      `70`, manda sobre el valor de `ci.yml`).
- [ ] `docs/deploy.md` documenta el umbral de 98.
- [ ] Cobertura medida de nuevo sobre el `dev` que haya al abrir el PR (por si HU-33 u
      otra HU ya están mergeadas).
- [ ] Entrada de HU-34 en `docs/ai-log.md` (la escribe Levi).
- [ ] PR revisada por otra persona y aprobada por Levi (PO).

## Out of Scope
- Auditoría de la calidad de los tests existentes (salvo avisar de lo visto, como el
  assert de `test_keep_awake.py:74`).
- Tests E2E y la colección Bruno.
- Cobertura del frontend.
- Refactor de `app/`.
- Ejecutar los tests contra Postgres en CI: `conftest.py` usa siempre SQLite. Se apunta
  como issue aparte, junto con la corrección de `AGENTS.md` ("el CI usa Postgres y puede
  fallar donde tú no viste nada"), que hoy no es cierta.

## Preguntas abiertas
(vacío: spec lista para implementar)

## Decisiones de la sesión

### Umbral del 98 % en `ci.yml`
- **Decisión**: valor por defecto `98` en `ci.yml` (`vars.COVERAGE_MIN || 98`); Levi pone
  la variable de GitHub a 98 o la borra.
- **Por qué**: queda versionado y se revisa en el PR. 98 deja unas 49 sentencias de margen
  a las próximas HU y detecta cualquier bajada real.
- **Alternativas rechazadas**: 100 % (cualquier rama defensiva nueva bloquearía un PR y
  empujaría a usar pragmas); dejar solo la variable de GitHub (no se ve en el repo).

### Sin `# pragma: no cover`
- **Decisión**: se cubren las 10 líneas; no se marca ninguna.
- **Por qué**: ninguna es inalcanzable. `stats.py:75` es la rama de Postgres, la que corre
  en producción.
- **Alternativas rechazadas**: pragma en `stats.py:75` y en `social_providers.py:59-60`.

### Equipo en `docs/agents/HU-34/`
- **Decisión**: el equipo va en `docs/agents/HU-34/`, no en `specs/agents/`.
- **Por qué**: es donde ya están HU-25 y HU-27 en `dev` y adonde la rama de HU-33 mueve
  todos los equipos.
- **Alternativas rechazadas**: `specs/agents/HU-34/` (habría que moverlo al mergear HU-33).

### Caso añadido al parametrize de `schema_order`
- **Decisión**: el hueco de `schema_order.py:45` se cubre con un caso más en el parametrize
  existente de `test_order_items_quantities.py`.
- **Por qué**: el nombre del test ya dice "los dos campos a la vez"; un test aparte
  repetiría el mismo patrón.
- **Alternativas rechazadas**: un test nuevo para la pareja `served`.

### Orden con HU-33
- **Decisión**: no se espera a HU-33; la cobertura se vuelve a medir sobre `dev` al abrir
  el PR.
- **Por qué**: la rama de HU-33 no toca los 4 módulos ni los 4 archivos de test; solo añade
  líneas a `tests/conftest.py`, que esta HU no toca.
- **Alternativas rechazadas**: esperar a que se mergee HU-33.

Todas las decisiones: Levi (PO), 16/10/2026.
