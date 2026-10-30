"""Build the Feature 1 planning flowchart as SVG and a one-page A4 PDF.

The generator uses only the Python standard library so the artifact can be rebuilt
without adding a runtime dependency to the assistant project.
"""
from __future__ import annotations

from pathlib import Path
from html import escape
import math

PAGE_W = 595.2756
PAGE_H = 841.8898
ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "docs" / "feature1-planning-task-execution-flowchart.svg"
PDF_PATH = ROOT / "docs" / "feature1-planning-task-execution-flowchart.pdf"

COLORS = {
    "ink": "#172B4D",
    "muted": "#52647A",
    "blue": "#1D4ED8",
    "blue_fill": "#E8F0FF",
    "orange": "#A04000",
    "orange_fill": "#FFF1E8",
    "purple": "#7C3AED",
    "purple_fill": "#F3E8FF",
    "surface": "#FFFFFF",
    "line": "#9AA9BC",
    "soft": "#F5F7FA",
}

# Coordinates use a bottom-left origin, like PDF. Boxes are deliberately separated
# so the diagram remains readable when printed in grayscale.
BOXES = {
    "start": (170, 744, 255, 42, "start", ["START", "User goal, task, deadline, priority,", "availability, or project requirement"]),
    "extract": (170, 678, 255, 48, "process", ["1. Extract goals and facts", "Separate known information from missing details."]),
    "complete": (170, 606, 255, 54, "decision", ["Required information complete?", "Check duration, deadline, availability,", "and dependencies."]),
    "clarify": (22, 592, 125, 66, "exception", ["CLARIFY", "Ask a focused question.", "Do not invent missing information."]),
    "tasks": (170, 536, 255, 46, "process", ["2. Create or update tasks", "Break the goal into manageable work items."]),
    "priority": (170, 468, 255, 46, "process", ["3. Set priority and dependencies", "Use urgency, importance, deadlines, and prerequisites."]),
    "constraints": (170, 398, 255, 50, "process", ["4. Check constraints", "Compare duration, availability, deadlines,", "and dependencies."]),
    "feasible": (170, 326, 255, 54, "decision", ["Plan feasible?", "Can the requested work fit the known constraints?"]),
    "revise": (22, 300, 125, 80, "exception", ["REVISE", "Explain conflicts and list", "unscheduled tasks.", "User changes tasks or constraints."]),
    "schedule": (170, 256, 255, 46, "process", ["5. Build a proposed schedule", "Place tasks in available time; keep assumptions visible."]),
    "present": (170, 186, 255, 50, "output", ["6. Present the result", "Show schedule, warnings, assumptions, and pending work."]),
    "changed": (170, 112, 255, 54, "decision", ["User changes something?", "Deadline, priority, task status, or requirement changed?"]),
    "update": (448, 98, 125, 70, "exception", ["UPDATE", "Apply the change and", "recalculate the plan."]),
    "progress": (170, 34, 255, 52, "output", ["7. Track progress and next action", "Mark work state; revise the proposal when the situation changes."]),
}


def rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def box_style(kind: str) -> tuple[str, str, str]:
    if kind == "start":
        return COLORS["blue"], COLORS["blue"], "#FFFFFF"
    if kind == "decision":
        return COLORS["orange_fill"], COLORS["orange"], COLORS["ink"]
    if kind == "exception":
        return COLORS["purple_fill"], COLORS["purple"], COLORS["ink"]
    if kind == "output":
        return COLORS["soft"], COLORS["blue"], COLORS["ink"]
    return COLORS["blue_fill"], COLORS["blue"], COLORS["ink"]


def pdf_round_rect(commands: list[str], x: float, y: float, w: float, h: float, radius: float, fill: str, stroke: str) -> None:
    fr, fg, fb = rgb(fill)
    sr, sg, sb = rgb(stroke)
    k = 0.5522848
    commands.append(f"{fr:.4f} {fg:.4f} {fb:.4f} rg")
    commands.append(f"{sr:.4f} {sg:.4f} {sb:.4f} RG")
    commands.append("1.1 w")
    commands.append(f"{x + radius:.2f} {y:.2f} m")
    commands.append(f"{x + w - radius:.2f} {y:.2f} l")
    commands.append(f"{x + w - radius + k * radius:.2f} {y:.2f} {x + w:.2f} {y + radius - k * radius:.2f} {x + w:.2f} {y + radius:.2f} c")
    commands.append(f"{x + w:.2f} {y + h - radius:.2f} l")
    commands.append(f"{x + w:.2f} {y + h - radius + k * radius:.2f} {x + w - radius + k * radius:.2f} {y + h:.2f} {x + w - radius:.2f} {y + h:.2f} c")
    commands.append(f"{x + radius:.2f} {y + h:.2f} l")
    commands.append(f"{x + radius - k * radius:.2f} {y + h:.2f} {x:.2f} {y + h - radius + k * radius:.2f} {x:.2f} {y + h - radius:.2f} c")
    commands.append(f"{x:.2f} {y + radius:.2f} l")
    commands.append(f"{x:.2f} {y + radius - k * radius:.2f} {x + radius - k * radius:.2f} {y:.2f} {x + radius:.2f} {y:.2f} c")
    commands.append("B")


def pdf_text(commands: list[str], x: float, y: float, text: str, size: float, color: str, bold: bool = False) -> None:
    r, g, b = rgb(color)
    font = "/F2" if bold else "/F1"
    commands.append(f"{r:.4f} {g:.4f} {b:.4f} rg")
    commands.append(f"BT {font} {size:.2f} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ({pdf_escape(text)}) Tj ET")


def centered_x(x: float, w: float, text: str, size: float) -> float:
    # Helvetica averages close to 0.50 em for the short labels used here.
    return x + max(8.0, (w - len(text) * size * 0.50) / 2)


def draw_box_pdf(commands: list[str], box: tuple[float, float, float, float, str, list[str]]) -> None:
    x, y, w, h, kind, lines = box
    fill, stroke, text_color = box_style(kind)
    pdf_round_rect(commands, x, y, w, h, 8, fill, stroke)
    total = len(lines) * 9.2
    baseline = y + (h + total) / 2 - 7.0
    for index, line in enumerate(lines):
        size = 9.0 if index == 0 else 7.8
        bold = index == 0
        px = centered_x(x, w, line, size)
        pdf_text(commands, px, baseline - index * 10.0, line, size, text_color, bold)


def arrow_pdf(commands: list[str], points: list[tuple[float, float]], label: str | None = None, label_at: tuple[float, float] | None = None) -> None:
    r, g, b = rgb(COLORS["muted"])
    commands.append(f"{r:.4f} {g:.4f} {b:.4f} RG 1.2 w")
    x0, y0 = points[0]
    commands.append(f"{x0:.2f} {y0:.2f} m")
    for x, y in points[1:]:
        commands.append(f"{x:.2f} {y:.2f} l")
    commands.append("S")
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 6.0
    spread = 0.48
    left = (x2 - length * math.cos(angle - spread), y2 - length * math.sin(angle - spread))
    right = (x2 - length * math.cos(angle + spread), y2 - length * math.sin(angle + spread))
    commands.append(f"{x2:.2f} {y2:.2f} m {left[0]:.2f} {left[1]:.2f} l {right[0]:.2f} {right[1]:.2f} l h f")
    if label and label_at:
        pdf_text(commands, label_at[0], label_at[1], label, 7.4, COLORS["muted"], True)


def make_pdf() -> bytes:
    c: list[str] = []
    c.append("q")
    # Page background.
    sr, sg, sb = rgb(COLORS["surface"])
    c.append(f"{sr:.4f} {sg:.4f} {sb:.4f} rg 0 0 {PAGE_W:.2f} {PAGE_H:.2f} re f")
    pdf_text(c, 34, 804, "Feature 1: Planning and Task Execution", 18, COLORS["ink"], True)
    pdf_text(c, 34, 786, "Flowchart based on the team's decomposition, pattern recognition, and abstraction analysis", 8.4, COLORS["muted"])
    # Thin divider.
    lr, lg, lb = rgb(COLORS["line"])
    c.append(f"{lr:.4f} {lg:.4f} {lb:.4f} RG 0.8 w 34 774 m {PAGE_W - 34:.2f} 774 l S")
    pdf_text(c, 34, 758, "Input", 7.4, COLORS["blue"], True)
    pdf_text(c, 71, 758, "Process", 7.4, COLORS["ink"], True)
    pdf_text(c, 119, 758, "Decision", 7.4, COLORS["orange"], True)
    pdf_text(c, 176, 758, "Exception / revision", 7.4, COLORS["purple"], True)

    # Main vertical path.
    main_pairs = [
        ("start", "extract"),
        ("extract", "complete"),
        ("complete", "tasks"),
        ("tasks", "priority"),
        ("priority", "constraints"),
        ("constraints", "feasible"),
        ("feasible", "schedule"),
        ("schedule", "present"),
        ("present", "changed"),
        ("changed", "progress"),
    ]
    for first, second in main_pairs:
        x, y, w, h, *_ = BOXES[first]
        x2, y2, w2, h2, *_ = BOXES[second]
        arrow_pdf(c, [(x + w / 2, y), (x2 + w2 / 2, y2 + h2)])

    # Side branches and revision loops.
    x, y, w, h, *_ = BOXES["complete"]
    sx, sy, sw, sh, *_ = BOXES["clarify"]
    arrow_pdf(c, [(x, y + h / 2), (sx + sw, sy + sh / 2)], "NO", (147, 628))
    arrow_pdf(c, [(sx, sy + sh / 2), (154, sy + sh / 2), (154, 702), (170, 702)], "back", (95, 668))
    x, y, w, h, *_ = BOXES["feasible"]
    rx, ry, rw, rh, *_ = BOXES["revise"]
    arrow_pdf(c, [(x, y + h / 2), (rx + rw, ry + rh / 2)], "NO", (146, 350))
    arrow_pdf(c, [(rx, ry + rh / 2), (154, ry + rh / 2), (154, 423), (170, 423)], "back", (94, 390))
    x, y, w, h, *_ = BOXES["changed"]
    ux, uy, uw, uh, *_ = BOXES["update"]
    arrow_pdf(c, [(x + w, y + h / 2), (ux, uy + uh / 2)], "YES", (426, 139))
    arrow_pdf(c, [(ux, uy + uh / 2), (575, uy + uh / 2), (575, 491), (425, 491)], "recalculate", (481, 478))
    # Decision labels on main path.
    pdf_text(c, 428, 346, "YES", 7.4, COLORS["muted"], True)
    pdf_text(c, 428, 130, "NO", 7.4, COLORS["muted"], True)

    for box in BOXES.values():
        draw_box_pdf(c, box)

    pdf_text(c, 34, 12, "A proposed schedule is reviewed and revised when the user's situation changes.", 7.4, COLORS["muted"])
    pdf_text(c, 450, 12, "Team 02", 7.4, COLORS["muted"], True)
    c.append("Q")
    stream = "\n".join(c).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>".encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(output)


def svg_color(color: str) -> str:
    return color


def make_svg() -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 595.28 841.89">',
        f'<rect width="595.28" height="841.89" fill="{COLORS["surface"]}"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#172B4D} .small{font-size:7.8px}.muted{fill:#52647A}.bold{font-weight:700}</style>',
        '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 Z" fill="#52647A"/></marker></defs>',
        '<text x="34" y="38" font-size="18" class="bold">Feature 1: Planning and Task Execution</text>',
        '<text x="34" y="56" font-size="8.4" class="muted">Flowchart based on the team\'s decomposition, pattern recognition, and abstraction analysis</text>',
        f'<line x1="34" y1="68" x2="561" y2="68" stroke="{COLORS["line"]}" stroke-width="0.8"/>',
        f'<text x="34" y="84" font-size="7.4" fill="{COLORS["blue"]}" class="bold">Input</text>',
        '<text x="71" y="84" font-size="7.4" class="bold">Process</text>',
        f'<text x="119" y="84" font-size="7.4" fill="{COLORS["orange"]}" class="bold">Decision</text>',
        f'<text x="176" y="84" font-size="7.4" fill="{COLORS["purple"]}" class="bold">Exception / revision</text>',
    ]
    # Convert PDF bottom-origin coordinates to SVG top-origin coordinates.
    def sy(y: float) -> float:
        return PAGE_H - y

    def box_svg(name: str) -> None:
        x, y, w, h, kind, lines = BOXES[name]
        fill, stroke, _ = box_style(kind)
        top = PAGE_H - y - h
        parts.append(f'<rect x="{x}" y="{top}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>')
        total = len(lines) * 9.2
        baseline = y + (h + total) / 2 - 7.0
        for index, line in enumerate(lines):
            size = 9.0 if index == 0 else 7.8
            cls = "bold" if index == 0 else ""
            text_y = sy(baseline - index * 10.0)
            parts.append(f'<text x="{x + w / 2}" y="{text_y:.2f}" font-size="{size}" text-anchor="middle" class="{cls}">{escape(line)}</text>')

    def line_svg(points: list[tuple[float, float]], label: str | None = None, label_at: tuple[float, float] | None = None) -> None:
        coords = " ".join(f"{x:.2f},{sy(y):.2f}" for x, y in points)
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{COLORS["muted"]}" stroke-width="1.2" marker-end="url(#arrow)"/>')
        if label and label_at:
            parts.append(f'<text x="{label_at[0]}" y="{sy(label_at[1]):.2f}" font-size="7.4" class="bold muted">{escape(label)}</text>')

    for first, second in [
        ("start", "extract"), ("extract", "complete"), ("complete", "tasks"), ("tasks", "priority"),
        ("priority", "constraints"), ("constraints", "feasible"), ("feasible", "schedule"),
        ("schedule", "present"), ("present", "changed"), ("changed", "progress"),
    ]:
        x, y, w, h, *_ = BOXES[first]
        x2, y2, w2, h2, *_ = BOXES[second]
        line_svg([(x + w / 2, y), (x2 + w2 / 2, y2 + h2)])
    x, y, w, h, *_ = BOXES["complete"]
    sx, sy0, sw, sh, *_ = BOXES["clarify"]
    line_svg([(x, y + h / 2), (sx + sw, sy0 + sh / 2)], "NO", (147, 628))
    line_svg([(sx, sy0 + sh / 2), (154, sy0 + sh / 2), (154, 702), (170, 702)], "back", (95, 668))
    x, y, w, h, *_ = BOXES["feasible"]
    rx, ry, rw, rh, *_ = BOXES["revise"]
    line_svg([(x, y + h / 2), (rx + rw, ry + rh / 2)], "NO", (146, 350))
    line_svg([(rx, ry + rh / 2), (154, ry + rh / 2), (154, 423), (170, 423)], "back", (94, 390))
    x, y, w, h, *_ = BOXES["changed"]
    ux, uy, uw, uh, *_ = BOXES["update"]
    line_svg([(x + w, y + h / 2), (ux, uy + uh / 2)], "YES", (426, 139))
    line_svg([(ux, uy + uh / 2), (575, uy + uh / 2), (575, 491), (425, 491)], "recalculate", (481, 478))
    parts.extend([
        '<text x="428" y="496" font-size="7.4" class="bold muted">YES</text>',
        '<text x="428" y="712" font-size="7.4" class="bold muted">NO</text>',
    ])
    for name in BOXES:
        box_svg(name)
    parts.extend([
        '<text x="34" y="832" font-size="7.4" class="muted">A proposed schedule is reviewed and revised when the user\'s situation changes.</text>',
        '<text x="450" y="832" font-size="7.4" class="bold muted">Team 02</text>',
        '</svg>',
    ])
    return "\n".join(parts)


def main() -> None:
    SVG_PATH.write_text(make_svg(), encoding="utf-8")
    PDF_PATH.write_bytes(make_pdf())
    print(f"Wrote {SVG_PATH}")
    print(f"Wrote {PDF_PATH}")
    print(f"PDF page size: {PAGE_W:.2f} x {PAGE_H:.2f} points (A4)")
    print("PDF pages: 1")


if __name__ == "__main__":
    main()
