import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "smags.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn

def get_latest_readings(limit=10):
    """Fetches the most recent readings for the dashboard."""
    conn = get_db_connection()
    query = "SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT ?"
    data = conn.execute(query, (limit,)).fetchall()
    conn.close()
    return data

def get_device_map():
    """Returns a dictionary mapping sensor_ids to friendly names."""
    conn = get_db_connection()
    devices = conn.execute("SELECT * FROM devices").fetchall()
    conn.close()
    # Convert list of rows to a dictionary { "MAC_ADDR": {"name": "Front Bed"} }
    return {d['sensor_id']: {"name": d['name']} for d in devices}

def register_reading(sensor_id, air_t, air_h, soil_t, soil_m):
    """Saves data and auto-registers unknown devices."""
    conn = get_db_connection()
    
    # 1. Check if device is known, if not, add it
    device_exists = conn.execute("SELECT 1 FROM devices WHERE sensor_id = ?", (sensor_id,)).fetchone()
    if not device_exists:
        conn.execute("INSERT INTO devices (sensor_id, name) VALUES (?, ?)", (sensor_id, f"New Device ({sensor_id})"))
    
    # 2. Get the current active session
    session = conn.execute("SELECT id FROM sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1").fetchone()
    session_id = session['id'] if session else 1
    
    # 3. Insert the data
    conn.execute('''
        INSERT INTO sensor_data (session_id, sensor_id, air_temp, air_humidity, soil_temp, soil_moisture)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, sensor_id, air_t, air_h, soil_t, soil_m))
    
    conn.commit()
    conn.close()

def get_all_sessions():
    """Fetches all past sessions for the /sessions page."""
    conn = get_db_connection()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY start_time DESC").fetchall()
    conn.close()
    return sessions