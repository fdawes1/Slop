#!/usr/bin/env python3
"""
fourier -- Fourier series epicycles animator.
"It's just circles all the way down, tha knows."
"""
from __future__ import annotations
import math
from collections import deque
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, Static
from textual import on

# Canvas dimensions
CANVAS_W = 72
CANVAS_H = 30
SPLIT = 36       # left half: epicycles, right half: waveform
CENTRE_X = 17    # epicycle centre col
CENTRE_Y = 15    # epicycle centre row
WAVE_LEN = 36    # rolling buffer length = right half width

# ── Waveform presets ──────────────────────────────────────────────────────────

def _square(n_terms: int) -> list[tuple[float, float, float]]:
    return [
        (4.0 / math.pi / n, n, 0.0)
        for n in range(1, n_terms * 2, 2)
    ][:n_terms]

def _sawtooth(n_terms: int) -> list[tuple[float, float, float]]:
    return [
        (2.0 / math.pi * ((-1) ** (k + 1)) / k, k, 0.0)
        for k in range(1, n_terms + 1)
    ]

def _triangle(n_terms: int) -> list[tuple[float, float, float]]:
    coeffs = []
    idx = 0
    for n in range(1, n_terms * 2 + 1, 2):
        amp = 8.0 / (math.pi ** 2) * ((-1) ** idx) / (n * n)
        coeffs.append((amp, n, 0.0))
        idx += 1
        if len(coeffs) == n_terms:
            break
    return coeffs

def _circle(n_terms: int) -> list[tuple[float, float, float]]:
    return [(12.0, 1, 0.0)]

def _figure8(n_terms: int) -> list[tuple[float, float, float]]:
    return [
        (10.0, 1, 0.0),
        (5.0, 2, math.pi / 2),
    ]

WAVEFORMS: dict[str, tuple[str, object]] = {
    "square":   ("Square",   _square),
    "sawtooth": ("Sawtooth", _sawtooth),
    "triangle": ("Triangle", _triangle),
    "circle":   ("Circle",   _circle),
    "figure8":  ("Figure-8", _figure8),
}

# ── Arm colour gradient (cyan → through colours → magenta) ───────────────────
_ARM_COLOURS = [
    "bright_cyan",
    "cyan",
    "bright_green",
    "yellow",
    "bright_red",
    "bright_magenta",
]

def _arm_colour(idx: int, total: int) -> str:
    if total == 1:
        return "bright_cyan"
    t = idx / max(total - 1, 1)
    i = int(t * (len(_ARM_COLOURS) - 1))
    return _ARM_COLOURS[min(i, len(_ARM_COLOURS) - 1)]

# ── Grid drawing helpers ──────────────────────────────────────────────────────

GridCell = tuple[str, str]
Grid = list[list[GridCell]]

BLANK: GridCell = (" ", "")

def make_grid() -> Grid:
    return [[BLANK] * CANVAS_W for _ in range(CANVAS_H)]

def _set(grid: Grid, x: int, y: int, char: str, color: str) -> None:
    xi, yi = int(round(x)), int(round(y))
    if 0 <= xi < CANVAS_W and 0 <= yi < CANVAS_H:
        grid[yi][xi] = (char, color)

def draw_circle(grid: Grid, cx: float, cy: float, r: float, char: str, color: str) -> None:
    if r < 0.5:
        return
    steps = max(16, int(2 * math.pi * r))
    for i in range(steps):
        a = 2 * math.pi * i / steps
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a) * 0.5
        _set(grid, x, y, char, color)

def draw_line(grid: Grid, x0: float, y0: float, x1: float, y1: float,
              char: str, color: str) -> None:
    ix0, iy0, ix1, iy1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx = abs(ix1 - ix0)
    dy = abs(iy1 - iy0)
    sx = 1 if ix0 < ix1 else -1
    sy = 1 if iy0 < iy1 else -1
    # pick directional char unless caller provided something specific
    if char == "auto":
        if dy == 0:
            ch = "─"
        elif dx == 0:
            ch = "│"
        elif (sx == sy):
            ch = "╲"
        else:
            ch = "╱"
    else:
        ch = char
    err = dx - dy
    x, y = ix0, iy0
    while True:
        _set(grid, x, y, ch, color)
        if x == ix1 and y == iy1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy

# ── Waveform trail colours ────────────────────────────────────────────────────
_TRAIL = [
    "bright_yellow",
    "yellow",
    "gold3",
    "dark_orange",
    "orange4",
    "grey62",
    "grey46",
    "grey39",
    "grey30",
    "grey23",
]

def _trail_colour(age: int, total: int) -> str:
    """age 0 = newest, age total-1 = oldest."""
    idx = int(age / max(total - 1, 1) * (len(_TRAIL) - 1))
    return _TRAIL[min(idx, len(_TRAIL) - 1)]

# ── Main render function ──────────────────────────────────────────────────────

def render_frame(
    coeffs: list[tuple[float, float, float]],
    t: float,
    wave_buf: deque,
) -> Text:
    grid = make_grid()

    # ── draw epicycles on left half ──
    px, py = float(CENTRE_X), float(CENTRE_Y)
    total = len(coeffs)
    for idx, (amp, freq, phase) in enumerate(coeffs):
        angle = 2 * math.pi * freq * t + phase
        nx = px + amp * math.cos(angle)
        ny = py + amp * math.sin(angle) * 0.5
        # clamp drawing to left half
        color = _arm_colour(idx, total)
        draw_circle(grid, px, py, amp, "·", "grey23")
        draw_line(grid, px, py, nx, ny, "auto", color)
        px, py = nx, ny

    tip_x, tip_y = px, py

    # ── waveform in right half ──
    buf_list = list(wave_buf)  # index 0 = oldest, -1 = newest
    n_buf = len(buf_list)
    for age_from_new, y_val in enumerate(reversed(buf_list)):
        col = SPLIT + (WAVE_LEN - 1 - age_from_new)
        row = int(round(CENTRE_Y + y_val))
        if 0 <= col < CANVAS_W and 0 <= row < CANVAS_H:
            if age_from_new == 0:
                grid[row][col] = ("●", "bright_yellow")
            else:
                c = _trail_colour(age_from_new, n_buf)
                grid[row][col] = ("·", c)

    # ── horizontal connector: tip → current waveform point ──
    if n_buf > 0:
        cur_col = SPLIT + WAVE_LEN - 1
        cur_row = int(round(CENTRE_Y + buf_list[-1]))
        draw_line(grid, tip_x, tip_y, cur_col, cur_row, "─", "grey42")

    # ── separator line ──
    for row in range(CANVAS_H):
        if grid[row][SPLIT] == BLANK:
            grid[row][SPLIT] = ("│", "grey23")

    # ── build Rich Text ──
    text = Text(no_wrap=True)
    for row in grid:
        for ch, col in row:
            if col:
                text.append(ch, style=col)
            else:
                text.append(ch)
        text.append("\n")
    return text

# ── App ───────────────────────────────────────────────────────────────────────

class FourierApp(App):
    CSS = """
    Screen { background: #050510; }
    #sidebar {
        width: 22;
        padding: 1 2;
        border-right: solid #1a1a3a;
    }
    .sect { color: #4444aa; margin-top: 1; height: 1; }
    .btn  { margin-top: 1; width: 100%; }
    .btn_sm { margin-top: 0; width: 49%; }
    #canvas { padding: 1; }
    #stats {
        height: 5;
        padding: 0 2;
        border-top: solid #1a1a3a;
        color: #888888;
        content-align: left middle;
    }
    #title {
        color: ansi_bright_cyan;
        text-style: bold;
        height: 2;
        content-align: center middle;
        border-bottom: solid #1a1a3a;
        margin-bottom: 1;
    }
    """
    TITLE = "FOURIER  --  Epicycle Waveform Decomposition"
    BINDINGS = [
        ("space", "toggle_pause", "Pause"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._waveform = "square"
        self._n_terms = 7
        self._dt = 0.05
        self._t = 0.0
        self._paused = False
        self._wave_buf: deque = deque(maxlen=WAVE_LEN)
        self._timer = None
        self._coeffs: list[tuple[float, float, float]] = []
        self._rebuild_coeffs()

    def _rebuild_coeffs(self) -> None:
        _, fn = WAVEFORMS[self._waveform]
        self._coeffs = fn(self._n_terms)
        # scale so max amplitude fits left half (0–35)
        total_amp = sum(abs(a) for a, _, __ in self._coeffs)
        if total_amp > 14:
            scale = 14.0 / total_amp
            self._coeffs = [(a * scale, f, p) for a, f, p in self._coeffs]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("◎ FOURIER", id="title")
                yield Label("── waveform ──", classes="sect")
                yield Button("Square",   id="btn_square",   classes="btn")
                yield Button("Sawtooth", id="btn_sawtooth", classes="btn")
                yield Button("Triangle", id="btn_triangle", classes="btn")
                yield Button("Circle",   id="btn_circle",   classes="btn")
                yield Button("Figure-8", id="btn_figure8",  classes="btn")
                yield Label("── terms ──", classes="sect")
                with Horizontal():
                    yield Button("−", id="btn_terms_dn", classes="btn_sm")
                    yield Button("+", id="btn_terms_up", classes="btn_sm")
                yield Label(f"Terms: {self._n_terms}", id="lbl_terms")
                yield Label("── speed ──", classes="sect")
                with Horizontal():
                    yield Button("slow", id="btn_slow", classes="btn_sm")
                    yield Button("fast", id="btn_fast", classes="btn_sm")
                yield Button("⏸ Pause", id="btn_pause", classes="btn", variant="warning")
            with Vertical():
                yield Static("", id="canvas")
                yield Static("", id="stats")
        yield Footer()

    def on_mount(self) -> None:
        self._wave_buf.clear()
        self._timer = self.set_interval(1 / 20, self._tick)
        self._render()

    def _render(self) -> None:
        frame = render_frame(self._coeffs, self._t, self._wave_buf)
        self.query_one("#canvas", Static).update(frame)
        name, _ = WAVEFORMS[self._waveform]
        self.query_one("#stats", Static).update(
            f"Waveform: {name}   Terms: {len(self._coeffs)}   "
            f"t = {self._t:.2f}   dt = {self._dt}"
        )
        self.query_one("#lbl_terms", Label).update(f"Terms: {self._n_terms}")

    def _tick(self) -> None:
        py = 0.0
        for amp, freq, phase in self._coeffs:
            py += amp * math.sin(2 * math.pi * freq * self._t + phase) * 0.5
        self._wave_buf.append(py)
        self._t += self._dt
        self._render()

    def action_toggle_pause(self) -> None:
        btn = self.query_one("#btn_pause", Button)
        if self._paused:
            self._timer.resume()
            self._paused = False
            btn.label = "⏸ Pause"
        else:
            self._timer.pause()
            self._paused = True
            btn.label = "▶ Resume"

    @on(Button.Pressed, "#btn_pause")
    def on_pause(self) -> None:
        self.action_toggle_pause()

    def _set_waveform(self, key: str) -> None:
        self._waveform = key
        self._wave_buf.clear()
        self._t = 0.0
        self._rebuild_coeffs()

    @on(Button.Pressed, "#btn_square")
    def on_square(self) -> None:
        self._set_waveform("square")

    @on(Button.Pressed, "#btn_sawtooth")
    def on_sawtooth(self) -> None:
        self._set_waveform("sawtooth")

    @on(Button.Pressed, "#btn_triangle")
    def on_triangle(self) -> None:
        self._set_waveform("triangle")

    @on(Button.Pressed, "#btn_circle")
    def on_circle(self) -> None:
        self._set_waveform("circle")

    @on(Button.Pressed, "#btn_figure8")
    def on_figure8(self) -> None:
        self._set_waveform("figure8")

    @on(Button.Pressed, "#btn_terms_up")
    def on_terms_up(self) -> None:
        self._n_terms = min(20, self._n_terms + 1)
        self._wave_buf.clear()
        self._t = 0.0
        self._rebuild_coeffs()

    @on(Button.Pressed, "#btn_terms_dn")
    def on_terms_dn(self) -> None:
        self._n_terms = max(1, self._n_terms - 1)
        self._wave_buf.clear()
        self._t = 0.0
        self._rebuild_coeffs()

    @on(Button.Pressed, "#btn_slow")
    def on_slow(self) -> None:
        self._dt = 0.02

    @on(Button.Pressed, "#btn_fast")
    def on_fast(self) -> None:
        self._dt = 0.08


if __name__ == "__main__":
    FourierApp().run()
