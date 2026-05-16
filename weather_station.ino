#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>

/* ================= PINS ================= */

// DHT11
#define DHTPIN 2          // D4
#define DHTTYPE DHT11

// Rain Sensor
#define RAIN_PIN 12       // D6

// Wind Sensor
#define WIND_PIN 14       // D5

// LDR MODULE (DIGITAL PIN)
#define VIS_PIN 13        // D7

/* ================= WIFI ================= */

const char* ssid = "R";
const char* password = "111111000";

/* ================= SERVER ================= */

const char* serverUrl =
"https://gpca-weather-station.onrender.com/api/data";

const char* apiKey =
"gpcaweatherstation25";

/* ================= SENSOR ================= */

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

  Serial.println();
  Serial.println("🚀 SYSTEM STARTING");

  /* WIFI */

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("✅ WiFi Connected");

  /* DHT */

  dht.begin();

  delay(2000);

  /* RAIN */

  pinMode(RAIN_PIN, INPUT_PULLUP);

  /* LDR */

  pinMode(VIS_PIN, INPUT);

  /* WIND */

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

    int rainHits = 0;

    for (int i = 0; i < 15; i++) {

      if (digitalRead(RAIN_PIN) == LOW) {
        rainHits++;
      }

      delay(15);
    }

    String rainStatus;

    if (rainHits >= 10) {
      rainStatus = "Rain Detected";
    }
    else {
      rainStatus = digitalRead(RAIN_PIN) == HIGH
      ? "No Rain"
      : "Rain Detected";
    }

    int rainIntensity =
      (rainStatus == "Rain Detected")
      ? 150
      : 0;

    Serial.print("🌧 Rain Status: ");
    Serial.println(rainStatus);

    /* ================= WIND ================= */

    int clicks = windClicks;

    windClicks = 0;

    float windSpeed;

    if(clicks < 0){
      windSpeed = -1;
    }
    else{
      windSpeed = min(clicks * 2.4, 120.0);
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
