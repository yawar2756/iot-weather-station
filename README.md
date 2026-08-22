# 🌦️ GPCA Smart Weather Station

> A real-time IoT weather monitoring system built with **ESP8266, environmental sensors, Flask, PostgreSQL, and a web dashboard**.

The **GPCA Smart Weather Station** collects environmental data from connected sensors, sends it to a cloud-based backend, stores historical readings, and presents the information through a responsive web dashboard.

---

## ✨ Features

* 🌡️ Real-time temperature monitoring
* 💧 Humidity monitoring
* 🌧️ Rain detection
* 💨 Wind monitoring
* 👁️ Visibility monitoring
* 📊 Real-time weather dashboard
* 📈 Historical weather analytics
* 🕐 Last 12 hours and last 7 days data
* 🔌 Device online/offline detection
* ⚠️ Weather condition alerts
* 📥 Historical data export
* 🔐 API key authentication
* 🛡️ API rate limiting
* 🗄️ PostgreSQL database
* 🌐 REST API

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │   Weather Sensors   │
                    │                     │
                    │ DHT11               │
                    │ Rain Sensor         │
                    │ Wind Sensor         │
                    │ Visibility Sensor   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      ESP8266        │
                    │                     │
                    │ Sensor Processing   │
                    │ Wi-Fi Communication │
                    └──────────┬──────────┘
                               │
                         HTTP / REST API
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Flask Backend    │
                    │                     │
                    │ REST API            │
                    │ Authentication      │
                    │ Rate Limiting       │
                    │ Data Processing     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     PostgreSQL      │
                    │                     │
                    │ Weather Readings    │
                    │ Historical Data     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Web Dashboard     │
                    │                     │
                    │ Live Data           │
                    │ Charts              │
                    │ Alerts              │
                    │ Analytics           │
                    └─────────────────────┘
```

---

## 🔧 Hardware

| Component               | Purpose                                |
| ----------------------- | -------------------------------------- |
| ESP8266                 | IoT controller and Wi-Fi communication |
| DHT11                   | Temperature and humidity               |
| Rain Sensor             | Rain detection                         |
| Wind Speed Sensor       | Wind measurement                       |
| LDR / Visibility Sensor | Visibility estimation                  |

### Pin Configuration

| Component         | ESP8266 Pin |
| ----------------- | ----------- |
| DHT11             | D4 / GPIO2  |
| Rain Sensor       | D6 / GPIO12 |
| Visibility Sensor | A0          |
| Wind Sensor       | D5 / GPIO14 |

> Pin configuration should match the hardware version being used for the deployment.

---

## 💻 Software Stack

### Hardware / Firmware

* ESP8266
* Arduino IDE
* C/C++
* DHT11 library
* Wi-Fi networking

### Backend

* Python
* Flask
* REST API
* PostgreSQL
* psycopg2
* Flask-Limiter

### Frontend

* HTML5
* CSS3
* JavaScript
* Chart.js

### Infrastructure

* PostgreSQL / Supabase
* Cloud deployment
* Git & GitHub

---

## 🔄 Data Flow

```text
Sensors
   ↓
ESP8266
   ↓
Collect sensor readings
   ↓
Create JSON payload
   ↓
POST /api/data
   ↓
Flask API
   ↓
Validate + process data
   ↓
PostgreSQL
   ↓
Dashboard API
   ↓
Charts + live weather information
```

---

## 🔌 API

The backend provides REST endpoints for sending and retrieving weather data.

| Endpoint       | Method | Purpose                     |
| -------------- | ------ | --------------------------- |
| `/api/data`    | POST   | Receive sensor readings     |
| `/api/latest`  | GET    | Get latest weather data     |
| `/api/history` | GET    | Get historical weather data |
| `/api/export`  | GET    | Export weather data         |
| `/api/ping`    | GET    | API connectivity check      |
| `/health`      | GET    | Backend health check        |

### Example Sensor Payload

```json
{
  "temperature": 24.5,
  "humidity": 68,
  "rain": false,
  "wind_speed": 2.4,
  "visibility": "Good"
}
```

---

## 📊 Dashboard

The dashboard provides a real-time view of the weather station.

### Dashboard capabilities

* Current weather conditions
* Sensor status
* Device status
* Temperature and humidity
* Historical charts
* Weather alerts
* Live updates
* Statistical summaries
* Data export

### Screenshots

> Add your best dashboard screenshot here.

```text
docs/images/dashboard.png
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/yawar2756/iot-weather-station.git
cd iot-weather-station
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
DATABASE_URL=your_postgresql_connection_string
API_KEY=your_api_key
SECRET_KEY=your_secret_key
```

> Never commit real credentials, API keys, passwords, or database connection strings to GitHub.

### 5. Run the application

```bash
python app.py
```

The application should then be available on the local server configured by the Flask application.

---

## 🔐 Security

The project includes several backend security measures:

* API key authentication
* API rate limiting
* Environment-based configuration
* PostgreSQL SSL connection
* Separation of secrets from source code

Sensitive credentials should always be stored as environment variables.

---

## 📁 Project Structure

```text
iot-weather-station/
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│   ├── index.html
│   ├── dashboard.html
│   └── about.html
│
├── app.py
├── requirements.txt
├── weather_station.ino
├── robots.txt
├── sitemap.xml
└── README.md
```

---

## 🎯 Project Objectives

The main objectives of the project are:

1. Collect real-time environmental data using IoT sensors.
2. Transmit sensor readings through an ESP8266.
3. Process and store weather data using a cloud backend.
4. Provide a real-time web-based monitoring dashboard.
5. Maintain historical weather records.
6. Detect device and sensor availability.
7. Provide useful weather analytics from collected data.

---

## ⚠️ Limitations

* Sensor accuracy depends on the quality and calibration of the hardware.
* DHT11 provides relatively limited temperature and humidity accuracy.
* Visibility estimation using an LDR is an approximation rather than a professional meteorological measurement.
* Wind measurements depend on the connected wind sensor and its calibration.
* Internet connectivity is required for cloud-based monitoring.

---

## 🔮 Future Improvements

* Add more accurate professional-grade sensors
* Add automatic weather forecasting
* Add AI-based weather anomaly detection
* Add mobile application support
* Add WebSocket-based real-time communication
* Add automated notifications
* Improve sensor calibration
* Add downloadable reports
* Add long-term weather analytics

---

## 👨‍💻 Developed By

**Yawar Nazir Sheikh**
**Muhammad Yaseen**

They are Computer Science Engineering Students at Govt Polytechnic College Anantnag

---

## 📜 License

This project is developed as an academic project.
See the repository license for usage and distribution terms.

---

### ⭐ If you find this project useful, consider starring the repository.
