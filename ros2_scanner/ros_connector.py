import json
import re
import select
import shlex
import threading
from typing import Generator, List, Optional, Tuple

import paramiko


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
            stdin, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            return out, err

    def _container_script(self, cmd: str) -> str:
        """Build a bash script that sources ROS2 then runs cmd."""
        lines = []
        if self.ros_setup:
            lines.append(f"source {self.ros_setup} 2>/dev/null")
        lines.append(cmd)
        return "\n".join(lines) + "\n"

    def _run(self, cmd: str, timeout: int = 15) -> Tuple[str, str]:
        """Run a ROS2 command inside the active container via stdin."""
        script = self._container_script(cmd)
        with self._lock:
            stdin, stdout, stderr = self._client.exec_command(
                f"docker exec -i {self._container_id} bash --norc --noprofile",
                timeout=timeout,
            )
            stdin.write(script.encode())
            stdin.channel.shutdown_write()
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
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
            f"timeout 8 ros2 topic echo --once {shlex.quote(topic)} 2>&1", timeout=12
        )
        return out or err or "(no data)"

    def publish_topic(self, topic: str, msg_type: str, data: str) -> dict:
        # shlex.quote handles all special characters safely
        cmd = (
            f"ros2 topic pub --once {shlex.quote(topic)} "
            f"{shlex.quote(msg_type)} {shlex.quote(data)}"
        )
        out, err = self._run(cmd, timeout=15)
        return {"output": out, "error": err}

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
        return {"output": out, "error": err}

    # ── Action operations ─────────────────────────────────────────────

    def get_action_info(self, action: str) -> dict:
        out, _ = self._run(
            f"ros2 action info {shlex.quote(action)} 2>/dev/null", timeout=10
        )
        info: dict = {"type": None, "raw": out}
        m = re.search(r"Action:\s+(\S+)", out)
        if m:
            info["type"] = m.group(1)
        return info

    def send_action_goal(self, action: str, action_type: str, goal: str) -> dict:
        cmd = (
            f"ros2 action send_goal {shlex.quote(action)} "
            f"{shlex.quote(action_type)} {shlex.quote(goal)}"
        )
        out, err = self._run(cmd, timeout=30)
        return {"output": out, "error": err}

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

        script = self._container_script(f"ros2 topic echo {shlex.quote(topic)}")
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
                ready, _, _ = select.select([channel], [], [], 1.0)
                if ready:
                    chunk = channel.recv(4096)
                    if not chunk:
                        break
                    for raw_line in chunk.decode("utf-8", errors="replace").splitlines():
                        line = raw_line.rstrip()
                        if line == "---":
                            if buffer_lines:
                                yield f"data: {json.dumps({'message': chr(10).join(buffer_lines), 'topic': topic})}\n\n"
                                buffer_lines = []
                        else:
                            buffer_lines.append(line)
                elif channel.exit_status_ready():
                    break
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
