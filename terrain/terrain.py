#!/usr/bin/env python3
"""
terrain -- Procedural terrain heightmap generator using Diamond-Square algorithm.
"It's just mountains and water. What more do you want?"
"""
from __future__ import annotations
import random
import math
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, Static
from textual import on

# Grid dimensions: 2^n+1. Use 65x33 (fits 65 wide, subsample to 28 tall).
GRID_W = 65
GRID_H = 33  # 2^5+1 = 33; we display top 28 rows
DISPLAY_H = 28

# Terrain thresholds and display chars/colours.
# These are base thresholds; sea_level shifts them.
BASE_THRESHOLDS = [
    (0.15, "≈", "bright_blue"),   # deep ocean
    (0.25, "~", "blue"),           # shallow water
    (0.30, "·", "yellow"),         # beach/sand
    (0.50, "░", "bright_green"),   # lowland/grass
    (0.65, "▒", "green"),          # forest/highland
    (0.78, "▓", "grey50"),         # mountain
    (0.88, "█", "white"),          # high mountain
    (1.01, "█", "bright_white"),   # snow/peak
]

UNGENERATED_CHAR = "?"
UNGENERATED_STYLE = "grey30"

# Cells per timer tick during generation animation
CELLS_PER_TICK = 12


def make_grid() -> list[list[float | None]]:
    return [[None] * GRID_W for _ in range(GRID_H)]


def terrain_char(h: float, sea_offset: float) -> tuple[str, str]:
    """Return (char, colour) for a height value with sea level offset applied."""
    shifted = h - sea_offset
    for threshold, char, colour in BASE_THRESHOLDS:
        if shifted < threshold:
            return char, colour
    return "█", "bright_white"


def render_terrain(grid: list[list[float | None]], sea_offset: float) -> Text:
    text = Text(no_wrap=True)
    for row_idx in range(DISPLAY_H):
        row = grid[row_idx]
        for cell in row:
            if cell is None:
                text.append(UNGENERATED_CHAR, style=UNGENERATED_STYLE)
            else:
                ch, col = terrain_char(cell, sea_offset)
                text.append(ch, style=col)
        text.append("\n")
    return text


def count_stats(
    grid: list[list[float | None]], sea_offset: float
) -> tuple[int, int, float]:
    """Return (generated_count, land_count, peak_height) for display rows only."""
    total = DISPLAY_H * GRID_W
    generated = 0
    land = 0
    peak = 0.0
    for row in grid[:DISPLAY_H]:
        for cell in row:
            if cell is not None:
                generated += 1
                shifted = cell - sea_offset
                # land = above shallow water threshold (0.25)
                if shifted >= 0.25:
                    land += 1
                if cell > peak:
                    peak = cell
    return generated, land, peak


class DiamondSquare:
    """
    Incremental Diamond-Square generator.

    Exposes a queue of pending (step, r, c, size) operations
    so the TUI can advance a few cells per tick.
    """

    def __init__(self, roughness: float, seed: int) -> None:
        self.roughness = roughness
        self.seed = seed
        self.grid = make_grid()
        self._rng = random.Random(seed)
        self._step_size = GRID_H - 1  # start with full grid
        self._range = 1.0
        self._queue: list[tuple[str, int, int, int]] = []
        self.done = False
        self._init_corners()
        self._build_queue()

    def _init_corners(self) -> None:
        sz = GRID_H - 1  # 32
        # corners must fit in both dimensions; GRID_W-1 = 64 = 2*sz
        self.grid[0][0] = self._rng.random()
        self.grid[0][GRID_W - 1] = self._rng.random()
        self.grid[GRID_H - 1][0] = self._rng.random()
        self.grid[GRID_H - 1][GRID_W - 1] = self._rng.random()

    def _build_queue(self) -> None:
        """Walk through all diamond then square steps and enqueue them."""
        # step_size halves each iteration; GRID_H-1 = 32
        step = GRID_H - 1  # 32
        while step >= 2:
            half = step // 2
            # Diamond steps: centres of each square tile
            r = half
            while r <= GRID_H - 1:
                c = half
                while c <= GRID_W - 1:
                    self._queue.append(("D", r, c, step))
                    c += step
                r += step
            # Square steps: all midpoints of diamond edges.
            # At each half-step, a point (r, c) is a square midpoint when
            # exactly one of r, c is an odd multiple of half and the other
            # is an even multiple of half (i.e. on a grid-aligned row or col).
            r = 0
            while r <= GRID_H - 1:
                # If r is an even multiple of half, columns are odd multiples of half
                if (r // half) % 2 == 0:
                    c = half
                    while c <= GRID_W - 1:
                        self._queue.append(("S", r, c, step))
                        c += step
                else:
                    # r is odd multiple of half, columns are even multiples of half
                    c = 0
                    while c <= GRID_W - 1:
                        self._queue.append(("S", r, c, step))
                        c += step
                r += half
            step //= 2

    def _rand(self, scale: float) -> float:
        return (self._rng.random() * 2 - 1) * scale

    def _scale_for_step(self, step: int) -> float:
        """Compute the roughness scale for a given step size."""
        # Number of halvings from initial step (32)
        if step == 0:
            return 0.0
        halvings = int(math.log2(GRID_H - 1)) - int(math.log2(step))
        return (self.roughness ** halvings)

    def _diamond(self, r: int, c: int, step: int) -> None:
        half = step // 2
        corners = []
        for dr, dc in [(-half, -half), (-half, half), (half, -half), (half, half)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < GRID_H and 0 <= nc < GRID_W:
                v = self.grid[nr][nc]
                if v is not None:
                    corners.append(v)
        if corners:
            avg = sum(corners) / len(corners)
            scale = self._scale_for_step(step)
            self.grid[r][c] = max(0.0, min(1.0, avg + self._rand(scale)))

    def _square(self, r: int, c: int, step: int) -> None:
        half = step // 2
        neighbors = []
        for dr, dc in [(-half, 0), (half, 0), (0, -half), (0, half)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < GRID_H and 0 <= nc < GRID_W:
                v = self.grid[nr][nc]
                if v is not None:
                    neighbors.append(v)
        if neighbors:
            avg = sum(neighbors) / len(neighbors)
            scale = self._scale_for_step(step)
            self.grid[r][c] = max(0.0, min(1.0, avg + self._rand(scale)))

    def advance(self, n: int) -> None:
        """Process up to n cells from the queue."""
        for _ in range(n):
            if not self._queue:
                self._fill_gaps()
                self.done = True
                return
            op, r, c, step = self._queue.pop(0)
            if op == "D":
                self._diamond(r, c, step)
            else:
                self._square(r, c, step)
        if not self._queue:
            self._fill_gaps()
            self.done = True

    def _fill_gaps(self) -> None:
        """Fill any remaining None cells with averaged neighbour values (catches edge cases in non-square grids)."""
        changed = True
        while changed:
            changed = False
            for r in range(GRID_H):
                for c in range(GRID_W):
                    if self.grid[r][c] is None:
                        neighbours = []
                        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < GRID_H and 0 <= nc < GRID_W and self.grid[nr][nc] is not None:
                                neighbours.append(self.grid[nr][nc])
                        if neighbours:
                            self.grid[r][c] = sum(neighbours) / len(neighbours)
                            changed = True

    def progress(self) -> float:
        total = DISPLAY_H * GRID_W
        gen, _, _ = count_stats(self.grid, 0.0)
        return gen / total if total else 1.0


class TerrainApp(App):
    CSS = """
    Screen { background: #050808; }
    #sidebar {
        width: 22;
        padding: 1 2;
        border-right: solid $primary-darken-3;
    }
    .lbl { color: $text-muted; margin-top: 1; height: 1; }
    .title { color: bright_white; text-style: bold; margin-bottom: 1; }
    .btn { margin-top: 1; width: 100%; }
    .row { height: 3; }
    .adj-btn { width: 5; min-width: 5; }
    .adj-lbl { width: 12; content-align: left middle; color: $text; }
    #canvas { padding: 1; }
    #stats {
        height: 8;
        padding: 0 2;
        border-top: solid $primary-darken-3;
        color: $text-muted;
    }
    """
    TITLE = "TERRAIN  --  Procedural Diamond-Square Heightmap"
    BINDINGS = [
        ("n", "new_terrain", "New"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._roughness: float = 0.5
        self._sea_level: float = 0.25
        self._sea_offset: float = 0.0  # derived: sea_level - 0.25
        self._seed: int = random.randint(0, 999999)
        self._gen: DiamondSquare | None = None
        self._timer = None
        self._paused = False
        self._gen_complete = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("⛰  TERRAIN", classes="title")
                yield Button("⟳ New", id="btn_new", variant="success", classes="btn")
                yield Label("", classes="lbl")
                # Roughness row
                with Horizontal(classes="row"):
                    yield Button("-", id="btn_rough_dn", classes="adj-btn")
                    yield Label(f"Rough: {self._roughness:.1f}", id="lbl_rough", classes="adj-lbl")
                    yield Button("+", id="btn_rough_up", classes="adj-btn")
                # Sea level row
                with Horizontal(classes="row"):
                    yield Button("-", id="btn_sea_dn", classes="adj-btn")
                    yield Label(f"Sea: {self._sea_level:.2f}", id="lbl_sea", classes="adj-lbl")
                    yield Button("+", id="btn_sea_up", classes="adj-btn")
                yield Label("", classes="lbl")
                yield Button("⏸ Pause gen", id="btn_pause", classes="btn")
            with Vertical():
                yield Static("", id="canvas")
                yield Static("", id="stats")
        yield Footer()

    def on_mount(self) -> None:
        self._start_generation()
        self._timer = self.set_interval(1 / 15, self._tick)

    def _start_generation(self) -> None:
        self._seed = random.randint(0, 999999)
        self._gen = DiamondSquare(self._roughness, self._seed)
        self._gen_complete = False
        self._paused = False
        btn = self.query_one("#btn_pause", Button)
        btn.label = "⏸ Pause gen"

    def _sea_offset_val(self) -> float:
        return self._sea_level - 0.25

    def _tick(self) -> None:
        if self._gen is None:
            return
        if not self._paused and not self._gen_complete:
            self._gen.advance(CELLS_PER_TICK)
            if self._gen.done:
                self._gen_complete = True
        self._redraw()

    def _redraw(self) -> None:
        if self._gen is None:
            return
        sea_off = self._sea_offset_val()
        canvas_text = render_terrain(self._gen.grid, sea_off)
        self.query_one("#canvas", Static).update(canvas_text)
        self._update_stats()

    def _update_stats(self) -> None:
        if self._gen is None:
            return
        sea_off = self._sea_offset_val()
        gen, land, peak = count_stats(self._gen.grid, sea_off)
        total = DISPLAY_H * GRID_W
        pct = gen / total * 100 if total else 100
        land_pct = land / gen * 100 if gen else 0.0
        status = "GENERATED" if self._gen_complete else f"{pct:.0f}%"
        stats_text = (
            f"Seed:     {self._seed}\n"
            f"Roughness: {self._roughness:.1f}\n"
            f"Sea level: {self._sea_level:.2f}\n"
            f"Land:      {land_pct:.1f}%\n"
            f"Peak:      {peak:.2f}\n"
            f"Progress:  {status}"
        )
        self.query_one("#stats", Static).update(stats_text)

    def _regen(self) -> None:
        """Regenerate with current roughness/sea_level but new seed."""
        self._start_generation()

    def _regen_same_seed(self) -> None:
        """Regenerate with current seed (used when params change)."""
        old_seed = self._seed
        self._gen = DiamondSquare(self._roughness, old_seed)
        self._gen_complete = False
        self._paused = False
        btn = self.query_one("#btn_pause", Button)
        btn.label = "⏸ Pause gen"

    @on(Button.Pressed, "#btn_new")
    def on_btn_new(self) -> None:
        self._regen()

    @on(Button.Pressed, "#btn_rough_up")
    def on_rough_up(self) -> None:
        self._roughness = min(1.0, round(self._roughness + 0.1, 1))
        self.query_one("#lbl_rough", Label).update(f"Rough: {self._roughness:.1f}")
        self._regen_same_seed()

    @on(Button.Pressed, "#btn_rough_dn")
    def on_rough_dn(self) -> None:
        self._roughness = max(0.1, round(self._roughness - 0.1, 1))
        self.query_one("#lbl_rough", Label).update(f"Rough: {self._roughness:.1f}")
        self._regen_same_seed()

    @on(Button.Pressed, "#btn_sea_up")
    def on_sea_up(self) -> None:
        self._sea_level = min(0.5, round(self._sea_level + 0.05, 2))
        self.query_one("#lbl_sea", Label).update(f"Sea: {self._sea_level:.2f}")
        self._redraw()

    @on(Button.Pressed, "#btn_sea_dn")
    def on_sea_dn(self) -> None:
        self._sea_level = max(0.0, round(self._sea_level - 0.05, 2))
        self.query_one("#lbl_sea", Label).update(f"Sea: {self._sea_level:.2f}")
        self._redraw()

    @on(Button.Pressed, "#btn_pause")
    def on_btn_pause(self) -> None:
        if self._gen_complete:
            return
        self._paused = not self._paused
        btn = self.query_one("#btn_pause", Button)
        btn.label = "▶ Resume gen" if self._paused else "⏸ Pause gen"

    def action_new_terrain(self) -> None:
        self._regen()


if __name__ == "__main__":
    TerrainApp().run()
