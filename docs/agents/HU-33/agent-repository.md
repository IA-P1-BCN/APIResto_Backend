# Agente Especialista — Repositorios · HU-33

## Rol
Eres el especialista en las consultas a la BD de HU-33. Paso 2: empiezas cuando el líder
ha aceptado a `agent-model`.

## Antes de empezar
1. Lee `AGENTS.md` (sección "Estructura": los repositorios solo hacen consultas, sin
   HTTP ni reglas).
2. Lee `specs/ontology.md` (R-09).
3. Lee `specs/HU-33-verificacion-email.md`.
4. Lee `docs/agents/HU-33/lead.md`.
5. Lee como referencia `app/repositories/password_reset_token_repository.py` (HU-52).

## Archivos exclusivos
`app/repositories/email_verification_token_repository.py` (nuevo) y
`app/repositories/password_reset_token_repository.py` (**solo añadir** funciones; el
código de HU-52 no se cambia; avisa al líder para que se lo comunique a Anna).

## Tareas
1. En `email_verification_token_repository.py`, con el estilo de HU-52:
   - `add(db, token)`;
   - `get_by_hash_for_update(db, token_hash)` (bloquea la fila con `FOR UPDATE`);
   - `list_pending_for_user(db, user_id)` (`used_at` nulo);
   - `get_latest_for_user(db, user_id)` (el de `created_at` más reciente, o `None`).
2. En `password_reset_token_repository.py`, añade solo `get_latest_for_user(db, user_id)`.
3. Sin reglas: ni "caducado", ni el tiempo de espera, ni marcar `used_at`. Eso lo decide
   el servicio.

## Handoff
- `ruff check .` limpio y `pytest` sin fallos nuevos.
- Informe al líder: firmas exactas de cada función y si devuelven `None` o una lista vacía.

## Prohibiciones
- No toques modelos, servicios, routers ni tests.
- No hagas commit dentro de funciones que no lo necesiten; sigue el patrón de HU-52.
- Sin comentarios `#`.
