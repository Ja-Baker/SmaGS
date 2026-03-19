//By: Aidan Engbert
//3/19/2026
#include <WiFi.h>
#include <WiFiMulti.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "DHT.h"
#include <Wire.h>
#include "SHT31.h"
#include "secrets.h"

#define DHTPIN 4
#define DHTTYPE DHT11
#define SOIL_PIN 34
#define RED_LED 12    
#define GREEN_LED 13  
#define BLUE_LED 14  
#define DRY_THRESHOLD 30.0 

WiFiMulti wifiMulti;
DHT dht(DHTPIN, DHTTYPE);
SHT31 sht(0x44);
const char* serverUrl = SECRET_SERVER_URL;
unsigned long lastConnectionTime = 0;
const unsigned long postingInterval = 60000;
float last_soil_moisture, last_soil_temp, last_air_humidity, last_air_temp;

void setup() {
  Serial.begin(115200);
  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(BLUE_LED, OUTPUT);
  dht.begin();
  Wire.begin(); 
  sht.begin();
  wifiMulti.addAP(SSID_1, PASS_1);
  wifiMulti.addAP(SSID_2, PASS_2);
  connectToWiFi();
}

void connectToWiFi() {
  Serial.println("Scanning for known WiFi networks...");
  if (wifiMulti.run() == WL_CONNECTED) {
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(RED_LED, LOW);
    Serial.print("Connected to: ");
    Serial.println(WiFi.SSID());
  } else {
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, HIGH);
    Serial.println("No known networks found.");
  }
}

void loop() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  sht.read();
  float soil_temp_val = sht.getTemperature();
  int soil_raw = analogRead(SOIL_PIN);
  float soil_moist_val = map(soil_raw, 4095, 0, 0, 100);
  if (isnan(h) || isnan(t) || soil_temp_val < -40) {
    digitalWrite(RED_LED, HIGH);
  } else {
    digitalWrite(RED_LED, LOW); 
  }
  if (soil_moist_val < DRY_THRESHOLD) {
    digitalWrite(BLUE_LED, HIGH);
  } else {
    digitalWrite(BLUE_LED, LOW);
  }
  if (millis() - lastConnectionTime > postingInterval) {
    last_air_humidity = h;
    last_air_temp = t;
    last_soil_moisture = soil_moist_val;
    last_soil_temp = soil_temp_val;
    sendData();
    lastConnectionTime = millis();
  }
}

void sendData() {
  if (wifiMulti.run() == WL_CONNECTED) {
    digitalWrite(GREEN_LED, HIGH);
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    StaticJsonDocument<256> doc;
    doc["mac_address"] = WiFi.macAddress();
    doc["soil_moisture"] = last_soil_moisture;
    doc["soil_temp"] = last_soil_temp;
    doc["air_humidity"] = last_air_humidity;
    doc["air_temp"] = last_air_temp;
    String jsonString;
    serializeJson(doc, jsonString);
    int httpResponseCode = http.POST(jsonString);
    if (httpResponseCode > 0) {
      Serial.print("Data Sent. Server Response: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Send Error: ");
      Serial.println(httpResponseCode);
      digitalWrite(RED_LED, HIGH);
    }
    http.end();
  } else {
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, HIGH);
    connectToWiFi();
  }
}