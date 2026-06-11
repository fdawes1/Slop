#!/usr/bin/env python3
"""
swarm -- Boids flocking simulation.
"Individually thick as pigeons, collectively sharper than owt."
"""
from __future__ import annotations
import math
import random
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, Static
from textual import on

CANVAS_W = 72
CANVAS_H = 26
MAX_SPEED = 4.0
MIN_SPEED = 0.5
VISION_RADIUS = 12.0
SEPARATION_RADIUS = 2.5
DT = 0.3

# Arrow chars: East, SE, South, SW, West, NW, North, NE  (8 dirs, clockwise from East)
_ARROWS = "→↘↓↙←↖↑↗"


def _dir_char(vx: float, vy: float) -> str:
    angle = math.atan2(vy, vx)  # -pi..pi, 0=East
    # Convert to 0..2pi, then bucket into 8 slices
    angle_norm = angle % (2 * math.pi)
    idx = int((angle_norm + math.pi / 8) / (math.pi / 4)) % 8
    return _ARROWS[idx]


def _clamp_speed(vx: float, vy: float) -> tuple[float, float]:
    spd = math.hypot(vx, vy)
    if spd == 0.0:
        angle = random.uniform(0, 2 * math.pi)
        return MIN_SPEED * math.cos(angle), MIN_SPEED * math.sin(angle)
    if spd > MAX_SPEED:
        f = MAX_SPEED / spd
        return vx * f, vy * f
    if spd < MIN_SPEED:
        f = MIN_SPEED / spd
        return vx * f, vy * f
    return vx, vy


def _torus_delta(a: float, b: float, size: float) -> float:
    """Signed delta from a to b on a toroidal axis of given size."""
    d = b - a
    if d > size / 2:
        d -= size
    elif d < -size / 2:
        d += size
    return d


def _torus_dist(x1: float, y1: float, x2: float, y2: float) -> float:
    dx = _torus_delta(x1, x2, CANVAS_W)
    dy = _torus_delta(y1, y2, CANVAS_H)
    return math.hypot(dx, dy)


class Boid:
    __slots__ = ("x", "y", "vx", "vy")

    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy


def _make_boids(n: int) -> list[Boid]:
    boids = []
    for _ in range(n):
        x = random.uniform(0, CANVAS_W)
        y = random.uniform(0, CANVAS_H)
        angle = random.uniform(0, 2 * math.pi)
        spd = random.uniform(MIN_SPEED, MAX_SPEED)
        boids.append(Boid(x, y, spd * math.cos(angle), spd * math.sin(angle)))
    return boids


def _step_boids(
    boids: list[Boid],
    sep_w: float,
    ali_w: float,
    coh_w: float,
) -> list[Boid]:
    n = len(boids)
    new_boids: list[Boid] = []

    for i, b in enumerate(boids):
        sep_fx = sep_fy = 0.0
        ali_vx = ali_vy = 0.0
        coh_cx = coh_cy = 0.0
        n_vision = 0
        n_sep = 0

        for j, o in enumerate(boids):
            if i == j:
                continue
            dist = _torus_dist(b.x, b.y, o.x, o.y)
            if dist < VISION_RADIUS:
                dx = _torus_delta(b.x, o.x, CANVAS_W)
                dy = _torus_delta(b.y, o.y, CANVAS_H)
                n_vision += 1
                ali_vx += o.vx
                ali_vy += o.vy
                coh_cx += dx
                coh_cy += dy
                if dist < SEPARATION_RADIUS and dist > 0.0:
                    # Push away: force proportional to 1/dist
                    sep_fx -= dx / dist
                    sep_fy -= dy / dist
                    n_sep += 1

        ax = ay = 0.0

        if n_sep > 0:
            ax += sep_w * sep_fx
            ay += sep_w * sep_fy

        if n_vision > 0:
            # Alignment: steer toward average velocity
            ax += ali_w * (ali_vx / n_vision - b.vx)
            ay += ali_w * (ali_vy / n_vision - b.vy)
            # Cohesion: steer toward centre of mass
            ax += coh_w * (coh_cx / n_vision)
            ay += coh_w * (coh_cy / n_vision)

        # Clamp acceleration magnitude
        acc_mag = math.hypot(ax, ay)
        if acc_mag > 0.5:
            f = 0.5 / acc_mag
            ax *= f
            ay *= f

        nvx = b.vx + ax * DT
        nvy = b.vy + ay * DT
        nvx, nvy = _clamp_speed(nvx, nvy)

        nx = (b.x + nvx * DT) % CANVAS_W
        ny = (b.y + nvy * DT) % CANVAS_H

        new_boids.append(Boid(nx, ny, nvx, nvy))

    return new_boids


def _render_boids(boids: list[Boid]) -> Text:
    # Build char/color grid
    grid_char = [[" "] * CANVAS_W for _ in range(CANVAS_H)]
    grid_col = [[""] * CANVAS_W for _ in range(CANVAS_H)]

    # Compute density for each boid (neighbours within radius 5)
    dense_radius = 5.0
    for b in boids:
        cx = int(b.x) % CANVAS_W
        cy = int(b.y) % CANVAS_H
        neighbours = sum(
            1 for o in boids
            if o is not b and _torus_dist(b.x, b.y, o.x, o.y) < dense_radius
        )
        colour = "bright_magenta" if neighbours >= 3 else "bright_cyan"
        char = _dir_char(b.vx, b.vy)
        grid_char[cy][cx] = char
        grid_col[cy][cx] = colour

    text = Text(no_wrap=True)
    for r in range(CANVAS_H):
        for c in range(CANVAS_W):
            ch = grid_char[r][c]
            col = grid_col[r][c]
            if col:
                text.append(ch, style=f"bold {col}")
            else:
                text.append(ch, style="dim #1a1a3a")
        text.append("\n")
    return text


def _avg_speed(boids: list[Boid]) -> float:
    if not boids:
        return 0.0
    return sum(math.hypot(b.vx, b.vy) for b in boids) / len(boids)


def _avg_neighbours(boids: list[Boid]) -> float:
    if not boids:
        return 0.0
    total = sum(
        sum(
            1 for o in boids
            if o is not b and _torus_dist(b.x, b.y, o.x, o.y) < VISION_RADIUS
        )
        for b in boids
    )
    return total / len(boids)


class SwarmApp(App):
    CSS = """
    Screen { background: #050510; }
    #sidebar {
        width: 28;
        padding: 1 2;
        border-right: solid #2a2a5a;
    }
    .section-lbl {
        color: #6060a0;
        margin-top: 1;
        height: 1;
    }
    .val-lbl {
        color: #a0a0d0;
        height: 1;
        margin-bottom: 0;
    }
    .btn-row {
        height: 3;
        margin-bottom: 0;
    }
    .adj-btn {
        width: 5;
        min-width: 3;
    }
    .big-btn {
        margin-top: 1;
        width: 100%;
    }
    #stats-lbl {
        color: #6060a0;
        margin-top: 1;
    }
    #canvas {
        padding: 1;
        border: solid #2a2a5a;
    }
    #title-lbl {
        color: bright_cyan;
        text-style: bold;
        margin-bottom: 1;
        height: 1;
    }
    """
    TITLE = "SWARM  --  Boids Flocking Simulation"
    BINDINGS = [
        ("space", "toggle_pause", "Pause/Resume"),
        ("r", "reset", "Reset"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.sep_w = 1.5
        self.ali_w = 1.0
        self.coh_w = 1.0
        self.population = 60
        self._tick_count = 0
        self._running = True
        self._timer = None
        self.boids = _make_boids(self.population)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("⬡ SWARM", id="title-lbl")

                yield Label("Separation", classes="section-lbl")
                yield Label(f"Sep: {self.sep_w:.1f}", id="lbl_sep", classes="val-lbl")
                with Horizontal(classes="btn-row"):
                    yield Button("+", id="btn_sep_up", classes="adj-btn")
                    yield Button("-", id="btn_sep_dn", classes="adj-btn")

                yield Label("Alignment", classes="section-lbl")
                yield Label(f"Ali: {self.ali_w:.1f}", id="lbl_ali", classes="val-lbl")
                with Horizontal(classes="btn-row"):
                    yield Button("+", id="btn_ali_up", classes="adj-btn")
                    yield Button("-", id="btn_ali_dn", classes="adj-btn")

                yield Label("Cohesion", classes="section-lbl")
                yield Label(f"Coh: {self.coh_w:.1f}", id="lbl_coh", classes="val-lbl")
                with Horizontal(classes="btn-row"):
                    yield Button("+", id="btn_coh_up", classes="adj-btn")
                    yield Button("-", id="btn_coh_dn", classes="adj-btn")

                yield Label("Population", classes="section-lbl")
                yield Label(f"Pop: {self.population}", id="lbl_pop", classes="val-lbl")
                with Horizontal(classes="btn-row"):
                    yield Button("+", id="btn_pop_up", classes="adj-btn")
                    yield Button("-", id="btn_pop_dn", classes="adj-btn")

                yield Button("⟳ Reset", id="btn_reset", classes="big-btn")
                yield Button("⏸ Pause", id="btn_pause", classes="big-btn")

                yield Label("", id="stats_lbl", classes="section-lbl")

            with Vertical():
                yield Static(_render_boids(self.boids), id="canvas")
        yield Footer()

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / 20, self._tick)
        self._update_stats()

    def _tick(self) -> None:
        self.boids = _step_boids(self.boids, self.sep_w, self.ali_w, self.coh_w)
        self._tick_count += 1
        self.query_one("#canvas", Static).update(_render_boids(self.boids))
        self._update_stats()

    def _update_stats(self) -> None:
        avg_spd = _avg_speed(self.boids)
        avg_nb = _avg_neighbours(self.boids)
        self.query_one("#stats_lbl", Label).update(
            f"Tick: {self._tick_count}\n"
            f"Boids: {len(self.boids)}\n"
            f"Avg spd: {avg_spd:.2f}\n"
            f"Avg nbrs: {avg_nb:.1f}"
        )

    def _update_param_labels(self) -> None:
        self.query_one("#lbl_sep", Label).update(f"Sep: {self.sep_w:.1f}")
        self.query_one("#lbl_ali", Label).update(f"Ali: {self.ali_w:.1f}")
        self.query_one("#lbl_coh", Label).update(f"Coh: {self.coh_w:.1f}")
        self.query_one("#lbl_pop", Label).update(f"Pop: {self.population}")

    @on(Button.Pressed, "#btn_sep_up")
    def on_sep_up(self) -> None:
        self.sep_w = round(min(3.0, self.sep_w + 0.1), 1)
        self._update_param_labels()

    @on(Button.Pressed, "#btn_sep_dn")
    def on_sep_dn(self) -> None:
        self.sep_w = round(max(0.0, self.sep_w - 0.1), 1)
        self._update_param_labels()

    @on(Button.Pressed, "#btn_ali_up")
    def on_ali_up(self) -> None:
        self.ali_w = round(min(3.0, self.ali_w + 0.1), 1)
        self._update_param_labels()

    @on(Button.Pressed, "#btn_ali_dn")
    def on_ali_dn(self) -> None:
        self.ali_w = round(max(0.0, self.ali_w - 0.1), 1)
        self._update_param_labels()

    @on(Button.Pressed, "#btn_coh_up")
    def on_coh_up(self) -> None:
        self.coh_w = round(min(3.0, self.coh_w + 0.1), 1)
        self._update_param_labels()

    @on(Button.Pressed, "#btn_coh_dn")
    def on_coh_dn(self) -> None:
        self.coh_w = round(max(0.0, self.coh_w - 0.1), 1)
        self._update_param_labels()

    @on(Button.Pressed, "#btn_pop_up")
    def on_pop_up(self) -> None:
        self.population = min(120, self.population + 5)
        self._update_param_labels()
        # Add extra boids on the fly
        extra = self.population - len(self.boids)
        if extra > 0:
            self.boids.extend(_make_boids(extra))

    @on(Button.Pressed, "#btn_pop_dn")
    def on_pop_dn(self) -> None:
        self.population = max(5, self.population - 5)
        self._update_param_labels()
        # Trim boids if over target
        if len(self.boids) > self.population:
            self.boids = self.boids[: self.population]

    @on(Button.Pressed, "#btn_reset")
    def on_reset_btn(self) -> None:
        self.action_reset()

    @on(Button.Pressed, "#btn_pause")
    def on_pause_btn(self) -> None:
        self.action_toggle_pause()

    def action_toggle_pause(self) -> None:
        if self._timer is None:
            return
        if self._running:
            self._timer.pause()
            self._running = False
            self.query_one("#btn_pause", Button).label = "▶ Resume"
        else:
            self._timer.resume()
            self._running = True
            self.query_one("#btn_pause", Button).label = "⏸ Pause"

    def action_reset(self) -> None:
        self._tick_count = 0
        self.boids = _make_boids(self.population)
        self.query_one("#canvas", Static).update(_render_boids(self.boids))
        self._update_stats()
        # Make sure timer is running after reset
        if self._timer and not self._running:
            self._timer.resume()
            self._running = True
            self.query_one("#btn_pause", Button).label = "⏸ Pause"


if __name__ == "__main__":
    SwarmApp().run()
