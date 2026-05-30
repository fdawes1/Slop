#!/usr/bin/env python3
"""netstr — Network Strength Tester"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, RichLog, Static

from core.arp_spoof import ArpSpoof
from core.deauth import DeauthAttack
from core.monitor import PacketMonitor
from core.scanner import AP, Host, scan_aps, scan_hosts


def _default_gateway() -> str:
    try:
        out = subprocess.run(
            ["ip", "route", "show", "default"], capture_output=True, text=True
        ).stdout
        for line in out.splitlines():
            parts = line.split()
            if "via" in parts:
                return parts[parts.index("via") + 1]
    except Exception:
        pass
    return "192.168.1.1"


def _subnet_for(iface: str) -> str:
    try:
        out = subprocess.run(
            ["ip", "-4", "addr", "show", iface], capture_output=True, text=True
        ).stdout
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                ip, prefix = line.split()[1].split("/")
                parts = ip.split(".")
                parts[-1] = "0"
                return ".".join(parts) + "/" + prefix
    except Exception:
        pass
    return "192.168.1.0/24"


LEVEL_COLOR = {
    "attack":  "bold red",
    "warning": "yellow",
    "event":   "cyan",
    "info":    "dim white",
}


class NetstrApp(App[None]):
    CSS = """
    Screen { background: $surface; }

    #main { height: 1fr; }

    #left {
        width: 46;
        border: solid $primary;
        padding: 0 1;
    }

    #right {
        width: 1fr;
        border: solid $accent;
        padding: 0 1;
    }

    .lbl { color: $text-muted; margin-top: 1; }

    #ap_table  { height: 8; margin-bottom: 1; }
    #host_table { height: 7; margin-bottom: 1; }

    #btn_scan  { width: 100%; margin: 1 0; }
    #btn_stop  { width: 100%; margin-top: 1; }
    #btn_deauth { width: 1fr; }
    #btn_arp    { width: 1fr; }

    .attack-row { height: 3; margin-top: 1; }

    #status { margin-top: 1; }
    #event_log { height: 1fr; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "scan", "Scan"),
        Binding("escape", "stop_attack", "Stop"),
    ]

    _selected_ap: Optional[AP] = None
    _selected_host: Optional[Host] = None
    _aps: list[AP] = []
    _hosts: list[Host] = []
    _deauth = DeauthAttack()
    _arp = ArpSpoof()
    _monitor: Optional[PacketMonitor] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Label("Interface", classes="lbl")
                yield Input("wlan0", id="iface", placeholder="wlan0")
                yield Button("Scan Network", id="btn_scan", variant="primary")

                yield Label("Access Points  [dim](click to select)[/]", classes="lbl", markup=True)
                ap = DataTable(id="ap_table", cursor_type="row", zebra_stripes=True)
                ap.add_columns("SSID", "BSSID", "Ch", "dBm")
                yield ap

                yield Label("Hosts  [dim](click to select target)[/]", classes="lbl", markup=True)
                ht = DataTable(id="host_table", cursor_type="row", zebra_stripes=True)
                ht.add_columns("IP", "MAC")
                yield ht

                yield Label("Gateway IP", classes="lbl")
                yield Input(_default_gateway(), id="gateway", placeholder="192.168.1.1")

                yield Label("Attack", classes="lbl")
                with Horizontal(classes="attack-row"):
                    yield Button("Deauth", id="btn_deauth", variant="error")
                    yield Button("ARP Spoof", id="btn_arp", variant="warning")
                yield Button("Stop", id="btn_stop")

                yield Static("[green]● Idle[/]", id="status", markup=True)

            with Vertical(id="right"):
                yield Label("Live Events", classes="lbl")
                yield RichLog(id="event_log", markup=True, wrap=True, highlight=False)

        yield Footer()

    def on_mount(self) -> None:
        self._restart_monitor()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _iface(self) -> str:
        return self.query_one("#iface", Input).value.strip() or "wlan0"

    def _gateway(self) -> str:
        return self.query_one("#gateway", Input).value.strip() or "192.168.1.1"

    def _log(self, level: str, msg: str) -> None:
        color = LEVEL_COLOR.get(level, "white")
        ts = datetime.now().strftime("%H:%M:%S")
        self.query_one("#event_log", RichLog).write(
            f"[dim]{ts}[/]  [{color}]{msg}[/]"
        )

    def _status(self, msg: str, ok: bool = True) -> None:
        color = "green" if ok else "red"
        self.query_one("#status", Static).update(f"[{color}]● {msg}[/]")

    def _restart_monitor(self) -> None:
        if self._monitor:
            self._monitor.stop()
        self._monitor = PacketMonitor(
            lambda lvl, msg: self.call_from_thread(self._log, lvl, msg)
        )
        self._monitor.start(self._iface())

    # ── scanning ─────────────────────────────────────────────────────────────

    @work(thread=True)
    def _scan(self) -> None:
        iface = self._iface()
        self.call_from_thread(self._status, "Scanning APs…")
        self._aps = scan_aps(iface)
        self.call_from_thread(self._populate_aps)

        self.call_from_thread(self._status, "Scanning hosts…")
        self._hosts = scan_hosts(_subnet_for(iface), iface)
        self.call_from_thread(self._populate_hosts)

        self.call_from_thread(
            self._status,
            f"Found {len(self._aps)} APs, {len(self._hosts)} hosts",
        )

    def _populate_aps(self) -> None:
        t = self.query_one("#ap_table", DataTable)
        t.clear()
        for ap in self._aps:
            t.add_row(ap.ssid[:18], ap.bssid, str(ap.channel), f"{ap.signal:.0f}")

    def _populate_hosts(self) -> None:
        t = self.query_one("#host_table", DataTable)
        t.clear()
        for h in self._hosts:
            t.add_row(h.ip, h.mac)

    # ── events ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn_scan":
                self._scan()
                self._restart_monitor()
            case "btn_deauth":
                self._launch_deauth()
            case "btn_arp":
                self._launch_arp()
            case "btn_stop":
                self.action_stop_attack()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "ap_table" and event.cursor_row < len(self._aps):
            self._selected_ap = self._aps[event.cursor_row]
            ap = self._selected_ap
            self._log("info", f"Selected AP: {ap.ssid}  ({ap.bssid})")
        elif event.data_table.id == "host_table" and event.cursor_row < len(self._hosts):
            self._selected_host = self._hosts[event.cursor_row]
            h = self._selected_host
            self._log("info", f"Selected host: {h.ip}  ({h.mac})")

    # ── attacks ───────────────────────────────────────────────────────────────

    def _launch_deauth(self) -> None:
        if not self._selected_ap:
            self._log("warning", "Select an AP from the table first (requires monitor-mode interface)")
            return
        if self._deauth.running:
            self._deauth.stop()
        ap = self._selected_ap
        self._deauth.start(self._iface(), ap.bssid)
        self._status(f"Deauth → {ap.ssid}", ok=False)
        self._log("attack", f"Deauth running — targeting {ap.ssid} ({ap.bssid}), all clients")

    def _launch_arp(self) -> None:
        if not self._selected_host:
            self._log("warning", "Select a target host from the table first")
            return
        if self._arp.running:
            self._arp.stop()
        host = self._selected_host
        gw = self._gateway()
        try:
            self._arp.start(self._iface(), host.ip, gw)
            self._status(f"ARP Spoof → {host.ip}", ok=False)
            self._log("attack", f"ARP spoof running — poisoning {host.ip} ↔ gateway {gw}")
        except ValueError as exc:
            self._log("warning", f"ARP spoof failed: {exc}")
            self._status("ARP spoof failed", ok=False)

    # ── actions ───────────────────────────────────────────────────────────────

    def action_scan(self) -> None:
        self._scan()

    def action_stop_attack(self) -> None:
        stopped = []
        if self._deauth.running:
            self._deauth.stop()
            stopped.append("deauth")
        if self._arp.running:
            self._arp.stop()
            stopped.append("ARP spoof (ARP tables restored)")
        if stopped:
            self._log("info", f"Stopped: {', '.join(stopped)}")
        self._status("Idle")

    def on_unmount(self) -> None:
        if self._deauth.running:
            self._deauth.stop()
        if self._arp.running:
            self._arp.stop()
        if self._monitor:
            self._monitor.stop()


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("netstr requires root — run with: sudo python3 netstr.py")
        sys.exit(1)
    NetstrApp().run()
