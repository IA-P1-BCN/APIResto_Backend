# HU-36 · Revisión automática de PRs

> Issue: #79 · Prioridad Could · Escribe: Anna · Revisa: pareja de revisión del sprint ·
> Aprueba: Levi (PO). Relacionadas: HU-21 (OpenCode con modelos gratuitos) y HU-35
> (comandos y subagentes). Usa `specs/HU-TEMPLATE.md`.

## Problem Statement
Cada PR depende de que quien revisa tenga tiempo de leer todo el diff. Errores repetidos
(capas mezcladas, falta de tests de 4xx, secretos o contraseñas en logs, migraciones sin
hacer) se escapan o se detectan tarde. La issue pide una revisión automática con un agente
en GitHub Actions y un modelo gratuito.

## Solution
Un workflow de GitHub Actions que, en cada PR a `dev` o `main`, ejecuta OpenCode con el
modelo gratuito `opencode/deepseek-v4.1-flash-free` y un agente revisor de solo lectura. El agente
revisa lo que la PR añade sobre su rama base contra `AGENTS.md`, la ontología y la spec de
la HU, y el workflow publica el resultado como **un único comentario** en la PR, que se
actualiza en cada push. Solo informa: nunca bloquea la PR ni pone la CI en rojo. La
revisión humana sigue siendo obligatoria.

## User Stories
1. Como autora de una PR, quiero un primer repaso automático en minutos, para corregir
   lo evidente antes de que la revise otra persona.
2. Como revisora, quiero un resumen de los riesgos con fichero y línea, para centrar mi
   revisión en lo importante.
3. Como equipo, queremos que la revisión no cueste dinero ni necesite claves, y que no
   pueda modificar el repo.

## Implementation Decisions
- **Disparador**: `pull_request` (`opened`, `synchronize`, `reopened`, `ready_for_review`)
  hacia `dev` y `main`. Se salta los borradores y las PRs que vienen de forks (su token es
  de solo lectura y no podría comentar). `concurrency` por PR cancela la revisión anterior
  si llega otro push.
- **Agente**: OpenCode `1.18.34` instalado con `npm` (versión fija) y modelo
  `opencode/deepseek-v4.1-flash-free`. No necesita clave ni secretos.
- **Agente `revisor`** (`.opencode/agents/revisor.md`): de solo lectura, igual que
  `seguridad` (HU-35): `edit`, `webfetch` y `task` denegados; en bash solo `git diff`, `git log` y
  `git show`. Revisa capas, tests, errores `{"detail", "code"}`, migraciones, seguridad y
  documentación del contrato, y responde con una tabla de hallazgos con fichero y línea.
- **Comando `/revision`** (`.opencode/commands/revision.md`): recibe el rango
  (`origin/<base>...HEAD`) y se puede usar también en local antes de abrir una PR.
- **Comentario**: lo publica el workflow con `gh` y el `GITHUB_TOKEN`
  (`pull-requests: write`). Lleva una marca oculta para encontrarlo y editarlo en el
  siguiente push en lugar de añadir otro. Indica el commit revisado y que es una revisión
  automática que no sustituye a la humana.
- **Seguridad**: se usa `pull_request` (no `pull_request_target`), así que el código de la
  PR nunca corre con permisos elevados. La configuración del agente (`.opencode/` y
  `opencode.json`) se toma de la rama base cuando ya existe allí, para que una PR no pueda
  ampliar sus permisos. El paso del agente no recibe el `GITHUB_TOKEN` y el
  checkout no guarda credenciales (`persist-credentials: false`). Aunque el diff intentara
  dar órdenes al agente, solo puede leer. Si no se puede restaurar la configuración de la
  rama base, no se revisa. Límite asumido: con `pull_request`, GitHub ejecuta el workflow de
  la propia PR, así que una PR del mismo repo podría cambiar este YAML; solo las abre el
  equipo (las de forks se saltan) y el token solo permite comentar en PRs.
- **Fallos**: si el modelo no responde o tarda más de 10 minutos, el comentario lo dice y
  el workflow termina en verde. `timeout-minutes: 15` para el trabajo.
- **Coste**: el repo es público, así que los minutos de Actions son gratis; el modelo
  también. No despliega nada ni mantiene nada despierto.

## Testing Decisions
- El comando `/revision` se prueba en local con `opencode run` sobre una rama con cambios
  reales (formato de la tabla, que no modifique ficheros y que respete el rango).
- El workflow se valida con un parseo del YAML y se prueba de verdad en la PR de esta HU:
  primer comentario al abrirla y el mismo comentario actualizado tras otro push.
- Sin tests de pytest: no cambia código de la app.

## Criterios de aceptación
- [ ] Al abrir una PR a `dev`, aparece un comentario con la revisión del agente.
- [ ] En cada push a la PR se actualiza ese mismo comentario (no se acumulan).
- [ ] La revisión nunca pone la PR en rojo, ni siquiera si el modelo falla.
- [ ] El agente no puede modificar ficheros ni ejecutar más que `git diff/log/show`.
- [ ] Sin claves ni secretos nuevos; modelo gratuito.
- [ ] README explica cómo funciona y cómo lanzar `/revision` en local.

## Out of Scope
- Comentarios en línea sobre cada fichero (un solo comentario de resumen).
- Bloquear el merge según la revisión.
- Revisión automática en el repo del frontend (se puede copiar después).
- Responder a comentarios o aplicar los cambios que propone.

## Preguntas abiertas
Ninguna.

## Decisiones de la sesión
Sesión del 16/10/2026 (Anna):
- **OpenCode + big-pickle con un subagente propio** → mismo agente y modelo que el equipo
  (HU-21, HU-35) y sin claves. Rechazado: GitHub Models (no es OpenCode, límites diarios y
  puede requerir que un admin de la organización lo active); acción oficial
  `anomalyco/opencode/github` (acción de terceros con permisos de escritura que decide
  cómo comenta).
- **Al abrir y en cada push, un único comentario que se actualiza** → feedback en cada
  cambio sin llenar la PR de comentarios. Rechazado: solo al abrir; solo bajo demanda.
- **Solo informa, no bloquea** → el modelo gratuito puede equivocarse o no responder.
- **Se nombra OpenCode y el modelo** en el workflow, el README, la spec y el comentario:
  es el objeto de la HU (como en la HU-21). Commits y PRs sin atribución.
- **Cambio de modelo tras la primera prueba en GitHub (16/10/2026)**: con `big-pickle` el
  agente se quedaba más de 10 minutos escribiendo la respuesta y la revisión no llegaba. Se
  probaron cuatro modelos gratuitos con el mismo diff: `deepseek-v4.1-flash-free` revisó en
  2 min 29 s, `space-bunny-free` en 3 min 8 s (con frases en inglés al principio) y
  `mimo-v2.6-flash-free` no terminó en 7 minutos. Se elige `deepseek-v4.1-flash-free`, que
  además no guarda ni usa los datos para entrenar.
- **Correcciones tras la primera revisión automática**: configuración del agente desde la
  rama base, `task` denegado, el paso del comentario nunca pone la CI en rojo y su script también sale de la rama base, sin tuberías
  que puedan cortarse con `pipefail` y el final del log del agente en el log del paso si
  falla.
