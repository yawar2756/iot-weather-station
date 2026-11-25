# 🌩️ GPCA Smart Weather Station

> Real-time IoT environmental monitoring for Government Polytechnic College Anantnag  
> *Engineered by Yawar Nazir Sheikh & Muhammad Yaseen — CSE Department*

---

<p align="center">
  <img src="https://img.shields.io/badge/ESP8266-Platform-000?style=for-the-badge&logo=espressif" alt="ESP8266" />
  <img src="https://img.shields.io/badge/Flask-Python-000?style=for-the-badge&logo=flask" alt="Flask" />
  <img src="https://img.shields.io/badge/PostgreSQL-Cloud-000?style=for-the-badge&logo=postgresql" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Chart.js-Realtime-000?style=for-the-badge&logo=chartdotjs" alt="Chart.js" />
  <img src="https://img.shields.io/badge/Render-Deploy-000?style=for-the-badge&logo=render" alt="Render" />
</p>

---

## 📸 Project Preview

| Live Dashboard | System Documentation | Weather Alerts |
|:---:|:---:|:---:|
| Realtime temperature & humidity charts with 12h / 7d views | Full IoT architecture documentation | Smart alert banners for Heat, Cold, Storm, Rain & Low Visibility |

---

## 🎯 About

The **GPCA Smart Weather Station** is a full-stack IoT project that captures meteorological data — temperature, humidity, rain detection, wind speed, and ambient light — using ESP8266 edge sensors, streams it securely over HTTPS to a Flask backend running on Render, and visualizes it through an elegant Chart.js dashboard.

Designed as an educational showcase at Government Polytechnic College Anantnag, it bridges edge hardware, cloud persistence, and responsive web presentation.

---

## ⚡ Key Features

- **🌡️ Real-Time Monitoring** — Live temperature, humidity, wind, rain, and light-level readings (the dashboard shows the last known values, dimmed, when the station is offline)
- **📊 Interactive Charts** — Chart.js temperature trends toggle between **12 Hours** and **7 Days**
- **🚨 Smart Alert System** — Heat, Cold, Storm Warning, Rain Alert, Low Visibility banners
- **📤 Data Export** — Download CSV reports of the last 7 days
- **🔐 Secure API** — HTTPS POST with `x-api-key` authentication
- **☁️ Cloud-Native** — Deployed on Render with PostgreSQL, gunicorn WSGI, and Procfile
- **📱 Mobile Ready** — PWA meta tags for installable web app experience
- **🔄 Auto Refresh** — Dashboard polls every 10s; charts refresh every 5 minutes

---

## 🛠️ Hardware Specification

| Component | Sensor | Pin |
|-----------|--------|-----|
| Microcontroller | ESP8266 Wi-Fi SoC | — |
| Temperature & Humidity | DHT11 | D4 |
| Precipitation | Rain Detection Module | D6 |
| Wind Speed | Anemometer Pulse Counter (GPIO Interrupt) | D5 |
| Light level | LDR module (digital: dark / bright) | D2 |

### Known sensor limits (read before trusting the numbers)

- **DHT11 reads 0–50 °C only (±2 °C, ±5 % RH).** It cannot report sub-zero temperatures. For Kashmir winters use a DHT22 or BME280.
- **Light level is not visibility.** The LDR module is a day/night switch (25 % / 90 %). Because of that, the "Low Visibility" alert is disabled unless you set `VISIBILITY_ALERT_ENABLED=1`.
- **Rain is wet / dry only.** The intensity value is a fixed placeholder, not a measurement.
- **Wind speed** assumes 2.4 km/h per pulse-per-second. Set `WIND_KMH_PER_HZ` in the firmware to match your anemometer's datasheet.
- **No wind vane**, so wind direction is not measured (shown as N/A).
- A sensor that is not fitted can be switched off with the `HAS_*` flags at the top of `weather_station.ino`. Missing data is sent as `null` and shown as `--`, never as a fake number.

All sensor data is packaged as JSON via ArduinoJson and transmitted securely over HTTPS with TLS certificate fingerprint validation to prevent MITM attacks.

---

## 📁 Repository Structure

```
iot-weather-station/
├── app.py                      # Flask backend (API, DB, seeding)
├── Procfile                    # Render WSGI entry point
├── weather_station.ino         # ESP8266 firmware
├── config.h                    # Placeholder template only (safe to commit)
├── config.private.h.example    # Copy to config.private.h and fill in secrets (git-ignored)
├── templates/
│   ├── index.html              # Landing page
│   ├── dashboard.html          # Live monitoring dashboard
│   └── about.html              # System architecture docs
├── static/
│   ├── css/
│   │   ├── main.css            # Shared design system
│   │   ├── index.css           # Landing page styles
│   │   ├── dashboard.css       # Dashboard styles
│   │   └── about.css           # Docs page styles
│   ├── js/
│   │   ├── dashboard.js        # Polling, rendering, chart
│   │   ├── index.js            # Landing page status badge
│   │   └── about.js            # Service worker registration
│   ├── favicon.png             # 128x128
│   ├── icon-192.png            # PWA icons
│   ├── icon-512.png
│   ├── manifest.json
│   └── service-worker.js       # Offline support (network-first for pages and API)
├── CHANGES.md                  # What changed in the v2 review pass
└── README.md                   # You are here
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL database (Render or local)
- ESP8266 (for hardware deployment)

### ESP8266 Hardware Setup

```bash
# 1. Copy the template and fill in YOUR values
cp config.private.h.example config.private.h
# 2. Edit config.private.h with your secrets
#    - API_KEY (must match Render env var)
#    - WIFI_SSID / WIFI_PASS
#    - SERVER_URL (your Render URL)
# 3. Open weather_station.ino in Arduino IDE / PlatformIO
# 4. Upload to ESP8266
```

⚠️ **Never commit `config.private.h`** — it's in `.gitignore` for your security.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Landing page |
| `GET` | `/dashboard` | Live monitoring dashboard |
| `GET` | `/about` | System documentation |
| `GET` | `/api/latest` | Latest sensor reading |
| `GET` | `/api/history?mode=hourly\|daily` | Chart history (12h / 7d) |
| `POST` | `/api/data` | Receive sensor data (ESP8266) |
| `GET` | `/api/export` | Download CSV (last 7 days) |
| `POST` | `/api/seed?live=1` | Insert a live demo reading (needs `ENABLE_SEED=1` + `x-api-key` header) |
| `POST` | `/api/seed?days=7` | Backfill 7 days of demo data (same requirements) |
| `DELETE` | `/api/seed` | Clear all demo rows (same requirements) |

---

## 🌤️ Testing Without Hardware

Demo seeding is **off by default**. To use it, set `ENABLE_SEED=1` on the server, then call it from your terminal (never paste your API key into a browser console or a URL):

```bash
# 7 days of demo history + one fresh reading
curl -X POST -H "x-api-key: $API_KEY" "https://YOUR-APP.onrender.com/api/seed?days=7"

# keep the dashboard "Online" with a fresh reading every 30 s
while true; do curl -s -X POST -H "x-api-key: $API_KEY" "https://YOUR-APP.onrender.com/api/seed?live=1"; sleep 30; done

# remove every demo row
curl -X DELETE -H "x-api-key: $API_KEY" "https://YOUR-APP.onrender.com/api/seed"
```

Demo rows are tagged `DEMO-SIM`, and the dashboard shows a **DEMO DATA** badge while the newest reading is a demo one. Turn `ENABLE_SEED` off again when the real station is running.

---

## ☁️ Deployment (Render)

1. Connect your GitHub repo to [Render](https://render.com)
2. Add environment variables:

   | Variable | Required | Purpose |
   |---|---|---|
   | `DATABASE_URL` | yes | PostgreSQL connection string |
   | `API_KEY` | yes | Shared secret the ESP8266 sends in `x-api-key` |
   | `ENABLE_SEED` | no | `1` enables the demo-data endpoints |
   | `RETENTION_DAYS` | no | Delete readings older than this (default 90, `0` = keep forever) |
   | `VISIBILITY_ALERT_ENABLED` | no | `1` re-enables the light-based "Low Visibility" alert |
3. Deploy using the included `Procfile`:
   ```
   web: gunicorn app:app --workers 1 --bind 0.0.0.0:${PORT:-8000}
   ```

   Render's free tier sleeps after ~15 minutes without traffic. Point a free uptime monitor (e.g. UptimeRobot) at `/ping` so the first visitor is not stuck waiting for a cold start.
4. Visit your Render URL and start monitoring

---

## 🤝 Contributors

<table>
  <tr>
    <td align="center"><b>Yawar Nazir Sheikh</b></td>
    <td align="center"><b>Muhammad Yaseen</b></td>
  </tr>
  <tr>
    <td>CSE Department</td>
    <td>CSE Department</td>
  </tr>
  <tr>
    <td>GPC Anantnag</td>
    <td>GPC Anantnag</td>
  </tr>
</table>

---

## 📄 License

© GPCA Smart Weather Station Project — Government Polytechnic College Anantnag. No open-source license has been chosen yet; add a `LICENSE` file if you want others to reuse the code.

---

<p align="center">
  Made with ⚡ and ☔ by IoT Lab @ GPCA
</p>
