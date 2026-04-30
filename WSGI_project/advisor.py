CROP_PROFILES = {
    'generic':{
        'soil_moisture_min': 60,
        'soil_moisture_max': 85,
        'air_temp_min': 7,
        'air_temp_max': 24,
        'soil_temp_min': 4,
        'air_humidity_max': 70,
    },
    'lettuce': { 
        'soil_moisture_min': 60,
        'soil_moisture_max': 85,
        'air_temp_min': 7,
        'air_temp_max': 24,
        'soil_temp_min': 4,
        'air_humidity_max': 70,
    },
    'tomato': { 
        'soil_moisture_min': 50,
        'soil_moisture_max': 80,
        'air_temp_min': 15,
        'air_temp_max': 30,
        'soil_temp_min': 16,
        'air_humidity_max': 85,
    },
    'corn': {
        'soil_moisture_min': 40,
        'soil_moisture_max': 75,
        'air_temp_min': 15,
        'air_temp_max': 35,
        'soil_temp_min': 10,
        'air_humidity_max': 90,
    },
    'arugula': {
        'soil_moisture_min': 45,
        'soil_moisture_max': 75,
        'air_temp_min': 7,
        'air_temp_max': 22,
        'soil_temp_min': 7,
        'air_humidity_max': 80,
    },
}
LEVEL_RANK = {'ok': 0, 'info': 1, 'warn': 2, 'critical': 3}

def _precip_window(periods):
    if not periods:
        return 0
    best = 0
    for p in periods:
        pop = p.get('probabilityOfPrecipitation') or {}
        v = pop.get('value')
        if v is not None and v > best:
            best = v
    return best

def _forecast_high_c(periods):
    highs = []
    for p in periods:
        t = p.get('temperature')
        unit = (p.get('temperatureUnit') or 'F').upper()
        if t is None:
            continue
        c = (t - 32) * 5 / 9 if unit == 'F' else t
        highs.append(c)
    return max(highs) if highs else None

def recommend(reading, forecast, crop='arugula'):
    profile = CROP_PROFILES.get(crop, CROP_PROFILES['arugula'])
    alerts = []

    sm = reading.get('soil_moisture')
    at = reading.get('air_temp')
    st = reading.get('soil_temp')
    ah = reading.get('air_humidity')

    rain_soon = _precip_window((forecast or {}).get('periods', [])[:2]) if forecast else 0
    rain_today = _precip_window((forecast or {}).get('periods', [])[:1]) if forecast else 0
    forecast_high = _forecast_high_c((forecast or {}).get('periods', [])[:2]) if forecast else None

    if sm is not None:
        if sm < profile['soil_moisture_min']:
            if rain_soon >= 50:
                alerts.append({'level': 'info', 'message': f"Soil dry ({sm:.0f}%) but rain {rain_soon}% in next 24h — hold"})
            elif rain_soon >= 30:
                alerts.append({'level': 'warn', 'message': f"Soil dry ({sm:.0f}%), rain only {rain_soon}% — light watering"})
            else:
                alerts.append({'level': 'critical', 'message': f"Soil dry ({sm:.0f}%) and no rain forecast — water now"})
        elif sm > profile['soil_moisture_max']:
            alerts.append({'level': 'warn', 'message': f"Soil oversaturated ({sm:.0f}%) — hold watering"})

    if at is not None:
        if at > profile['air_temp_max']:
            alerts.append({'level': 'warn', 'message': f"Air temp {at:.1f}°C above {crop} range — vent"})
        elif at < profile['air_temp_min']:
            alerts.append({'level': 'warn', 'message': f"Air temp {at:.1f}°C below {crop} range — add heat"})

    if st is not None and st < profile['soil_temp_min']:
        alerts.append({'level': 'warn', 'message': f"Soil {st:.1f}°C below {crop} germination floor"})

    if ah is not None and ah > profile['air_humidity_max']:
        alerts.append({'level': 'warn', 'message': f"Humidity {ah:.0f}% high — disease risk, increase airflow"})

    if forecast_high is not None and forecast_high > profile['air_temp_max'] + 3:
        alerts.append({'level': 'info', 'message': f"Forecast peak {forecast_high:.0f}°C — pre-vent before midday"})

    if rain_today >= 70 and sm is not None and sm > profile['soil_moisture_min']:
        alerts.append({'level': 'info', 'message': f"Heavy rain likely ({rain_today}%) — skip scheduled watering"})

    if not alerts:
        return {'level': 'ok', 'message': f"Conditions nominal for {crop}"}

    alerts.sort(key=lambda a: LEVEL_RANK[a['level']], reverse=True)
    return alerts[0]
