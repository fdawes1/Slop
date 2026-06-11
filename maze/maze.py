#!/usr/bin/env python3
"""
maze -- Procedural maze generator with 4 solving algorithms racing simultaneously.
"Right, let's see which one of you lot can find the bloody exit."
"""
from __future__ import annotations

import heapq
import random
from collections import deque
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, Static
from textual import on

# Logical grid dimensions (odd so walls sit between cells)
MAZE_W = 25   # logical cells wide
MAZE_H = 15   # logical cells tall

# Display canvas dimensions: each cell takes 2 chars, +1 for outer walls
DISP_W = 2 * MAZE_W + 1   # 51
DISP_H = 2 * MAZE_H + 1   # 31

STEPS_SLOW = 1
STEPS_MED  = 5
STEPS_FAST = 20

SOLVER_STYLES = {
    "BFS":      ("bright_cyan",    "BFS  (shortest path)"),
    "DFS":      ("bright_yellow",  "DFS  (go deep)"),
    "A*":       ("bright_magenta", "A*   (heuristic)"),
    "Dijkstra": ("bright_green",   "Dijkstra"),
}

# ─── Maze generation ─────────────────────────────────────────────────────────

def generate_maze(w: int, h: int) -> list[list[bool]]:
    """
    Recursive backtracker DFS.
    Returns a boolean grid of size (2h+1) x (2w+1).
    True = passage (open), False = wall.
    """
    # Start all walls closed
    grid = [[False] * (2 * w + 1) for _ in range(2 * h + 1)]

    # Open cell centres
    for cy in range(h):
        for cx in range(w):
            grid[2 * cy + 1][2 * cx + 1] = True

    visited = [[False] * w for _ in range(h)]

    def carve(cx: int, cy: int) -> None:
        visited[cy][cx] = True
        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                # Remove wall between (cx,cy) and (nx,ny)
                grid[2 * cy + 1 + dy][2 * cx + 1 + dx] = True
                carve(nx, ny)

    # Iterative DFS to avoid Python recursion limit on larger mazes
    stack = [(0, 0)]
    visited[0][0] = True
    while stack:
        cx, cy = stack[-1]
        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        random.shuffle(dirs)
        moved = False
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                grid[2 * cy + 1 + dy][2 * cx + 1 + dx] = True
                visited[ny][nx] = True
                stack.append((nx, ny))
                moved = True
                break
        if not moved:
            stack.pop()

    # Entry: gap in top wall above (0,0)
    grid[0][1] = True
    # Exit: gap in bottom wall below (w-1, h-1)
    grid[2 * h][2 * (w - 1) + 1] = True

    return grid


def maze_neighbours(grid: list[list[bool]], cx: int, cy: int) -> list[tuple[int, int]]:
    """Return logical-cell neighbours reachable from (cx, cy)."""
    neighbours = []
    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
        nx, ny = cx + dx, cy + dy
        if 0 <= nx < MAZE_W and 0 <= ny < MAZE_H:
            # Wall between them is at display coords (2cy+1+dy, 2cx+1+dx)
            if grid[2 * cy + 1 + dy][2 * cx + 1 + dx]:
                neighbours.append((nx, ny))
    return neighbours


# ─── Solvers ─────────────────────────────────────────────────────────────────

class Solver:
    name: str
    color: str

    def __init__(self, grid: list[list[bool]], start: tuple[int, int], end: tuple[int, int]) -> None:
        self.grid = grid
        self.start = start
        self.end = end
        self.visited: dict[tuple[int, int], tuple[int, int] | None] = {}  # cell -> parent
        self.frontier: set[tuple[int, int]] = set()
        self.done = False
        self.path: list[tuple[int, int]] = []
        self.steps = 0
        self._init()

    def _init(self) -> None:
        raise NotImplementedError

    def step(self) -> bool:
        """Advance one node. Returns True if done."""
        raise NotImplementedError

    def _reconstruct(self, cell: tuple[int, int]) -> list[tuple[int, int]]:
        path = []
        cur: tuple[int, int] | None = cell
        while cur is not None:
            path.append(cur)
            cur = self.visited.get(cur)
        path.reverse()
        return path


class BFSSolver(Solver):
    name = "BFS"
    color = "bright_cyan"

    def _init(self) -> None:
        self._queue: deque[tuple[int, int]] = deque([self.start])
        self.visited[self.start] = None
        self.frontier = {self.start}

    def step(self) -> bool:
        if not self._queue or self.done:
            return self.done
        cell = self._queue.popleft()
        self.frontier.discard(cell)
        self.steps += 1
        if cell == self.end:
            self.done = True
            self.path = self._reconstruct(cell)
            return True
        for nb in maze_neighbours(self.grid, *cell):
            if nb not in self.visited:
                self.visited[nb] = cell
                self._queue.append(nb)
                self.frontier.add(nb)
        return False


class DFSSolver(Solver):
    name = "DFS"
    color = "bright_yellow"

    def _init(self) -> None:
        self._stack: list[tuple[int, int]] = [self.start]
        self.visited[self.start] = None
        self.frontier = {self.start}

    def step(self) -> bool:
        if not self._stack or self.done:
            return self.done
        cell = self._stack.pop()
        self.frontier.discard(cell)
        self.steps += 1
        if cell == self.end:
            self.done = True
            self.path = self._reconstruct(cell)
            return True
        for nb in maze_neighbours(self.grid, *cell):
            if nb not in self.visited:
                self.visited[nb] = cell
                self._stack.append(nb)
                self.frontier.add(nb)
        return False


class AStarSolver(Solver):
    name = "A*"
    color = "bright_magenta"

    def _init(self) -> None:
        ex, ey = self.end
        h = abs(self.start[0] - ex) + abs(self.start[1] - ey)
        self._heap: list[tuple[int, int, tuple[int, int]]] = [(h, 0, self.start)]
        self._g: dict[tuple[int, int], int] = {self.start: 0}
        self.visited[self.start] = None
        self.frontier = {self.start}

    def step(self) -> bool:
        if not self._heap or self.done:
            return self.done
        _, g, cell = heapq.heappop(self._heap)
        self.frontier.discard(cell)
        self.steps += 1
        if cell == self.end:
            self.done = True
            self.path = self._reconstruct(cell)
            return True
        if g > self._g.get(cell, float("inf")):
            return False  # stale entry
        ex, ey = self.end
        for nb in maze_neighbours(self.grid, *cell):
            ng = g + 1
            if ng < self._g.get(nb, float("inf")):
                self._g[nb] = ng
                self.visited[nb] = cell
                h = abs(nb[0] - ex) + abs(nb[1] - ey)
                heapq.heappush(self._heap, (ng + h, ng, nb))
                self.frontier.add(nb)
        return False


class DijkstraSolver(Solver):
    name = "Dijkstra"
    color = "bright_green"

    def _init(self) -> None:
        self._heap: list[tuple[int, tuple[int, int]]] = [(0, self.start)]
        self._dist: dict[tuple[int, int], int] = {self.start: 0}
        self.visited[self.start] = None
        self.frontier = {self.start}

    def step(self) -> bool:
        if not self._heap or self.done:
            return self.done
        d, cell = heapq.heappop(self._heap)
        self.frontier.discard(cell)
        self.steps += 1
        if cell == self.end:
            self.done = True
            self.path = self._reconstruct(cell)
            return True
        if d > self._dist.get(cell, float("inf")):
            return False
        for nb in maze_neighbours(self.grid, *cell):
            nd = d + 1
            if nd < self._dist.get(nb, float("inf")):
                self._dist[nb] = nd
                self.visited[nb] = cell
                heapq.heappush(self._heap, (nd, nb))
                self.frontier.add(nb)
        return False


# ─── Rendering ───────────────────────────────────────────────────────────────

def render_maze(
    maze_grid: list[list[bool]],
    solvers: list[Solver],
    running: bool,
) -> Text:
    """
    Build the display canvas as a Rich Text.
    Display coords: (dx, dy) where dx in [0, DISP_W), dy in [0, DISP_H).
    Logical cell (cx, cy) → display centre (2cx+1, 2cy+1).
    """
    # Build a flat char+style grid: list of rows, each row a list of (char, style)
    canvas: list[list[tuple[str, str]]] = [
        [("█", "grey30")] * DISP_W for _ in range(DISP_H)
    ]

    # Carve open passages from the maze boolean grid
    for dy in range(DISP_H):
        for dx in range(DISP_W):
            if maze_grid[dy][dx]:
                canvas[dy][dx] = (" ", "")

    # Entry / exit markers (open gaps already set by generate_maze)
    # S at logical (0,0) display (1,1), E at logical (MAZE_W-1, MAZE_H-1)
    canvas[1][1] = ("S", "bold bright_green")
    canvas[2 * (MAZE_H - 1) + 1][2 * (MAZE_W - 1) + 1] = ("E", "bold bright_red")

    if running or any(s.done for s in solvers):
        # Layer order: path on top, then frontier, then visited
        # Paint visited first (background layer), then frontier, then finished paths

        # visited cells (dimmer dot)
        for solver in solvers:
            for (cx, cy) in solver.visited:
                if (cx, cy) == (0, 0):
                    continue
                dx, dy = 2 * cx + 1, 2 * cy + 1
                canvas[dy][dx] = ("·", "dim " + solver.color)

        # frontier cells (bold block)
        for solver in solvers:
            if not solver.done:
                for (cx, cy) in solver.frontier:
                    dx, dy = 2 * cx + 1, 2 * cy + 1
                    canvas[dy][dx] = ("▓", solver.color)

        # finished paths (light block, on top of everything)
        for solver in solvers:
            if solver.done:
                for (cx, cy) in solver.path:
                    dx, dy = 2 * cx + 1, 2 * cy + 1
                    canvas[dy][dx] = ("░", "bold " + solver.color)

    # Restore S and E on top
    canvas[1][1] = ("S", "bold bright_green")
    canvas[2 * (MAZE_H - 1) + 1][2 * (MAZE_W - 1) + 1] = ("E", "bold bright_red")

    text = Text(no_wrap=True)
    for row in canvas:
        for ch, style in row:
            if style:
                text.append(ch, style=style)
            else:
                text.append(ch)
        text.append("\n")
    return text


# ─── App ─────────────────────────────────────────────────────────────────────

class MazeApp(App):
    CSS = """
    Screen {
        background: #080808;
    }
    #sidebar {
        width: 26;
        padding: 1 2;
        border-right: solid #222222;
        background: #0d0d0d;
    }
    .section-label {
        color: #888888;
        margin-top: 1;
        height: 1;
        text-style: bold;
    }
    .title-label {
        color: bright_white;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }
    .btn {
        margin-top: 1;
        width: 100%;
    }
    .speed-btn {
        width: 1fr;
        margin-top: 1;
    }
    #speed-row {
        height: 3;
        margin-top: 0;
    }
    #canvas {
        padding: 0 1;
    }
    #stats {
        height: auto;
        padding: 0 2;
        border-top: solid #222222;
        color: #888888;
    }
    #legend {
        margin-top: 1;
        color: #888888;
    }
    #winner {
        height: 1;
        margin-top: 1;
        color: bright_white;
        text-style: bold;
    }
    """
    TITLE = "MAZE  --  4-Algorithm Solver Race"
    BINDINGS = [
        ("space", "toggle_pause", "Pause/Resume"),
        ("n", "new_maze", "New Maze"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._maze_grid: list[list[bool]] = generate_maze(MAZE_W, MAZE_H)
        self._solvers: list[Solver] = []
        self._timer = None
        self._running = False
        self._paused = False
        self._tick_count = 0
        self._steps_per_tick = STEPS_MED
        self._winner: str | None = None
        self._solved = False

    def _make_solvers(self) -> list[Solver]:
        start = (0, 0)
        end = (MAZE_W - 1, MAZE_H - 1)
        return [
            BFSSolver(self._maze_grid, start, end),
            DFSSolver(self._maze_grid, start, end),
            AStarSolver(self._maze_grid, start, end),
            DijkstraSolver(self._maze_grid, start, end),
        ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("⬡ MAZE", classes="title-label")
                yield Button("⟳  New Maze", id="btn_new", variant="default", classes="btn")
                yield Button("▶  Solve", id="btn_solve", variant="success", classes="btn")
                yield Button("⏸  Pause", id="btn_pause", variant="default", classes="btn")
                yield Label("Speed", classes="section-label")
                with Horizontal(id="speed-row"):
                    yield Button("1×", id="btn_slow", classes="speed-btn")
                    yield Button("5×", id="btn_med",  classes="speed-btn")
                    yield Button("20×", id="btn_fast", classes="speed-btn")
                yield Label("Solvers", classes="section-label")
                yield Static(self._legend_text(), id="legend")
                yield Label("", id="winner")
                yield Label("Stats", classes="section-label")
                yield Static("—", id="stats")
            with Vertical():
                yield Static(
                    render_maze(self._maze_grid, self._solvers, False),
                    id="canvas",
                )
        yield Footer()

    def _legend_text(self) -> Text:
        t = Text(no_wrap=True)
        for name, (color, desc) in SOLVER_STYLES.items():
            t.append("▓ ", style=color)
            t.append(f"{desc}\n", style="dim white")
        return t

    def _stats_text(self) -> Text:
        t = Text(no_wrap=True)
        t.append(f"Ticks: {self._tick_count}\n", style="dim white")
        for solver in self._solvers:
            color = solver.color
            status = "done" if solver.done else "running"
            path_info = f"  path={len(solver.path)}" if solver.done else ""
            t.append(f"{solver.name}: ", style=color)
            t.append(f"{solver.steps} steps{path_info}\n", style="dim white")
        return t

    def on_mount(self) -> None:
        self._refresh_canvas()

    def _refresh_canvas(self) -> None:
        self.query_one("#canvas", Static).update(
            render_maze(self._maze_grid, self._solvers, self._running or self._solved)
        )

    def _start_solving(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None
        self._solvers = self._make_solvers()
        self._tick_count = 0
        self._winner = None
        self._solved = False
        self._running = True
        self._paused = False
        self._timer = self.set_interval(1 / 20, self._tick)
        self.query_one("#btn_pause", Button).label = "⏸  Pause"
        self.query_one("#winner", Label).update("")

    @on(Button.Pressed, "#btn_new")
    def on_btn_new(self) -> None:
        self.action_new_maze()

    @on(Button.Pressed, "#btn_solve")
    def on_btn_solve(self) -> None:
        self._start_solving()

    @on(Button.Pressed, "#btn_pause")
    def on_btn_pause(self) -> None:
        self.action_toggle_pause()

    @on(Button.Pressed, "#btn_slow")
    def on_btn_slow(self) -> None:
        self._steps_per_tick = STEPS_SLOW

    @on(Button.Pressed, "#btn_med")
    def on_btn_med(self) -> None:
        self._steps_per_tick = STEPS_MED

    @on(Button.Pressed, "#btn_fast")
    def on_btn_fast(self) -> None:
        self._steps_per_tick = STEPS_FAST

    def action_new_maze(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None
        self._running = False
        self._paused = False
        self._solved = False
        self._winner = None
        self._tick_count = 0
        self._solvers = []
        self._maze_grid = generate_maze(MAZE_W, MAZE_H)
        self.query_one("#btn_pause", Button).label = "⏸  Pause"
        self.query_one("#winner", Label).update("")
        self.query_one("#stats", Static).update("—")
        self._refresh_canvas()

    def action_toggle_pause(self) -> None:
        if self._timer is None:
            return
        if self._running and not self._paused:
            self._timer.pause()
            self._paused = True
            self._running = False
            self.query_one("#btn_pause", Button).label = "▶  Resume"
        else:
            self._timer.resume()
            self._paused = False
            self._running = True
            self.query_one("#btn_pause", Button).label = "⏸  Pause"

    def _tick(self) -> None:
        if not self._running:
            return

        all_done = all(s.done for s in self._solvers)
        if all_done and self._solvers:
            self._running = False
            self._solved = True
            if self._timer:
                self._timer.stop()
                self._timer = None
            self._refresh_canvas()
            self.query_one("#stats", Static).update(self._stats_text())
            return

        self._tick_count += 1

        for _ in range(self._steps_per_tick):
            for solver in self._solvers:
                if not solver.done:
                    solver.step()
                    # Announce first finisher
                    if solver.done and self._winner is None:
                        self._winner = solver.name
                        self.query_one("#winner", Label).update(
                            f"🏆 {solver.name} wins! ({len(solver.path)-1} steps)"
                        )

        self._refresh_canvas()
        self.query_one("#stats", Static).update(self._stats_text())

        # Check again after stepping
        if all(s.done for s in self._solvers):
            self._running = False
            self._solved = True
            if self._timer:
                self._timer.stop()
                self._timer = None


if __name__ == "__main__":
    MazeApp().run()
