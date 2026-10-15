# Bitácora de IA (ai-log)

Registro de cómo usa el equipo los agentes de IA (Claude Code, OpenCode) para desarrollar
RestoAPI. Es un entregable de P3: deja trazabilidad de qué generó el agente, qué
aceptamos, qué corregimos y qué aprendimos para la siguiente HU.

## Cómo rellenarla

- **Quién:** la persona que lanzó la sesión con el agente. La entrada la escribe ella,
  no el agente (ver `AGENTS.md`, sección "Registro de IA").
- **Cuándo:** después de cada sesión relevante (genera código, tests o documentación, o
  sale una decisión). La entrada va en la **misma PR** que el trabajo.
- **Dónde:** en la sección de su HU, dentro de "Entradas". Si la sección no existe, se
  crea en orden numérico. Dentro de cada HU, la entrada más reciente va al final.
- **Cómo:**
  - Corta: debería llevar unos cinco minutos.
  - Causa raíz, no síntoma. "El agente se equivocó" no sirve; "el prompt no decía que
    el registro ignora el rol del payload (R-03)" sí.
  - Datos comprobables: commits, PR, tests o comandos, no de memoria.
  - Cita las reglas de `specs/ontology.md` por su id (R-xx).
  - Si un campo no aplica, escribe "nada"; no lo borres.
- **Lecciones:** si la misma lección sale en dos entradas, se propone como regla en
  `AGENTS.md` en una PR aparte.

## Plantilla

Copia este bloque en la sección de tu HU:

```markdown
#### AAAA-MM-DD · Título corto de la sesión · @usuario-github

- **Herramienta y modelo:** Claude Code · modelo / OpenCode · modelo gratuito
- **Issue y reglas:** #N · R-xx
- **Prompt clave:** el texto o un resumen
- **Resultado:** aceptado / aceptado con cambios / rechazado, y por qué
- **Errores o alucinaciones:** qué hizo mal o inventó, causa raíz y cómo se corrigió
- **Trabajo descartado:** qué se rehízo o no se usó, y por qué
- **Mi prompt o la spec:** qué faltaba o era ambiguo
- **Decisiones humanas:** reglas que faltaban y decidió una persona (quién)
- **Lección:** una línea para la próxima sesión
```

## Ejemplo (ficticio, solo para orientar)

```markdown
#### 2026-10-15 · Endpoint de registro · @usuario-ejemplo

- **Herramienta y modelo:** OpenCode · modelo gratuito X
- **Issue y reglas:** #00 · R-01, R-02, R-03
- **Prompt clave:** "Implementa POST /auth/register según la issue y specs/ontology.md"
- **Resultado:** aceptado con cambios. El endpoint y los tests eran correctos salvo el rol.
- **Errores o alucinaciones:** guardaba el `role` que llegaba en el payload, así que
  cualquiera podía registrarse como `admin`. Causa raíz: el agente no leyó la
  ontología. Corregido forzando `customer` y con un test que envía `role=admin`.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** el prompt no citaba R-03; lo daba por sabido.
- **Decisiones humanas:** nada
- **Lección:** citar en el prompt las reglas R-xx que afectan a la HU.
```

## Entradas

<!-- Una sección por HU: "### HU-XX · Título de la HU", con sus entradas debajo. -->

### HU-21 · Configuración de OpenCode con modelos gratuitos

#### 2026-10-14 · Configurar OpenCode y elegir modelos gratuitos · @costanna

- **Herramienta y modelo:** Claude Code para preparar la configuración y la documentación; OpenCode 1.18.34 para las pruebas · `opencode/big-pickle` (por defecto), `mimo-v2.6-flash-free`, `longcat-2.5-preview-free` y `nemotron-3-ultra-free` (comparación)
- **Issue y reglas:** #63 · nada (HU de configuración)
- **Prompt clave:** prueba de humo de la HU-20 ("¿Qué roles existen y qué no debes hacer?") con cinco modelos gratuitos, y revisión en modo `plan` de la migración 0006 de la PR #119 como prueba con una HU real
- **Resultado:** aceptado. Los cuatro modelos que respondieron dieron los 5 roles y las prohibiciones de `AGENTS.md`; big-pickle fue el más rápido (16 s) y se dejó por defecto en `opencode.json`. La revisión de la migración fue correcta (cadena 0004 → 0005 → 0006, conversión segura y pérdida de recuentos parciales al bajar).
- **Errores o alucinaciones:** `ling-3.1-flash-free` devolvió un error del servicio. En la revisión, big-pickle avisó de un caso con `quantity = 0` que no puede darse porque la BD exige `quantity > 0`: solo tenía la migración adjunta, no el modelo.
- **Trabajo descartado:** `ling-3.1-flash-free` como opción
- **Mi prompt o la spec:** en `opencode run`, la opción `-f` se tragó el texto de la pregunta como si fuera otro fichero; el mensaje tiene que ir antes de `-f`.
- **Decisiones humanas:** big-pickle por defecto para todo el equipo aunque yo uso mi propio proveedor (lo cambio con `/models`); documentar OpenCode en el README (Anna).
- **Lección:** para consultas que no deben tocar ficheros, usar `--agent plan`, y adjuntar con `-f` todo lo que la pregunta necesita (por ejemplo, el modelo además de la migración).

### HU-53 · Bitácora de IA

#### 2026-10-14 · Creación de la bitácora · @arita-pereira

- **Herramienta y modelo:** Claude (claude.ai, no Claude Code) · Opus 5.5
- **Issue y reglas:** #111 · nada (HU de documentación)
- **Prompt clave:** crear la bitácora usando como base la skill de retro de Manon
- **Resultado:** aceptado con cambios. El archivo final sigue la sección "Registro de IA" de `AGENTS.md` y añade ideas de la skill de Manon (causa raíz, trabajo descartado, autocrítica del prompt, lección).
- **Errores o alucinaciones:** la primera propuesta del agente llevaba un campo "Spec" (`specs/HU-XX.md`) y una skill para que el agente redactara la entrada. Causa raíz: la propuso antes de leer el repo; en `dev` ya estaba `AGENTS.md`, que dice que la entrada la escribe la persona, y el equipo decidió el 13/10 no hacer spec por HU. Se corrigió al revisar `dev`.
- **Trabajo descartado:** el campo "Spec" y el paso 3 (la skill).
- **Mi prompt o la spec:** no le dije que `AGENTS.md` ya definía el registro de IA ni que no hay spec por HU; lo descubrió al leer `dev`.
- **Decisiones humanas:** separar HU-21 en HU-21 (OpenCode, Anna) y HU-53 (bitácora, Rita), decidido por mí.
- **Lección:** antes de pedir una propuesta, pedir al agente que lea `AGENTS.md` y el estado de `dev`.


### HU-24 · Filtros admin de usuarios

#### 2026-10-15 · Spec, filtros, búsqueda y paginación de GET /users · @arita-pereira

- **Herramienta y modelo:** Claude (claude.ai, no Claude Code) · Opus 5.5
- **Issue y reglas:** #67 · R-11 (`include_deleted` de HU-32)
- **Prompt clave:** "empezamos el HU-24", con el estado del proyecto adjunto; la issue solo tenía la historia, sin criterios de aceptación
- **Resultado:** aceptado. Spec en `specs/HU-24-filtros-admin.md` y `GET /users/` con `Page[UserOut]`, `role`, `is_active` y `q`. 589 tests en verde con SQLite y Postgres 16.
- **Errores o alucinaciones:** en la cabecera de la spec puso "Aprueba: Levi (PO)", copiado de `specs/HU-TEMPLATE.md`. Causa raíz: la plantilla y la DoD de `AGENTS.md` aún dicen que aprueba Levi, pero el equipo ya no depende de él. Corregido a "Revisa y aprueba: Manon". Además, no preparó los comentarios de cada paso para el issue hasta que lo eché en falta.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** la issue no tenía criterios de aceptación; los fijó la spec con cuatro preguntas (formato, filtros, búsqueda y orden).
- **Decisiones humanas:** `Page[UserOut]` aunque sea breaking-api, filtros `role` + `is_active`, un solo `q` en nombre o email, orden fijo por `id` (Rita).
- **Lección:** leer `AGENTS.md` y `dev` antes de empezar funcionó otra vez: detectó que la PR #110 había vuelto a exigir spec por HU, y que HU-32 ya fijaba `include_deleted`.
