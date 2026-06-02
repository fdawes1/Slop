#!/usr/bin/env python3
"""
trebuchet -- Medieval siege physics simulator.
"We have the Holy Hand Grenade, but frankly the trebuchet has better range."
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, Static
from textual import on

G = 9.81
CANVAS_W = 64
CANVAS_H = 22


@dataclass
class Params:
    counterweight_kg: float = 100.0
    arm_ratio: float = 4.0
    arm_length: float = 5.0
    sling_length: float = 3.0
    projectile_kg: float = 5.0
    angle_deg: float = 45.0


def simulate(p: Params) -> tuple[list[tuple[float, float]], float, float, float, float]:
    """Returns (points, range_m, max_h_m, flight_s, v_launch_ms).

    Moment-of-inertia model:
      I = M*a^2 + m*b^2
      omega = sqrt(2*M*g*h / I)
      v_launch = omega * (b + sling)
    """
    a = p.arm_length / (1 + p.arm_ratio)
    b = p.arm_length - a
    h_drop = 2 * a
    I = p.counterweight_kg * a**2 + p.projectile_kg * b**2
    if I <= 0 or p.projectile_kg <= 0 or p.counterweight_kg <= 0:
        return [], 0, 0, 0, 0
    omega = math.sqrt(max(2 * p.counterweight_kg * G * h_drop / I, 0))
    v_launch = min(omega * (b + p.sling_length), 500.0)
    angle = math.radians(max(0.1, min(89.9, p.angle_deg)))
    vx = v_launch * math.cos(angle)
    vy = v_launch * math.sin(angle)
    launch_h = max(b, 1.0)
    dt = 0.1
    t = 0.0
    pts: list[tuple[float, float]] = [(0.0, launch_h)]
    max_h = launch_h
    flight_t = 0.0
    while t < 600:
        t += dt
        x = vx * t
        y = launch_h + vy * t - 0.5 * G * t**2
        if y <= 0:
            prev = pts[-1]
            denom = prev[1] - y
            frac = prev[1] / denom if denom else 1.0
            pts.append((prev[0] + (x - prev[0]) * frac, 0.0))
            flight_t = t - dt + dt * frac
            break
        pts.append((x, y))
        max_h = max(max_h, y)
    else:
        flight_t = t
    return pts, pts[-1][0], max_h, flight_t, v_launch


def draw(pts: list[tuple[float, float]], rng: float, max_h: float) -> str:
    W, H = CANVAS_W, CANVAS_H
    g = [[" "] * W for _ in range(H)]
    for c in range(W):
        g[H - 1][c] = "-"
    g[H - 1][2] = "A"
    g[H - 2][2] = "|"
    g[H - 3][2] = "T"
    g[H - 4][3] = "/"
    g[H - 4][1] = "\\"
    if not pts or rng <= 0:
        return "\n".join("".join(r) for r in g)
    xs = (W - 8) / rng
    ys = (H - 3) / max(max_h * 1.1, 1.0)
    arc = ".:*o"
    n = len(pts)
    for i, (x, y) in enumerate(pts[:-1]):
        cx = int(4 + x * xs)
        cy = int(H - 2 - y * ys)
        if 0 <= cx < W and 0 <= cy < H - 1:
            g[cy][cx] = arc[min(int(i / n * len(arc)), len(arc) - 1)]
    ix = int(4 + pts[-1][0] * xs)
    if 0 <= ix < W:
        g[H - 1][ix] = "X"
    return "\n".join("".join(r) for r in g)


class TrebuchetApp(App):
    CSS = """
    Screen { background: $surface; }
    #sidebar {
        width: 30;
        padding: 1 2;
        border-right: solid $primary-darken-2;
    }
    .lbl { color: $text-muted; margin-top: 1; height: 1; }
    Input { margin-bottom: 0; height: 3; }
    #fire { margin-top: 2; width: 100%; }
    #canvas { padding: 1; }
    #stats {
        height: 3;
        padding: 0 2;
        border-top: solid $primary-darken-2;
        color: $text-muted;
        content-align: left middle;
    }
    """
    TITLE = "TREBUCHET  --  Medieval Siege Physics"
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Counterweight (kg)", classes="lbl")
                yield Input("100", id="cw")
                yield Label("Arm ratio  long:short", classes="lbl")
                yield Input("4", id="ar")
                yield Label("Arm length (m)", classes="lbl")
                yield Input("5", id="al")
                yield Label("Sling length (m)", classes="lbl")
                yield Input("3", id="sl")
                yield Label("Projectile (kg)", classes="lbl")
                yield Input("5", id="pm")
                yield Label("Launch angle (deg)", classes="lbl")
                yield Input("45", id="la")
                yield Button("FIRE", id="fire", variant="error")
            with Vertical():
                yield Static(draw([], 0, 0), id="canvas")
                yield Static("Awaiting launch orders.", id="stats")
        yield Footer()

    def _params(self) -> Params:
        def f(id, d):
            try:
                return float(self.query_one(f"#{id}", Input).value)
            except Exception:
                return d
        return Params(f("cw", 100), f("ar", 4), f("al", 5), f("sl", 3), f("pm", 5), f("la", 45))

    @on(Button.Pressed, "#fire")
    def action_fire(self) -> None:
        p = self._params()
        pts, rng, max_h, t, v = simulate(p)
        self.query_one("#canvas", Static).update(draw(pts, rng, max_h))
        if rng > 0:
            self.query_one("#stats", Static).update(
                f"Range: [bold]{rng:.0f} m[/bold]   "
                f"Max height: [bold]{max_h:.0f} m[/bold]   "
                f"Flight: [bold]{t:.1f} s[/bold]   "
                f"Velocity: [bold]{v:.0f} m/s[/bold]"
            )
        else:
            self.query_one("#stats", Static).update("Invalid parameters. Try again.")


if __name__ == "__main__":
    TrebuchetApp().run()
