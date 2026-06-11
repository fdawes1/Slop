#!/usr/bin/env python3
"""
pendulum -- Double pendulum chaos visualiser.
"Two rods, one pivot, infinite trouble. That's physics for you."
"""
from __future__ import annotations
import math
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, Static
from textual import on

# ── canvas geometry ────────────────────────────────────────────────────────────
CANVAS_W = 70
CANVAS_H = 28
PIVOT_COL = 35
PIVOT_ROW = 2

# physics constants
G = 9.81
SUBSTEPS = 5
SUBSTEP_DT = 0.01          # total dt = 0.05 per frame
TRAIL_MAX = 300
FPS = 30


# ── physics ────────────────────────────────────────────────────────────────────

def derivatives(
    state: tuple[float, float, float, float],
    m1: float, m2: float, L1: float, L2: float, g: float
) -> tuple[float, float, float, float]:
    """Return (dθ1, dω1, dθ2, dω2) for the double pendulum."""
    th1, w1, th2, w2 = state
    delta = th2 - th1
    sin_d = math.sin(delta)
    cos_d = math.cos(delta)

    denom1 = (m1 + m2) * L1 - m2 * L1 * cos_d * cos_d
    denom2 = (L2 / L1) * denom1

    dw1 = (
        m2 * L1 * w1 * w1 * sin_d * cos_d
        + m2 * g * math.sin(th2) * cos_d
        + m2 * L2 * w2 * w2 * sin_d
        - (m1 + m2) * g * math.sin(th1)
    ) / denom1

    dw2 = (
        -m2 * L2 * w2 * w2 * sin_d * cos_d
        + (m1 + m2) * g * math.sin(th1) * cos_d
        - (m1 + m2) * L1 * w1 * w1 * sin_d
        - (m1 + m2) * g * math.sin(th2)
    ) / denom2

    return (w1, dw1, w2, dw2)


def rk4_step(
    state: tuple[float, float, float, float],
    m1: float, m2: float, L1: float, L2: float, g: float, dt: float
) -> tuple[float, float, float, float]:
    """Single RK4 integration step."""
    def add(s, ds, h):
        return tuple(a + b * h for a, b in zip(s, ds))

    k1 = derivatives(state, m1, m2, L1, L2, g)
    k2 = derivatives(add(state, k1, dt / 2), m1, m2, L1, L2, g)
    k3 = derivatives(add(state, k2, dt / 2), m1, m2, L1, L2, g)
    k4 = derivatives(add(state, k3, dt), m1, m2, L1, L2, g)

    return tuple(
        s + (dt / 6) * (a + 2 * b + 2 * c + d)
        for s, a, b, c, d in zip(state, k1, k2, k3, k4)
    )


def energy(state: tuple[float, float, float, float],
           m1: float, m2: float, L1: float, L2: float, g: float) -> float:
    """Total mechanical energy."""
    th1, w1, th2, w2 = state
    # positions
    y1 = -L1 * math.cos(th1)
    y2 = -L1 * math.cos(th1) - L2 * math.cos(th2)
    # KE
    vx1 = L1 * w1 * math.cos(th1)
    vy1 = L1 * w1 * math.sin(th1)
    vx2 = vx1 + L2 * w2 * math.cos(th2)
    vy2 = vy1 + L2 * w2 * math.sin(th2)
    ke = 0.5 * m1 * (vx1**2 + vy1**2) + 0.5 * m2 * (vx2**2 + vy2**2)
    # PE  (pivot is zero reference)
    pe = m1 * g * y1 + m2 * g * y2
    return ke + pe


# ── Bresenham line ─────────────────────────────────────────────────────────────

def bresenham(x0: int, y0: int, x1: int, y1: int):
    """Yield (x, y) integer grid points along the line."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1
    err = dx - dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


# ── canvas renderer ────────────────────────────────────────────────────────────

def render_canvas(
    state: tuple[float, float, float, float],
    trail: list[tuple[float, float]],
    ghost_state: tuple[float, float, float, float] | None,
    ghost_trail: list[tuple[float, float]],
    L1: float, L2: float,
) -> Text:
    # scale so L1+L2 spans ~12 rows
    scale = 12.0 / (L1 + L2)

    # blank grid  (space)
    grid: list[list[tuple[str, str]]] = [
        [(" ", "") for _ in range(CANVAS_W)]
        for _ in range(CANVAS_H)
    ]

    def set_cell(col: int, row: int, ch: str, style: str) -> None:
        if 0 <= col < CANVAS_W and 0 <= row < CANVAS_H:
            grid[row][col] = (ch, style)

    def pendulum_positions(st):
        th1, _, th2, _ = st
        j_col = PIVOT_COL + int(round(L1 * scale * math.sin(th1)))
        j_row = PIVOT_ROW + int(round(L1 * scale * math.cos(th1)))
        t_col = j_col + int(round(L2 * scale * math.sin(th2)))
        t_row = j_row + int(round(L2 * scale * math.cos(th2)))
        return j_col, j_row, t_col, t_row

    # ── ghost trail ────────────────────────────────────────────────────────────
    if ghost_trail:
        n = len(ghost_trail)
        for i, (gc, gr) in enumerate(ghost_trail[::3]):
            frac = i / max(n // 3, 1)
            style = "bright_cyan" if frac > 0.7 else ("cyan" if frac > 0.3 else "grey39")
            set_cell(int(round(gc)), int(round(gr)), "·", style)

    # ── main trail ─────────────────────────────────────────────────────────────
    n = len(trail)
    for i, (tc, tr) in enumerate(trail[::3]):
        frac = i / max(n // 3, 1)
        style = "bright_red" if frac > 0.7 else ("red" if frac > 0.3 else "grey30")
        set_cell(int(round(tc)), int(round(tr)), "·", style)

    # ── ghost pendulum arms ────────────────────────────────────────────────────
    if ghost_state is not None:
        gj_col, gj_row, gt_col, gt_row = pendulum_positions(ghost_state)
        for x, y in bresenham(PIVOT_COL, PIVOT_ROW, gj_col, gj_row):
            set_cell(x, y, "·", "dark_cyan")
        for x, y in bresenham(gj_col, gj_row, gt_col, gt_row):
            set_cell(x, y, "·", "dark_cyan")
        set_cell(gj_col, gj_row, "○", "cyan")
        set_cell(gt_col, gt_row, "●", "bright_cyan")

    # ── main pendulum arms ─────────────────────────────────────────────────────
    j_col, j_row, t_col, t_row = pendulum_positions(state)

    for x, y in bresenham(PIVOT_COL, PIVOT_ROW, j_col, j_row):
        set_cell(x, y, "·", "bright_white")
    for x, y in bresenham(j_col, j_row, t_col, t_row):
        set_cell(x, y, "·", "bright_white")

    set_cell(PIVOT_COL, PIVOT_ROW, "▲", "bright_white")
    set_cell(j_col, j_row, "○", "bright_white")
    set_cell(t_col, t_row, "●", "bright_red")

    # ── assemble Rich Text ─────────────────────────────────────────────────────
    text = Text(no_wrap=True)
    for row in grid:
        for ch, style in row:
            if style:
                text.append(ch, style=style)
            else:
                text.append(ch)
        text.append("\n")
    return text


def tip_canvas_pos(
    state: tuple[float, float, float, float],
    L1: float, L2: float,
) -> tuple[float, float]:
    """Return canvas (col, row) of the tip (end of second rod)."""
    th1, _, th2, _ = state
    scale = 12.0 / (L1 + L2)
    j_col = PIVOT_COL + L1 * scale * math.sin(th1)
    j_row = PIVOT_ROW + L1 * scale * math.cos(th1)
    t_col = j_col + L2 * scale * math.sin(th2)
    t_row = j_row + L2 * scale * math.cos(th2)
    return t_col, t_row


# ── App ────────────────────────────────────────────────────────────────────────

class PendulumApp(App):
    CSS = """
    Screen { background: $surface; }
    #sidebar {
        width: 28;
        padding: 1 2;
        border-right: solid $primary-darken-2;
    }
    .lbl { color: $text-muted; margin-top: 1; height: 1; }
    .param-row { height: 1; margin-top: 1; }
    .param-label { width: 10; color: $text; content-align: left middle; }
    .param-btn { width: 3; min-width: 3; }
    .param-val { width: 8; color: $accent; content-align: center middle; }
    .btn { margin-top: 1; width: 100%; }
    #canvas { padding: 1; }
    #stats {
        height: 4;
        padding: 0 2;
        border-top: solid $primary-darken-2;
        color: $text-muted;
    }
    """
    TITLE = "PENDULUM  --  Double Pendulum Chaos Visualiser"
    BINDINGS = [
        ("space", "toggle_pause", "Pause"),
        ("r", "reset", "Reset"),
        ("g", "ghost", "Ghost"),
        ("q", "quit", "Quit"),
    ]

    # ── param limits ──────────────────────────────────────────────────────────
    PARAM_DEFS: dict[str, tuple[float, float, float, float]] = {
        # id: (min, max, step, default)
        "m1":   (0.5, 5.0,   0.5,  1.0),
        "m2":   (0.5, 5.0,   0.5,  1.0),
        "th1":  (-180, 180,  15.0, 90.0),
        "th2":  (-180, 180,  15.0, 90.0),
    }

    def __init__(self) -> None:
        super().__init__()
        # current param values
        self._vals: dict[str, float] = {k: v[3] for k, v in self.PARAM_DEFS.items()}
        # simulation state: (θ1, ω1, θ2, ω2)  angles in radians
        self._state = self._initial_state()
        self._trail: list[tuple[float, float]] = []
        self._ghost_state: tuple[float, float, float, float] | None = None
        self._ghost_trail: list[tuple[float, float]] = []
        self._running = False
        self._paused = False
        self._tick_count = 0
        self._timer = None

    def _initial_state(self) -> tuple[float, float, float, float]:
        th1 = math.radians(self._vals["th1"])
        th2 = math.radians(self._vals["th2"])
        return (th1, 0.0, th2, 0.0)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("⌬ PENDULUM", classes="lbl")
                # parameter rows
                for pid, (lo, hi, step, default) in self.PARAM_DEFS.items():
                    with Horizontal(classes="param-row", id=f"row_{pid}"):
                        yield Button("-", id=f"dec_{pid}", classes="param-btn")
                        yield Static(self._fmt_param(pid), id=f"val_{pid}", classes="param-val")
                        yield Button("+", id=f"inc_{pid}", classes="param-btn")
                yield Button("⟳ Reset", id="btn_reset", variant="default", classes="btn")
                yield Button("⏸ Pause", id="btn_pause", variant="primary", classes="btn")
                yield Button("👻 Ghost", id="btn_ghost", variant="warning", classes="btn")
                yield Label("", id="stats_params", classes="lbl")
                yield Static("", id="stats_energy")
            with Vertical():
                yield Static(
                    render_canvas(
                        self._state, self._trail,
                        self._ghost_state, self._ghost_trail,
                        1.0, 1.0
                    ),
                    id="canvas"
                )
                yield Static("Press ⟳ Reset to start.", id="stats")
        yield Footer()

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / FPS, self._tick)
        self._timer.pause()
        self._update_canvas()

    # ── param formatting ──────────────────────────────────────────────────────

    def _fmt_param(self, pid: str) -> str:
        v = self._vals[pid]
        if pid == "m1":
            return f"m₁: {v:.1f}"
        if pid == "m2":
            return f"m₂: {v:.1f}"
        if pid == "th1":
            return f"θ₁: {int(v):+d}°"
        if pid == "th2":
            return f"θ₂: {int(v):+d}°"
        return str(v)

    def _refresh_param_label(self, pid: str) -> None:
        self.query_one(f"#val_{pid}", Static).update(self._fmt_param(pid))

    # ── button handlers ───────────────────────────────────────────────────────

    def _handle_param_button(self, pid: str, direction: int) -> None:
        lo, hi, step, _ = self.PARAM_DEFS[pid]
        new_val = self._vals[pid] + direction * step
        self._vals[pid] = max(lo, min(hi, new_val))
        self._refresh_param_label(pid)

    @on(Button.Pressed, "#dec_m1")
    def dec_m1(self) -> None: self._handle_param_button("m1", -1)

    @on(Button.Pressed, "#inc_m1")
    def inc_m1(self) -> None: self._handle_param_button("m1", +1)

    @on(Button.Pressed, "#dec_m2")
    def dec_m2(self) -> None: self._handle_param_button("m2", -1)

    @on(Button.Pressed, "#inc_m2")
    def inc_m2(self) -> None: self._handle_param_button("m2", +1)

    @on(Button.Pressed, "#dec_th1")
    def dec_th1(self) -> None: self._handle_param_button("th1", -1)

    @on(Button.Pressed, "#inc_th1")
    def inc_th1(self) -> None: self._handle_param_button("th1", +1)

    @on(Button.Pressed, "#dec_th2")
    def dec_th2(self) -> None: self._handle_param_button("th2", -1)

    @on(Button.Pressed, "#inc_th2")
    def inc_th2(self) -> None: self._handle_param_button("th2", +1)

    @on(Button.Pressed, "#btn_reset")
    def on_reset(self) -> None:
        self.action_reset()

    @on(Button.Pressed, "#btn_pause")
    def on_pause_btn(self) -> None:
        self.action_toggle_pause()

    @on(Button.Pressed, "#btn_ghost")
    def on_ghost_btn(self) -> None:
        self.action_ghost()

    # ── actions ───────────────────────────────────────────────────────────────

    def action_reset(self) -> None:
        self._state = self._initial_state()
        self._trail = []
        self._ghost_state = None
        self._ghost_trail = []
        self._tick_count = 0
        self._paused = False
        if self._timer:
            self._timer.resume()
        self._running = True
        self.query_one("#btn_pause", Button).label = "⏸ Pause"
        self._update_canvas()
        self._update_stats()

    def action_toggle_pause(self) -> None:
        if not self._running:
            self.action_reset()
            return
        if self._paused:
            self._timer.resume()
            self._paused = False
            self.query_one("#btn_pause", Button).label = "⏸ Pause"
        else:
            self._timer.pause()
            self._paused = True
            self.query_one("#btn_pause", Button).label = "▶ Resume"

    def action_ghost(self) -> None:
        """Spawn a ghost pendulum offset by +0.01 rad on θ1."""
        th1, w1, th2, w2 = self._state
        self._ghost_state = (th1 + 0.01, w1, th2, w2)
        self._ghost_trail = []
        if not self._running:
            self.action_reset()

    # ── simulation tick ───────────────────────────────────────────────────────

    def _tick(self) -> None:
        m1 = self._vals["m1"]
        m2 = self._vals["m2"]
        L1 = 1.0
        L2 = 1.0

        for _ in range(SUBSTEPS):
            self._state = rk4_step(self._state, m1, m2, L1, L2, G, SUBSTEP_DT)
            if self._ghost_state is not None:
                self._ghost_state = rk4_step(
                    self._ghost_state, m1, m2, L1, L2, G, SUBSTEP_DT
                )

        # record trail
        tip = tip_canvas_pos(self._state, L1, L2)
        self._trail.append(tip)
        if len(self._trail) > TRAIL_MAX:
            self._trail = self._trail[-TRAIL_MAX:]

        if self._ghost_state is not None:
            gtip = tip_canvas_pos(self._ghost_state, L1, L2)
            self._ghost_trail.append(gtip)
            if len(self._ghost_trail) > TRAIL_MAX:
                self._ghost_trail = self._ghost_trail[-TRAIL_MAX:]

        self._tick_count += 1
        self._update_canvas()
        if self._tick_count % 3 == 0:
            self._update_stats()

    def _update_canvas(self) -> None:
        self.query_one("#canvas", Static).update(
            render_canvas(
                self._state, self._trail,
                self._ghost_state, self._ghost_trail,
                1.0, 1.0,
            )
        )

    def _update_stats(self) -> None:
        th1, w1, th2, w2 = self._state
        m1 = self._vals["m1"]
        m2 = self._vals["m2"]
        e = energy(self._state, m1, m2, 1.0, 1.0, G)
        status = "PAUSED" if self._paused else ("RUNNING" if self._running else "STOPPED")
        self.query_one("#stats", Static).update(
            f"Tick: {self._tick_count}   Status: {status}\n"
            f"θ₁: {math.degrees(th1):+.1f}°  θ₂: {math.degrees(th2):+.1f}°\n"
            f"Energy: {e:.3f} J"
            + ("  [Ghost active]" if self._ghost_state is not None else "")
        )


if __name__ == "__main__":
    PendulumApp().run()
