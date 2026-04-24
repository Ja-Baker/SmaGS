import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "smags.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Device Mapping Table (ID to Name)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            sensor_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')

    # 2. Sessions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME,
            status TEXT DEFAULT 'active'
        )
    ''')

    # 3. Sensor Data Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            sensor_id TEXT,
            air_temp REAL,
            air_humidity REAL,
            soil_temp REAL,
            soil_moisture REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (sensor_id) REFERENCES devices(sensor_id)
        )
    ''')

    # Ensure at least one active session exists
    cursor.execute("SELECT id FROM sessions WHERE status = 'active'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO sessions (status) VALUES ('active')")

    conn.commit()
    conn.close()
    print(f"SmaGS: Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()