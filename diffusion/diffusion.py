#!/usr/bin/env python3
"""
diffusion -- Gray-Scott reaction-diffusion simulator.
"Two chemicals walk into a grid. One feeds, one eats. Neither leaves."
"""
from __future__ import annotations
import random
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, Static
from textual import on

GRID_W = 60
GRID_H = 24
Du = 0.16
Dv = 0.08
DT = 1.0
SUBSTEPS = 5

PRESETS: dict[str, tuple[float, float]] = {
    "Spots":   (0.035, 0.065),
    "Stripes": (0.060, 0.062),
    "Maze":    (0.029, 0.057),
    "Coral":   (0.058, 0.065),
    "Chaos":   (0.026, 0.051),
    "Mitosis": (0.028, 0.053),
}


def make_grid() -> tuple[list[list[float]], list[list[float]]]:
    U = [[1.0] * GRID_W for _ in range(GRID_H)]
    V = [[0.0] * GRID_W for _ in range(GRID_H)]
    # seed a handful of 3x3 blobs
    for _ in range(6):
        sr = random.randint(2, GRID_H - 4)
        sc = random.randint(2, GRID_W - 4)
        for dr in range(3):
            for dc in range(3):
                U[sr + dr][sc + dc] = 0.0
                V[sr + dr][sc + dc] = 1.0
    return U, V


def step(U: list[list[float]], V: list[list[float]], f: float, k: float) -> None:
    """In-place Gray-Scott update. Runs one substep."""
    H = GRID_H
    W = GRID_W
    # pre-build new arrays to avoid reading half-updated values
    nU = [[0.0] * W for _ in range(H)]
    nV = [[0.0] * W for _ in range(H)]

    for r in range(H):
        r_u = (r - 1) % H
        r_d = (r + 1) % H
        Ur = U[r]
        Vr = V[r]
        U_up   = U[r_u]
        U_down = U[r_d]
        V_up   = V[r_u]
        V_down = V[r_d]
        nUr = nU[r]
        nVr = nV[r]
        for c in range(W):
            c_l = (c - 1) % W
            c_r = (c + 1) % W
            u = Ur[c]
            v = Vr[c]
            lap_u = U_up[c] + U_down[c] + Ur[c_l] + Ur[c_r] - 4.0 * u
            lap_v = V_up[c] + V_down[c] + Vr[c_l] + Vr[c_r] - 4.0 * v
            uvv = u * v * v
            du = Du * lap_u - uvv + f * (1.0 - u)
            dv = Dv * lap_v + uvv - (f + k) * v
            nUr[c] = u + du * DT
            nVr[c] = v + dv * DT

    # copy back
    for r in range(H):
        U[r][:] = nU[r]
        V[r][:] = nV[r]


def render_grid(V: list[list[float]]) -> Text:
    text = Text(no_wrap=True)
    for row in V:
        for v in row:
            if v < 0.1:
                text.append(" ", style="default")
            elif v < 0.2:
                text.append("·", style="grey")
            elif v < 0.35:
                text.append("░", style="grey")
            elif v < 0.5:
                text.append("▒", style="bright_blue")
            elif v < 0.65:
                text.append("▓", style="bright_cyan")
            elif v < 0.8:
                text.append("█", style="bright_green")
            else:
                text.append("█", style="bright_yellow")
        text.append("\n")
    return text


class DiffusionApp(App):
    CSS = """
    Screen { background: #000408; }
    #sidebar {
        width: 26;
        padding: 1 2;
        border-right: solid #0a2a3a;
    }
    #title {
        color: ansi_bright_cyan;
        text-style: bold;
        margin-bottom: 1;
        height: 1;
    }
    .section-lbl {
        color: grey;
        margin-top: 1;
        height: 1;
    }
    .btn-preset {
        margin-top: 0;
        width: 100%;
        height: 2;
    }
    .btn-action {
        margin-top: 1;
        width: 100%;
        height: 2;
    }
    #stats {
        margin-top: 2;
        color: grey;
    }
    #canvas {
        padding: 1 1;
    }
    Footer { background: #000408; }
    Header { background: #000408; color: ansi_bright_cyan; }
    """
    TITLE = "DIFFUSION  --  Gray-Scott Reaction-Diffusion"
    BINDINGS = [
        ("space", "pause", "Pause/Resume"),
        ("r", "reset", "Reset"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._preset = "Spots"
        self._f, self._k = PRESETS["Spots"]
        self.U, self.V = make_grid()
        self._timer = None
        self._running = False
        self._ticks = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("⬡ DIFFUSION", id="title")
                yield Label("Presets", classes="section-lbl")
                yield Button("Spots",   id="btn_spots",   classes="btn-preset")
                yield Button("Stripes", id="btn_stripes", classes="btn-preset")
                yield Button("Maze",    id="btn_maze",    classes="btn-preset")
                yield Button("Coral",   id="btn_coral",   classes="btn-preset")
                yield Button("Chaos",   id="btn_chaos",   classes="btn-preset")
                yield Button("Mitosis", id="btn_mitosis", classes="btn-preset")
                yield Button("⟳ Reset", id="btn_reset",  classes="btn-action", variant="default")
                yield Button("⏸ Pause", id="btn_pause",  classes="btn-action", variant="primary")
                yield Static("", id="stats")
            yield Static(render_grid(self.V), id="canvas")
        yield Footer()

    def on_mount(self) -> None:
        self._running = True
        self._timer = self.set_interval(1 / 20, self._tick)
        self._update_stats()

    def _update_stats(self) -> None:
        self.query_one("#stats", Static).update(
            f"[bright_cyan]{self._preset}[/]\n"
            f"[grey50]steps:[/] {self._ticks * SUBSTEPS}\n"
            f"[grey50]f:[/] {self._f:.3f}\n"
            f"[grey50]k:[/] {self._k:.3f}"
        )

    def _tick(self) -> None:
        for _ in range(SUBSTEPS):
            step(self.U, self.V, self._f, self._k)
        self._ticks += 1
        self.query_one("#canvas", Static).update(render_grid(self.V))
        self._update_stats()

    def _set_preset(self, name: str) -> None:
        self._preset = name
        self._f, self._k = PRESETS[name]
        self._do_reset()

    def _do_reset(self) -> None:
        self.U, self.V = make_grid()
        self._ticks = 0
        if not self._running and self._timer:
            self._timer.resume()
            self._running = True
            self.query_one("#btn_pause", Button).label = "⏸ Pause"
        self.query_one("#canvas", Static).update(render_grid(self.V))
        self._update_stats()

    @on(Button.Pressed, "#btn_spots")
    def on_spots(self) -> None:
        self._set_preset("Spots")

    @on(Button.Pressed, "#btn_stripes")
    def on_stripes(self) -> None:
        self._set_preset("Stripes")

    @on(Button.Pressed, "#btn_maze")
    def on_maze(self) -> None:
        self._set_preset("Maze")

    @on(Button.Pressed, "#btn_coral")
    def on_coral(self) -> None:
        self._set_preset("Coral")

    @on(Button.Pressed, "#btn_chaos")
    def on_chaos(self) -> None:
        self._set_preset("Chaos")

    @on(Button.Pressed, "#btn_mitosis")
    def on_mitosis(self) -> None:
        self._set_preset("Mitosis")

    @on(Button.Pressed, "#btn_reset")
    def on_reset(self) -> None:
        self._do_reset()

    @on(Button.Pressed, "#btn_pause")
    def on_pause_btn(self) -> None:
        self.action_pause()

    def action_pause(self) -> None:
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
        self._do_reset()


if __name__ == "__main__":
    DiffusionApp().run()
