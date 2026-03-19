# how the ESP32s send data to the flask app

POST to `http://<pi_ip>:5000/api/data` with this json:

```json
{
    "sensor_id": "sensor_1",
    "soil_moisture": 45.2,
    "soil_temp": 22.1,
    "air_humidity": 60.5,
    "air_temp": 24.3
}
```

sensor_id = string, just sensor_1 sensor_2 etc matching the plot number
soil_moisture = float, percentage 0-100
soil_temp = float, celsius
air_humidity = float, percentage 0-100
air_temp = float, celsius

no need to send a timestamp the pi adds it

sends back 200 with the data if it worked, 400 if youre missing fields

send every 5 min

## esp32 example code

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverUrl = "http://192.168.1.100:5000/api/data";
const char* sensorId = "sensor_1";

void sendData(float soilMoisture, float soilTemp, float airHumidity, float airTemp) {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverUrl);
        http.addHeader("Content-Type", "application/json");

        String json = "{";
        json += "\"sensor_id\":\"" + String(sensorId) + "\",";
        json += "\"soil_moisture\":" + String(soilMoisture, 1) + ",";
        json += "\"soil_temp\":" + String(soilTemp, 1) + ",";
        json += "\"air_humidity\":" + String(airHumidity, 1) + ",";
        json += "\"air_temp\":" + String(airTemp, 1);
        json += "}";

        int responseCode = http.POST(json);

        if (responseCode == 200) {
            Serial.println("Data sent ok");
        } else {
            Serial.println("Error: " + String(responseCode));
        }

        http.end();
    }
}
```

## endpoints

GET / = the webpage
POST /api/data = where esp32s send to
GET /api/data = all data as json
GET /api/latest = newest reading per sensor
