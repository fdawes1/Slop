import re
import subprocess
import threading
from shlex import quote
from typing import Optional, Tuple


class TmuxConn:
    def __init__(self):
        self._mode = "local"
        self._client = None
        self._lock = threading.Lock()
        self._conn_params: dict = {}

        self.connected = False
        self.host: Optional[str] = None

    # ── Connection management ─────────────────────────────────────────────────

    def connect_local(self) -> dict:
        with self._lock:
            if self._client:
                self._client.close()
                self._client = None
            self._mode = "local"
            self.host = "localhost"
            self.connected = True
        return {"success": True}

    def connect_ssh(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        port: int = 22,
    ) -> dict:
        import paramiko

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            kwargs: dict = dict(hostname=host, port=port, username=username, timeout=15)
            if key_file:
                kwargs["key_filename"] = key_file
            elif password:
                kwargs["password"] = password
            client.connect(**kwargs)

            with self._lock:
                if self._client:
                    self._client.close()
                self._client = client
                self._mode = "ssh"
                self.host = host
                self.connected = True
                self._conn_params = dict(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    key_file=key_file,
                )
            return {"success": True}
        except Exception as exc:
            self.connected = False
            return {"success": False, "error": str(exc)}

    def disconnect(self) -> None:
        with self._lock:
            if self._client:
                self._client.close()
                self._client = None
            self._mode = "local"
            self.connected = False
            self.host = None

    # ── Low-level runner ──────────────────────────────────────────────────────

    def _run(self, *args: str) -> str:
        cmd = ["tmux"] + list(args)
        if self._mode == "local":
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return r.stdout.strip()
        else:
            with self._lock:
                if not self._client:
                    return ""
                try:
                    shell_cmd = " ".join(quote(a) for a in cmd)
                    _, stdout, _ = self._client.exec_command(shell_cmd, timeout=10)
                    return stdout.read().decode("utf-8", errors="replace").strip()
                except Exception:
                    self.connected = False
                    return ""

    def _run_no_strip(self, *args: str) -> str:
        cmd = ["tmux"] + list(args)
        if self._mode == "local":
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return r.stdout
        else:
            with self._lock:
                if not self._client:
                    return ""
                try:
                    shell_cmd = " ".join(quote(a) for a in cmd)
                    _, stdout, _ = self._client.exec_command(shell_cmd, timeout=10)
                    return stdout.read().decode("utf-8", errors="replace")
                except Exception:
                    self.connected = False
                    return ""

    # ── Tmux data ─────────────────────────────────────────────────────────────

    def get_tree(self) -> list:
        sessions_raw = self._run(
            "list-sessions", "-F", "#{session_name}\t#{session_attached}"
        )
        if not sessions_raw:
            return []

        sessions = []
        for line in sessions_raw.splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            sname, attached = parts[0], parts[1]

            wins_raw = self._run(
                "list-windows",
                "-t", sname,
                "-F", "#{window_index}\t#{window_name}\t#{window_active}",
            )
            windows = []
            for wline in wins_raw.splitlines():
                wparts = wline.split("\t")
                if len(wparts) < 3:
                    continue
                widx, wname, wactive = wparts[0], wparts[1], wparts[2]

                panes_raw = self._run(
                    "list-panes",
                    "-t", f"{sname}:{widx}",
                    "-F",
                    "#{pane_index}\t#{pane_current_command}\t#{pane_width}\t#{pane_height}\t#{pane_active}",
                )
                panes = []
                for pline in panes_raw.splitlines():
                    pparts = pline.split("\t")
                    if len(pparts) < 5:
                        continue
                    pidx, pcmd, pw, ph, pactive = pparts
                    target = f"{sname}:{widx}.{pidx}"
                    content = self._run_no_strip(
                        "capture-pane", "-p", "-e", "-J", "-t", target
                    )
                    panes.append(
                        {
                            "index": int(pidx),
                            "command": pcmd,
                            "width": int(pw),
                            "height": int(ph),
                            "active": pactive == "1",
                            "target": target,
                            "content": content,
                        }
                    )

                windows.append(
                    {
                        "index": int(widx),
                        "name": wname,
                        "active": wactive == "1",
                        "panes": panes,
                    }
                )

            sessions.append(
                {
                    "name": sname,
                    "attached": attached == "1",
                    "windows": windows,
                }
            )

        return sessions

    # ── Interaction ───────────────────────────────────────────────────────────

    def send_keys(self, target: str, keys: str, literal: bool = False) -> None:
        args = ["send-keys", "-t", target]
        if literal:
            args.append("-l")
        args.append(keys)
        self._run(*args)

    def new_window(self, session: str, name: Optional[str] = None) -> None:
        args = ["new-window", "-t", session]
        if name:
            args += ["-n", name]
        self._run(*args)

    def kill_pane(self, target: str) -> None:
        self._run("kill-pane", "-t", target)

    def kill_window(self, target: str) -> None:
        self._run("kill-window", "-t", target)

    def resize_pane(self, target: str, width: int, height: int) -> None:
        self._run("resize-pane", "-t", target, "-x", str(width), "-y", str(height))

    def new_session(self, name: str) -> None:
        self._run("new-session", "-d", "-s", name)

    def kill_session(self, name: str) -> None:
        self._run("kill-session", "-t", name)

    # ── Reconnect for SSH ─────────────────────────────────────────────────────

    def _reconnect(self) -> None:
        if self._mode != "ssh" or not self._conn_params:
            return
        import paramiko

        p = self._conn_params
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            kwargs: dict = dict(
                hostname=p["hostname"], port=p["port"],
                username=p["username"], timeout=15,
            )
            if p.get("key_file"):
                kwargs["key_filename"] = p["key_file"]
            elif p.get("password"):
                kwargs["password"] = p["password"]
            client.connect(**kwargs)
            with self._lock:
                self._client = client
                self.connected = True
        except Exception:
            self.connected = False
