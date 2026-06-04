import json
import re
import shlex
import threading
import time
from typing import Generator, List, Optional, Tuple

import paramiko

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHFJA-Z]")
# Zenoh/Rust tracing lines: "2026-06-03T08:00:00.000000Z  INFO ThreadId(...) zenoh::..."
_ZENOH_LOG_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s+(INFO|WARN|ERROR|DEBUG|TRACE)\b")
# RCL deprecation warnings and rclpy cleanup errors that are always benign noise
_RCL_NOISE_RE = re.compile(
    r"^\[(?:WARN|INFO)\]\s+\[[\d.]+\]\s+\[rcl\]:.*$|^!rclpy\.ok\(\)\s*$",
    re.MULTILINE,
)


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _is_zenoh_log(line: str) -> bool:
    return bool(_ZENOH_LOG_RE.match(line.lstrip()))


def _clean_cmd(text: str) -> str:
    """Strip ANSI codes, RCL deprecation warnings, and rclpy cleanup noise."""
    return _RCL_NOISE_RE.sub("", _strip_ansi(text)).strip()


class ROSConnector:
    """SSH → Docker → ROS2 interface.

    Flow: SSH to robot → find Docker container → exec all ROS2 commands
    inside the container via stdin (avoids shell quoting entirely).
    """

    DISTRO_PREFERENCE = ["jazzy", "iron", "humble", "rolling", "galactic", "foxy"]

    def __init__(self):
        self._client: Optional[paramiko.SSHClient] = None
        self._lock = threading.Lock()
        self._conn_params: dict = {}

        # SSH state
        self.connected: bool = False
        self.host: Optional[str] = None

        # Container state (set after container selection)
        self._container_id: Optional[str] = None
        self.container_name: Optional[str] = None
        self.ros_setup: Optional[str] = None
        self.ros_distro: Optional[str] = None
        self.ros_overlays: List[str] = []
        self.middleware: Optional[str] = None
        self.ready: bool = False  # True once container is selected

    # ── SSH connection ────────────────────────────────────────────────

    def connect(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        port: int = 22,
    ) -> dict:
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
                self.host = host
                self.connected = True
                self._conn_params = dict(
                    hostname=host, port=port, username=username,
                    password=password, key_file=key_file,
                )

            self._reset_container()
            return {"success": True}
        except Exception as exc:
            self.connected = False
            return {"success": False, "error": str(exc)}

    def disconnect(self) -> None:
        with self._lock:
            if self._client:
                self._client.close()
                self._client = None
            self.connected = False
        self._reset_container()
        self.host = None

    def _reset_container(self) -> None:
        self._container_id = None
        self.container_name = None
        self.ros_setup = None
        self.ros_distro = None
        self.ros_overlays: List[str] = []
        self.middleware = None
        self.ready = False

    # ── Docker container discovery ────────────────────────────────────

    def get_containers(self) -> List[dict]:
        """List all running containers, flagging those with ROS2."""
        out, _ = self._run_raw(
            "docker ps --format '{{json .}}' 2>/dev/null", timeout=10
        )
        containers = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                containers.append({
                    "id": c.get("ID", ""),
                    "name": c.get("Names", ""),
                    "image": c.get("Image", ""),
                    "status": c.get("Status", ""),
                    "has_ros": False,
                    "ros_distros": [],
                })
            except json.JSONDecodeError:
                continue

        for c in containers:
            cid = c["id"]
            # Check /opt/ros
            out, _ = self._run_raw(
                f"docker exec {cid} ls /opt/ros/ 2>/dev/null", timeout=5
            )
            if out.strip():
                c["has_ros"] = True
                c["ros_distros"] = out.strip().split()
            else:
                # Fallback: check if ros2 binary is in PATH
                out, _ = self._run_raw(
                    f"docker exec {cid} which ros2 2>/dev/null", timeout=3
                )
                if out.strip():
                    c["has_ros"] = True

        return containers

    def select_container(self, container_id: str, ros_path: Optional[str] = None) -> dict:
        """Activate a container: detect ROS2 distro and middleware."""
        self._container_id = container_id

        # Resolve display name
        out, _ = self._run_raw(
            f"docker inspect --format '{{{{.Name}}}}' {container_id} 2>/dev/null", timeout=5
        )
        self.container_name = out.strip().lstrip("/") or container_id

        if ros_path:
            self.ros_setup = ros_path
            self.ros_distro = "custom"
        else:
            self._detect_ros_in_container()
            self.ros_overlays = self._detect_workspace_overlays()

        self._detect_middleware()
        self.ready = True

        return {
            "success": True,
            "container_id": container_id,
            "container_name": self.container_name,
            "ros_distro": self.ros_distro,
            "ros_setup": self.ros_setup,
            "middleware": self.middleware,
        }

    def _detect_ros_in_container(self) -> None:
        out, _ = self._run_raw(
            f"docker exec {self._container_id} ls /opt/ros/ 2>/dev/null", timeout=5
        )
        distros = out.strip().split()
        for pref in self.DISTRO_PREFERENCE:
            if pref in distros:
                self.ros_distro = pref
                self.ros_setup = f"/opt/ros/{pref}/setup.bash"
                return
        if distros:
            self.ros_distro = distros[0]
            self.ros_setup = f"/opt/ros/{distros[0]}/setup.bash"
            return
        # Try env var already set inside the container
        out, _ = self._run_raw(
            f"docker exec {self._container_id} bash -c 'echo $ROS_DISTRO' 2>/dev/null",
            timeout=5,
        )
        distro = out.strip()
        if distro:
            self.ros_distro = distro
            self.ros_setup = f"/opt/ros/{distro}/setup.bash"

    def _detect_workspace_overlays(self) -> List[str]:
        """Find workspace overlay setup.bash files."""
        found: List[str] = []
        seen: set = set()

        def _check_paths(paths: List[str]) -> None:
            if not paths:
                return
            checks = '; '.join(f"[ -f {p} ] && echo {p}" for p in paths)
            out, _ = self._run_raw(
                f"docker exec {self._container_id} bash -c '{checks}' 2>/dev/null",
                timeout=5,
            )
            for line in out.splitlines():
                p = line.strip()
                if p and p not in seen:
                    seen.add(p)
                    found.append(p)

        # Pass 1: login shell — picks up anything the container already sources
        out, _ = self._run_raw(
            f"docker exec {self._container_id} bash -l -c 'echo $AMENT_PREFIX_PATH' 2>/dev/null",
            timeout=8,
        )
        install_dirs: List[str] = []
        dir_seen: set = set()
        for prefix in out.split(':'):
            prefix = prefix.strip().rstrip('/')
            if not prefix or '/opt/ros/' in prefix:
                continue
            for candidate in ['/'.join(prefix.split('/')[:-1]), prefix]:
                if candidate and candidate not in dir_seen:
                    dir_seen.add(candidate)
                    install_dirs.append(candidate)
        _check_paths([f"{d}/setup.bash" for d in install_dirs])

        # Pass 2: brute-force check common workspace locations
        common = [
            "/ros2_ws/install/setup.bash",
            "/workspace/install/setup.bash",
            "/home/ros/ros2_ws/install/setup.bash",
            "/home/user/ros2_ws/install/setup.bash",
            "/root/ros2_ws/install/setup.bash",
            "/opt/workspace/install/setup.bash",
            "/colcon_ws/install/setup.bash",
        ]
        _check_paths([p for p in common if p not in seen])

        # Pass 3: shallow find under likely roots (fast — maxdepth 5)
        if not found:
            out, _ = self._run_raw(
                f"docker exec {self._container_id} "
                f"find /ros2_ws /workspace /home /root /opt/ros_ws "
                f"-maxdepth 5 -name setup.bash -path '*/install/*' 2>/dev/null | head -8",
                timeout=8,
            )
            for line in out.splitlines():
                p = line.strip()
                if p and p not in seen and '/opt/ros/' not in p:
                    seen.add(p)
                    found.append(p)

        return found

    def _detect_middleware(self) -> None:
        out, _ = self._run_raw(
            f"docker exec {self._container_id} bash -c 'echo $RMW_IMPLEMENTATION' 2>/dev/null",
            timeout=5,
        )
        rmw = out.strip()
        self.middleware = rmw if rmw else "rmw_fastrtps_cpp"

    # ── Low-level SSH helpers ─────────────────────────────────────────

    def _run_raw(self, cmd: str, timeout: int = 10) -> Tuple[str, str]:
        """Run a raw shell command over SSH (no container)."""
        with self._lock:
            if self._client is None:
                try:
                    self._client = self._new_client()
                    self.connected = True
                except Exception as exc:
                    return "", f"SSH disconnected: {exc}"
            try:
                stdin, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
                out = stdout.read().decode("utf-8", errors="replace")
                err = stderr.read().decode("utf-8", errors="replace")
                return out, err
            except Exception as exc:
                self._client = None
                self.connected = False
                return "", f"SSH error: {exc}"

    def _container_script(self, cmd: str) -> str:
        """Build a bash script that sources ROS2 (base + workspace overlays) then runs cmd."""
        lines = []
        if self.ros_setup:
            lines.append(f"source {self.ros_setup} 2>/dev/null")
        for overlay in self.ros_overlays:
            lines.append(f"source {overlay} 2>/dev/null")
        # Suppress zenoh/Rust INFO+WARN messages that rmw_zenoh_cpp writes to stdout
        lines.append("export RUST_LOG=error")
        lines.append(cmd)
        return "\n".join(lines) + "\n"

    def _run(self, cmd: str, timeout: int = 15) -> Tuple[str, str]:
        """Run a ROS2 command inside the active container via stdin."""
        script = self._container_script(cmd)
        with self._lock:
            if self._client is None:
                try:
                    self._client = self._new_client()
                    self.connected = True
                except Exception as exc:
                    return "", f"SSH disconnected — reconnect failed: {exc}"
            try:
                stdin, stdout, stderr = self._client.exec_command(
                    f"docker exec -i {self._container_id} bash --norc --noprofile",
                    timeout=timeout,
                )
                stdin.write(script.encode())
                stdin.channel.shutdown_write()
                out = stdout.read().decode("utf-8", errors="replace")
                err = stderr.read().decode("utf-8", errors="replace")
            except Exception as exc:
                self._client = None
                self.connected = False
                return "", f"SSH error (connection dropped): {exc}"
        return out, err

    def _new_client(self) -> paramiko.SSHClient:
        p = self._conn_params
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs: dict = dict(hostname=p["hostname"], port=p["port"],
                            username=p["username"], timeout=15)
        if p.get("key_file"):
            kwargs["key_filename"] = p["key_file"]
        elif p.get("password"):
            kwargs["password"] = p["password"]
        client.connect(**kwargs)
        return client

    # ── ROS2 discovery ────────────────────────────────────────────────

    def get_topics(self) -> List[str]:
        out, _ = self._run("ros2 topic list 2>/dev/null")
        return sorted(t.strip() for t in out.splitlines() if t.strip())

    def get_services(self) -> List[str]:
        out, _ = self._run("ros2 service list 2>/dev/null")
        return sorted(s.strip() for s in out.splitlines() if s.strip())

    def get_actions(self) -> List[str]:
        out, _ = self._run("ros2 action list 2>/dev/null")
        return sorted(
            a.strip() for a in out.splitlines()
            if a.strip() and not a.strip().startswith("[")
        )

    # ── Topic operations ──────────────────────────────────────────────

    def get_topic_info(self, topic: str) -> dict:
        out, _ = self._run(
            f"ros2 topic info {shlex.quote(topic)} -v 2>/dev/null", timeout=10
        )
        info: dict = {"type": None, "publisher_count": 0, "subscriber_count": 0, "raw": out}
        m = re.search(r"Type:\s+(\S+)", out)
        if m:
            info["type"] = m.group(1)
        m = re.search(r"Publisher count:\s+(\d+)", out)
        if m:
            info["publisher_count"] = int(m.group(1))
        m = re.search(r"Subscription count:\s+(\d+)", out)
        if m:
            info["subscriber_count"] = int(m.group(1))
        return info

    def echo_topic_once(self, topic: str) -> str:
        out, err = self._run(
            f"timeout 8 ros2 topic echo --once {shlex.quote(topic)}", timeout=12
        )
        raw = out or err or "(no data)"
        lines = [l for l in _strip_ansi(raw).splitlines() if not _is_zenoh_log(l)]
        return "\n".join(lines).strip() or "(no data)"

    def publish_topic(self, topic: str, msg_type: str, data: str) -> dict:
        # --times 1 avoids the rclpy !rclpy.ok() cleanup race in --once
        cmd = (
            f"ros2 topic pub --times 1 {shlex.quote(topic)} "
            f"{shlex.quote(msg_type)} {shlex.quote(data)}"
        )
        out, err = self._run(cmd, timeout=15)
        return {"output": _clean_cmd(out), "error": _clean_cmd(err)}

    # ── Service operations ────────────────────────────────────────────

    def get_service_type(self, service: str) -> str:
        out, _ = self._run(
            f"ros2 service type {shlex.quote(service)} 2>/dev/null", timeout=10
        )
        return out.strip()

    def call_service(self, service: str, srv_type: str, data: str) -> dict:
        cmd = (
            f"ros2 service call {shlex.quote(service)} "
            f"{shlex.quote(srv_type)} {shlex.quote(data)}"
        )
        out, err = self._run(cmd, timeout=20)
        return {"output": _clean_cmd(out), "error": _clean_cmd(err)}

    # ── Action operations ─────────────────────────────────────────────

    def get_action_info(self, action: str) -> dict:
        # -t flag makes ros2 print types in brackets: /node [pkg/action/Type]
        out, _ = self._run(
            f"ros2 action info -t {shlex.quote(action)} 2>/dev/null", timeout=10
        )
        info: dict = {"type": None, "raw": out}
        m = re.search(r"\[(\S+/action/\S+)\]", out)
        if m:
            info["type"] = m.group(1)
        return info

    def send_action_goal(self, action: str, action_type: str, goal: str) -> dict:
        cmd = (
            f"ros2 action send_goal {shlex.quote(action)} "
            f"{shlex.quote(action_type)} {shlex.quote(goal)}"
        )
        out, err = self._run(cmd, timeout=30)
        return {"output": _clean_cmd(out), "error": _clean_cmd(err)}

    # ── Interface introspection ───────────────────────────────────────

    def get_interface_proto(self, type_name: str) -> dict:
        """Return the YAML prototype for a message/service/action type."""
        out, err = self._run(
            f"ros2 interface proto {shlex.quote(type_name)} 2>/dev/null", timeout=10
        )
        proto = out.strip()
        if not proto:
            return {"error": err.strip() or "No prototype returned"}
        return {"proto": proto}

    # ── Topic streaming (SSE) ─────────────────────────────────────────

    def stream_topic(self, topic: str) -> Generator[str, None, None]:
        if not self.connected or not self._container_id:
            yield f"data: {json.dumps({'error': 'Not ready — select a container first'})}\n\n"
            return

        try:
            client = self._new_client()
        except Exception as exc:
            yield f"data: {json.dumps({'error': f'SSH failed: {exc}'})}\n\n"
            return

        # PYTHONUNBUFFERED=1 forces ros2 topic echo (a Python process) to flush
        # each message immediately instead of accumulating in a block buffer
        script = self._container_script(
            f"PYTHONUNBUFFERED=1 ros2 topic echo {shlex.quote(topic)}"
        )
        channel = None
        try:
            stdin, stdout, _ = client.exec_command(
                f"docker exec -i {self._container_id} bash --norc --noprofile",
                timeout=300,
            )
            stdin.write(script.encode())
            stdin.channel.shutdown_write()
            channel = stdout.channel
            buffer_lines: List[str] = []

            while True:
                if channel.recv_ready():
                    chunk = channel.recv(4096)
                    if not chunk:
                        break
                    for raw_line in _strip_ansi(chunk.decode("utf-8", errors="replace")).splitlines():
                        line = raw_line.rstrip()
                        if line == "---":
                            if buffer_lines:
                                yield f"data: {json.dumps({'message': chr(10).join(buffer_lines), 'topic': topic})}\n\n"
                                buffer_lines = []
                        elif not _is_zenoh_log(line):
                            buffer_lines.append(line)
                elif channel.exit_status_ready():
                    break
                else:
                    time.sleep(0.05)
        except GeneratorExit:
            pass
        except Exception as exc:
            try:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            except Exception:
                pass
        finally:
            try:
                if channel:
                    channel.close()
                client.close()
            except Exception:
                pass
