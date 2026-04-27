import os
import json
import sqlite3
import pytz
from datetime import datetime
from urllib.parse import parse_qs
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, os.getenv("DB_PATH", "smags.db"))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
CSS_DIR = os.path.join(STATIC_DIR, "css")
LOCAL_TZ = pytz.timezone('America/Chicago')

ALL_METRICS = ["soil_moisture", "soil_temp", "air_humidity", "air_temp"]

# Setup Jinja2
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# --- DATABASE & COOKIE HELPERS ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_available_themes():
    """Scans static/css to populate the UI Museum dropdown."""
    try:
        if not os.path.exists(CSS_DIR):
            return ['green']
        files = [f.replace('.css', '') for f in os.listdir(CSS_DIR) if f.endswith('.css')]
        return sorted(files) if files else ['green']
    except Exception:
        return ['green']

def get_cookie(environ, key, default='false'):
    """Helper to parse cookies from the WSGI environment."""
    cookie_str = environ.get('HTTP_COOKIE', '')
    if not cookie_str:
        return default
    cookies = {}
    for item in cookie_str.split(';'):
        if '=' in item:
            k, v = item.split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies.get(key, default)

# --- ROUTE HANDLERS ---

def handle_favicon(environ, start_response):
    """Serves the SmaGS logo/favicon to the browser."""
    try:
        # Serves the icon from the root /app folder in your container
        with open(os.path.join(BASE_DIR, 'favicon.ico'), 'rb') as f:
            data = f.read()
        start_response('200 OK', [('Content-Type', 'image/x-icon')])
        return [data]
    except FileNotFoundError:
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b"Favicon not found"]

def handle_index(environ, start_response):
    """Main Dashboard Route."""
    consented = get_cookie(environ, 'cookie_consent', 'false') == 'true'
    theme = get_cookie(environ, 'theme', 'green') if consented else 'green'
    
    themes_list = get_available_themes()
    
    conn = get_db()
    # Fetch data for live cards and history table
    latest_data = conn.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 20").fetchall()
    
    # Map MAC addresses to friendly names
    devices_raw = conn.execute("SELECT * FROM devices").fetchall()
    device_map = {d['mac_address']: {"name": d['name'], "visible_metrics": json.loads(d['visible_metrics'])} for d in devices_raw}
    conn.close()

    template = jinja_env.get_template("index.html")
    content = template.render(
        latest=latest_data, 
        device_map=device_map, 
        theme=theme,
        themes=themes_list,
        all_metrics=ALL_METRICS,
        consented=consented
    ).encode("utf-8")

    start_response("200 OK", [("Content-Type", "text/html")])
    return [content]

def handle_set_theme(environ, start_response):
    """Handles theme updates via 303 Redirect."""
    try:
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
        params = parse_qs(post_data)
        new_theme = params.get('theme', ['green'])[0]
        
        consented = get_cookie(environ, 'cookie_consent', 'false') == 'true'
        
        headers = [
            ("Location", "/?theme_updated=1"),
            ("Cache-Control", "no-cache, no-store, must-revalidate"),
            ("Pragma", "no-cache"),
            ("Expires", "0")
        ]
        
        if consented:
            headers.append((
                "Set-Cookie", 
                f"theme={new_theme}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000"
            ))

        start_response("303 See Other", headers)
        return [b""]
    except Exception:
        start_response("303 See Other", [("Location", "/")])
        return [b""]

def handle_accept_cookies(environ, start_response):
    """Sets the consent cookie."""
    headers = [
        ("Location", "/"),
        ("Set-Cookie", "cookie_consent=true; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000")
    ]
    start_response("303 See Other", headers)
    return [b""]

def handle_api_data(environ, start_response):
    """Endpoint for ESP32/Pi sensor nodes."""
    if environ.get('REQUEST_METHOD') != 'POST':
        start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
        return [b"Method Not Allowed"]
    try:
        length = int(environ.get('CONTENT_LENGTH', 0))
        data = json.loads(environ['wsgi.input'].read(length))
        ts = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
        
        conn = get_db()
        conn.execute("""
            INSERT INTO sensor_data (sensor_id, soil_moisture, soil_temp, air_humidity, air_temp, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data["mac_address"], data["soil_moisture"], data["soil_temp"], data["air_humidity"], data["air_temp"], ts))
        conn.commit()
        conn.close()

        start_response("200 OK", [("Content-Type", "application/json")])
        return [json.dumps({"status": "success"}).encode("utf-8")]
    except Exception as e:
        start_response("400 Bad Request", [])
        return [str(e).encode("utf-8")]

# --- MAIN WSGI APP ---

def application(environ, start_response):
    path = environ.get('PATH_INFO', '/')

    # Routing Logic
    if path == "/":
        return handle_index(environ, start_response)
    elif path == "/favicon.ico":
        return handle_favicon(environ, start_response)
    elif path == "/set_theme":
        return handle_set_theme(environ, start_response)
    elif path == "/accept_cookies":
        return handle_accept_cookies(environ, start_response)
    elif path == "/api/data":
        return handle_api_data(environ, start_response)
    
    # Static File Server
    elif path.startswith("/static/"):
        file_path = os.path.join(BASE_DIR, path.lstrip("/"))
        if os.path.exists(file_path) and os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            
            mime = "text/plain"
            if path.endswith(".css"): mime = "text/css"
            elif path.endswith(".js"): mime = "application/javascript"
            elif path.endswith(".png"): mime = "image/png"
            elif path.endswith(".jpg") or path.endswith(".jpeg"): mime = "image/jpeg"
            
            start_response("200 OK", [("Content-Type", mime)])
            return [content]

    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"404 - Not Found"]