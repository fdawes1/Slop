#!/usr/bin/env python3
"""
sandpit -- Falling sand cellular automaton.
"It's just sand. And water. And fire. And chaos."
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

# Material constants
EMPTY = 0
SAND  = 1
WATER = 2
FIRE  = 3
STONE = 4
STEAM = 5

# Display: (char, style_normal) — fire handled separately for flicker
DISPLAY = {
    EMPTY: (" ",  "default"),
    SAND:  ("░",  "yellow"),
    WATER: ("~",  "bright_cyan"),
    STONE: ("█",  "grey50"),
    STEAM: ("°",  "grey70"),
}

FIRE_FRAMES = [
    ("▲", "bright_red"),
    ("▴", "yellow"),
]

MATERIAL_NAMES = {
    SAND:  "Sand",
    WATER: "Water",
    FIRE:  "Fire",
    STONE: "Stone",
    EMPTY: "Eraser",
}


def _new_grid() -> list[list[int]]:
    return [[EMPTY] * GRID_W for _ in range(GRID_H)]


def _new_lifetime() -> list[list[int]]:
    return [[0] * GRID_W for _ in range(GRID_H)]


def tick(grid: list[list[int]], lifetime: list[list[int]], frame: int) -> None:
    """Apply one step of physics in-place."""
    moved = [[False] * GRID_W for _ in range(GRID_H)]

    # --- FIRE & STEAM: process top-to-bottom ---
    rows_tb = list(range(GRID_H))
    for r in rows_tb:
        cols = list(range(GRID_W))
        random.shuffle(cols)
        for c in cols:
            mat = grid[r][c]
            if moved[r][c]:
                continue

            if mat == FIRE:
                lifetime[r][c] -= 1
                if lifetime[r][c] <= 0:
                    # Die — chance to become steam
                    grid[r][c] = STEAM if random.random() < 0.3 else EMPTY
                    if grid[r][c] == STEAM:
                        lifetime[r][c] = random.randint(20, 40)
                    else:
                        lifetime[r][c] = 0
                    moved[r][c] = True
                    continue

                # Try to ignite adjacent sand (5% per adjacent sand)
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < GRID_H and 0 <= nc < GRID_W:
                        if grid[nr][nc] == SAND and random.random() < 0.05:
                            grid[nr][nc] = FIRE
                            lifetime[nr][nc] = random.randint(15, 30)

                # Move upward 60% of the time
                if r > 0 and grid[r - 1][c] == EMPTY and random.random() < 0.6:
                    grid[r - 1][c] = FIRE
                    lifetime[r - 1][c] = lifetime[r][c]
                    grid[r][c] = EMPTY
                    lifetime[r][c] = 0
                    moved[r - 1][c] = True
                    moved[r][c] = True

            elif mat == STEAM:
                lifetime[r][c] -= 1
                if lifetime[r][c] <= 0:
                    grid[r][c] = EMPTY
                    lifetime[r][c] = 0
                    moved[r][c] = True
                    continue

                # Drift upward 40%
                moved_steam = False
                if r > 0 and random.random() < 0.4:
                    target_r = r - 1
                    if grid[target_r][c] == EMPTY:
                        grid[target_r][c] = STEAM
                        lifetime[target_r][c] = lifetime[r][c]
                        grid[r][c] = EMPTY
                        lifetime[r][c] = 0
                        moved[target_r][c] = True
                        moved[r][c] = True
                        moved_steam = True

                # Sideways drift
                if not moved_steam:
                    dirs = [-1, 1]
                    random.shuffle(dirs)
                    for dc in dirs:
                        nc = c + dc
                        if 0 <= nc < GRID_W and grid[r][nc] == EMPTY:
                            grid[r][nc] = STEAM
                            lifetime[r][nc] = lifetime[r][c]
                            grid[r][c] = EMPTY
                            lifetime[r][c] = 0
                            moved[r][nc] = True
                            moved[r][c] = True
                            break

    # --- SAND & WATER: process bottom-to-top ---
    rows_bt = list(range(GRID_H - 1, -1, -1))
    for r in rows_bt:
        cols = list(range(GRID_W))
        random.shuffle(cols)
        for c in cols:
            mat = grid[r][c]
            if moved[r][c]:
                continue

            if mat == SAND:
                below = r + 1
                if below >= GRID_H:
                    continue

                # Fall straight down into EMPTY or WATER
                if grid[below][c] == EMPTY:
                    grid[below][c] = SAND
                    grid[r][c] = EMPTY
                    moved[below][c] = True
                    moved[r][c] = True
                elif grid[below][c] == WATER:
                    # Swap: sand sinks, water rises
                    grid[below][c] = SAND
                    grid[r][c] = WATER
                    moved[below][c] = True
                    moved[r][c] = True
                else:
                    # Try diagonal
                    diags = [(-1, 1), (1, 1)]  # (dc, dr) where dr=+1 means below
                    random.shuffle(diags)
                    for dc, dr in diags:
                        nc = c + dc
                        nr = r + dr
                        if 0 <= nc < GRID_W and 0 <= nr < GRID_H:
                            if grid[nr][nc] == EMPTY:
                                grid[nr][nc] = SAND
                                grid[r][c] = EMPTY
                                moved[nr][nc] = True
                                moved[r][c] = True
                                break
                            elif grid[nr][nc] == WATER:
                                grid[nr][nc] = SAND
                                grid[r][c] = WATER
                                moved[nr][nc] = True
                                moved[r][c] = True
                                break

            elif mat == WATER:
                below = r + 1
                if below < GRID_H and grid[below][c] == EMPTY:
                    grid[below][c] = WATER
                    grid[r][c] = EMPTY
                    moved[below][c] = True
                    moved[r][c] = True
                else:
                    # Flow sideways
                    dirs = [-1, 1]
                    random.shuffle(dirs)
                    for dc in dirs:
                        nc = c + dc
                        if 0 <= nc < GRID_W and grid[r][nc] == EMPTY:
                            grid[r][nc] = WATER
                            grid[r][c] = EMPTY
                            moved[r][nc] = True
                            moved[r][c] = True
                            break


def render_grid(
    grid: list[list[int]],
    cursor: tuple[int, int],
    frame: int,
) -> Text:
    """Build a Rich Text object for the grid with cursor overlay."""
    text = Text(no_wrap=True)
    cx, cy = cursor  # cx=col, cy=row
    fire_char, fire_style = FIRE_FRAMES[frame % 2]

    for r in range(GRID_H):
        for c in range(GRID_W):
            if r == cy and c == cx:
                text.append("+", style="bold bright_white")
                continue
            mat = grid[r][c]
            if mat == FIRE:
                text.append(fire_char, style=fire_style)
            else:
                ch, style = DISPLAY[mat]
                text.append(ch, style=style)
        text.append("\n")
    return text


def count_materials(grid: list[list[int]]) -> dict[int, int]:
    counts: dict[int, int] = {SAND: 0, WATER: 0, FIRE: 0, STONE: 0, STEAM: 0}
    for row in grid:
        for cell in row:
            if cell in counts:
                counts[cell] += 1
    return counts


class SandpitApp(App):
    CSS = """
    Screen { background: $surface; }

    #sidebar {
        width: 26;
        padding: 1 2;
        border-right: solid $primary-darken-2;
    }

    .section-lbl {
        color: $text-muted;
        margin-top: 1;
        height: 1;
    }

    .mat-btn {
        width: 100%;
        margin-top: 0;
    }

    #btn_clear {
        margin-top: 2;
        width: 100%;
    }

    #selected-lbl {
        margin-top: 1;
        height: 2;
        color: $text;
    }

    #canvas {
        padding: 1;
    }

    #stats {
        height: 3;
        padding: 0 2;
        border-top: solid $primary-darken-2;
        color: $text-muted;
        content-align: left middle;
    }
    """

    TITLE = "SANDPIT  --  Falling Sand Automaton"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "clear", "Clear"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.grid: list[list[int]] = _new_grid()
        self.lifetime: list[list[int]] = _new_lifetime()
        self._tick_count = 0
        self._frame = 0
        self._cursor = (GRID_W // 2, GRID_H // 2)  # (col, row)
        self._material = SAND
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Material", classes="section-lbl")
                yield Button("1: Sand",   id="btn_sand",   variant="warning",  classes="mat-btn")
                yield Button("2: Water",  id="btn_water",  variant="primary",  classes="mat-btn")
                yield Button("3: Fire",   id="btn_fire",   variant="error",    classes="mat-btn")
                yield Button("4: Stone",  id="btn_stone",  variant="default",  classes="mat-btn")
                yield Button("5: Eraser", id="btn_eraser", variant="success",  classes="mat-btn")
                yield Label("", id="selected-lbl")
                yield Button("Clear (c)", id="btn_clear",  variant="default")
            with Vertical():
                yield Static(
                    render_grid(self.grid, self._cursor, self._frame),
                    id="canvas",
                )
                yield Static("", id="stats")
        yield Footer()

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / 20, self._step)
        self._refresh_selected()
        self._refresh_stats()

    # ------------------------------------------------------------------ #
    #  Timer step                                                          #
    # ------------------------------------------------------------------ #

    def _step(self) -> None:
        tick(self.grid, self.lifetime, self._frame)
        self._tick_count += 1
        self._frame += 1
        self.query_one("#canvas", Static).update(
            render_grid(self.grid, self._cursor, self._frame)
        )
        self._refresh_stats()

    # ------------------------------------------------------------------ #
    #  Key handling                                                        #
    # ------------------------------------------------------------------ #

    def on_key(self, event) -> None:
        cx, cy = self._cursor
        key = event.key

        if key == "up":
            cy = max(0, cy - 1)
        elif key == "down":
            cy = min(GRID_H - 1, cy + 1)
        elif key == "left":
            cx = max(0, cx - 1)
        elif key == "right":
            cx = min(GRID_W - 1, cx + 1)
        elif key in ("space", "enter"):
            self._place()
            return
        elif key == "1":
            self._set_material(SAND)
            return
        elif key == "2":
            self._set_material(WATER)
            return
        elif key == "3":
            self._set_material(FIRE)
            return
        elif key == "4":
            self._set_material(STONE)
            return
        elif key == "5":
            self._set_material(EMPTY)
            return
        else:
            return

        self._cursor = (cx, cy)
        # Immediate canvas refresh so cursor feels responsive
        self.query_one("#canvas", Static).update(
            render_grid(self.grid, self._cursor, self._frame)
        )

    # ------------------------------------------------------------------ #
    #  Placement                                                           #
    # ------------------------------------------------------------------ #

    def _place(self) -> None:
        cx, cy = self._cursor
        mat = self._material
        self.grid[cy][cx] = mat
        if mat == FIRE:
            self.lifetime[cy][cx] = random.randint(15, 30)
        elif mat == STEAM:
            self.lifetime[cy][cx] = random.randint(20, 40)
        else:
            self.lifetime[cy][cx] = 0

    # ------------------------------------------------------------------ #
    #  Material selection                                                  #
    # ------------------------------------------------------------------ #

    def _set_material(self, mat: int) -> None:
        self._material = mat
        self._refresh_selected()

    def _refresh_selected(self) -> None:
        name = MATERIAL_NAMES.get(self._material, "Unknown")
        self.query_one("#selected-lbl", Label).update(f"Selected:\n[bold]{name}[/bold]")

    # ------------------------------------------------------------------ #
    #  Stats                                                               #
    # ------------------------------------------------------------------ #

    def _refresh_stats(self) -> None:
        counts = count_materials(self.grid)
        cx, cy = self._cursor
        self.query_one("#stats", Static).update(
            f"Tick: {self._tick_count}   "
            f"Cursor: ({cx},{cy})   "
            f"Sand: {counts[SAND]}  "
            f"Water: {counts[WATER]}  "
            f"Fire: {counts[FIRE]}  "
            f"Stone: {counts[STONE]}  "
            f"Steam: {counts[STEAM]}"
        )

    # ------------------------------------------------------------------ #
    #  Button handlers                                                     #
    # ------------------------------------------------------------------ #

    @on(Button.Pressed, "#btn_sand")
    def _on_btn_sand(self) -> None:
        self._set_material(SAND)

    @on(Button.Pressed, "#btn_water")
    def _on_btn_water(self) -> None:
        self._set_material(WATER)

    @on(Button.Pressed, "#btn_fire")
    def _on_btn_fire(self) -> None:
        self._set_material(FIRE)

    @on(Button.Pressed, "#btn_stone")
    def _on_btn_stone(self) -> None:
        self._set_material(STONE)

    @on(Button.Pressed, "#btn_eraser")
    def _on_btn_eraser(self) -> None:
        self._set_material(EMPTY)

    @on(Button.Pressed, "#btn_clear")
    def _on_btn_clear(self) -> None:
        self.action_clear()

    # ------------------------------------------------------------------ #
    #  Actions                                                             #
    # ------------------------------------------------------------------ #

    def action_clear(self) -> None:
        self.grid = _new_grid()
        self.lifetime = _new_lifetime()
        self._tick_count = 0


if __name__ == "__main__":
    SandpitApp().run()
