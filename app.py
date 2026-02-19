import os
import psycopg2
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

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
        print("Database initialized successfully")

    except Exception as e:
        print("Database init failed:", e)

init_db()


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/health")
def health():
    return jsonify({"status": "running"})


@app.route("/api/data", methods=["POST"])
def receive_data():
    try:
        data = request.get_json(force=True)

        required = ["temperature", "humidity", "rain_value", "rain_status"]
        if not data or not all(k in data for k in required):
            return jsonify({"error": "Invalid data"}), 400

        temperature = data["temperature"]
        humidity = data["humidity"]
        rain_value = data["rain_value"]
        rain_status = data["rain_status"]
        wind_speed = data.get("wind_speed")
        wind_direction = data.get("wind_direction")
        visibility = data.get("visibility")

        alert_message = "Normal"
        if temperature > 40:
            alert_message = "Heat Alert"
        elif wind_speed and wind_speed > 30:
            alert_message = "Storm Warning"
        elif visibility and visibility < 20:
            alert_message = "Low Visibility Warning"
        elif rain_status.lower() != "no rain":
            alert_message = "Rain Alert"

        con = get_db()
        cur = con.cursor()

        cur.execute("""
            INSERT INTO weather
            (temperature, humidity, rain_value, rain_status,
             wind_speed, wind_direction, visibility, alert)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            temperature, humidity, rain_value, rain_status,
            wind_speed, wind_direction, visibility, alert_message
        ))

        con.commit()
        cur.close()
        con.close()

        return jsonify({"status": "stored", "alert": alert_message}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/latest", methods=["GET"])
def latest_data():
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
        current_time = datetime.utcnow()

        seconds_diff = (current_time - created_time).total_seconds()
        device_status = "Offline" if seconds_diff > 30 else "Online"

        if device_status == "Offline":
            cur.close()
            con.close()
            return jsonify({
                "temperature": None,
                "humidity": None,
                "rain": None,
                "wind_speed": None,
                "wind_direction": None,
                "visibility": None,
                "alert": None,
                "trend": None,
                "min_temp": None,
                "max_temp": None,
                "avg_temp": None,
                "device_status": "Offline",
                "time": None
            })

        # TREND
        cur.execute("""
            SELECT temperature
            FROM weather
            ORDER BY id DESC
            LIMIT 5
        """)
        temps = [t[0] for t in cur.fetchall()]
        trend = "Stable"

        if len(temps) >= 5:
            first_avg = sum(temps[3:5]) / 2
            last_avg = sum(temps[0:2]) / 2
            if last_avg > first_avg:
                trend = "Rising"
            elif last_avg < first_avg:
                trend = "Falling"

        # STATS
        cur.execute("""
            SELECT temperature
            FROM weather
            ORDER BY id DESC
            LIMIT 24
        """)
        stats = [t[0] for t in cur.fetchall()]

        min_temp = min(stats)
        max_temp = max(stats)
        avg_temp = round(sum(stats)/len(stats), 2)

        cur.close()
        con.close()

        return jsonify({
            "temperature": row[0],
            "humidity": row[1],
            "rain": row[2],
            "wind_speed": row[3],
            "wind_direction": row[4],
            "visibility": row[5],
            "alert": row[6],
            "trend": trend,
            "min_temp": min_temp,
            "max_temp": max_temp,
            "avg_temp": avg_temp,
            "device_status": device_status,
            "time": row[7]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def history():
    try:
        mode = request.args.get("mode", "hourly")

        con = get_db()
        cur = con.cursor()

        if mode == "daily":
            cur.execute("""
                SELECT DATE(created_at) as day,
                       ROUND(AVG(temperature)::numeric, 2)
                FROM weather
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY day
                ORDER BY day ASC
            """)
            rows = cur.fetchall()

            data = [{
                "time": str(r[0]),
                "temperature": float(r[1])
            } for r in rows]

        else:
            # PROPER LAST 12 HOURS
            cur.execute("""
                WITH hours AS (
                    SELECT generate_series(
                        date_trunc('hour', NOW()) - INTERVAL '11 hours',
                        date_trunc('hour', NOW()),
                        INTERVAL '1 hour'
                    ) AS hour
                )
                SELECT h.hour,
                       ROUND(AVG(w.temperature)::numeric, 2)
                FROM hours h
                LEFT JOIN weather w
                  ON date_trunc('hour', w.created_at) = h.hour
                GROUP BY h.hour
                ORDER BY h.hour ASC
            """)
            rows = cur.fetchall()

            data = [{
                "time": str(r[0]),
                "temperature": float(r[1]) if r[1] is not None else None
            } for r in rows]

        cur.close()
        con.close()

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500




