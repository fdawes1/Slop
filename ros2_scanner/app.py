import json
import os

from flask import Flask, Response, jsonify, make_response, render_template, request, stream_with_context

from ros_connector import ROSConnector

app = Flask(__name__)
ros = ROSConnector()

CREDS_FILE  = os.path.join(os.path.dirname(__file__), "credentials.json")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")


def _load_creds():
    try:
        with open(CREDS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_creds(entries):
    with open(CREDS_FILE, "w") as f:
        json.dump(entries, f, indent=2)


# ── Connection ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    resp = make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/api/connect", methods=["POST"])
def connect():
    data = request.get_json()
    result = ros.connect(
        host=data["host"],
        username=data["username"],
        password=data.get("password") or None,
        key_file=data.get("key_file") or None,
        port=int(data.get("port", 22)),
    )
    return jsonify(result)


@app.route("/api/disconnect", methods=["POST"])
def disconnect():
    ros.disconnect()
    return jsonify({"success": True})


# ── Saved credentials ─────────────────────────────────────────────────────────

@app.route("/api/credentials")
def get_credentials():
    return jsonify({"credentials": _load_creds()})


@app.route("/api/credentials", methods=["POST"])
def save_credential():
    data = request.get_json()
    entry = {
        "host":     data.get("host", ""),
        "port":     int(data.get("port", 22)),
        "username": data.get("username", ""),
        "password": data.get("password", ""),
    }
    entries = _load_creds()
    # Deduplicate by host+username+port; update password if re-saved
    for e in entries:
        if e["host"] == entry["host"] and e["username"] == entry["username"] and e["port"] == entry["port"]:
            e["password"] = entry["password"]
            _save_creds(entries)
            return jsonify({"success": True})
    entries.insert(0, entry)
    entries = entries[:20]  # keep last 20
    _save_creds(entries)
    return jsonify({"success": True})


# ── Config / saved views ─────────────────────────────────────────────────────

@app.route("/api/config")
def get_config():
    try:
        with open(CONFIG_FILE) as f:
            return jsonify(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({})


@app.route("/api/config", methods=["POST"])
def save_config():
    cfg = request.get_json()
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    return jsonify({"success": True})


@app.route("/api/status")
def status():
    return jsonify({
        "connected": ros.connected,
        "ready": ros.ready,
        "host": ros.host,
        "container_name": ros.container_name,
        "ros_distro": ros.ros_distro,
        "middleware": ros.middleware,
    })


# ── Container discovery + selection ──────────────────────────────────────────

@app.route("/api/containers")
def containers():
    if not ros.connected:
        return jsonify({"error": "Not connected via SSH"}), 400
    try:
        return jsonify({"containers": ros.get_containers()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/container/select", methods=["POST"])
def container_select():
    if not ros.connected:
        return jsonify({"error": "Not connected"}), 400
    data = request.get_json()
    container_id = data.get("container_id", "")
    ros_path = data.get("ros_path") or None
    if not container_id:
        return jsonify({"error": "container_id required"}), 400
    try:
        result = ros.select_container(container_id, ros_path=ros_path)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── ROS2 discovery ────────────────────────────────────────────────────────────

@app.route("/api/discover")
def discover():
    if not ros.ready:
        return jsonify({"error": "No container selected"}), 400
    try:
        return jsonify({
            "topics": ros.get_topics(),
            "services": ros.get_services(),
            "actions": ros.get_actions(),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Topic endpoints ───────────────────────────────────────────────────────────

@app.route("/api/topic/info", methods=["POST"])
def topic_info():
    topic = request.get_json().get("topic", "")
    return jsonify(ros.get_topic_info(topic))


@app.route("/api/topic/echo_once", methods=["POST"])
def topic_echo_once():
    topic = request.get_json().get("topic", "")
    return jsonify({"data": ros.echo_topic_once(topic)})


@app.route("/api/topic/publish", methods=["POST"])
def topic_publish():
    body = request.get_json()
    result = ros.publish_topic(body["topic"], body["type"], body["data"])
    return jsonify(result)


@app.route("/api/topic/stream")
def topic_stream():
    topic = request.args.get("topic", "")
    if not topic:
        return jsonify({"error": "topic parameter required"}), 400
    return Response(
        stream_with_context(ros.stream_topic(topic)),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Service endpoints ─────────────────────────────────────────────────────────

@app.route("/api/service/type", methods=["POST"])
def service_type():
    service = request.get_json().get("service", "")
    return jsonify({"type": ros.get_service_type(service)})


@app.route("/api/service/call", methods=["POST"])
def service_call():
    body = request.get_json()
    result = ros.call_service(body["service"], body["type"], body["data"])
    return jsonify(result)


# ── Interface introspection ───────────────────────────────────────────────────

@app.route("/api/interface/proto", methods=["POST"])
def interface_proto():
    type_name = request.get_json().get("type", "")
    if not type_name:
        return jsonify({"error": "type required"}), 400
    if not ros.ready:
        return jsonify({"error": "No container selected"}), 400
    try:
        return jsonify(ros.get_interface_proto(type_name))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Action endpoints ──────────────────────────────────────────────────────────

@app.route("/api/action/info", methods=["POST"])
def action_info():
    action = request.get_json().get("action", "")
    return jsonify(ros.get_action_info(action))


@app.route("/api/action/send_goal", methods=["POST"])
def action_send_goal():
    body = request.get_json()
    result = ros.send_action_goal(body["action"], body["type"], body["goal"])
    return jsonify(result)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
