import time
import json
import requests

PI_IP = "127.0.0.1"   # change to your Pi's IP
URL = f"http://{PI_IP}:5001/api/data"

def send_sensor_packet(
    sensor_id: str,
    soil_moisture: float,
    soil_temp: float,
    air_humidity: float,
    air_temp: float
):
    payload = {
        "sensor_id": sensor_id,
        "soil_moisture": soil_moisture,
        "soil_temp": soil_temp,
        "air_humidity": air_humidity,
        "air_temp": air_temp
    }

    try:
        r = requests.post(URL, json=payload, timeout=5)
        print("Status:", r.status_code)
        print("Response:", r.text)
    except Exception as e:
        print("Error sending packet:", e)


if __name__ == "__main__":
    while True:
        send_sensor_packet(
            sensor_id="sensor_1",
            soil_moisture=45.2,
            soil_temp=22.1,
            air_humidity=60.5,
            air_temp=24.3
        )

        time.sleep(5)  # 5 minutes
