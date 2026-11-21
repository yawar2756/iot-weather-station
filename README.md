# 🌦️ GPCA Smart Weather Station

> A professional IoT environmental monitoring platform built with **ESP32/ESP8266, Flask, PostgreSQL, and a modern Enterprise UI dashboard**.

The **GPCA Smart Weather Station** is an advanced IoT student project developed at **Government Polytechnic College Anantnag (GPCA)**. It continuously collects meteorological data from connected sensors, securely transmits JSON payloads over Wi-Fi, persists time-series data in PostgreSQL, and presents live analytics through a high-performance web dashboard.

---

## ✨ Key Features

* 🌡️ **Real-time Thermal Tracking:** Live temperature & humidity monitoring with min/max/avg statistical calculations.
* 🌧️ **Precipitation Detection:** Automated rain status detection and alerts.
* 💨 **Wind Dynamics:** Speed and direction measurement via custom interrupt-driven anemometer logic.
* 👁️ **Visibility Index:** Ambient light and visibility evaluation.
* 📊 **Interactive Analytics:** Dynamic Chart.js visualizations supporting 12-hour and 7-day trend analysis.
* 🔌 **Device Health Monitoring:** Automatic online/offline heartbeat detection (35s threshold).
* ⚠️ **Priority Alert System:** Automated warnings for extreme temperatures, storm conditions, and low visibility.
* 📥 **Data Export:** Instant CSV export of the last 7 days of historical telemetry.
* 🛡️ **Enterprise Security:** API key authentication and secure SSL database connections.

---

## 🏗️ System Architecture

```text
┌─────────────────────────┐
│    Environmental Sensors│
│  (DHT11, Rain, Wind, LDR)│
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│        ESP32/8266       │
│  Edge Processing & Wi-Fi│
└────────────┬────────────┘
             │ HTTP POST (JSON + API Key)
             ▼
┌─────────────────────────┐
│      Flask Backend      │
│  Validation & Alert Logic│
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│       PostgreSQL        │
│  Time-Series Persistence│
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     Web Dashboard       │
│  Chart.js & Live UI     │
└─────────────────────────┘
```

---

## 🔧 Hardware Specifications

| Component | Pin (ESP8266/ESP32) | Purpose |
| :--- | :--- | :--- |
| **DHT11** | D4 (GPIO2) | Temperature & Humidity |
| **Rain Sensor** | D6 (GPIO12) | Precipitation Detection |
| **Wind Anemometer** | D5 (GPIO14) | Wind Speed (Interrupt Counter) |
| **Visibility LDR** | D2 (GPIO4) | Ambient Light / Visibility |

---

## 💻 Tech Stack

- **Firmware:** C/C++ (Arduino IDE, ESP8266WiFi, DHT sensor library)
- **Backend:** Python, Flask, Psycopg2, Gunicorn
- **Database:** PostgreSQL (Cloud hosted)
- **Frontend:** HTML5, CSS3 (Enterprise Grid, Glassmorphism), JavaScript (ES6+), Chart.js
- **Deployment:** Render Platform

---

## 👨‍💻 Project Authors

**Yawar Nazir Sheikh & Muhammad Yaseen**  
Department of Computer Science Engineering  
**Government Polytechnic College Anantnag (GPCA)**

---

## 📜 License

Developed as an academic engineering project for educational and demonstration purposes.
