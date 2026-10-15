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

### HU-40 · Estación de barra en los pedidos

#### 2026-10-15 · HU-40_Estación de barra en los pedidos  · @ManonChab

- **Herramienta y modelo:** Claude Code with Sonnet 5.5
- **Issue y reglas:** #83
- **Prompt clave:**  "Read the necessary doc, the repo back and front, the kanban and let's start the new       H-40U,starting by spec definition"
- **Resultado:** aceptado 
- **Errores o alucinaciones:**
  - The one-line issue: I found the real gap by reading the code, and invented nothing.
  - The empty WebSocket assertion I wrote and then replaced.
  - The lazy="joined" draft I changed.
  - The two old tests that R-14 broke. I changed their data and didn't weaken them.
- **Trabajo descartado:** //
- **Mi prompt o la spec:**
    · ¿Qué entrega el backend en HU-40? Hoy el filtro por estación solo existe en el frontend (StationBoard); el  backend manda todo a cocina y a barra. → Filtrar en el backend (Recomendado)
    · El `status` del pedido es único (pending → in_kitchen → served) y hoy lo mueve cualquiera de cocina/barra. Con dos estaciones, ¿qué hacemos en esta HU? → Dejarlo como está (Recomendado)
    · En el pedido filtrado que ve `kitchen`/`bartender`, ¿qué se devuelve en `total`? → El del pedido completo (Recomendado)
    · Si el admin cambia la `station` de una categoría con pedidos abiertos, ¿qué pasa con las líneas ya creadas? → Se derivan en vivo (Recomendado)
    · Producción (Neon): las categorías existentes quedaron `kitchen` por defecto. ¿Cómo pasan Bebidas y Postres a `bar`? → Migración de datos
    · El enrutado por estación no está en la ontología (solo se cita como referencia externa). ¿Añadimos una regla R-14 a specs/ontology.md en el mismo PR? → Sí, R-14 (Recomendado)
- **Decisiones humanas:**

```text
   Tema     │                            Decisión                            │
├──────────────┼────────────────────────────────────────────────────────────────┤
│              │ El backend filtra según el rol: kitchen ve y marca solo líneas │
│ Alcance      │  kitchen, bartender solo bar, y admin/waiter ven todo. Esto    │
│              │ vale para GET /orders, GET /orders/{id}, PATCH .../items/{id}  │
│              │ y el WebSocket.                                                │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Contrato     │ Cada línea del pedido expone station. No hay parámetro         │
│              │ ?station=. total sigue siendo el del pedido completo.          │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Estado del   │ Sin cambios. El estado por producto o estación es HU-45 de     │
│ pedido       │ Rita, que toca el mismo router, así que hay que avisarla.      │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Estación de  │ Se deriva en vivo de la categoría actual del plato. No hay     │
│ una línea    │ columna nueva.                                                 │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Datos de     │ Migración 0007 que marca Bebidas y Postres como bar. Elegí     │
│ producción   │ esto frente a la opción recomendada, que era que el admin las  │
│              │ marcara.                                                       │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Ontología    │ Se añade la regla R-14 a specs/ontology.md en el mismo PR.     │
│              │ Necesita el visto bueno de Levi.
```

- **Lección:** //
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

#### 2026-10-15 · Revisión de Manon: acentos, longitud de q y skip/limit · @arita-pereira

- **Herramienta y modelo:** Claude (claude.ai, no Claude Code) · Opus 5.5
- **Issue y reglas:** #67 (PR #126 ya integrada) · nada
- **Prompt clave:** los tres comentarios de Manon en la PR #126
- **Resultado:** aceptado. Búsqueda sin acentos con `translate()` (`app/core/text_search.py`), `q` con máximo 100 caracteres y casillas de la spec marcadas.
- **Errores o alucinaciones:** en la PR #126 el agente afirmó que los tests pasaban "con SQLite y con Postgres 16", y era falso: `tests/conftest.py` usa siempre SQLite en memoria, aunque se le pase la URL de Postgres. Causa raíz: dio por bueno que cambiar `DATABASE_URL` cambiaba la base de datos de los tests, sin leer el `conftest.py`. Por eso no vio que el `lower()` no quita los acentos. Corregido probando la consulta directamente contra Postgres. Además, el primer intento (48 `replace()` anidados) desbordó la pila de SQLite.
- **Trabajo descartado:** los `replace()` anidados; la extensión `unaccent` (migración y no existe en SQLite).
- **Mi prompt o la spec:** la spec no decía nada de acentos, aunque el equipo trabaja con nombres en español y portugués.
- **Decisiones humanas:** `translate()` sin migración; `skip`/`limit` sin 422, solo la etiqueta `breaking-api` (Rita).
- **Lección:** antes de decir "probado en X", comprobar qué base de datos usan los tests de verdad.

### HU-25 · Cambio de contraseña y edición del propio perfil                                                                                                                     
                                                                                                                                                                                   
#### 2026-10-15 · Perfil propio y cambio de contraseña con un equipo de agentes · @levifvy                                                                                       
                                                                                                                                                                                   
- **Herramienta y modelo:** Claude Code · Opus 5.5. Usé un agente líder que coordinaba a cinco ayudantes, cada uno con una parte del trabajo: los datos de entrada, las reglas,  
los endpoints, los tests y la documentación.                                                                                                                                     
- **Issue y reglas:** #68 · R-01, R-02, R-03, R-04, R-11                                                                                                                         
- **Prompt clave:** le pedí que hiciera de líder del equipo para la HU-25 y que, antes de empezar, me confirmara qué campos del perfil se podían editar, cómo funcionaría el     
cambio de contraseña y dónde irían los endpoints. Cada ayudante debía tocar solo sus archivos y esperar a que terminara el anterior.                                             
- **Resultado:** aceptado. Ahora cualquier usuario puede editar su nombre, email y teléfono, y cambiar su contraseña indicando la actual. No hizo falta tocar la base de datos.  
Al final todo pasaba los tests (620) y el lint estaba limpio. Commits principales: 95fc335 (spec), 97222c7 (código), be56010 (tests), f601792 (docs) y f01523b (merge con `dev`).
- **Errores o alucinaciones:** el código salió bien a la primera. Lo que falló fue mi prompt, que no coincidía con el estado real del repo, y el agente me lo señaló al leerlo:  
daba por borrada una carpeta antigua que aún tenía restos, mencionaba una spec y una colección Bruno que todavía no estaban en `dev`, y no tenía en cuenta que la sección        
`/users` era solo para admins. Si se hubiera hecho tal cual, un cliente no habría podido editar su perfil; se resolvió con un router aparte. Además, el primer intento de commit 
falló por un error de sintaxis en el comando, sin llegar a guardar nada, y se repitió bien.                                                                                      
- **Trabajo descartado:** la colección Bruno, porque aún no se había subido al repositorio. Tampoco hizo falta migración.                                                        
- **Mi prompt o la spec:** di por hecho cómo estaba `dev` sin comprobarlo (aún no se habían aceptado algunas pull requests) y no pensé en dos casos: usuarios que entran solo con
Google o GitHub y no tienen contraseña, y alguien que "cambia" la contraseña por la misma. También olvidé que `AGENTS.md` pide escribir la spec antes del código; la redactó el  
agente, la revisé y la commiteé primero.                                                                                                                                         
- **Decisiones humanas:** las tomé yo y están en `specs/HU-25-cambio-password-perfil.md`:                                                                                        
  - si la contraseña actual es incorrecta se devuelve 403 y no 401, para que no parezca que la sesión ha caducado;                                                               
  - si alguien intenta cambiarse el rol o la activación desde su perfil, se rechaza con un error en vez de ignorarlo en silencio;
  - una cuenta sin contraseña no puede usar este cambio (lo cubrirá la HU de recuperación);
  - no se acepta como nueva la misma contraseña;
  - los endpoints van en `/users/me`;
  - equipo de cinco ayudantes, aunque el agente proponía tres;
  - revisores de la spec: Ana, Carla, Manon y Rita.
  - **Después del trabajo:** mientras trabajábamos se aceptó en `dev` la HU-24, que tocaba los mismos archivos. El agente unió los cambios de las dos historias sin perder nada y
  volvió a pasar todos los tests. También dejé documentado cómo trabajó cada ayudante en `docs/agents/HU-25/`.
  - **Lección:** comprobar el estado de `dev` antes de dar contexto al agente, y escribir la spec primero aunque la historia parezca pequeña.

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
