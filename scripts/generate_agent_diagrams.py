"""Genera los diagramas PNG de la arquitectura agéntica de HU-27.

Uso: python scripts/generate_agent_diagrams.py

No forma parte del runtime de la API. Requiere matplotlib, que no está en
requirements.txt: se instala aparte solo para regenerar los diagramas.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "agents" / "HU-27"
BRANCH = "feature/HU-27-coleccion-bruno-postman"
DPI = 150

plt.switch_backend("Agg")
plt.rcParams["font.family"] = "DejaVu Sans"

WHITE = "#ffffff"
GREY = "#eeeeee"
GREEN = "#d9f2d9"
BLUE = "#d6e6fa"
YELLOW = "#fff4c2"
ORANGE = "#ffdcb8"
PINK = "#fbdde8"


def new_canvas(figsize, width, height):
    """Crea una figura blanca sin ejes con un sistema de coordenadas fijo."""
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")
    return fig, ax


def box(ax, cx, cy, w, h, title, body="", color=WHITE, title_size=11):
    """Dibuja una caja centrada en (cx, cy) con título en negrita y cuerpo."""
    ax.add_patch(
        FancyBboxPatch(
            (cx - w / 2, cy - h / 2),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.15",
            linewidth=0.8,
            edgecolor="black",
            facecolor=color,
        )
    )
    if body:
        ax.text(cx, cy + h * 0.18, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold")
        ax.text(cx, cy - h * 0.16, body, ha="center", va="center",
                fontsize=10, linespacing=1.4)
    else:
        ax.text(cx, cy, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold")
    return {"cx": cx, "cy": cy, "w": w, "h": h}


def arrow(ax, src, dst, label="", src_side="bottom", dst_side="top"):
    """Une dos cajas con una flecha fina y una etiqueta opcional."""
    def anchor(b, side):
        offsets = {
            "top": (0, b["h"] / 2),
            "bottom": (0, -b["h"] / 2),
            "left": (-b["w"] / 2, 0),
            "right": (b["w"] / 2, 0),
        }
        dx, dy = offsets[side]
        return b["cx"] + dx, b["cy"] + dy

    start = anchor(src, src_side)
    end = anchor(dst, dst_side)
    ax.add_patch(
        FancyArrowPatch(
            start, end, arrowstyle="-|>", mutation_scale=14,
            linewidth=0.9, color="black", shrinkA=2, shrinkB=2,
        )
    )
    if label:
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        ax.text(mx, my, label, ha="center", va="center", fontsize=9,
                style="italic",
                bbox={"facecolor": WHITE, "edgecolor": "none", "pad": 1.5})


def save(fig, name):
    """Guarda la figura en OUTPUT_DIR y devuelve la ruta."""
    path = OUTPUT_DIR / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    return path


def diagram_1():
    """Esquema visual detallado: jerarquía de NIVEL 0 a NIVEL 4."""
    fig, ax = new_canvas((16, 20), 16, 20)
    ax.set_xlim(-1.8, 16)
    ax.set_ylim(1.8, 20)
    ax.text(8, 19.5, "Esquema visual detallado · HU-27", ha="center",
            fontsize=16, fontweight="bold")

    def level(y, text):
        ax.text(-1.7, y, text, ha="left", va="center", fontsize=10,
                color="#555555", fontweight="bold")

    level(18.3, "NIVEL 0")
    agents = box(ax, 8, 18.3, 5, 1.0, "AGENTS.md",
                 "reglas · stack · convenciones · DoD", GREY)

    level(16.3, "NIVEL 0-1")
    ontology = box(ax, 3.2, 16.3, 4.2, 1.1, "specs/ontology.md",
                   "vocabulario · roles · R-01…R-14", GREEN)
    briefing = box(ax, 8, 16.3, 4.2, 1.1, "docs/Briefing del Proyecto.md",
                   "encargo · requisitos · niveles", GREY)
    plan = box(ax, 12.8, 16.3, 4.2, 1.1, "docs/Plan v3.pdf",
               "Sprint 2 (P3) · HU-27 → Levi", GREY)
    for child in (ontology, briefing, plan):
        arrow(ax, agents, child)

    level(14.0, "NIVEL 2")
    spec = box(ax, 8, 14.0, 7, 1.3, "specs/HU-27-coleccion-bruno.md",
               "Issue #70 · 141 requests esperados · Swagger fuera de alcance",
               BLUE)
    for parent in (ontology, briefing, plan):
        arrow(ax, parent, spec)

    level(11.8, "NIVEL 3")
    lead = box(ax, 8, 11.8, 5, 1.2, "docs/agents/HU-27/lead.md",
               "orquesta · no escribe .bru", YELLOW)
    arrow(ax, spec, lead)

    specialists = [
        ("agent-auth", "00-health · 01-02"),
        ("agent-menus", "03-05"),
        ("agent-orders", "07-08"),
        ("agent-reservations", "06"),
        ("agent-cleanup", "09-11"),
    ]
    level(9.3, "NIVEL 3")
    agent_boxes = []
    for i, (name, folders) in enumerate(specialists):
        b = box(ax, 1.9 + i * 3.05, 9.3, 2.8, 1.2, name, folders, YELLOW,
                title_size=10)
        arrow(ax, lead, b)
        agent_boxes.append(b)

    level(5.6, "NIVEL 4")
    bruno = box(ax, 8, 5.6, 14.5, 4.2, "", "", PINK)
    ax.text(8, 7.25, "bruno/", ha="center", fontsize=13, fontweight="bold")
    ax.text(8, 6.65, "141 requests · 12 carpetas de dominio", ha="center",
            fontsize=10)
    folders = [
        "bruno.json", "README.md", "environments/", "00-health/",
        "01-auth/", "02-users/", "03-categories/", "04-dishes/",
        "05-tables/", "06-reservations/", "07-orders/", "08-invoices/",
        "09-stats/", "10-exports/", "11-cleanup/",
    ]
    for i, folder in enumerate(folders):
        col, row = i % 5, i // 5
        ax.text(2.6 + col * 2.7, 5.9 - row * 0.75, folder, ha="center",
                va="center", fontsize=10, family="DejaVu Sans Mono")
    for b in agent_boxes:
        arrow(ax, b, bruno)

    ax.text(8, 2.9, "bruno.json · README.md · environments/ → consolidados "
            "por el líder", ha="center", fontsize=10, style="italic")
    ax.text(8, 2.2, f"Rama: {BRANCH}", ha="center", fontsize=10)
    return save(fig, "esquema-visual-detallado.png")


def diagram_2():
    """Mapa de dependencias entre los agentes especialistas."""
    fig, ax = new_canvas((14, 10), 14, 10)
    ax.text(7, 9.6, "Mapa de dependencias entre agentes · HU-27",
            ha="center", fontsize=16, fontweight="bold")

    lead = box(ax, 7, 8.3, 4, 1.0, "lead.md", "orquesta · verifica", WHITE)
    auth = box(ax, 2.2, 5.9, 3.4, 1.1, "agent-auth", "independiente", GREEN)
    menus = box(ax, 7, 5.9, 3.4, 1.1, "agent-menus", "base de datos", BLUE)
    reservations = box(ax, 11.8, 5.9, 3.4, 1.1, "agent-reservations",
                       "depende de menus", YELLOW)
    orders = box(ax, 7, 3.6, 3.4, 1.1, "agent-orders", "depende de menus",
                 YELLOW)
    cleanup = box(ax, 7, 1.3, 3.8, 1.1, "agent-cleanup",
                  "depende de menus + orders", ORANGE)

    for target in (auth, menus, reservations):
        arrow(ax, lead, target, "paralelo")
    arrow(ax, menus, orders)
    arrow(ax, orders, cleanup)
    arrow(ax, menus, reservations, src_side="right", dst_side="left")
    return save(fig, "mapa-dependencias-agentes.png")


TREE = [
    ("Resto-API_Backend/", None),
    ("│", None),
    ("├── AGENTS.md", 0),
    ("├── CLAUDE.md", 0),
    ("│", None),
    ("├── docs/", None),
    ("│   ├── Briefing del Proyecto.md", 0),
    ("│   ├── RestoAPI Plan de Proyecto v3.pdf", 0),
    ("│   ├── ai-log.md", "bitácora"),
    ("│   └── agents/", None),
    ("│       └── HU-27/", None),
    ("│           ├── lead.md", 3),
    ("│           ├── agent-auth.md", 3),
    ("│           ├── agent-menus.md", 3),
    ("│           ├── agent-orders.md", 3),
    ("│           ├── agent-reservations.md", 3),
    ("│           ├── agent-cleanup.md", 3),
    ("│           ├── esquema-visual-detallado.png", "salida"),
    ("│           ├── mapa-dependencias-agentes.png", "salida"),
    ("│           └── esquema-archivos-por-nivel.png", "salida"),
    ("│", None),
    ("├── specs/", None),
    ("│   ├── ontology.md", 1),
    ("│   ├── HU-20-agents-ontologia.md", 1),
    ("│   └── HU-27-coleccion-bruno.md", 2),
    ("│", None),
    ("├── bruno/", 4),
    ("│", None),
    ("└── app/", "código"),
]

LEVEL_COLORS = {0: GREY, 1: GREEN, 2: BLUE, 3: YELLOW, 4: PINK}


def diagram_3():
    """Árbol del repo con los archivos agénticos etiquetados por nivel."""
    fig, ax = new_canvas((16, 18), 16, 18)
    ax.text(8, 17.5, "Esquema de archivos por nivel · HU-27", ha="center",
            fontsize=16, fontweight="bold")

    top, step = 16.6, 0.49
    for i, (text, tag) in enumerate(TREE):
        y = top - i * step
        if isinstance(tag, int):
            ax.add_patch(
                FancyBboxPatch(
                    (1.0, y - step * 0.42), 13.6, step * 0.84,
                    boxstyle="round,pad=0,rounding_size=0.08",
                    linewidth=0.5, edgecolor="#999999",
                    facecolor=LEVEL_COLORS[tag],
                )
            )
            label = f"[NIVEL {tag}]"
        elif tag == "código":
            label = "(código, NO se toca)"
        elif tag:
            label = f"[{tag}]"
        else:
            label = ""
        ax.text(1.2, y, text, ha="left", va="center", fontsize=11,
                family="DejaVu Sans Mono")
        if label:
            ax.text(14.4, y, label, ha="right", va="center", fontsize=10,
                    fontweight="bold" if isinstance(tag, int) else "normal")

    legend_y = top - len(TREE) * step - 0.4
    names = ["Directrices", "Specs", "Spec HU-27", "Agentes", "Entregable"]
    for level, name in enumerate(names):
        x = 1.0 + level * 2.75
        ax.add_patch(
            FancyBboxPatch((x, legend_y - 0.18), 0.4, 0.36,
                           boxstyle="square,pad=0", linewidth=0.5,
                           edgecolor="#999999",
                           facecolor=LEVEL_COLORS[level])
        )
        ax.text(x + 0.55, legend_y, f"Nivel {level} · {name}", va="center",
                fontsize=10)
    return save(fig, "esquema-archivos-por-nivel.png")


def main():
    """Genera los tres diagramas y muestra sus rutas."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [diagram_1(), diagram_2(), diagram_3()]
    print("Generados: " + ", ".join(str(p) for p in paths))


if __name__ == "__main__":
    main()
