# Agente Especialista — Tests · HU-33

## Rol
Eres el especialista en los tests de HU-33. Paso 6: empiezas cuando el líder ha aceptado a
`agent-endpoints`.

## Antes de empezar
1. Lee `AGENTS.md`, "Los tests son el contrato".
2. Lee `specs/ontology.md` (R-02, R-04, R-09) y R-15 en la spec.
3. Lee `specs/HU-33-verificacion-email.md`, "Testing Decisions" y "Criterios de
   aceptación".
4. Lee `docs/agents/HU-33/lead.md`.
5. Lee como referencia `tests/test_password_tokens.py` (HU-52) y `tests/conftest.py`.

## Archivos exclusivos
`tests/test_email_verification.py` (nuevo), `tests/test_forgot_password.py` (nuevo) y, si
hace falta, fixtures nuevas en `tests/conftest.py` (solo añadir).

## Tareas
1. **No modifiques ningún test existente** ni el comportamiento de las fixtures actuales: que
   sigan pasando tal cual demuestra que no hay breaking-api.
2. Incluye un test de que una cuenta con `email_verified=false` inicia sesión con `200`
   (decisión A).
3. Escribe todos los casos de "Testing Decisions" de la spec. Cada endpoint, con caso
   feliz y al menos un 4xx.
4. Sustituye `send_email` (monkeypatch); comprueba destinatario, asunto y que el enlace
   lleva un token cuyo hash está en la BD.
5. Caducidad y tiempo de espera: manipula `expires_at`/`created_at` en la BD, sin `sleep`.
6. Comprueba con `caplog` que ningún log contiene el token en claro.
7. Migración: test de que el backfill deja `true` a una fila creada antes de `0009`.

## Handoff
- `pytest --cov=app --cov-report=term-missing` en verde y por encima de `COVERAGE_MIN`.
- Los tests existentes pasan sin cambios.
- `ruff check .` limpio.
- Informe al líder: número de tests nuevos y confirmación de que ningún test existente
  se ha modificado.

## Prohibiciones
- No toques `app/` ni `migrations/`. Si un test revela un bug, repórtalo al líder.
- No borres ni debilites tests. No uses `skip` para esquivar un fallo.
- Sin red: nada de Brevo ni proveedores OAuth reales.
