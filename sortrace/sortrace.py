#!/usr/bin/env python3
"""
sortrace -- Sorting algorithm race visualiser.
"May the fastest O(n log n) win. Or bubble sort. Actually, not bubble sort."
"""
from __future__ import annotations

import math
import random
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static
from textual import on

N = 32


# ---------------------------------------------------------------------------
# Sorting algorithm state machines
# ---------------------------------------------------------------------------

class BubbleSorter:
    name = "BUBBLE SORT"

    def __init__(self, arr: list[int]) -> None:
        self.arr = arr[:]
        self.highlight: set[int] = set()
        self.sorted_indices: set[int] = set()
        self.comps = 0
        self.swaps = 0
        self.done = False
        self._i = 0
        self._j = 0
        self._n = len(arr)

    def step(self) -> None:
        if self.done:
            return
        n = self._n
        # Find next valid (i, j) position
        while self._i < n - 1:
            j = self._j
            i = self._i
            if j < n - 1 - i:
                self.comps += 1
                self.highlight = {j, j + 1}
                if self.arr[j] > self.arr[j + 1]:
                    self.arr[j], self.arr[j + 1] = self.arr[j + 1], self.arr[j]
                    self.swaps += 1
                self._j += 1
                return
            else:
                # End of inner pass — mark rightmost unsorted as sorted
                self.sorted_indices.add(n - 1 - i)
                self._i += 1
                self._j = 0
        # All done
        for k in range(n):
            self.sorted_indices.add(k)
        self.highlight = set()
        self.done = True


class InsertionSorter:
    name = "INSERTION SORT"

    def __init__(self, arr: list[int]) -> None:
        self.arr = arr[:]
        self.highlight: set[int] = set()
        self.sorted_indices: set[int] = set()
        self.comps = 0
        self.swaps = 0
        self.done = False
        self._i = 1
        self._j = 1  # current shifting position within pass i

    def step(self) -> None:
        if self.done:
            return
        n = len(self.arr)
        # We track _i as the outer index, _j as the current insertion point
        while self._i < n:
            j = self._j
            if j > 0 and self.arr[j - 1] > self.arr[j]:
                self.comps += 1
                self.highlight = {j - 1, j}
                self.arr[j - 1], self.arr[j] = self.arr[j], self.arr[j - 1]
                self.swaps += 1
                self._j -= 1
                return
            else:
                if j > 0:
                    self.comps += 1
                # Done inserting arr[_i], mark sorted up to _i
                for k in range(self._i + 1):
                    self.sorted_indices.add(k)
                self.highlight = set()
                self._i += 1
                self._j = self._i
                return
        for k in range(n):
            self.sorted_indices.add(k)
        self.highlight = set()
        self.done = True


class SelectionSorter:
    name = "SELECTION SORT"

    def __init__(self, arr: list[int]) -> None:
        self.arr = arr[:]
        self.highlight: set[int] = set()
        self.sorted_indices: set[int] = set()
        self.comps = 0
        self.swaps = 0
        self.done = False
        self._i = 0       # outer: position being filled
        self._j = 1       # inner: current scan position
        self._min_idx = 0
        n = len(arr)
        self._n = n

    def step(self) -> None:
        if self.done:
            return
        n = self._n
        i = self._i
        if i >= n - 1:
            self.sorted_indices.add(n - 1)
            self.highlight = set()
            self.done = True
            return

        j = self._j
        if j < n:
            self.comps += 1
            self.highlight = {self._min_idx, j}
            if self.arr[j] < self.arr[self._min_idx]:
                self._min_idx = j
            self._j += 1
        else:
            # End of scan — swap min into position i
            if self._min_idx != i:
                self.arr[i], self.arr[self._min_idx] = self.arr[self._min_idx], self.arr[i]
                self.swaps += 1
            self.sorted_indices.add(i)
            self.highlight = set()
            self._i += 1
            self._j = self._i + 1
            self._min_idx = self._i


class MergeSorter:
    name = "MERGE SORT"

    def __init__(self, arr: list[int]) -> None:
        self.arr = arr[:]
        self.highlight: set[int] = set()
        self.sorted_indices: set[int] = set()
        self.comps = 0
        self.swaps = 0
        self.done = False
        # Pre-compute all steps
        self._steps: list[tuple[list[int], set[int], set[int]]] = []
        self._step_idx = 0
        work = arr[:]
        self._precompute(work, 0, len(work) - 1)
        # Final state — everything sorted
        self._steps.append((sorted(arr), set(), set(range(len(arr)))))

    def _precompute(self, arr: list[int], lo: int, hi: int) -> None:
        if lo >= hi:
            return
        mid = (lo + hi) // 2
        self._precompute(arr, lo, mid)
        self._precompute(arr, mid + 1, hi)
        # Merge arr[lo..mid] and arr[mid+1..hi]
        left = arr[lo:mid + 1]
        right = arr[mid + 1:hi + 1]
        i = j = 0
        k = lo
        sorted_so_far: set[int] = set()
        while i < len(left) and j < len(right):
            hl = {lo + i, mid + 1 + j}
            if left[i] <= right[j]:
                arr[k] = left[i]
                i += 1
            else:
                arr[k] = right[j]
                j += 1
            sorted_so_far.add(k)
            k += 1
            self._steps.append((arr[:], hl, set(sorted_so_far)))
        while i < len(left):
            arr[k] = left[i]
            sorted_so_far.add(k)
            k += 1
            i += 1
            self._steps.append((arr[:], set(), set(sorted_so_far)))
        while j < len(right):
            arr[k] = right[j]
            sorted_so_far.add(k)
            k += 1
            j += 1
            self._steps.append((arr[:], set(), set(sorted_so_far)))

    def step(self) -> None:
        if self.done:
            return
        if self._step_idx >= len(self._steps):
            self.done = True
            self.highlight = set()
            return
        snapshot, hl, si = self._steps[self._step_idx]
        self.arr = snapshot
        self.highlight = hl
        self.sorted_indices = si
        self.comps += 1
        self._step_idx += 1
        if self._step_idx >= len(self._steps):
            self.done = True
            self.highlight = set()


class QuickSorter:
    name = "QUICK SORT"

    def __init__(self, arr: list[int]) -> None:
        self.arr = arr[:]
        self.highlight: set[int] = set()
        self.sorted_indices: set[int] = set()
        self.comps = 0
        self.swaps = 0
        self.done = False
        self._n = len(arr)
        # Iterative quicksort stack: (lo, hi)
        self._stack: list[tuple[int, int]] = [(0, self._n - 1)]
        # Within a partition: state
        self._in_partition = False
        self._lo = 0
        self._hi = 0
        self._pivot_val = 0
        self._pivot_idx = 0  # Lomuto: pivot at hi
        self._i = -1         # i tracks boundary of "less than pivot"
        self._j = 0          # j scans forward

    def _start_partition(self, lo: int, hi: int) -> None:
        self._lo = lo
        self._hi = hi
        self._pivot_val = self.arr[hi]
        self._pivot_idx = hi
        self._i = lo - 1
        self._j = lo
        self._in_partition = True

    def step(self) -> None:
        if self.done:
            return

        if not self._in_partition:
            if not self._stack:
                # All done
                for k in range(self._n):
                    self.sorted_indices.add(k)
                self.highlight = set()
                self.done = True
                return
            lo, hi = self._stack.pop()
            if lo >= hi:
                if lo == hi:
                    self.sorted_indices.add(lo)
                return
            self._start_partition(lo, hi)
            return

        # One comparison step in current partition
        lo, hi = self._lo, self._hi
        j = self._j
        if j < hi:
            self.comps += 1
            self.highlight = {j, hi}
            if self.arr[j] <= self._pivot_val:
                self._i += 1
                if self._i != j:
                    self.arr[self._i], self.arr[j] = self.arr[j], self.arr[self._i]
                    self.swaps += 1
                    self.highlight = {self._i, j}
            self._j += 1
        else:
            # Place pivot
            pivot_pos = self._i + 1
            if pivot_pos != hi:
                self.arr[pivot_pos], self.arr[hi] = self.arr[hi], self.arr[pivot_pos]
                self.swaps += 1
            self.sorted_indices.add(pivot_pos)
            self.highlight = set()
            self._in_partition = False
            # Push sub-ranges
            if pivot_pos - 1 > lo:
                self._stack.append((lo, pivot_pos - 1))
            elif pivot_pos - 1 == lo:
                self.sorted_indices.add(lo)
            if pivot_pos + 1 < hi:
                self._stack.append((pivot_pos + 1, hi))
            elif pivot_pos + 1 == hi:
                self.sorted_indices.add(hi)


class HeapSorter:
    name = "HEAP SORT"

    def __init__(self, arr: list[int]) -> None:
        self.arr = arr[:]
        self.highlight: set[int] = set()
        self.sorted_indices: set[int] = set()
        self.comps = 0
        self.swaps = 0
        self.done = False
        self._n = len(arr)
        # Phase 0: build heap (heapify from n//2-1 down to 0)
        # Phase 1: extract
        self._phase = 0
        self._build_i = self._n // 2 - 1
        self._extract_end = self._n - 1
        # Sift-down state
        self._sifting = False
        self._sift_root = 0
        self._sift_end = 0

    def _start_sift(self, root: int, end: int) -> None:
        self._sifting = True
        self._sift_root = root
        self._sift_end = end

    def step(self) -> None:
        if self.done:
            return

        if self._sifting:
            root = self._sift_root
            end = self._sift_end
            largest = root
            left = 2 * root + 1
            right = 2 * root + 2
            self.comps += 1
            if left <= end:
                if self.arr[left] > self.arr[largest]:
                    largest = left
                if right <= end and self.arr[right] > self.arr[largest]:
                    largest = right
            self.highlight = {root, largest}
            if largest != root:
                self.arr[root], self.arr[largest] = self.arr[largest], self.arr[root]
                self.swaps += 1
                self._sift_root = largest
            else:
                self._sifting = False
                self.highlight = set()
            return

        if self._phase == 0:
            if self._build_i >= 0:
                self._start_sift(self._build_i, self._n - 1)
                self._build_i -= 1
            else:
                self._phase = 1
        elif self._phase == 1:
            end = self._extract_end
            if end > 0:
                self.arr[0], self.arr[end] = self.arr[end], self.arr[0]
                self.swaps += 1
                self.sorted_indices.add(end)
                self._extract_end -= 1
                self._start_sift(0, self._extract_end)
            else:
                self.sorted_indices.add(0)
                self.highlight = set()
                self.done = True


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

BAR_FULL = "██"
BAR_EMPTY = "  "


def render_all(sorters: list, winner: str | None, ticks: int) -> Text:
    text = Text(no_wrap=True)

    for s in sorters:
        n = len(s.arr)
        # Row 0: name + stats
        done_marker = "  ✓ DONE" if s.done else ""
        header = f" {s.name:<16}  comps: {s.comps:<6} swaps: {s.swaps:<6}{done_marker}"
        if s.done:
            text.append(header, style="bold bright_green")
        else:
            text.append(header, style="bold bright_white")
        text.append("\n")

        # Rows 1-4: bar chart
        for row in range(1, 5):
            text.append(" ")  # left pad
            for j in range(n):
                v = s.arr[j]
                bar_height = max(1, math.ceil(v * 4 / N))
                filled = row >= (5 - bar_height)
                if filled:
                    if j in s.highlight:
                        style = "bold bright_yellow"
                    elif j in s.sorted_indices:
                        style = "bright_green"
                    else:
                        style = "bright_blue"
                    text.append(BAR_FULL, style=style)
                else:
                    text.append(BAR_EMPTY)
            text.append("\n")

        # Row 5: blank separator
        text.append("\n")

    return text


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

SORTER_CLASSES = [
    BubbleSorter,
    InsertionSorter,
    SelectionSorter,
    MergeSorter,
    QuickSorter,
    HeapSorter,
]


class SortRaceApp(App):
    CSS = """
    Screen { background: #0d0d0d; }
    #sidebar {
        width: 28;
        padding: 1 2;
        border-right: solid $primary-darken-2;
    }
    #canvas {
        padding: 1 2;
    }
    #stats {
        height: 3;
        padding: 0 2;
        border-top: solid $primary-darken-2;
        color: $text-muted;
        content-align: left middle;
    }
    .btn { margin-top: 1; width: 100%; }
    .speed-btn { margin-top: 0; width: 100%; }
    #speed-label { margin-top: 2; color: $text-muted; height: 1; }
    """
    TITLE = "SORTRACE  --  Sorting Algorithm Race"
    BINDINGS = [
        ("space", "toggle", "Start/Stop"),
        ("r", "reset", "Reset"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._base_arr: list[int] = list(range(1, N + 1))
        random.shuffle(self._base_arr)
        self._sorters: list = [cls(self._base_arr) for cls in SORTER_CLASSES]
        self._running = False
        self._timer = None
        self._ticks = 0
        self._steps_per_tick = 1
        self._winner: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Button("▶ Start", id="btn_start", variant="success", classes="btn")
                yield Button("⟳ Reset", id="btn_reset", variant="default", classes="btn")
                yield Static("Speed:", id="speed-label")
                yield Button("1x", id="btn_1x", variant="primary", classes="speed-btn")
                yield Button("5x", id="btn_5x", variant="default", classes="speed-btn")
                yield Button("20x", id="btn_20x", variant="default", classes="speed-btn")
            with Vertical():
                yield Static(
                    render_all(self._sorters, self._winner, self._ticks),
                    id="canvas",
                )
                yield Static(self._stats_text(), id="stats")
        yield Footer()

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / 30, self._tick)
        self._timer.pause()

    def _stats_text(self) -> str:
        if self._winner:
            return f"Winner: {self._winner}   Ticks: {self._ticks}"
        if self._running:
            return f"Racing...   Ticks: {self._ticks}"
        if self._ticks > 0:
            return f"Paused   Ticks: {self._ticks}"
        return "Press ▶ Start or SPACE to begin the race."

    def _tick(self) -> None:
        if not self._running:
            return
        self._ticks += 1
        for s in self._sorters:
            if not s.done:
                for _ in range(self._steps_per_tick):
                    s.step()
                    if s.done:
                        break

        # Check for winner
        if self._winner is None:
            for s in self._sorters:
                if s.done:
                    self._winner = s.name
                    break

        # Stop if all done
        all_done = all(s.done for s in self._sorters)

        self.query_one("#canvas", Static).update(
            render_all(self._sorters, self._winner, self._ticks)
        )
        self.query_one("#stats", Static).update(self._stats_text())

        if all_done:
            self._running = False
            self._timer.pause()
            self.query_one("#btn_start", Button).label = "▶ Start"

    @on(Button.Pressed, "#btn_start")
    def on_start(self) -> None:
        self.action_toggle()

    @on(Button.Pressed, "#btn_reset")
    def on_reset(self) -> None:
        self.action_reset()

    @on(Button.Pressed, "#btn_1x")
    def on_1x(self) -> None:
        self._steps_per_tick = 1
        self._update_speed_buttons(1)

    @on(Button.Pressed, "#btn_5x")
    def on_5x(self) -> None:
        self._steps_per_tick = 5
        self._update_speed_buttons(5)

    @on(Button.Pressed, "#btn_20x")
    def on_20x(self) -> None:
        self._steps_per_tick = 20
        self._update_speed_buttons(20)

    def _update_speed_buttons(self, active: int) -> None:
        mapping = {1: "#btn_1x", 5: "#btn_5x", 20: "#btn_20x"}
        for speed, bid in mapping.items():
            self.query_one(bid, Button).variant = "primary" if speed == active else "default"

    def action_toggle(self) -> None:
        if self._timer is None:
            return
        if self._running:
            self._running = False
            self._timer.pause()
            self.query_one("#btn_start", Button).label = "▶ Start"
        else:
            self._running = True
            self._timer.resume()
            self.query_one("#btn_start", Button).label = "⏸ Pause"

    def action_reset(self) -> None:
        if self._timer:
            self._timer.pause()
        self._running = False
        self._ticks = 0
        self._winner = None
        random.shuffle(self._base_arr)
        self._sorters = [cls(self._base_arr) for cls in SORTER_CLASSES]
        self.query_one("#btn_start", Button).label = "▶ Start"
        self.query_one("#canvas", Static).update(
            render_all(self._sorters, self._winner, self._ticks)
        )
        self.query_one("#stats", Static).update(self._stats_text())


if __name__ == "__main__":
    SortRaceApp().run()
