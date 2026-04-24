import sqlite3
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, os.getenv("DB_PATH", "smags.db"))

def get_db_connection():
    """Establishes a connection to the SQLite database with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_latest_readings(session_id):
    """
    Fetches the most recent reading for every unique sensor 
    registered in a specific session.
    """
    conn = get_db_connection()
    # Using an INNER JOIN to get the full row for the maximum timestamp per sensor
    query = """
        SELECT s1.*
        FROM sensor_data s1
        INNER JOIN (
            SELECT sensor_id, MAX(timestamp) as max_ts
            FROM sensor_data
            WHERE session_id = ?
            GROUP BY sensor_id
        ) s2 ON s1.sensor_id = s2.sensor_id AND s1.timestamp = s2.max_ts
        ORDER BY s1.sensor_id
    """
    rows = conn.execute(query, (session_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_device_map():
    """
    Returns a dictionary mapping MAC addresses to their friendly names
    and visibility settings.
    """
    conn = get_db_connection()
    devices = conn.execute("SELECT mac_address, name, visible_metrics FROM devices").fetchall()
    conn.close()
    
    device_map = {}
    for dev in devices:
        device_map[dev['mac_address']] = {
            "name": dev['name'],
            "visible_metrics": json.loads(dev['visible_metrics'])
        }
    return device_map

def register_or_update_device(mac_address):
    """
    Checks if a device exists; if not, registers it automatically.
    This is called when an ESP32 first checks in.
    """
    conn = get_db_connection()
    device = conn.execute("SELECT * FROM devices WHERE mac_address = ?", (mac_address,)).fetchone()
    
    if not device:
        print(f"[*] New device detected: {mac_address}. Registering...")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        default_name = f"Sensor {mac_address[-5:]}" # Use last 5 of MAC as default name
        default_metrics = json.dumps(["soil_moisture", "soil_temp", "air_humidity", "air_temp"])
        
        conn.execute("""
            INSERT INTO devices (mac_address, name, first_seen, visible_metrics)
            VALUES (?, ?, ?, ?)
        """, (mac_address, default_name, now, default_metrics))
        conn.commit()
    
    conn.close()

def get_all_metrics():
    """Static list of metrics supported by SmaGS hardware."""
    return ["soil_moisture", "soil_temp", "air_humidity", "air_temp"]