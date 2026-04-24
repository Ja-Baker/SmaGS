import os
import json
import sqlite3
from datetime import datetime
from urllib.parse import parse_qs
from jinja2 import Environment, FileSystemLoader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'smags.db')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
ALL_METRICS =["soil_moisture", "soil_temp", "air_humidity", "air_temp"]
