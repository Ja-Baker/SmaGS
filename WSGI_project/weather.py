import os
import json
import time
import urllib.request

_cache = {}
_TTL = 1800

def _fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'SmaGS/1.0 (greenhouse monitor)',
        'Accept': 'application/json'
    })
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read())

def get_forecast(lat=None, lon=None):
    lat = lat if lat is not None else float(os.getenv("SMAGS_LAT", "38.95"))
    lon = lon if lon is not None else float(os.getenv("SMAGS_LON", "-92.33"))
    key = f"{lat:.4f},{lon:.4f}"
    now = time.time()

    cached = _cache.get(key)
    if cached and now - cached['t'] < _TTL:
        return cached['data']

    try:
        points = _fetch(f"https://api.weather.gov/points/{lat},{lon}")
        forecast_url = points['properties']['forecast']
        hourly_url = points['properties'].get('forecastHourly')
        fc = _fetch(forecast_url)
        periods = fc['properties']['periods'][:4]

        hourly = []
        if hourly_url:
            try:
                hr = _fetch(hourly_url)
                hourly = hr['properties']['periods'][:12]
            except Exception:
                hourly = []

        data = {
            'current': periods[0] if periods else None,
            'periods': periods,
            'hourly': hourly,
            'updated': fc['properties'].get('updated'),
            'location': points['properties'].get('relativeLocation', {}).get('properties', {})
        }
        _cache[key] = {'t': now, 'data': data}
        return data
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        if cached:
            return cached['data']
        return None
