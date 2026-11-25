#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>
#include <ArduinoJson.h>
// Secrets live in config.private.h (copy from config.private.h.example, never commit it)
#include "config.private.h"

/* ================= WHAT IS ACTUALLY WIRED UP =================
   Set a sensor to 0 if it is not connected. The firmware then sends null for it
   and the dashboard shows "--" instead of a made-up value. */
#define HAS_DHT          1
#define HAS_RAIN         1
#define HAS_ANEMOMETER   1
#define HAS_LIGHT_SENSOR 1

/* ================= HARDWARE CONFIG ================= */

// DHT11: only reads 0..50 °C (±2 °C) and 20..80 %RH (±5 %). Below 0 °C it cannot report.
// For Kashmir winters use a DHT22 (-40..80 °C) or BME280 and change DHTTYPE.
#define DHTPIN D4
#define DHTTYPE DHT11

#define RAIN_PIN D6   // digital rain module (wet = LOW)
#define WIND_PIN D5   // anemometer reed switch / pulse output
#define LIGHT_PIN D2  // LDR module digital output (day/night switch, NOT visibility)

// Pulses per second -> km/h. 2.4 km/h per 1 Hz is the common cup-anemometer
// calibration. CHECK YOUR SENSOR'S DATASHEET and change this if it differs.
const float WIND_KMH_PER_HZ = 2.4;
const unsigned long WIND_DEBOUNCE_MS = 15;

// If the server cannot be reached this many times in a row, reboot and rejoin WiFi.
const int MAX_CONSECUTIVE_FAILURES = 10;
const unsigned long WIFI_TIMEOUT_MS = 30000;

/* ================= TLS =================
   ESP8266 setFingerprint() takes the SHA-1 fingerprint of the server certificate:
     openssl s_client -connect gpca-weather-station.onrender.com:443 </dev/null 2>/dev/null \
       | openssl x509 -fingerprint -sha1 -noout
   Hosting providers renew certificates regularly, which changes the fingerprint.
   When posts start failing with a negative HTTP code, regenerate this value and re-flash.
   (Compile with -DALLOW_INSECURE_TLS only for debugging: it skips verification and
   exposes your API key to anyone on the network path.) */
const char* SERVER_FINGERPRINT = "E9:9F:6E:AF:76:CB:E6:75:50:AE:DF:2B:CC:F1:AA:9E:3C:41:E9:96";

/* ================= GLOBAL STATE ================= */

DHT dht(DHTPIN, DHTTYPE);
unsigned long lastSend = 0;
unsigned long windWindowStart = 0;
int consecutiveFailures = 0;

volatile uint32_t windClicks = 0;
volatile unsigned long lastClickMs = 0;

/* ================= INTERRUPT SERVICE ================= */

ICACHE_RAM_ATTR void countWind() {
  unsigned long now = millis();
  if (now - lastClickMs > WIND_DEBOUNCE_MS) {   // ignore reed-switch bounce
    windClicks++;
    lastClickMs = now;
  }
}

/* ================= SYSTEM UTILITIES ================= */

bool connectWiFi(unsigned long timeoutMs) {
  if (WiFi.status() == WL_CONNECTED) return true;

  Serial.println("📡 Connecting WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < timeoutMs) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  return WiFi.status() == WL_CONNECTED;
}

void noteFailure(const char* why) {
  consecutiveFailures++;
  Serial.printf("⚠️ %s (%d/%d)\n", why, consecutiveFailures, MAX_CONSECUTIVE_FAILURES);
  if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
    Serial.println("🔁 Too many failures, restarting");
    delay(200);
    ESP.restart();
  }
}

/* ================= SYSTEM SETUP ================= */

void setup() {
  Serial.begin(115200);
  Serial.println("\n🚀 GPCA WEATHER SYSTEM INITIALIZING");

  if (!connectWiFi(WIFI_TIMEOUT_MS)) {
    Serial.println("❌ WiFi not available, restarting");
    delay(1000);
    ESP.restart();
  }
  Serial.println("✅ Network Connected");

#if HAS_DHT
  dht.begin();
#endif
#if HAS_RAIN
  pinMode(RAIN_PIN, INPUT_PULLUP);
#endif
#if HAS_LIGHT_SENSOR
  pinMode(LIGHT_PIN, INPUT_PULLUP);
#endif
#if HAS_ANEMOMETER
  pinMode(WIND_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(WIND_PIN), countWind, FALLING);
#endif

  windWindowStart = millis();
  Serial.println("✅ Sensors ready");
}

/* ================= MAIN LOOP ================= */

void loop() {
  if (!connectWiFi(10000)) {
    noteFailure("WiFi down");
    delay(2000);
    return;
  }

  if (millis() - lastSend < DATA_INTERVAL) {
    delay(50);
    return;
  }
  lastSend = millis();

  StaticJsonDocument<320> doc;

  // 🌡️ Temperature & humidity: null when the sensor fails (never a fake number)
#if HAS_DHT
  float temp = dht.readTemperature();
  float humidity = dht.readHumidity();
  if (isnan(temp)) doc["temperature"] = nullptr; else doc["temperature"] = temp;
  if (isnan(humidity)) doc["humidity"] = nullptr; else doc["humidity"] = humidity;
  if (isnan(temp) || isnan(humidity)) Serial.println("❌ DHT read failed");
#else
  doc["temperature"] = nullptr;
  doc["humidity"] = nullptr;
#endif

  // 🌧️ Precipitation (digital module: wet / dry only, no real intensity)
#if HAS_RAIN
  bool raining = (digitalRead(RAIN_PIN) == LOW);
  doc["rain_status"] = raining ? "Rain Detected" : "No Rain";
  doc["rain_value"] = raining ? 150 : 0;
#else
  doc["rain_status"] = nullptr;
  doc["rain_value"] = nullptr;
#endif

  // 🌬️ Wind: pulses counted over the real elapsed window, converted to km/h. Calm = 0.
#if HAS_ANEMOMETER
  noInterrupts();
  uint32_t clicks = windClicks;
  windClicks = 0;
  interrupts();
  unsigned long now = millis();
  float seconds = (now - windWindowStart) / 1000.0f;
  windWindowStart = now;
  float windKmh = (seconds > 0) ? (clicks / seconds) * WIND_KMH_PER_HZ : 0;
  doc["wind_speed"] = windKmh;
#else
  doc["wind_speed"] = nullptr;
#endif
  doc["wind_direction"] = nullptr;   // no wind vane fitted

  // 💡 Light level (LDR module): 25 = dark, 90 = bright. Sent in the "visibility" field.
#if HAS_LIGHT_SENSOR
  doc["visibility"] = (digitalRead(LIGHT_PIN) == HIGH) ? 25 : 90;
#else
  doc["visibility"] = nullptr;
#endif

  doc["device"] = DEVICE_ID;

  String json;
  serializeJson(doc, json);

  // 📡 Cloud transmission
  WiFiClientSecure client;
#ifdef ALLOW_INSECURE_TLS
  client.setInsecure();
#else
  client.setFingerprint(SERVER_FINGERPRINT);
#endif
  HTTPClient http;
  http.setTimeout(20000);   // free hosting can take 30-60 s to wake from sleep

  if (!http.begin(client, SERVER_URL)) {
    noteFailure("HTTP begin failed");
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-api-key", API_KEY);

  int httpCode = http.POST(json);
  Serial.printf("📡 POST -> %d\n", httpCode);

  if (httpCode == 200) {
    consecutiveFailures = 0;
  } else if (httpCode == 401) {
    Serial.println("🔑 API key rejected: check API_KEY in config.private.h and on the server");
    consecutiveFailures = 0;   // rebooting will not fix a wrong key
  } else if (httpCode < 0) {
    Serial.printf("❌ %s (if TLS: the certificate fingerprint may have changed)\n",
                  http.errorToString(httpCode).c_str());
    noteFailure("Cannot reach server");
  } else {
    noteFailure("Server error");
  }
  http.end();
  Serial.println("--------------------------------");
}
