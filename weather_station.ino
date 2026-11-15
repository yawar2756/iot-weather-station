#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>
#include "config.h"

/* ================= HARDWARE CONFIG ================= */

// DHT11 Sensor
#define DHTPIN D4
#define DHTTYPE DHT11

// Precipitation Sensor
#define RAIN_PIN D6

// Wind Speed Anemometer
#define WIND_PIN D5

// Visibility/Light Sensor
#define VIS_PIN D2

/* ================= GLOBAL OBJECTS ================= */

DHT dht(DHTPIN, DHTTYPE);
unsigned long lastSend = 0;
volatile int windClicks = 0;

/* ================= INTERRUPT SERVICE ================= */

ICACHE_RAM_ATTR void countWind() {
  windClicks++;
}

/* ================= SYSTEM UTILITIES ================= */

void reconnectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.println("📡 Reconnecting WiFi...");
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
}

/* ================= SYSTEM SETUP ================= */

void setup() {
  Serial.begin(115200);
  Serial.println("\n🚀 GPCA WEATHER SYSTEM INITIALIZING");

  // Network Initialization
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Network Connected");

  // Sensor Initialization
  dht.begin();
  pinMode(RAIN_PIN, INPUT_PULLUP);
  pinMode(VIS_PIN, INPUT_PULLUP);
  pinMode(WIND_PIN, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(WIND_PIN), countWind, FALLING);
  Serial.println("✅ All Sensors Synchronized");
}

/* ================= MAIN PROCESSING LOOP ================= */

void loop() {
  reconnectWiFi();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ Network Failure");
    delay(2000);
    return;
  }

  if (millis() - lastSend >= DATA_INTERVAL) {

    // 🌡️ Temperature & Humidity
    float temp = dht.readTemperature();
    float humidity = dht.readHumidity();

    if (isnan(temp) || isnan(humidity)) {
      Serial.println("❌ Sensor Read Failure: DHT11");
      temp = -1;
      humidity = -1;
    }

    // 🌧️ Precipitation
    int rainRaw = digitalRead(RAIN_PIN);
    String rainStatus = (rainRaw == LOW) ? "Rain Detected" : "No Rain";
    int rainIntensity = (rainRaw == LOW) ? 150 : 0;

    // 🌬️ Wind Speed
    int clicks = windClicks;
    windClicks = 0;
    float windSpeed = (digitalRead(WIND_PIN) == HIGH && clicks == 0) ? -1 : (min(clicks * 2.4, 120.0));

    // 👁️ Visibility (LDR approximation)
    int ldrValue = digitalRead(VIS_PIN);
    float visibility = (ldrValue == HIGH) ? 25 : 90;
    String visibilityStatus = (ldrValue == HIGH) ? "Low" : "Good";

    // 📦 Data Packaging
    String json = "{";
    json += "\"temperature\":" + String(temp, 1) + ",";
    json += "\"humidity\":" + String(humidity, 1) + ",";
    json += "\"rain_value\":" + String(rainIntensity) + ",";
    json += "\"rain_status\":\"" + rainStatus + "\",";
    json += "\"wind_speed\":" + String(windSpeed, 1) + ",";
    json += "\"wind_direction\":\"North\",";
    json += "\"visibility\":" + String(visibility, 0) + ",";
    json += "\"visibility_status\":\"" + visibilityStatus + "\",";
    json += "\"device\":\"ESP8266\"";
    json += "}";

    // 📡 Cloud Transmission
    WiFiClientSecure client;
    client.setInsecure();
    HTTPClient http;

    if (http.begin(client, SERVER_URL)) {
      http.addHeader("Content-Type", "application/json");
      http.addHeader("x-api-key", API_KEY);

      int httpCode = http.POST(json);
      Serial.print("📡 HTTP Payload Sent. Response: ");
      Serial.println(httpCode);

      if (httpCode > 0) {
        String response = http.getString();
        Serial.println("✅ Response Received: " + response);
      } else {
        Serial.println("❌ Cloud Communication Error");
      }
      http.end();
    }

    Serial.println("--------------------------------");
    lastSend = millis();
  }
}
