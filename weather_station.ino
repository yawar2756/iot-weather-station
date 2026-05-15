#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>

/* ========= PINS ========= */
#define DHTPIN 2
#define DHTTYPE DHT11

#define RAIN_PIN 12       // D6 (DIGITAL)
#define VIS_PIN A0        // ANALOG
#define WIND_PIN 14       // D5

/* ========= WIFI ========= */
const char* ssid = "R";
const char* password = "111111000";

/* ========= SERVER ========= */
const char* serverUrl = "https://gpca-weather-station.onrender.com/api/data";
const char* apiKey = "gpcaweatherstation25";

/* ========= SENSOR ========= */
DHT dht(DHTPIN, DHTTYPE);

/* ========= TIMER ========= */
unsigned long lastSend = 0;
const long interval = 10000;

/* ========= WIND COUNT ========= */
volatile int windClicks = 0;

ICACHE_RAM_ATTR void countWind() {
  windClicks++;
}

/* ========= WIFI RECONNECT ========= */
void reconnectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.println("Reconnecting WiFi...");
  WiFi.disconnect();
  WiFi.begin(ssid, password);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(500);
    Serial.print(".");
  }
}

/* ========= SETUP ========= */
void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  WiFi.begin(ssid, password);

  unsigned long startAttempt = millis();
  
  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 10000) {
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\n❌ WiFi Failed, restarting...");
    ESP.restart();
  }
  
  Serial.println("\nWiFi CONNECTED");

  Serial.println("\nWiFi CONNECTED");

  dht.begin();

  pinMode(RAIN_PIN, INPUT_PULLUP);           // DIGITAL rain
  pinMode(WIND_PIN, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(WIND_PIN), countWind, FALLING);
}

/* ========= LOOP ========= */
void loop() {

  reconnectWiFi();
  if (WiFi.status() != WL_CONNECTED) return;

  if (millis() - lastSend >= interval) {

    /* ========= TEMP ========= */
    float temp = dht.readTemperature();
    float humidity = dht.readHumidity();

    if (isnan(temp) || isnan(humidity)) {
      Serial.println("❌ DHT Read Failed");
      return;
    }

    if (temp < -40 || temp > 80) {
      Serial.println("❌ Invalid temperature");
      return;
    }

    Serial.print("Temp: "); Serial.println(temp);
    Serial.print("Humidity: "); Serial.println(humidity);

    /* ========= RAIN (DIGITAL) ========= */
    int rainHits = 0;

    for(int i=0;i<5;i++){
    
      if(digitalRead(RAIN_PIN)==LOW){
        rainHits++;
      }
    
      delay(20);
    }
    
    String rainStatus;
    
    if(rainHits >= 3){
      rainStatus = "Rain Detected";
    }
    else{
      rainStatus = "No Rain";
    }

    Serial.print("Rain Hits: ");
    Serial.println(rainHits);
    
    Serial.print("Rain Status: ");
    Serial.println(rainStatus);
    /* ========= VISIBILITY ========= */
    int visRaw1 = analogRead(VIS_PIN);
    delay(10);
    int visRaw2 = analogRead(VIS_PIN);

    Serial.print("VIS RAW1: ");
    Serial.print(visRaw1);
    Serial.print("  VIS RAW2: ");
    Serial.println(visRaw2);
    
    int visibility;
    
    // 🔥 detect floating (unstable signal)
    if (abs(visRaw1 - visRaw2) > 50) {
      visibility = 101;
    }
    else if (visRaw1 < 10 || visRaw1 > 1010) {
      visibility = 101;
    }
    else {
      visibility = map(visRaw1, 0, 1023, 0, 100);
    }

    Serial.print("Visibility Final: ");
    Serial.println(visibility);

    /* ========= WIND ========= */
    noInterrupts();
    int clicks = windClicks;
    windClicks = 0;
    interrupts();

    float windSpeed;

    if (clicks == 0) {
      windSpeed = 0;   // assume no wind
    } else if (clicks > 1000) {
      windSpeed = 0;   // noise protection
    } else {
      windSpeed = min(clicks * 2.4, 120.0);
    }

    /* ========= JSON ========= */
    String json = "{";
    json += "\"temperature\":" + String(temp,1) + ",";
    json += "\"humidity\":" + String(humidity,1) + ",";
    int rainIntensity = (rainStatus == "Rain Detected") ? 150 : 0;

    json += "\"rain_value\":" + String(rainIntensity) + ",";
    json += "\"rain_status\":\"" + rainStatus + "\",";
    json += "\"wind_speed\":" + String(windSpeed,1) + ",";
    json += "\"wind_direction\":null,";
    json += "\"visibility\":" + String(visibility) + ",";
    json += "\"visibility_status\":\"" + String(visibility == 101 ? "Not Connected" : "OK") + "\",";
    json += "\"device\":\"ESP8266\"";
    json += "}";

    Serial.println(json);

    /* ========= SEND ========= */
    WiFiClientSecure client;
    client.setInsecure();
    HTTPClient http;

    if (http.begin(client, serverUrl)) {

      Serial.println("Sending data...");   // 👈 PUT HERE
    
      http.addHeader("Content-Type", "application/json");
      http.addHeader("x-api-key", apiKey);
    
      lastSend = millis();
    
      int code = http.POST(json);
    
      Serial.print("HTTP CODE: ");
      Serial.println(code);
    
      http.end();
    }
  }
}
