import os
import json
import sqlite3
import hmac
import hashlib
from datetime import datetime
from urllib.parse import parse_qs
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

# --- CONFIGURATION & SECRETS ---
# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Fetch key from .env (as requested) or fallback for safety
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-default-key").encode('utf-8')
DB_PATH = os.path.join(BASE_DIR, os.getenv("DB_PATH", "smags.db"))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

ALL_METRICS = ["soil_moisture", "soil_temp", "air_humidity", "air_temp"]

# Setup Jinja2 for professional HTML rendering
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# --- DATABASE HELPERS ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite database with the required SmaGS tables."""
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
            timestamp TEXT NOT NULL
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

# --- UTILITIES ---
def get_cookie(environ, key, default='green'):
    """Extracts a specific cookie value from the WSGI environment."""
    cookie_str = environ.get('HTTP_COOKIE', '')
    if not cookie_str:
        return default
    # Parse cookies manually (professional WSGI standard)
    cookies = {k.strip(): v[0] for k, v in parse_qs(cookie_str.replace('; ', '&')).items()}
    return cookies.get(key, default)

# --- ROUTE HANDLERS ---
def handle_index(environ, start_response):
    theme = get_cookie(environ, 'theme', 'green')
    conn = get_db()
    
    # Fetch latest data for the dashboard
    latest = conn.execute("""
        SELECT * FROM sensor_data 
        ORDER BY timestamp DESC LIMIT 10
    """).fetchall()
    
    devices = conn.execute("SELECT * FROM devices").fetchall()
    conn.close()

    template = jinja_env.get_template("index.html")
    content = template.render(
        latest=latest, 
        devices=devices, 
        theme=theme,
        all_metrics=ALL_METRICS
    ).encode("utf-8")

    start_response("200 OK", [("Content-Type", "text/html"), ("Content-Length", str(len(content)))])
    return [content]

def handle_set_theme(environ, start_response):
    """Sets the user's theme preference via a cookie."""
    try:
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        body = environ['wsgi.input'].read(content_length).decode('utf-8')
        params = parse_qs(body)
        new_theme = params.get('theme', ['green'])[0]
        
        # Redirect back to home with the Set-Cookie header
        headers = [
            ("Location", "/"),
            ("Set-Cookie", f"theme={new_theme}; Path=/; HttpOnly; SameSite=Lax")
        ]
        start_response("303 See Other", headers)
        return [b""]
    except Exception:
        start_response("400 Bad Request", [("Content-Type", "text/plain")])
        return [b"Error setting theme"]

def handle_api_data(environ, start_response):
    """Handles POST requests from greenhouse sensors (ESP32/Raspberry Pi)."""
    if environ['REQUEST_METHOD'] != 'POST':
        start_response("405 Method Not Allowed", [])
        return [b"Method Not Allowed"]

    try:
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length)
        data = json.loads(post_data)

        mac_address = data.get("mac_address") or data.get("sensor_id")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        conn.execute("""
            INSERT INTO sensor_data (sensor_id, soil_moisture, soil_temp, air_humidity, air_temp, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (mac_address, data["soil_moisture"], data["soil_temp"], data["air_humidity"], data["air_temp"], timestamp))
        conn.commit()
        conn.close()

        response = json.dumps({"status": "ok", "time": timestamp}).encode("utf-8")
        start_response("200 OK", [("Content-Type", "application/json")])
        return [response]
    except Exception as e:
        start_response("400 Bad Request", [("Content-Type", "application/json")])
        return [json.dumps({"error": str(e)}).encode("utf-8")]

# --- THE MAIN WSGI APPLICATION ---
def application(environ, start_response):
    path = environ.get('PATH_INFO', '/')

    # Routing logic
    if path == "/":
        return handle_index(environ, start_response)
    
    elif path == "/set_theme":
        return handle_set_theme(environ, start_response)
    
    elif path == "/api/data":
        return handle_api_data(environ, start_response)

    # Manual static file serving for CSS/Themes
    elif path.startswith("/static/"):
        file_path = os.path.join(BASE_DIR, path.lstrip("/"))
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            mime = "text/css" if path.endswith(".css") else "application/octet-stream"
            start_response("200 OK", [("Content-Type", mime), ("Content-Length", str(len(content)))])
            return [content]

    # 404 fallback
    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"Not Found"]

# For local testing only. Production should use Gunicorn.
if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    init_db()
    print("Serving SmaGS (WSGI) on http://localhost:5001...")
    httpd = make_server('0.0.0.0', 5001, application)
    httpd.serve_forever()