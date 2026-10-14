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