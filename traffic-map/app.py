#!/usr/bin/env python3
import threading
import time
from collections import defaultdict

import psutil
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

geo_cache = {}
connections_data = []
my_location = {"lat": 0, "lon": 0, "city": "Unknown", "country": ""}
_lock = threading.Lock()

PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "169.254.", "::1", "fe80")


def is_private(ip):
    return any(ip.startswith(p) for p in PRIVATE_PREFIXES) or ip.startswith("172.") and 16 <= int(ip.split(".")[1]) <= 31


def get_remote_ips():
    conns = psutil.net_connections(kind="inet")
    seen = {}
    for c in conns:
        if c.raddr and c.raddr.ip and not is_private(c.raddr.ip):
            ip = c.raddr.ip
            if ip not in seen:
                seen[ip] = []
            seen[ip].append({"port": c.raddr.port, "status": c.status or "NONE", "pid": c.pid})
    return seen


def geolocate_batch(ips):
    uncached = [ip for ip in ips if ip not in geo_cache]
    for i in range(0, len(uncached), 100):
        batch = uncached[i : i + 100]
        try:
            resp = requests.post(
                "http://ip-api.com/batch",
                json=[{"query": ip, "fields": "status,lat,lon,city,country,isp,org,query"} for ip in batch],
                timeout=8,
            )
            for item in resp.json():
                if item.get("status") == "success":
                    geo_cache[item["query"]] = item
        except Exception as e:
            print(f"Geo batch error: {e}")


def fetch_my_location():
    global my_location
    try:
        r = requests.get("http://ip-api.com/json?fields=status,lat,lon,city,country,query", timeout=8)
        data = r.json()
        if data.get("status") == "success":
            my_location = {"lat": data["lat"], "lon": data["lon"], "city": data.get("city", ""), "country": data.get("country", ""), "ip": data.get("query", "")}
    except Exception as e:
        print(f"My location error: {e}")


def update_loop():
    fetch_my_location()
    while True:
        try:
            ip_conns = get_remote_ips()
            geolocate_batch(list(ip_conns.keys()))

            result = []
            for ip, conns in ip_conns.items():
                if ip in geo_cache:
                    g = geo_cache[ip]
                    result.append(
                        {
                            "ip": ip,
                            "lat": g["lat"],
                            "lon": g["lon"],
                            "city": g.get("city", ""),
                            "country": g.get("country", ""),
                            "isp": g.get("isp", g.get("org", "")),
                            "connections": conns,
                        }
                    )

            with _lock:
                connections_data.clear()
                connections_data.extend(result)
        except Exception as e:
            print(f"Update error: {e}")
        time.sleep(4)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/connections")
def api_connections():
    with _lock:
        return jsonify({"my_location": my_location, "connections": list(connections_data)})


if __name__ == "__main__":
    t = threading.Thread(target=update_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False)
