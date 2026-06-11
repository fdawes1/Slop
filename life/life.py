#!/usr/bin/env python3
"""
life -- Conway's Game of Life.
"Any live cell with two or three live neighbours survives."
"""
from __future__ import annotations
import random
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, Static
from textual import on

GRID_W = 70
GRID_H = 28

# Age colour thresholds
def age_style(age: int) -> str:
    if age == 1:
        return "bright_white"
    elif age <= 3:
        return "bright_cyan"
    elif age <= 7:
        return "bright_blue"
    else:
        return "bright_magenta"


def step(cells: list[list[int]], ages: list[list[int]]) -> tuple[list[list[int]], list[list[int]]]:
    new_cells = [[0] * GRID_W for _ in range(GRID_H)]
    new_ages  = [[0] * GRID_W for _ in range(GRID_H)]
    for r in range(GRID_H):
        for c in range(GRID_W):
            neighbours = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    neighbours += cells[(r + dr) % GRID_H][(c + dc) % GRID_W]
            alive = cells[r][c]
            if alive:
                survives = neighbours in (2, 3)
                new_cells[r][c] = 1 if survives else 0
                new_ages[r][c]  = ages[r][c] + 1 if survives else 0
            else:
                born = neighbours == 3
                new_cells[r][c] = 1 if born else 0
                new_ages[r][c]  = 1 if born else 0
    return new_cells, new_ages


def empty_grid() -> list[list[int]]:
    return [[0] * GRID_W for _ in range(GRID_H)]


def render_grid(
    cells: list[list[int]],
    ages: list[list[int]],
    cursor_r: int,
    cursor_c: int,
    draw_mode: bool,
) -> Text:
    text = Text(no_wrap=True)
    for r in range(GRID_H):
        for c in range(GRID_W):
            if r == cursor_r and c == cursor_c:
                style = "bold bright_green"
                text.append("+", style=style)
            elif cells[r][c]:
                text.append("█", style=age_style(ages[r][c]))
            else:
                text.append(" ")
        text.append("\n")
    return text


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

def place_pattern(cells: list[list[int]], coords: list[tuple[int, int]], origin_r: int, origin_c: int) -> None:
    for dr, dc in coords:
        r, c = (origin_r + dr) % GRID_H, (origin_c + dc) % GRID_W
        cells[r][c] = 1


GLIDER_COORDS = [
    (0, 1),
    (1, 2),
    (2, 0), (2, 1), (2, 2),
]

# Gosper Glider Gun — all 36 cells, absolute (row, col) coords
GOSPER_GUN_COORDS = [
    (0, 24),
    (1, 22), (1, 24),
    (2, 12), (2, 13), (2, 20), (2, 21), (2, 34), (2, 35),
    (3, 11), (3, 15), (3, 20), (3, 21), (3, 34), (3, 35),
    (4,  0), (4,  1), (4, 10), (4, 16), (4, 20), (4, 21),
    (5,  0), (5,  1), (5, 10), (5, 14), (5, 16), (5, 17), (5, 22), (5, 24),
    (6, 10), (6, 16), (6, 24),
    (7, 11), (7, 15),
    (8, 12), (8, 13),
]

# Pulsar — period-3 oscillator, 48 cells in canonical form (relative to centre)
def pulsar_coords(centre_r: int = 14, centre_c: int = 35) -> list[tuple[int, int]]:
    # Pulsar has 4-fold symmetry; defined by one quadrant arm + reflections
    # Relative coords of the full pulsar (centred at 0,0)
    arm = [
        (-6, -4), (-6, -3), (-6, -2),
        (-4, -6), (-3, -6), (-2, -6),
        (-4, -1), (-3, -1), (-2, -1),
        (-1, -4), (-1, -3), (-1, -2),
    ]
    coords = []
    for dr, dc in arm:
        for sr, sc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            coords.append((centre_r + dr * sr, centre_c + dc * sc))
    return coords

R_PENTOMINO_COORDS = [
    (0, 1), (0, 2),
    (1, 0), (1, 1),
    (2, 1),
]

# Lightweight Spaceship (LWSS) — 9 cells
LWSS_COORDS = [
    (0, 1), (0, 4),
    (1, 0),
    (2, 0), (2, 4),
    (3, 0), (3, 1), (3, 2), (3, 3),
]


def make_glider() -> tuple[list[list[int]], list[list[int]]]:
    cells = empty_grid()
    place_pattern(cells, GLIDER_COORDS, 2, 2)
    return cells, empty_ages(cells)


def make_gosper_gun() -> tuple[list[list[int]], list[list[int]]]:
    cells = empty_grid()
    # Centre the gun vertically, leave left margin
    origin_r = (GRID_H - 10) // 2
    origin_c = 2
    for dr, dc in GOSPER_GUN_COORDS:
        r, c = (origin_r + dr) % GRID_H, (origin_c + dc) % GRID_W
        cells[r][c] = 1
    return cells, empty_ages(cells)


def make_pulsar() -> tuple[list[list[int]], list[list[int]]]:
    cells = empty_grid()
    for r, c in pulsar_coords(GRID_H // 2, GRID_W // 2):
        if 0 <= r < GRID_H and 0 <= c < GRID_W:
            cells[r][c] = 1
    return cells, empty_ages(cells)


def make_rpentomino() -> tuple[list[list[int]], list[list[int]]]:
    cells = empty_grid()
    place_pattern(cells, R_PENTOMINO_COORDS, GRID_H // 2, GRID_W // 2)
    return cells, empty_ages(cells)


def make_lwss() -> tuple[list[list[int]], list[list[int]]]:
    cells = empty_grid()
    place_pattern(cells, LWSS_COORDS, 4, 4)
    return cells, empty_ages(cells)


def make_random() -> tuple[list[list[int]], list[list[int]]]:
    cells = [[1 if random.random() < 0.30 else 0 for _ in range(GRID_W)] for _ in range(GRID_H)]
    return cells, empty_ages(cells)


def empty_ages(cells: list[list[int]]) -> list[list[int]]:
    return [[1 if cells[r][c] else 0 for c in range(GRID_W)] for r in range(GRID_H)]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class LifeApp(App):
    CSS = """
    Screen { background: #0a0a16; }

    #sidebar {
        width: 28;
        padding: 1 2;
        border-right: solid #2a2a4a;
        background: #0d0d1f;
    }

    .title {
        text-align: center;
        color: bright_cyan;
        text-style: bold;
        margin-bottom: 1;
    }

    .section-lbl {
        color: #6060a0;
        margin-top: 1;
        height: 1;
    }

    .btn {
        width: 100%;
        margin-top: 0;
        margin-bottom: 0;
    }

    .speed-row {
        layout: horizontal;
        width: 100%;
        height: 3;
        margin-top: 1;
    }

    .speed-btn {
        width: 1fr;
    }

    #stats-box {
        margin-top: 1;
        color: #8080c0;
        height: auto;
    }

    #canvas {
        padding: 0 1;
        border: solid #2a2a4a;
    }

    #draw-indicator {
        height: 1;
        padding: 0 1;
        color: bright_green;
    }
    """

    TITLE = "LIFE  --  Conway's Game of Life"
    BINDINGS = [
        ("r", "random_fill", "Random"),
        ("c", "clear_grid", "Clear"),
        ("s", "step_once", "Step"),
        ("p", "pause_resume", "Pause/Resume"),
        ("q", "quit", "Quit"),
        ("up", "move_up", "Up"),
        ("down", "move_down", "Down"),
        ("left", "move_left", "Left"),
        ("right", "move_right", "Right"),
        ("d", "toggle_draw", "Draw mode"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.cells, self.ages = make_random()
        self._timer = None
        self._running = False
        self._generation = 0
        self._speed = 10.0
        self._cursor_r = 0
        self._cursor_c = 0
        self._draw_mode = False

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("⬡  LIFE", classes="title")

                yield Label("── Patterns ──", classes="section-lbl")
                yield Button("Glider",      id="btn_glider",     classes="btn", variant="default")
                yield Button("Gosper Gun",  id="btn_gun",        classes="btn", variant="default")
                yield Button("Pulsar",      id="btn_pulsar",     classes="btn", variant="default")
                yield Button("R-Pentomino", id="btn_rpentomino", classes="btn", variant="default")
                yield Button("Spaceship",   id="btn_spaceship",  classes="btn", variant="default")
                yield Button("Random",      id="btn_random",     classes="btn", variant="default")
                yield Button("🗑  Clear",   id="btn_clear",      classes="btn", variant="warning")

                yield Label("── Control ──", classes="section-lbl")
                yield Button("⟳ Step",  id="btn_step",  classes="btn", variant="default")
                yield Button("⏸ Pause", id="btn_pause", classes="btn", variant="success")

                yield Label("── Speed ──", classes="section-lbl")
                with Horizontal(classes="speed-row"):
                    yield Button("1/s",  id="btn_slow", classes="speed-btn", variant="default")
                    yield Button("10/s", id="btn_med",  classes="speed-btn", variant="primary")
                    yield Button("30/s", id="btn_fast", classes="speed-btn", variant="default")

                yield Static("", id="stats-box")

            with Vertical():
                yield Static("", id="draw-indicator")
                yield Static(id="canvas")

        yield Footer()

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / self._speed, self._tick)
        self._running = True
        self._refresh_canvas()
        self._refresh_stats()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _refresh_canvas(self) -> None:
        self.query_one("#canvas", Static).update(
            render_grid(self.cells, self.ages, self._cursor_r, self._cursor_c, self._draw_mode)
        )

    def _live_count(self) -> int:
        return sum(self.cells[r][c] for r in range(GRID_H) for c in range(GRID_W))

    def _refresh_stats(self) -> None:
        draw_txt = "[DRAW]" if self._draw_mode else ""
        self.query_one("#draw-indicator", Static).update(draw_txt)
        self.query_one("#stats-box", Static).update(
            f"Gen:    {self._generation}\n"
            f"Live:   {self._live_count()}\n"
            f"Cursor: ({self._cursor_c}, {self._cursor_r})\n"
            f"Speed:  {self._speed:.0f}/s"
        )

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        if not self._running:
            return
        self.cells, self.ages = step(self.cells, self.ages)
        self._generation += 1
        self._refresh_canvas()
        self._refresh_stats()

    def _load_pattern(self, cells: list[list[int]], ages: list[list[int]]) -> None:
        if self._timer:
            self._timer.stop()
        self.cells = cells
        self.ages  = ages
        self._generation = 0
        self._running = True
        self._timer = self.set_interval(1 / self._speed, self._tick)
        self.query_one("#btn_pause", Button).label = "⏸ Pause"
        self._refresh_canvas()
        self._refresh_stats()

    def _set_speed(self, speed: float) -> None:
        self._speed = speed
        if self._timer:
            self._timer.stop()
        self._timer = self.set_interval(1 / self._speed, self._tick)
        self._refresh_stats()

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    @on(Button.Pressed, "#btn_glider")
    def on_glider(self) -> None:
        self._load_pattern(*make_glider())

    @on(Button.Pressed, "#btn_gun")
    def on_gun(self) -> None:
        self._load_pattern(*make_gosper_gun())

    @on(Button.Pressed, "#btn_pulsar")
    def on_pulsar(self) -> None:
        self._load_pattern(*make_pulsar())

    @on(Button.Pressed, "#btn_rpentomino")
    def on_rpentomino(self) -> None:
        self._load_pattern(*make_rpentomino())

    @on(Button.Pressed, "#btn_spaceship")
    def on_spaceship(self) -> None:
        self._load_pattern(*make_lwss())

    @on(Button.Pressed, "#btn_random")
    def on_random_btn(self) -> None:
        self._load_pattern(*make_random())

    @on(Button.Pressed, "#btn_clear")
    def on_clear_btn(self) -> None:
        cells = empty_grid()
        self._load_pattern(cells, empty_grid())

    @on(Button.Pressed, "#btn_step")
    def on_step_btn(self) -> None:
        self.action_step_once()

    @on(Button.Pressed, "#btn_pause")
    def on_pause_btn(self) -> None:
        self.action_pause_resume()

    @on(Button.Pressed, "#btn_slow")
    def on_slow(self) -> None:
        self._set_speed(1.0)

    @on(Button.Pressed, "#btn_med")
    def on_med(self) -> None:
        self._set_speed(10.0)

    @on(Button.Pressed, "#btn_fast")
    def on_fast(self) -> None:
        self._set_speed(30.0)

    # ------------------------------------------------------------------
    # Key actions
    # ------------------------------------------------------------------

    def action_pause_resume(self) -> None:
        if self._running:
            self._running = False
            self.query_one("#btn_pause", Button).label = "▶ Resume"
        else:
            self._running = True
            self.query_one("#btn_pause", Button).label = "⏸ Pause"
        self._refresh_stats()

    def action_random_fill(self) -> None:
        self._load_pattern(*make_random())

    def action_clear_grid(self) -> None:
        cells = empty_grid()
        self._load_pattern(cells, empty_grid())

    def action_step_once(self) -> None:
        was_running = self._running
        self._running = False
        self.cells, self.ages = step(self.cells, self.ages)
        self._generation += 1
        self._running = was_running
        self._refresh_canvas()
        self._refresh_stats()

    def _move_cursor(self, dr: int, dc: int) -> None:
        self._cursor_r = (self._cursor_r + dr) % GRID_H
        self._cursor_c = (self._cursor_c + dc) % GRID_W
        if self._draw_mode:
            r, c = self._cursor_r, self._cursor_c
            self.cells[r][c] = 1
            self.ages[r][c]  = max(1, self.ages[r][c])
        self._refresh_canvas()
        self._refresh_stats()

    def action_move_up(self)    -> None: self._move_cursor(-1,  0)
    def action_move_down(self)  -> None: self._move_cursor( 1,  0)
    def action_move_left(self)  -> None: self._move_cursor( 0, -1)
    def action_move_right(self) -> None: self._move_cursor( 0,  1)

    def action_toggle_draw(self) -> None:
        self._draw_mode = not self._draw_mode
        self._refresh_canvas()
        self._refresh_stats()

    def on_key(self, event) -> None:
        if event.key == "space":
            # Space also toggles cell at cursor (when not bound to pause)
            r, c = self._cursor_r, self._cursor_c
            if self.cells[r][c]:
                self.cells[r][c] = 0
                self.ages[r][c]  = 0
            else:
                self.cells[r][c] = 1
                self.ages[r][c]  = 1
            self._refresh_canvas()
            self._refresh_stats()
            event.stop()


if __name__ == "__main__":
    LifeApp().run()
