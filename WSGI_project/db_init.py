import sqlite3
import os

# Update this path if your db is located elsewhere
DB_PATH = "smags.db"

def setup_database():
    # Remove old DB if you want a totally fresh start (Optional)
    # if os.path.exists(DB_PATH): os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- Initializing SmaGS Database ---")

    # 1. Create Devices Table
    # Added 'visible_metrics' which is required for the new dashboard
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            sensor_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            visible_metrics TEXT DEFAULT '["soil_moisture", "soil_temp", "air_humidity", "air_temp"]'
        )
    ''')

    # 2. Create Sessions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time DATETIME DEFAULT (datetime('now', 'localtime')),
            end_time DATETIME,
            status TEXT DEFAULT 'active'
        )
    ''')

    # 3. Create Sensor Data Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            sensor_id TEXT,
            air_temp REAL,
            air_humidity REAL,
            soil_temp REAL,
            soil_moisture REAL,
            timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (sensor_id) REFERENCES devices(sensor_id)
        )
    ''')

    # 4. PRE-REGISTER YOUR SENSORS (Optional but helpful)
    # This ensures your sensors show up on the Devices page immediately
    known_sensors = [
        ('378:1C:3C:B8:EE:6C', 'Greenhouse Alpha'),
        ('36C:C8:40:93:F7:04', 'Greenhouse Beta')
    ]
    
    for sensor_id, name in known_sensors:
        cursor.execute('''
            INSERT OR IGNORE INTO devices (sensor_id, name) 
            VALUES (?, ?)
        ''', (sensor_id, name))

    # 5. Create an initial active session if none exists
    cursor.execute("SELECT id FROM sessions WHERE status = 'active'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO sessions (status) VALUES ('active')")

    conn.commit()
    conn.close()
    print("Success: Database schema is ready for the dashboard!")

if __name__ == "__main__":
    setup_database()