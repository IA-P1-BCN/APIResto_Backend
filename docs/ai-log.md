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

### HU-14 · Pantalla de facturas en el frontend

#### 2026-10-14 · Facturas y CSV para Excel (Frontend #38) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #32 · nada (UI sobre la API de la HU-14)
- **Prompt clave:** hacer la pantalla de facturas que faltaba en el frontend con los endpoints de Rita; después, "el CSV pierde datos cuando lo abro en Excel"
- **Resultado:** aceptado con cambios. Vista con pedidos por facturar, facturas emitidas con filtro de fechas y exportación CSV para el admin.
- **Errores o alucinaciones:** el CSV de la API (comas y punto decimal) salía en una sola columna en Excel en catalán. Causa raíz: el agente no tuvo en cuenta la configuración regional de Excel. Se comprobó abriéndolo con Excel y se convierte al descargar: `;`, coma decimal, fecha local y BOM. Al escribir el BOM desde la terminal se coló el carácter literal y el lint falló; se cambió por `\uFEFF`.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** no dije que el CSV era para abrirlo en Excel con configuración española.
- **Decisiones humanas:** no tocar el CSV de la API (es de Rita y sirve para contabilidad) y convertirlo solo en el frontend (Anna).
- **Lección:** probar las exportaciones con el programa con el que se van a abrir.

### HU-15 · Pantalla de estadísticas en el frontend

#### 2026-10-14 · Estadísticas de ventas (Frontend #39) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #33 · nada (UI sobre la API de la HU-15)
- **Prompt clave:** añadir las estadísticas en el frontend
- **Resultado:** aceptado. Total vendido, pedidos y ticket medio, ventas por día con su tabla, platos más vendidos y filtro de periodo.
- **Errores o alucinaciones:** el color principal no pasaba el validador de color para gráficos (poca saturación) y se eligió `#00879e` / `#2fa3b0`. En la primera captura, las barras de 10, 8 y 7 unidades medían lo mismo por un `max-width`; se corrigió al ver la captura, los tests no lo detectaban. Las ventas de ejemplo del modo simulado incluían los pimientos y rompían el test de borrar un plato; se limitaron los platos del historial.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** nada
- **Decisiones humanas:** nada
- **Lección:** mirar una captura del gráfico además de pasar los tests.

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

### HU-35 · Comandos y subagentes de OpenCode

#### 2026-10-15 · Comandos /tests, /seguridad y /migracion · @costanna

- **Herramienta y modelo:** Claude Code para escribir los comandos, el subagente y la documentación; OpenCode 1.18.34 con `opencode/big-pickle` para probarlos
- **Issue y reglas:** #78 · R-02 (contraseñas), R-13 (vinculación social) en la revisión de seguridad
- **Prompt clave:** `/seguridad c8f0ca1^..c8f0ca1` sobre el login social de la #116; `/tests` sobre `PATCH /orders/{order_id}/items/{item_id}` con unidades; `/migracion` sin argumentos para ver el número libre
- **Resultado:** aceptado con cambios. `/seguridad` dio 3 hallazgos medios y 6 bajos sin tocar ficheros; comprobé cuatro (sin longitud máxima en `code` y `redirect_uri`, `get_by_id` sin comprobar en la línea 59, `downgrade` de la 0005 con `password_hash = ''` y `UserUpdate.password` sin mínimo) y son ciertos. `/tests` generó 24 tests que pasan con ruff limpio. `/migracion` respondió 0007, que es correcto.
- **Errores o alucinaciones:** la primera versión de `/migracion` se inventó la variable `ALCHEMY_DATABASE_URL` (es `DATABASE_URL`), escribió mal el nombre de la 0006 y no se paró en el paso 3 sin argumentos; el prompt no decía qué variable usar ni prohibía describir los pasos siguientes. Una ejecución de `/tests` terminó vacía y la siguiente funcionó. `opencode run` se quedaba esperando cuando la entrada estándar no se cerraba.
- **Trabajo descartado:** los 24 tests de `/tests`, que eran solo una prueba del comando; mis cambios no los necesitan.
- **Mi prompt o la spec:** en `/migracion` faltaba decir que sin argumentos no se ejecuta ningún comando y que los nombres se copian de la lista; se añadió.
- **Decisiones humanas:** el subagente de seguridad solo puede leer y usar `git diff`, `git log` y `git show`; los hallazgos de la #116 se pasan a Manon en lugar de arreglarlos, porque es su código (Anna).
- **Lección:** en un comando, decir cuándo parar y qué variables y ficheros existen; y en scripts, lanzar `opencode run` con `< /dev/null`.

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

### HU-41 · Pantalla de barra en tiempo real

#### 2026-10-14 · Pantalla de barra (Frontend #37) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** #85 · nada
- **Prompt clave:** empezar la HU-41: pantalla de barra en tiempo real como la de cocina
- **Resultado:** aceptado con cambios. Cocina y Barra comparten pantalla y cada plato va a una según el campo `station` de su categoría.
- **Errores o alucinaciones:** la primera versión daba por hecho que `station` llegaría con la HU-40; llegó antes con la #99 y encajó. Faltaba que el admin pudiera elegir la estación: en producción todas las categorías quedarían en cocina y Barra vacía. Se añadió el selector en Gestionar categorías.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** no pensé en cómo se rellenaría `station` en una BD que ya existe.
- **Decisiones humanas:** el estado del pedido lo lleva cocina salvo en los pedidos solo de barra (Anna).
- **Lección:** comprobar cómo queda una función nueva con los datos que ya hay en producción.

### HU-46 · Estilo de la vista de pedidos del camarero

#### 2026-10-14 · Carta sin viñetas y aviso al repetir un plato (Frontend #34) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #26 · nada
- **Prompt clave:** quitar las viñetas al hacer un pedido y avisar al añadir otra vez el mismo producto
- **Resultado:** aceptado. Carta en rejilla y aviso dentro de la app al repetir un plato; los botones + y − no preguntan.
- **Errores o alucinaciones:** nada
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** la HU-47 (#27) pide quitar una de las dos formas de añadir platos; este cambio solo avisa.
- **Decisiones humanas:** aviso en lugar de quitar una forma de añadir (Anna).
- **Lección:** nada

### HU-48 · Paleta de restaurante con modo noche/día

#### 2026-10-14 · Colores, modo claro y oscuro, accesibilidad y botones táctiles (Frontend #36) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #28 · nada
- **Prompt clave:** colores de restaurante con modo oscuro, que pasen el filtro para personas con discapacidad visual y botones pensados para pantalla táctil
- **Resultado:** aceptado con cambios. Primero se hizo en crema y burdeos y el cliente pidió azules y verdes; se cambió.
- **Errores o alucinaciones:** simulando deuteranopia, los fondos de los estados verde y rojo casi no se distinguían; se añadió un símbolo a cada estado y bordes distintos en las mesas. Los textos se comprobaron con un script de contraste (AAA, 7:1) y de daltonismo.
- **Trabajo descartado:** la primera paleta en crema y burdeos.
- **Mi prompt o la spec:** no sabía los colores que quería el cliente hasta ver la primera versión.
- **Decisiones humanas:** azules y verdes en los dos modos (Anna, a petición del cliente).
- **Lección:** medir el contraste y simular el daltonismo con un script en vez de mirarlo a ojo.

### HU-49 · Pop-ups en lugar de menús desplegables para editar

#### 2026-10-14 · Formularios en ventana modal (Frontend #35) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #29 · nada
- **Prompt clave:** usar modales en el frontend
- **Resultado:** aceptado. Pedido, reservas, platos, categorías y mesas se editan en un modal con el foco dentro y Escape para cerrar.
- **Errores o alucinaciones:** un test pulsaba Nuevo plato antes de que se cargaran las categorías (el botón estaba desactivado). Al juntar ramas, colores y modales chocaban en `index.css` porque las dos añadían estilos al final; se movieron junto a sus reglas.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** "usa los modales" podía ser solo para los avisos; se aclaró que eran los formularios.
- **Decisiones humanas:** nada
- **Lección:** no añadir estilos al final de un CSS que tocan varias ramas a la vez.

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

### Tarea #117 · Unidades preparadas y servidas

#### 2026-10-14 · Contar unidades (Backend #118 y #119, Frontend #42) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** #117 · relacionado con la HU-45 (#89)
- **Prompt clave:** "si hay 2 paellas se marcan como entregadas las 2 de golpe, ¿estaría bien para un restaurante?"
- **Resultado:** aceptado con cambios. `prepared_quantity` y `served_quantity` con migración que convierte los datos, compatible con `prepared` y `served`, y contador − 1/2 + en la web.
- **Errores o alucinaciones:** la migración de unidades entró con el número 0005 a la vez que la de login social (#116): dos cabezas y el CI de `dev` en rojo. Causa raíz: no se comprobó qué números usaban las PRs abiertas. Se renumeró a 0006 en la #119. Antes, la #108 de Manon movió `update_item` a otro fichero y hubo conflicto; se mantuvieron sus líneas y solo se cambió el bucle, con permiso de Anna.
- **Trabajo descartado:** la rama con la 0003 de `station`, que ya había entrado con la #109.
- **Mi prompt o la spec:** nada
- **Decisiones humanas:** contar unidades aunque solapa con la HU-45 de Rita; resolver el conflicto con el código de Manon sin tocar sus líneas (Anna).
- **Lección:** antes de mergear una migración, mirar los números de las PRs abiertas (de aquí sale el comando `/migracion`).

### Tarea #40 · Nombre APIResto y nueva URL

#### 2026-10-14 · Nombre visible y URL de producción (Frontend #41, Backend #120) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #40 · nada
- **Prompt clave:** cambiar en la app la parte visible de RestoAPI a APIResto y la URL de Vercel
- **Resultado:** aceptado. Título, cabecera y login con APIResto y enlaces a `apiresto-f5.vercel.app`.
- **Errores o alucinaciones:** al cambiar la URL, `ALLOWED_ORIGINS` quedó mal escrito en Render y el backend rechazaba todos los orígenes, también los antiguos; se detectó probando el CORS desde la terminal y se dejó con las dos URLs separadas por comas. La guía de la HU-38 usaba `restoapi.vercel.app`, que no es nuestra: registrarla como callback habría dejado los códigos de login en manos de quien la registrara.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** nada
- **Decisiones humanas:** mantener la URL antigua activa y aceptar las dos en `ALLOWED_ORIGINS` (Anna).
- **Lección:** después de tocar variables en Render, probar el login desde las dos URLs.