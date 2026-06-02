#!/usr/bin/env python3
"""
plague -- Medieval plague spread simulator (SIR model).
"Bring out your dead! What do you mean the simulation converged? I don't want to go on the cart."
"""
from __future__ import annotations
import random
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, Static
from textual import on

GRID_W = 55
GRID_H = 20
DT = 0.08


class Cell:
    def __init__(self) -> None:
        self.s = 1.0
        self.i = 0.0
        self.r = 0.0

    def copy(self) -> "Cell":
        c = Cell.__new__(Cell)
        c.s = self.s
        c.i = self.i
        c.r = self.r
        return c

    def seed(self, amount: float = 0.5) -> None:
        taken = min(amount, self.s)
        self.s -= taken
        self.i += taken


def tick_grid(grid: list[list[Cell]], beta: float, gamma: float) -> list[list[Cell]]:
    H, W = len(grid), len(grid[0])
    new = [[grid[r][c].copy() for c in range(W)] for r in range(H)]
    for r in range(H):
        for c in range(W):
            cell = grid[r][c]
            if cell.s < 0.001 and cell.i < 0.001:
                continue
            ni_sum = 0.0
            ni_count = 0
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W:
                    ni_sum += grid[nr][nc].i
                    ni_count += 1
            pressure = cell.i + 0.25 * (ni_sum / ni_count if ni_count else 0.0)
            d_new_i = min(beta * pressure * cell.s * DT, cell.s)
            d_rec = gamma * cell.i * DT
            nc_ = new[r][c]
            nc_.s = max(0.0, cell.s - d_new_i)
            nc_.i = max(0.0, cell.i + d_new_i - d_rec)
            nc_.r = min(1.0, cell.r + d_rec)
    return new


def render_grid(grid: list[list[Cell]]) -> str:
    lines = []
    for row in grid:
        parts = []
        for c in row:
            if c.i > 0.5:
                parts.append("[bold red]#[/bold red]")
            elif c.i > 0.2:
                parts.append("[red]#[/red]")
            elif c.i > 0.05:
                parts.append("[yellow].[/yellow]")
            elif c.r > 0.6:
                parts.append("[green]+[/green]")
            elif c.r > 0.15:
                parts.append("[dim green].[/dim green]")
            else:
                parts.append("[dim white].[/dim white]")
        lines.append("".join(parts))
    return "\n".join(lines)


def grid_totals(grid: list[list[Cell]]) -> tuple[float, float, float]:
    s = i = r = 0.0
    for row in grid:
        for c in row:
            s += c.s
            i += c.i
            r += c.r
    n = len(grid) * len(grid[0])
    return s / n, i / n, r / n


class PlagueApp(App):
    CSS = """
    Screen { background: $surface; }
    #sidebar {
        width: 28;
        padding: 1 2;
        border-right: solid $primary-darken-2;
    }
    .lbl { color: $text-muted; margin-top: 1; height: 1; }
    Input { margin-bottom: 0; height: 3; }
    .btn { margin-top: 1; width: 100%; }
    #canvas { padding: 1; }
    #stats {
        height: 3;
        padding: 0 2;
        border-top: solid $primary-darken-2;
        color: $text-muted;
        content-align: left middle;
    }
    #legend { margin-top: 2; color: $text-muted; }
    """
    TITLE = "PLAGUE  --  Medieval Disease Spread (SIR Model)"
    BINDINGS = [
        ("space", "toggle", "Pause/Resume"),
        ("r", "action_reset", "Reset"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.grid: list[list[Cell]] = [[Cell() for _ in range(GRID_W)] for _ in range(GRID_H)]
        self._timer = None
        self._running = False
        self._day = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Infection rate (beta)", classes="lbl")
                yield Input("0.4", id="beta")
                yield Label("Recovery rate (gamma)", classes="lbl")
                yield Input("0.1", id="gamma")
                yield Label("", id="r0")
                yield Button("UNLEASH", id="start", variant="error", classes="btn")
                yield Button("RESET", id="reset-btn", variant="default", classes="btn")
                yield Label(
                    "[red]#[/red] infected  [yellow].[/yellow] spreading\n"
                    "[green]+[/green] recovered  [dim].[/dim] susceptible",
                    id="legend",
                )
            with Vertical():
                yield Static(render_grid(self.grid), id="canvas")
                yield Static("Press UNLEASH to patient-zero a random village.", id="stats")
        yield Footer()

    def on_mount(self) -> None:
        self._update_r0()

    def _params(self) -> tuple[float, float]:
        def f(id, d):
            try:
                return max(0.001, float(self.query_one(f"#{id}", Input).value))
            except Exception:
                return d
        return f("beta", 0.4), f("gamma", 0.1)

    def _update_r0(self) -> None:
        beta, gamma = self._params()
        self.query_one("#r0", Label).update(f"R₀ = [bold]{beta / gamma:.2f}[/bold]")

    @on(Button.Pressed, "#start")
    def on_start(self) -> None:
        if not self._running:
            ry = random.randint(GRID_H // 4, 3 * GRID_H // 4)
            rx = random.randint(GRID_W // 4, 3 * GRID_W // 4)
            self.grid[ry][rx].seed(0.5)
            self._running = True
            self._timer = self.set_interval(0.05, self._tick)
            self.query_one("#start", Button).label = "PAUSE"
        else:
            self.action_toggle()

    def action_toggle(self) -> None:
        if self._timer is None:
            return
        if self._running:
            self._timer.pause()
            self._running = False
            self.query_one("#start", Button).label = "RESUME"
        else:
            self._timer.resume()
            self._running = True
            self.query_one("#start", Button).label = "PAUSE"

    @on(Button.Pressed, "#reset-btn")
    def action_reset(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None
        self._running = False
        self._day = 0
        self.grid = [[Cell() for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.query_one("#canvas", Static).update(render_grid(self.grid))
        self.query_one("#stats", Static).update("Reset. Press UNLEASH to begin again.")
        self.query_one("#start", Button).label = "UNLEASH"
        self._update_r0()

    def _tick(self) -> None:
        beta, gamma = self._params()
        self.grid = tick_grid(self.grid, beta, gamma)
        self._day += 1
        s, i, r = grid_totals(self.grid)
        self.query_one("#canvas", Static).update(render_grid(self.grid))
        self.query_one("#stats", Static).update(
            f"Day [bold]{self._day}[/bold]   "
            f"Susceptible: [white]{s * 100:.1f}%[/white]   "
            f"[red]Infected: {i * 100:.2f}%[/red]   "
            f"[green]Recovered: {r * 100:.1f}%[/green]"
        )
        self._update_r0()
        if i < 0.0005 and self._day > 10:
            if self._timer:
                self._timer.stop()
                self._timer = None
            self._running = False
            self.query_one("#start", Button).label = "UNLEASH"
            self.query_one("#stats", Static).update(
                f"[bold]Outbreak concluded. Day {self._day}.[/bold]   "
                f"Survived: [white]{s * 100:.1f}%[/white]   "
                f"[green]Recovered: {r * 100:.1f}%[/green]   "
                '[dim]"I got better."[/dim]'
            )


if __name__ == "__main__":
    PlagueApp().run()
