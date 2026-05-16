#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>

/* ================= PINS ================= */

// DHT11
#define DHTPIN D4
#define DHTTYPE DHT11

// Rain Sensor
#define RAIN_PIN D6

// Wind Sensor
#define WIND_PIN D5

// LDR MODULE
#define VIS_PIN D2

/* ================= WIFI ================= */

const char* ssid = "R";
const char* password = "111111000";

/* ================= SERVER ================= */

const char* serverUrl =
"https://gpca-weather-station.onrender.com/api/data";

const char* apiKey =
"gpcaweatherstation25";

/* ================= DHT ================= */

DHT dht(DHTPIN, DHTTYPE);

/* ================= TIMER ================= */

unsigned long lastSend = 0;
const long interval = 12000;

/* ================= WIND ================= */

volatile int windClicks = 0;

ICACHE_RAM_ATTR void countWind() {
  windClicks++;
}

/* ================= WIFI RECONNECT ================= */

void reconnectWiFi() {

  if (WiFi.status() == WL_CONNECTED)
    return;

  Serial.println("📡 Reconnecting WiFi...");

  WiFi.disconnect();
  WiFi.begin(ssid, password);

  unsigned long start = millis();

  while (
    WiFi.status() != WL_CONNECTED &&
    millis() - start < 10000
  ) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();
}

/* ================= SETUP ================= */

void setup() {

  Serial.begin(115200);

  Serial.println("\n🚀 SYSTEM STARTING");

  /* WIFI */

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
    Serial.print(".");
  }

  Serial.println("\n✅ WiFi Connected");

  /* DHT */

  dht.begin();
  delay(2000);

  /* SENSOR MODES */

  pinMode(RAIN_PIN, INPUT_PULLUP);

  pinMode(VIS_PIN, INPUT_PULLUP);

  pinMode(WIND_PIN, INPUT_PULLUP);

  attachInterrupt(
    digitalPinToInterrupt(WIND_PIN),
    countWind,
    FALLING
  );

  Serial.println("✅ ALL SENSORS READY");
}

/* ================= LOOP ================= */

void loop() {

  reconnectWiFi();

  if (WiFi.status() != WL_CONNECTED) {

    Serial.println("❌ WiFi Failed");

    delay(2000);
    return;
  }

  if (millis() - lastSend >= interval) {

    /* ================= DHT ================= */

    float temp = NAN;
    float humidity = NAN;

    for (int i = 0; i < 3; i++) {

      temp = dht.readTemperature();
      humidity = dht.readHumidity();

      if (!isnan(temp) && !isnan(humidity)) {
        break;
      }

      delay(1000);
    }

    bool dhtConnected = true;

    if (isnan(temp) || isnan(humidity)) {

      Serial.println("❌ DHT NOT CONNECTED");

      temp = -1;
      humidity = -1;

      dhtConnected = false;
    }

    Serial.print("🌡 Temp: ");
    Serial.println(temp);

    Serial.print("💧 Humidity: ");
    Serial.println(humidity);

    /* ================= RAIN ================= */

    int rainRaw = digitalRead(RAIN_PIN);
    
    String rainStatus;
    int rainIntensity;
    
    // WATER DETECTED
    if (rainRaw == LOW) {
    
      rainStatus = "Rain Detected";
      rainIntensity = 150;
    }
    
    // NORMAL
    else {
    
      rainStatus = "No Rain";
      rainIntensity = 0;
    }
    
    Serial.print("🌧 Rain: ");
    Serial.println(rainStatus);

    /* ================= WIND ================= */

    int clicks = windClicks;

    windClicks = 0;

    float windSpeed;

    // disconnected
    if (
      digitalRead(WIND_PIN) == HIGH &&
      clicks == 0
    ) {

      windSpeed = -1;
    }

    // connected
    else {

      windSpeed =
        min(clicks * 2.4, 120.0);
    }

    Serial.print("🌬 Wind Speed: ");
    Serial.println(windSpeed);

    /* ================= LDR DIGITAL ================= */

    int ldrValue = digitalRead(VIS_PIN);
    
    Serial.print("LDR Raw Value: ");
    Serial.println(ldrValue);
    
    float visibility;
    String visibilityStatus;
    
    // COVERED / DARK
    if (ldrValue == HIGH) {
    
      visibility = 25;
      visibilityStatus = "Low";
    }
    
    // BRIGHT
    else {
    
      visibility = 90;
      visibilityStatus = "Good";
    }
    
    Serial.print("👀 Visibility: ");
    Serial.println(visibility);
    
    Serial.print("💡 Visibility Status: ");
    Serial.println(visibilityStatus);

    /* ================= JSON ================= */

    String json = "{";

    json += "\"temperature\":" +
            String(temp, 1) + ",";

    json += "\"humidity\":" +
            String(humidity, 1) + ",";

    json += "\"rain_value\":" +
            String(rainIntensity) + ",";

    json += "\"rain_status\":\"" +
            rainStatus + "\",";

    json += "\"wind_speed\":" +
            String(windSpeed, 1) + ",";

    json += "\"wind_direction\":\"North\",";

    json += "\"visibility\":" +
            String(visibility, 0) + ",";

    json += "\"visibility_status\":\"" +
            visibilityStatus + "\",";

    json += "\"device\":\"ESP8266\"";

    json += "}";

    Serial.println("📦 JSON:");
    Serial.println(json);

    /* ================= SEND ================= */

    WiFiClientSecure client;

    client.setInsecure();

    HTTPClient http;

    if (http.begin(client, serverUrl)) {

      http.addHeader(
        "Content-Type",
        "application/json"
      );

      http.addHeader(
        "x-api-key",
        apiKey
      );

      int httpCode = http.POST(json);

      Serial.print("📡 HTTP Response: ");
      Serial.println(httpCode);

      if (httpCode > 0) {

        String response = http.getString();

        Serial.println("✅ Server Response:");
        Serial.println(response);
      }
      else {

        Serial.println("❌ POST FAILED");
      }

      http.end();
    }

    Serial.println("--------------------------------");

    lastSend = millis();
  }
}
