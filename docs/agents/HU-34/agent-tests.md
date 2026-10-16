# Agente Especialista — Tests · HU-34

## Rol
Eres el especialista que cubre las 10 sentencias sin cubrir de HU-34. Paso 1.

## Antes de empezar
1. Lee `AGENTS.md`, "Los tests son el contrato".
2. Lee `specs/ontology.md` (R-02, R-13, R-14).
3. Lee `specs/HU-34-cobertura-tests.md`, "Implementation Decisions" y "Testing Decisions".
4. Lee `docs/agents/HU-34/lead.md` (parámetros compartidos).
5. Lee los 4 módulos con huecos y sus tests: `tests/test_order_items_quantities.py`,
   `tests/test_keep_awake.py`, `tests/test_social_login.py`, `tests/test_stats.py`.

## Archivos exclusivos
`tests/test_order_items_quantities.py`, `tests/test_keep_awake.py`,
`tests/test_social_login.py`, `tests/test_stats.py`. Solo añadir.

## Tareas
1. `test_order_items_quantities.py`: añade `{"served": True, "served_quantity": 1}` al
   parametrize de `test_rechaza_cantidades_negativas_o_los_dos_campos_a_la_vez`. Es el
   único cambio permitido en un test existente.
2. `test_keep_awake.py`: `test_run_sleeps_between_pings`. Llama a `_run` directamente
   (sin hilo) con un `ping` que activa `stop` en la 2.ª llamada y un `sleep` que guarda
   los segundos. Comprueba 2 pings a la URL y `sleeps == [600]`.
3. `test_social_login.py`, con el fixture `provider_api` y `_login`:
   - `test_provider_bad_responses_are_502`, parametrizado: userinfo de Google `(500, {})`,
     userinfo de Google sin `sub`, token de GitHub `(500, {})`, usuario de GitHub sin
     `id`. Comprueba `502` y `code == "provider_unavailable"`.
   - `test_google_token_without_access_token_is_401`: token de Google `(200, {})`.
     Comprueba `401` y `code == "invalid_code"`.
   - `test_provider_invalid_json_is_502`: `monkeypatch` local de
     `providers.httpx.request` que devuelve
     `httpx.Response(200, content=b"<html>", request=httpx.Request("POST", "http://test"))`.
     Comprueba `502` y `code == "provider_unavailable"`. No modifiques `provider_api`.
4. `test_stats.py`: `test_as_date_accepts_postgres_date_and_sqlite_text`, parametrizado con
   `date(2026, 10, 1)` y `"2026-10-01"`; los dos devuelven `date(2026, 10, 1)`.
5. Antes de escribir cada test, comprueba que no existe otro que pruebe lo mismo. Si lo
   hay, avisa al líder en vez de escribirlo.

## Handoff
- `pytest --cov=app --cov-report=term-missing`: 100 %, 0 sentencias sin cubrir.
- Los 746 tests de partida pasan sin cambios.
- `ruff check .` limpio.
- Informe al líder: tests nuevos (funciones y ejecuciones), la línea que cubre cada uno y
  la confirmación de que ningún test existente se ha modificado salvo el parametrize.

## Prohibiciones
- No toques `app/`, `tests/conftest.py` ni otros archivos de tests. Si un test revela un
  bug, repórtalo al líder y para.
- No borres, renombres ni debilites tests. No uses `skip`.
- No añadas `# pragma: no cover` ni comentarios `#`.
- Sin red ni `sleep` real; sin hilos en el test de `_run`.
