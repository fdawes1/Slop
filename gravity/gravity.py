#!/usr/bin/env python3
"""
gravity -- N-body orbital simulator.
"What goes up must come down. What goes sideways is probably in orbit. What goes diagonally is somebody else's problem."
"""
from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static
from textual import on

CANVAS_W = 70
CANVAS_H = 24
G = 500.0
DT = 0.016
MAX_SPEED = 50.0
SOFTENING = 5.0
TRAIL_LEN = 25

# Aspect ratio: terminal chars are ~2x as tall as wide
# Correct by multiplying dy by 2 in force calc, multiplying vy update by 0.5
ASPECT = 2.0


@dataclass
class Body:
    x: float
    y: float
    vx: float
    vy: float
    mass: float
    char: str
    color: str
    trail: list[tuple[float, float]] = field(default_factory=list)


def _wrap(v: float, size: float) -> float:
    return v % size


def tick_bodies(bodies: list[Body]) -> None:
    n = len(bodies)
    # Compute pairwise gravitational forces
    ax = [0.0] * n
    ay = [0.0] * n
    for i in range(n):
        for j in range(i + 1, n):
            dx = bodies[j].x - bodies[i].x
            dy = bodies[j].y - bodies[i].y
            # Aspect-correct dy for force calculation
            dy_corr = dy * ASPECT
            dist2 = dx * dx + dy_corr * dy_corr + SOFTENING * SOFTENING
            dist = math.sqrt(dist2)
            # Force magnitude / dist (for unit vector scaling)
            f = G / dist2
            fx = f * dx / dist
            fy = f * dy_corr / dist
            ax[i] += bodies[j].mass * fx
            ay[i] += bodies[j].mass * fy
            ax[j] -= bodies[i].mass * fx
            ay[j] -= bodies[i].mass * fy

    for i, b in enumerate(bodies):
        # Record trail before moving
        b.trail.append((b.x, b.y))
        if len(b.trail) > TRAIL_LEN:
            b.trail.pop(0)

        # Integrate velocity
        b.vx += ax[i] * DT
        # Aspect-correct vy: multiply by 0.5 so vertical motion is half a char-height per tick
        b.vy += ay[i] * DT * 0.5

        # Clamp speed
        spd = math.sqrt(b.vx * b.vx + b.vy * b.vy)
        if spd > MAX_SPEED:
            scale = MAX_SPEED / spd
            b.vx *= scale
            b.vy *= scale

        # Integrate position
        b.x += b.vx * DT
        b.y += b.vy * DT

        # Toroidal wrap
        b.x = _wrap(b.x, CANVAS_W)
        b.y = _wrap(b.y, CANVAS_H)


def render_bodies(bodies: list[Body]) -> Text:
    # Build a grid: each cell holds (char, style) or None
    grid: list[list[tuple[str, str] | None]] = [[None] * CANVAS_W for _ in range(CANVAS_H)]

    # Draw trails first (older = dimmer)
    for b in bodies:
        trail_len = len(b.trail)
        for idx, (tx, ty) in enumerate(b.trail):
            cx = int(tx) % CANVAS_W
            cy = int(ty) % CANVAS_H
            # Skip if a body char is already there (will be placed later)
            if grid[cy][cx] is not None and grid[cy][cx][0] != "·":
                continue
            # Recent positions are brighter
            frac = idx / max(trail_len - 1, 1)
            style = "grey70" if frac > 0.5 else "grey46"
            grid[cy][cx] = ("·", style)

    # Draw bodies on top
    for b in bodies:
        cx = int(b.x) % CANVAS_W
        cy = int(b.y) % CANVAS_H
        grid[cy][cx] = (b.char, b.color)

    text = Text(no_wrap=True)
    for row in grid:
        for cell in row:
            if cell is None:
                text.append(" ")
            else:
                text.append(cell[0], style=cell[1])
        text.append("\n")
    return text


def kinetic_energy(bodies: list[Body]) -> float:
    return sum(0.5 * b.mass * (b.vx ** 2 + b.vy ** 2) for b in bodies)


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

def preset_chaos() -> list[Body]:
    """12 random bodies in roughly circular orbits around the centre."""
    cx, cy = CANVAS_W / 2, CANVAS_H / 2
    colors = [
        "bright_red", "bright_yellow", "bright_cyan", "bright_magenta",
        "bright_green", "bright_white", "red", "yellow", "cyan",
        "magenta", "green", "white",
    ]
    chars = ["●", "◆", "★", "▲", "■", "◉", "○", "◇", "☆", "△", "□", "◎"]
    bodies: list[Body] = []
    for k in range(12):
        angle = random.uniform(0, 2 * math.pi)
        radius = random.uniform(5, 14)
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        mass = random.uniform(3, 12)
        # Circular orbit velocity: v = sqrt(G * M_total / r) — rough estimate
        # with aspect correction the effective radius differs; use canvas radius
        v_circ = math.sqrt(G * 8 / max(radius, 1))
        # Perpendicular to radius vector
        vx = -v_circ * math.sin(angle) * random.uniform(0.7, 1.3)
        vy = v_circ * math.cos(angle) * random.uniform(0.7, 1.3)
        bodies.append(Body(x, y, vx, vy, mass, chars[k], colors[k]))
    return bodies


def preset_binary() -> list[Body]:
    """2 equal-mass stars orbiting each other + 2 small test particles."""
    cx, cy = CANVAS_W / 2, CANVAS_H / 2
    sep = 10.0
    star_mass = 50.0
    # Circular orbit: v = sqrt(G * M / (2*sep))
    v = math.sqrt(G * star_mass / (2 * sep))
    bodies = [
        Body(cx - sep / 2, cy, 0.0, v, star_mass, "★", "bright_yellow"),
        Body(cx + sep / 2, cy, 0.0, -v, star_mass, "★", "bright_cyan"),
        # Test particles in wider orbit
        Body(cx, cy - 18, v * 0.7, 0.0, 0.1, "·", "bright_green"),
        Body(cx, cy + 18, -v * 0.7, 0.0, 0.1, "·", "bright_magenta"),
    ]
    return bodies


def preset_solar() -> list[Body]:
    """1 large central star + 5 planets at increasing radii."""
    cx, cy = CANVAS_W / 2, CANVAS_H / 2
    star_mass = 500.0
    planet_data = [
        # (radius, mass, char, color)
        (4,  0.5, "●", "bright_red"),
        (7,  1.0, "◆", "bright_yellow"),
        (10, 1.2, "◉", "bright_cyan"),
        (14, 0.8, "▲", "bright_magenta"),
        (19, 2.0, "■", "bright_green"),
    ]
    bodies: list[Body] = [Body(cx, cy, 0.0, 0.0, star_mass, "☀", "bright_yellow")]
    for radius, mass, char, color in planet_data:
        angle = random.uniform(0, 2 * math.pi)
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        v = math.sqrt(G * star_mass / radius)
        vx = -v * math.sin(angle)
        vy = v * math.cos(angle)
        bodies.append(Body(x, y, vx, vy, mass, char, color))
    return bodies


def preset_figure8() -> list[Body]:
    """3 equal-mass bodies in the Chenciner-Montgomery figure-8 choreography.

    Reference solution (Chenciner & Montgomery 2000):
      positions at t=0 (normalised):
        r1 = ( 0.9700436, -0.2430087)
        r2 = (-0.9700436,  0.2430087)
        r3 = ( 0.0,        0.0)
      velocities:
        v3 = (0.93240737/2, 0.86473146/2)  -- actually (2*v3) shared symmetrically
    Scaled to canvas coordinates.
    """
    cx, cy = CANVAS_W / 2, CANVAS_H / 2
    # The canonical figure-8 uses G=1, mass=1. We need to scale to our G and canvas.
    # Scale factor: map unit positions to roughly ±8 canvas units
    scale_pos = 8.0
    # Time scaling: in canonical units, period T ≈ 6.3259. With our G=500, mass=1:
    # velocities scale as sqrt(G*m/scale_pos) relative to canonical
    scale_vel = math.sqrt(G / scale_pos)

    # Canonical positions (Chenciner-Montgomery)
    pos = [
        ( 0.9700436, -0.2430087),
        (-0.9700436,  0.2430087),
        ( 0.0,        0.0),
    ]
    # Canonical velocities
    vx3 =  0.93240737 / 2
    vy3 =  0.86473146 / 2
    vel = [
        ( vx3,  vy3),
        ( vx3,  vy3),
        (-2 * vx3, -2 * vy3),
    ]

    mass = 1.0
    colors = ["bright_red", "bright_cyan", "bright_yellow"]
    chars = ["●", "◆", "★"]

    bodies: list[Body] = []
    for k in range(3):
        x = cx + pos[k][0] * scale_pos
        y = cy + pos[k][1] * scale_pos
        vx = vel[k][0] * scale_vel
        vy = vel[k][1] * scale_vel
        bodies.append(Body(x, y, vx, vy, mass, chars[k], colors[k]))
    return bodies


PRESETS = {
    "Chaos":    preset_chaos,
    "Binary":   preset_binary,
    "Solar":    preset_solar,
    "Figure-8": preset_figure8,
}


class GravityApp(App):
    CSS = """
    Screen { background: #0a0a0a; }
    #sidebar {
        width: 28;
        padding: 1 2;
        border-right: solid grey;
    }
    .lbl { color: grey; margin-top: 1; height: 1; }
    .btn { margin-top: 1; width: 100%; }
    .preset-btn { margin-top: 0; width: 100%; }
    #canvas {
        padding: 1;
        border: solid grey;
    }
    #stats {
        height: 3;
        padding: 0 2;
        border-top: solid grey;
        color: grey;
        content-align: left middle;
    }
    #section-lbl {
        color: grey;
        margin-top: 2;
        height: 1;
    }
    """
    TITLE = "GRAVITY  --  N-Body Orbital Simulator"
    BINDINGS = [
        ("space", "toggle_pause", "Pause/Resume"),
        ("r", "reset", "Reset"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._preset_name = "Solar"
        self._bodies: list[Body] = PRESETS[self._preset_name]()
        self._timer = None
        self._paused = False
        self._tick_count = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Button("⏸  PAUSE", id="btn_pause", variant="warning", classes="btn")
                yield Button("↺  RESET", id="btn_reset", variant="default", classes="btn")
                yield Static("── Presets ──", id="section-lbl")
                yield Button("Chaos",    id="btn_chaos",   variant="default", classes="preset-btn")
                yield Button("Binary",   id="btn_binary",  variant="default", classes="preset-btn")
                yield Button("Solar",    id="btn_solar",   variant="primary", classes="preset-btn")
                yield Button("Figure-8", id="btn_figure8", variant="default", classes="preset-btn")
            with Vertical():
                yield Static(render_bodies(self._bodies), id="canvas")
                yield Static(self._stats_text(), id="stats")
        yield Footer()

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / 30, self._tick)

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    @on(Button.Pressed, "#btn_pause")
    def on_btn_pause(self) -> None:
        self.action_toggle_pause()

    @on(Button.Pressed, "#btn_reset")
    def on_btn_reset(self) -> None:
        self.action_reset()

    @on(Button.Pressed, "#btn_chaos")
    def on_btn_chaos(self) -> None:
        self._load_preset("Chaos")

    @on(Button.Pressed, "#btn_binary")
    def on_btn_binary(self) -> None:
        self._load_preset("Binary")

    @on(Button.Pressed, "#btn_solar")
    def on_btn_solar(self) -> None:
        self._load_preset("Solar")

    @on(Button.Pressed, "#btn_figure8")
    def on_btn_figure8(self) -> None:
        self._load_preset("Figure-8")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_toggle_pause(self) -> None:
        if self._timer is None:
            return
        if self._paused:
            self._timer.resume()
            self._paused = False
            self.query_one("#btn_pause", Button).label = "⏸  PAUSE"
        else:
            self._timer.pause()
            self._paused = True
            self.query_one("#btn_pause", Button).label = "▶  RESUME"

    def action_reset(self) -> None:
        self._bodies = PRESETS[self._preset_name]()
        self._tick_count = 0
        if self._paused and self._timer:
            self._timer.resume()
            self._paused = False
            self.query_one("#btn_pause", Button).label = "⏸  PAUSE"
        self._redraw()

    def _load_preset(self, name: str) -> None:
        self._preset_name = name
        self._bodies = PRESETS[name]()
        self._tick_count = 0
        # Highlight active preset button
        for pid, pname in (
            ("btn_chaos",   "Chaos"),
            ("btn_binary",  "Binary"),
            ("btn_solar",   "Solar"),
            ("btn_figure8", "Figure-8"),
        ):
            btn = self.query_one(f"#{pid}", Button)
            btn.variant = "primary" if pname == name else "default"
        if self._paused and self._timer:
            self._timer.resume()
            self._paused = False
            self.query_one("#btn_pause", Button).label = "⏸  PAUSE"
        self._redraw()

    # ------------------------------------------------------------------
    # Simulation loop
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        tick_bodies(self._bodies)
        self._tick_count += 1
        self._redraw()

    def _redraw(self) -> None:
        self.query_one("#canvas", Static).update(render_bodies(self._bodies))
        self.query_one("#stats",  Static).update(self._stats_text())

    def _stats_text(self) -> str:
        ke = kinetic_energy(self._bodies)
        return (
            f"Bodies: {len(self._bodies)}   "
            f"Preset: {self._preset_name}   "
            f"Tick: {self._tick_count}   "
            f"KE: {ke:.1f}"
        )


if __name__ == "__main__":
    GravityApp().run()
