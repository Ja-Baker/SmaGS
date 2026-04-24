import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables to get the correct DB_PATH
load_dotenv()

def init_db():
    # Fetch DB_PATH from .env or default to smags.db
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_name = os.getenv("DB_PATH", "smags.db")
    db_path = os.path.join(base_dir, db_name)

    print(f"[*] Initializing SmaGS database at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Sessions Table: Track greenhouse monitoring periods
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT
        )
    """)

    # 2. Sensor Data Table: The core readings from ESP32s
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            sensor_id TEXT NOT NULL,
            soil_moisture REAL,
            soil_temp REAL,
            air_humidity REAL,
            air_temp REAL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    """)

    # 3. Devices Table: Manage and name your ESP32 hardware
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            visible_metrics TEXT NOT NULL DEFAULT '["soil_moisture","soil_temp","air_humidity","air_temp"]'
        )
    """)

    # 4. Create an initial session if none exists (Professional convenience)
    cursor.execute("SELECT COUNT(*) FROM sessions")
    if cursor.fetchone()[0] == 0:
        now = "2026-04-23 20:00:00" # Placeholder start time
        cursor.execute("INSERT INTO sessions (start_time) VALUES (?)", (now,))
        print("[+] Initial monitoring session created.")

    conn.commit()
    conn.close()
    print("[+] Database initialization complete.")

if __name__ == "__main__":
    init_db()