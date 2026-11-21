#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>
#include <ArduinoJson.h>
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

// SHA-256 Fingerprint for gpca-weather-station.onrender.com
// Get this from: openssl s_client -connect gpca-weather-station.onrender.com:443 < /dev/null 2>/dev/null | openssl x509 -fingerprint -sha256 -noout -in /dev/stdin
const char* SERVER_FINGERPRINT = "E9:9F:6E:AF:76:CB:E6:75:50:AE:DF:2B:CC:F1:AA:9E:3C:41:E9:96";

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

    // 📦 Data Packaging with ArduinoJson (robust serialization)
    StaticJsonDocument<256> doc;
    doc["temperature"] = temp;
    doc["humidity"] = humidity;
    doc["rain_value"] = rainIntensity;
    doc["rain_status"] = rainStatus;
    doc["wind_speed"] = windSpeed;
    doc["wind_direction"] = "North";
    doc["visibility"] = visibility;
    doc["visibility_status"] = visibilityStatus;
    doc["device"] = DEVICE_ID;  // From config.h for multi-station support

    String json;
    serializeJson(doc, json);

    // 📡 Cloud Transmission (SECURE: Certificate Fingerprint Validation)
    WiFiClientSecure client;
    client.setFingerprint(SERVER_FINGERPRINT);  // Validates server identity - prevents MITM
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

        // Optional: parse server response for dynamic config (e.g., new interval)
        if (httpCode == 200) {
          StaticJsonDocument<128> respDoc;
          deserializeJson(respDoc, response);
          if (respDoc.containsKey("interval")) {
            // Future: dynamic interval adjustment from server
          }
        }
      } else {
        Serial.printf("❌ Cloud Communication Error: %s\n", http.errorToString(httpCode).c_str());
      }
      http.end();
    } else {
      Serial.println("❌ HTTP Begin Failed");
    }

    Serial.println("--------------------------------");
    lastSend = millis();
  }
}
