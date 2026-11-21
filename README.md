# 🌩️ GPCA Smart Weather Station

> Real-time IoT environmental monitoring for Government Polytechnic College Anantnag  
> *Engineered by Yawar Nazir Sheikh & Muhammad Yaseen — CSE Department*

---

<p align="center">
  <img src="https://img.shields.io/badge/ESP8266-ESP32-000?style=for-the-badge&logo=espressif" alt="ESP8266/ESP32" />
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

The **GPCA Smart Weather Station** is a full-stack IoT project that captures real-time meteorological data — temperature, humidity, rainfall, wind speed, wind direction, and visibility — using ESP8266/ESP32 edge sensors, streams it securely over HTTPS to a Flask backend running on Render, and visualizes it through an elegant Chart.js dashboard.

Designed as an educational showcase at Government Polytechnic College Anantnag, it bridges edge hardware, cloud persistence, and responsive web presentation in one production-ready package.

---

## ⚡ Key Features

- **🌡️ Real-Time Monitoring** — Live temperature, humidity, wind, rain, and visibility readings
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
| Microcontroller | ESP8266 / ESP32 Wi-Fi SoC | — |
| Temperature & Humidity | DHT11 | D4 |
| Precipitation | Rain Detection Module | D6 |
| Wind Speed | Anemometer Pulse Counter (GPIO Interrupt) | D5 |
| Visibility / Light | LDR Photocell | D2 |

All sensor data is packaged as JSON via ArduinoJson and transmitted securely over HTTPS with TLS certificate fingerprint validation to prevent MITM attacks.

---

## 📁 Repository Structure

```
iot-weather-station/
├── app.py                      # Flask backend (API, DB, seeding)
├── Procfile                    # Render WSGI entry point
├── weather_station.ino         # ESP8266 firmware
├── config.h                    # WiFi, API keys, server URL (keep private)
├── templates/
│   ├── index.html              # Landing page
│   ├── dashboard.html          # Live monitoring dashboard
│   └── about.html              # System architecture docs
├── static/
│   ├── css/main.css            # Styles
│   ├── favicon.png
│   ├── manifest.json
│   └── service-worker.js       # PWA support
└── README.md                   # You are here
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL database (Render or local)
- ESP8266/ESP32 (for hardware deployment)

### Local Development (Flask Server)

```bash
# Clone the repository
git clone https://github.com/yawar2756/iot-weather-station.git
cd iot-weather-station

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="your-postgres-url"
export API_KEY="your-api-key-here"

# Run the server
python app.py
```

Visit `http://localhost:5000` to see the app.

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
| `POST` | `/api/seed?key=...&live=1` | Insert live demo reading |
| `POST` | `/api/seed?key=...&days=7` | Backfill 7 days of demo data |
| `DELETE` | `/api/seed?key=...` | Clear all demo rows |

---

## 🌤️ Testing Without Hardware

Don't have an ESP8266 handy? Simulate live weather data from your browser console:

```javascript
(async () => {
  // 🔑 Replace with your own Render API key
  const KEY = 'YOUR_API_KEY';   // ← set your own key from environment

  const API = 'https://your-render-url.com/api/seed';

  const summon = async () => {
    const r = await fetch(`${API}?key=${KEY}&live=1`, {
      method: 'POST',
      headers: { 'x-api-key': KEY }
    });
    console.log('🌦️ Weather refreshed:', await r.json());
  };

  setInterval(() => summon(), 30000);
  console.log('☔ Weather oracle active — updating every 30s');
})();
```

Paste into DevTools (F12 → Console) on your dashboard page and watch values change in real time.

---

## ☁️ Deployment (Render)

1. Connect your GitHub repo to [Render](https://render.com)
2. Add environment variables: `DATABASE_URL`, `API_KEY`
3. Deploy using the included `Procfile`:
   ```
   web: gunicorn app:app --workers 1 --bind 0.0.0.0:8000
   ```
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
    <td>GPCA Anantnag</td>
    <td>GPCA Anantnag</td>
  </tr>
</table>

---

## 📄 License

© 2024 GPCA Smart Weather Station Project — Government Polytechnic College Anantnag

---

<p align="center">
  Made with ⚡ and ☔ by IoT Lab @ GPCA
</p>