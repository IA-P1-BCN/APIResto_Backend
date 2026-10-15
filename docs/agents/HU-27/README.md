# Diagramas de la arquitectura agéntica · HU-27

Documentación visual de cómo se organizó el equipo de agentes (Claude Code) que revisó la colección
Bruno de HU-27 (issue #70). Spec de la HU: [`specs/HU-27-agents-ontologia.md`](../../../specs/HU-27-agents-ontologia.md).
Directrices de los agentes: [`specs/agents/HU-27/`](../../../specs/agents/HU-27/).

## Qué muestra cada PNG

| Archivo | Contenido |
|---|---|
| [`esquema-visual-detallado.png`](esquema-visual-detallado.png) | Jerarquía completa de archivos agénticos, del NIVEL 0 (`AGENTS.md`, briefing, plan v3, ontología) al NIVEL 4 (`bruno/`). Muestra cómo cada nivel alimenta al siguiente y cómo el líder (`lead.md`) reparte las carpetas entre los 5 especialistas. |
| [`mapa-dependencias-agentes.png`](mapa-dependencias-agentes.png) | Dependencias entre agentes: `agent-auth` y `agent-menus` arrancan en paralelo; `agent-orders` y `agent-reservations` esperan a `agent-menus` (consumen `tableId`, `dishId`…); `agent-cleanup` espera a `agent-menus` y `agent-orders`. |
| [`esquema-archivos-por-nivel.png`](esquema-archivos-por-nivel.png) | Árbol del repo con los archivos agénticos etiquetados por nivel (0 directrices · 1 specs generales · 2 spec de HU-27 · 3 directrices de agentes · 4 entregable). Es el esquema **previsto**: incluye `docs/ai-log.md` aunque todavía no exista. |

## Datos de la colección

- **130 requests** en 12 carpetas (`00-health` … `11-cleanup`).
- `app/routers/*.py` expone **43 endpoints HTTP** (más `GET /` y `GET /health` en `app/main.py`, y el
  WebSocket `/ws/kitchen`, que se prueba a mano: ver `bruno/README.md`).

## Cómo regenerarlos

Desde la raíz del repo, con el `.venv` activo:

```bash
pip install matplotlib
python scripts/generate_agent_diagrams.py
```

El script crea esta carpeta si no existe y sobrescribe los tres PNG.

> **Nota:** `scripts/generate_agent_diagrams.py` no forma parte del runtime de la API. `matplotlib` no
> está en `requirements.txt` a propósito: solo se instala para regenerar estos diagramas.
