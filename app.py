import os
import psycopg2
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from datetime import datetime
import csv
import io

app = Flask(__name__)
CORS(app)

# 🔐 SECURITY
API_KEY = "gpcaweatherstation25"

# ⚡ RATE LIMIT
limiter = Limiter(get_remote_address, app=app, default_limits=["10 per minute"])

# 📦 DATABASE
DATABASE_URL = os.environ.get("DATABASE_URL")

# ⚡ CACHE
latest_cache = None


# ================= DATABASE =================

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    try:
        con = get_db()
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id SERIAL PRIMARY KEY,
                temperature FLOAT,
                humidity FLOAT,
                rain_value INT,
                rain_status TEXT,
                wind_speed FLOAT,
                wind_direction TEXT,
                visibility FLOAT,
                alert TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        con.commit()
        cur.close()
        con.close()
        print("✅ DB READY")

    except Exception as e:
        print("❌ DB INIT ERROR:", e)


if DATABASE_URL:
    init_db()
else:
    print("❌ DATABASE_URL missing")


# ================= PAGES =================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/health")
def health():
    return jsonify({"status": "running"})

@app.route("/ping")
def ping():
    return "ok"


# ================= RECEIVE DATA =================

@app.route("/api/data", methods=["POST"])
@limiter.limit("10 per minute")
def receive_data():

    # 🔐 API KEY CHECK
    if request.headers.get("x-api-key") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        temperature = data.get("temperature")
        humidity = data.get("humidity")
        rain_value = data.get("rain_value")
        rain_status = data.get("rain_status", "No Rain")
        wind_speed = data.get("wind_speed")
        wind_direction = data.get("wind_direction", "N/A")
        visibility = data.get("visibility")
        visibility_status = data.get("visibility_status", "OK")

        # 🔧 HANDLE NOT CONNECTED
        if visibility_status == "Not Connected":
            visibility = -1

        # 🚨 ALERTS
        alerts = []

        # ✅ SAFE CHECKS (NO CRASH)
        if wind_speed is not None and wind_speed > 30:
            alerts.append("Storm Warning")
        
        if temperature is not None and temperature > 40:
            alerts.append("Heat Alert")
        
        if visibility_status != "Not Connected" and visibility is not None and visibility < 20:
            alerts.append("Low Visibility")
        
        if rain_status != "Not Connected" and rain_status and rain_status.lower() in ["light rain", "heavy rain"]:
            alerts.append("Rain Alert")

        alert = ", ".join(alerts) if alerts else "Normal"

        # 💾 STORE IN DB
        try:
            con = get_db()
            cur = con.cursor()

            cur.execute("""
                INSERT INTO weather
                (temperature, humidity, rain_value, rain_status,
                 wind_speed, wind_direction, visibility, alert)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                temperature, humidity, rain_value, rain_status,
                wind_speed, wind_direction, visibility, alert
            ))

            con.commit()
            cur.close()
            con.close()

        except Exception as db_error:
            print("❌ DB ERROR:", db_error)
            return jsonify({"error": "Database Failed"}), 500

        # ⚡ UPDATE CACHE (NO device_status here)
        global latest_cache
        latest_cache = {
            "temperature": temperature,
            "humidity": humidity,
            "rain": rain_status,
            "wind_speed": wind_speed,
            "visibility": visibility,
            "visibility_status": visibility_status,
            "alert": alert
        }

        return jsonify({"status": "stored", "alert": alert})

    except Exception as e:
        print("❌ API ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ================= LATEST =================

@app.route("/api/latest")
def latest():
    global latest_cache

    try:
        con = get_db()
        cur = con.cursor()

        cur.execute("""
            SELECT temperature, humidity, rain_status,
                   wind_speed, wind_direction, visibility,
                   alert, created_at
            FROM weather
            ORDER BY id DESC
            LIMIT 1
        """)

        row = cur.fetchone()

        if not row:
            return jsonify({"message": "No data available yet"})

        created_time = row[7]
        now = datetime.utcnow()

        seconds = (now - created_time).total_seconds()
        device_status = "Offline" if seconds > 40 else "Online"

        if device_status == "Offline":
            return jsonify({"device_status": "Offline"})

        # 📊 STATS (12 HOURS)
        cur.execute("""
            SELECT MIN(temperature), MAX(temperature), AVG(temperature)
            FROM weather
            WHERE created_at >= NOW() - INTERVAL '12 hours'
        """)

        stats = cur.fetchone()

        min_temp = float(stats[0]) if stats[0] else None
        max_temp = float(stats[1]) if stats[1] else None
        avg_temp = round(float(stats[2]), 2) if stats[2] else None

        # 📈 TREND (SMART)
        cur.execute("""
            SELECT temperature
            FROM weather
            ORDER BY id DESC
            LIMIT 6
        """)

        temps = [t[0] for t in cur.fetchall() if t[0] is not None]

        trend = "Stable"

        if len(temps) >= 3:
            changes = [(temps[i] - temps[i+1]) for i in range(len(temps)-1)]
            avg_change = sum(changes) / len(changes)

            if avg_change > 0.5:
                trend = "Rising"
            elif avg_change < -0.5:
                trend = "Falling"

        cur.close()
        con.close()

        # ⚡ USE CACHE FOR LATEST
        if latest_cache:
            temperature = latest_cache.get("temperature", row[0])
            humidity = latest_cache.get("humidity", row[1])
            rain = latest_cache.get("rain", row[2])
            wind_speed = latest_cache.get("wind_speed", row[3])
            visibility = latest_cache.get("visibility", row[5])
            visibility_status = latest_cache.get("visibility_status", "OK")
            alert = latest_cache.get("alert", row[6])
        else:
            temperature = row[0]
            humidity = row[1]
            rain = row[2]
            wind_speed = row[3]
            visibility = row[5]
            visibility_status = "Not Connected" if row[5] == -1 else "OK"
            alert = row[6]

        return jsonify({
            "temperature": temperature,
            "humidity": humidity,
            "rain": rain,
            "wind_speed": wind_speed,
            "wind_direction": row[4],
            "visibility": visibility,
            "visibility_status": visibility_status,
            "alert": alert,
            "min_temp": min_temp,
            "max_temp": max_temp,
            "avg_temp": avg_temp,
            "trend": trend,
            "device_status": device_status
        })

    except Exception as e:
        print("❌ LATEST ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ================= HISTORY =================

@app.route("/api/history")
def history():
    try:
        mode = request.args.get("mode", "hourly")

        con = get_db()
        cur = con.cursor()

        if mode == "daily":
            cur.execute("""
                WITH days AS (
                    SELECT generate_series(
                        CURRENT_DATE - INTERVAL '6 days',
                        CURRENT_DATE,
                        INTERVAL '1 day'
                    ) AS day
                )
                SELECT d.day,
                       COALESCE(ROUND(AVG(w.temperature)::numeric, 2), 0)
                FROM days d
                LEFT JOIN weather w
                ON DATE(w.created_at) = d.day
                GROUP BY d.day
                ORDER BY d.day ASC
            """)
        else:
            cur.execute("""
                WITH hours AS (
                    SELECT generate_series(
                        date_trunc('hour', NOW()) - INTERVAL '11 hours',
                        date_trunc('hour', NOW()),
                        INTERVAL '1 hour'
                    ) AS hour
                )
                SELECT h.hour,
                       COALESCE(ROUND(AVG(w.temperature)::numeric, 2), 0)
                FROM hours h
                LEFT JOIN weather w
                ON date_trunc('hour', w.created_at) = h.hour
                GROUP BY h.hour
                ORDER BY h.hour ASC
            """)

        rows = cur.fetchall()
        cur.close()
        con.close()

        return jsonify([
            {"time": str(r[0]), "temperature": float(r[1])}
            for r in rows
        ])

    except Exception as e:
        print("HISTORY ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ================= EXPORT =================

@app.route("/api/export")
def export_csv():
    try:
        con = get_db()
        cur = con.cursor()

        cur.execute("""
            SELECT created_at, temperature, humidity,
                   rain_status, wind_speed,
                   wind_direction, visibility
            FROM weather
            WHERE created_at >= NOW() - INTERVAL '7 days'
            ORDER BY created_at ASC
        """)

        rows = cur.fetchall()
        cur.close()
        con.close()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Date", "Time", "Temperature (°C)", "Humidity (%)",
            "Rain Status", "Wind Speed (km/h)", "Wind Direction", "Visibility (%)"
        ])

        for row in rows:
            timestamp = row[0]
            writer.writerow([
                timestamp.strftime("%d-%m-%Y"),
                timestamp.strftime("%I:%M %p"),
                f"{row[1]} °C",
                f"{row[2]} %",
                row[3],
                f"{row[4]} km/h" if row[4] else "",
                row[5] if row[5] else "",
                f"{row[6]} %" if row[6] else ""
            ])

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=weather_data_last_7_days.csv"}
        )

    except Exception as e:
        print("EXPORT ERROR:", e)
        return jsonify({"error": str(e)}), 500


     # ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)
