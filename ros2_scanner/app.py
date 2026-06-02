from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from ros_connector import ROSConnector

app = Flask(__name__)
ros = ROSConnector()


# ── Connection ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


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
