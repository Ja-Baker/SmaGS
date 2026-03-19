from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import sqlite3
import os
import json

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smags.db")

ALL_METRICS = ["soil_moisture", "soil_temp", "air_humidity", "air_temp"]

current_session_id = None


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            sensor_id TEXT NOT NULL,
            soil_moisture REAL,
            soil_temp REAL,
            air_humidity REAL,
            air_temp REAL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            visible_metrics TEXT NOT NULL DEFAULT '["soil_moisture","soil_temp","air_humidity","air_temp"]'
        )
    """)
    conn.commit()
    conn.close()


def start_session():
    global current_session_id
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute("INSERT INTO sessions (start_time) VALUES (?)", (now,))
    current_session_id = cursor.lastrowid
    conn.commit()
    conn.close()


def end_session():
    global current_session_id
    if current_session_id:
        conn = get_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE sessions SET end_time = ? WHERE id = ?", (now, current_session_id))
        conn.commit()
        conn.close()


def get_or_create_device(conn, mac_address):
    device = conn.execute("SELECT * FROM devices WHERE mac_address = ?", (mac_address,)).fetchone()
    if device:
        return device

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = conn.execute("SELECT COUNT(*) as c FROM devices").fetchone()["c"]
    default_name = f"Sensor {count + 1}"

    conn.execute(
        "INSERT INTO devices (mac_address, name, first_seen, visible_metrics) VALUES (?, ?, ?, ?)",
        (mac_address, default_name, now, json.dumps(ALL_METRICS))
    )
    conn.commit()
    return conn.execute("SELECT * FROM devices WHERE mac_address = ?", (mac_address,)).fetchone()


def get_device_map(conn):
    devices = conn.execute("SELECT * FROM devices").fetchall()
    device_map = {}
    for d in devices:
        device_map[d["mac_address"]] = {
            "name": d["name"],
            "visible_metrics": json.loads(d["visible_metrics"]),
            "mac_address": d["mac_address"],
            "first_seen": d["first_seen"]
        }
    for d in devices:
        device_map[d["name"]] = device_map[d["mac_address"]]
    return device_map


def resolve_sensor_name(sensor_id, device_map):
    if sensor_id in device_map:
        return device_map[sensor_id]["name"]
    return sensor_id.replace("_", " ").title()


# ─── Frontend Routes ────────────────────────────────────────────────


@app.route("/")
def index():
    conn = get_db()

    latest = conn.execute("""
        SELECT s1.*
        FROM sensor_data s1
        INNER JOIN (
            SELECT sensor_id, MAX(timestamp) as max_ts
            FROM sensor_data
            WHERE session_id = ?
            GROUP BY sensor_id
        ) s2 ON s1.sensor_id = s2.sensor_id AND s1.timestamp = s2.max_ts
        ORDER BY s1.sensor_id
    """, (current_session_id,)).fetchall()

    history = conn.execute("""
        SELECT * FROM sensor_data
        WHERE session_id = ?
        ORDER BY timestamp DESC
        LIMIT 20
    """, (current_session_id,)).fetchall()

    device_map = get_device_map(conn)
    conn.close()
    return render_template("index.html", latest=latest, history=history,
                           session_id=current_session_id, device_map=device_map,
                           all_metrics=ALL_METRICS)


@app.route("/sessions")
def sessions_list():
    conn = get_db()
    sessions = conn.execute("""
        SELECT s.*, COUNT(d.id) as reading_count
        FROM sessions s
        LEFT JOIN sensor_data d ON d.session_id = s.id
        GROUP BY s.id
        ORDER BY s.start_time DESC
    """).fetchall()
    conn.close()
    return render_template("sessions.html", sessions=sessions, current_session_id=current_session_id)


@app.route("/sessions/<int:session_id>")
def session_detail(session_id):
    conn = get_db()

    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not session:
        conn.close()
        return "Session not found", 404

    latest = conn.execute("""
        SELECT s1.*
        FROM sensor_data s1
        INNER JOIN (
            SELECT sensor_id, MAX(timestamp) as max_ts
            FROM sensor_data
            WHERE session_id = ?
            GROUP BY sensor_id
        ) s2 ON s1.sensor_id = s2.sensor_id AND s1.timestamp = s2.max_ts
        ORDER BY s1.sensor_id
    """, (session_id,)).fetchall()

    readings = conn.execute("""
        SELECT * FROM sensor_data
        WHERE session_id = ?
        ORDER BY timestamp DESC
    """, (session_id,)).fetchall()

    device_map = get_device_map(conn)
    conn.close()
    return render_template("session_detail.html", session=session, latest=latest,
                           readings=readings, device_map=device_map, all_metrics=ALL_METRICS)


@app.route("/devices")
def devices_page():
    conn = get_db()
    devices = conn.execute("SELECT * FROM devices ORDER BY first_seen").fetchall()
    conn.close()
    devices_list = []
    for d in devices:
        devices_list.append({
            "id": d["id"],
            "mac_address": d["mac_address"],
            "name": d["name"],
            "first_seen": d["first_seen"],
            "visible_metrics": json.loads(d["visible_metrics"])
        })
    return render_template("devices.html", devices=devices_list, all_metrics=ALL_METRICS)


@app.route("/devices/<int:device_id>/update", methods=["POST"])
def update_device(device_id):
    conn = get_db()
    device = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    if not device:
        conn.close()
        return "Device not found", 404

    name = request.form.get("name", device["name"]).strip()
    if not name:
        name = device["name"]

    visible = request.form.getlist("visible_metrics")
    if not visible:
        visible = ALL_METRICS

    conn.execute("UPDATE devices SET name = ?, visible_metrics = ? WHERE id = ?",
                 (name, json.dumps(visible), device_id))
    conn.commit()
    conn.close()
    return redirect(url_for("devices_page"))


# ─── API Routes ──────────────────────────────────────────────────────


@app.route("/api/data", methods=["POST"])
def receive_data():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    mac_address = data.get("mac_address") or data.get("sensor_id")
    if not mac_address:
        return jsonify({"error": "Missing mac_address or sensor_id"}), 400

    required_fields = ["soil_moisture", "soil_temp", "air_humidity", "air_temp"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()

    device = get_or_create_device(conn, mac_address)

    conn.execute("""
        INSERT INTO sensor_data (session_id, sensor_id, soil_moisture, soil_temp, air_humidity, air_temp, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        current_session_id,
        mac_address,
        float(data["soil_moisture"]),
        float(data["soil_temp"]),
        float(data["air_humidity"]),
        float(data["air_temp"]),
        timestamp
    ))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "ok",
        "session_id": current_session_id,
        "device_name": device["name"],
        "recorded": {
            "mac_address": mac_address,
            "soil_moisture": data["soil_moisture"],
            "soil_temp": data["soil_temp"],
            "air_humidity": data["air_humidity"],
            "air_temp": data["air_temp"],
            "timestamp": timestamp
        }
    }), 200


@app.route("/api/data", methods=["GET"])
def get_all_data():
    conn = get_db()
    rows = conn.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/latest", methods=["GET"])
def get_latest():
    conn = get_db()
    rows = conn.execute("""
        SELECT s1.*
        FROM sensor_data s1
        INNER JOIN (
            SELECT sensor_id, MAX(timestamp) as max_ts
            FROM sensor_data
            WHERE session_id = ?
            GROUP BY sensor_id
        ) s2 ON s1.sensor_id = s2.sensor_id AND s1.timestamp = s2.max_ts
        ORDER BY s1.sensor_id
    """, (current_session_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/devices", methods=["GET"])
def get_devices():
    conn = get_db()
    devices = conn.execute("SELECT * FROM devices ORDER BY first_seen").fetchall()
    conn.close()
    result = []
    for d in devices:
        result.append({
            "id": d["id"],
            "mac_address": d["mac_address"],
            "name": d["name"],
            "first_seen": d["first_seen"],
            "visible_metrics": json.loads(d["visible_metrics"])
        })
    return jsonify(result)


if __name__ == "__main__":
    init_db()
    start_session()
    try:
        app.run(host="0.0.0.0", port=5001, debug=True)
    finally:
        end_session()
