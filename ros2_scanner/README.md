# ROS2 Scanner

A browser-based tool for exploring and interacting with ROS2 nodes running inside Docker containers on a remote robot over SSH.

## Features

- **SSH → Docker → ROS2**: connects to your robot via SSH, discovers running Docker containers, and sources ROS2 automatically
- **Auto-select containers**: prefers Zenoh containers; falls back to the first ROS2-capable container
- **Topics, Services, Actions**: browse all three with live counts and a filter box
- **Parameter autocomplete**: when you select a topic/service/action, the YAML data field is pre-filled with the correct prototype (via `ros2 interface proto`)
- **Topic streaming**: live SSE stream with a 300-message rolling buffer
- **Echo once / Publish**: single-shot echo or publish with YAML payload
- **Service call / Action goal**: send requests directly from the browser
- **ROS2 distro detection**: auto-detects installed distros (prefers Jazzy → Iron → Humble → Rolling)
- **Middleware detection**: reads `$RMW_IMPLEMENTATION` from the container

## Requirements

- Python 3.10+
- `flask>=3.0`
- `paramiko>=3.4`

```
pip install -r requirements.txt
```

The remote robot must have Docker running and a container with ROS2 installed.  
`ros2 interface proto` requires **ROS2 Humble or later**.

## Usage

```bash
python app.py
```

Open `http://localhost:5000` in your browser.

1. Enter the robot's IP, SSH port (default 22), username, and password, then click **Connect**
2. The app scans Docker containers and auto-selects the best ROS2 one
3. Click a different container card if needed, or override the ROS2 setup path
4. Browse Topics / Services / Actions in the sidebar; click any item to inspect it
5. The YAML data field is auto-filled with the correct parameter structure
6. Use **Echo Once**, **Live Stream**, **Publish**, **Call**, or **Send Goal** as needed

## Architecture

```
app.py            Flask HTTP + SSE server
ros_connector.py  SSH → docker exec → ROS2 command runner
templates/
  index.html      Single-page UI (Bootstrap 5, vanilla JS)
```

All ROS2 commands run inside the selected Docker container via `docker exec -i <id> bash`, with the ROS2 setup script sourced first. A separate SSH connection is opened for streaming to avoid blocking the main lock.
