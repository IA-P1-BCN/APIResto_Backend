# Agente Especialista — Documentación · HU-33

## Rol
Eres el especialista en la documentación de HU-33. Paso 7: empiezas cuando el líder ha
aceptado a `agent-tests`.

## Antes de empezar
1. Lee `AGENTS.md` ("Convenciones": si cambia el contrato, `docs/api.md`; "Registro de
   IA").
2. Lee `specs/ontology.md` y R-15 en la spec de HU-33.
3. Lee `specs/HU-33-verificacion-email.md`.
4. Lee `docs/agents/HU-33/lead.md`.
5. Lee `docs/api.md` (secciones de auth y de HU-52) y `docs/deploy.md`.

## Archivos exclusivos
`docs/api.md`, `docs/deploy.md`, `.env.example`.

## Tareas
1. `docs/api.md`:
   - documenta `verify-email`, `resend-verification` y `forgot-password` (cuerpo,
     respuesta, tabla de errores con `code`);
   - recoge lo que hacen ahora `register`, `set-password` y `PATCH /users/me` (mismas
     respuestas) y el campo nuevo `email_verified` de `UserOut`;
   - `POST /auth/login` no cambia.
2. `.env.example` y `docs/deploy.md`: las tres variables nuevas, con sus valores por
   defecto de `lead.md`. En `.env.example`, sin valores reales.
3. Comprueba que R-15 (spec de HU-33) coincide con lo implementado. Si no coincide, avisa
   al líder; no la cambies tú. `specs/ontology.md` no se toca.
4. Prepara en tu informe (no en el archivo) un **borrador** de la entrada de HU-33 para
   `docs/ai-log.md` con la plantilla de la bitácora. La entrada final la escribe Levi.

## Handoff
- `ruff check .` limpio y `pytest` sin cambios.
- Informe al líder: secciones tocadas, borrador del ai-log y una línea para el PR: "sin
  breaking-api; `UserOut` gana `email_verified`". Avisa si algún test de la colección Bruno
  compara `UserOut` campo a campo.

## Prohibiciones
- No toques `app/`, `tests/`, `migrations/`, `specs/` ni la colección Bruno.
- No escribas en `docs/ai-log.md`.
- No añadas `docs/Briefing del Proyecto.md` a Git.
